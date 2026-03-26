# -*- coding: utf-8 -*-
"""
ERP SERVICES BI - URLS COMPLETAS
"""
from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

app_name = 'ERP_ServicesBI'

urlpatterns = [
    # =============================================================================
    # LOGIN
    # =============================================================================
    path('login/', auth_views.LoginView.as_view(template_name='ERP_ServicesBI/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='ERP_ServicesBI:dashboard'), name='logout'),

    # =============================================================================
    # DASHBOARD
    # =============================================================================
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard_alt'),

    # =============================================================================
    # CADASTRO
    # =============================================================================

    # CLIENTES
    path('cadastro/clientes/', views.cliente_list, name='cliente_list'),
    path('cadastro/clientes/novo/', views.cliente_add, name='cliente_add'),
    path('cadastro/clientes/editar/<int:pk>/', views.cliente_edit, name='cliente_edit'),
    path('cadastro/clientes/excluir/<int:pk>/', views.cliente_delete, name='cliente_delete'),

    # EMPRESAS
    path('cadastro/empresas/', views.empresa_list, name='empresa_list'),
    path('cadastro/empresas/nova/', views.empresa_add, name='empresa_add'),
    path('cadastro/empresas/editar/<int:pk>/', views.empresa_edit, name='empresa_edit'),
    path('cadastro/empresas/excluir/<int:pk>/', views.empresa_delete, name='empresa_delete'),

    # FORNECEDORES
    path('cadastro/fornecedores/', views.fornecedor_list, name='fornecedor_list'),
    path('cadastro/fornecedores/novo/', views.fornecedor_add, name='fornecedor_add'),
    path('cadastro/fornecedores/editar/<int:pk>/', views.fornecedor_edit, name='fornecedor_edit'),
    path('cadastro/fornecedores/excluir/<int:pk>/', views.fornecedor_delete, name='fornecedor_delete'),

    # CATEGORIAS
    path('cadastro/categorias/', views.categoria_list, name='categoria_list'),
    path('cadastro/categorias/nova/', views.categoria_add, name='categoria_add'),
    path('cadastro/categorias/editar/<int:pk>/', views.categoria_edit, name='categoria_edit'),
    path('cadastro/categorias/excluir/<int:pk>/', views.categoria_delete, name='categoria_delete'),
    path('ajax/categoria/criar/', views.categoria_create_ajax, name='categoria_create_ajax'),
    path('ajax/categoria/excluir/<int:pk>/', views.categoria_delete_ajax, name='categoria_delete_ajax'),

    # PRODUTOS
    path('cadastro/produtos/', views.produto_list, name='produto_list'),
    path('cadastro/produtos/novo/', views.produto_add, name='produto_add'),
    path('cadastro/produtos/editar/<int:pk>/', views.produto_edit, name='produto_edit'),
    path('cadastro/produtos/excluir/<int:pk>/', views.produto_delete, name='produto_delete'),
    path('api/produto/<int:pk>/json/', views.produto_json, name='produto_json'),

    # =============================================================================
    # COMPRAS
    # =============================================================================
    
    # PEDIDOS DE COMPRA
    path('compras/pedidos/', views.pedidocompra_list, name='pedidocompra_list'),
    path('compras/pedidos/novo/', views.pedidocompra_add, name='pedidocompra_add'),
    path('compras/pedidos/editar/<int:pk>/', views.pedidocompra_edit, name='pedidocompra_edit'),
    path('compras/pedidos/excluir/<int:pk>/', views.pedidocompra_delete, name='pedidocompra_delete'),
    path('compras/pedidos/<int:pedido_pk>/itens/novo/', views.pedidocompra_item_add, name='pedidocompra_item_add'),
    path('compras/pedidos/<int:pedido_pk>/itens/<int:item_pk>/editar/', views.pedidocompra_item_edit, name='pedidocompra_item_edit'),
    path('compras/pedidos/itens/excluir/<int:pk>/', views.pedidocompra_item_delete, name='pedidocompra_item_delete'),
    path('compras/pedidos/<int:pk>/gerar-nfe/', views.pedidocompra_gerar_nfe, name='pedidocompra_gerar_nfe'),

    # NOTAS FISCAIS DE ENTRADA
    path('compras/notas-fiscais/', views.notafiscalentrada_list, name='notafiscalentrada_list'),
    path('compras/notas-fiscais/nova/', views.notafiscalentrada_add, name='notafiscalentrada_add'),
    path('compras/notas-fiscais/editar/<int:pk>/', views.notafiscalentrada_edit, name='notafiscalentrada_edit'),
    path('compras/notas-fiscais/excluir/<int:pk>/', views.notafiscalentrada_delete, name='notafiscalentrada_delete'),
    path('compras/notas-fiscais/<int:nota_pk>/item/novo/', views.notafiscalentrada_item_add, name='notafiscalentrada_item_add'),
    path('compras/notas-fiscais/item/excluir/<int:pk>/', views.notafiscalentrada_item_delete, name='notafiscalentrada_item_delete'),

    # RELATÓRIOS COMPRAS
    path('compras/relatorios/', views.relatorio_compras, name='relatorio_compras'),

    # =============================================================================
    # COTAÇÃO COMPARATIVA (WIZARD)
    # =============================================================================
    
    # Lista e Wizard
    path('compras/cotacoes/', views.cotacao_lista, name='cotacao_lista'),
    path('compras/cotacoes/nova/', views.cotacao_wizard, name='cotacao_wizard'),
    path('compras/cotacoes/<int:pk>/', views.cotacao_wizard, name='cotacao_wizard_edit'),
    
    # APIs AJAX - Salvar Dados
    path('api/cotacao/salvar-dados/', views.cotacao_salvar_dados, name='cotacao_salvar_dados_novo'),
    path('api/cotacao/<int:pk>/salvar-dados/', views.cotacao_salvar_dados, name='cotacao_salvar_dados'),
    path('api/cotacao/<int:pk>/salvar-itens/', views.cotacao_salvar_itens, name='cotacao_salvar_itens'),
    
    # APIs AJAX - Fornecedores
    path('api/cotacao/<int:pk>/importar-fornecedor/', views.cotacao_importar_fornecedor, name='cotacao_importar_fornecedor'),
    path('api/cotacao/<int:pk>/remover-fornecedor/<int:fornecedor_pk>/', views.cotacao_remover_fornecedor, name='cotacao_remover_fornecedor'),
    
    # APIs AJAX - Comparar e Selecionar
    path('api/cotacao/<int:pk>/calcular-sugestoes/', views.cotacao_calcular_sugestoes, name='cotacao_calcular_sugestoes'),
    path('api/cotacao/<int:pk>/salvar-selecao/', views.cotacao_salvar_selecao, name='cotacao_salvar_selecao'),
    
    # APIs AJAX - Gerar Pedidos
    path('api/cotacao/<int:pk>/gerar-pedidos/', views.cotacao_gerar_pedidos, name='cotacao_gerar_pedidos'),
    path('api/cotacao/<int:pk>/excluir/', views.cotacao_excluir, name='cotacao_excluir'),
    
    # Utilitários
    path('api/cotacao/<int:pk>/copiar-lista-email/', views.cotacao_copiar_lista_email, name='cotacao_copiar_lista_email'),
    path('api/cotacao/<int:pk>/copiar-lista-whatsapp/', views.cotacao_copiar_lista_whatsapp, name='cotacao_copiar_lista_whatsapp'),

    # =============================================================================
    # VENDAS
    # =============================================================================
    
    # ORÇAMENTOS
    path('vendas/orcamentos/', views.orcamento_list, name='orcamento_list'),
    path('vendas/orcamentos/novo/', views.orcamento_add, name='orcamento_add'),
    path('vendas/orcamentos/editar/<int:pk>/', views.orcamento_edit, name='orcamento_edit'),
    path('vendas/orcamentos/excluir/<int:pk>/', views.orcamento_delete, name='orcamento_delete'),
    path('vendas/orcamentos/<int:orcamento_pk>/item/novo/', views.orcamento_item_add, name='orcamento_item_add'),
    path('vendas/orcamentos/item/excluir/<int:pk>/', views.orcamento_item_delete, name='orcamento_item_delete'),
    path('vendas/orcamentos/<int:pk>/gerar-pedido/', views.orcamento_gerar_pedido, name='orcamento_gerar_pedido'),

    # PEDIDOS DE VENDA
    path('vendas/pedidos/', views.pedidovenda_list, name='pedidovenda_list'),
    path('vendas/pedidos/novo/', views.pedidovenda_add, name='pedidovenda_add'),
    path('vendas/pedidos/editar/<int:pk>/', views.pedidovenda_edit, name='pedidovenda_edit'),
    path('vendas/pedidos/excluir/<int:pk>/', views.pedidovenda_delete, name='pedidovenda_delete'),
    path('vendas/pedidos/<int:pedido_pk>/item/novo/', views.pedidovenda_item_add, name='pedidovenda_item_add'),
    path('vendas/pedidos/item/excluir/<int:pk>/', views.pedidovenda_item_delete, name='pedidovenda_item_delete'),
    path('vendas/pedidos/<int:pk>/gerar-nfs/', views.pedidovenda_gerar_nfe, name='pedidovenda_gerar_nfs'),

    # NOTAS FISCAIS DE SAÍDA
    path('vendas/notas-fiscais/', views.notafiscalsaida_list, name='notafiscalsaida_list'),
    path('vendas/notas-fiscais/nova/', views.notafiscalsaida_add, name='notafiscalsaida_add'),
    path('vendas/notas-fiscais/editar/<int:pk>/', views.notafiscalsaida_edit, name='notafiscalsaida_edit'),
    path('vendas/notas-fiscais/excluir/<int:pk>/', views.notafiscalsaida_delete, name='notafiscalsaida_delete'),
    path('vendas/notas-fiscais/<int:nota_pk>/item/novo/', views.notafiscalsaida_item_add, name='notafiscalsaida_item_add'),
    path('vendas/notas-fiscais/item/excluir/<int:pk>/', views.notafiscalsaida_item_delete, name='notafiscalsaida_item_delete'),

    # RELATÓRIOS VENDAS
    path('vendas/relatorios/', views.relatorio_vendas, name='relatorio_vendas'),

    # =============================================================================
    # FINANCEIRO
    # =============================================================================
    
    # CATEGORIAS FINANCEIRAS
    path('financeiro/categorias/', views.categoriafinanceira_list, name='categoriafinanceira_list'),
    path('financeiro/categorias/nova/', views.categoriafinanceira_add, name='categoriafinanceira_add'),
    path('financeiro/categorias/editar/<int:pk>/', views.categoriafinanceira_edit, name='categoriafinanceira_edit'),
    path('financeiro/categorias/excluir/<int:pk>/', views.categoriafinanceira_delete, name='categoriafinanceira_delete'),

    # CENTROS DE CUSTO
    path('financeiro/centros-custo/', views.centrocusto_list, name='centrocusto_list'),
    path('financeiro/centros-custo/novo/', views.centrocusto_add, name='centrocusto_add'),
    path('financeiro/centros-custo/editar/<int:pk>/', views.centrocusto_edit, name='centrocusto_edit'),
    path('financeiro/centros-custo/excluir/<int:pk>/', views.centrocusto_delete, name='centrocusto_delete'),

    # ORÇAMENTO FINANCEIRO
    path('financeiro/orcamentos/', views.orcamentofinanceiro_list, name='orcamentofinanceiro_list'),
    path('financeiro/orcamentos/novo/', views.orcamentofinanceiro_add, name='orcamentofinanceiro_add'),
    path('financeiro/orcamentos/editar/<int:pk>/', views.orcamentofinanceiro_edit, name='orcamentofinanceiro_edit'),
    path('financeiro/orcamentos/excluir/<int:pk>/', views.orcamentofinanceiro_delete, name='orcamentofinanceiro_delete'),

    # CONTAS A RECEBER
    path('financeiro/contas-receber/', views.contareceber_list, name='contareceber_list'),
    path('financeiro/contas-receber/nova/', views.contareceber_add, name='contareceber_add'),
    path('financeiro/contas-receber/editar/<int:pk>/', views.contareceber_edit, name='contareceber_edit'),
    path('financeiro/contas-receber/excluir/<int:pk>/', views.contareceber_delete, name='contareceber_delete'),
    path('financeiro/contas-receber/baixar/<int:pk>/', views.contareceber_baixar, name='contareceber_baixar'),

    # CONTAS A PAGAR
    path('financeiro/contas-pagar/', views.contapagar_list, name='contapagar_list'),
    path('financeiro/contas-pagar/nova/', views.contapagar_add, name='contapagar_add'),
    path('financeiro/contas-pagar/editar/<int:pk>/', views.contapagar_edit, name='contapagar_edit'),
    path('financeiro/contas-pagar/excluir/<int:pk>/', views.contapagar_delete, name='contapagar_delete'),
    path('financeiro/contas-pagar/baixar/<int:pk>/', views.contapagar_baixar, name='contapagar_baixar'),

    # FLUXO DE CAIXA
    path('financeiro/fluxo-caixa/', views.fluxo_caixa, name='fluxo_caixa'),
    path('financeiro/fluxo-caixa/lancamento/', views.movimentocaixa_add, name='movimentocaixa_add'),

    # CONCILIAÇÃO BANCÁRIA
    path('financeiro/conciliacao/', views.conciliacao_list, name='conciliacao_list'),
    path('financeiro/conciliacao/novo/', views.conciliacao_add, name='conciliacao_add'),
    path('financeiro/conciliacao/editar/<int:pk>/', views.conciliacao_edit, name='conciliacao_edit'),
    path('financeiro/conciliacao/excluir/<int:pk>/', views.conciliacao_delete, name='conciliacao_delete'),

    # DRE GERENCIAL
    path('financeiro/dre/', views.dre_gerencial, name='dre_gerencial'),

    # =============================================================================
    # ESTOQUE
    # =============================================================================
    
    # MOVIMENTAÇÕES
    path('estoque/movimentacoes/', views.movimentacaoestoque_list, name='movimentacaoestoque_list'),
    path('estoque/movimentacoes/nova/', views.movimentacaoestoque_add, name='movimentacaoestoque_add'),
    path('estoque/movimentacoes/editar/<int:pk>/', views.movimentacaoestoque_edit, name='movimentacaoestoque_edit'),
    path('estoque/movimentacoes/excluir/<int:pk>/', views.movimentacaoestoque_delete, name='movimentacaoestoque_delete'),

    # INVENTÁRIO
    path('estoque/inventarios/', views.inventario_list, name='inventario_list'),
    path('estoque/inventarios/novo/', views.inventario_add, name='inventario_add'),
    path('estoque/inventarios/editar/<int:pk>/', views.inventario_edit, name='inventario_edit'),
    path('estoque/inventarios/excluir/<int:pk>/', views.inventario_delete, name='inventario_delete'),

    # TRANSFERÊNCIAS
    path('estoque/transferencias/', views.transferencia_list, name='transferencia_list'),
    path('estoque/transferencias/nova/', views.transferencia_add, name='transferencia_add'),
    path('estoque/transferencias/editar/<int:pk>/', views.transferencia_edit, name='transferencia_edit'),
    path('estoque/transferencias/excluir/<int:pk>/', views.transferencia_delete, name='transferencia_delete'),

    # RELATÓRIOS
    path('estoque/relatorio-posicao/', views.relatorio_estoque, name='relatorio_estoque'),
    path('estoque/relatorio-movimentacoes/', views.relatorio_movimentacoes, name='relatorio_movimentacoes'),
]