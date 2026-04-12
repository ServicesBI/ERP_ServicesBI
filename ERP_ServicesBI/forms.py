# -*- coding: utf-8 -*-
from django import forms
from decimal import Decimal
from .models import (
    # Cadastros Base
    Empresa, Cliente, Fornecedor, Vendedor, Projeto,

    # Produtos
    Produto, CategoriaProduto, UnidadeMedida,

    # Pagamentos
    CondicaoPagamento, FormaPagamento,

    # Compras
    PedidoCompra, ItemPedidoCompra,
    NotaFiscalEntrada, ItemNotaFiscalEntrada,
    CotacaoMae, ItemSolicitado,
    CotacaoFornecedor, ItemCotacaoFornecedor,
    RegraAprovacao, PedidoAprovacao,

    # Vendas
    # NOTA: Orcamento e ItemOrcamento não existem no models.py
    # Usando OrcamentoProjeto como alternativa temporária
    PedidoVenda, ItemPedidoVenda,
    NotaFiscalSaida, ItemNotaFiscalSaida,

    # Financeiro
    ContaPagar, ContaReceber, MovimentoCaixa,
    CategoriaFinanceira, CentroCusto, OrcamentoFinanceiro,
    ExtratoBancario, LancamentoExtrato, ContaBancaria,
    ConfiguracaoDRE, LinhaDRE, RelatorioDRE, ItemRelatorioDRE,

    # Planejamento x Realizado 
    OrcamentoProjeto,

    # Estoque
    MovimentacaoEstoque,
    Deposito, SaldoEstoque,
    EntradaNFE, ItemEntradaNFE,
    Inventario, ItemInventario,
    TransferenciaEstoque, ItemTransferencia,
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
        self.fields['condicao_pagamento_padrao'].required = False
        self.fields['forma_pagamento_padrao'].required = False
        self.fields['condicao_pagamento_padrao'].queryset = CondicaoPagamento.objects.filter(ativo=True)
        self.fields['forma_pagamento_padrao'].queryset = FormaPagamento.objects.filter(ativo=True)
        self.fields['condicao_pagamento_padrao'].widget.attrs.update({'class': 'form-select'})
        self.fields['forma_pagamento_padrao'].widget.attrs.update({'class': 'form-select'})

# =============================================================================
# MÓDULO: CADASTRO - VENDEDORES
# =============================================================================

class VendedorForm(forms.ModelForm):
    class Meta:
        model = Vendedor
        fields = [
            'ativo', 'foto', 'nome', 'cpf', 'apelido',
            'telefone', 'email', 'comissao_padrao', 'meta_vendas', 'observacoes',
        ]
        widgets = {
            'foto': forms.FileInput(attrs={'class': 'foto-input', 'accept': 'image/*'}),
            'nome': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Digite o nome completo do vendedor'}),
            'cpf': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '000.000.000-00', 'maxlength': '14'}),
            'apelido': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Como prefere ser chamado'}),
            'telefone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '(00) 00000-0000', 'maxlength': '15'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'email@exemplo.com'}),
            'comissao_padrao': forms.TextInput(attrs={'class': 'form-input has-suffix', 'placeholder': '5.00'}),
            'meta_vendas': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '0.00'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-textarea', 'placeholder': 'Informações adicionais sobre o vendedor...', 'rows': '4'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['foto'].required = False
        self.fields['cpf'].required = False
        self.fields['apelido'].required = False
        self.fields['telefone'].required = False
        self.fields['meta_vendas'].required = False
        self.fields['observacoes'].required = False
        self.fields['comissao_padrao'].label = 'Comissão Padrão (%)'
        self.fields['meta_vendas'].label = 'Meta de Vendas Mensal'
        self.fields['comissao_padrao'].help_text = 'Use ponto para decimal (ex: 15.00)'
        self.fields['meta_vendas'].help_text = 'Opcional - meta em reais'
        self.fields['foto'].help_text = 'Formatos: JPG, PNG. Máx: 2MB'

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf', '')
        if cpf:
            cpf_limpo = ''.join(filter(str.isdigit, cpf))
            if len(cpf_limpo) != 11:
                raise forms.ValidationError('CPF deve ter 11 dígitos.')
            return cpf_limpo
        return cpf

    def clean_telefone(self):
        telefone = self.cleaned_data.get('telefone', '')
        if telefone:
            return ''.join(filter(str.isdigit, telefone))
        return telefone

    def clean_comissao_padrao(self):
        comissao = self.cleaned_data.get('comissao_padrao')
        if isinstance(comissao, Decimal):
            return comissao
        if not comissao or comissao == '':
            raise forms.ValidationError('Comissão é obrigatória.')
        try:
            valor = Decimal(str(comissao).replace(',', '.'))
            if valor < 0 or valor > 100:
                raise forms.ValidationError('Comissão deve estar entre 0 e 100.')
            return valor
        except Exception:
            raise forms.ValidationError('Valor inválido. Use formato: 5.00')

    def clean_meta_vendas(self):
        meta = self.cleaned_data.get('meta_vendas')
        if isinstance(meta, Decimal) or meta is None:
            return meta
        if meta == '':
            return None
        try:
            return Decimal(str(meta).replace('.', '').replace(',', '.'))
        except Exception:
            raise forms.ValidationError('Valor inválido. Use formato: 1000.00')

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        if email:
            qs = Vendedor.objects.filter(email=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('email', 'Já existe um vendedor com este e-mail.')
        return cleaned_data



# =============================================================================
# MÓDULO: CADASTRO - PROJETOS
# =============================================================================

class ProjetoForm(BaseForm):
    """Formulário para cadastro de projetos"""
    class Meta:
        model = Projeto
        fields = ['nome', 'codigo', 'cliente', 'data_inicio', 'data_fim', 'status', 'observacoes']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'erp-input', 'placeholder': 'Nome do projeto'}),
            'codigo': forms.TextInput(attrs={'class': 'erp-input', 'placeholder': 'Gerado automaticamente se vazio'}),
            'cliente': forms.Select(attrs={'class': 'erp-select'}),
            'data_inicio': forms.DateInput(attrs={'class': 'erp-input', 'type': 'date'}),
            'data_fim': forms.DateInput(attrs={'class': 'erp-input', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'erp-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'erp-textarea', 'rows': 3, 'placeholder': 'Observações...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cliente'].queryset = Cliente.objects.filter(ativo=True)
        self.fields['cliente'].empty_label = "Selecione um cliente..."
        self.fields['codigo'].required = False
        self.fields['cliente'].required = False
        self.fields['data_inicio'].required = False
        self.fields['data_fim'].required = False
        self.fields['observacoes'].required = False

# =============================================================================
# MÓDULO: CONFIGURAÇÕES - EMPRESA
# =============================================================================

_ESTADOS_CHOICES = [
    ('', 'Selecione...'),
    ('AC', 'AC'), ('AL', 'AL'), ('AP', 'AP'), ('AM', 'AM'),
    ('BA', 'BA'), ('CE', 'CE'), ('DF', 'DF'), ('ES', 'ES'),
    ('GO', 'GO'), ('MA', 'MA'), ('MT', 'MT'), ('MS', 'MS'),
    ('MG', 'MG'), ('PA', 'PA'), ('PB', 'PB'), ('PR', 'PR'),
    ('PE', 'PE'), ('PI', 'PI'), ('RJ', 'RJ'), ('RN', 'RN'),
    ('RS', 'RS'), ('RO', 'RO'), ('RR', 'RR'), ('SC', 'SC'),
    ('SP', 'SP'), ('SE', 'SE'), ('TO', 'TO'),
]

class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = [
            'ativo', 'nome_fantasia', 'razao_social', 'cnpj',
            'inscricao_estadual', 'inscricao_municipal', 'telefone', 'email',
            'cep', 'endereco', 'numero', 'bairro', 'cidade', 'estado',
        ]
        widgets = {
            'nome_fantasia': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nome fantasia da empresa'}),
            'razao_social': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Razão social completa'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '00.000.000/0000-00', 'maxlength': '18'}),
            'inscricao_estadual': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Inscrição Estadual'}),
            'inscricao_municipal': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Inscrição Municipal'}),
            'telefone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '(00) 00000-0000', 'maxlength': '15'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'empresa@exemplo.com'}),
            'cep': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '00000-000', 'maxlength': '9'}),
            'endereco': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Rua, Avenida, etc.'}),
            'numero': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nº'}),
            'bairro': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Bairro'}),
            'cidade': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Cidade'}),
            'estado': forms.Select(attrs={'class': 'form-select'}, choices=_ESTADOS_CHOICES),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome_fantasia'].required = True
        self.fields['razao_social'].required = True
        self.fields['cnpj'].required = True
        for f in ['inscricao_estadual', 'inscricao_municipal', 'telefone', 'email',
                  'cep', 'endereco', 'numero', 'bairro', 'cidade', 'estado']:
            self.fields[f].required = False
        self.fields['nome_fantasia'].label = 'Nome Fantasia'
        self.fields['razao_social'].label = 'Razão Social'
        self.fields['inscricao_estadual'].label = 'Inscrição Estadual'
        self.fields['inscricao_municipal'].label = 'Inscrição Municipal'

    def clean_cnpj(self):
        cnpj = self.cleaned_data.get('cnpj', '')
        if cnpj:
            limpo = ''.join(filter(str.isdigit, cnpj))
            if len(limpo) != 14:
                raise forms.ValidationError('CNPJ deve ter 14 dígitos.')
            return limpo
        return cnpj

    def clean_telefone(self):
        tel = self.cleaned_data.get('telefone', '')
        return ''.join(filter(str.isdigit, tel)) if tel else tel

    def clean_cep(self):
        cep = self.cleaned_data.get('cep', '')
        return ''.join(filter(str.isdigit, cep)) if cep else cep

# =============================================================================
# MÓDULO: CADASTRO - FORNECEDORES
# =============================================================================

class FornecedorForm(forms.ModelForm):
    class Meta:
        model = Fornecedor
        fields = [
            'ativo', 'tipo_pessoa', 'nome_razao_social', 'nome_fantasia',
            'cpf_cnpj', 'rg_inscricao_estadual', 'telefone', 'email',
            'cep', 'endereco', 'numero', 'bairro', 'cidade', 'estado',
            'limite_credito', 'observacoes',
            'condicao_pagamento_padrao', 'forma_pagamento_padrao',
        ]
        widgets = {
            'tipo_pessoa': forms.Select(attrs={'class': 'form-select'}, choices=[('', 'Selecione...'), ('F', 'Física'), ('J', 'Jurídica')]),
            'nome_razao_social': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nome ou razão social'}),
            'nome_fantasia': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nome fantasia'}),
            'cpf_cnpj': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '00.000.000/0000-00', 'maxlength': '18'}),
            'rg_inscricao_estadual': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'RG ou Inscrição Estadual'}),
            'telefone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '(00) 00000-0000', 'maxlength': '15'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'email@exemplo.com'}),
            'cep': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '00000-000', 'maxlength': '9'}),
            'endereco': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Rua, Avenida, etc.'}),
            'numero': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nº'}),
            'bairro': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Bairro'}),
            'cidade': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Cidade'}),
            'estado': forms.Select(attrs={'class': 'form-select'}, choices=_ESTADOS_CHOICES),
            'limite_credito': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'R$ 0,00'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-textarea', 'placeholder': 'Observações...', 'rows': '3'}),
            'condicao_pagamento_padrao': forms.Select(attrs={'class': 'form-select'}),
            'forma_pagamento_padrao': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo_pessoa'].required = True
        self.fields['nome_razao_social'].required = True
        self.fields['cpf_cnpj'].required = True
        for f in ['nome_fantasia', 'rg_inscricao_estadual', 'telefone', 'email',
                  'cep', 'endereco', 'numero', 'bairro', 'cidade', 'estado',
                  'limite_credito', 'observacoes', 'ativo',
                  'condicao_pagamento_padrao', 'forma_pagamento_padrao']:
            self.fields[f].required = False
        self.fields['condicao_pagamento_padrao'].queryset = CondicaoPagamento.objects.filter(ativo=True)
        self.fields['forma_pagamento_padrao'].queryset = FormaPagamento.objects.filter(ativo=True)
        self.fields['nome_razao_social'].label = 'Nome / Razão Social'
        self.fields['nome_fantasia'].label = 'Nome Fantasia'
        self.fields['cpf_cnpj'].label = 'CPF/CNPJ'
        self.fields['rg_inscricao_estadual'].label = 'RG/Inscrição Estadual'
        self.fields['limite_credito'].label = 'Limite de Crédito'
        self.fields['condicao_pagamento_padrao'].label = 'Condição de Pagamento Padrão'
        self.fields['forma_pagamento_padrao'].label = 'Forma de Pagamento Padrão'

    def clean_cpf_cnpj(self):
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
        tel = self.cleaned_data.get('telefone', '')
        return ''.join(filter(str.isdigit, tel)) if tel else tel

    def clean_cep(self):
        cep = self.cleaned_data.get('cep', '')
        return ''.join(filter(str.isdigit, cep)) if cep else cep

    def clean_limite_credito(self):
        limite = self.cleaned_data.get('limite_credito')
        if isinstance(limite, Decimal):
            return limite
        if not limite or limite == '':
            return Decimal('0')
        try:
            return Decimal(str(limite).replace('R$', '').replace('.', '').replace(',', '.').strip())
        except Exception:
            raise forms.ValidationError('Valor inválido para limite de crédito.')

