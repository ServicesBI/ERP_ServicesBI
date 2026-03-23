from django.contrib import admin
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


# =============================================================================
# CADASTRO
# =============================================================================

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ['nome_fantasia', 'razao_social', 'cnpj', 'telefone', 'ativo']
    search_fields = ['nome_fantasia', 'razao_social', 'cnpj']
    list_filter = ['ativo', 'estado']


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['nome_razao_social', 'cpf_cnpj', 'telefone', 'email', 'ativo']
    search_fields = ['nome_razao_social', 'cpf_cnpj', 'email']
    list_filter = ['ativo', 'tipo_pessoa']


@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ['nome_razao_social', 'nome_fantasia', 'cpf_cnpj', 'telefone', 'ativo']
    search_fields = ['nome_razao_social', 'nome_fantasia', 'cpf_cnpj']
    list_filter = ['ativo', 'tipo_pessoa']


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'ativo']
    search_fields = ['nome']


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'descricao', 'categoria', 'preco_venda', 'estoque_atual', 'estoque_minimo', 'ativo']  # CORRIGIDO: quantidade_estoque -> estoque_atual
    search_fields = ['codigo', 'descricao']
    list_filter = ['ativo', 'categoria', 'unidade']
    # CORRIGIDO: quantidade_estoque -> estoque_atual
    fields = ['codigo', 'descricao', 'categoria', 'unidade', 'preco_custo', 'preco_venda', 'estoque_atual', 'estoque_minimo', 'ativo']


# =============================================================================
# COMPRAS
# =============================================================================

class ItemCotacaoInline(admin.TabularInline):
    model = ItemCotacao
    extra = 1


@admin.register(Cotacao)
class CotacaoAdmin(admin.ModelAdmin):
    list_display = ['numero', 'fornecedor', 'data_solicitacao', 'status', 'valor_total']
    search_fields = ['numero', 'fornecedor__nome_razao_social']
    list_filter = ['status', 'data_solicitacao']
    inlines = [ItemCotacaoInline]


class ItemPedidoCompraInline(admin.TabularInline):
    model = ItemPedidoCompra
    extra = 1


@admin.register(PedidoCompra)
class PedidoCompraAdmin(admin.ModelAdmin):
    list_display = ['numero', 'fornecedor', 'data_pedido', 'status', 'valor_total']
    search_fields = ['numero', 'fornecedor__nome_razao_social']
    list_filter = ['status', 'data_pedido']
    inlines = [ItemPedidoCompraInline]


class ItemNotaFiscalEntradaInline(admin.TabularInline):
    model = ItemNotaFiscalEntrada
    extra = 1


@admin.register(NotaFiscalEntrada)
class NotaFiscalEntradaAdmin(admin.ModelAdmin):
    list_display = ['numero_nf', 'fornecedor', 'data_entrada', 'valor_total']
    search_fields = ['numero_nf', 'fornecedor__nome_razao_social']
    list_filter = ['data_entrada']
    inlines = [ItemNotaFiscalEntradaInline]


# =============================================================================
# VENDAS
# =============================================================================

class ItemOrcamentoInline(admin.TabularInline):
    model = ItemOrcamento
    extra = 1


@admin.register(Orcamento)
class OrcamentoAdmin(admin.ModelAdmin):
    list_display = ['numero', 'cliente', 'vendedor', 'data_orcamento', 'status', 'valor_total']
    search_fields = ['numero', 'cliente__nome_razao_social']
    list_filter = ['status', 'data_orcamento']
    inlines = [ItemOrcamentoInline]


class ItemPedidoVendaInline(admin.TabularInline):
    model = ItemPedidoVenda
    extra = 1


@admin.register(PedidoVenda)
class PedidoVendaAdmin(admin.ModelAdmin):
    list_display = ['numero', 'cliente', 'vendedor', 'data_pedido', 'status', 'valor_total']
    search_fields = ['numero', 'cliente__nome_razao_social']
    list_filter = ['status', 'data_pedido']
    inlines = [ItemPedidoVendaInline]


