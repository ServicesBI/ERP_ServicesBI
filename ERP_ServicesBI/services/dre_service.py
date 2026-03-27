# =============================================================================
# services/dre_service.py
# =============================================================================
# CRIAR ESTE ARQUIVO EM: ERP_ServicesBI/services/dre_service.py
# (Crie a pasta 'services' se não existir, com um __init__.py vazio)
# =============================================================================

from decimal import Decimal
from datetime import date, timedelta
from django.db.models import Sum, Q
from django.utils import timezone


class DREService:
    """
    Serviço para cálculo automático da DRE
    Busca dados de ContaPagar, ContaReceber e calcula conforme regime tributário
    """
    
    def __init__(self, empresa, data_inicio, data_fim, regime_tributario=None):
        self.empresa = empresa
        self.data_inicio = data_inicio
        self.data_fim = data_fim
        
        # Buscar configuração da empresa ou usar regime informado
        from ..models import ConfiguracaoDRE
        try:
            self.config = ConfiguracaoDRE.objects.get(empresa=empresa)
            self.regime = regime_tributario or self.config.regime_tributario
        except ConfiguracaoDRE.DoesNotExist:
            self.config = None
            self.regime = regime_tributario or 'simples'
    
    def calcular_dre_completa(self):
        """
        Calcula todos os valores da DRE e retorna dicionário completo
        """
        resultado = {
            'empresa': self.empresa,
            'periodo': {
                'inicio': self.data_inicio,
                'fim': self.data_fim,
            },
            'regime': self.regime,
            'linhas': [],
            'totais': {},
            'indicadores': {},
        }
        
        # 1. RECEITA OPERACIONAL BRUTA
        receita_bruta = self._calcular_receitas_brutas()
        
        # 2. DEDUÇÕES DA RECEITA
        deducoes = self._calcular_deducoes()
        
        # 3. RECEITA LÍQUIDA
        receita_liquida = receita_bruta - deducoes
        
        # 4. CUSTOS (CMV/CPV/CSV)
        custos = self._calcular_custos()
        
        # 5. LUCRO BRUTO
        lucro_bruto = receita_liquida - custos
        
        # 6. DESPESAS OPERACIONAIS
        despesas_op = self._calcular_despesas_operacionais()
        
        # 7. RESULTADO OPERACIONAL (EBIT)
        resultado_operacional = lucro_bruto - despesas_op['total']
        
        # 8. RESULTADO FINANCEIRO
        resultado_financeiro = self._calcular_resultado_financeiro()
        
        # 9. RESULTADO ANTES IR/CSLL (LAIR)
        lair = resultado_operacional + resultado_financeiro['liquido']
        
        # 10. IMPOSTOS SOBRE O LUCRO
        impostos = self._calcular_impostos(receita_bruta, lair)
        
        # 11. LUCRO LÍQUIDO
        lucro_liquido = lair - impostos['total']
        
        # Montar estrutura de linhas
        resultado['linhas'] = self._montar_linhas(
            receita_bruta=receita_bruta,
            deducoes=deducoes,
            receita_liquida=receita_liquida,
            custos=custos,
            lucro_bruto=lucro_bruto,
            despesas_op=despesas_op,
            resultado_operacional=resultado_operacional,
            resultado_financeiro=resultado_financeiro,
            lair=lair,
            impostos=impostos,
            lucro_liquido=lucro_liquido
        )
        
        # Totais
        resultado['totais'] = {
            'receita_bruta': receita_bruta,
            'deducoes': deducoes,
            'receita_liquida': receita_liquida,
            'custos': custos,
            'lucro_bruto': lucro_bruto,
            'despesas_operacionais': despesas_op['total'],
            'resultado_operacional': resultado_operacional,
            'receitas_financeiras': resultado_financeiro['receitas'],
            'despesas_financeiras': resultado_financeiro['despesas'],
            'resultado_financeiro': resultado_financeiro['liquido'],
            'lair': lair,
            'impostos': impostos['total'],
            'lucro_liquido': lucro_liquido,
        }
        
        # Indicadores
        resultado['indicadores'] = self._calcular_indicadores(resultado['totais'])
        
        return resultado
    
    def _calcular_receitas_brutas(self):
        """Soma receitas brutas do período (ContaReceber pagas)"""
        from ..models import ContaReceber, CategoriaFinanceira
        
        # Buscar categorias de receita bruta
        categorias_receita = CategoriaFinanceira.objects.filter(
            grupo_dre__in=['receita_bruta', 'outras_receitas'],
            ativo=True
        ).values_list('id', flat=True)
        
        total = ContaReceber.objects.filter(
            Q(data_recebimento__gte=self.data_inicio, data_recebimento__lte=self.data_fim) |
            Q(data_baixa__gte=self.data_inicio, data_baixa__lte=self.data_fim),
            status__in=['recebido', 'quitado'],
            categoria_id__in=categorias_receita
        ).aggregate(total=Sum('valor_recebido'))['total'] or Decimal('0')
        
        # Se não tem categoria específica, pegar todas as receitas
        if total == 0:
            total = ContaReceber.objects.filter(
                Q(data_recebimento__gte=self.data_inicio, data_recebimento__lte=self.data_fim) |
                Q(data_baixa__gte=self.data_inicio, data_baixa__lte=self.data_fim),
                status__in=['recebido', 'quitado']
            ).aggregate(total=Sum('valor_recebido'))['total'] or Decimal('0')
        
        return total
    
    def _calcular_deducoes(self):
        """Calcula deduções da receita (impostos sobre vendas, devoluções)"""
        from ..models import ContaPagar, CategoriaFinanceira
        
        # Buscar categorias de deduções
        categorias_deducoes = CategoriaFinanceira.objects.filter(
            grupo_dre='deducoes',
            ativo=True
        ).values_list('id', flat=True)
        
        total = ContaPagar.objects.filter(
            Q(data_pagamento__gte=self.data_inicio, data_pagamento__lte=self.data_fim) |
            Q(data_baixa__gte=self.data_inicio, data_baixa__lte=self.data_fim),
            status__in=['pago', 'quitado'],
            categoria_id__in=categorias_deducoes
        ).aggregate(total=Sum('valor_pago'))['total'] or Decimal('0')
        
        return total
    
    def _calcular_custos(self):
        """Calcula CMV/CPV/CSV"""
        from ..models import ContaPagar, CategoriaFinanceira
        
        # Buscar categorias de custo
        categorias_custo = CategoriaFinanceira.objects.filter(
            grupo_dre__in=['cmv', 'cpv', 'csv'],
            ativo=True
        ).values_list('id', flat=True)
        
        total = ContaPagar.objects.filter(
            Q(data_pagamento__gte=self.data_inicio, data_pagamento__lte=self.data_fim) |
            Q(data_baixa__gte=self.data_inicio, data_baixa__lte=self.data_fim),
            status__in=['pago', 'quitado'],
            categoria_id__in=categorias_custo
        ).aggregate(total=Sum('valor_pago'))['total'] or Decimal('0')
        
        return total
    
    def _calcular_despesas_operacionais(self):
        """Calcula despesas operacionais por grupo"""
        from ..models import ContaPagar, CategoriaFinanceira
        
        grupos_despesa = ['despesa_vendas', 'despesa_admin', 'despesa_pessoal', 'depreciacao', 'outras_despesas']
        
        resultado = {
            'vendas': Decimal('0'),
            'administrativas': Decimal('0'),
            'pessoal': Decimal('0'),
            'depreciacao': Decimal('0'),
            'outras': Decimal('0'),
            'total': Decimal('0'),
        }
        
        for grupo in grupos_despesa:
            categorias = CategoriaFinanceira.objects.filter(
                grupo_dre=grupo,
                ativo=True
            ).values_list('id', flat=True)
            
            valor = ContaPagar.objects.filter(
                Q(data_pagamento__gte=self.data_inicio, data_pagamento__lte=self.data_fim) |
                Q(data_baixa__gte=self.data_inicio, data_baixa__lte=self.data_fim),
                status__in=['pago', 'quitado'],
                categoria_id__in=categorias
            ).aggregate(total=Sum('valor_pago'))['total'] or Decimal('0')
            
            if grupo == 'despesa_vendas':
                resultado['vendas'] = valor
            elif grupo == 'despesa_admin':
                resultado['administrativas'] = valor
            elif grupo == 'despesa_pessoal':
                resultado['pessoal'] = valor
            elif grupo == 'depreciacao':
                resultado['depreciacao'] = valor
            else:
                resultado['outras'] = valor
        
        resultado['total'] = sum([
            resultado['vendas'],
            resultado['administrativas'],
            resultado['pessoal'],
            resultado['depreciacao'],
            resultado['outras']
        ])
        
        return resultado
    
    def _calcular_resultado_financeiro(self):
        """Calcula receitas e despesas financeiras"""
        from ..models import ContaPagar, ContaReceber, CategoriaFinanceira
        
        # Receitas Financeiras
        cat_receita_fin = CategoriaFinanceira.objects.filter(
            grupo_dre='receita_financeira',
            ativo=True
        ).values_list('id', flat=True)
        
        receitas = ContaReceber.objects.filter(
            Q(data_recebimento__gte=self.data_inicio, data_recebimento__lte=self.data_fim) |
            Q(data_baixa__gte=self.data_inicio, data_baixa__lte=self.data_fim),
            status__in=['recebido', 'quitado'],
            categoria_id__in=cat_receita_fin
        ).aggregate(total=Sum('valor_recebido'))['total'] or Decimal('0')
        
        # Despesas Financeiras
        cat_despesa_fin = CategoriaFinanceira.objects.filter(
            grupo_dre='despesa_financeira',
            ativo=True
        ).values_list('id', flat=True)
        
        despesas = ContaPagar.objects.filter(
            Q(data_pagamento__gte=self.data_inicio, data_pagamento__lte=self.data_fim) |
            Q(data_baixa__gte=self.data_inicio, data_baixa__lte=self.data_fim),
            status__in=['pago', 'quitado'],
            categoria_id__in=cat_despesa_fin
        ).aggregate(total=Sum('valor_pago'))['total'] or Decimal('0')
        
        return {
            'receitas': receitas,
            'despesas': despesas,
            'liquido': receitas - despesas
        }
    
    def _calcular_impostos(self, receita_bruta, lair):
        """
        Calcula impostos conforme regime tributário
        """
        resultado = {
            'das': Decimal('0'),
            'irpj': Decimal('0'),
            'irpj_adicional': Decimal('0'),
            'csll': Decimal('0'),
            'total': Decimal('0'),
        }
        
        if not self.config:
            return resultado
        
        if self.regime == 'simples':
            # Simples Nacional: alíquota única sobre receita bruta
            resultado['das'] = receita_bruta * (self.config.aliquota_simples / 100)
            resultado['total'] = resultado['das']
            
        elif self.regime == 'presumido':
            # Lucro Presumido
            if lair > 0:
                # Base de cálculo presumida
                if self.config.atividade_principal == 'servico':
                    base_presuncao = receita_bruta * (self.config.percentual_presuncao_servico / 100)
                else:
                    base_presuncao = receita_bruta * (self.config.percentual_presuncao_comercio / 100)
                
                # IRPJ (15%)
                resultado['irpj'] = base_presuncao * (self.config.aliquota_irpj / 100)
                
                # IRPJ Adicional (10% sobre excedente de R$ 20.000/mês)
                meses = self._calcular_meses_periodo()
                limite = Decimal('20000') * meses
                if base_presuncao > limite:
                    resultado['irpj_adicional'] = (base_presuncao - limite) * (self.config.aliquota_irpj_adicional / 100)
                
                # CSLL (9%)
                resultado['csll'] = base_presuncao * (self.config.aliquota_csll / 100)
                
                resultado['total'] = resultado['irpj'] + resultado['irpj_adicional'] + resultado['csll']
                
        elif self.regime == 'real':
            # Lucro Real
            if lair > 0:
                # IRPJ (15%)
                resultado['irpj'] = lair * (self.config.aliquota_irpj / 100)
                
                # IRPJ Adicional (10% sobre excedente de R$ 20.000/mês)
                meses = self._calcular_meses_periodo()
                limite = Decimal('20000') * meses
                if lair > limite:
                    resultado['irpj_adicional'] = (lair - limite) * (self.config.aliquota_irpj_adicional / 100)
                
                # CSLL (9%)
                resultado['csll'] = lair * (self.config.aliquota_csll / 100)
                
                resultado['total'] = resultado['irpj'] + resultado['irpj_adicional'] + resultado['csll']
        
        return resultado
    
    def _calcular_meses_periodo(self):
        """Calcula número de meses no período"""
        delta = self.data_fim - self.data_inicio
        meses = delta.days / 30
        return max(1, round(meses))
    
    def _calcular_indicadores(self, totais):
        """Calcula indicadores financeiros"""
        receita_liq = totais.get('receita_liquida', Decimal('0'))
        
        if receita_liq == 0:
            return {
                'margem_bruta': Decimal('0'),
                'margem_operacional': Decimal('0'),
                'margem_ebitda': Decimal('0'),
                'margem_liquida': Decimal('0'),
            }
        
        return {
            'margem_bruta': (totais['lucro_bruto'] / receita_liq) * 100,
            'margem_operacional': (totais['resultado_operacional'] / receita_liq) * 100,
            'margem_ebitda': ((totais['resultado_operacional'] + totais.get('depreciacao', Decimal('0'))) / receita_liq) * 100,
            'margem_liquida': (totais['lucro_liquido'] / receita_liq) * 100,
        }
    
    def _montar_linhas(self, **kwargs):
        """Monta estrutura de linhas para exibição"""
        receita_liq = kwargs['receita_liquida'] or Decimal('1')
        
        def pct(valor):
            """Calcula percentual sobre receita líquida"""
            if receita_liq == 0:
                return Decimal('0')
            return (valor / receita_liq) * 100
        
        linhas = [
            {
                'codigo': '1.0',
                'descricao': 'RECEITA OPERACIONAL BRUTA',
                'valor': kwargs['receita_bruta'],
                'percentual': pct(kwargs['receita_bruta']),
                'nivel': 0,
                'negrito': True,
                'natureza': 'receita',
            },
            {
                'codigo': '2.0',
                'descricao': '(-) DEDUÇÕES DA RECEITA',
                'valor': kwargs['deducoes'],
                'percentual': pct(kwargs['deducoes']),
                'nivel': 0,
                'negrito': False,
                'natureza': 'despesa',
            },
            {
                'codigo': '3.0',
                'descricao': '(=) RECEITA OPERACIONAL LÍQUIDA',
                'valor': kwargs['receita_liquida'],
                'percentual': Decimal('100'),
                'nivel': 0,
                'negrito': True,
                'natureza': 'resultado',
            },
            {
                'codigo': '4.0',
                'descricao': '(-) CUSTOS OPERACIONAIS (CMV/CPV/CSV)',
                'valor': kwargs['custos'],
                'percentual': pct(kwargs['custos']),
                'nivel': 0,
                'negrito': False,
                'natureza': 'despesa',
            },
            {
                'codigo': '5.0',
                'descricao': '(=) LUCRO BRUTO',
                'valor': kwargs['lucro_bruto'],
                'percentual': pct(kwargs['lucro_bruto']),
                'nivel': 0,
                'negrito': True,
                'natureza': 'resultado',
            },
            {
                'codigo': '6.0',
                'descricao': '(-) DESPESAS OPERACIONAIS',
                'valor': kwargs['despesas_op']['total'],
                'percentual': pct(kwargs['despesas_op']['total']),
                'nivel': 0,
                'negrito': False,
                'natureza': 'despesa',
            },
            {
                'codigo': '6.1',
                'descricao': 'Despesas com Vendas',
                'valor': kwargs['despesas_op']['vendas'],
                'percentual': pct(kwargs['despesas_op']['vendas']),
                'nivel': 1,
                'negrito': False,
                'natureza': 'despesa',
            },
            {
                'codigo': '6.2',
                'descricao': 'Despesas Administrativas',
                'valor': kwargs['despesas_op']['administrativas'],
                'percentual': pct(kwargs['despesas_op']['administrativas']),
                'nivel': 1,
                'negrito': False,
                'natureza': 'despesa',
            },
            {
                'codigo': '6.3',
                'descricao': 'Despesas com Pessoal',
                'valor': kwargs['despesas_op']['pessoal'],
                'percentual': pct(kwargs['despesas_op']['pessoal']),
                'nivel': 1,
                'negrito': False,
                'natureza': 'despesa',
            },
            {
                'codigo': '6.4',
                'descricao': 'Depreciação e Amortização',
                'valor': kwargs['despesas_op']['depreciacao'],
                'percentual': pct(kwargs['despesas_op']['depreciacao']),
                'nivel': 1,
                'negrito': False,
                'natureza': 'despesa',
            },
            {
                'codigo': '6.5',
                'descricao': 'Outras Despesas Operacionais',
                'valor': kwargs['despesas_op']['outras'],
                'percentual': pct(kwargs['despesas_op']['outras']),
                'nivel': 1,
                'negrito': False,
                'natureza': 'despesa',
            },
            {
                'codigo': '7.0',
                'descricao': '(=) RESULTADO OPERACIONAL (EBIT)',
                'valor': kwargs['resultado_operacional'],
                'percentual': pct(kwargs['resultado_operacional']),
                'nivel': 0,
                'negrito': True,
                'natureza': 'resultado',
            },
            {
                'codigo': '8.0',
                'descricao': '(+) Receitas Financeiras',
                'valor': kwargs['resultado_financeiro']['receitas'],
                'percentual': pct(kwargs['resultado_financeiro']['receitas']),
                'nivel': 0,
                'negrito': False,
                'natureza': 'receita',
            },
            {
                'codigo': '8.1',
                'descricao': '(-) Despesas Financeiras',
                'valor': kwargs['resultado_financeiro']['despesas'],
                'percentual': pct(kwargs['resultado_financeiro']['despesas']),
                'nivel': 0,
                'negrito': False,
                'natureza': 'despesa',
            },
            {
                'codigo': '9.0',
                'descricao': '(=) RESULTADO ANTES DO IR/CSLL (LAIR)',
                'valor': kwargs['lair'],
                'percentual': pct(kwargs['lair']),
                'nivel': 0,
                'negrito': True,
                'natureza': 'resultado',
            },
        ]
        
        # Adicionar impostos conforme regime
        if self.regime == 'simples':
            linhas.append({
                'codigo': '10.0',
                'descricao': '(-) DAS (Simples Nacional)',
                'valor': kwargs['impostos']['das'],
                'percentual': pct(kwargs['impostos']['das']),
                'nivel': 0,
                'negrito': False,
                'natureza': 'despesa',
            })
        else:
            linhas.extend([
                {
                    'codigo': '10.0',
                    'descricao': '(-) IRPJ',
                    'valor': kwargs['impostos']['irpj'],
                    'percentual': pct(kwargs['impostos']['irpj']),
                    'nivel': 0,
                    'negrito': False,
                    'natureza': 'despesa',
                },
                {
                    'codigo': '10.1',
                    'descricao': '(-) IRPJ Adicional',
                    'valor': kwargs['impostos']['irpj_adicional'],
                    'percentual': pct(kwargs['impostos']['irpj_adicional']),
                    'nivel': 1,
                    'negrito': False,
                    'natureza': 'despesa',
                },
                {
                    'codigo': '10.2',
                    'descricao': '(-) CSLL',
                    'valor': kwargs['impostos']['csll'],
                    'percentual': pct(kwargs['impostos']['csll']),
                    'nivel': 0,
                    'negrito': False,
                    'natureza': 'despesa',
                },
            ])
        
        # Lucro Líquido
        linhas.append({
            'codigo': '11.0',
            'descricao': '(=) LUCRO/PREJUÍZO LÍQUIDO DO EXERCÍCIO',
            'valor': kwargs['lucro_liquido'],
            'percentual': pct(kwargs['lucro_liquido']),
            'nivel': 0,
            'negrito': True,
            'natureza': 'resultado',
        })
        
        return linhas
    
    def salvar_relatorio(self, user=None):
        """Salva o relatório calculado no banco"""
        from ..models import RelatorioDRE
        
        dados = self.calcular_dre_completa()
        
        relatorio, created = RelatorioDRE.objects.update_or_create(
            empresa=self.empresa,
            data_inicio=self.data_inicio,
            data_fim=self.data_fim,
            defaults={
                'regime_tributario': self.regime,
                'receita_bruta': dados['totais']['receita_bruta'],
                'deducoes': dados['totais']['deducoes'],
                'receita_liquida': dados['totais']['receita_liquida'],
                'custo_total': dados['totais']['custos'],
                'lucro_bruto': dados['totais']['lucro_bruto'],
                'despesas_operacionais': dados['totais']['despesas_operacionais'],
                'resultado_operacional': dados['totais']['resultado_operacional'],
                'resultado_financeiro': dados['totais']['resultado_financeiro'],
                'resultado_antes_ir': dados['totais']['lair'],
                'impostos_lucro': dados['totais']['impostos'],
                'lucro_liquido': dados['totais']['lucro_liquido'],
                'dados_json': dados,
                'gerado_por': user,
            }
        )
        
        return relatorio