# =============================================================================
# MÓDULO: CADASTRO - PRODUTOS
# =============================================================================

class CategoriaProdutoForm(BaseForm):
    class Meta:
        model = CategoriaProduto
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
        for f in ['codigo', 'categoria', 'fornecedor', 'unidade',
                  'estoque_atual', 'estoque_minimo', 'observacoes', 'ativo']:
            self.fields[f].required = False

# =============================================================================
# MÓDULO: CADASTRO - UNIDADE DE MEDIDA
# =============================================================================

class UnidadeMedidaForm(BaseForm):
    class Meta:
        model = UnidadeMedida
        fields = ['sigla', 'nome', 'ativo']
        widgets = {
            'sigla': forms.TextInput(attrs={'class': 'erp-input', 'placeholder': 'Ex: UN, KG, LT'}),
            'nome': forms.TextInput(attrs={'class': 'erp-input', 'placeholder': 'Ex: Unidade, Quilograma'}),
        }

# =============================================================================
# MÓDULO: CADASTRO - CONDIÇÕES DE PAGAMENTO
# =============================================================================

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

class OrcamentoForm(BaseForm):
    valor_total = MoneyField(required=False)

    class Meta:
        model = OrcamentoProjeto  # Substituído temporariamente
        fields = '__all__'
        widgets = {'data_inicio': forms.DateInput(attrs={'type': 'date'})}  # Campo ajustado


