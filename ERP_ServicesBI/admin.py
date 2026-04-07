# -*- coding: utf-8 -*-
from django.contrib import admin
from .models import (
    # Cadastros
    Empresa, Cliente, Fornecedor, Produto, CategoriaProduto,
    Vendedor, CondicaoPagamento, FormaPagamento, Deposito,

    # Compras
    PedidoCompra, ItemPedidoCompra, PedidoAprovacao, RegraAprovacao,
    NotaFiscalEntrada, ItemNotaFiscalEntrada,
    CotacaoMae, ItemSolicitado, CotacaoFornecedor, ItemCotacaoFornecedor,

    # Vendas
    Orcamento, ItemOrcamento, PedidoVenda, ItemPedidoVenda,
    NotaFiscalSaida, ItemNotaFiscalSaida,

    # Financeiro
    ContaPagar, ContaReceber, MovimentoCaixa,
    CategoriaFinanceira, CentroCusto, OrcamentoFinanceiro,
    ExtratoBancario, LancamentoExtrato, ContaBancaria,
    ConfiguracaoDRE, LinhaDRE, RelatorioDRE, ItemRelatorioDRE,

    # Estoque
    MovimentacaoEstoque, Inventario, ItemInventario,
    TransferenciaEstoque, ItemTransferencia, SaldoEstoque,
    EntradaNFE, ItemEntradaNFE,

    # Planejado x Realizado
    Projeto, OrcamentoProjeto,
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


@admin.register(Vendedor)
class VendedorAdmin(admin.ModelAdmin):
    list_display = ['nome', 'apelido', 'email', 'comissao_padrao', 'ativo']
    search_fields = ['nome', 'apelido', 'email', 'cpf']
    list_filter = ['ativo']


@admin.register(CategoriaProduto)
class CategoriaProdutoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'ativo']
    search_fields = ['nome']


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'descricao', 'categoria', 'preco_venda', 'estoque_atual', 'estoque_minimo', 'ativo']
    search_fields = ['codigo', 'descricao']
    list_filter = ['ativo', 'categoria', 'unidade']


@admin.register(CondicaoPagamento)
class CondicaoPagamentoAdmin(admin.ModelAdmin):
    list_display = ['descricao', 'parcelas', 'periodicidade', 'ativo']
    search_fields = ['descricao']
    list_filter = ['periodicidade', 'ativo']


@admin.register(FormaPagamento)
class FormaPagamentoAdmin(admin.ModelAdmin):
    list_display = ['descricao', 'tipo', 'ativo']
    search_fields = ['descricao']
    list_filter = ['tipo', 'ativo']


@admin.register(Deposito)
class DepositoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'responsavel', 'ativo']
    search_fields = ['codigo', 'nome', 'responsavel']
    list_filter = ['ativo']


# =============================================================================
# COMPRAS
# =============================================================================

class ItemPedidoCompraInline(admin.TabularInline):
    model = ItemPedidoCompra
    extra = 1


@admin.register(PedidoCompra)
class PedidoCompraAdmin(admin.ModelAdmin):
    list_display = ['numero', 'fornecedor', 'data_pedido', 'status', 'valor_total', 'nivel_aprovacao_atual']
    search_fields = ['numero', 'fornecedor__nome_razao_social']
    list_filter = ['status', 'data_pedido']
    inlines = [ItemPedidoCompraInline]


@admin.register(PedidoAprovacao)
class PedidoAprovacaoAdmin(admin.ModelAdmin):
    list_display = ['pedido', 'usuario', 'acao', 'nivel', 'data']
    list_filter = ['acao', 'nivel', 'data']
    search_fields = ['pedido__numero', 'usuario__username']


@admin.register(RegraAprovacao)
class RegraAprovacaoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'valor_minimo', 'valor_maximo', 'nivel', 'ativo']
    list_filter = ['nivel', 'ativo']
    search_fields = ['nome']


class ItemNotaFiscalEntradaInline(admin.TabularInline):
    model = ItemNotaFiscalEntrada
    extra = 1


@admin.register(NotaFiscalEntrada)
class NotaFiscalEntradaAdmin(admin.ModelAdmin):
    list_display = ['numero_nf', 'fornecedor', 'data_recebimento', 'valor_total', 'status']  # ✅ CORRIGIDO: data_entrada → data_recebimento
    search_fields = ['numero_nf', 'fornecedor__nome_razao_social']
    list_filter = ['status', 'data_recebimento']  # ✅ CORRIGIDO: data_entrada → data_recebimento
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
    list_display = ['numero_nf', 'cliente', 'data_emissao', 'valor_total', 'status']  # ✅ Adicionado status
    search_fields = ['numero_nf', 'cliente__nome_razao_social']
    list_filter = ['status', 'data_emissao']  # ✅ Adicionado status
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


@admin.register(ContaBancaria)
class ContaBancariaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'banco', 'tipo', 'saldo_atual', 'ativa']
    search_fields = ['nome', 'banco', 'agencia', 'conta']
    list_filter = ['tipo', 'ativa']


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
# DRE
# =============================================================================

@admin.register(ConfiguracaoDRE)
class ConfiguracaoDREAdmin(admin.ModelAdmin):
    list_display = ['empresa', 'regime_tributario', 'atividade_principal', 'ativo']
    list_filter = ['regime_tributario', 'ativo']


