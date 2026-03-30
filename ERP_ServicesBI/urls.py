# -*- coding: utf-8 -*-
"""
ERP SERVICES BI - URLS COMPLETAS (PADRONIZADAS)
"""
from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

app_name = 'ERP_ServicesBI'

urlpatterns = [
    # LOGIN
    # =============================================================================
    path('login/', auth_views.LoginView.as_view(template_name='ERP_ServicesBI/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='ERP_ServicesBI:dashboard'), name='logout'),

    # DASHBOARD
    # =============================================================================
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard_alt'),

    # CADASTRO
    # =============================================================================
    # MÓDULO: CADASTRO - CLIENTES (URLS UNIFICADAS)
    # =============================================================================
    path('clientes/', views.cliente_manager, name='cliente_manager'),
    path('clientes/novo/', views.cliente_form, name='cliente_form'),
    path('clientes/<int:pk>/editar/', views.cliente_form, name='cliente_form_edit'),
    path('clientes/<int:pk>/excluir/', views.cliente_excluir, name='cliente_excluir'),
    
    # =============================================================================
    # API - CONDIÇÃO E FORMA DE PAGAMENTO (AJAX)
    # =============================================================================
    path('api/condicao-pagamento/criar/', views.api_condicao_pagamento_criar, name='api_condicao_pagamento_criar'),
    path('api/condicao-pagamento/<int:pk>/excluir/', views.api_condicao_pagamento_excluir, name='api_condicao_pagamento_excluir'),
    path('api/forma-pagamento/criar/', views.api_forma_pagamento_criar, name='api_forma_pagamento_criar'),
    path('api/forma-pagamento/<int:pk>/excluir/', views.api_forma_pagamento_excluir, name='api_forma_pagamento_excluir'),

    # =============================================================================
    # MÓDULO: CADASTRO - VENDEDORES (URLS UNIFICADAS - NOVO PADRÃO)
    # =============================================================================
    path('vendedores/', views.vendedor_manager, name='vendedor_manager'),
    path('vendedores/novo/', views.vendedor_form, name='vendedor_form'),
    path('vendedores/<int:pk>/editar/', views.vendedor_form, name='vendedor_form_edit'),
    path('vendedores/<int:pk>/excluir/', views.vendedor_excluir, name='vendedor_excluir'),

    # =============================================================================
    # MÓDULO: CADASTRO - EMPRESAS (URLS UNIFICADAS - NOVO PADRÃO)
    # =============================================================================
    path('cadastro/empresas/', views.empresa_manager, name='empresa_list'),
    path('cadastro/empresas/nova/', views.empresa_form, name='empresa_add'),
    path('cadastro/empresas/editar/<int:pk>/', views.empresa_form, name='empresa_edit'),
    path('cadastro/empresas/excluir/<int:pk>/', views.empresa_excluir, name='empresa_delete'),

    # =============================================================================
    # MÓDULO: CADASTRO - FORNECEDORES (URLS UNIFICADAS - NOVO PADRÃO)
    # =============================================================================
    path('cadastro/fornecedores/', views.fornecedor_manager, name='fornecedor_manager'),
    path('cadastro/fornecedores/novo/', views.fornecedor_form, name='fornecedor_add'),
    path('cadastro/fornecedores/editar/<int:pk>/', views.fornecedor_form, name='fornecedor_edit'),
    path('cadastro/fornecedores/excluir/<int:pk>/', views.fornecedor_excluir, name='fornecedor_delete'),

    # =============================================================================
    # APIs - CATEGORIA PRODUTO (embutida no Produto)
    # =============================================================================
    path('api/categoria-produto/criar/', views.categoria_produto_create_ajax, name='categoria_produto_create_ajax'),
    path('api/categoria-produto/<int:pk>/excluir/', views.categoria_produto_delete_ajax, name='categoria_produto_delete_ajax'),

    # PRODUTOS
    path('cadastro/produtos/', views.produto_manager, name='produto_list'),
    path('cadastro/produtos/novo/', views.produto_form, name='produto_add'),
    path('cadastro/produtos/editar/<int:pk>/', views.produto_form, name='produto_edit'),
    path('cadastro/produtos/excluir/<int:pk>/', views.produto_excluir, name='produto_delete'),
    #path('api/produto/<int:pk>/json/', views.produto_json, name='produto_json'),

    
    # =============================================================================
    # COMPRAS
    # =============================================================================
    
    path('compras/cotacoes/', views.cotacao_manager, name='cotacao_manager'),
    
    # API endpoints para cotações
    path('api/cotacao/salvar/', views.cotacao_salvar_api, name='cotacao_salvar_api'),
    path('api/cotacao/<int:pk>/dados/', views.cotacao_dados_api, name='cotacao_dados_api'),
    path('api/cotacao/<int:pk>/comparativo/', views.cotacao_comparativo_api, name='cotacao_comparativo_api'),
    path('api/cotacao/<int:pk>/excluir/', views.cotacao_excluir_api, name='cotacao_excluir_api'),
    path('api/cotacao/<int:pk>/enviar/', views.cotacao_enviar_api, name='cotacao_enviar_api'),
    path('api/cotacao/<int:pk>/concluir/', views.cotacao_concluir_api, name='cotacao_concluir_api'),
    path('api/cotacao/<int:pk>/importar-cotacao/', views.cotacao_importar_fornecedor, name='cotacao_importar_fornecedor'),
    path('api/cotacao/<int:pk>/fornecedores-importados/', views.cotacao_fornecedores_importados_api, name='cotacao_fornecedores_importados_api'),
    
    # ============================================================================
    # PEDIDOS DE COMPRA
    # ============================================================================
    
    path('compras/pedidos/', views.pedido_compra_manager, name='pedido_compra_manager'),
    
    # API endpoints para pedidos
    path('api/pedido/salvar/', views.pedido_salvar_api, name='pedido_salvar_api'),
    path('api/pedido/<int:pk>/dados/', views.pedido_dados_api, name='pedido_dados_api'),
    path('api/pedido/<int:pk>/dados-simples/', views.pedido_dados_simples_api, name='pedido_dados_simples_api'),
    path('api/pedido/<int:pk>/cancelar/', views.pedido_cancelar_api, name='pedido_cancelar_api'),
    path('api/pedido/<int:pk>/receber/', views.pedido_receber_api, name='pedido_receber_api'),
    path('api/pedido/<int:pk>/dados-recebimento/', views.pedido_dados_recebimento_api, name='pedido_dados_recebimento_api'),
    
    # Delete confirmation (manter template existente)
    path('compras/pedido/<int:pk>/confirmar-delete/', views.pedido_compra_confirm_delete, name='pedido_compra_confirm_delete'),
    
    # ============================================================================
    # NOTAS FISCAIS DE ENTRADA
    # ============================================================================
    
    # Manager principal (novo - unificado)
    path('compras/notas-fiscais/', views.nota_fiscal_entrada_manager, name='nota_fiscal_entrada_manager'),
    
    # API endpoints para notas fiscais
    path('api/nota-fiscal/salvar/', views.nota_fiscal_salvar_api, name='nota_fiscal_salvar_api'),
    path('api/nota-fiscal/<int:pk>/dados/', views.nota_fiscal_dados_api, name='nota_fiscal_dados_api'),
    path('api/nota-fiscal/<int:pk>/excluir/', views.nota_fiscal_excluir_api, name='nota_fiscal_excluir_api'),
    path('api/nota-fiscal/<int:pk>/confirmar/', views.nota_fiscal_confirmar_api, name='nota_fiscal_confirmar_api'),
    
    # Delete confirmation (manter template existente)
    path('compras/nota-fiscal/<int:pk>/confirmar-delete/', views.nota_fiscal_entrada_confirm_delete, name='nota_fiscal_entrada_confirm_delete'),
    
    # ============================================================================
    # RELATÓRIOS DE COMPRAS
    # ============================================================================
    
    path('compras/relatorios/', views.relatorio_compras, name='relatorio_compras'),
    path('api/compras/relatorio/dados/', views.relatorio_compras_dados_api, name='relatorio_compras_dados_api'),
    path('api/compras/relatorio/exportar/', views.relatorio_compras_exportar_api, name='relatorio_compras_exportar_api'),
    
    # ============================================================================
    # FORNECEDORES (INTEGRAÇÃO)
    # ============================================================================
    
    # Usa as mesmas URLs do módulo cadastro, mas referenciadas aqui para facilitar
    # path('cadastro/fornecedores/', views.fornecedor_manager, name='fornecedor_manager'),
    # path('cadastro/fornecedores/novo/', views.fornecedor_form, name='fornecedor_form'),
    
    # ============================================================================
    # APIs AUXILIARES
    # ============================================================================
    
    # Condição de pagamento (já deve existir no cadastro)
    path('api/condicao-pagamento/criar/', views.condicao_pagamento_criar_api, name='condicao_pagamento_criar_api'),
    path('api/condicao-pagamento/<int:pk>/excluir/', views.condicao_pagamento_excluir_api, name='condicao_pagamento_excluir_api'),
    
    # Forma de pagamento (já deve existir no cadastro)
    path('api/forma-pagamento/criar/', views.forma_pagamento_criar_api, name='forma_pagamento_criar_api'),
    path('api/forma-pagamento/<int:pk>/excluir/', views.forma_pagamento_excluir_api, name='forma_pagamento_excluir_api'),


    # =============================================================================
    # VENDAS
    # =============================================================================
    path('vendas/orcamentos/', views.orcamento_list, name='orcamento_list'),
    path('vendas/orcamentos/novo/', views.orcamento_add, name='orcamento_add'),
    path('vendas/orcamentos/editar/<int:pk>/', views.orcamento_edit, name='orcamento_edit'),
    path('vendas/orcamentos/excluir/<int:pk>/', views.orcamento_delete, name='orcamento_delete'),
    path('vendas/orcamentos/<int:orcamento_pk>/item/novo/', views.orcamento_item_add, name='orcamento_item_add'),
    path('vendas/orcamentos/item/excluir/<int:pk>/', views.orcamento_item_delete, name='orcamento_item_delete'),
    path('vendas/orcamentos/<int:pk>/gerar-pedido/', views.orcamento_gerar_pedido, name='orcamento_gerar_pedido'),

    path('vendas/pedidos/', views.pedido_venda_list, name='pedido_venda_list'),
    path('vendas/pedidos/novo/', views.pedido_venda_add, name='pedido_venda_add'),
    path('vendas/pedidos/editar/<int:pk>/', views.pedido_venda_edit, name='pedido_venda_edit'),
    path('vendas/pedidos/excluir/<int:pk>/', views.pedido_venda_delete, name='pedido_venda_delete'),
    path('vendas/pedidos/<int:pedido_pk>/item/novo/', views.pedido_venda_item_add, name='pedido_venda_item_add'),
    path('vendas/pedidos/item/excluir/<int:pk>/', views.pedido_venda_item_delete, name='pedido_venda_item_delete'),
    path('vendas/pedidos/<int:pk>/gerar-nfs/', views.pedido_venda_gerar_nfe, name='pedido_venda_gerar_nfs'),

    path('vendas/notas-fiscais/', views.nota_fiscal_saida_list, name='nota_fiscal_saida_list'),
    path('vendas/notas-fiscais/nova/', views.nota_fiscal_saida_add, name='nota_fiscal_saida_add'),
    path('vendas/notas-fiscais/editar/<int:pk>/', views.nota_fiscal_saida_edit, name='nota_fiscal_saida_edit'),
    path('vendas/notas-fiscais/excluir/<int:pk>/', views.nota_fiscal_saida_delete, name='nota_fiscal_saida_delete'),
    path('vendas/notas-fiscais/<int:nota_pk>/item/novo/', views.nota_fiscal_saida_item_add, name='nota_fiscal_saida_item_add'),
    path('vendas/notas-fiscais/item/excluir/<int:pk>/', views.nota_fiscal_saida_item_delete, name='nota_fiscal_saida_item_delete'),

    path('vendas/relatorios/', views.relatorio_vendas, name='relatorio_vendas'),

    # =============================================================================
    # FINANCEIRO
    # =============================================================================
    path('financeiro/categorias/', views.categoria_financeira_list, name='categoria_financeira_list'),
    path('financeiro/categorias/nova/', views.categoria_financeira_add, name='categoria_financeira_add'),
    path('financeiro/categorias/editar/<int:pk>/', views.categoria_financeira_edit, name='categoria_financeira_edit'),
    path('financeiro/categorias/excluir/<int:pk>/', views.categoria_financeira_delete, name='categoria_financeira_delete'),

    path('financeiro/centros-custo/', views.centro_custo_list, name='centro_custo_list'),
    path('financeiro/centros-custo/novo/', views.centro_custo_add, name='centro_custo_add'),
    path('financeiro/centros-custo/editar/<int:pk>/', views.centro_custo_edit, name='centro_custo_edit'),
    path('financeiro/centros-custo/excluir/<int:pk>/', views.centro_custo_delete, name='centro_custo_delete'),

    path('financeiro/orcamentos/', views.orcamento_financeiro_list, name='orcamento_financeiro_list'),
    path('financeiro/orcamentos/novo/', views.orcamento_financeiro_add, name='orcamento_financeiro_add'),
    path('financeiro/orcamentos/editar/<int:pk>/', views.orcamento_financeiro_edit, name='orcamento_financeiro_edit'),
    path('financeiro/orcamentos/excluir/<int:pk>/', views.orcamento_financeiro_delete, name='orcamento_financeiro_delete'),

    path('financeiro/contas-receber/', views.conta_receber_list, name='conta_receber_list'),
    path('financeiro/contas-receber/nova/', views.conta_receber_add, name='conta_receber_add'),
    path('financeiro/contas-receber/editar/<int:pk>/', views.conta_receber_edit, name='conta_receber_edit'),
    path('financeiro/contas-receber/excluir/<int:pk>/', views.conta_receber_delete, name='conta_receber_delete'),
    path('financeiro/contas-receber/baixar/<int:pk>/', views.conta_receber_baixar, name='conta_receber_baixar'),

    path('financeiro/contas-pagar/', views.conta_pagar_list, name='conta_pagar_list'),
    path('financeiro/contas-pagar/nova/', views.conta_pagar_add, name='conta_pagar_add'),
    path('financeiro/contas-pagar/editar/<int:pk>/', views.conta_pagar_edit, name='conta_pagar_edit'),
    path('financeiro/contas-pagar/excluir/<int:pk>/', views.conta_pagar_delete, name='conta_pagar_delete'),
    path('financeiro/contas-pagar/baixar/<int:pk>/', views.conta_pagar_baixar, name='conta_pagar_baixar'),

    path('financeiro/fluxo-caixa/', views.fluxo_caixa, name='fluxo_caixa'),
    path('financeiro/fluxo-caixa/lancamento/', views.movimentacao_caixa_add, name='movimentacao_caixa_add'),

    path('financeiro/conciliacao/', views.conciliacao_list, name='conciliacao_list'),
    path('financeiro/conciliacao/novo/', views.conciliacao_add, name='conciliacao_add'),
    path('financeiro/conciliacao/editar/<int:pk>/', views.conciliacao_edit, name='conciliacao_edit'),
    path('financeiro/conciliacao/excluir/<int:pk>/', views.conciliacao_delete, name='conciliacao_delete'),

    # =============================================================================
    # DRE
    # =============================================================================
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
    # ESTOQUE
    # =============================================================================
    path('estoque/movimentacoes/', views.movimentacao_estoque_list, name='movimentacao_estoque_list'),
    path('estoque/movimentacoes/nova/', views.movimentacao_estoque_add, name='movimentacao_estoque_add'),
    path('estoque/movimentacoes/editar/<int:pk>/', views.movimentacao_estoque_edit, name='movimentacao_estoque_edit'),
    path('estoque/movimentacoes/excluir/<int:pk>/', views.movimentacao_estoque_delete, name='movimentacao_estoque_delete'),

    path('estoque/inventarios/', views.inventario_list, name='inventario_list'),
    path('estoque/inventarios/novo/', views.inventario_add, name='inventario_add'),
    path('estoque/inventarios/editar/<int:pk>/', views.inventario_edit, name='inventario_edit'),
    path('estoque/inventarios/excluir/<int:pk>/', views.inventario_delete, name='inventario_delete'),

    path('estoque/transferencias/', views.transferencia_list, name='transferencia_list'),
    path('estoque/transferencias/nova/', views.transferencia_add, name='transferencia_add'),
    path('estoque/transferencias/editar/<int:pk>/', views.transferencia_edit, name='transferencia_edit'),
    path('estoque/transferencias/excluir/<int:pk>/', views.transferencia_delete, name='transferencia_delete'),

    path('estoque/relatorio-posicao/', views.relatorio_estoque, name='relatorio_estoque'),
    path('estoque/relatorio-movimentacoes/', views.relatorio_movimentacoes, name='relatorio_movimentacoes'),
]