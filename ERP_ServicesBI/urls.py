# -*- coding: utf-8 -*-
"""
ERP SERVICES BI - URLS COMPLETAS (PADRONIZADAS)
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

    # VENDEDORES
    path('cadastro/vendedores/', views.vendedor_list, name='vendedor_list'),
    path('cadastro/vendedores/novo/', views.vendedor_add, name='vendedor_add'),
    path('cadastro/vendedores/editar/<int:pk>/', views.vendedor_edit, name='vendedor_edit'),
    path('cadastro/vendedores/excluir/<int:pk>/', views.vendedor_delete, name='vendedor_delete'),

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

    # CONDIÇÕES DE PAGAMENTO
    path('cadastro/condicoes-pagamento/', views.condicao_pagamento_list, name='condicao_pagamento_list'),
    path('cadastro/condicoes-pagamento/nova/', views.condicao_pagamento_add, name='condicao_pagamento_add'),
    path('cadastro/condicoes-pagamento/editar/<int:pk>/', views.condicao_pagamento_edit, name='condicao_pagamento_edit'),
    path('cadastro/condicoes-pagamento/excluir/<int:pk>/', views.condicao_pagamento_delete, name='condicao_pagamento_delete'),

    # FORMAS DE PAGAMENTO
    path('cadastro/formas-pagamento/', views.forma_pagamento_list, name='forma_pagamento_list'),
    path('cadastro/formas-pagamento/nova/', views.forma_pagamento_add, name='forma_pagamento_add'),
    path('cadastro/formas-pagamento/editar/<int:pk>/', views.forma_pagamento_edit, name='forma_pagamento_edit'),
    path('cadastro/formas-pagamento/excluir/<int:pk>/', views.forma_pagamento_delete, name='forma_pagamento_delete'),

    # =============================================================================
    # COMPRAS
    # =============================================================================
    
    # PEDIDOS DE COMPRA (PADRONIZADO COM UNDERLINE)
    path('compras/pedidos/', views.pedido_compra_list, name='pedido_compra_list'),
    path('compras/pedidos/novo/', views.pedido_compra_add, name='pedido_compra_add'),
    path('compras/pedidos/editar/<int:pk>/', views.pedido_compra_edit, name='pedido_compra_edit'),
    path('compras/pedidos/excluir/<int:pk>/', views.pedido_compra_delete, name='pedido_compra_delete'),
    path('compras/pedidos/<int:pedido_pk>/itens/novo/', views.pedido_compra_item_add, name='pedido_compra_item_add'),
    path('compras/pedidos/<int:pedido_pk>/itens/<int:item_pk>/editar/', views.pedido_compra_item_edit, name='pedido_compra_item_edit'),
    path('compras/pedidos/itens/excluir/<int:pk>/', views.pedido_compra_item_delete, name='pedido_compra_item_delete'),
    path('compras/pedidos/<int:pk>/gerar-nfe/', views.pedido_compra_gerar_nfe, name='pedido_compra_gerar_nfe'),

    # NOTAS FISCAIS DE ENTRADA (PADRONIZADO COM UNDERLINE)
    path('compras/notas-fiscais/', views.nota_fiscal_entrada_list, name='nota_fiscal_entrada_list'),
    path('compras/notas-fiscais/nova/', views.nota_fiscal_entrada_add, name='nota_fiscal_entrada_add'),
    path('compras/notas-fiscais/editar/<int:pk>/', views.nota_fiscal_entrada_edit, name='nota_fiscal_entrada_edit'),
    path('compras/notas-fiscais/excluir/<int:pk>/', views.nota_fiscal_entrada_delete, name='nota_fiscal_entrada_delete'),
    path('compras/notas-fiscais/<int:nota_pk>/item/novo/', views.nota_fiscal_entrada_item_add, name='nota_fiscal_entrada_item_add'),
    path('compras/notas-fiscais/item/excluir/<int:pk>/', views.nota_fiscal_entrada_item_delete, name='nota_fiscal_entrada_item_delete'),

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
    path('vendas/pedidos/', views.pedido_venda_list, name='pedido_venda_list'),
    path('vendas/pedidos/novo/', views.pedido_venda_add, name='pedido_venda_add'),
    path('vendas/pedidos/editar/<int:pk>/', views.pedido_venda_edit, name='pedido_venda_edit'),
    path('vendas/pedidos/excluir/<int:pk>/', views.pedido_venda_delete, name='pedido_venda_delete'),
    path('vendas/pedidos/<int:pedido_pk>/item/novo/', views.pedido_venda_item_add, name='pedido_venda_item_add'),
    path('vendas/pedidos/item/excluir/<int:pk>/', views.pedido_venda_item_delete, name='pedido_venda_item_delete'),
    path('vendas/pedidos/<int:pk>/gerar-nfs/', views.pedido_venda_gerar_nfe, name='pedido_venda_gerar_nfs'),

    # NOTAS FISCAIS DE SAÍDA
    path('vendas/notas-fiscais/', views.nota_fiscal_saida_list, name='nota_fiscal_saida_list'),
    path('vendas/notas-fiscais/nova/', views.nota_fiscal_saida_add, name='nota_fiscal_saida_add'),
    path('vendas/notas-fiscais/editar/<int:pk>/', views.nota_fiscal_saida_edit, name='nota_fiscal_saida_edit'),
    path('vendas/notas-fiscais/excluir/<int:pk>/', views.nota_fiscal_saida_delete, name='nota_fiscal_saida_delete'),
    path('vendas/notas-fiscais/<int:nota_pk>/item/novo/', views.nota_fiscal_saida_item_add, name='nota_fiscal_saida_item_add'),
    path('vendas/notas-fiscais/item/excluir/<int:pk>/', views.nota_fiscal_saida_item_delete, name='nota_fiscal_saida_item_delete'),

    # RELATÓRIOS VENDAS
    path('vendas/relatorios/', views.relatorio_vendas, name='relatorio_vendas'),

    # =============================================================================
    # FINANCEIRO (TODOS PADRONIZADOS COM UNDERLINE)
    # =============================================================================
    
    # CATEGORIAS FINANCEIRAS
    path('financeiro/categorias/', views.categoria_financeira_list, name='categoria_financeira_list'),
    path('financeiro/categorias/nova/', views.categoria_financeira_add, name='categoria_financeira_add'),
    path('financeiro/categorias/editar/<int:pk>/', views.categoria_financeira_edit, name='categoria_financeira_edit'),
    path('financeiro/categorias/excluir/<int:pk>/', views.categoria_financeira_delete, name='categoria_financeira_delete'),

    # CENTROS DE CUSTO
    path('financeiro/centros-custo/', views.centro_custo_list, name='centro_custo_list'),
    path('financeiro/centros-custo/novo/', views.centro_custo_add, name='centro_custo_add'),
    path('financeiro/centros-custo/editar/<int:pk>/', views.centro_custo_edit, name='centro_custo_edit'),
    path('financeiro/centros-custo/excluir/<int:pk>/', views.centro_custo_delete, name='centro_custo_delete'),

    # ORÇAMENTO FINANCEIRO
    path('financeiro/orcamentos/', views.orcamento_financeiro_list, name='orcamento_financeiro_list'),
    path('financeiro/orcamentos/novo/', views.orcamento_financeiro_add, name='orcamento_financeiro_add'),
    path('financeiro/orcamentos/editar/<int:pk>/', views.orcamento_financeiro_edit, name='orcamento_financeiro_edit'),
    path('financeiro/orcamentos/excluir/<int:pk>/', views.orcamento_financeiro_delete, name='orcamento_financeiro_delete'),

    # CONTAS A RECEBER
    path('financeiro/contas-receber/', views.conta_receber_list, name='conta_receber_list'),
    path('financeiro/contas-receber/nova/', views.conta_receber_add, name='conta_receber_add'),
    path('financeiro/contas-receber/editar/<int:pk>/', views.conta_receber_edit, name='conta_receber_edit'),
    path('financeiro/contas-receber/excluir/<int:pk>/', views.conta_receber_delete, name='conta_receber_delete'),
    path('financeiro/contas-receber/baixar/<int:pk>/', views.conta_receber_baixar, name='conta_receber_baixar'),

    # CONTAS A PAGAR
    path('financeiro/contas-pagar/', views.conta_pagar_list, name='conta_pagar_list'),
    path('financeiro/contas-pagar/nova/', views.conta_pagar_add, name='conta_pagar_add'),
    path('financeiro/contas-pagar/editar/<int:pk>/', views.conta_pagar_edit, name='conta_pagar_edit'),
    path('financeiro/contas-pagar/excluir/<int:pk>/', views.conta_pagar_delete, name='conta_pagar_delete'),
    path('financeiro/contas-pagar/baixar/<int:pk>/', views.conta_pagar_baixar, name='conta_pagar_baixar'),

    # FLUXO DE CAIXA
    path('financeiro/fluxo-caixa/', views.fluxo_caixa, name='fluxo_caixa'),
    path('financeiro/fluxo-caixa/lancamento/', views.movimentacao_caixa_add, name='movimentacao_caixa_add'),

    # CONCILIAÇÃO BANCÁRIA
    path('financeiro/conciliacao/', views.conciliacao_list, name='conciliacao_list'),
    path('financeiro/conciliacao/novo/', views.conciliacao_add, name='conciliacao_add'),
    path('financeiro/conciliacao/editar/<int:pk>/', views.conciliacao_edit, name='conciliacao_edit'),
    path('financeiro/conciliacao/excluir/<int:pk>/', views.conciliacao_delete, name='conciliacao_delete'),

   
    # =============================================================================
    # DRE - ADICIONAR ESTAS ROTAS
    # =============================================================================

    # DRE Gerencial
    path('dre/', views.dre_gerencial, name='dre_gerencial'),
    path('dre/configuracao/', views.dre_configuracao, name='dre_configuracao'),
    path('dre/configuracao/<int:empresa_id>/', views.dre_configuracao, name='dre_configuracao_empresa'),
    path('dre/alterar-regime/', views.dre_alterar_regime, name='dre_alterar_regime'),
    path('dre/exportar/pdf/', views.dre_exportar_pdf, name='dre_exportar_pdf'),
    path('dre/exportar/excel/', views.dre_exportar_excel, name='dre_exportar_excel'),
    path('dre/salvar/', views.dre_salvar_relatorio, name='dre_salvar_relatorio'),
    path('dre/historico/', views.dre_historico, name='dre_historico'),
    path('dre/relatorio/<int:pk>/', views.dre_visualizar_relatorio, name='dre_visualizar_relatorio'),
    path('dre/comparativo/', views.dre_comparativo, name='dre_comparativo'),

    # =============================================================================
    # ESTOQUE (PADRONIZADOS COM UNDERLINE)
    # =============================================================================
    
    # MOVIMENTAÇÕES
    path('estoque/movimentacoes/', views.movimentacao_estoque_list, name='movimentacao_estoque_list'),
    path('estoque/movimentacoes/nova/', views.movimentacao_estoque_add, name='movimentacao_estoque_add'),
    path('estoque/movimentacoes/editar/<int:pk>/', views.movimentacao_estoque_edit, name='movimentacao_estoque_edit'),
    path('estoque/movimentacoes/excluir/<int:pk>/', views.movimentacao_estoque_delete, name='movimentacao_estoque_delete'),

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