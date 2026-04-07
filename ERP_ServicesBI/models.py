from django.db import models, transaction
from django.db.models import Sum, Count, Q, F
from django.contrib.auth.models import User, Group
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.apps import apps
from datetime import timedelta
from django.db.models import Max
from decimal import Decimal

# =============================================================================
# GERENCIADOR DE SEQUENCIAIS - THREAD SAFE
# =============================================================================

class SequencialManager:
    """
    Gerenciador thread-safe de sequenciais numéricos usando PostgreSQL
    """
    @staticmethod
    @transaction.atomic
    def proximo_numero(model, campo_prefixo='numero', prefixo='', padding=5):
        """
        Gera próximo número sequencial com lock no banco de dados
        """
        ultimo = model.objects.select_for_update().order_by('-id').first()

        if ultimo and getattr(ultimo, campo_prefixo, None):
            ultimo_numero = getattr(ultimo, campo_prefixo).replace(prefixo, '')
            try:
                novo_id = int(ultimo_numero) + 1
            except ValueError:
                novo_id = 1
        else:
            novo_id = 1

        return f"{prefixo}{novo_id:0{padding}d}"

class SequencialMixin(models.Model):
    """
    Mixin que garante geração thread-safe de códigos sequenciais
    """
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.pk:
            campo_numero = getattr(self, 'CAMPO_NUMERO', 'numero')
            prefixo = getattr(self, 'PREFIXO_NUMERO', '')
            padding = getattr(self, 'PADDING_NUMERO', 5)

            if not getattr(self, campo_numero):
                setattr(self, campo_numero, SequencialManager.proximo_numero(
                    self.__class__, 
                    campo_numero,
                    prefixo,
                    padding
                ))

        super().save(*args, **kwargs)

# =============================================================================
# MÓDULO: CADASTRO - CLIENTES
# =============================================================================

class Pessoa(models.Model):
    """
    Modelo abstrato base para Cliente e Fornecedor
    """
    TIPO_CHOICES = [
        ('F', 'Física'),
        ('J', 'Jurídica'),
    ]

    nome_razao_social = models.CharField(max_length=255, blank=True, null=True)
    tipo_pessoa = models.CharField(max_length=1, choices=TIPO_CHOICES, default='J')
    cpf_cnpj = models.CharField(max_length=20, unique=True)
    rg_inscricao_estadual = models.CharField(max_length=20, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    cep = models.CharField(max_length=10, blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True, null=True)
    numero = models.CharField(max_length=10, blank=True, null=True)
    bairro = models.CharField(max_length=100, blank=True, null=True)
    cidade = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=2, blank=True, null=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.nome_razao_social or "Sem nome"

    @property
    def nome(self):
        return self.nome_razao_social or ""

class Cliente(Pessoa):
    """Cadastro de clientes do sistema"""
    nome_fantasia = models.CharField(max_length=255, blank=True, null=True)
    limite_credito = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    observacoes = models.TextField(blank=True, null=True)

    condicao_pagamento_padrao = models.ForeignKey(
        'CondicaoPagamento',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Condição de Pagamento Padrão',
        related_name='clientes_condicao'
    )
    forma_pagamento_padrao = models.ForeignKey(
        'FormaPagamento',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Forma de Pagamento Padrão',
        related_name='clientes_forma'
    )

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['nome_razao_social']

# =============================================================================
# MÓDULO: CONFIGURAÇÕES - VENDEDOR
# =============================================================================

class Vendedor(models.Model):
    """Cadastro de vendedores/comissionados do sistema"""

    usuario = models.OneToOneField(
        User, 
        on_delete=models.PROTECT,
        related_name='vendedor_profile',
        verbose_name='Usuário do Sistema',
        null=True,
        blank=True
    )

    foto = models.ImageField(
        upload_to='vendedores/fotos/%Y/%m/',
        verbose_name='Foto',
        null=True,
        blank=True,
        help_text='Formatos: JPG, PNG. Máx: 2MB'
    )

    nome = models.CharField(max_length=255, verbose_name='Nome Completo')
    apelido = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name='Apelido',
        help_text='Como prefere ser chamado'
    )
    cpf = models.CharField(
        max_length=11,
        blank=True,
        null=True,
        verbose_name='CPF',
        help_text='Apenas números'
    )
    email = models.EmailField(verbose_name='E-mail')
    telefone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Telefone')

    comissao_padrao = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        verbose_name='Comissão Padrão (%)',
        help_text='Percentual padrão sobre vendas'
    )

    meta_vendas = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        blank=True,
        null=True,
        verbose_name='Meta de Vendas Mensal',
        help_text='Meta em reais (opcional)'
    )

    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    observacoes = models.TextField(blank=True, verbose_name='Observações')

    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Vendedor'
        verbose_name_plural = 'Vendedores'
        ordering = ['nome']
        db_table = 'cadastro_vendedor'

    def __str__(self):
        if self.apelido:
            return f"{self.nome} ({self.apelido})"
        return self.nome

    def save(self, *args, **kwargs):
        if self.cpf:
            self.cpf = ''.join(filter(str.isdigit, self.cpf))
        if self.telefone:
            self.telefone = ''.join(filter(str.isdigit, self.telefone))
        super().save(*args, **kwargs)

    @property
    def foto_url(self):
        if self.foto and hasattr(self.foto, 'url'):
            return self.foto.url
        return None

    @property
    def total_vendas_mes(self):
        from datetime import datetime
        hoje = datetime.now()
        return self.orcamentos.filter(
            data_orcamento__month=hoje.month,
            data_orcamento__year=hoje.year,
            status__in=['aprovado', 'convertido']
        ).aggregate(total=models.Sum('valor_total'))['total'] or 0

    @property
    def comissao_a_receber(self):
        return (self.total_vendas_mes * self.comissao_padrao) / 100

    @property
    def meta_atingida(self):
        if self.meta_vendas and self.meta_vendas > 0:
            return (self.total_vendas_mes / self.meta_vendas) * 100
        return 0

# =============================================================================
# MÓDULO: CONFIGURAÇÕES - EMPRESA
# =============================================================================

class Empresa(models.Model):
    """Cadastro da empresa matriz/filial do sistema"""
    nome_fantasia = models.CharField(max_length=100)
    razao_social = models.CharField(max_length=100)
    cnpj = models.CharField(max_length=20, unique=True)
    inscricao_estadual = models.CharField(max_length=20, blank=True, null=True)
    inscricao_municipal = models.CharField(max_length=20, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    cep = models.CharField(max_length=10, blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True, null=True)
    numero = models.CharField(max_length=10, blank=True, null=True)
    bairro = models.CharField(max_length=100, blank=True, null=True)
    cidade = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=2, blank=True, null=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering = ['nome_fantasia']

    def __str__(self):
        return self.nome_fantasia

# =============================================================================
# MÓDULO: CADASTRO - FORNECEDORES
# =============================================================================

class Fornecedor(Pessoa):
    """Cadastro de fornecedores do sistema"""
    nome_fantasia = models.CharField(max_length=255, blank=True, null=True)
    limite_credito = models.DecimalField(max_digits=15, decimal_places=2, default=0, blank=True, null=True)
    observacoes = models.TextField(blank=True, null=True)

    condicao_pagamento_padrao = models.ForeignKey(
        'CondicaoPagamento',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Condição de Pagamento Padrão',
        related_name='fornecedores_condicao'
    )
    forma_pagamento_padrao = models.ForeignKey(
        'FormaPagamento',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Forma de Pagamento Padrão',
        related_name='fornecedores_forma'
    )

    class Meta:
        verbose_name = 'Fornecedor'
        verbose_name_plural = 'Fornecedores'
        ordering = ['nome_razao_social']

    @property
    def cnpj(self):
        return self.cpf_cnpj if self.tipo_pessoa == 'J' else ''

# =============================================================================
# MÓDULO: CADASTRO - PRODUTOS
# =============================================================================

class CategoriaProduto(models.Model):
    """Categorias para classificação de produtos"""
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True, null=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Categoria de Produto'
        verbose_name_plural = 'Categorias de Produtos'
        ordering = ['nome']
        db_table = 'cadastro_categoriaproduto'

    def __str__(self):
        return self.nome

class UnidadeMedida(models.Model):
    sigla = models.CharField(max_length=10, unique=True)
    nome = models.CharField(max_length=100)
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = 'unidade_medida'
        verbose_name = 'Unidade de Medida'
        verbose_name_plural = 'Unidades de Medida'

    def __str__(self):
        return f"{self.sigla} - {self.nome}"

class Produto(SequencialMixin, models.Model):
    """Cadastro de produtos/serviços do sistema"""
    UNIDADE_CHOICES = [
        ('UN', 'Unidade'),
        ('KG', 'Quilograma'),
        ('LT', 'Litro'),
        ('MT', 'Metro'),
        ('PC', 'Peça'),
    ]

    codigo = models.CharField(max_length=20, unique=True, blank=True, null=True)
    descricao = models.CharField(max_length=255)
    categoria = models.ForeignKey(
        CategoriaProduto,
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='produtos'
    )
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.SET_NULL, null=True, blank=True, related_name='produtos')
    unidade = models.CharField(max_length=2, choices=UNIDADE_CHOICES, default='UN')
    preco_custo = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    estoque_atual = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    estoque_minimo = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    observacoes = models.TextField(blank=True, null=True)
    ativo = models.BooleanField(default=True)

    CAMPO_NUMERO = 'codigo'
    PREFIXO_NUMERO = ''
    PADDING_NUMERO = 3

    class Meta:
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        ordering = ['descricao']

    def __str__(self):
        return f"{self.codigo} - {self.descricao}"

    @property
    def nome(self):
        return self.descricao

    @property
    def estoque_baixo(self):
        if self.estoque_minimo and self.estoque_minimo > 0:
            return (self.estoque_atual or 0) < self.estoque_minimo
        return False

    @property
    def status_estoque(self):
        if not self.estoque_minimo or self.estoque_minimo == 0:
            return 'sem_minimo'
        if (self.estoque_atual or 0) <= 0:
            return 'critico'
        if self.estoque_atual < self.estoque_minimo:
            return 'alerta'
        return 'ok'

    @property
    def quantidade_sugerida_compra(self):
        if self.estoque_minimo and self.estoque_minimo > 0:
            saldo = self.estoque_minimo - (self.estoque_atual or 0)
            return max(0, saldo)
        return 0

# =============================================================================
# MÓDULO: CADASTRO - CONDIÇÕES E FORMAS DE PAGAMENTO
# =============================================================================