class ItemOrcamentoForm(BaseForm):
    preco_unitario = MoneyField()
    subtotal = MoneyField(required=False)

    class Meta:
        model = ItemPedidoVenda  # Substituído temporariamente - modelo ItemOrcamento não existe
        fields = '__all__'

# =============================================================================
# MÓDULO: VENDAS - PEDIDO DE VENDA
# =============================================================================

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

class ContaReceberForm(BaseForm):
    valor_original = MoneyField()
    valor_pago = MoneyField(required=False)

    class Meta:
        model = ContaReceber
        fields = '__all__'
        widgets = {'data_vencimento': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cliente'].queryset = Cliente.objects.all()
        self.fields['categoria'].queryset = CategoriaFinanceira.objects.filter(tipo='receita')

# =============================================================================
# MÓDULO: FINANCEIRO - BAIXA DE CONTAS
# =============================================================================

class BaixaContaPagarForm(forms.Form):
    data_pagamento = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'erp-input', 'type': 'date'}),
        label='Data de Pagamento'
    )
    valor_pago = forms.DecimalField(
        max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'erp-input', 'step': '0.01'}),
        label='Valor Pago'
    )
    observacoes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'erp-textarea', 'rows': 2}),
        label='Observações'
    )


class BaixaContaReceberForm(forms.Form):
    data_recebimento = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'erp-input', 'type': 'date'}),
        label='Data de Recebimento'
    )
    valor_recebido = forms.DecimalField(
        max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'erp-input', 'step': '0.01'}),
        label='Valor Recebido'
    )
    observacoes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'erp-textarea', 'rows': 2}),
        label='Observações'
    )

