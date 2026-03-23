# -*- coding: utf-8 -*-
from django import forms
from django.contrib.auth.models import User
from .models import (
    Empresa, Cliente, Fornecedor, Produto, Categoria,
    Cotacao, ItemCotacao, PedidoCompra, ItemPedidoCompra, 
    NotaFiscalEntrada, ItemNotaFiscalEntrada,
    Orcamento, ItemOrcamento, PedidoVenda, ItemPedidoVenda, 
    NotaFiscalSaida, ItemNotaFiscalSaida,
    ContaPagar, ContaReceber, MovimentoCaixa,
    CategoriaFinanceira, CentroCusto, OrcamentoFinanceiro,
    ExtratoBancario, LancamentoExtrato,
    MovimentacaoEstoque, Inventario, ItemInventario, 
    TransferenciaEstoque, ItemTransferencia
)

# --- CAMPO DE MOEDA PADRÃO ---
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


# --- CONFIGURAÇÃO PADRÃO DE ESTILO ---
class BaseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'erp-input'})

# =============================================================================
# MÓDULO: CADASTRO
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


class EmpresaForm(BaseForm):
    class Meta:
        model = Empresa
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        self.fields['ativo'].required = False


class FornecedorForm(BaseForm):
    limite_credito = MoneyField()
    
    class Meta:
        model = Fornecedor
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


class CategoriaForm(BaseForm):
    class Meta:
        model = Categoria
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
# MÓDULO: COMPRAS
# =============================================================================

class CotacaoForm(BaseForm):
    valor_total = MoneyField(required=False)
    
    class Meta:
        model = Cotacao
        fields = ['fornecedor', 'solicitante', 'prazo_entrega', 'status', 'observacoes', 'ativo']
        widgets = {
            'fornecedor': forms.Select(attrs={'class': 'erp-select'}),
            'solicitante': forms.TextInput(attrs={'class': 'erp-input', 'placeholder': 'Nome do solicitante'}),
            'prazo_entrega': forms.DateInput(attrs={'type': 'date', 'class': 'erp-input'}),
            'status': forms.Select(attrs={'class': 'erp-select'}),
            'observacoes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Informações adicionais...', 'class': 'erp-textarea'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Popular Fornecedores (apenas ativos)
        if 'fornecedor' in self.fields:
            self.fields['fornecedor'].queryset = Fornecedor.objects.filter(ativo=True).order_by('nome_razao_social')
            self.fields['fornecedor'].empty_label = "Selecione um fornecedor..."
        
        # Solicitante - CAMPO TEXTO LIVRE (não precisa queryset)
        if 'solicitante' in self.fields:
            self.fields['solicitante'].required = True
            self.fields['solicitante'].widget.attrs.update({
                'placeholder': 'Digite o nome do solicitante',
                'class': 'erp-input'
            })
        
        # Campos não obrigatórios
        self.fields['observacoes'].required = False

class ItemCotacaoForm(BaseForm):
    preco_unitario = MoneyField()
    subtotal = MoneyField(required=False)
    
    class Meta:
        model = ItemCotacao
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['produto'].queryset = Produto.objects.filter(ativo=True).order_by('descricao')
        self.fields['produto'].empty_label = "Selecione um produto..."


class PedidoCompraForm(BaseForm):
    valor_total = MoneyField(required=False)
    
    class Meta:
        model = PedidoCompra
        fields = ['fornecedor', 'data_prevista_entrega', 'status', 'cotacao_origem', 'observacoes', 'ativo']
        widgets = {
            'fornecedor': forms.Select(attrs={'class': 'erp-select'}),
            'data_prevista_entrega': forms.DateInput(attrs={'type': 'date', 'class': 'erp-input'}),
            'status': forms.Select(attrs={'class': 'erp-select'}),
            'cotacao_origem': forms.Select(attrs={'class': 'erp-select'}),
            'observacoes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Informações adicionais...', 'class': 'erp-textarea'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Popular Fornecedores (apenas ativos)
        self.fields['fornecedor'].queryset = Fornecedor.objects.filter(ativo=True).order_by('nome_razao_social')
        self.fields['fornecedor'].empty_label = "Selecione um fornecedor..."
        
        # Cotação Origem - apenas cotações disponíveis
        self.fields['cotacao_origem'].queryset = Cotacao.objects.filter(
            status__in=['aprovada', 'pendente', 'respondida']
        ).order_by('-data_solicitacao')
        self.fields['cotacao_origem'].empty_label = "Nenhuma (opcional)"
        self.fields['cotacao_origem'].required = False
        
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
        
        # Pedido Origem - apenas pedidos disponíveis
        self.fields['pedido_origem'].queryset = PedidoCompra.objects.filter(
            status__in=['aprovado', 'parcial']
        ).order_by('-data_pedido')
        self.fields['pedido_origem'].empty_label = "Nenhum (opcional)"
        self.fields['pedido_origem'].required = False
        
        self.fields['chave_acesso'].required = False
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
# MÓDULO: VENDAS
# =============================================================================

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
# MÓDULO: FINANCEIRO
# =============================================================================

class ContaPagarForm(BaseForm):
    valor_original = MoneyField()
    valor_pago = MoneyField(required=False)
    
    class Meta:
        model = ContaPagar
        fields = '__all__'
        widgets = {'data_vencimento': forms.DateInput(attrs={'type': 'date'})}


class ContaReceberForm(BaseForm):
    valor_original = MoneyField()
    valor_pago = MoneyField(required=False)
    
    class Meta:
        model = ContaReceber
        fields = '__all__'
        widgets = {'data_vencimento': forms.DateInput(attrs={'type': 'date'})}


class MovimentoCaixaForm(BaseForm):
    valor = MoneyField()
    
    class Meta:
        model = MovimentoCaixa
        fields = '__all__'


class CategoriaFinanceiraForm(BaseForm):
    class Meta:
        model = CategoriaFinanceira
        fields = '__all__'


class CentroCustoForm(BaseForm):
    class Meta:
        model = CentroCusto
        fields = '__all__'


class OrcamentoFinanceiroForm(BaseForm):
    valor_previsto = MoneyField()
    valor_realizado = MoneyField(required=False)
    
    class Meta:
        model = OrcamentoFinanceiro
        fields = '__all__'


class ExtratoBancarioForm(BaseForm):
    saldo_inicial = MoneyField(required=False)
    saldo_final = MoneyField(required=False)
    
    class Meta:
        model = ExtratoBancario
        fields = '__all__'


class LancamentoExtratoForm(BaseForm):
    valor = MoneyField()
    
    class Meta:
        model = LancamentoExtrato
        fields = '__all__'

# =============================================================================
# MÓDULO: ESTOQUE
# =============================================================================

class MovimentacaoEstoqueForm(BaseForm):
    custo_unitario = MoneyField(required=False)
    
    class Meta:
        model = MovimentacaoEstoque
        fields = '__all__'


class InventarioForm(BaseForm):
    class Meta:
        model = Inventario
        fields = '__all__'
        widgets = {'data_inventario': forms.DateInput(attrs={'type': 'date'})}


class ItemInventarioForm(BaseForm):
    quantidade_sistema = MoneyField(required=False)
    quantidade_contada = MoneyField(required=False)
    valor_unitario = MoneyField(required=False)
    
    class Meta:
        model = ItemInventario
        fields = '__all__'


class TransferenciaEstoqueForm(BaseForm):
    class Meta:
        model = TransferenciaEstoque
        fields = '__all__'


class ItemTransferenciaForm(BaseForm):
    class Meta:
        model = ItemTransferencia
        fields = '__all__'