class CondicaoPagamento(models.Model):
    """Condições de pagamento (prazos e parcelas) - COM CÁLCULO AUTOMÁTICO"""

    PERIODICIDADE_CHOICES = [
        ('diario', 'Diário'),
        ('semanal', 'Semanal'),
        ('quinzenal', 'Quinzenal'),
        ('mensal', 'Mensal'),
        ('bimestral', 'Bimestral'),
        ('trimestral', 'Trimestral'),
        ('semestral', 'Semestral'),
        ('anual', 'Anual'),
    ]

    descricao = models.CharField(max_length=100, verbose_name='Descrição')
    parcelas = models.IntegerField(default=1, verbose_name='Quantidade de Parcelas', validators=[MinValueValidator(1)])
    periodicidade = models.CharField(
        max_length=20, 
        choices=PERIODICIDADE_CHOICES, 
        default='mensal',
        verbose_name='Periodicidade'
    )
    dias_primeira_parcela = models.IntegerField(
        default=0, 
        verbose_name='Dias 1ª Parcela',
        help_text='Dias para a primeira parcela (0 = à vista)'
    )
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Condição de Pagamento'
        verbose_name_plural = 'Condições de Pagamento'
        ordering = ['descricao']

    def __str__(self):
        return self.descricao

    @property
    def dias_periodo(self):
        dias_map = {
            'diario': 1,
            'semanal': 7,
            'quinzenal': 15,
            'mensal': 30,
            'bimestral': 60,
            'trimestral': 90,
            'semestral': 180,
            'anual': 365,
        }
        return dias_map.get(self.periodicidade, 30)

    def calcular_parcelas(self, data_base=None):
        from datetime import datetime, timedelta

        if data_base is None:
            data_base = datetime.now().date()

        parcelas_calculadas = []
        dias = self.dias_primeira_parcela

        for i in range(1, self.parcelas + 1):
            data_vencimento = data_base + timedelta(days=dias)
            parcelas_calculadas.append({
                'numero': i,
                'dias': dias,
                'data_vencimento': data_vencimento,
                'valor_percentual': round(100 / self.parcelas, 2),
            })
            dias += self.dias_periodo

        return parcelas_calculadas

    @property
    def prazo_total_dias(self):
        return self.dias_primeira_parcela + (self.dias_periodo * (self.parcelas - 1))

    @property
    def resumo(self):
        return f"{self.parcelas}x {self.get_periodicidade_display()} - {self.prazo_total_dias} dias"

class FormaPagamento(models.Model):
    """Formas de pagamento (meios: PIX, Cartão, etc.)"""
    TIPO_CHOICES = [
        ('dinheiro', 'Dinheiro'),
        ('pix', 'PIX'),
        ('cartao_debito', 'Cartão de Débito'),
        ('cartao_credito', 'Cartão de Crédito'),
        ('boleto', 'Boleto'),
        ('transferencia', 'Transferência Bancária'),
        ('cheque', 'Cheque'),
        ('outro', 'Outro'),
    ]

    descricao = models.CharField(max_length=100, verbose_name='Descrição')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='outro', verbose_name='Tipo')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Forma de Pagamento'
        verbose_name_plural = 'Formas de Pagamento'
        ordering = ['descricao']

    def __str__(self):
        return self.descricao

# =============================================================================
# MÓDULO: ESTOQUE - DEPÓSITO (MOVIDO PARA ANTES DAS CLASSES QUE O REFERENCIAM)
# =============================================================================

class Deposito(models.Model):
    """Cadastro de depósitos/armazéns do sistema"""
    codigo = models.CharField(
        max_length=20, 
        unique=True, 
        null=True,
        blank=True
    )
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True, null=True)
    responsavel = models.CharField(max_length=100, blank=True, null=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Depósito'
        verbose_name_plural = 'Depósitos'
        ordering = ['nome']
        db_table = 'estoque_deposito'

    def save(self, *args, **kwargs):
        if not self.codigo:
            ultimo = Deposito.objects.order_by('-id').first()
            if ultimo:
                self.codigo = f'DEP{ultimo.id + 1:03d}'
            else:
                self.codigo = 'DEP001'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.nome}" if self.codigo else self.nome

# =============================================================================
# MÓDULO: COMPRAS - COTAÇÃO MÃE
# =============================================================================

class CotacaoMae(models.Model):
    """
    Cotação 'Mãe' - Solicitação original do setor
    """
    STATUS_CHOICES = [
        ('rascunho', 'Rascunho'),
        ('enviada', 'Enviada aos Fornecedores'),
        ('respondida', 'Cotações Recebidas'),
        ('em_analise', 'Em Análise'),
        ('concluida', 'Concluída'),
        ('cancelada', 'Cancelada'),
    ]

    numero = models.CharField(max_length=20, unique=True, verbose_name='Número')
    titulo = models.CharField(max_length=200, verbose_name='Título/Descrição')
    solicitante = models.ForeignKey(
        User, 
        on_delete=models.PROTECT,
        related_name='cotacoes_mae_solicitadas',
        verbose_name='Solicitante'
    )
    setor = models.CharField(max_length=100, verbose_name='Setor')
    data_solicitacao = models.DateField(auto_now_add=True, verbose_name='Data Solicitação')
    data_limite_resposta = models.DateField(null=True, blank=True, verbose_name='Data Limite Resposta')
    observacoes = models.TextField(blank=True, verbose_name='Observações')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='rascunho',
        verbose_name='Status'
    )
    ativo = models.BooleanField(default=True, verbose_name='Ativo')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cotação Mãe'
        verbose_name_plural = 'Cotações Mãe'
        ordering = ['-data_solicitacao']

    def __str__(self):
        return f'{self.numero} - {self.titulo}'

    def save(self, *args, **kwargs):
        if not self.numero:
            from datetime import datetime
            ano = datetime.now().year
            ultima = CotacaoMae.objects.filter(numero__startswith=f'COT-{ano}').order_by('-numero').first()
            if ultima:
                ultimo_numero = int(ultima.numero.split('-')[-1])
                self.numero = f'COT-{ano}-{ultimo_numero + 1:04d}'
            else:
                self.numero = f'COT-{ano}-0001'
        super().save(*args, **kwargs)

    @property
    def total_itens(self):
        return self.itens_solicitados.count()

    @property
    def total_fornecedores(self):
        return self.cotacoes_fornecedor.count()

    @property
    def fornecedores_respondidos(self):
        return self.cotacoes_fornecedor.exclude(status='pendente').count()

# =============================================================================
# MÓDULO: COMPRAS - ITENS SOLICITADOS
# =============================================================================

class ItemSolicitado(models.Model):
    """
    Itens que o solicitante pediu na Cotação Mãe
    """
    cotacao_mae = models.ForeignKey(
        CotacaoMae,
        on_delete=models.CASCADE,
        related_name='itens_solicitados',
        verbose_name='Cotação Mãe'
    )
    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name='Produto (se cadastrado)'
    )
    descricao_manual = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Descrição (se não cadastrado)'
    )
    quantidade = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        verbose_name='Quantidade'
    )
    unidade_medida = models.CharField(
        max_length=20,
        default='UN',
        verbose_name='Unidade de Medida'
    )
    observacao = models.TextField(blank=True, verbose_name='Observação')

    class Meta:
        verbose_name = 'Item Solicitado'
        verbose_name_plural = 'Itens Solicitados'
        ordering = ['id']

    def __str__(self):
        descricao = self.produto.descricao if self.produto else self.descricao_manual
        return f'{descricao} ({self.quantidade} {self.unidade_medida})'

    @property
    def descricao_display(self):
        return self.produto.descricao if self.produto else self.descricao_manual

    @property
    def codigo_display(self):
        return self.produto.codigo if self.produto else ''

# =============================================================================
# MÓDULO: COMPRAS - COTAÇÃO FORNECEDOR
# =============================================================================

class CotacaoFornecedor(models.Model):
    """
    Cotação que cada fornecedor respondeu
    """
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('importada', 'Importada'),
        ('processada', 'Processada'),
        ('aprovada', 'Aprovada'),
        ('rejeitada', 'Rejeitada'),
    ]

    cotacao_mae = models.ForeignKey(
        CotacaoMae,
        on_delete=models.CASCADE,
        related_name='cotacoes_fornecedor',
        verbose_name='Cotação Mãe'
    )
    fornecedor = models.ForeignKey(
        Fornecedor,
        on_delete=models.PROTECT,
        verbose_name='Fornecedor'
    )
    contato_nome = models.CharField(max_length=100, blank=True, default='', verbose_name='Nome do Contato')
    contato_email = models.EmailField(blank=True, verbose_name='Email do Contato')
    contato_telefone = models.CharField(max_length=20, blank=True, default='', verbose_name='Telefone')

    valor_total_bruto = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Valor Total Bruto'
    )
    percentual_desconto = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='% Desconto'
    )
    valor_frete = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Valor Frete'
    )
    valor_total_liquido = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Valor Total Líquido'
    )

    condicao_pagamento = models.CharField(max_length=100, blank=True, default='', verbose_name='Condição de Pagamento')
    forma_pagamento = models.CharField(
        max_length=100, 
        blank=True, 
        default='',
        verbose_name='Forma de Pagamento'
    )

    prazo_entrega_dias = models.IntegerField(default=0, verbose_name='Prazo Entrega (dias)')
    disponibilidade_produtos = models.CharField(
        max_length=50,
        default='100%',
        verbose_name='% Disponibilidade Produtos'
    )

    nota_confiabilidade = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1)],
        verbose_name='Nota de Confiabilidade (1-10)'
    )

    arquivo_origem = models.FileField(
        upload_to='cotacoes_fornecedor/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Arquivo Original'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pendente',
        verbose_name='Status'
    )
    observacoes = models.TextField(blank=True, verbose_name='Observações')

    data_envio = models.DateField(null=True, blank=True, verbose_name='Data Envio')
    data_recebimento = models.DateField(null=True, blank=True, verbose_name='Data Recebimento')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cotação do Fornecedor'
        verbose_name_plural = 'Cotações dos Fornecedores'
        unique_together = ['cotacao_mae', 'fornecedor']
        ordering = ['-created_at']

    def __str__(self):
        nome = self.fornecedor.nome_fantasia or self.fornecedor.nome_razao_social
        return f'{nome} - {self.cotacao_mae.numero}'

    def calcular_total(self):
        total_itens = self.itens.aggregate(total=models.Sum('preco_total'))['total'] or 0
        self.valor_total_bruto = total_itens
        desconto = self.valor_total_bruto * (self.percentual_desconto / 100)
        self.valor_total_liquido = self.valor_total_bruto - desconto + self.valor_frete
        self.save(update_fields=['valor_total_bruto', 'valor_total_liquido'])
        return self.valor_total_liquido

    @property
    def total_itens_cotados(self):
        return self.itens.count()

# =============================================================================
# MÓDULO: COMPRAS - ITENS DA COTAÇÃO DO FORNECEDOR
# =============================================================================