# =============================================================================
# MÓDULO: FINANCEIRO - CATEGORIA FINANCEIRA
# =============================================================================

class CategoriaFinanceiraForm(BaseForm):
    class Meta:
        model = CategoriaFinanceira
        fields = '__all__'

# =============================================================================
# MÓDULO: FINANCEIRO - CENTRO DE CUSTO
# =============================================================================

class CentroCustoForm(BaseForm):
    class Meta:
        model = CentroCusto
        fields = '__all__'

# =============================================================================
# MÓDULO: FINANCEIRO - ORÇAMENTO FINANCEIRO
# =============================================================================

class OrcamentoFinanceiroForm(BaseForm):
    valor_orcado = MoneyField()
    valor_realizado = MoneyField(required=False)

    class Meta:
        model = OrcamentoFinanceiro
        fields = '__all__'

# =============================================================================
# MÓDULO: FINANCEIRO - EXTRATO BANCÁRIO
# =============================================================================

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

class MovimentoCaixaForm(BaseForm):
    valor = MoneyField()

    class Meta:
        model = MovimentoCaixa
        fields = '__all__'

# =============================================================================
# MÓDULO: FINANCEIRO - DRE
# =============================================================================

# =============================================================================
# MÓDULO: FINANCEIRO - DRE - FORMS
# =============================================================================
# NOTA: ConfiguracaoDREForm foi removido daqui e movido para views.py
# como form dinâmico para evitar import circular com cadastros.Empresa
# =============================================================================

from django import forms
from .models import LinhaDRE  # Apenas modelos do próprio app


class LinhaDREForm(forms.ModelForm):
    """Form para cadastro de linhas DRE - NÃO depende de Empresa"""
    
    class Meta:
        model = LinhaDRE
        fields = [
            'codigo', 'descricao', 'tipo', 'natureza', 'grupos_dre',
            'formula', 'ordem', 'nivel', 'negrito', 'visivel',
            'regime_especifico', 'ativo',
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 1.0, 2.1'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'natureza': forms.Select(attrs={'class': 'form-control'}),
            'grupos_dre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: receita_bruta,outras_receitas'}),
            'formula': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 1.0-2.0 ou 3.0+4.0'}),
            'ordem': forms.NumberInput(attrs={'class': 'form-control'}),
            'nivel': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 3}),
            'negrito': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'visivel': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'regime_especifico': forms.Select(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class FiltroDREForm(forms.Form):
    """Form para filtrar/visualizar DRE - Usa lazy queryset"""
    
    empresa = forms.ModelChoiceField(
        queryset=None,  # Será setado no __init__
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Empresa'
    )
    data_inicio = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Data Início'
    )
    data_fim = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
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
        # Lazy import e queryset - só executa quando o form é instanciado
        from cadastros.models import Empresa
        self.fields['empresa'].queryset = Empresa.objects.filter(ativo=True)

