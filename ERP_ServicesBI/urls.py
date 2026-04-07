from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

app_name = 'ERP_ServicesBI'

urlpatterns = [
    # =============================================================================
    # LOGIN
    # =============================================================================
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='ERP_ServicesBI:dashboard'), name='logout'),

    # =============================================================================
    # DASHBOARD
    # =============================================================================
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard_alt'),

    # =============================================================================
    # CADASTRO - CLIENTES
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
    # CADASTRO - VENDEDORES
    # =============================================================================
    path('vendedores/', views.vendedor_manager, name='vendedor_manager'),
    path('vendedores/novo/', views.vendedor_form, name='vendedor_form'),
    path('vendedores/<int:pk>/editar/', views.vendedor_form, name='vendedor_form_edit'),
    path('vendedores/<int:pk>/excluir/', views.vendedor_excluir, name='vendedor_excluir'),

    # =============================================================================
    # CADASTRO - EMPRESAS
    # =============================================================================
    path('cadastro/empresas/', views.empresa_manager, name='empresa_list'),
    path('cadastro/empresas/nova/', views.empresa_form, name='empresa_add'),
    path('cadastro/empresas/editar/<int:pk>/', views.empresa_form, name='empresa_edit'),
    path('cadastro/empresas/excluir/<int:pk>/', views.empresa_excluir, name='empresa_delete'),

    # =============================================================================
    # CADASTRO - FORNECEDORES
    # =============================================================================
    path('cadastro/fornecedores/', views.fornecedor_manager, name='fornecedor_manager'),
    path('cadastro/fornecedores/novo/', views.fornecedor_form, name='fornecedor_add'),
    path('cadastro/fornecedores/editar/<int:pk>/', views.fornecedor_form, name='fornecedor_edit'),
    path('cadastro/fornecedores/excluir/<int:pk>/', views.fornecedor_excluir, name='fornecedor_delete'),

    # =============================================================================
    # APIs - CATEGORIA PRODUTO
    # =============================================================================
    path('api/categoria-produto/criar/', views.categoria_produto_create_ajax, name='categoria_produto_create_ajax'),
    path('api/categoria-produto/<int:pk>/excluir/', views.categoria_produto_delete_ajax, name='categoria_produto_delete_ajax'),

    # =============================================================================
    # CADASTRO - PRODUTOS
    # =============================================================================
    path('cadastro/produtos/', views.produto_manager, name='produto_list'),
    path('cadastro/produtos/novo/', views.produto_form, name='produto_add'),
    path('cadastro/produtos/editar/<int:pk>/', views.produto_form, name='produto_edit'),
    path('cadastro/produtos/excluir/<int:pk>/', views.produto_excluir, name='produto_delete'),

    # =============================================================================
    # COMPRAS - COTAÇÕES
    # =============================================================================
    path('compras/cotacoes/', views.cotacao_manager, name='cotacao_manager'),
    path('api/cotacao/salvar/', views.cotacao_salvar_api, name='cotacao_salvar_api'),
    path('api/cotacao/<int:pk>/dados/', views.cotacao_dados_api, name='cotacao_dados_api'),
    path('api/cotacao/<int:pk>/comparativo/', views.cotacao_comparativo_api, name='cotacao_comparativo_api'),
    path('api/cotacao/<int:pk>/excluir/', views.cotacao_excluir_api, name='cotacao_excluir_api'),
    path('api/cotacao/<int:pk>/enviar/', views.cotacao_enviar_api, name='cotacao_enviar_api'),
    path('api/cotacao/<int:pk>/concluir/', views.cotacao_concluir_api, name='cotacao_concluir_api'),
    path('api/cotacao/<int:pk>/importar-cotacao/', views.cotacao_importar_fornecedor, name='cotacao_importar_fornecedor'),
    path('api/cotacao/<int:pk>/fornecedores-importados/', views.cotacao_fornecedores_importados_api, name='cotacao_fornecedores_importados_api'),
    path('api/cotacao/<int:pk>/gerar-pedidos/', views.cotacao_gerar_pedidos, name='cotacao_gerar_pedidos'),
    path('api/cotacao/<int:pk>/salvar-selecao/', views.cotacao_salvar_selecao, name='cotacao_salvar_selecao'),
    path('api/cotacao/<int:pk>/calcular-sugestoes/', views.cotacao_calcular_sugestoes, name='cotacao_calcular_sugestoes'),
    path('api/cotacao/<int:pk>/remover-fornecedor/<int:fornecedor_pk>/', views.cotacao_remover_fornecedor, name='cotacao_remover_fornecedor'),
    path('api/cotacao/<int:pk>/copiar-email/', views.cotacao_copiar_lista_email, name='cotacao_copiar_lista_email'),
    path('api/cotacao/<int:pk>/copiar-whatsapp/', views.cotacao_copiar_lista_whatsapp, name='cotacao_copiar_lista_whatsapp'),
    path('compras/cotacao/<int:pk>/confirmar-delete/', views.cotacao_confirm_delete, name='cotacao_confirm_delete'),

    # =============================================================================
    # COMPRAS - PEDIDOS DE COMPRA
    # =============================================================================
    path('compras/pedidos/', views.pedido_compra_manager, name='pedido_compra_manager'),
    path('api/pedido/salvar/', views.pedido_salvar_api, name='pedido_salvar_api'),
    path('api/pedido/<int:pk>/dados/', views.pedido_dados_api, name='pedido_dados_api'),
    path('api/pedido/<int:pk>/dados-simples/', views.pedido_dados_simples_api, name='pedido_dados_simples_api'),
    path('api/pedido/<int:pk>/cancelar/', views.pedido_cancelar_api, name='pedido_cancelar_api'),
    path('api/pedido/<int:pk>/receber/', views.pedido_receber_api, name='pedido_receber_api'),
    path('api/pedido/<int:pk>/dados-recebimento/', views.pedido_dados_recebimento_api, name='pedido_dados_recebimento_api'),
    path('compras/pedido/<int:pk>/confirmar-delete/', views.pedido_compra_confirm_delete, name='pedido_compra_confirm_delete'),
    path('compras/pedidos/<int:pk>/gerar-nfe/', views.pedido_compra_gerar_nfe, name='pedido_compra_gerar_nfe'),
    path('api/pedido/<int:pk>/dados-para-nfe/', views.api_pedido_dados_para_nfe, name='api_pedido_dados_para_nfe'),
    path('api/pedido/<int:pk>/gerar-nfe/', views.api_gerar_nfe_from_pedido, name='api_gerar_nfe_from_pedido'),

    # =============================================================================
    # COMPRAS - APROVAÇÃO DE PEDIDOS
    # =============================================================================
    path('compras/aprovacoes/', views.pedido_aprovacao_list, name='pedido_aprovacao_list'),
    path('compras/aprovacoes/<int:pk>/', views.pedido_aprovacao_detail, name='pedido_aprovacao_detail'),
    path('compras/aprovacoes/<int:pk>/aprovar/', views.pedido_aprovacao_approve, name='pedido_aprovacao_approve'),
    path('compras/aprovacoes/<int:pk>/rejeitar/', views.pedido_aprovacao_reject, name='pedido_aprovacao_reject'),
    path('api/pedidos/pendentes-alcada/', views.api_pedidos_pendentes_alcada, name='api_pedidos_pendentes_alcada'),
    path('api/pedido/<int:pk>/aprovar/', views.api_aprovar_pedido, name='api_aprovar_pedido'),
    path('api/pedido/<int:pk>/rejeitar/', views.api_rejeitar_pedido, name='api_rejeitar_pedido'),
    path('api/pedido/<int:pk>/historico-aprovacoes/', views.api_historico_aprovacoes, name='api_historico_aprovacoes'),
    path('api/pedido/<int:pk>/divergencias-3way/', views.api_verificar_divergencias_3way, name='api_verificar_divergencias_3way'),

    # =============================================================================
    # COMPRAS - NOTAS FISCAIS DE ENTRADA
    # =============================================================================
    path('compras/notas-fiscais/', views.nota_fiscal_entrada_manager, name='nota_fiscal_entrada_manager'),
    path('api/nota-fiscal/salvar/', views.nota_fiscal_salvar_api, name='nota_fiscal_salvar_api'),
    path('api/nota-fiscal/<int:pk>/dados/', views.nota_fiscal_dados_api, name='nota_fiscal_dados_api'),
    path('api/nota-fiscal/<int:pk>/excluir/', views.nota_fiscal_excluir_api, name='nota_fiscal_excluir_api'),
    path('api/nota-fiscal/<int:pk>/confirmar/', views.nota_fiscal_confirmar_api, name='nota_fiscal_confirmar_api'),
    path('api/nota-fiscal/<int:pk>/cancelar/', views.nota_fiscal_cancelar_api, name='nota_fiscal_cancelar_api'),
    path('compras/nota-fiscal/<int:pk>/confirmar-delete/', views.nota_fiscal_entrada_confirm_delete, name='nota_fiscal_entrada_confirm_delete'),

    # =============================================================================
    # COMPRAS - RELATÓRIOS
    # =============================================================================
    path('compras/relatorios/', views.relatorio_compras, name='relatorio_compras'),
    path('api/compras/relatorio/dados/', views.relatorio_compras_dados_api, name='relatorio_compras_dados_api'),
    path('api/compras/relatorio/exportar/', views.relatorio_compras_exportar_api, name='relatorio_compras_exportar_api'),

    # =============================================================================
    # VENDAS - ORÇAMENTOS
    # =============================================================================
    path('vendas/orcamentos/', views.orcamento_manager, name='orcamento_manager'),
    path('vendas/orcamentos/novo/', views.orcamento_form, name='orcamento_form'),
    path('vendas/orcamentos/<int:pk>/editar/', views.orcamento_form, name='orcamento_form_edit'),
    path('vendas/orcamentos/<int:pk>/excluir/', views.orcamento_excluir_api, name='orcamento_excluir'),
    path('vendas/orcamentos/<int:pk>/gerar-pedido/', views.orcamento_gerar_pedido, name='orcamento_gerar_pedido'),

    # =============================================================================
    # VENDAS - PEDIDOS
    # =============================================================================
    path('vendas/pedidos/', views.pedido_venda_manager, name='pedido_venda_manager'),
    path('vendas/pedidos/novo/', views.pedido_venda_form, name='pedido_venda_form'),
    path('vendas/pedidos/<int:pk>/editar/', views.pedido_venda_form, name='pedido_venda_form_edit'),
    path('vendas/pedidos/<int:pk>/excluir/', views.pedido_venda_excluir_api, name='pedido_venda_excluir'),
    path('vendas/pedidos/<int:pk>/gerar-nfe/', views.pedido_venda_gerar_nfe, name='pedido_venda_gerar_nfe'),

    # =============================================================================
    # VENDAS - NOTAS FISCAIS DE SAÍDA
    # =============================================================================
    path('vendas/notas-fiscais/', views.nota_fiscal_saida_manager, name='nota_fiscal_saida_manager'),
    path('vendas/notas-fiscais/novo/', views.nota_fiscal_saida_form, name='nota_fiscal_saida_form'),
    path('vendas/notas-fiscais/<int:pk>/editar/', views.nota_fiscal_saida_form, name='nota_fiscal_saida_form_edit'),
    path('vendas/notas-fiscais/<int:pk>/excluir/', views.nota_fiscal_saida_excluir_api, name='nota_fiscal_saida_excluir'),

    # =============================================================================
    # VENDAS - RELATÓRIOS
    # =============================================================================
    path('vendas/relatorios/', views.relatorio_vendas, name='relatorio_vendas'),

    # =============================================================================
    # FINANCEIRO - RELATÓRIO
    # =============================================================================
    path('financeiro/', views.relatorio_financeiro, name='relatorio_financeiro'),
    # Alias para PDF - redireciona para o mesmo relatório por enquanto
    path('financeiro/pdf/', views.relatorio_financeiro, name='relatorio_financeiro_pdf'),

    # =============================================================================
    # FINANCEIRO - FLUXO DE CAIXA
    # =============================================================================
    path('fluxo-caixa/', views.fluxo_caixa_list, name='fluxo_caixa_list'),
    path('fluxo-caixa/adicionar/', views.fluxo_caixa_add, name='fluxo_caixa_add'),
    path('fluxo-caixa/<int:pk>/editar/', views.fluxo_caixa_edit, name='fluxo_caixa_edit'),
    path('fluxo-caixa/<int:pk>/excluir/', views.fluxo_caixa_delete, name='fluxo_caixa_delete'),

    # Alias usado pelos templates do fluxo de caixa
    path('movimentacao-caixa/adicionar/', views.fluxo_caixa_add, name='movimentacao_caixa_add'),

    # =============================================================================
    # FINANCEIRO - CONTAS A RECEBER
    # =============================================================================
    path('contas-receber/', views.conta_receber_list, name='conta_receber_list'),
    path('contas-receber/adicionar/', views.conta_receber_add, name='conta_receber_add'),
    path('contas-receber/<int:pk>/editar/', views.conta_receber_edit, name='conta_receber_edit'),
    path('contas-receber/<int:pk>/excluir/', views.conta_receber_delete, name='conta_receber_excluir'),
    path('contas-receber/<int:pk>/baixar/', views.conta_receber_baixar, name='conta_receber_baixar'),

    # =============================================================================
    # FINANCEIRO - CONTAS A PAGAR
    # =============================================================================
    path('contas-pagar/', views.conta_pagar_list, name='conta_pagar_list'),
    path('contas-pagar/adicionar/', views.conta_pagar_add, name='conta_pagar_add'),
    path('contas-pagar/<int:pk>/editar/', views.conta_pagar_edit, name='conta_pagar_edit'),
    path('contas-pagar/<int:pk>/excluir/', views.conta_pagar_delete, name='conta_pagar_excluir'),
    path('contas-pagar/<int:pk>/baixar/', views.conta_pagar_baixar, name='conta_pagar_baixar'),


    # =============================================================================
    # FINANCEIRO - CONCILIAÇÃO BANCÁRIA
    # =============================================================================

    path('conciliacao-bancaria/', views.conciliacao_bancaria_list, name='conciliacao_bancaria_list'),
    path('conciliacao-bancaria/adicionar/', views.conciliacao_bancaria_add, name='conciliacao_bancaria_add'),
    path('conciliacao-bancaria/<int:pk>/editar/', views.conciliacao_bancaria_edit, name='conciliacao_bancaria_edit'),
    path('conciliacao-bancaria/<int:pk>/detalhar/', views.conciliacao_bancaria_detail, name='conciliacao_bancaria_detail'),
    path('conciliacao-bancaria/<int:pk>/excluir/', views.conciliacao_bancaria_delete, name='conciliacao_bancaria_delete'),
    path('conciliacao-bancaria/<int:pk>/processar/', views.conciliacao_bancaria_processar, name='conciliacao_bancaria_processar'),
    path('conciliacao-bancaria/<int:pk>/vincular/', views.conciliacao_bancaria_vincular, name='conciliacao_bancaria_vincular'),
    path('conciliacao-bancaria/importar-ofx/', views.conciliacao_importar_ofx, name='conciliacao_importar_ofx'),
    path('conciliacao-bancaria/buscar-lancamentos/', views.conciliacao_buscar_lancamentos, name='conciliacao_buscar_lancamentos'),
    path('conciliacao-bancaria/realizar/', views.conciliacao_realizar, name='conciliacao_realizar'),
    path('conciliacao-bancaria/auto/', views.conciliacao_auto, name='conciliacao_auto'),

    # =============================================================================
    # FINANCEIRO - DRE GERENCIAL
    # =============================================================================
    path('dre/', views.dre_list, name='dre_list'),
    path('dre/adicionar/', views.dre_add, name='dre_add'),
    path('dre/<int:pk>/editar/', views.dre_edit, name='dre_edit'),

    # Alias usado pelo template dre_manager.html
    path('dre/configuracao/', views.dre_edit, name='dre_configuracao'),

    # NOVAS URLS:
    path('dre/salvar/', views.dre_salvar, name='dre_salvar'),
    path('dre/relatorio/<int:pk>/', views.dre_relatorio, name='dre_relatorio'),
    path('dre/comparativo/', views.dre_comparativo, name='dre_comparativo'),

    # =============================================================================
    # FINANCEIRO - PLANEJADO X REALIZADO
    # =============================================================================
    path('planejado-realizado/', views.planejado_x_realizado_list, name='planejado_x_realizado_list'),
    path('planejado-realizado/adicionar/', views.planejado_x_realizado_add, name='planejado_x_realizado_add'),
    path('planejado-realizado/<int:pk>/editar/', views.planejado_x_realizado_edit, name='planejado_x_realizado_edit'),
    path('planejado-realizado/excel/', views.planejado_x_realizado_excel, name='planejado_x_realizado_excel'),
    path('api/projetos/criar/', views.api_criar_projeto, name='api_criar_projeto'),
    path('api/projeto/criar/', views.projeto_create_ajax, name='projeto_create_ajax'),
    path('api/projeto/<int:pk>/excluir/', views.projeto_delete_ajax, name='projeto_delete_ajax'),

    # =============================================================================
    # FINANCEIRO - CATEGORIAS (mantidas para APIs AJAX dos forms)
    # =============================================================================
    path('categorias/', views.categoria_financeira_list, name='categoria_financeira_list'),
    path('categorias/adicionar/', views.categoria_financeira_add, name='categoria_financeira_add'),
    path('categorias/<int:pk>/editar/', views.categoria_financeira_edit, name='categoria_financeira_edit'),
    path('categorias/<int:pk>/excluir/', views.categoria_financeira_delete, name='categoria_financeira_delete'),

    # =============================================================================
    # FINANCEIRO - CENTROS DE CUSTO (mantidos para APIs AJAX dos forms)
    # =============================================================================
    path('centros-custo/', views.centro_custo_list, name='centro_custo_list'),
    path('centros-custo/adicionar/', views.centro_custo_add, name='centro_custo_add'),
    path('centros-custo/<int:pk>/editar/', views.centro_custo_edit, name='centro_custo_edit'),
    path('centros-custo/<int:pk>/excluir/', views.centro_custo_delete, name='centro_custo_delete'),

    # =============================================================================
    # FINANCEIRO - APIs AJAX (categorias e centros de custo)
    # =============================================================================
    path('api/categorias/criar/', views.api_categoria_criar, name='api_categoria_criar'),
    path('api/categorias/<int:pk>/excluir/', views.api_categoria_excluir, name='api_categoria_excluir'),
    path('api/centros-custo/criar/', views.api_centro_custo_criar, name='api_centro_custo_criar'),
    path('api/centros-custo/<int:pk>/excluir/', views.api_centro_custo_excluir, name='api_centro_custo_excluir'),

    # Alias usado pelo conta_pagar_form.html e conta_receber_form.html
    path('api/financeiro/categorias/criar/', views.api_categoria_criar, name='api_financeiro_categoria_criar'),
    path('api/financeiro/categorias/<int:pk>/excluir/', views.api_categoria_excluir, name='api_financeiro_categoria_excluir'),
    path('api/financeiro/centros-custo/criar/', views.api_centro_custo_criar, name='api_financeiro_centro_custo_criar'),
    path('api/financeiro/centros-custo/<int:pk>/excluir/', views.api_centro_custo_excluir, name='api_financeiro_centro_custo_excluir'),

    # =============================================================================
    # ESTOQUE - MOVIMENTAÇÕES
    # =============================================================================
    path('estoque/movimentacoes/', views.movimentacao_estoque_list, name='movimentacao_estoque_list'),
    path('estoque/movimentacoes/nova/', views.movimentacao_estoque_add, name='movimentacao_estoque_add'),
    path('estoque/movimentacoes/<int:pk>/editar/', views.movimentacao_estoque_edit, name='movimentacao_estoque_edit'),
    path('estoque/movimentacoes/<int:pk>/', views.movimentacao_estoque_detail, name='movimentacao_estoque_detail'),
    path('estoque/movimentacoes/<int:pk>/excluir/', views.movimentacao_estoque_delete, name='movimentacao_estoque_delete'),

    # =============================================================================
    # ESTOQUE - DEPÓSITOS
    # =============================================================================
    path('estoque/depositos/', views.deposito_list, name='deposito_list'),
    path('estoque/depositos/novo/', views.deposito_add, name='deposito_add'),
    path('estoque/depositos/<int:pk>/editar/', views.deposito_edit, name='deposito_edit'),
    path('estoque/depositos/<int:pk>/excluir/', views.deposito_delete, name='deposito_delete'),

    # =============================================================================
    # ESTOQUE - DEPÓSITOS (AJAX) - CORRIGIDO
    # =============================================================================
    path('estoque/depositos/add/ajax/', views.deposito_create_ajax, name='deposito_create_ajax'),
    path('estoque/depositos/<int:pk>/delete/ajax/', views.deposito_delete_ajax, name='deposito_delete_ajax'),

    # =============================================================================
    # ESTOQUE - APIs - CORRIGIDO (removida api_produto_saldo duplicada)
    # =============================================================================
    path('api/estoque/saldo/', views.api_estoque_saldo, name='api_estoque_saldo'),
    path('api/produto/<int:pk>/saldo/', views.api_produto_saldo_disponivel, name='api_produto_saldo_disponivel'),
    # REMOVIDO: path('api/produto/<int:produto_id>/saldo/', views.api_produto_saldo, name='api_produto_saldo'),
    path('api/produtos/busca/', views.api_produtos_busca, name='api_produtos_busca'),

    # =============================================================================
    # ESTOQUE - INVENTÁRIO
    # =============================================================================
    path('estoque/inventarios/', views.inventario_list, name='inventario_list'),
    path('estoque/inventarios/novo/', views.inventario_add, name='inventario_add'),
    path('estoque/inventarios/<int:pk>/contagem/', views.inventario_contagem, name='inventario_contagem'),
    path('estoque/inventarios/<int:pk>/finalizar/', views.inventario_finalizar, name='inventario_finalizar'),
    path('estoque/inventarios/<int:pk>/editar/', views.inventario_edit, name='inventario_edit'),
    path('estoque/inventarios/<int:pk>/excluir/', views.inventario_delete, name='inventario_delete'),

    # =============================================================================
    # ESTOQUE - ENTRADA NF-E
    # =============================================================================
    path('estoque/entradas-nfe/', views.entrada_nfe_list, name='entrada_nfe_list'),
    path('estoque/entradas-nfe/nova/', views.entrada_nfe_add, name='entrada_nfe_add'),
    path('estoque/entradas-nfe/<int:pk>/itens/', views.entrada_nfe_itens, name='entrada_nfe_itens'),
    path('estoque/entradas-nfe/<int:pk>/finalizar/', views.entrada_nfe_finalizar, name='entrada_nfe_finalizar'),
    path('estoque/entradas-nfe/<int:pk>/', views.entrada_nfe_detail, name='entrada_nfe_detail'),
    path('estoque/entradas-nfe/<int:pk>/editar/', views.entrada_nfe_edit, name='entrada_nfe_edit'),
    path('estoque/entradas-nfe/importar-xml/', views.entrada_nfe_importar_xml, name='entrada_nfe_importar_xml'),

    # =============================================================================
    # ESTOQUE - RELATÓRIOS
    # =============================================================================
    path('estoque/relatorio-posicao/', views.relatorio_estoque, name='relatorio_estoque'),
    path('estoque/relatorio-movimentacoes/', views.relatorio_movimentacao, name='relatorio_movimentacoes'),
    path('estoque/consulta-saldo/', views.consulta_saldo, name='consulta_saldo'),

    # =============================================================================
    # ESTOQUE - APIs
    # =============================================================================
    path('api/produto/<int:produto_id>/saldo/', views.api_produto_saldo_disponivel, name='api_produto_saldo'),
    path('api/produtos/busca/', views.api_produtos_busca, name='api_produtos_busca'),

    # =============================================================================
    # ESTOQUE - TRANSFERÊNCIAS
    # =============================================================================
    path('estoque/transferencias/', views.transferencia_list, name='transferencia_list'),
    path('estoque/transferencias/nova/', views.transferencia_add, name='transferencia_add'),
    path('estoque/transferencias/<int:pk>/', views.transferencia_detail, name='transferencia_detail'),
    path('estoque/transferencias/<int:pk>/editar/', views.transferencia_edit, name='transferencia_edit'),
    path('estoque/transferencias/<int:pk>/excluir/', views.transferencia_delete, name='transferencia_delete'),
    path('estoque/transferencias/<int:pk>/enviar/', views.transferencia_enviar, name='transferencia_enviar'),
    path('estoque/transferencias/<int:pk>/receber/', views.transferencia_receber, name='transferencia_receber'),
]