class ItemCotacaoFornecedor(models.Model):
    """
    Cada item que o fornecedor cotou
    """
    cotacao_fornecedor = models.ForeignKey(
        CotacaoFornecedor,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Cotação do Fornecedor'
    )
    item_solicitado = models.ForeignKey(
        ItemSolicitado,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cotacoes_recebidas',
        verbose_name='Item Solicitado (vinculado)'
    )

    descricao_fornecedor = models.CharField(max_length=255, verbose_name='Descrição no Arquivo')
    codigo_fornecedor = models.CharField(max_length=50, blank=True, default='', verbose_name='Código do Fornecedor')
    quantidade = models.DecimalField(max_digits=15, decimal_places=3, verbose_name='Quantidade')
    unidade_medida = models.CharField(max_length=20, blank=True, default='', verbose_name='Unidade')
    preco_unitario = models.DecimalField(max_digits=15, decimal_places=4, verbose_name='Preço Unitário')
    preco_total = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Preço Total')

    disponivel = models.BooleanField(default=True, verbose_name='Disponível')
    prazo_entrega_item = models.IntegerField(null=True, blank=True, verbose_name='Prazo Específico (dias)')
    observacao = models.TextField(blank=True, verbose_name='Observação')

    match_automatico = models.BooleanField(default=False, verbose_name='Match Automático')
    match_score = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Score de Match')

    melhor_preco = models.BooleanField(default=False, verbose_name='Melhor Preço')
    melhor_prazo = models.BooleanField(default=False, verbose_name='Melhor Prazo')
    sugerido = models.BooleanField(default=False, verbose_name='Sugerido pelo Sistema')
    selecionado = models.BooleanField(default=False, verbose_name='Selecionado para Compra')

    pedido_compra = models.ForeignKey(
        'PedidoCompra',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='itens_cotacao_origem',
        verbose_name='Pedido de Compra Gerado'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Item da Cotação do Fornecedor'
        verbose_name_plural = 'Itens das Cotações dos Fornecedores'
        ordering = ['id']

    def __str__(self):
        return f'{self.descricao_fornecedor} - R$ {self.preco_unitario}'

    def save(self, *args, **kwargs):
        if self.preco_unitario and self.quantidade:
            self.preco_total = self.preco_unitario * self.quantidade
        super().save(*args, **kwargs)

# =============================================================================
# MÓDULO: COMPRAS - REGRA DE APROVAÇÃO
# =============================================================================

class RegraAprovacao(models.Model):
    """
    Configuração de alçadas de aprovação para pedidos de compra.
    """
    nome = models.CharField(max_length=100, verbose_name='Nome da Regra')
    valor_minimo = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        verbose_name='Valor Mínimo (R$)'
    )
    valor_maximo = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        verbose_name='Valor Máximo (R$)'
    )
    nivel = models.IntegerField(
        verbose_name='Nível de Aprovação',
        help_text='1=Primeiro nível, 2=Segundo, etc.'
    )
    grupo_aprovador = models.ForeignKey(
        Group, 
        on_delete=models.PROTECT,
        verbose_name='Grupo Aprovador',
        related_name='regras_aprovacao'
    )
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Regra de Aprovação'
        verbose_name_plural = 'Regras de Aprovação'
        ordering = ['nivel', 'valor_maximo']
        unique_together = ['nivel', 'grupo_aprovador']

    def __str__(self):
        return f"{self.nome} (Nível {self.nivel}: R$ {self.valor_minimo} - R$ {self.valor_maximo})"

# =============================================================================
# MÓDULO: COMPRAS - PEDIDO DE COMPRA
# =============================================================================

class PedidoCompra(SequencialMixin, models.Model):
    """
    Pedido de Compra completo com workflow de aprovação e integrações.
    """
    STATUS_CHOICES = [
        ('rascunho', 'Rascunho'),
        ('em_aprovacao', 'Em Aprovação'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
        ('pendente_entrega', 'Pendente de Entrega'),
        ('parcial', 'Entrega Parcial'),
        ('recebido', 'Recebido'),
        ('cancelado', 'Cancelado'),
    ]

    numero = models.CharField(max_length=20, unique=True, blank=True)
    fornecedor = models.ForeignKey(
        Fornecedor, 
        on_delete=models.PROTECT, 
        related_name='pedidos_compra'
    )

    cotacao_mae = models.ForeignKey(
        CotacaoMae,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pedidos_gerados',
        verbose_name='Cotação de Origem'
    )
    cotacao_fornecedor = models.ForeignKey(
        CotacaoFornecedor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pedidos_gerados',
        verbose_name='Cotação do Fornecedor'
    )

    data_pedido = models.DateField(auto_now_add=True)
    data_prevista_entrega = models.DateField(null=True, blank=True)
    data_aprovacao = models.DateTimeField(null=True, blank=True)
    data_recebimento = models.DateTimeField(null=True, blank=True)
    data_cancelamento = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='rascunho',
        verbose_name='Status'
    )

    nivel_aprovacao_necessario = models.IntegerField(
        default=0,
        verbose_name='Nível de Aprovação Necessário',
        help_text='0 = Não precisa de aprovação'
    )
    nivel_aprovacao_atual = models.IntegerField(
        default=0,
        verbose_name='Nível de Aprovação Atual'
    )

    solicitante = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='pedidos_solicitados',
        verbose_name='Solicitante'
    )
    aprovador_atual = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pedidos_para_aprovar',
        verbose_name='Aprovador Atual'
    )
    usuario_aprovacao = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pedidos_aprovados',
        verbose_name='Usuário que Aprovou'
    )
    usuario_recebimento = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pedidos_recebidos',
        verbose_name='Usuário que Recebeu'
    )
    usuario_cancelamento = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pedidos_cancelados',
        verbose_name='Usuário que Cancelou'
    )

    valor_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    valor_frete = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    percentual_desconto = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    valor_desconto = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    valor_liquido = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    condicao_pagamento = models.CharField(max_length=100, blank=True, default='', verbose_name='Condição de Pagamento')
    forma_pagamento = models.CharField(max_length=100, blank=True, default='', verbose_name='Forma de Pagamento')
    prazo_entrega_dias = models.IntegerField(default=0, verbose_name='Prazo de Entrega (dias)')

    motivo_rejeicao = models.TextField(blank=True, verbose_name='Motivo da Rejeição')
    observacao_recebimento = models.TextField(blank=True, verbose_name='Observações do Recebimento')
    observacoes = models.TextField(blank=True, verbose_name='Observações Gerais')

    conta_pagar_gerada = models.BooleanField(default=False, verbose_name='Conta a Pagar Gerada?')
    movimento_estoque_gerado = models.BooleanField(default=False, verbose_name='Movimento de Estoque Gerado?')
    nota_fiscal_vinculada = models.BooleanField(default=False, verbose_name='Nota Fiscal Vinculada?')

    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    CAMPO_NUMERO = 'numero'
    PREFIXO_NUMERO = 'PC-'
    PADDING_NUMERO = 5

    class Meta:
        verbose_name = 'Pedido de Compra'
        verbose_name_plural = 'Pedidos de Compra'
        ordering = ['-data_pedido']
        permissions = [
            ('pode_aprovar_pedido_nivel_1', 'Pode aprovar pedidos nível 1'),
            ('pode_aprovar_pedido_nivel_2', 'Pode aprovar pedidos nível 2'),
            ('pode_aprovar_pedido_nivel_3', 'Pode aprovar pedidos nível 3'),
            ('pode_receber_pedido', 'Pode receber pedidos'),
            ('pode_cancelar_pedido', 'Pode cancelar pedidos'),
        ]

    def __str__(self):
        return f"PC-{self.numero} - {self.fornecedor.nome_razao_social[:30]}"

    def save(self, *args, **kwargs):
        self.valor_desconto = (self.valor_total * self.percentual_desconto) / 100
        self.valor_liquido = self.valor_total - self.valor_desconto + self.valor_frete
        super().save(*args, **kwargs)

    def verificar_aprovacao_necessaria(self):
        if self.status != 'rascunho':
            return False

        regras = RegraAprovacao.objects.filter(
            ativo=True,
            valor_minimo__lte=self.valor_total,
            valor_maximo__gte=self.valor_total
        ).order_by('nivel')

        if regras.exists():
            maior_regra = regras.last()
            self.nivel_aprovacao_necessario = maior_regra.nivel
            self.status = 'em_aprovacao'
            self.nivel_aprovacao_atual = 0
            return True
        else:
            self.nivel_aprovacao_necessario = 0
            self.status = 'aprovado'
            self.data_aprovacao = timezone.now()
            return False

    def pode_ser_aprovado_por(self, usuario):
        if self.status != 'em_aprovacao':
            return False

        proximo_nivel = self.nivel_aprovacao_atual + 1
        grupo_nome = f'aprovador_nivel_{proximo_nivel}'
        return usuario.groups.filter(name=grupo_nome).exists()

    def aprovar(self, usuario, observacao=''):
        if not self.pode_ser_aprovado_por(usuario):
            raise PermissionError("Usuário não tem permissão para aprovar este pedido.")

        proximo_nivel = self.nivel_aprovacao_atual + 1

        PedidoAprovacao.objects.create(
            pedido=self,
            usuario=usuario,
            acao='aprovou',
            nivel=proximo_nivel,
            observacao=observacao
        )

        self.nivel_aprovacao_atual = proximo_nivel

        if self.nivel_aprovacao_atual >= self.nivel_aprovacao_necessario:
            self.status = 'aprovado'
            self.data_aprovacao = timezone.now()
            self.aprovador_atual = None
            self.usuario_aprovacao = usuario
        else:
            self.aprovador_atual = None

        self.save()

    def rejeitar(self, usuario, motivo):
        if self.status != 'em_aprovacao':
            raise ValueError("Apenas pedidos em aprovação podem ser rejeitados.")

        PedidoAprovacao.objects.create(
            pedido=self,
            usuario=usuario,
            acao='rejeitou',
            nivel=self.nivel_aprovacao_atual + 1,
            observacao=motivo
        )

        self.status = 'rejeitado'
        self.motivo_rejeicao = motivo
        self.aprovador_atual = None
        self.save()

    def cancelar(self, usuario, motivo=''):
        if self.status in ['recebido', 'cancelado']:
            raise ValueError("Pedido já recebido ou cancelado não pode ser cancelado.")

        self.status = 'cancelado'
        self.data_cancelamento = timezone.now()
        self.usuario_cancelamento = usuario
        if motivo:
            self.observacoes = f"{self.observacoes}\nCancelado: {motivo}"
        self.save()

    def calcular_total(self):
        total = self.itens.aggregate(
            total=Sum('preco_total')
        )['total'] or 0

        self.valor_total = total
        self.save(update_fields=['valor_total', 'valor_liquido', 'valor_desconto'])

    def percentual_recebido(self):
        total_itens = self.itens.count()
        if total_itens == 0:
            return 0

        itens_completos = self.itens.filter(
            quantidade_recebida__gte=F('quantidade')
        ).count()

        return (itens_completos / total_itens) * 100

    @property
    def status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

# =============================================================================
# MÓDULO: COMPRAS - HISTÓRICO DE APROVAÇÃO
# =============================================================================

class PedidoAprovacao(models.Model):
    """
    Histórico de aprovações, rejeições e encaminhamentos do pedido.
    """
    ACAO_CHOICES = [
        ('aprovou', 'Aprovou'),
        ('rejeitou', 'Rejeitou'),
        ('encaminhou', 'Encaminhou'),
    ]

    pedido = models.ForeignKey(
        PedidoCompra,
        on_delete=models.CASCADE,
        related_name='historico_aprovacoes',
        verbose_name='Pedido'
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Usuário'
    )
    acao = models.CharField(
        max_length=20,
        choices=ACAO_CHOICES,
        verbose_name='Ação'
    )
    nivel = models.IntegerField(
        verbose_name='Nível da Ação',
        help_text='Nível de aprovação em que a ação foi tomada'
    )
    data = models.DateTimeField(auto_now_add=True, verbose_name='Data')
    observacao = models.TextField(blank=True, verbose_name='Observação')

    class Meta:
        verbose_name = 'Histórico de Aprovação'
        verbose_name_plural = 'Históricos de Aprovação'
        ordering = ['-data']

    def __str__(self):
        return f"{self.get_acao_display()} - {self.pedido.numero} (Nível {self.nivel})"

# =============================================================================
# MÓDULO: COMPRAS - ITENS DO PEDIDO DE COMPRA
# =============================================================================