# =============================================================================
# MÓDULO: ESTOQUE - DEPÓSITO
# =============================================================================

class DepositoForm(forms.ModelForm):
    class Meta:
        model = Deposito
        fields = ['codigo', 'nome', 'descricao', 'endereco', 'responsavel', 'ativo']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código'}),
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do Depósito'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'responsavel': forms.TextInput(attrs={'class': 'form-control'}),
        }

# =============================================================================
# MÓDULO: ESTOQUE - MOVIMENTAÇÃO
# =============================================================================

class MovimentacaoEstoqueForm(forms.ModelForm):
    """Formulário para movimentação de estoque"""
    
    class Meta:
        model = MovimentacaoEstoque
        fields = [
            'tipo', 'produto', 'data', 'nota_fiscal_entrada', 'nota_fiscal_saida',
            'deposito_origem', 'deposito_destino', 'quantidade', 
            'preco_unitario', 'valor_total', 'motivo', 'observacoes'
        ]
        widgets = {
            'data': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'quantidade': forms.NumberInput(attrs={'step': '0.001', 'min': '0.001'}),
            'preco_unitario': forms.TextInput(attrs={'placeholder': '0,00'}),
            'valor_total': forms.TextInput(attrs={'readonly': 'readonly'}),
            'motivo': forms.TextInput(attrs={'placeholder': 'Ex: Entrada via NF, Ajuste de inventário...'}),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Tornar campos condicionais não obrigatórios no form
        self.fields['deposito_origem'].required = False
        self.fields['deposito_destino'].required = False
        self.fields['nota_fiscal_entrada'].required = False
        self.fields['nota_fiscal_saida'].required = False
        self.fields['preco_unitario'].required = False
        self.fields['valor_total'].required = False
        self.fields['motivo'].required = False
        self.fields['observacoes'].required = False
        
        # Querysets
        self.fields['produto'].queryset = Produto.objects.filter(ativo=True)
        self.fields['deposito_origem'].queryset = Deposito.objects.filter(ativo=True)
        self.fields['deposito_destino'].queryset = Deposito.objects.filter(ativo=True)
        self.fields['nota_fiscal_entrada'].queryset = NotaFiscalEntrada.objects.filter(status='confirmada')
    
    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        deposito_origem = cleaned_data.get('deposito_origem')
        deposito_destino = cleaned_data.get('deposito_destino')
        quantidade = cleaned_data.get('quantidade')
        produto = cleaned_data.get('produto')
        
        # Validações baseadas no tipo
        if tipo == 'entrada':
            if not deposito_destino:
                self.add_error('deposito_destino', 'Depósito de destino é obrigatório para entradas.')
        
        elif tipo == 'saida':
            if not deposito_origem:
                self.add_error('deposito_origem', 'Depósito de origem é obrigatório para saídas.')
            # Verificar se há estoque suficiente
            if produto and quantidade:
                if produto.estoque_atual < quantidade:
                    self.add_error('quantidade', f'Estoque insuficiente. Disponível: {produto.estoque_atual}')
        
        elif tipo == 'transferencia':
            if not deposito_origem:
                self.add_error('deposito_origem', 'Depósito de origem é obrigatório para transferências.')
            if not deposito_destino:
                self.add_error('deposito_destino', 'Depósito de destino é obrigatório para transferências.')
            if deposito_origem and deposito_destino and deposito_origem == deposito_destino:
                self.add_error('deposito_destino', 'Depósito de destino deve ser diferente do de origem.')
        
        elif tipo == 'ajuste':
            if not deposito_origem:
                self.add_error('deposito_origem', 'Depósito é obrigatório para ajustes.')
        
        return cleaned_data
    
    def clean_preco_unitario(self):
        valor = self.cleaned_data.get('preco_unitario')
        if valor:
            if isinstance(valor, str):
                valor = valor.replace('.', '').replace(',', '.')
            return Decimal(valor) if valor else None
        return None
    
    def clean_valor_total(self):
        valor = self.cleaned_data.get('valor_total')
        if valor:
            if isinstance(valor, str):
                valor = valor.replace('.', '').replace(',', '.')
            return Decimal(valor) if valor else None
        return None

# =============================================================================
# MÓDULO: ESTOQUE - INVENTÁRIO (CORRIGIDO)
# =============================================================================

class InventarioForm(forms.ModelForm):
    class Meta:
        model = Inventario
        fields = ['data', 'deposito', 'observacoes']  # ✅ Campos específicos
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'deposito': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ItemInventarioForm(forms.ModelForm):
    class Meta:
        model = ItemInventario
        fields = ['quantidade_contada', 'observacoes']  # ✅ Removido 'produto' (é automático)
        widgets = {
            'quantidade_contada': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        
# =============================================================================
# MÓDULO: ESTOQUE - TRANSFERÊNCIA
# =============================================================================

class TransferenciaEstoqueForm(BaseForm):
    class Meta:
        model = TransferenciaEstoque
        fields = '__all__'


class ItemTransferenciaForm(BaseForm):
    class Meta:
        model = ItemTransferencia
        fields = '__all__'

# =============================================================================
# MÓDULO: ESTOQUE - ENTRADA NF-E
# =============================================================================

class EntradaNFEForm(forms.ModelForm):
    class Meta:
        model = EntradaNFE
        fields = [
            'numero_nfe', 'serie', 'chave_acesso', 'fornecedor',
            'pedido_compra', 'deposito', 'data_emissao', 'observacoes',
        ]
        widgets = {
            'numero_nfe': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número da NF-e'}),
            'serie': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1'}),
            'chave_acesso': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Chave de Acesso (44 dígitos)'}),
            'fornecedor': forms.Select(attrs={'class': 'form-control'}),
            'pedido_compra': forms.Select(attrs={'class': 'form-control'}),
            'deposito': forms.Select(attrs={'class': 'form-control'}),
            'data_emissao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ItemEntradaNFEForm(forms.ModelForm):
    class Meta:
        model = ItemEntradaNFE
        fields = ['produto', 'quantidade', 'valor_unitario']
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-control'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'valor_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
        }

# =============================================================================
# MÓDULO: COTAÇÃO COMPARATIVA
# =============================================================================

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
        fields = [
            'fornecedor', 'contato_nome', 'contato_email', 'contato_telefone',
            'valor_total_bruto', 'percentual_desconto', 'valor_frete',
            'condicao_pagamento', 'prazo_entrega_dias', 'disponibilidade_produtos',
            'status', 'observacoes',
        ]
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
        fields = [
            'item_solicitado', 'descricao_fornecedor', 'codigo_fornecedor',
            'quantidade', 'unidade_medida', 'preco_unitario', 'disponivel',
            'prazo_entrega_item', 'observacao',
        ]
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

# =============================================================================
# MÓDULO: PLANEJADO X REALIZADO - FORMULÁRIO
# =============================================================================

class OrcamentoProjetoForm(BaseForm):
    receitas_orcadas = MoneyField()
    despesas_orcadas = MoneyField()
    realizado_receitas = MoneyField(required=False)
    realizado_despesas = MoneyField(required=False)
    
    class Meta:
        model = OrcamentoProjeto
        fields = ['projeto', 'ano', 'mes', 'receitas_orcadas', 'despesas_orcadas', 
                  'realizado_receitas', 'realizado_despesas', 'observacoes']
        widgets = {
            'projeto': forms.Select(attrs={'class': 'erp-select'}),
            'ano': forms.NumberInput(attrs={'class': 'erp-input', 'min': '2000', 'max': '2100'}),
            'mes': forms.Select(attrs={'class': 'erp-select'}),
            'observacoes': forms.Textarea(attrs={'rows': 3, 'class': 'erp-textarea'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['projeto'].queryset = Projeto.objects.filter(status='ativo').order_by('nome')
        self.fields['projeto'].empty_label = "Selecione um projeto..."
        self.fields['realizado_receitas'].initial = 0
        self.fields['realizado_despesas'].initial = 0
        
        # Se for edição, carregar valores realizados
        if self.instance and self.instance.pk:
            self.fields['realizado_receitas'].initial = self.instance.realizado_receitas
            self.fields['realizado_despesas'].initial = self.instance.realizado_despesas
    
    def clean(self):
        cleaned_data = super().clean()
        projeto = cleaned_data.get('projeto')
        ano = cleaned_data.get('ano')
        mes = cleaned_data.get('mes')
        
        # Verificar duplicidade (exceto na edição do próprio registro)
        if projeto and ano and mes:
            qs = OrcamentoProjeto.objects.filter(projeto=projeto, ano=ano, mes=mes)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f'Já existe um orçamento para {projeto} em {mes}/{ano}.'
                )
        
        return cleaned_data

# =============================================================================
# FORMS ADICIONAIS - CRIADOS AUTOMATICAMENTE PARA COMPATIBILIDADE COM VIEWS.PY
# =============================================================================

# -----------------------------------------------------------------------------
# CADASTROS - TRANSPORTADORA (Modelo não existe - usando Fornecedor como base)
# -----------------------------------------------------------------------------
class TransportadoraForm(forms.ModelForm):
    """Form para Transportadora - usando Fornecedor como base temporária"""
    class Meta:
        model = Fornecedor  # Substituído temporariamente
        fields = ['nome_razao_social', 'nome_fantasia', 'cpf_cnpj', 'telefone', 'email', 'ativo']
        widgets = {
            'nome_razao_social': forms.TextInput(attrs={'class': 'erp-input', 'placeholder': 'Razão Social'}),
            'nome_fantasia': forms.TextInput(attrs={'class': 'erp-input', 'placeholder': 'Nome Fantasia'}),
            'cpf_cnpj': forms.TextInput(attrs={'class': 'erp-input', 'placeholder': 'CNPJ'}),
            'telefone': forms.TextInput(attrs={'class': 'erp-input', 'placeholder': 'Telefone'}),
            'email': forms.EmailInput(attrs={'class': 'erp-input', 'placeholder': 'Email'}),
        }


# -----------------------------------------------------------------------------
# CADASTROS - MARCA (Modelo não existe - usando CategoriaProduto como base)
# -----------------------------------------------------------------------------
class MarcaForm(forms.ModelForm):
    """Form para Marca - usando CategoriaProduto como base temporária"""
    class Meta:
        model = CategoriaProduto  # Substituído temporariamente
        fields = ['nome', 'descricao', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'erp-input', 'placeholder': 'Nome da Marca'}),
            'descricao': forms.Textarea(attrs={'class': 'erp-textarea', 'rows': 3, 'placeholder': 'Descrição'}),
        }


# -----------------------------------------------------------------------------
# COMPRAS - COTAÇÃO
# -----------------------------------------------------------------------------
class CotacaoForm(forms.ModelForm):
    """Form para Cotação (CotacaoMae)"""
    class Meta:
        model = CotacaoMae
        fields = ['titulo', 'setor', 'data_limite_resposta', 'observacoes', 'status', 'ativo']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'erp-input', 'placeholder': 'Título da Cotação'}),
            'setor': forms.TextInput(attrs={'class': 'erp-input', 'placeholder': 'Setor solicitante'}),
            'data_limite_resposta': forms.DateInput(attrs={'class': 'erp-input', 'type': 'date'}),
            'observacoes': forms.Textarea(attrs={'class': 'erp-textarea', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'erp-select'}),
        }