class ItemNotaFiscalSaidaInline(admin.TabularInline):
    model = ItemNotaFiscalSaida
    extra = 1


@admin.register(NotaFiscalSaida)
class NotaFiscalSaidaAdmin(admin.ModelAdmin):
    list_display = ['numero_nf', 'cliente', 'data_emissao', 'valor_total']
    search_fields = ['numero_nf', 'cliente__nome_razao_social']
    list_filter = ['data_emissao']
    inlines = [ItemNotaFiscalSaidaInline]


# =============================================================================
# FINANCEIRO
# =============================================================================

@admin.register(CategoriaFinanceira)
class CategoriaFinanceiraAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'tipo', 'grupo_dre', 'ativo']
    search_fields = ['codigo', 'nome']
    list_filter = ['tipo', 'grupo_dre', 'ativo']


@admin.register(CentroCusto)
class CentroCustoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo', 'responsavel', 'ativo']
    search_fields = ['nome', 'responsavel']
    list_filter = ['tipo', 'ativo']


@admin.register(OrcamentoFinanceiro)
class OrcamentoFinanceiroAdmin(admin.ModelAdmin):
    list_display = ['categoria', 'centro_custo', 'ano', 'mes', 'valor_orcado', 'valor_realizado']
    search_fields = ['categoria__nome', 'centro_custo__nome']
    list_filter = ['ano', 'mes', 'categoria__tipo']


class LancamentoExtratoInline(admin.TabularInline):
    model = LancamentoExtrato
    extra = 0


@admin.register(ExtratoBancario)
class ExtratoBancarioAdmin(admin.ModelAdmin):
    list_display = ['conta_bancaria', 'data_arquivo', 'data_importacao', 'processado']
    search_fields = ['conta_bancaria']
    list_filter = ['processado', 'data_arquivo']
    inlines = [LancamentoExtratoInline]


@admin.register(ContaPagar)
class ContaPagarAdmin(admin.ModelAdmin):
    list_display = ['descricao', 'fornecedor', 'data_vencimento', 'valor_original', 'status']
    search_fields = ['descricao', 'fornecedor__nome_razao_social']
    list_filter = ['status', 'data_vencimento', 'categoria']


@admin.register(ContaReceber)
class ContaReceberAdmin(admin.ModelAdmin):
    list_display = ['descricao', 'cliente', 'data_vencimento', 'valor_original', 'status']
    search_fields = ['descricao', 'cliente__nome_razao_social']
    list_filter = ['status', 'data_vencimento', 'categoria']


@admin.register(MovimentoCaixa)
class MovimentoCaixaAdmin(admin.ModelAdmin):
    list_display = ['descricao', 'tipo', 'data', 'valor']
    search_fields = ['descricao']
    list_filter = ['tipo', 'data']


# =============================================================================
# ESTOQUE
# =============================================================================

@admin.register(MovimentacaoEstoque)
class MovimentacaoEstoqueAdmin(admin.ModelAdmin):
    list_display = ['produto', 'tipo', 'quantidade', 'data', 'usuario']
    search_fields = ['produto__descricao', 'motivo']
    list_filter = ['tipo', 'data']


class ItemInventarioInline(admin.TabularInline):
    model = ItemInventario
    extra = 0


@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = ['numero', 'data', 'status', 'usuario']
    search_fields = ['numero']
    list_filter = ['status', 'data']
    inlines = [ItemInventarioInline]


class ItemTransferenciaInline(admin.TabularInline):
    model = ItemTransferencia
    extra = 1


@admin.register(TransferenciaEstoque)
class TransferenciaEstoqueAdmin(admin.ModelAdmin):
    list_display = ['numero', 'origem', 'destino', 'data', 'status']
    search_fields = ['numero', 'origem', 'destino']
    list_filter = ['status', 'data']
    inlines = [ItemTransferenciaInline]