class ItemPedidoCompra(models.Model):
    """
    Item do pedido de compra com controle de recebimento (3-Way Matching).
    """
    pedido = models.ForeignKey(
        PedidoCompra,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Pedido'
    )
    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        verbose_name='Produto',
        related_name='itens_pedido'
    )

    item_cotacao_origem = models.ForeignKey(
        ItemCotacaoFornecedor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='itens_pedido_gerados',
        verbose_name='Item da Cotação Origem'
    )

    descricao = models.CharField(max_length=255, blank=True, default='', verbose_name='Descrição')
    quantidade = models.DecimalField(max_digits=10, decimal_places=3, default=1)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    preco_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    quantidade_recebida = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=0,
        verbose_name='Quantidade Recebida'
    )
    quantidade_conferida = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=0,
        verbose_name='Quantidade Conferida (Física)'
    )
    preco_unitario_recebido = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name='Preço Unitário Recebido'
    )

    divergencia_encontrada = models.BooleanField(
        default=False,
        verbose_name='Divergência Encontrada?'
    )
    TIPO_DIVERGENCIA_CHOICES = [
        ('quantidade_maior', 'Quantidade Maior que o Pedido'),
        ('quantidade_menor', 'Quantidade Menor que o Pedido'),
        ('preco_diferente', 'Preço Diferente do Pedido'),
        ('qualidade', 'Problema de Qualidade'),
        ('atraso', 'Atraso na Entrega'),
        ('produto_errado', 'Produto Errado'),
        ('avaria', 'Avaria no Transporte'),
    ]
    tipo_divergencia = models.CharField(
        max_length=50,
        blank=True,
        default='',
        choices=TIPO_DIVERGENCIA_CHOICES,
        verbose_name='Tipo de Divergência'
    )
    observacao_divergencia = models.TextField(
        blank=True,
        verbose_name='Observação da Divergência'
    )

    recebido_completo = models.BooleanField(
        default=False,
        verbose_name='Recebido Completo?'
    )
    data_ultimo_recebimento = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data do Último Recebimento'
    )

    class Meta:
        verbose_name = 'Item do Pedido'
        verbose_name_plural = 'Itens do Pedido'
        ordering = ['id']

    def __str__(self):
        return f"{self.descricao[:30]} - {self.quantidade} UN"

    def save(self, *args, **kwargs):
        self.preco_total = self.quantidade * self.preco_unitario

        if not self.descricao and self.produto:
            self.descricao = self.produto.descricao

        if self.quantidade_recebida >= self.quantidade:
            self.recebido_completo = True
        else:
            self.recebido_completo = False

        super().save(*args, **kwargs)

    def saldo_receber(self):
        return self.quantidade - self.quantidade_recebida

    def verificar_divergencia(self, qtd_recebida, preco_recebido=None):
        if qtd_recebida > self.quantidade:
            return True, 'quantidade_maior'

        if qtd_recebida < self.saldo_receber():
            return True, 'quantidade_menor'

        if preco_recebido and preco_recebido != self.preco_unitario:
            return True, 'preco_diferente'

        return False, None

    def registrar_recebimento(self, quantidade, usuario, preco_recebido=None, observacao=''):
        self.quantidade_recebida += quantidade
        self.data_ultimo_recebimento = timezone.now()

        if preco_recebido:
            self.preco_unitario_recebido = preco_recebido

        tem_div, tipo_div = self.verificar_divergencia(
            self.quantidade_recebida, 
            preco_recebido
        )

        if tem_div:
            self.divergencia_encontrada = True
            self.tipo_divergencia = tipo_div
            self.observacao_divergencia = observacao

        self.save()
        self.pedido.save()

# =============================================================================
# MÓDULO: COMPRAS - NOTA FISCAL DE ENTRADA (INTEGRADA COM ESTOQUE)
# =============================================================================

class NotaFiscalEntrada(models.Model):
    """
    Nota Fiscal de Entrada (Compras) - INTEGRADA COM ESTOQUE
    """
    STATUS_CHOICES = [
        ('rascunho', 'Rascunho'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
    ]

    numero_nf = models.CharField('Número NF', max_length=20)
    serie = models.CharField('Série', max_length=10, default='1')
    fornecedor = models.ForeignKey(
        Fornecedor, 
        on_delete=models.PROTECT,
        related_name='notas_fiscais_entrada'
    )
    data_emissao = models.DateField('Data Emissão')
    data_recebimento = models.DateField('Data Recebimento', null=True, blank=True)

    deposito = models.ForeignKey(
        Deposito,
        on_delete=models.PROTECT,
        related_name='entradas_nf',
        verbose_name='Depósito Destino',
        null=True,
        blank=True
    )

    chave_acesso = models.CharField('Chave de Acesso', max_length=44, blank=True)

    valor_produtos = models.DecimalField(
        'Valor Produtos', 
        max_digits=15, 
        decimal_places=2,
        default=Decimal('0.00')
    )
    valor_frete = models.DecimalField(
        'Valor Frete', 
        max_digits=15, 
        decimal_places=2,
        default=Decimal('0.00')
    )
    valor_impostos = models.DecimalField(
        'Valor Impostos', 
        max_digits=15, 
        decimal_places=2,
        default=Decimal('0.00')
    )
    valor_total = models.DecimalField(
        'Valor Total', 
        max_digits=15, 
        decimal_places=2,
        default=Decimal('0.00')
    )

    status = models.CharField(
        'Status', 
        max_length=20, 
        choices=STATUS_CHOICES,
        default='rascunho'
    )

    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    usuario = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Nota Fiscal de Entrada'
        verbose_name_plural = 'Notas Fiscais de Entrada'
        ordering = ['-data_emissao', '-id']

    def __str__(self):
        return f'NF {self.numero_nf} - {self.fornecedor.nome_razao_social}'

    def save(self, *args, **kwargs):
        if self.pk:
            old_status = None
            try:
                old = NotaFiscalEntrada.objects.get(pk=self.pk)
                old_status = old.status
            except NotaFiscalEntrada.DoesNotExist:
                pass

            if old_status != 'confirmada' and self.status == 'confirmada':
                self._confirmar_entrada()
            elif old_status == 'confirmada' and self.status == 'cancelada':
                self._estornar_entrada()

        super().save(*args, **kwargs)

    def _confirmar_entrada(self):
        """INTEGRAÇÃO: Quando NF é confirmada, atualiza estoque automaticamente"""
        for item in self.itens.all():
            if not item.produto:
                continue

            MovimentacaoEstoque.objects.create(
                produto=item.produto,
                tipo='entrada',
                quantidade=item.quantidade,
                preco_unitario=item.preco_unitario,
                valor_total=item.valor_total,
                nota_fiscal_entrada=self,
                deposito_destino=self.deposito,
                observacoes=f'Entrada via NF {self.numero_nf}',
                usuario=self.usuario,
                data=timezone.now()
            )

            produto = item.produto
            estoque_anterior = produto.estoque_atual or Decimal('0.00')
            produto.estoque_atual = estoque_anterior + item.quantidade

            if produto.estoque_atual > 0:
                custo_total_anterior = estoque_anterior * (produto.preco_custo or Decimal('0.00'))
                custo_total_novo = item.quantidade * item.preco_unitario
                novo_custo = (custo_total_anterior + custo_total_novo) / produto.estoque_atual
                produto.preco_custo = novo_custo

            produto.save(update_fields=['estoque_atual', 'preco_custo'])

    def _estornar_entrada(self):
        """INTEGRAÇÃO: Quando NF é cancelada, estorna entrada no estoque"""
        for item in self.itens.all():
            if not item.produto:
                continue

            MovimentacaoEstoque.objects.create(
                produto=item.produto,
                tipo='saida',
                quantidade=item.quantidade,
                preco_unitario=item.preco_unitario,
                valor_total=item.valor_total,
                observacoes=f'Estorno NF cancelada {self.numero_nf}',
                usuario=self.usuario,
                data=timezone.now()
            )

            produto = item.produto
            produto.estoque_atual = max(
                Decimal('0.00'), 
                (produto.estoque_atual or Decimal('0.00')) - item.quantidade
            )
            produto.save(update_fields=['estoque_atual'])

    def calcular_total(self):
        """Recalcula totais baseado nos itens"""
        total_itens = self.itens.aggregate(
            total=models.Sum('valor_total')
        )['total'] or Decimal('0.00')

        self.valor_produtos = total_itens
        self.valor_total = (
            self.valor_produtos + 
            self.valor_frete + 
            self.valor_impostos
        )

        NotaFiscalEntrada.objects.filter(pk=self.pk).update(
            valor_produtos=self.valor_produtos,
            valor_total=self.valor_total
        )


class ItemNotaFiscalEntrada(models.Model):
    """Itens da Nota Fiscal de Entrada - DEFINIÇÃO ÚNICA E COMPLETA"""
    nota_fiscal = models.ForeignKey(
        NotaFiscalEntrada,
        on_delete=models.CASCADE,
        related_name='itens'
    )
    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        related_name='entradas_nf',
        null=True,
        blank=True
    )
    quantidade = models.DecimalField(
        'Quantidade', 
        max_digits=15, 
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        default=1
    )
    preco_unitario = models.DecimalField(
        'Preço Unitário', 
        max_digits=15, 
        decimal_places=4,
        default=Decimal('0.00')
    )
    valor_total = models.DecimalField(
        'Valor Total', 
        max_digits=15, 
        decimal_places=2,
        default=Decimal('0.00')
    )

    class Meta:
        verbose_name = 'Item NF Entrada'
        verbose_name_plural = 'Itens NF Entrada'

    def save(self, *args, **kwargs):
        self.valor_total = self.quantidade * self.preco_unitario
        super().save(*args, **kwargs)
        self.nota_fiscal.calcular_total()

# =============================================================================
# MÓDULO: VENDAS - ORÇAMENTO
# =============================================================================

