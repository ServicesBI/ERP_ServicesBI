# -*- coding: utf-8 -*-
from django import forms
from django.contrib.auth.models import User
from .models import (
    Empresa, Cliente, Fornecedor, Produto, CategoriaProduto, Vendedor, 
    CondicaoPagamento, FormaPagamento,
    PedidoCompra, ItemPedidoCompra, 
    NotaFiscalEntrada, ItemNotaFiscalEntrada,
    Orcamento, ItemOrcamento, PedidoVenda, ItemPedidoVenda, 
    NotaFiscalSaida, ItemNotaFiscalSaida,
    ContaPagar, ContaReceber, MovimentoCaixa,
    CategoriaFinanceira, CentroCusto, OrcamentoFinanceiro,
    ExtratoBancario, LancamentoExtrato, ConfiguracaoDRE, LinhaDRE, RelatorioDRE,
    MovimentacaoEstoque, Inventario, ItemInventario, 
    TransferenciaEstoque, ItemTransferencia,
    CotacaoMae, ItemSolicitado, CotacaoFornecedor, ItemCotacaoFornecedor
)

# =============================================================================
# GERENCIADOR
# =============================================================================

def MoneyField(**kwargs):
    """Campo de moeda com formato brasileiro"""
    defaults = {
        'max_digits': 15,
        'decimal_places': 2,
        'localize': True,
        'required': False,
        'initial': 0
    }
    defaults.update(kwargs)
    return forms.DecimalField(**defaults)