@admin.register(LinhaDRE)
class LinhaDREAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'descricao', 'tipo', 'natureza', 'ordem', 'visivel']
    list_filter = ['tipo', 'natureza', 'visivel']
    search_fields = ['codigo', 'descricao']


@admin.register(RelatorioDRE)
class RelatorioDREAdmin(admin.ModelAdmin):
    list_display = ['empresa', 'data_inicio', 'data_fim', 'regime_tributario', 'status', 'gerado_em']
    list_filter = ['status', 'regime_tributario', 'gerado_em']


@admin.register(ItemRelatorioDRE)
class ItemRelatorioDREAdmin(admin.ModelAdmin):
    list_display = ['relatorio', 'linha_dre', 'valor', 'percentual_vertical']
    list_filter = ['linha_dre__natureza']


# =============================================================================
# ESTOQUE
# =============================================================================

@admin.register(MovimentacaoEstoque)
class MovimentacaoEstoqueAdmin(admin.ModelAdmin):
    list_display = ['produto', 'tipo', 'quantidade', 'data', 'usuario', 'valor_total']
    search_fields = ['produto__descricao', 'motivo']
    list_filter = ['tipo', 'data']


class ItemInventarioInline(admin.TabularInline):
    model = ItemInventario
    extra = 0


@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = ['numero', 'data', 'status', 'deposito', 'usuario']  # ✅ Adicionado deposito
    search_fields = ['numero']
    list_filter = ['status', 'data', 'deposito']  # ✅ Adicionado deposito
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


@admin.register(SaldoEstoque)
class SaldoEstoqueAdmin(admin.ModelAdmin):
    list_display = ['produto', 'deposito', 'quantidade', 'quantidade_reservada', 'quantidade_disponivel']
    search_fields = ['produto__descricao', 'deposito__nome']
    list_filter = ['deposito']


class ItemEntradaNFEInline(admin.TabularInline):
    model = ItemEntradaNFE
    extra = 1


@admin.register(EntradaNFE)
class EntradaNFEAdmin(admin.ModelAdmin):
    list_display = ['numero_nfe', 'fornecedor', 'deposito', 'data_entrada', 'valor_total', 'status']
    search_fields = ['numero_nfe', 'fornecedor__nome_razao_social']
    list_filter = ['status', 'data_entrada', 'deposito']
    inlines = [ItemEntradaNFEInline]


@admin.register(ItemEntradaNFE)
class ItemEntradaNFEAdmin(admin.ModelAdmin):
    list_display = ['entrada', 'produto', 'quantidade', 'valor_unitario', 'valor_total']
    search_fields = ['produto__descricao', 'entrada__numero_nfe']


# =============================================================================
# COTAÇÃO COMPARATIVA
# =============================================================================

class ItemSolicitadoInline(admin.TabularInline):
    model = ItemSolicitado
    extra = 1
    fields = ['produto', 'descricao_manual', 'quantidade', 'unidade_medida']


@admin.register(CotacaoMae)
class CotacaoMaeAdmin(admin.ModelAdmin):
    list_display = ['numero', 'titulo', 'solicitante', 'setor', 'status', 'data_solicitacao']
    list_filter = ['status', 'setor', 'data_solicitacao']
    search_fields = ['numero', 'titulo', 'observacoes']
    inlines = [ItemSolicitadoInline]
    readonly_fields = ['numero', 'created_at', 'updated_at']


class ItemCotacaoFornecedorInline(admin.TabularInline):
    model = ItemCotacaoFornecedor
    extra = 0
    fields = ['item_solicitado', 'descricao_fornecedor', 'quantidade', 'preco_unitario', 'preco_total', 'disponivel']


@admin.register(CotacaoFornecedor)
class CotacaoFornecedorAdmin(admin.ModelAdmin):
    list_display = ['fornecedor', 'cotacao_mae', 'status', 'valor_total_liquido', 'data_recebimento']
    list_filter = ['status', 'data_recebimento']
    search_fields = ['fornecedor__nome_fantasia', 'cotacao_mae__numero']
    inlines = [ItemCotacaoFornecedorInline]


@admin.register(ItemSolicitado)
class ItemSolicitadoAdmin(admin.ModelAdmin):
    list_display = ['cotacao_mae', 'descricao_display', 'quantidade', 'unidade_medida']
    list_filter = ['cotacao_mae__status']
    search_fields = ['produto__descricao', 'descricao_manual']


@admin.register(ItemCotacaoFornecedor)
class ItemCotacaoFornecedorAdmin(admin.ModelAdmin):
    list_display = ['cotacao_fornecedor', 'descricao_fornecedor', 'preco_unitario', 'preco_total', 'disponivel']
    list_filter = ['disponivel', 'match_automatico']


# =============================================================================
# PLANEJADO X REALIZADO
# =============================================================================

@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'cliente', 'status', 'data_inicio']
    search_fields = ['codigo', 'nome', 'cliente__nome_razao_social']
    list_filter = ['status']


@admin.register(OrcamentoProjeto)
class OrcamentoProjetoAdmin(admin.ModelAdmin):
    list_display = ['projeto', 'ano', 'mes', 'valor_planejado', 'valor_realizado', 'variacao']
    list_filter = ['ano', 'mes']
    search_fields = ['projeto__nome']