class Orcamento(SequencialMixin, models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('convertido', 'Convertido'),
        ('rejeitado', 'Rejeitado'),
        ('expirado', 'Expirado'),
        ('cancelado', 'Cancelado'),
    ]

    numero = models.CharField(max_length=20, unique=True, blank=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='orcamentos')
    vendedor = models.ForeignKey(Vendedor, on_delete=models.PROTECT, related_name='orcamentos', null=True, blank=True)
    data_orcamento = models.DateField(auto_now_add=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_validade = models.DateField()
    observacoes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    valor_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    CAMPO_NUMERO = 'numero'
    PREFIXO_NUMERO = 'ORC-'
    PADDING_NUMERO = 5

    class Meta:
        verbose_name = 'Orçamento'
        verbose_name_plural = 'Orçamentos'
        ordering = ['-data_orcamento']

    def __str__(self):
        return f"Orçamento {self.numero} - {self.cliente.nome_razao_social}"

    def calcular_total(self):
        total = self.itens.aggregate(total=models.Sum('preco_total'))['total'] or 0
        self.valor_total = total
        self.save(update_fields=['valor_total'])


class ItemOrcamento(models.Model):
    orcamento = models.ForeignKey(Orcamento, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    preco_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    desconto = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Item do Orçamento'
        verbose_name_plural = 'Itens do Orçamento'

    def save(self, *args, **kwargs):
        self.preco_total = (self.quantidade * self.preco_unitario) - self.desconto
        self.subtotal = self.preco_total
        super().save(*args, **kwargs)

# =============================================================================
# MÓDULO: VENDAS - PEDIDO DE VENDA
# =============================================================================

class PedidoVenda(SequencialMixin, models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('parcial', 'Parcial'),
        ('faturado', 'Faturado'),
        ('entregue', 'Entregue'),
        ('cancelado', 'Cancelado'),
    ]

    numero = models.CharField(max_length=20, unique=True, blank=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='pedidos')
    vendedor = models.ForeignKey(Vendedor, on_delete=models.PROTECT, related_name='pedidos', null=True, blank=True)
    orcamento_origem = models.ForeignKey(Orcamento, on_delete=models.SET_NULL, null=True, blank=True, related_name='pedido_gerado')
    data_pedido = models.DateField(auto_now_add=True)
    data_prevista_entrega = models.DateField()
    observacoes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    valor_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    CAMPO_NUMERO = 'numero'
    PREFIXO_NUMERO = 'PV-'
    PADDING_NUMERO = 5

    class Meta:
        verbose_name = 'Pedido de Venda'
        verbose_name_plural = 'Pedidos de Venda'
        ordering = ['-data_pedido']

    def __str__(self):
        return f"Pedido {self.numero} - {self.cliente.nome_razao_social}"

    def calcular_total(self):
        total = self.itens.aggregate(total=models.Sum('preco_total'))['total'] or 0
        self.valor_total = total
        self.save(update_fields=['valor_total'])


class ItemPedidoVenda(models.Model):
    pedido = models.ForeignKey(PedidoVenda, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    preco_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    desconto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantidade_entregue = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Item do Pedido'
        verbose_name_plural = 'Itens do Pedido'

    def save(self, *args, **kwargs):
        self.preco_total = (self.quantidade * self.preco_unitario) - self.desconto
        self.subtotal = self.preco_total
        super().save(*args, **kwargs)

# =============================================================================
# MÓDULO: VENDAS - NOTA FISCAL DE SAÍDA (INTEGRADA COM ESTOQUE)
# =============================================================================

class NotaFiscalSaida(models.Model):
    """
    Nota Fiscal de Saída (Vendas) - INTEGRADA COM ESTOQUE
    """
    STATUS_CHOICES = [
        ('rascunho', 'Rascunho'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
    ]

    numero_nf = models.CharField('Número NF', max_length=20)
    serie = models.CharField('Série', max_length=10, default='1')
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name='notas_fiscais_saida'
    )
    data_emissao = models.DateField('Data Emissão', default=timezone.now)

    deposito_origem = models.ForeignKey(
        Deposito,
        on_delete=models.PROTECT,
        related_name='saidas_nf',
        verbose_name='Depósito Origem',
        null=True,
        blank=True
    )

    valor_produtos = models.DecimalField(
        'Valor Produtos',
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    valor_frete = models.DecimalField(
        'Valor Frete',
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    valor_impostos = models.DecimalField(
        'Valor Impostos',
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    valor_total = models.DecimalField(
        'Valor Total',
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )

    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_CHOICES,
        default='rascunho'
    )

    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Nota Fiscal de Saída'
        verbose_name_plural = 'Notas Fiscais de Saída'
        ordering = ['-data_emissao', '-id']

    def __str__(self):
        return f'NF {self.numero_nf} - {self.cliente.nome_razao_social}'

    def save(self, *args, **kwargs):
        if self.pk:
            old_status = None
            try:
                old = NotaFiscalSaida.objects.get(pk=self.pk)
                old_status = old.status
            except NotaFiscalSaida.DoesNotExist:
                pass

            if old_status != 'confirmada' and self.status == 'confirmada':
                self._confirmar_saida()
            elif old_status == 'confirmada' and self.status == 'cancelada':
                self._estornar_saida()

        super().save(*args, **kwargs)

    def _confirmar_saida(self):
        """INTEGRAÇÃO: Quando NF é confirmada, baixa estoque automaticamente"""
        for item in self.itens.all():
            if not item.produto:
                continue

            produto = item.produto
            estoque_atual = produto.estoque_atual or Decimal('0.00')

            if estoque_atual < item.quantidade:
                raise ValueError(
                    f'Estoque insuficiente para "{produto.descricao}". '
                    f'Disponível: {estoque_atual} | Solicitado: {item.quantidade}'
                )

            MovimentacaoEstoque.objects.create(
                produto=item.produto,
                tipo='saida',
                quantidade=item.quantidade,
                preco_unitario=item.preco_unitario,
                valor_total=item.valor_total,
                nota_fiscal_saida=self,
                deposito_origem=self.deposito_origem,
                observacoes=f'Saída via NF {self.numero_nf}',
                usuario=self.usuario,
                data=timezone.now()
            )

            produto.estoque_atual = estoque_atual - item.quantidade
            produto.save(update_fields=['estoque_atual'])

    def _estornar_saida(self):
        """INTEGRAÇÃO: Quando NF é cancelada, devolve estoque"""
        for item in self.itens.all():
            if not item.produto:
                continue

            MovimentacaoEstoque.objects.create(
                produto=item.produto,
                tipo='entrada',
                quantidade=item.quantidade,
                preco_unitario=item.preco_unitario,
                valor_total=item.valor_total,
                observacoes=f'Estorno NF cancelada {self.numero_nf}',
                usuario=self.usuario,
                data=timezone.now()
            )

            produto = item.produto
            produto.estoque_atual = (produto.estoque_atual or Decimal('0.00')) + item.quantidade
            produto.save(update_fields=['estoque_atual'])

    def calcular_total(self):
        """Recalcula totais baseado nos itens"""
        total_itens = self.itens.aggregate(
            total=models.Sum('valor_total')
        )['total'] or Decimal('0.00')

        self.valor_produtos = total_itens
        self.valor_total = (
            self.valor_produtos +
            self.valor_frete +
            self.valor_impostos
        )

        NotaFiscalSaida.objects.filter(pk=self.pk).update(
            valor_produtos=self.valor_produtos,
            valor_total=self.valor_total
        )


class ItemNotaFiscalSaida(models.Model):
    """Itens da Nota Fiscal de Saída"""
    nota_fiscal = models.ForeignKey(
        NotaFiscalSaida,
        on_delete=models.CASCADE,
        related_name='itens'
    )
    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        related_name='saidas_nf'
    )
    quantidade = models.DecimalField(
        'Quantidade',
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        default=1
    )
    preco_unitario = models.DecimalField(
        'Preço Unitário',
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    valor_total = models.DecimalField(
        'Valor Total',
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )

    class Meta:
        verbose_name = 'Item NF Saída'
        verbose_name_plural = 'Itens NF Saída'

    def save(self, *args, **kwargs):
        self.valor_total = self.quantidade * self.preco_unitario
        super().save(*args, **kwargs)
        self.nota_fiscal.calcular_total()

# =============================================================================
# MÓDULO: FINANCEIRO - CATEGORIA FINANCEIRA
# =============================================================================

class CategoriaFinanceira(models.Model):
    TIPO_CHOICES = [
        ('receita', 'Receita'),
        ('despesa', 'Despesa'),
    ]

    GRUPO_DRE_CHOICES = [
        ('receita_bruta', 'Receita Operacional Bruta'),
        ('deducoes', 'Deduções da Receita'),
        ('outras_receitas', 'Outras Receitas Operacionais'),
        ('cmv', 'CMV - Custo das Mercadorias Vendidas'),
        ('cpv', 'CPV - Custo dos Produtos Vendidos'),
        ('csv', 'CSV - Custo dos Serviços Prestados'),
        ('despesa_vendas', 'Despesas com Vendas'),
        ('despesa_admin', 'Despesas Administrativas'),
        ('despesa_pessoal', 'Despesas com Pessoal'),
        ('depreciacao', 'Depreciação e Amortização'),
        ('outras_despesas', 'Outras Despesas Operacionais'),
        ('receita_financeira', 'Receitas Financeiras'),
        ('despesa_financeira', 'Despesas Financeiras'),
        ('impostos_lucro', 'Impostos sobre o Lucro (IR/CSLL)'),
    ]

    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    grupo_dre = models.CharField(max_length=20, choices=GRUPO_DRE_CHOICES)
    codigo = models.CharField(max_length=10, unique=True)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ['codigo']
        verbose_name = 'Categoria Financeira'
        verbose_name_plural = 'Categorias Financeiras'

    def __str__(self):
        return f"{self.codigo} - {self.nome}"

# =============================================================================
# MÓDULO: FINANCEIRO - CENTRO DE CUSTO
# =============================================================================

class CentroCusto(models.Model):
    TIPO_CHOICES = [
        ('administrativo', 'Administrativo'),
        ('vendas', 'Vendas'),
        ('producao', 'Produção'),
        ('financeiro', 'Financeiro'),
        ('rh', 'Recursos Humanos'),
        ('ti', 'Tecnologia'),
        ('servicos', 'Serviços'),
        ('outros', 'Outros'),
    ]

    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    responsavel = models.CharField(max_length=100, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Centro de Custo'
        verbose_name_plural = 'Centros de Custo'

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"

# =============================================================================
# MÓDULO: FINANCEIRO - ORÇAMENTO FINANCEIRO
# =============================================================================

class OrcamentoFinanceiro(models.Model):
    PERIODO_CHOICES = [
        ('mensal', 'Mensal'),
        ('trimestral', 'Trimestral'),
        ('anual', 'Anual'),
    ]

    categoria = models.ForeignKey(CategoriaFinanceira, on_delete=models.CASCADE)
    centro_custo = models.ForeignKey(CentroCusto, on_delete=models.SET_NULL, null=True, blank=True)
    periodo = models.CharField(max_length=10, choices=PERIODO_CHOICES, default='mensal')
    ano = models.IntegerField()
    mes = models.IntegerField(null=True, blank=True)
    trimestre = models.IntegerField(null=True, blank=True)

    valor_orcado = models.DecimalField(max_digits=15, decimal_places=2)
    valor_realizado = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    observacoes = models.TextField(blank=True)
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['categoria', 'centro_custo', 'periodo', 'ano', 'mes', 'trimestre']
        ordering = ['-ano', '-mes', 'categoria']
        verbose_name = 'Orçamento Financeiro'
        verbose_name_plural = 'Orçamentos Financeiros'

    @property
    def variacao(self):
        if self.valor_orcado == 0:
            return 0
        return ((self.valor_realizado - self.valor_orcado) / self.valor_orcado) * 100

    def __str__(self):
        periodo_str = f"{self.mes:02d}" if self.mes else (f"Q{self.trimestre}" if self.trimestre else 'Anual')
        return f"{self.categoria} - {self.ano}/{periodo_str}"

# =============================================================================
# MÓDULO: FINANCEIRO - EXTRATO BANCÁRIO
# =============================================================================

class ExtratoBancario(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('processando', 'Processando'),
        ('conciliado', 'Conciliado'),
        ('divergente', 'Divergente'),
    ]

    conta_bancaria = models.CharField(max_length=100)
    banco = models.CharField(max_length=100, blank=True)
    agencia = models.CharField(max_length=20, blank=True)
    conta = models.CharField(max_length=20, blank=True)
    descricao = models.CharField(max_length=255, blank=True)

    data_arquivo = models.DateField()
    data_inicial = models.DateField(null=True, blank=True)
    data_final = models.DateField(null=True, blank=True)
    data_upload = models.DateTimeField(auto_now_add=True)
    data_importacao = models.DateTimeField(auto_now_add=True)
    data_processamento = models.DateTimeField(null=True, blank=True)

    arquivo = models.FileField(upload_to='extratos/%Y/%m/')

    saldo_inicial = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    saldo_final = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    importado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='extratos_importados')
    processado = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')

    observacoes = models.TextField(blank=True)

    class Meta:
        ordering = ['-data_arquivo']
        verbose_name = 'Extrato Bancário'
        verbose_name_plural = 'Extratos Bancários'

    def __str__(self):
        return f"Extrato {self.conta_bancaria} - {self.data_arquivo}"

    @property
    def total_lancamentos(self):
        return self.lancamentos.count()

    def save(self, *args, **kwargs):
        self.processado = (self.status in ['conciliado', 'divergente'])
        super().save(*args, **kwargs)

# =============================================================================
# MÓDULO: FINANCEIRO - CONTA BANCÁRIA
# =============================================================================

class ContaBancaria(models.Model):
    """
    Cadastro de contas bancárias para conciliação
    """
    TIPO_CONTA_CHOICES = [
        ('corrente', 'Conta Corrente'),
        ('poupanca', 'Conta Poupança'),
        ('investimento', 'Conta Investimento'),
    ]

    nome = models.CharField(max_length=100, verbose_name='Nome da Conta')
    banco = models.CharField(max_length=100, verbose_name='Banco')
    agencia = models.CharField(max_length=20, verbose_name='Agência', blank=True, default='')
    conta = models.CharField(max_length=20, verbose_name='Número da Conta', blank=True, default='')
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CONTA_CHOICES,
        default='corrente',
        verbose_name='Tipo de Conta'
    )
    saldo_inicial = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Saldo Inicial'
    )
    saldo_atual = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Saldo Atual'
    )
    ativa = models.BooleanField(default=True, verbose_name='Ativa')
    observacoes = models.TextField(blank=True, verbose_name='Observações')

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Conta Bancária'
        verbose_name_plural = 'Contas Bancárias'
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} - {self.banco}"

    def atualizar_saldo(self):
        """Atualiza o saldo baseado nos extratos"""
        ultimo_extrato = self.extratos.filter(status='conciliado').order_by('-data_arquivo').first()
        if ultimo_extrato:
            self.saldo_atual = ultimo_extrato.saldo_final
            self.save(update_fields=['saldo_atual'])


# =============================================================================
# MÓDULO: FINANCEIRO - LANÇAMENTO DO EXTRATO
# =============================================================================

class LancamentoExtrato(models.Model):
    TIPO_CHOICES = [
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
        ('debito', 'Débito'),
        ('credito', 'Crédito'),
    ]

    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('conciliado', 'Conciliado'),
        ('ignorado', 'Ignorado'),
    ]

    extrato = models.ForeignKey(ExtratoBancario, on_delete=models.CASCADE, related_name='lancamentos')
    data = models.DateField()
    descricao = models.CharField(max_length=255)
    documento = models.CharField(max_length=50, blank=True)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    valor = models.DecimalField(max_digits=15, decimal_places=2)

    conciliado = models.BooleanField(default=False)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pendente')
    conta_pagar = models.ForeignKey('ContaPagar', on_delete=models.SET_NULL, null=True, blank=True)
    conta_receber = models.ForeignKey('ContaReceber', on_delete=models.SET_NULL, null=True, blank=True)
    movimento_caixa = models.ForeignKey('MovimentoCaixa', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['data', 'id']
        verbose_name = 'Lançamento do Extrato'
        verbose_name_plural = 'Lançamentos do Extrato'

    def __str__(self):
        return f"{self.data} - {self.descricao} - R$ {self.valor}"

    def save(self, *args, **kwargs):
        self.conciliado = (self.status == 'conciliado')
        super().save(*args, **kwargs)

# =============================================================================
# MÓDULO: FINANCEIRO - CONTAS A RECEBER
# =============================================================================

class ContaReceber(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aberto', 'Aberto'),
        ('parcial', 'Parcial'),
        ('recebido', 'Recebido'),
        ('quitado', 'Quitado'),
        ('atrasado', 'Atrasado'),
        ('cancelado', 'Cancelado'),
    ]

    descricao = models.CharField(max_length=255)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='contas_receber', null=True, blank=True)
    nota_fiscal = models.ForeignKey(NotaFiscalSaida, on_delete=models.SET_NULL, null=True, blank=True, related_name='contas_receber')

    categoria = models.ForeignKey(CategoriaFinanceira, on_delete=models.SET_NULL, 
                                   null=True, blank=True, 
                                   limit_choices_to={'tipo': 'receita'},
                                   related_name='contas_receber')
    centro_custo = models.ForeignKey(CentroCusto, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='contas_receber')

    data_emissao = models.DateField(auto_now_add=True)
    data_vencimento = models.DateField()
    data_recebimento = models.DateField(null=True, blank=True)
    data_baixa = models.DateField(null=True, blank=True)
    valor_original = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_recebido = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_saldo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    observacoes = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Conta a Receber'
        verbose_name_plural = 'Contas a Receber'
        ordering = ['data_vencimento']

    def __str__(self):
        return f"{self.descricao} - R$ {self.valor_original}"

    def save(self, *args, **kwargs):
        self.valor_saldo = self.valor_original - (self.valor_recebido or 0)
        self.valor = self.valor_original
        super().save(*args, **kwargs)

    @property
    def dias_atraso(self):
        if self.status in ['recebido', 'quitado', 'cancelado']:
            return 0
        hoje = timezone.now().date()
        if hoje > self.data_vencimento:
            return (hoje - self.data_vencimento).days
        return 0

    def baixar(self, data_baixa=None, valor_recebido=None):
        if data_baixa:
            self.data_recebimento = data_baixa
            self.data_baixa = data_baixa
        else:
            self.data_recebimento = timezone.now().date()
            self.data_baixa = timezone.now().date()

        if valor_recebido:
            self.valor_recebido = Decimal(valor_recebido)

        if self.valor_recebido >= self.valor_original:
            self.status = 'recebido'
        elif self.valor_recebido > 0:
            self.status = 'parcial'

        self.save()