class ItemCotacaoForm(forms.ModelForm):
    """Form para Item de Cotação (ItemSolicitado)"""
    class Meta:
        model = ItemSolicitado
        fields = ['produto', 'descricao_manual', 'quantidade', 'unidade_medida']
        widgets = {
            'produto': forms.Select(attrs={'class': 'erp-select'}),
            'descricao_manual': forms.TextInput(attrs={'class': 'erp-input', 'placeholder': 'Descrição manual se não tiver produto'}),
            'quantidade': forms.NumberInput(attrs={'class': 'erp-input', 'step': '0.001'}),
            'unidade_medida': forms.TextInput(attrs={'class': 'erp-input'}),
        }


# -----------------------------------------------------------------------------
# FINANCEIRO - FLUXO DE CAIXA
# -----------------------------------------------------------------------------
class FluxoCaixaForm(forms.ModelForm):
    """Form para Fluxo de Caixa (MovimentoCaixa)"""
    class Meta:
        model = MovimentoCaixa
        fields = '__all__'
        widgets = {
            'data': forms.DateInput(attrs={'class': 'erp-input', 'type': 'date'}),
            'descricao': forms.TextInput(attrs={'class': 'erp-input'}),
            'tipo': forms.Select(attrs={'class': 'erp-select'}),
            'categoria': forms.Select(attrs={'class': 'erp-select'}),
            'valor': forms.NumberInput(attrs={'class': 'erp-input', 'step': '0.01'}),
        }