class BaseForm(forms.ModelForm):
    """Configuração padrão de estilo para todos os forms"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'erp-input'})

# =============================================================================
# MÓDULO: CADASTRO - CLIENTES
# =============================================================================
# Pessoa (abstract), Cliente

class ClienteForm(BaseForm):
    limite_credito = MoneyField()
    
    class Meta:
        model = Cliente
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome_fantasia'].required = False
        self.fields['observacoes'].required = False
        self.fields['telefone'].required = False
        self.fields['email'].required = False
        self.fields['cep'].required = False
        self.fields['endereco'].required = False
        self.fields['numero'].required = False
        self.fields['bairro'].required = False
        self.fields['cidade'].required = False
        self.fields['estado'].required = False
        self.fields['rg_inscricao_estadual'].required = False
        self.fields['ativo'].required = False
        
        # NOVOS CAMPOS: Não obrigatórios
        self.fields['condicao_pagamento_padrao'].required = False
        self.fields['forma_pagamento_padrao'].required = False
        
        # Filtrar apenas registros ativos nos selects
        self.fields['condicao_pagamento_padrao'].queryset = CondicaoPagamento.objects.filter(ativo=True)
        self.fields['forma_pagamento_padrao'].queryset = FormaPagamento.objects.filter(ativo=True)
        
        # Adicionar classes CSS
        self.fields['condicao_pagamento_padrao'].widget.attrs.update({'class': 'form-select'})
        self.fields['forma_pagamento_padrao'].widget.attrs.update({'class': 'form-select'})



# =============================================================================
# MÓDULO: CADASTRO - VENDEDORES
# =============================================================================
# Vendedor

from decimal import Decimal
from django import forms
from .models import Vendedor


class VendedorForm(forms.ModelForm):
    class Meta:
        model = Vendedor
        fields = [
            'ativo',
            'foto',
            'nome',
            'cpf',
            'apelido',
            'telefone',
            'email',
            'comissao_padrao',
            'meta_vendas',
            'observacoes',
        ]
        widgets = {
            'foto': forms.FileInput(attrs={
                'class': 'foto-input',
                'accept': 'image/*',
            }),
            'nome': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Digite o nome completo do vendedor',
            }),
            'cpf': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '000.000.000-00',
                'maxlength': '14',
            }),
            'apelido': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Como prefere ser chamado',
            }),
            'telefone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '(00) 00000-0000',
                'maxlength': '15',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'email@exemplo.com',
            }),
            # CORRIGIDO: TextInput em vez de NumberInput
            'comissao_padrao': forms.TextInput(attrs={
                'class': 'form-input has-suffix',
                'placeholder': '5.00',
            }),
            'meta_vendas': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '0.00',
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Informações adicionais sobre o vendedor...',
                'rows': '4',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Campos opcionais
        self.fields['foto'].required = False
        self.fields['cpf'].required = False
        self.fields['apelido'].required = False
        self.fields['telefone'].required = False
        self.fields['meta_vendas'].required = False
        self.fields['observacoes'].required = False
        
        # Label customizado
        self.fields['comissao_padrao'].label = 'Comissão Padrão (%)'
        self.fields['meta_vendas'].label = 'Meta de Vendas Mensal'
        
        # Help texts
        self.fields['comissao_padrao'].help_text = 'Use ponto para decimal (ex: 15.00)'
        self.fields['meta_vendas'].help_text = 'Opcional - meta em reais'
        self.fields['foto'].help_text = 'Formatos: JPG, PNG. Máx: 2MB'
    
    def clean_cpf(self):
        """Valida e limpa o CPF"""
        cpf = self.cleaned_data.get('cpf', '')
        if cpf:
            cpf_limpo = ''.join(filter(str.isdigit, cpf))
            if len(cpf_limpo) != 11:
                raise forms.ValidationError('CPF deve ter 11 dígitos.')
            return cpf_limpo
        return cpf
    
    def clean_telefone(self):
        """Valida e limpa o telefone"""
        telefone = self.cleaned_data.get('telefone', '')
        if telefone:
            telefone_limpo = ''.join(filter(str.isdigit, telefone))
            return telefone_limpo
        return telefone
    
    def clean_comissao_padrao(self):
        """Converte comissão para Decimal"""
        comissao = self.cleaned_data.get('comissao_padrao')
        
        # Se já for Decimal, retorna direto
        if isinstance(comissao, Decimal):
            return comissao
            
        if not comissao or comissao == '':
            raise forms.ValidationError('Comissão é obrigatória.')
        
        try:
            # Converte string para Decimal (troca vírgula por ponto se necessário)
            comissao_str = str(comissao).replace(',', '.')
            valor = Decimal(comissao_str)
            
            # Valida range
            if valor < 0 or valor > 100:
                raise forms.ValidationError('Comissão deve estar entre 0 e 100.')
                
            return valor
        except:
            raise forms.ValidationError('Valor inválido. Use formato: 5.00')
    
    def clean_meta_vendas(self):
        """Converte meta de vendas para Decimal"""
        meta = self.cleaned_data.get('meta_vendas')
        
        # Se já for Decimal ou None, retorna
        if isinstance(meta, Decimal) or meta is None:
            return meta
            
        if meta == '':
            return None
            
        try:
            # Remove pontos de milhar e troca vírgula por ponto
            meta_str = str(meta).replace('.', '').replace(',', '.')
            return Decimal(meta_str)
        except:
            raise forms.ValidationError('Valor inválido. Use formato: 1000.00')
    
    def clean(self):
        """Validações gerais do formulário"""
        cleaned_data = super().clean()
        
        # Validação de email único
        email = cleaned_data.get('email')
        if email:
            qs = Vendedor.objects.filter(email=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('email', 'Já existe um vendedor com este e-mail.')
        
        return cleaned_data

# =============================================================================
# MÓDULO: CONFIGURAÇÕES - EMPRESA
# =============================================================================
# Empresa

class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = [
            'ativo',
            'nome_fantasia',
            'razao_social',
            'cnpj',
            'inscricao_estadual',
            'inscricao_municipal',
            'telefone',
            'email',
            'cep',
            'endereco',
            'numero',
            'bairro',
            'cidade',
            'estado',
        ]
        widgets = {
            'nome_fantasia': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Nome fantasia da empresa',
            }),
            'razao_social': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Razão social completa',
            }),
            'cnpj': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '00.000.000/0000-00',
                'maxlength': '18',
            }),
            'inscricao_estadual': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Inscrição Estadual',
            }),
            'inscricao_municipal': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Inscrição Municipal',
            }),
            'telefone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '(00) 00000-0000',
                'maxlength': '15',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'empresa@exemplo.com',
            }),
            'cep': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '00000-000',
                'maxlength': '9',
            }),
            'endereco': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Rua, Avenida, etc.',
            }),
            'numero': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Nº',
            }),
            'bairro': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Bairro',
            }),
            'cidade': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Cidade',
            }),
            'estado': forms.Select(attrs={
                'class': 'form-select',
            }, choices=[
                ('', 'Selecione...'),
                ('AC', 'AC'), ('AL', 'AL'), ('AP', 'AP'), ('AM', 'AM'),
                ('BA', 'BA'), ('CE', 'CE'), ('DF', 'DF'), ('ES', 'ES'),
                ('GO', 'GO'), ('MA', 'MA'), ('MT', 'MT'), ('MS', 'MS'),
                ('MG', 'MG'), ('PA', 'PA'), ('PB', 'PB'), ('PR', 'PR'),
                ('PE', 'PE'), ('PI', 'PI'), ('RJ', 'RJ'), ('RN', 'RN'),
                ('RS', 'RS'), ('RO', 'RO'), ('RR', 'RR'), ('SC', 'SC'),
                ('SP', 'SP'), ('SE', 'SE'), ('TO', 'TO'),
            ]),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Campos obrigatórios
        self.fields['nome_fantasia'].required = True
        self.fields['razao_social'].required = True
        self.fields['cnpj'].required = True
        
        # Campos opcionais
        self.fields['inscricao_estadual'].required = False
        self.fields['inscricao_municipal'].required = False
        self.fields['telefone'].required = False
        self.fields['email'].required = False
        self.fields['cep'].required = False
        self.fields['endereco'].required = False
        self.fields['numero'].required = False
        self.fields['bairro'].required = False
        self.fields['cidade'].required = False
        self.fields['estado'].required = False
        
        # Labels
        self.fields['nome_fantasia'].label = 'Nome Fantasia'
        self.fields['razao_social'].label = 'Razão Social'
        self.fields['inscricao_estadual'].label = 'Inscrição Estadual'
        self.fields['inscricao_municipal'].label = 'Inscrição Municipal'
    
    def clean_cnpj(self):
        """Valida e limpa o CNPJ"""
        cnpj = self.cleaned_data.get('cnpj', '')
        if cnpj:
            cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
            if len(cnpj_limpo) != 14:
                raise forms.ValidationError('CNPJ deve ter 14 dígitos.')
            return cnpj_limpo
        return cnpj
    
    def clean_telefone(self):
        """Valida e limpa o telefone"""
        telefone = self.cleaned_data.get('telefone', '')
        if telefone:
            telefone_limpo = ''.join(filter(str.isdigit, telefone))
            return telefone_limpo
        return telefone
    
    def clean_cep(self):
        """Valida e limpa o CEP"""
        cep = self.cleaned_data.get('cep', '')
        if cep:
            cep_limpo = ''.join(filter(str.isdigit, cep))
            return cep_limpo
        return cep


class FornecedorForm(forms.ModelForm):
    class Meta:
        model = Fornecedor
        fields = [
            'ativo',
            'tipo_pessoa',
            'nome_razao_social',
            'nome_fantasia',
            'cpf_cnpj',
            'rg_inscricao_estadual',
            'telefone',
            'email',
            'cep',
            'endereco',
            'numero',
            'bairro',
            'cidade',
            'estado',
            'limite_credito',
            'observacoes',
            'condicao_pagamento_padrao',
            'forma_pagamento_padrao',
        ]
        widgets = {
            'tipo_pessoa': forms.Select(attrs={
                'class': 'form-select',
            }, choices=[
                ('', 'Selecione...'),
                ('F', 'Física'),
                ('J', 'Jurídica'),
            ]),
            'nome_razao_social': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Nome ou razão social',
            }),
            'nome_fantasia': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Nome fantasia',
            }),
            'cpf_cnpj': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '00.000.000/0000-00',
                'maxlength': '18',
            }),
            'rg_inscricao_estadual': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'RG ou Inscrição Estadual',
            }),
            'telefone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '(00) 00000-0000',
                'maxlength': '15',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'email@exemplo.com',
            }),
            'cep': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '00000-000',
                'maxlength': '9',
            }),
            'endereco': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Rua, Avenida, etc.',
            }),
            'numero': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Nº',
            }),
            'bairro': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Bairro',
            }),
            'cidade': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Cidade',
            }),
            'estado': forms.Select(attrs={
                'class': 'form-select',
            }, choices=[
                ('', 'Selecione...'),
                ('AC', 'AC'), ('AL', 'AL'), ('AP', 'AP'), ('AM', 'AM'),
                ('BA', 'BA'), ('CE', 'CE'), ('DF', 'DF'), ('ES', 'ES'),
                ('GO', 'GO'), ('MA', 'MA'), ('MT', 'MT'), ('MS', 'MS'),
                ('MG', 'MG'), ('PA', 'PA'), ('PB', 'PB'), ('PR', 'PR'),
                ('PE', 'PE'), ('PI', 'PI'), ('RJ', 'RJ'), ('RN', 'RN'),
                ('RS', 'RS'), ('RO', 'RO'), ('RR', 'RR'), ('SC', 'SC'),
                ('SP', 'SP'), ('SE', 'SE'), ('TO', 'TO'),
            ]),
            'limite_credito': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'R$ 0,00',
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Observações...',
                'rows': '3',
            }),
            'condicao_pagamento_padrao': forms.Select(attrs={
                'class': 'form-select',
            }),
            'forma_pagamento_padrao': forms.Select(attrs={
                'class': 'form-select',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Campos obrigatórios
        self.fields['tipo_pessoa'].required = True
        self.fields['nome_razao_social'].required = True
        self.fields['cpf_cnpj'].required = True
        
        # Campos opcionais
        self.fields['nome_fantasia'].required = False
        self.fields['rg_inscricao_estadual'].required = False
        self.fields['telefone'].required = False
        self.fields['email'].required = False
        self.fields['cep'].required = False
        self.fields['endereco'].required = False
        self.fields['numero'].required = False
        self.fields['bairro'].required = False
        self.fields['cidade'].required = False
        self.fields['estado'].required = False
        self.fields['limite_credito'].required = False
        self.fields['observacoes'].required = False
        self.fields['ativo'].required = False
        
        # NOVOS CAMPOS: Não obrigatórios
        self.fields['condicao_pagamento_padrao'].required = False
        self.fields['forma_pagamento_padrao'].required = False
        
        # Filtrar apenas registros ativos nos selects
        self.fields['condicao_pagamento_padrao'].queryset = CondicaoPagamento.objects.filter(ativo=True)
        self.fields['forma_pagamento_padrao'].queryset = FormaPagamento.objects.filter(ativo=True)
        
        # Labels
        self.fields['nome_razao_social'].label = 'Nome / Razão Social'
        self.fields['nome_fantasia'].label = 'Nome Fantasia'
        self.fields['cpf_cnpj'].label = 'CPF/CNPJ'
        self.fields['rg_inscricao_estadual'].label = 'RG/Inscrição Estadual'
        self.fields['limite_credito'].label = 'Limite de Crédito'
        self.fields['condicao_pagamento_padrao'].label = 'Condição de Pagamento Padrão'
        self.fields['forma_pagamento_padrao'].label = 'Forma de Pagamento Padrão'
    
    def clean_cpf_cnpj(self):
        """Valida e limpa o CPF/CNPJ"""
        cpf_cnpj = self.cleaned_data.get('cpf_cnpj', '')
        if cpf_cnpj:
            limpo = ''.join(filter(str.isdigit, cpf_cnpj))
            tipo = self.cleaned_data.get('tipo_pessoa')
            
            if tipo == 'F' and len(limpo) != 11:
                raise forms.ValidationError('CPF deve ter 11 dígitos.')
            elif tipo == 'J' and len(limpo) != 14:
                raise forms.ValidationError('CNPJ deve ter 14 dígitos.')
            
            return limpo
        return cpf_cnpj
    
    def clean_telefone(self):
        """Valida e limpa o telefone"""
        telefone = self.cleaned_data.get('telefone', '')
        if telefone:
            return ''.join(filter(str.isdigit, telefone))
        return telefone
    
    def clean_cep(self):
        """Valida e limpa o CEP"""
        cep = self.cleaned_data.get('cep', '')
        if cep:
            return ''.join(filter(str.isdigit, cep))
        return cep
    
    def clean_limite_credito(self):
        """Converte limite de crédito para Decimal"""
        limite = self.cleaned_data.get('limite_credito')
        
        if isinstance(limite, Decimal):
            return limite
            
        if not limite or limite == '':
            return Decimal('0')
        
        try:
            # Remove R$ e pontos, troca vírgula por ponto
            limite_str = str(limite).replace('R$', '').replace('.', '').replace(',', '.').strip()
            return Decimal(limite_str)
        except:
            raise forms.ValidationError('Valor inválido para limite de crédito.')


# =============================================================================
# MÓDULO: CADASTRO - PRODUTOS
# =============================================================================
# CategoriaProduto, Produto

class CategoriaProdutoForm(BaseForm):
    """Form para Categoria de Produto"""
    class Meta:
        model = CategoriaProduto  # ✅ ATUALIZADO
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['descricao'].required = False
        self.fields['ativo'].required = False


class ProdutoForm(BaseForm):
    preco_custo = MoneyField()
    preco_venda = MoneyField()
    
    class Meta:
        model = Produto
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['codigo'].required = False
        self.fields['categoria'].required = False
        self.fields['fornecedor'].required = False
        self.fields['unidade'].required = False
        self.fields['estoque_atual'].required = False
        self.fields['estoque_minimo'].required = False
        self.fields['observacoes'].required = False
        self.fields['ativo'].required = False


# =============================================================================
# MÓDULO: CADASTRO - CONDIÇÕES DE PAGAMENTO
# =============================================================================
# CondicaoPagamento

class CondicaoPagamentoForm(BaseForm):
    class Meta:
        model = CondicaoPagamento
        fields = ['descricao', 'parcelas', 'periodicidade', 'dias_primeira_parcela', 'ativo']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['descricao'].widget.attrs.update({'placeholder': 'Ex: 30/60/90 dias'})
        self.fields['parcelas'].widget.attrs.update({'min': '1', 'max': '24'})
        self.fields['dias_primeira_parcela'].widget.attrs.update({'min': '0'})
    
    def clean_parcelas(self):
        parcelas = self.cleaned_data.get('parcelas')
        if parcelas < 1:
            raise forms.ValidationError('Mínimo 1 parcela')
        if parcelas > 24:
            raise forms.ValidationError('Máximo 24 parcelas')
        return parcelas
# =============================================================================
# MÓDULO: CADASTRO - FORMAS DE PAGAMENTO
# =============================================================================
# FormaPagamento

class FormaPagamentoForm(BaseForm):
    class Meta:
        model = FormaPagamento
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['descricao'].required = True
        self.fields['tipo'].required = True
        self.fields['ativo'].required = False

# =============================================================================
# MÓDULO: COMPRAS - PEDIDO DE COMPRA
# =============================================================================
# PedidoCompra, ItemPedidoCompra

class PedidoCompraForm(BaseForm):
    valor_total = MoneyField(required=False)
    
    class Meta:
        model = PedidoCompra
        fields = ['fornecedor', 'data_prevista_entrega', 'status', 'observacoes', 'ativo']
        widgets = {
            'fornecedor': forms.Select(attrs={'class': 'erp-select'}),
            'data_prevista_entrega': forms.DateInput(attrs={'type': 'date', 'class': 'erp-input'}),
            'status': forms.Select(attrs={'class': 'erp-select'}),
            'observacoes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Informações adicionais...', 'class': 'erp-textarea'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fornecedor'].queryset = Fornecedor.objects.filter(ativo=True).order_by('nome_razao_social')
        self.fields['fornecedor'].empty_label = "Selecione um fornecedor..."
        self.fields['observacoes'].required = False


class ItemPedidoCompraForm(BaseForm):
    preco_unitario = MoneyField()
    subtotal = MoneyField(required=False)
    
    class Meta:
        model = ItemPedidoCompra
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['produto'].queryset = Produto.objects.filter(ativo=True).order_by('descricao')
        self.fields['produto'].empty_label = "Selecione um produto..."

# =============================================================================
# MÓDULO: COMPRAS - NOTA FISCAL DE ENTRADA
# =============================================================================
# NotaFiscalEntrada, ItemNotaFiscalEntrada

class NotaFiscalEntradaForm(BaseForm):
    valor_total = MoneyField(required=False)
    
    class Meta:
        model = NotaFiscalEntrada
        fields = '__all__'
        widgets = {
            'data_entrada': forms.DateInput(attrs={'type': 'date'}),
            'data_emissao': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fornecedor'].queryset = Fornecedor.objects.filter(ativo=True).order_by('nome_razao_social')
        self.fields['fornecedor'].empty_label = "Selecione um fornecedor..."
        
        self.fields['pedido_origem'].queryset = PedidoCompra.objects.filter(
            status__in=['aprovado', 'parcial']
        ).order_by('-data_pedido')
        self.fields['pedido_origem'].empty_label = "Nenhum (opcional)"
        self.fields['pedido_origem'].required = False
        
        self.fields['observacoes'].required = False


class ItemNotaFiscalEntradaForm(BaseForm):
    valor_unitario = MoneyField()
    valor_total = MoneyField(required=False)
    
    class Meta:
        model = ItemNotaFiscalEntrada
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['produto'].queryset = Produto.objects.filter(ativo=True).order_by('descricao')
        self.fields['produto'].empty_label = "Selecione um produto..."

# =============================================================================
# MÓDULO: VENDAS - ORÇAMENTO
# =============================================================================
# Orcamento, ItemOrcamento

class OrcamentoForm(BaseForm):
    valor_total = MoneyField(required=False)
    
    class Meta:
        model = Orcamento
        fields = '__all__'
        widgets = {'data_validade': forms.DateInput(attrs={'type': 'date'})}


class ItemOrcamentoForm(BaseForm):
    preco_unitario = MoneyField()
    subtotal = MoneyField(required=False)
    
    class Meta:
        model = ItemOrcamento
        fields = '__all__'

# =============================================================================
# MÓDULO: VENDAS - PEDIDO DE VENDA
# =============================================================================
# PedidoVenda, ItemPedidoVenda

class PedidoVendaForm(BaseForm):
    valor_total = MoneyField(required=False)
    
    class Meta:
        model = PedidoVenda
        fields = '__all__'


class ItemPedidoVendaForm(BaseForm):
    preco_unitario = MoneyField()
    subtotal = MoneyField(required=False)
    
    class Meta:
        model = ItemPedidoVenda
        fields = '__all__'

# =============================================================================
# MÓDULO: VENDAS - NOTA FISCAL DE SAÍDA
# =============================================================================
# NotaFiscalSaida, ItemNotaFiscalSaida

class NotaFiscalSaidaForm(BaseForm):
    valor_total = MoneyField(required=False)
    
    class Meta:
        model = NotaFiscalSaida
        fields = '__all__'
        widgets = {'data_emissao': forms.DateInput(attrs={'type': 'date'})}


class ItemNotaFiscalSaidaForm(BaseForm):
    valor_unitario = MoneyField()
    valor_total = MoneyField(required=False)
    
    class Meta:
        model = ItemNotaFiscalSaida
        fields = '__all__'

# =============================================================================
# MÓDULO: FINANCEIRO - CONTAS A PAGAR
# =============================================================================
# ContaPagar

class ContaPagarForm(BaseForm):
    valor_original = MoneyField()
    valor_pago = MoneyField(required=False)
    
    class Meta:
        model = ContaPagar
        fields = '__all__'
        widgets = {'data_vencimento': forms.DateInput(attrs={'type': 'date'})}

# =============================================================================
# MÓDULO: FINANCEIRO - CONTAS A RECEBER
# =============================================================================
# ContaReceber

class ContaReceberForm(BaseForm):
    valor_original = MoneyField()
    valor_pago = MoneyField(required=False)
    
    class Meta:
        model = ContaReceber
        fields = '__all__'
        widgets = {'data_vencimento': forms.DateInput(attrs={'type': 'date'})}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from ERP_ServicesBI.models import Cliente, CategoriaFinanceira
        self.fields['cliente'].queryset = Cliente.objects.all()
        self.fields['categoria'].queryset = CategoriaFinanceira.objects.filter(tipo='receita')

# =============================================================================
# MÓDULO: FINANCEIRO - CATEGORIA FINANCEIRA
# =============================================================================
# CategoriaFinanceira

class CategoriaFinanceiraForm(BaseForm):
    class Meta:
        model = CategoriaFinanceira
        fields = '__all__'

# =============================================================================
# MÓDULO: FINANCEIRO - CENTRO DE CUSTO
# =============================================================================
# CentroCusto

class CentroCustoForm(BaseForm):
    class Meta:
        model = CentroCusto
        fields = '__all__'

# =============================================================================
# MÓDULO: FINANCEIRO - ORÇAMENTO FINANCEIRO
# =============================================================================
# OrcamentoFinanceiro

class OrcamentoFinanceiroForm(BaseForm):
    valor_orcado = MoneyField()
    valor_realizado = MoneyField(required=False)
    
    class Meta:
        model = OrcamentoFinanceiro
        fields = '__all__'

# =============================================================================
# MÓDULO: FINANCEIRO - EXTRATO BANCÁRIO
# =============================================================================
# ExtratoBancario, LancamentoExtrato

class ExtratoBancarioForm(BaseForm):
    class Meta:
        model = ExtratoBancario
        fields = '__all__'


class LancamentoExtratoForm(BaseForm):
    valor = MoneyField()
    
    class Meta:
        model = LancamentoExtrato
        fields = '__all__'

# =============================================================================
# MÓDULO: FINANCEIRO - FLUXO DE CAIXA
# =============================================================================
# MovimentoCaixa

class MovimentoCaixaForm(BaseForm):
    valor = MoneyField()
    
    class Meta:
        model = MovimentoCaixa
        fields = '__all__'

# =============================================================================
# MÓDULO: FINANCEIRO - DRE
# =============================================================================
# ConfiguracaoDRE, LinhaDRE, RelatorioDRE

class ConfiguracaoDREForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoDRE
        fields = [
            'empresa',
            'regime_tributario',
            'atividade_principal',
            'aliquota_simples',
            'percentual_presuncao_comercio',
            'percentual_presuncao_servico',
            'aliquota_irpj',
            'aliquota_irpj_adicional',
            'aliquota_csll',
            'ativo',
        ]
        widgets = {
            'empresa': forms.Select(attrs={'class': 'form-control'}),
            'regime_tributario': forms.Select(attrs={'class': 'form-control'}),
            'atividade_principal': forms.Select(attrs={'class': 'form-control'}),
            'aliquota_simples': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'percentual_presuncao_comercio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'percentual_presuncao_servico': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'aliquota_irpj': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'aliquota_irpj_adicional': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'aliquota_csll': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class LinhaDREForm(forms.ModelForm):
    class Meta:
        model = LinhaDRE
        fields = [
            'codigo',
            'descricao',
            'tipo',
            'natureza',
            'grupos_dre',
            'formula',
            'ordem',
            'nivel',
            'negrito',
            'visivel',
            'regime_especifico',
            'ativo',
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 1.0, 2.1'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'natureza': forms.Select(attrs={'class': 'form-control'}),
            'grupos_dre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: receita_bruta,outras_receitas'
            }),
            'formula': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 1.0-2.0 ou 3.0+4.0'
            }),
            'ordem': forms.NumberInput(attrs={'class': 'form-control'}),
            'nivel': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 3}),
            'negrito': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'visivel': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'regime_especifico': forms.Select(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class FiltroDREForm(forms.Form):
    empresa = forms.ModelChoiceField(
        queryset=None,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Empresa'
    )
    data_inicio = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Data Início'
    )
    data_fim = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Data Fim'
    )
    regime = forms.ChoiceField(
        choices=[
            ('', 'Usar configuração da empresa'),
            ('simples', 'Simples Nacional'),
            ('presumido', 'Lucro Presumido'),
            ('real', 'Lucro Real'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Regime Tributário'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Empresa
        self.fields['empresa'].queryset = Empresa.objects.filter(ativo=True)

# =============================================================================
# MÓDULO: ESTOQUE - MOVIMENTAÇÃO
# =============================================================================
# MovimentacaoEstoque

class MovimentacaoEstoqueForm(forms.ModelForm):
    produto = forms.ModelChoiceField(
        queryset=Produto.objects.filter(ativo=True).order_by('descricao'),
        empty_label="Selecione um produto...",
        required=True,
        widget=forms.Select(attrs={'class': 'erp-select'})
    )
    
    tipo = forms.ChoiceField(
        choices=[('', 'Selecione o tipo...')] + list(MovimentacaoEstoque.TIPO_CHOICES),
        required=True,
        widget=forms.Select(attrs={'class': 'erp-select'})
    )
    
    quantidade = forms.DecimalField(
        required=True,
        widget=forms.NumberInput(attrs={'class': 'erp-input', 'step': '0.001'})
    )
    
    observacoes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'erp-textarea', 'rows': 3})
    )
    
    class Meta:
        model = MovimentacaoEstoque
        exclude = ['data', 'usuario', 'nota_fiscal_entrada', 'nota_fiscal_saida', 'transferencia']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['produto'].queryset = Produto.objects.filter(ativo=True).order_by('descricao')

# =============================================================================
# MÓDULO: ESTOQUE - INVENTÁRIO
# =============================================================================
# Inventario, ItemInventario

class InventarioForm(BaseForm):
    class Meta:
        model = Inventario
        fields = '__all__'
        widgets = {'data': forms.DateInput(attrs={'type': 'date'})}


class ItemInventarioForm(BaseForm):
    class Meta:
        model = ItemInventario
        fields = '__all__'

# =============================================================================
# MÓDULO: ESTOQUE - TRANSFERÊNCIA
# =============================================================================
# TransferenciaEstoque, ItemTransferencia

class TransferenciaEstoqueForm(BaseForm):
    class Meta:
        model = TransferenciaEstoque
        fields = '__all__'


class ItemTransferenciaForm(BaseForm):
    class Meta:
        model = ItemTransferencia
        fields = '__all__'

# =============================================================================
# MÓDULO: COTAÇÃO COMPARATIVA
# =============================================================================
# CotacaoMae, ItemSolicitado, CotacaoFornecedor, ItemCotacaoFornecedor

class CotacaoMaeForm(BaseForm):
    class Meta:
        model = CotacaoMae
        fields = ['titulo', 'setor', 'data_limite_resposta', 'observacoes', 'status', 'ativo']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'erp-input', 'placeholder': 'Ex: Material de Escritório'}),
            'setor': forms.TextInput(attrs={'class': 'erp-input', 'placeholder': 'Ex: RH, TI, etc'}),
            'data_limite_resposta': forms.DateInput(attrs={'type': 'date', 'class': 'erp-input'}),
            'observacoes': forms.Textarea(attrs={'rows': 3, 'class': 'erp-textarea'}),
            'status': forms.Select(attrs={'class': 'erp-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data_limite_resposta'].required = False
        self.fields['observacoes'].required = False


class ItemSolicitadoForm(BaseForm):
    class Meta:
        model = ItemSolicitado
        fields = ['produto', 'descricao_manual', 'quantidade', 'unidade_medida']
        widgets = {
            'produto': forms.Select(attrs={'class': 'erp-select'}),
            'descricao_manual': forms.TextInput(attrs={'class': 'erp-input', 'placeholder': 'Se não tiver cadastrado'}),
            'quantidade': forms.NumberInput(attrs={'class': 'erp-input', 'step': '0.001'}),
            'unidade_medida': forms.TextInput(attrs={'class': 'erp-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['produto'].queryset = Produto.objects.filter(ativo=True).order_by('descricao')
        self.fields['produto'].empty_label = "Selecione ou digite abaixo..."
        self.fields['produto'].required = False
        self.fields['descricao_manual'].required = False


ItemSolicitadoFormSet = forms.inlineformset_factory(
    CotacaoMae,
    ItemSolicitado,
    form=ItemSolicitadoForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class CotacaoFornecedorForm(BaseForm):
    valor_total_bruto = MoneyField()
    percentual_desconto = forms.DecimalField(max_digits=5, decimal_places=2, required=False)
    valor_frete = MoneyField()
    valor_total_liquido = MoneyField(required=False)
    
    class Meta:
        model = CotacaoFornecedor
        fields = ['fornecedor', 'contato_nome', 'contato_email', 'contato_telefone', 
                  'valor_total_bruto', 'percentual_desconto', 'valor_frete', 
                  'condicao_pagamento', 'prazo_entrega_dias', 'disponibilidade_produtos', 
                  'status', 'observacoes']
        widgets = {
            'fornecedor': forms.Select(attrs={'class': 'erp-select'}),
            'status': forms.Select(attrs={'class': 'erp-select'}),
            'observacoes': forms.Textarea(attrs={'rows': 3, 'class': 'erp-textarea'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fornecedor'].queryset = Fornecedor.objects.filter(ativo=True).order_by('nome_fantasia')
        self.fields['contato_email'].required = False
        self.fields['contato_telefone'].required = False
        self.fields['observacoes'].required = False
        self.fields['condicao_pagamento'].required = False


class ItemCotacaoFornecedorForm(BaseForm):
    preco_unitario = MoneyField()
    preco_total = MoneyField(required=False)
    
    class Meta:
        model = ItemCotacaoFornecedor
        fields = ['item_solicitado', 'descricao_fornecedor', 'codigo_fornecedor', 
                  'quantidade', 'unidade_medida', 'preco_unitario', 'disponivel', 
                  'prazo_entrega_item', 'observacao']
        widgets = {
            'item_solicitado': forms.Select(attrs={'class': 'erp-select'}),
            'observacao': forms.Textarea(attrs={'rows': 2, 'class': 'erp-textarea'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['item_solicitado'].required = False
        self.fields['codigo_fornecedor'].required = False
        self.fields['unidade_medida'].required = False
        self.fields['prazo_entrega_item'].required = False
        self.fields['observacao'].required = False


ItemCotacaoFornecedorFormSet = forms.inlineformset_factory(
    CotacaoFornecedor,
    ItemCotacaoFornecedor,
    form=ItemCotacaoFornecedorForm,
    extra=0,
    can_delete=True,
)