# =============================================================================
# MÓDULO: FINANCEIRO - CONTAS A PAGAR
# =============================================================================

class ContaPagar(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aberto', 'Aberto'),
        ('parcial', 'Parcial'),
        ('pago', 'Pago'),
        ('quitado', 'Quitado'),
        ('atrasado', 'Atrasado'),
        ('cancelado', 'Cancelado'),
    ]

    descricao = models.CharField(max_length=255)
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.PROTECT, related_name='contas_pagar', null=True, blank=True)
    nota_fiscal = models.ForeignKey(NotaFiscalEntrada, on_delete=models.SET_NULL, null=True, blank=True, related_name='contas_pagar')

    categoria = models.ForeignKey(CategoriaFinanceira, on_delete=models.SET_NULL, 
                                   null=True, blank=True, 
                                   limit_choices_to={'tipo': 'despesa'},
                                   related_name='contas_pagar')
    centro_custo = models.ForeignKey(CentroCusto, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='contas_pagar')

    data_emissao = models.DateField(auto_now_add=True)
    data_vencimento = models.DateField()
    data_pagamento = models.DateField(null=True, blank=True)
    data_baixa = models.DateField(null=True, blank=True)
    valor_original = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_pago = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_saldo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    observacoes = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Conta a Pagar'
        verbose_name_plural = 'Contas a Pagar'
        ordering = ['data_vencimento']

    def __str__(self):
        return f"{self.descricao} - R$ {self.valor_original}"

    def save(self, *args, **kwargs):
        self.valor_saldo = self.valor_original - (self.valor_pago or 0)
        self.valor = self.valor_original
        super().save(*args, **kwargs)

    @property
    def dias_atraso(self):
        if self.status in ['pago', 'quitado', 'cancelado']:
            return 0
        hoje = timezone.now().date()
        if hoje > self.data_vencimento:
            return (hoje - self.data_vencimento).days
        return 0

    def baixar(self, data_baixa=None, valor_pago=None):
        if data_baixa:
            self.data_pagamento = data_baixa
            self.data_baixa = data_baixa
        else:
            self.data_pagamento = timezone.now().date()
            self.data_baixa = timezone.now().date()

        if valor_pago:
            self.valor_pago = Decimal(valor_pago)

        if self.valor_pago >= self.valor_original:
            self.status = 'pago'
        elif self.valor_pago > 0:
            self.status = 'parcial'

        self.save()

# =============================================================================
# MÓDULO: FLUXO DE CAIXA
# =============================================================================

class MovimentoCaixa(models.Model):
    TIPO_CHOICES = [
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
    ]

    descricao = models.CharField(max_length=255)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    data = models.DateField(auto_now_add=True)
    valor = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    conta_receber = models.ForeignKey(ContaReceber, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimentos')
    conta_pagar = models.ForeignKey(ContaPagar, on_delete=models.SET_NULL, null=True, blank=True, related_name='movimentos')
    observacoes = models.TextField(blank=True)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, related_name='movimentos_caixa')

    class Meta:
        verbose_name = 'Movimento de Caixa'
        verbose_name_plural = 'Movimentos de Caixa'
        ordering = ['-data']

    def __str__(self):
        return f"{self.descricao} - {self.tipo} - R$ {self.valor}"

# =============================================================================
# CONSTANTES DRE
# =============================================================================

REGIME_TRIBUTARIO_CHOICES = [
    ('simples', 'Simples Nacional'),
    ('simples_excesso', 'Simples Nacional - Excesso de Sublimite'),
    ('presumido', 'Lucro Presumido'),
    ('real', 'Lucro Real'),
]

ATIVIDADE_CHOICES = [
    ('comercio', 'Comércio'),
    ('servicos', 'Serviços'),
    ('industria', 'Indústria'),
    ('misto', 'Misto'),
]

TIPO_LINHA_CHOICES = [
    ('soma_categoria', 'Soma por Categoria'),
    ('subtotal', 'Subtotal (Cálculo)'),
    ('total', 'Total Final'),
    ('espacamento', 'Espaçamento'),
    ('descricao', 'Descrição Livre'),
]

NATUREZA_CHOICES = [
    ('receita', 'Receita'),
    ('despesa', 'Despesa'),
    ('resultado', 'Resultado'),
]

STATUS_DRE_CHOICES = [
    ('rascunho', 'Rascunho'),
    ('processando', 'Processando'),
    ('concluido', 'Concluído'),
    ('erro', 'Erro'),
]

# =============================================================================
# MÓDULO: DRE - CONFIGURAÇÃO
# =============================================================================