# -----------------------------------------------------------------------------
# FINANCEIRO - LANÇAMENTO DRE
# -----------------------------------------------------------------------------
class LancamentoDREForm(forms.ModelForm):
    """Form para Lançamento DRE (ItemRelatorioDRE)"""
    class Meta:
        model = ItemRelatorioDRE
        fields = '__all__'


# -----------------------------------------------------------------------------
# FINANCEIRO - CONCILIAÇÃO BANCÁRIA
# -----------------------------------------------------------------------------
class ConciliacaoBancariaForm(forms.ModelForm):
    """Form para Conciliação Bancária (ExtratoBancario)"""
    class Meta:
        model = ExtratoBancario
        fields = '__all__'
        widgets = {
            'data': forms.DateInput(attrs={'class': 'erp-input', 'type': 'date'}),
            'descricao': forms.TextInput(attrs={'class': 'erp-input'}),
            'valor': forms.NumberInput(attrs={'class': 'erp-input', 'step': '0.01'}),
        }


# -----------------------------------------------------------------------------
# FINANCEIRO - PLANEJADO X REALIZADO
# -----------------------------------------------------------------------------
class PlanejadoRealizadoForm(forms.ModelForm):
    """Form para Planejado x Realizado (OrcamentoProjeto)"""
    class Meta:
        model = OrcamentoProjeto
        fields = ['projeto', 'ano', 'mes', 'receitas_orcadas', 'despesas_orcadas', 
                  'realizado_receitas', 'realizado_despesas', 'observacoes']
        widgets = {
            'projeto': forms.Select(attrs={'class': 'erp-select'}),
            'ano': forms.NumberInput(attrs={'class': 'erp-input'}),
            'mes': forms.Select(attrs={'class': 'erp-select'}),
            'receitas_orcadas': forms.NumberInput(attrs={'class': 'erp-input', 'step': '0.01'}),
            'despesas_orcadas': forms.NumberInput(attrs={'class': 'erp-input', 'step': '0.01'}),
            'realizado_receitas': forms.NumberInput(attrs={'class': 'erp-input', 'step': '0.01'}),
            'realizado_despesas': forms.NumberInput(attrs={'class': 'erp-input', 'step': '0.01'}),
            'observacoes': forms.Textarea(attrs={'class': 'erp-textarea', 'rows': 3}),
        }


