# -*- coding: utf-8 -*-
"""
ERP_ServicesBI - urls.py CORRIGIDO
Padrão: nome da URL = nome da view (ex: cliente_manager)
"""
from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

app_name = 'ERP_ServicesBI'

urlpatterns = [
    # =========================================================================
    # LOGIN / LOGOUT
    # =========================================================================
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='ERP_ServicesBI:dashboard'), name='logout'),

    # =========================================================================
    # DASHBOARD
    # =========================================================================
    path('', views.dashboard, name='dashboard'),
    path('api/dashboard/dados/', views.api_dashboard_dados, name='api_dashboard_dados'),

    # =========================================================================
    # CADASTRO - CLIENTES
    # =========================================================================
    path('clientes/', views.cliente_manager, name='cliente_manager'),  # ✅ Alterado
    path('clientes/novo/', views.cliente_form, name='cliente_add'),
    path('clientes/<int:pk>/editar/', views.cliente_form, name='cliente_edit'),
    path('clientes/<int:pk>/excluir/', views.cliente_delete, name='cliente_delete'),
    path('api/cliente/<int:pk>/', views.cliente_detail_api, name='cliente_detail_api'),

    # =========================================================================
    # CADASTRO - FORNECEDORES
    # =========================================================================
    path('fornecedores/', views.fornecedor_manager, name='fornecedor_manager'),  # ✅ Alterado
    path('fornecedores/novo/', views.fornecedor_form, name='fornecedor_add'),
    path('fornecedores/<int:pk>/editar/', views.fornecedor_form, name='fornecedor_edit'),
    path('fornecedores/<int:pk>/excluir/', views.fornecedor_delete, name='fornecedor_delete'),

    # =========================================================================
    # CADASTRO - PRODUTOS
    # =========================================================================
    path('produtos/', views.produto_manager, name='produto_manager'),  # ✅ Alterado
    path('produtos/novo/', views.produto_form, name='produto_add'),
    path('produtos/<int:pk>/editar/', views.produto_form, name='produto_edit'),
    path('produtos/<int:pk>/excluir/', views.produto_delete, name='produto_delete'),
    path('api/produto/<int:pk>/saldo/', views.api_produto_saldo_disponivel, name='api_produto_saldo_disponivel'),

    # =========================================================================
    # CADASTRO - VENDEDORES
    # =========================================================================
    path('vendedores/', views.vendedor_manager, name='vendedor_manager'),  # ✅ Alterado
    path('vendedores/novo/', views.vendedor_form, name='vendedor_add'),
    path('vendedores/<int:pk>/editar/', views.vendedor_form, name='vendedor_edit'),
    path('vendedores/<int:pk>/excluir/', views.vendedor_delete, name='vendedor_delete'),

    # =========================================================================
    # CADASTRO - EMPRESAS
    # =========================================================================
    path('empresas/', views.empresa_manager, name='empresa_manager'),  # ✅ Alterado
    path('empresas/nova/', views.empresa_form, name='empresa_add'),
    path('empresas/<int:pk>/editar/', views.empresa_form, name='empresa_edit'),
    path('empresas/<int:pk>/excluir/', views.empresa_delete, name='empresa_delete'),

    # =========================================================================
    # CADASTRO - TRANSPORTADORAS
    # =========================================================================
    path('transportadoras/', views.transportadora_manager, name='transportadora_manager'),
    path('transportadoras/nova/', views.transportadora_form, name='transportadora_add'),
    path('transportadoras/<int:pk>/editar/', views.transportadora_form, name='transportadora_edit'),
    path('transportadoras/<int:pk>/excluir/', views.transportadora_delete, name='transportadora_delete'),

    # =========================================================================
    # CADASTRO - CATEGORIAS
    # =========================================================================
    path('categorias/', views.categoria_manager, name='categoria_manager'),
    path('categorias/nova/', views.categoria_form, name='categoria_add'),
    path('categorias/<int:pk>/editar/', views.categoria_form, name='categoria_edit'),
    path('categorias/<int:pk>/excluir/', views.categoria_delete, name='categoria_delete'),

    # =========================================================================
    # CADASTRO - MARCAS
    # =========================================================================
    path('marcas/', views.marca_manager, name='marca_manager'),
    path('marcas/nova/', views.marca_form, name='marca_add'),
    path('marcas/<int:pk>/editar/', views.marca_form, name='marca_edit'),
    path('marcas/<int:pk>/excluir/', views.marca_delete, name='marca_delete'),

    # =========================================================================
    # CADASTRO - UNIDADES DE MEDIDA
    # =========================================================================
    path('unidades-medida/', views.unidade_medida_manager, name='unidade_medida_manager'),
    path('unidades-medida/nova/', views.unidade_medida_form, name='unidade_medida_add'),
    path('unidades-medida/<int:pk>/editar/', views.unidade_medida_form, name='unidade_medida_edit'),
    path('unidades-medida/<int:pk>/excluir/', views.unidade_medida_delete, name='unidade_medida_delete'),

    # =========================================================================
    # CADASTRO - PROJETOS
    # =========================================================================
    path('projetos/', views.projeto_manager, name='projeto_manager'),
    path('projetos/novo/', views.projeto_form, name='projeto_add'),
    path('projetos/<int:pk>/editar/', views.projeto_form, name='projeto_edit'),
    path('projetos/<int:pk>/excluir/', views.projeto_excluir, name='projeto_delete'),
    path('api/projeto/criar/', views.projeto_create_ajax, name='projeto_create_ajax'),
    path('api/projeto/<int:pk>/excluir/', views.projeto_delete_ajax, name='projeto_delete_ajax'),

    # =========================================================================
    # COMPRAS - COTAÇÕES
    # =========================================================================
    path('cotacoes/', views.cotacao_manager, name='cotacao_manager'),  # ✅ Alterado
    path('cotacoes/nova/', views.cotacao_form, name='cotacao_add'),
    path('cotacoes/<int:pk>/editar/', views.cotacao_form, name='cotacao_edit'),
    path('cotacoes/<int:pk>/excluir/', views.cotacao_delete, name='cotacao_delete'),
    path('api/cotacao/<int:pk>/dados/', views.cotacao_dados_api, name='cotacao_dados_api'),
    path('api/cotacao/enviar/', views.cotacao_enviar_api, name='cotacao_enviar_api'),
    path('api/cotacao/item/add/', views.cotacao_item_add_api, name='cotacao_item_add_api'),
    path('api/cotacao/item/<int:item_id>/delete/', views.cotacao_item_delete_api, name='cotacao_item_delete_api'),

    # =========================================================================
    # COMPRAS - PEDIDOS DE COMPRA
    # =========================================================================
    path('pedidos-compra/', views.pedido_compra_manager, name='pedido_compra_manager'),  # ✅ Alterado
    path('pedidos-compra/novo/', views.pedido_compra_form, name='pedido_compra_add'),
    path('pedidos-compra/<int:pk>/editar/', views.pedido_compra_form, name='pedido_compra_edit'),
    path('pedidos-compra/<int:pk>/excluir/', views.pedido_compra_delete, name='pedido_compra_delete'),
    path('api/pedido-compra/<int:pk>/dados/', views.pedido_compra_dados_api, name='pedido_compra_dados_api'),
    path('api/pedido-compra/salvar/', views.pedido_salvar_api, name='pedido_salvar_api'),
    path('api/pedido-compra/item/add/', views.pedido_item_add_api, name='pedido_item_add_api'),
    path('api/pedido-compra/item/<int:item_id>/delete/', views.pedido_item_delete_api, name='pedido_item_delete_api'),
    path('api/pedido-compra/enviar-aprovacao/', views.api_enviar_aprovacao, name='api_enviar_aprovacao'),

    # =========================================================================
    # COMPRAS - NOTAS FISCAIS DE ENTRADA
    # =========================================================================
    path('notas-entrada/', views.nota_fiscal_entrada_manager, name='nota_fiscal_entrada_manager'),  # ✅ Alterado
    path('notas-entrada/nova/', views.nota_fiscal_entrada_form, name='nota_fiscal_entrada_add'),
    path('notas-entrada/<int:pk>/editar/', views.nota_fiscal_entrada_form, name='nota_fiscal_entrada_edit'),
    path('notas-entrada/<int:pk>/excluir/', views.nota_fiscal_entrada_delete, name='nota_fiscal_entrada_delete'),
    path('notas-entrada/nfe/', views.entrada_nfe, name='entrada_nfe'),
    path('api/nota-entrada/salvar/', views.nota_fiscal_salvar_api, name='nota_fiscal_salvar_api'),
    path('api/nota-entrada/<int:pk>/dados/', views.nota_fiscal_entrada_dados_api, name='nota_fiscal_entrada_dados_api'),
    path('api/nota-entrada/item/add/', views.nota_fiscal_entrada_item_add_api, name='nota_fiscal_entrada_item_add_api'),
    path('api/nota-entrada/item/<int:item_id>/delete/', views.nota_fiscal_entrada_item_delete_api, name='nota_fiscal_entrada_item_delete_api'),
    path('api/nota-entrada/<int:pk>/confirmar/', views.nota_fiscal_entrada_confirmar_recebimento, name='nota_fiscal_entrada_confirmar'),

    # =========================================================================
    # COMPRAS - RELATÓRIOS
    # =========================================================================
    path('relatorio-compras/', views.relatorio_compras, name='relatorio_compras'),

    # =========================================================================
    # VENDAS - ORÇAMENTOS
    # =========================================================================
    path('orcamentos/', views.orcamento_manager, name='orcamento_manager'),  # ✅ Alterado
    path('orcamentos/novo/', views.orcamento_form, name='orcamento_add'),
    path('orcamentos/<int:pk>/editar/', views.orcamento_form, name='orcamento_edit'),
    path('orcamentos/<int:pk>/excluir/', views.orcamento_delete, name='orcamento_delete'),
    path('api/orcamento/<int:pk>/dados/', views.orcamento_dados_api, name='orcamento_dados_api'),
    path('api/orcamento/salvar/', views.orcamento_salvar_api, name='orcamento_salvar_api'),
    path('api/orcamento/item/add/', views.orcamento_item_add_api, name='orcamento_item_add_api'),
    path('api/orcamento/item/<int:item_id>/delete/', views.orcamento_item_delete_api, name='orcamento_item_delete_api'),
    path('api/orcamento/<int:pk>/gerar-pedido/', views.orcamento_gerar_pedido, name='orcamento_gerar_pedido'),

    # =========================================================================
    # VENDAS - ORÇAMENTOS DE PROJETO
    # =========================================================================
    path('orcamentos-projeto/', views.orcamento_projeto_manager, name='orcamento_projeto_manager'),
    path('orcamentos-projeto/novo/', views.orcamento_projeto_form, name='orcamento_projeto_add'),
    path('orcamentos-projeto/<int:pk>/editar/', views.orcamento_projeto_form, name='orcamento_projeto_edit'),
    path('orcamentos-projeto/<int:pk>/excluir/', views.orcamento_projeto_delete, name='orcamento_projeto_delete'),

    # =========================================================================
    # VENDAS - PEDIDOS DE VENDA
    # =========================================================================
    path('pedidos-venda/', views.pedido_venda_manager, name='pedido_venda_manager'),  # ✅ Alterado
    path('pedidos-venda/novo/', views.pedido_venda_form, name='pedido_venda_add'),
    path('pedidos-venda/<int:pk>/editar/', views.pedido_venda_form, name='pedido_venda_edit'),
    path('pedidos-venda/<int:pk>/excluir/', views.pedido_venda_delete, name='pedido_venda_delete'),
    path('api/pedido-venda/<int:pk>/dados/', views.pedido_venda_dados_api, name='pedido_venda_dados_api'),
    path('api/pedido-venda/salvar/', views.pedido_venda_salvar_api, name='pedido_venda_salvar_api'),
    path('api/pedido-venda/item/add/', views.pedido_venda_item_add_api, name='pedido_venda_item_add_api'),
    path('api/pedido-venda/item/<int:item_id>/delete/', views.pedido_venda_item_delete_api, name='pedido_venda_item_delete_api'),
    path('api/pedido-venda/<int:pk>/gerar-nfe/', views.pedido_venda_gerar_nfe, name='pedido_venda_gerar_nfe'),

    # =========================================================================
    # VENDAS - NOTAS FISCAIS DE SAÍDA
    # =========================================================================
    path('notas-saida/', views.nota_fiscal_saida_manager, name='nota_fiscal_saida_manager'),  # ✅ Alterado
    path('notas-saida/nova/', views.nota_fiscal_saida_form, name='nota_fiscal_saida_add'),
    path('notas-saida/<int:pk>/editar/', views.nota_fiscal_saida_form, name='nota_fiscal_saida_edit'),
    path('notas-saida/<int:pk>/excluir/', views.nota_fiscal_saida_delete, name='nota_fiscal_saida_delete'),
    path('api/nota-saida/<int:pk>/dados/', views.nota_fiscal_saida_dados_api, name='nota_fiscal_saida_dados_api'),
    path('api/nota-saida/salvar/', views.nota_fiscal_saida_salvar_api, name='nota_fiscal_saida_salvar_api'),
    path('api/nota-saida/item/add/', views.nota_fiscal_saida_item_add_api, name='nota_fiscal_saida_item_add_api'),
    path('api/nota-saida/item/<int:item_id>/delete/', views.nota_fiscal_saida_item_delete_api, name='nota_fiscal_saida_item_delete_api'),
    path('api/nota-saida/<int:pk>/confirmar-entrega/', views.nota_fiscal_saida_confirmar_entrega, name='nota_fiscal_saida_confirmar_entrega'),

    # =========================================================================
    # VENDAS - RELATÓRIOS
    # =========================================================================
    path('relatorio-vendas/', views.relatorio_vendas, name='relatorio_vendas'),

    # =========================================================================
    # FINANCEIRO - RELATÓRIO
    # =========================================================================
    path('financeiro/', views.relatorio_financeiro, name='relatorio_financeiro'),

    # =========================================================================
    # FINANCEIRO - FLUXO DE CAIXA
    # =========================================================================
    path('fluxo-caixa/', views.fluxo_caixa_manager, name='fluxo_caixa_manager'),  # ✅ Alterado

    # =========================================================================
    # FINANCEIRO - CONTAS A PAGAR
    # =========================================================================
    path('contas-pagar/', views.conta_pagar_list, name='conta_pagar_list'),
    path('contas-pagar/nova/', views.conta_pagar_add, name='conta_pagar_add'),
    path('contas-pagar/<int:pk>/editar/', views.conta_pagar_edit, name='conta_pagar_edit'),
    path('contas-pagar/<int:pk>/excluir/', views.conta_pagar_delete, name='conta_pagar_delete'),
    path('api/conta-pagar/<int:pk>/baixar/', views.conta_pagar_baixar, name='conta_pagar_baixar'),

    # =========================================================================
    # FINANCEIRO - CONTAS A RECEBER
    # =========================================================================
    path('contas-receber/', views.conta_receber_list, name='conta_receber_list'),
    path('contas-receber/nova/', views.conta_receber_add, name='conta_receber_add'),
    path('contas-receber/<int:pk>/editar/', views.conta_receber_edit, name='conta_receber_edit'),
    path('contas-receber/<int:pk>/excluir/', views.conta_receber_delete, name='conta_receber_delete'),
    path('api/conta-receber/<int:pk>/baixar/', views.conta_receber_baixar, name='conta_receber_baixar'),

    # =========================================================================
    # FINANCEIRO - CONCILIAÇÃO BANCÁRIA
    # =========================================================================
    path('conciliacao/', views.conciliacao_bancaria_manager, name='conciliacao_bancaria_manager'),  # ✅ Alterado

    # =========================================================================
    # FINANCEIRO - DRE
    # =========================================================================
    path('dre/', views.dre_manager, name='dre_manager'),  # ✅ Alterado

    # =========================================================================
    # FINANCEIRO - PLANEJADO X REALIZADO
    # =========================================================================
    path('planejado-realizado/', views.planejado_x_realizado_manager, name='planejado_x_realizado_manager'),

    # =========================================================================
    # FINANCEIRO - CATEGORIAS FINANCEIRAS
    # =========================================================================
    path('categorias-financeiras/', views.categoria_financeira_list, name='categoria_financeira_list'),

    # =========================================================================
    # FINANCEIRO - CENTROS DE CUSTO
    # =========================================================================
    path('centros-custo/', views.centro_custo_list, name='centro_custo_list'),

    # =========================================================================
    # FINANCEIRO - CONTAS BANCÁRIAS
    # =========================================================================
    path('contas-bancarias/', views.conta_bancaria_list, name='conta_bancaria_list'),

    # =========================================================================
    # FINANCEIRO - FORMAS DE PAGAMENTO
    # =========================================================================
    path('formas-pagamento/', views.forma_pagamento_list, name='forma_pagamento_list'),

    # =========================================================================
    # FINANCEIRO - CONDIÇÕES DE PAGAMENTO
    # =========================================================================
    path('condicoes-pagamento/', views.condicao_pagamento_list, name='condicao_pagamento_list'),
    path('condicoes-pagamento/nova/', views.condicao_pagamento_add, name='condicao_pagamento_add'),
    path('condicoes-pagamento/<int:pk>/editar/', views.condicao_pagamento_edit, name='condicao_pagamento_edit'),
    path('condicoes-pagamento/<int:pk>/excluir/', views.condicao_pagamento_delete, name='condicao_pagamento_delete'),
    path('api/condicao-pagamento/<int:pk>/dados/', views.condicao_pagamento_dados_api, name='condicao_pagamento_dados_api'),

    # =========================================================================
    # ESTOQUE - MOVIMENTAÇÕES
    # =========================================================================
    path('movimentacoes/', views.movimentacao_estoque_manager, name='movimentacao_estoque_manager'),  # ✅ Alterado

    # =========================================================================
    # ESTOQUE - INVENTÁRIOS
    # =========================================================================
    path('inventarios/', views.inventario_manager, name='inventario_manager'),  # ✅ Alterado

    # =========================================================================
    # ESTOQUE - TRANSFERÊNCIAS
    # =========================================================================
    path('transferencias/', views.transferencia_estoque_manager, name='transferencia_estoque_manager'),  # ✅ Alterado

    # =========================================================================
    # ESTOQUE - DEPÓSITOS
    # =========================================================================
    path('depositos/', views.deposito_list, name='deposito_list'),

    # =========================================================================
    # ESTOQUE - RELATÓRIOS
    # =========================================================================
    path('relatorio-estoque/posicao/', views.relatorio_estoque_posicao, name='relatorio_estoque_posicao'),
    path('relatorio-estoque/movimentacao/', views.relatorio_estoque_movimentacao, name='relatorio_estoque_movimentacao'),
    path('relatorio-estoque/inventario/', views.relatorio_estoque_inventario, name='relatorio_estoque_inventario'),

    # =========================================================================
    # APIs GENÉRICAS
    # =========================================================================
    path('api/buscar-produtos/', views.api_buscar_produtos, name='api_buscar_produtos'),
    path('api/buscar-clientes/', views.api_buscar_clientes, name='api_buscar_clientes'),
    path('api/buscar-fornecedores/', views.api_buscar_fornecedores, name='api_buscar_fornecedores'),
]