class ConfiguracaoDRE(models.Model):
    """
    Configuração da DRE por empresa - define regime tributário e parâmetros
    """
    empresa = models.OneToOneField(
        Empresa,
        on_delete=models.CASCADE,
        related_name='configuracao_dre',
        verbose_name='Empresa'
    )
    regime_tributario = models.CharField(
        max_length=15,
        choices=REGIME_TRIBUTARIO_CHOICES,
        default='simples',
        verbose_name='Regime Tributário'
    )
    atividade_principal = models.CharField(
        max_length=15,
        choices=ATIVIDADE_CHOICES,
        default='comercio',
        verbose_name='Atividade Principal'
    )

    # Parâmetros Simples Nacional
    aliquota_simples = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=6.00,
        verbose_name='Alíquota Simples (%)',
        help_text='Alíquota efetiva do Simples Nacional'
    )

    # Parâmetros Lucro Presumido
    percentual_presuncao_comercio = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=8.00,
        verbose_name='% Presunção Comércio',
        help_text='Percentual de presunção para comércio (8%)'
    )
    percentual_presuncao_servico = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=32.00,
        verbose_name='% Presunção Serviços',
        help_text='Percentual de presunção para serviços (32%)'
    )

    # Alíquotas IR/CSLL (Presumido e Real)
    aliquota_irpj = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=15.00,
        verbose_name='Alíquota IRPJ (%)'
    )
    aliquota_irpj_adicional = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        verbose_name='Alíquota IRPJ Adicional (%)',
        help_text='Adicional sobre lucro excedente a R$ 20.000/mês'
    )
    aliquota_csll = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=9.00,
        verbose_name='Alíquota CSLL (%)'
    )

    # Controle
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuração DRE'
        verbose_name_plural = 'Configurações DRE'

    def __str__(self):
        return f"Config DRE - {self.empresa.nome_fantasia} ({self.get_regime_tributario_display()})"


class LinhaDRE(models.Model):
    """
    Define a estrutura/layout de cada linha da DRE
    """
    codigo = models.CharField(
        max_length=10,
        unique=True,
        verbose_name='Código',
        help_text='Ex: 1.0, 1.1, 2.0, 3.0'
    )
    descricao = models.CharField(
        max_length=100,
        verbose_name='Descrição',
        help_text='Nome da linha na DRE'
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_LINHA_CHOICES,
        default='soma_categoria',
        verbose_name='Tipo'
    )
    natureza = models.CharField(
        max_length=10,
        choices=NATUREZA_CHOICES,
        default='despesa',
        verbose_name='Natureza'
    )

    # Vinculação com grupo_dre da CategoriaFinanceira
    grupos_dre = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Grupos DRE',
        help_text='Lista separada por vírgula dos grupo_dre a somar. Ex: receita_bruta,outras_receitas'
    )

    # Para linhas de cálculo (subtotais)
    formula = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Fórmula',
        help_text='Códigos das linhas para cálculo. Ex: 1.0-2.0 ou 3.0+4.0-5.0'
    )

    # Configuração de exibição
    ordem = models.IntegerField(
        default=0,
        verbose_name='Ordem de Exibição'
    )
    nivel = models.IntegerField(
        default=0,
        verbose_name='Nível de Indentação',
        help_text='0=Principal, 1=Subitem, 2=Detalhe'
    )
    negrito = models.BooleanField(
        default=False,
        verbose_name='Negrito',
        help_text='Destacar linha em negrito'
    )
    visivel = models.BooleanField(
        default=True,
        verbose_name='Visível',
        help_text='Exibir no relatório'
    )

    # Regime tributário (None = todos)
    regime_especifico = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        choices=REGIME_TRIBUTARIO_CHOICES,
        verbose_name='Regime Específico',
        help_text='Deixe vazio para exibir em todos os regimes'
    )

    ativo = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Linha DRE'
        verbose_name_plural = 'Linhas DRE'
        ordering = ['ordem', 'codigo']

    def __str__(self):
        return f"{self.codigo} - {self.descricao}"

    def get_grupos_lista(self):
        """Retorna lista de grupos_dre"""
        if not self.grupos_dre:
            return []
        return [g.strip() for g in self.grupos_dre.split(',')]


class RelatorioDRE(models.Model):
    """
    Relatório DRE gerado - armazena resultado para histórico/cache
    """
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='relatorios_dre',
        verbose_name='Empresa'
    )

    # Período
    data_inicio = models.DateField(verbose_name='Data Início')
    data_fim = models.DateField(verbose_name='Data Fim')

    # Regime usado no cálculo
    regime_tributario = models.CharField(
        max_length=15,
        choices=REGIME_TRIBUTARIO_CHOICES,
        verbose_name='Regime Tributário'
    )

    # Totais calculados (cache)
    receita_bruta = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    deducoes = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    receita_liquida = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    custo_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    lucro_bruto = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    despesas_operacionais = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    resultado_operacional = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    resultado_financeiro = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    resultado_antes_ir = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    impostos_lucro = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    lucro_liquido = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # JSON com todos os dados detalhados
    dados_json = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Dados Completos (JSON)'
    )

    # Controle
    status = models.CharField(
        max_length=15,
        choices=STATUS_DRE_CHOICES,
        default='rascunho',
        verbose_name='Status'
    )
    gerado_em = models.DateTimeField(auto_now_add=True, verbose_name='Gerado em')
    gerado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='relatorios_dre_gerados',
        verbose_name='Gerado por'
    )
    observacoes = models.TextField(blank=True, verbose_name='Observações')

    class Meta:
        verbose_name = 'Relatório DRE'
        verbose_name_plural = 'Relatórios DRE'
        ordering = ['-data_fim', '-gerado_em']
        unique_together = ['empresa', 'data_inicio', 'data_fim']

    def __str__(self):
        return f"DRE {self.empresa.nome_fantasia} - {self.data_inicio} a {self.data_fim}"

    @property
    def periodo_formatado(self):
        return f"{self.data_inicio.strftime('%d/%m/%Y')} a {self.data_fim.strftime('%d/%m/%Y')}"

    @property
    def margem_bruta(self):
        """Margem Bruta = Lucro Bruto / Receita Líquida * 100"""
        if self.receita_liquida == 0:
            return 0
        return (self.lucro_bruto / self.receita_liquida) * 100

    @property
    def margem_operacional(self):
        """Margem Operacional = Resultado Operacional / Receita Líquida * 100"""
        if self.receita_liquida == 0:
            return 0
        return (self.resultado_operacional / self.receita_liquida) * 100

    @property
    def margem_liquida(self):
        """Margem Líquida = Lucro Líquido / Receita Líquida * 100"""
        if self.receita_liquida == 0:
            return 0
        return (self.lucro_liquido / self.receita_liquida) * 100


class ItemRelatorioDRE(models.Model):
    """
    Cada linha do relatório DRE com seu valor calculado
    """
    relatorio = models.ForeignKey(
        RelatorioDRE,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Relatório'
    )
    linha_dre = models.ForeignKey(
        LinhaDRE,
        on_delete=models.PROTECT,
        related_name='itens_relatorio',
        verbose_name='Linha DRE'
    )

    valor = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Valor'
    )
    valor_anterior = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Valor Período Anterior',
        help_text='Para análise comparativa'
    )

    # Análise Vertical (% sobre Receita Líquida)
    percentual_vertical = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name='% Vertical'
    )

    # Análise Horizontal (variação vs período anterior)
    percentual_horizontal = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name='% Horizontal'
    )

    class Meta:
        verbose_name = 'Item do Relatório DRE'
        verbose_name_plural = 'Itens do Relatório DRE'
        ordering = ['linha_dre__ordem']
        unique_together = ['relatorio', 'linha_dre']

    def __str__(self):
        return f"{self.linha_dre.descricao}: R$ {self.valor}"

# =============================================================================
# MÓDULO: PLANEJADO X REALIZADO - PROJETO
# =============================================================================

class Projeto(models.Model):
    nome = models.CharField(max_length=200)
    codigo = models.CharField(max_length=50, unique=True, null=True, blank=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, null=True, blank=True, related_name='projetos')
    data_inicio = models.DateField(null=True, blank=True)
    data_fim = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, default='ativo')
    observacoes = models.TextField(blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Projeto'
        verbose_name_plural = 'Projetos'

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self.gerar_codigo()
        super().save(*args, **kwargs)

    def gerar_codigo(self):
        """Gera código no formato PRJ001, PRJ002..."""
        ultimo = Projeto.objects.aggregate(Max('id'))['id__max'] or 0
        return f"PRJ{ultimo + 1:03d}"

    def __str__(self):
        return f"{self.codigo} - {self.nome}" if self.codigo else self.nome


class OrcamentoProjeto(models.Model):
    """
    Orçamento/Planejamento mensal por projeto
    """
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name='orcamentos')

    ano = models.IntegerField()
    mes = models.IntegerField(choices=[(i, i) for i in range(1, 13)])

    # Campos de planejamento (orçado)
    receitas_orcadas = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    despesas_orcadas = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Campos de realizado (executado)
    realizado_receitas = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    realizado_despesas = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    observacoes = models.TextField(blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['projeto', 'ano', 'mes']
        ordering = ['projeto', 'ano', 'mes']
        verbose_name = 'Orçamento do Projeto'
        verbose_name_plural = 'Orçamentos dos Projetos'

    @property
    def valor_planejado(self):
        """Saldo planejado = receitas orçadas - despesas orçadas"""
        return self.receitas_orcadas - self.despesas_orcadas

    @property
    def valor_realizado(self):
        """Saldo realizado = receitas realizadas - despesas realizadas"""
        return self.realizado_receitas - self.realizado_despesas

    @property
    def variacao(self):
        """Variação entre realizado e planejado"""
        return self.valor_realizado - self.valor_planejado

    @property
    def variacao_percentual(self):
        if self.valor_planejado == 0:
            return 0
        return ((self.valor_realizado - self.valor_planejado) / abs(self.valor_planejado)) * 100

    @property
    def valor_projetado(self):
        """
        Projetado = Realizado (contas pagas/recebidas) + contas em aberto
        """
        from datetime import date

        # Período do mês
        data_inicio = date(self.ano, self.mes, 1)
        if self.mes == 12:
            data_fim = date(self.ano + 1, 1, 1)
        else:
            data_fim = date(self.ano, self.mes + 1, 1)

        # Contas a receber em aberto
        receber_aberto = ContaReceber.objects.filter(
            data_vencimento__gte=data_inicio,
            data_vencimento__lt=data_fim,
            status__in=['pendente', 'parcial']
        ).aggregate(total=Sum('valor_original'))['total'] or 0

        # Contas a pagar em aberto
        pagar_aberto = ContaPagar.objects.filter(
            data_vencimento__gte=data_inicio,
            data_vencimento__lt=data_fim,
            status__in=['pendente', 'parcial']
        ).aggregate(total=Sum('valor_original'))['total'] or 0

        return self.valor_realizado + (receber_aberto - pagar_aberto)

    def __str__(self):
        return f"{self.projeto} - {self.mes}/{self.ano}"

# =============================================================================
# MÓDULO: ESTOQUE - MOVIMENTAÇÃO
# =============================================================================

class MovimentacaoEstoque(models.Model):
    TIPO_CHOICES = [
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
        ('ajuste', 'Ajuste'),
        ('transferencia', 'Transferência'),
    ]

    produto = models.ForeignKey(
        Produto, 
        on_delete=models.PROTECT, 
        related_name='movimentacoes',
        null=True,
        blank=True
    )
    tipo = models.CharField(
        max_length=20, 
        choices=TIPO_CHOICES,
        default='entrada'
    )
    quantidade = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0
    )
    data = models.DateTimeField(
        default=timezone.now,
        verbose_name='Data'
    )

    preco_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Preço Unitário'
    )

    valor_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Valor Total'
    )

    nota_fiscal_entrada = models.ForeignKey(
        NotaFiscalEntrada, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='movimentacoes'
    )
    nota_fiscal_saida = models.ForeignKey(
        NotaFiscalSaida, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='movimentacoes'
    )

    deposito_origem = models.ForeignKey(
        Deposito,
        on_delete=models.PROTECT,
        related_name='movimentacoes_origem',
        null=True,
        blank=True,
        verbose_name='Depósito de Origem'
    )

    deposito_destino = models.ForeignKey(
        Deposito,
        on_delete=models.PROTECT,
        related_name='movimentacoes_destino',
        null=True,
        blank=True,
        verbose_name='Depósito de Destino'
    )

    motivo = models.CharField(
        max_length=255, 
        blank=True, 
        default=''
    )
    observacoes = models.TextField(blank=True)
    usuario = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        null=True,
        blank=True,
        related_name='movimentacoes_estoque'
    )

    class Meta:
        verbose_name = 'Movimentação de Estoque'
        verbose_name_plural = 'Movimentações de Estoque'
        ordering = ['-data']

    def __str__(self):
        produto_str = self.produto.descricao if self.produto else 'Sem produto'
        return f"{self.tipo} - {produto_str} - {self.quantidade}"

    def atualizar_estoque(self):
        if self.produto:
            if self.tipo == 'entrada':
                self.produto.estoque_atual += self.quantidade
            elif self.tipo == 'saida':
                self.produto.estoque_atual -= self.quantidade
            self.produto.save(update_fields=['estoque_atual'])

    def reverter_estoque(self):
        if self.produto:
            if self.tipo == 'entrada':
                self.produto.estoque_atual -= self.quantidade
            elif self.tipo == 'saida':
                self.produto.estoque_atual += self.quantidade
            self.produto.save(update_fields=['estoque_atual'])

    def save(self, *args, **kwargs):
        # Calcula valor_total automaticamente se preco_unitario e quantidade existirem
        if self.preco_unitario and self.quantidade:
            self.valor_total = self.preco_unitario * self.quantidade
        super().save(*args, **kwargs)