# -----------------------------------------------------------------------------
# FINANCEIRO - CONTA BANCÁRIA
# -----------------------------------------------------------------------------
class ContaBancariaForm(forms.ModelForm):
    """Form para Conta Bancária"""
    class Meta:
        model = ContaBancaria
        fields = '__all__'
        widgets = {
            'banco': forms.TextInput(attrs={'class': 'erp-input'}),
            'agencia': forms.TextInput(attrs={'class': 'erp-input'}),
            'conta': forms.TextInput(attrs={'class': 'erp-input'}),
            'titular': forms.TextInput(attrs={'class': 'erp-input'}),
        }


# -----------------------------------------------------------------------------
# ESTOQUE - ITEM MOVIMENTAÇÃO
# -----------------------------------------------------------------------------
class ItemMovimentacaoEstoqueForm(forms.ModelForm):
    """Form para Item de Movimentação de Estoque"""
    class Meta:
        model = MovimentacaoEstoque
        fields = ['tipo', 'produto', 'quantidade', 'deposito_origem', 'deposito_destino', 
                  'motivo', 'observacoes']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'erp-select'}),
            'produto': forms.Select(attrs={'class': 'erp-select'}),
            'quantidade': forms.NumberInput(attrs={'class': 'erp-input', 'step': '0.001'}),
            'deposito_origem': forms.Select(attrs={'class': 'erp-select'}),
            'deposito_destino': forms.Select(attrs={'class': 'erp-select'}),
            'motivo': forms.TextInput(attrs={'class': 'erp-input'}),
            'observacoes': forms.Textarea(attrs={'class': 'erp-textarea', 'rows': 3}),
        }


# -----------------------------------------------------------------------------
# ESTOQUE - ITEM TRANSFERÊNCIA
# -----------------------------------------------------------------------------
class ItemTransferenciaEstoqueForm(forms.ModelForm):
    """Form para Item de Transferência de Estoque"""
    class Meta:
        model = ItemTransferencia
        fields = '__all__'
        widgets = {
            'produto': forms.Select(attrs={'class': 'erp-select'}),
            'quantidade': forms.NumberInput(attrs={'class': 'erp-input', 'step': '0.001'}),
        }


# -----------------------------------------------------------------------------
# COMPRAS - REGRA DE APROVAÇÃO
# -----------------------------------------------------------------------------
class RegraAprovacaoForm(forms.ModelForm):
    """Form para Regra de Aprovação"""
    class Meta:
        model = RegraAprovacao
        fields = '__all__'
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'erp-input'}),
            'valor_minimo': forms.NumberInput(attrs={'class': 'erp-input', 'step': '0.01'}),
            'valor_maximo': forms.NumberInput(attrs={'class': 'erp-input', 'step': '0.01'}),
            'nivel_aprovacao': forms.NumberInput(attrs={'class': 'erp-input'}),
        }


# -----------------------------------------------------------------------------
# COMPRAS - PEDIDO APROVAÇÃO
# -----------------------------------------------------------------------------
class PedidoAprovacaoForm(forms.ModelForm):
    """Form para Pedido de Aprovação"""
    class Meta:
        model = PedidoAprovacao
        fields = '__all__'
        widgets = {
            'status': forms.Select(attrs={'class': 'erp-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'erp-textarea', 'rows': 3}),
        }


# -----------------------------------------------------------------------------
# FINANCEIRO - ITEM RELATÓRIO DRE
# -----------------------------------------------------------------------------
class ItemRelatorioDREForm(forms.ModelForm):
    """Form para Item de Relatório DRE"""
    class Meta:
        model = ItemRelatorioDRE
        fields = '__all__'
        widgets = {
            'relatorio': forms.Select(attrs={'class': 'erp-select'}),
            'linha_dre': forms.Select(attrs={'class': 'erp-select'}),
            'valor': forms.NumberInput(attrs={'class': 'erp-input', 'step': '0.01'}),
        }


# -----------------------------------------------------------------------------
# ALIAS: CategoriaForm = CategoriaProdutoForm (para compatibilidade)
# -----------------------------------------------------------------------------
CategoriaForm = CategoriaProdutoForm