# =============================================================================
# MÓDULO: ESTOQUE - INVENTÁRIO
# =============================================================================

class Inventario(SequencialMixin, models.Model):
    STATUS_CHOICES = [
        ('aberto', 'Aberto'),
        ('em_andamento', 'Em Andamento'),
        ('concluido', 'Concluído'),
        ('cancelado', 'Cancelado'),
    ]

    numero = models.CharField(max_length=20, unique=True, blank=True)
    data = models.DateField(default=timezone.now)
    data_criacao = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='aberto'
    )

    deposito = models.ForeignKey(
        Deposito,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='inventarios',
        verbose_name='Depósito'
    )

    observacoes = models.TextField(blank=True)
    usuario = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        null=True,
        blank=True,
        related_name='inventarios'
    )

    CAMPO_NUMERO = 'numero'
    PREFIXO_NUMERO = 'INV-'
    PADDING_NUMERO = 5

    class Meta:
        verbose_name = 'Inventário'
        verbose_name_plural = 'Inventários'
        ordering = ['-data']

    def __str__(self):
        return f"Inventário {self.numero} - {self.data}"

    def gerar_itens_inventario(self):
        """
        Cria itens de inventário baseado no ESTOQUE SISTÊMICO atual.
        Versão corrigida - usa Produto diretamente (já definido acima).
        """
        if self.status != 'aberto':
            return 0

        # Busca produtos com estoque > 0
        produtos = Produto.objects.filter(
            estoque_atual__gt=0,
            ativo=True
        ).order_by('descricao')

        itens_criados = 0
        for produto in produtos:
            ItemInventario.objects.create(
                inventario=self,
                produto=produto,
                quantidade_sistema=produto.estoque_atual,
                quantidade_contada=0
            )
            itens_criados += 1

        self.status = 'em_andamento'
        self.save(update_fields=['status'])

        return itens_criados

    def finalizar(self, usuario=None):
        """
        Finaliza o inventário e aplica ajustes.
        """
        if self.status == 'concluido':
            return 0

        ajustes_aplicados = 0

        for item in self.itens.all():
            if item.diferenca != 0:
                MovimentacaoEstoque.objects.create(
                    produto=item.produto,
                    tipo='ajuste',
                    quantidade=abs(item.diferenca),
                    observacoes=f'Ajuste de inventário {self.numero}',
                    usuario=usuario,
                    data=timezone.now()
                )

                produto = item.produto
                produto.estoque_atual = item.quantidade_contada
                produto.save(update_fields=['estoque_atual'])

                ajustes_aplicados += 1

        self.status = 'concluido'
        self.save(update_fields=['status'])

        return ajustes_aplicados

    def aplicar_ajustes(self):
        """Método legado - mantido para compatibilidade"""
        return self.finalizar(usuario=self.usuario)


class ItemInventario(models.Model):
    """Itens do Inventário"""
    inventario = models.ForeignKey(
        Inventario, 
        on_delete=models.CASCADE, 
        related_name='itens'
    )
    produto = models.ForeignKey(
        Produto, 
        on_delete=models.PROTECT,
        related_name='itens_inventario'
    )
    quantidade_sistema = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name='Qtd. Sistema'
    )
    quantidade_contada = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name='Qtd. Contada'
    )
    quantidade_fisica = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name='Qtd. Física'
    )
    divergencia = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0
    )
    diferenca = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0
    )
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Item do Inventário'
        verbose_name_plural = 'Itens do Inventário'
        unique_together = ['inventario', 'produto']

    def __str__(self):
        return f'{self.produto.descricao} - Sistema: {self.quantidade_sistema}'

    @property
    def diferenca_calc(self):
        return self.quantidade_contada - self.quantidade_sistema

    def save(self, *args, **kwargs):
        self.diferenca = self.quantidade_contada - self.quantidade_sistema
        self.divergencia = self.diferenca
        self.quantidade_fisica = self.quantidade_contada
        super().save(*args, **kwargs)

# =============================================================================
# MÓDULO: ESTOQUE - TRANSFERÊNCIA
# =============================================================================

class TransferenciaEstoque(SequencialMixin, models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('concluida', 'Concluída'),
        ('efetivada', 'Efetivada'),
        ('cancelada', 'Cancelada'),
    ]

    numero = models.CharField(max_length=20, unique=True, blank=True)
    origem = models.CharField(max_length=100, default='')
    destino = models.CharField(max_length=100, default='')
    deposito_origem = models.CharField(
        max_length=100, 
        blank=True, 
        default=''
    )
    deposito_destino = models.CharField(
        max_length=100, 
        blank=True, 
        default=''
    )
    data = models.DateField(auto_now_add=True)
    data_efetivacao = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pendente'
    )
    observacoes = models.TextField(blank=True)
    usuario = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        null=True,
        blank=True,
        related_name='transferencias'
    )

    CAMPO_NUMERO = 'numero'
    PREFIXO_NUMERO = 'TRF-'
    PADDING_NUMERO = 5

    class Meta:
        verbose_name = 'Transferência de Estoque'
        verbose_name_plural = 'Transferências de Estoque'
        ordering = ['-data']

    def __str__(self):
        return f"Transferência {self.numero} - {self.origem} → {self.destino}"

    def save(self, *args, **kwargs):
        if not self.deposito_origem:
            self.deposito_origem = self.origem
        if not self.deposito_destino:
            self.deposito_destino = self.destino
        super().save(*args, **kwargs)


class ItemTransferencia(models.Model):
    transferencia = models.ForeignKey(TransferenciaEstoque, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Item da Transferência'
        verbose_name_plural = 'Itens da Transferência'

# =============================================================================
# MÓDULO: ESTOQUE - SALDO POR DEPÓSITO
# =============================================================================

class SaldoEstoque(models.Model):
    """Controle de saldo de estoque por depósito"""
    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        related_name='saldos_por_deposito'
    )
    deposito = models.ForeignKey(
        Deposito,
        on_delete=models.PROTECT,
        related_name='saldos'
    )
    quantidade = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=0,
        verbose_name='Quantidade em Estoque'
    )
    quantidade_reservada = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=0,
        verbose_name='Quantidade Reservada'
    )
    quantidade_disponivel = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=0,
        verbose_name='Quantidade Disponível'
    )
    data_ultimo_movimento = models.DateTimeField(null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Saldo de Estoque'
        verbose_name_plural = 'Saldos de Estoque'
        unique_together = ['produto', 'deposito']
        ordering = ['produto__descricao', 'deposito__nome']
        db_table = 'estoque_saldo'

    def __str__(self):
        return f"{self.produto.descricao[:30]} - {self.deposito.nome}: {self.quantidade}"

    def save(self, *args, **kwargs):
        # Calcula quantidade disponível
        self.quantidade_disponivel = self.quantidade - self.quantidade_reservada
        super().save(*args, **kwargs)

    @property
    def saldo_disponivel(self):
        return self.quantidade - self.quantidade_reservada

# =============================================================================
# MÓDULO: ESTOQUE - ENTRADA DE NF-E
# =============================================================================

class EntradaNFE(models.Model):
    """
    Registro de entrada de Nota Fiscal Eletrônica no estoque
    """
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('em_processamento', 'Em Processamento'),
        ('finalizada', 'Finalizada'),
        ('cancelada', 'Cancelada'),
    ]

    numero_nfe = models.CharField(max_length=20, verbose_name='Número NF-e')
    serie = models.CharField(max_length=3, default='1', verbose_name='Série')
    chave_acesso = models.CharField(
        max_length=44, 
        blank=True, 
        default='', 
        verbose_name='Chave de Acesso'
    )

    fornecedor = models.ForeignKey(
        Fornecedor,
        on_delete=models.PROTECT,
        related_name='entradas_nfe',
        verbose_name='Fornecedor'
    )

    pedido_compra = models.ForeignKey(
        PedidoCompra,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entradas_nfe',
        verbose_name='Pedido de Compra'
    )

    deposito = models.ForeignKey(
        Deposito,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='entradas_nfe',
        verbose_name='Depósito de Destino'
    )

    data_emissao = models.DateField(
        default=timezone.now,
        verbose_name='Data de Emissão'
    )

    data_entrada = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Data de Entrada'
    )

    valor_total = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0, 
        verbose_name='Valor Total'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pendente',
        verbose_name='Status'
    )

    observacoes = models.TextField(blank=True, verbose_name='Observações')

    usuario = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='entradas_nfe',
        verbose_name='Usuário'
    )

    class Meta:
        verbose_name = 'Entrada de NF-e'
        verbose_name_plural = 'Entradas de NF-e'
        ordering = ['-data_entrada']

    def __str__(self):
        return f"NF-e {self.numero_nfe} - {self.fornecedor.nome_razao_social}"


class ItemEntradaNFE(models.Model):
    """
    Itens da Nota Fiscal de Entrada
    """
    entrada = models.ForeignKey(
        EntradaNFE,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Entrada NF-e'
    )
    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='itens_entrada_nfe',
        verbose_name='Produto'
    )
    quantidade = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=0,
        verbose_name='Quantidade'
    )
    valor_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        verbose_name='Valor Unitário'
    )
    valor_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Valor Total'
    )
    observacoes = models.TextField(blank=True, verbose_name='Observações')

    class Meta:
        verbose_name = 'Item da Entrada NF-e'
        verbose_name_plural = 'Itens da Entrada NF-e'
        ordering = ['id']

    def __str__(self):
        return f"{self.produto.descricao if self.produto else 'Sem produto'} - {self.quantidade} UN"

    def save(self, *args, **kwargs):
        self.valor_total = self.quantidade * self.valor_unitario
        super().save(*args, **kwargs)