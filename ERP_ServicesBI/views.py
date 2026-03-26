# -*- coding: utf-8 -*-
"""
ERP SERVICES BI - VIEWS COMPLETAS (COM WIZARD DE COTAÇÃO)
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Q, F, Min
from django.db import transaction
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from datetime import timedelta
from decimal import Decimal
import csv
import io
import json

from .models import (
    Cliente, Empresa, Fornecedor, Produto, Categoria,
    PedidoCompra, ItemPedidoCompra, NotaFiscalEntrada, ItemNotaFiscalEntrada,
    Orcamento, ItemOrcamento, PedidoVenda, ItemPedidoVenda, NotaFiscalSaida, ItemNotaFiscalSaida,
    ContaPagar, ContaReceber, MovimentoCaixa,
    CategoriaFinanceira, CentroCusto, OrcamentoFinanceiro,
    ExtratoBancario, LancamentoExtrato,
    MovimentacaoEstoque, Inventario, ItemInventario, TransferenciaEstoque, ItemTransferencia,
    CotacaoMae, ItemSolicitado, CotacaoFornecedor, ItemCotacaoFornecedor
)

from .forms import (
    ClienteForm, EmpresaForm, FornecedorForm, CategoriaForm, ProdutoForm,
    PedidoCompraForm, ItemPedidoCompraForm, NotaFiscalEntradaForm, ItemNotaFiscalEntradaForm,
    OrcamentoForm, ItemOrcamentoForm, PedidoVendaForm, ItemPedidoVendaForm, NotaFiscalSaidaForm, ItemNotaFiscalSaidaForm,
    ContaPagarForm, ContaReceberForm, MovimentoCaixaForm,
    CategoriaFinanceiraForm, CentroCustoForm, OrcamentoFinanceiroForm,
    ExtratoBancarioForm, LancamentoExtratoForm,
    MovimentacaoEstoqueForm, InventarioForm, ItemInventarioForm, TransferenciaEstoqueForm, ItemTransferenciaForm,
    CotacaoMaeForm, ItemSolicitadoForm, ItemSolicitadoFormSet, CotacaoFornecedorForm, ItemCotacaoFornecedorForm, ItemCotacaoFornecedorFormSet
)


# =============================================================================
# DASHBOARD
# =============================================================================

@login_required
def dashboard(request):
    """Dashboard principal do ERP"""
    context = {
        'total_clientes': Cliente.objects.filter(ativo=True).count(),
        'total_fornecedores': Fornecedor.objects.filter(ativo=True).count(),
        'total_produtos': Produto.objects.filter(ativo=True).count(),
        'pedidos_pendentes': PedidoCompra.objects.filter(status='pendente').count(),
        'vendas_pendentes': PedidoVenda.objects.filter(status='pendente').count(),
        'contas_vencer': ContaReceber.objects.filter(status__in=['pendente', 'aberto']).count(),
        'contas_pagar_vencer': ContaPagar.objects.filter(status__in=['pendente', 'aberto']).count(),
        'valor_pedidos_abertos': PedidoCompra.objects.filter(status__in=['pendente', 'aprovado']).aggregate(total=Sum('valor_total'))['total'] or 0,
        'valor_vendas_aberto': PedidoVenda.objects.filter(status__in=['pendente', 'aprovado']).aggregate(total=Sum('valor_total'))['total'] or 0,
    }
    return render(request, 'dashboard_novo.html', context)


# =============================================================================
# CADASTRO - CLIENTES
# =============================================================================

@login_required
def cliente_list(request):
    clientes = Cliente.objects.all().order_by('-id')
    context = {'clientes': clientes}
    return render(request, 'cadastro/cliente_list.html', context)

@login_required
def cliente_add(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente adicionado com sucesso!')
            return redirect('ERP_ServicesBI:cliente_list')
    else:
        form = ClienteForm()
    context = {'form': form, 'titulo': 'Novo Cliente'}
    return render(request, 'cadastro/cliente_form.html', context)

@login_required
def cliente_edit(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente atualizado com sucesso!')
            return redirect('ERP_ServicesBI:cliente_list')
    else:
        form = ClienteForm(instance=cliente)
    context = {'form': form, 'titulo': 'Editar Cliente', 'cliente': cliente}
    return render(request, 'cadastro/cliente_form.html', context)

@login_required
def cliente_delete(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        cliente.delete()
        messages.success(request, 'Cliente excluído com sucesso!')
        return redirect('ERP_ServicesBI:cliente_list')
    context = {'cliente': cliente, 'titulo': 'Excluir Cliente'}
    return render(request, 'cadastro/cliente_confirm_delete.html', context)


# =============================================================================
# CADASTRO - EMPRESAS
# =============================================================================

@login_required
def empresa_list(request):
    empresas = Empresa.objects.all().order_by('-id')
    context = {'empresas': empresas}
    return render(request, 'cadastro/empresa_list.html', context)

@login_required
def empresa_add(request):
    if request.method == 'POST':
        form = EmpresaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Empresa adicionada com sucesso!')
            return redirect('ERP_ServicesBI:empresa_list')
    else:
        form = EmpresaForm()
    context = {'form': form, 'titulo': 'Nova Empresa'}
    return render(request, 'cadastro/empresa_form.html', context)

@login_required
def empresa_edit(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    if request.method == 'POST':
        form = EmpresaForm(request.POST, instance=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Empresa atualizada com sucesso!')
            return redirect('ERP_ServicesBI:empresa_list')
    else:
        form = EmpresaForm(instance=empresa)
    context = {'form': form, 'titulo': 'Editar Empresa', 'empresa': empresa}
    return render(request, 'cadastro/empresa_form.html', context)

@login_required
def empresa_delete(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    if request.method == 'POST':
        empresa.delete()
        messages.success(request, 'Empresa excluída com sucesso!')
        return redirect('ERP_ServicesBI:empresa_list')
    context = {'empresa': empresa, 'titulo': 'Excluir Empresa'}
    return render(request, 'cadastro/empresa_confirm_delete.html', context)


# =============================================================================
# CADASTRO - FORNECEDORES
# =============================================================================

@login_required
def fornecedor_list(request):
    fornecedores = Fornecedor.objects.all().order_by('-id')
    context = {'fornecedores': fornecedores}
    return render(request, 'cadastro/fornecedor_list.html', context)

@login_required
def fornecedor_add(request):
    if request.method == 'POST':
        form = FornecedorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fornecedor adicionado com sucesso!')
            return redirect('ERP_ServicesBI:fornecedor_list')
    else:
        form = FornecedorForm()
    context = {'form': form, 'titulo': 'Novo Fornecedor'}
    return render(request, 'cadastro/fornecedor_form.html', context)

@login_required
def fornecedor_edit(request, pk):
    fornecedor = get_object_or_404(Fornecedor, pk=pk)
    if request.method == 'POST':
        form = FornecedorForm(request.POST, instance=fornecedor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fornecedor atualizado com sucesso!')
            return redirect('ERP_ServicesBI:fornecedor_list')
    else:
        form = FornecedorForm(instance=fornecedor)
    context = {'form': form, 'titulo': 'Editar Fornecedor', 'fornecedor': fornecedor}
    return render(request, 'cadastro/fornecedor_form.html', context)

@login_required
def fornecedor_delete(request, pk):
    fornecedor = get_object_or_404(Fornecedor, pk=pk)
    if request.method == 'POST':
        fornecedor.delete()
        messages.success(request, 'Fornecedor excluído com sucesso!')
        return redirect('ERP_ServicesBI:fornecedor_list')
    context = {'fornecedor': fornecedor, 'titulo': 'Excluir Fornecedor'}
    return render(request, 'cadastro/fornecedor_confirm_delete.html', context)


# =============================================================================
# CADASTRO - CATEGORIAS
# =============================================================================

@login_required
def categoria_list(request):
    categorias = Categoria.objects.all().order_by('-id')
    context = {'categorias': categorias}
    return render(request, 'cadastro/categoria_list.html', context)

@login_required
def categoria_add(request):
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoria adicionada com sucesso!')
            return redirect('ERP_ServicesBI:categoria_list')
    else:
        form = CategoriaForm()
    context = {'form': form, 'titulo': 'Nova Categoria'}
    return render(request, 'cadastro/categoria_form.html', context)

@login_required
def categoria_edit(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoria atualizada com sucesso!')
            return redirect('ERP_ServicesBI:categoria_list')
    else:
        form = CategoriaForm(instance=categoria)
    context = {'form': form, 'titulo': 'Editar Categoria', 'categoria': categoria}
    return render(request, 'cadastro/categoria_form.html', context)

@login_required
def categoria_delete(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, 'Categoria excluída com sucesso!')
        return redirect('ERP_ServicesBI:categoria_list')
    context = {'categoria': categoria, 'titulo': 'Excluir Categoria'}
    return render(request, 'cadastro/categoria_confirm_delete.html', context)

@login_required
def categoria_create_ajax(request):
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        if nome:
            categoria, created = Categoria.objects.get_or_create(nome=nome)
            return JsonResponse({'success': True, 'id': categoria.id, 'nome': categoria.nome})
    return JsonResponse({'success': False})

@login_required
def categoria_delete_ajax(request, pk):
    if request.method == 'POST':
        try:
            categoria = Categoria.objects.get(pk=pk)
            categoria.delete()
            return JsonResponse({'success': True})
        except Categoria.DoesNotExist:
            return JsonResponse({'success': False})
    return JsonResponse({'success': False})


# =============================================================================
# CADASTRO - PRODUTOS
# =============================================================================

@login_required
def produto_list(request):
    produtos = Produto.objects.select_related('categoria', 'fornecedor').all().order_by('-id')
    context = {'produtos': produtos}
    return render(request, 'cadastro/produto_list.html', context)

@login_required
def produto_add(request):
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES)
        if form.is_valid():
            produto = form.save(commit=False)
            if not produto.codigo:
                ultimo = Produto.objects.order_by('-id').first()
                if ultimo and ultimo.codigo:
                    try:
                        num = int(''.join(filter(str.isdigit, ultimo.codigo))) + 1
                    except ValueError:
                        num = Produto.objects.count() + 1
                else:
                    num = 1
                produto.codigo = f"PROD-{num:03d}"
            produto.save()
            messages.success(request, 'Produto adicionado com sucesso!')
            return redirect('ERP_ServicesBI:produto_list')
    else:
        form = ProdutoForm()
    categorias = Categoria.objects.all().order_by('nome')
    context = {'form': form, 'titulo': 'Novo Produto', 'categorias': categorias}
    return render(request, 'cadastro/produto_form.html', context)

@login_required
def produto_edit(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    if request.method == 'POST':
        form = ProdutoForm(request.POST, instance=produto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produto atualizado com sucesso!')
            return redirect('ERP_ServicesBI:produto_list')
    else:
        form = ProdutoForm(instance=produto)
    categorias = Categoria.objects.all().order_by('nome')
    context = {'form': form, 'titulo': 'Editar Produto', 'produto': produto, 'categorias': categorias}
    return render(request, 'cadastro/produto_form.html', context)

@login_required
def produto_delete(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    if request.method == 'POST':
        produto.delete()
        messages.success(request, 'Produto excluído com sucesso!')
        return redirect('ERP_ServicesBI:produto_list')
    context = {'produto': produto, 'titulo': 'Excluir Produto'}
    return render(request, 'cadastro/produto_confirm_delete.html', context)

@login_required
def produto_json(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    return JsonResponse({
        'id': produto.id,
        'descricao': produto.descricao,
        'codigo': produto.codigo,
        'preco_venda': float(produto.preco_venda or 0),
        'estoque_atual': float(produto.estoque_atual or 0),
    })


# =============================================================================
# COMPRAS - PEDIDOS
# =============================================================================

@login_required
def pedidocompra_list(request):
    pedidos = PedidoCompra.objects.select_related('fornecedor').all().order_by('-data_pedido')
    context = {'pedidos': pedidos}
    return render(request, 'compras/pedido_compra_list.html', context)


@login_required
def pedidocompra_add(request):
    if request.method == 'POST':
        form = PedidoCompraForm(request.POST)
        if form.is_valid():
            pedido = form.save()
            messages.success(request, f'Pedido {pedido.numero} criado com sucesso!')
            return redirect('ERP_ServicesBI:pedido_compra_list')
    else:
        form = PedidoCompraForm()
    context = {'form': form, 'titulo': 'Novo Pedido de Compra'}
    return render(request, 'compras/pedido_compra_form.html', context)


@login_required
def pedidocompra_edit(request, pk):
    pedido = get_object_or_404(PedidoCompra, pk=pk)
    if request.method == 'POST':
        form = PedidoCompraForm(request.POST, instance=pedido)
        if form.is_valid():
            form.save()
            messages.success(request, 'Pedido atualizado com sucesso!')
            return redirect('ERP_ServicesBI:pedido_compra_list')
    else:
        form = PedidoCompraForm(instance=pedido)
    context = {'form': form, 'titulo': 'Editar Pedido de Compra', 'pedido': pedido}
    return render(request, 'compras/pedido_compra_form.html', context)


@login_required
def pedidocompra_delete(request, pk):
    pedido = get_object_or_404(PedidoCompra, pk=pk)
    if request.method == 'POST':
        numero = pedido.numero
        pedido.delete()
        messages.success(request, f'Pedido {numero} excluído com sucesso!')
        return redirect('ERP_ServicesBI:pedido_compra_list')
    context = {'objeto': pedido, 'titulo': 'Excluir Pedido de Compra'}
    return render(request, 'compras/pedido_compra_confirm_delete.html', context)


@login_required
def pedidocompra_item_add(request, pedido_pk):
    pedido = get_object_or_404(PedidoCompra, pk=pedido_pk)
    if request.method == 'POST':
        form = ItemPedidoCompraForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.pedido = pedido
            item.save()
            pedido.calcular_total()
            messages.success(request, 'Item adicionado com sucesso!')
            return redirect('ERP_ServicesBI:pedido_compra_edit', pk=pedido.pk)
    else:
        form = ItemPedidoCompraForm()
    context = {'form': form, 'pedido': pedido, 'titulo': 'Novo Item'}
    return render(request, 'compras/pedido_compra_item_form.html', context)


@login_required
def pedidocompra_item_edit(request, pedido_pk, item_pk):
    pedido = get_object_or_404(PedidoCompra, pk=pedido_pk)
    item = get_object_or_404(ItemPedidoCompra, pk=item_pk, pedido=pedido)
    if request.method == 'POST':
        form = ItemPedidoCompraForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            pedido.calcular_total()
            messages.success(request, 'Item atualizado com sucesso!')
            return redirect('ERP_ServicesBI:pedido_compra_edit', pk=pedido.pk)
    else:
        form = ItemPedidoCompraForm(instance=item)
    context = {'form': form, 'pedido': pedido, 'titulo': 'Editar Item'}
    return render(request, 'compras/pedido_compra_item_form.html', context)


@login_required
@require_POST
def pedidocompra_item_delete(request, pk):
    item = get_object_or_404(ItemPedidoCompra, pk=pk)
    pedido = item.pedido
    item.delete()
    pedido.calcular_total()
    messages.success(request, 'Item removido com sucesso!')
    return redirect('ERP_ServicesBI:pedido_compra_edit', pk=pedido.pk)


@login_required
def pedidocompra_gerar_nfe(request, pk):
    pedido = get_object_or_404(PedidoCompra, pk=pk)
    context = {'pedido': pedido}
    return render(request, 'compras/gerar_nfe.html', context)


# =============================================================================
# COMPRAS - NOTAS FISCAIS
# =============================================================================

@login_required
def notafiscalentrada_list(request):
    notas = NotaFiscalEntrada.objects.select_related('fornecedor').all().order_by('-data_entrada')
    context = {'notas': notas}
    return render(request, 'compras/nota_fiscal_entrada_list.html', context)


@login_required
def notafiscalentrada_add(request):
    if request.method == 'POST':
        form = NotaFiscalEntradaForm(request.POST)
        if form.is_valid():
            nota = form.save()
            messages.success(request, f'NF {nota.numero_nf} criada com sucesso!')
            return redirect('ERP_ServicesBI:nota_fiscal_entrada_list')
    else:
        form = NotaFiscalEntradaForm()
    context = {'form': form, 'titulo': 'Nova Nota Fiscal de Entrada'}
    return render(request, 'compras/nota_fiscal_entrada_form.html', context)


@login_required
def notafiscalentrada_edit(request, pk):
    nota = get_object_or_404(NotaFiscalEntrada, pk=pk)
    if request.method == 'POST':
        form = NotaFiscalEntradaForm(request.POST, instance=nota)
        if form.is_valid():
            form.save()
            messages.success(request, 'Nota fiscal atualizada com sucesso!')
            return redirect('ERP_ServicesBI:nota_fiscal_entrada_list')
    else:
        form = NotaFiscalEntradaForm(instance=nota)
    context = {'form': form, 'titulo': 'Editar Nota Fiscal de Entrada', 'nota': nota}
    return render(request, 'compras/nota_fiscal_entrada_form.html', context)


@login_required
def notafiscalentrada_delete(request, pk):
    nota = get_object_or_404(NotaFiscalEntrada, pk=pk)
    if request.method == 'POST':
        numero = nota.numero_nf
        nota.delete()
        messages.success(request, f'NF {numero} excluída com sucesso!')
        return redirect('ERP_ServicesBI:nota_fiscal_entrada_list')
    context = {'objeto': nota, 'titulo': 'Excluir Nota Fiscal de Entrada'}
    return render(request, 'compras/nota_fiscal_entrada_confirm_delete.html', context)


@login_required
def notafiscalentrada_item_add(request, nota_pk):
    nota = get_object_or_404(NotaFiscalEntrada, pk=nota_pk)
    if request.method == 'POST':
        form = ItemNotaFiscalEntradaForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.nota_fiscal = nota
            item.save()
            nota.calcular_total()
            messages.success(request, 'Item adicionado com sucesso!')
            return redirect('ERP_ServicesBI:nota_fiscal_entrada_edit', pk=nota.pk)
    else:
        form = ItemNotaFiscalEntradaForm()
    context = {'form': form, 'nota': nota, 'titulo': 'Novo Item'}
    return render(request, 'compras/nota_fiscal_entrada_item_form.html', context)


@login_required
@require_POST
def notafiscalentrada_item_delete(request, pk):
    item = get_object_or_404(ItemNotaFiscalEntrada, pk=pk)
    nota = item.nota_fiscal
    item.delete()
    nota.calcular_total()
    messages.success(request, 'Item removido com sucesso!')
    return redirect('ERP_ServicesBI:nota_fiscal_entrada_edit', pk=nota.pk)


@login_required
def relatorio_compras(request):
    context = {}
    return render(request, 'compras/relatorio_compras.html', context)


# =============================================================================
# COTAÇÃO COMPARATIVA - WIZARD (NOVO)
# =============================================================================

@login_required
def cotacao_lista(request):
    """Lista todas as cotações"""
    cotacoes = CotacaoMae.objects.select_related('solicitante').prefetch_related(
        'itens_solicitados', 'cotacoes_fornecedor'
    ).order_by('-data_solicitacao')
    
    context = {
        'cotacoes': cotacoes,
        'titulo': 'Cotações Comparativas'
    }
    return render(request, 'compras/cotacao_lista.html', context)


@login_required
def cotacao_wizard(request, pk=None):
    """Wizard de cotação - tela única com 5 etapas"""
    if pk:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        itens = cotacao.itens_solicitados.select_related('produto').all()
        cotacoes_fornecedor = cotacao.cotacoes_fornecedor.select_related('fornecedor').prefetch_related('itens').all()
    else:
        cotacao = None
        itens = []
        cotacoes_fornecedor = []
    
    produtos = Produto.objects.filter(ativo=True).order_by('descricao')
    fornecedores = Fornecedor.objects.filter(ativo=True).order_by('nome_fantasia', 'nome_razao_social')
    
    comparativo = []
    if cotacao and cotacoes_fornecedor.exists():
        comparativo = montar_comparativo(cotacao)
    
    context = {
        'cotacao': cotacao,
        'itens': itens,
        'cotacoes_fornecedor': cotacoes_fornecedor,
        'comparativo': comparativo,
        'produtos': produtos,
        'fornecedores': fornecedores,
        'titulo': f'Cotação {cotacao.numero}' if cotacao else 'Nova Cotação'
    }
    return render(request, 'compras/cotacao_wizard.html', context)


def montar_comparativo(cotacao):
    """Monta estrutura de dados para o quadro comparativo"""
    itens_solicitados = cotacao.itens_solicitados.select_related('produto').all()
    cotacoes_fornecedor = cotacao.cotacoes_fornecedor.select_related('fornecedor').prefetch_related('itens').all()
    
    comparativo = []
    
    for item in itens_solicitados:
        linha = {'item': item, 'fornecedores': [], 'menor_preco': None, 'menor_prazo': None}
        precos = []
        prazos = []
        
        for cot_forn in cotacoes_fornecedor:
            item_cot = cot_forn.itens.filter(item_solicitado=item).first()
            
            dados_fornecedor = {
                'cotacao_fornecedor': cot_forn,
                'item_cotacao': item_cot,
                'preco_unitario': item_cot.preco_unitario if item_cot else None,
                'preco_total': item_cot.preco_total if item_cot else None,
                'disponivel': item_cot.disponivel if item_cot else False,
                'prazo': item_cot.prazo_entrega_item or cot_forn.prazo_entrega_dias if item_cot else None,
                'selecionado': item_cot.selecionado if item_cot else False,
                'sugerido': item_cot.sugerido if item_cot else False,
                'melhor_preco': False,
                'melhor_prazo': False
            }
            
            if item_cot and item_cot.disponivel and item_cot.preco_unitario:
                precos.append((cot_forn.id, float(item_cot.preco_unitario)))
                prazo = item_cot.prazo_entrega_item or cot_forn.prazo_entrega_dias
                if prazo:
                    prazos.append((cot_forn.id, prazo))
            
            linha['fornecedores'].append(dados_fornecedor)
        
        if precos:
            menor_preco_id = min(precos, key=lambda x: x[1])[0]
            linha['menor_preco'] = menor_preco_id
            for f in linha['fornecedores']:
                if f['cotacao_fornecedor'].id == menor_preco_id:
                    f['melhor_preco'] = True
        
        if prazos:
            menor_prazo_id = min(prazos, key=lambda x: x[1])[0]
            linha['menor_prazo'] = menor_prazo_id
            for f in linha['fornecedores']:
                if f['cotacao_fornecedor'].id == menor_prazo_id:
                    f['melhor_prazo'] = True
        
        comparativo.append(linha)
    
    return comparativo


@login_required
@require_POST
def cotacao_salvar_dados(request, pk=None):
    """Salva dados básicos da cotação (título, setor, etc)"""
    try:
        data = json.loads(request.body)
        
        if pk and pk != 0:
            cotacao = get_object_or_404(CotacaoMae, pk=pk)
        else:
            cotacao = CotacaoMae(solicitante=request.user)
        
        cotacao.titulo = data.get('titulo', '')
        cotacao.setor = data.get('setor', '')
        cotacao.observacoes = data.get('observacoes', '')
        
        if data.get('data_limite_resposta'):
            cotacao.data_limite_resposta = data['data_limite_resposta']
        
        cotacao.save()
        
        return JsonResponse({
            'success': True,
            'cotacao_id': cotacao.pk,
            'numero': cotacao.numero,
            'message': 'Dados salvos com sucesso!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def cotacao_salvar_itens(request, pk):
    """Salva itens solicitados da cotação"""
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        data = json.loads(request.body)
        itens = data.get('itens', [])
        
        with transaction.atomic():
            ids_recebidos = [item.get('id') for item in itens if item.get('id')]
            cotacao.itens_solicitados.exclude(id__in=ids_recebidos).delete()
            
            for item_data in itens:
                item_id = item_data.get('id')
                
                if item_id:
                    item = ItemSolicitado.objects.get(pk=item_id, cotacao_mae=cotacao)
                else:
                    item = ItemSolicitado(cotacao_mae=cotacao)
                
                produto_id = item_data.get('produto_id')
                if produto_id:
                    item.produto_id = produto_id
                    item.descricao_manual = ''
                else:
                    item.produto = None
                    item.descricao_manual = item_data.get('descricao_manual', '')
                
                item.quantidade = Decimal(str(item_data.get('quantidade', 1)))
                item.unidade_medida = item_data.get('unidade_medida', 'UN')
                item.observacao = item_data.get('observacao', '')
                item.save()
        
        itens_atualizados = []
        for item in cotacao.itens_solicitados.select_related('produto').all():
            itens_atualizados.append({
                'id': item.id,
                'produto_id': item.produto_id,
                'descricao': item.descricao_display,
                'quantidade': float(item.quantidade),
                'unidade_medida': item.unidade_medida
            })
        
        return JsonResponse({
            'success': True,
            'itens': itens_atualizados,
            'message': 'Itens salvos com sucesso!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def cotacao_importar_fornecedor(request, pk):
    """Importa arquivo de cotação do fornecedor (CSV, Excel, PDF)"""
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        
        fornecedor_id = request.POST.get('fornecedor_id')
        arquivo = request.FILES.get('arquivo')
        
        if not fornecedor_id:
            return JsonResponse({'success': False, 'error': 'Selecione um fornecedor'}, status=400)
        
        fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_id)
        
        cotacao_forn, created = CotacaoFornecedor.objects.get_or_create(
            cotacao_mae=cotacao,
            fornecedor=fornecedor,
            defaults={
                'status': 'importada',
                'data_recebimento': timezone.now().date()
            }
        )
        
        if arquivo:
            cotacao_forn.arquivo_origem = arquivo
            cotacao_forn.save()
            processar_arquivo_cotacao(cotacao, cotacao_forn, arquivo)
            cotacao_forn.calcular_total()
        
        cotacao_forn.prazo_entrega_dias = int(request.POST.get('prazo_entrega', 0) or 0)
        cotacao_forn.condicao_pagamento = request.POST.get('condicao_pagamento', '')
        cotacao_forn.percentual_desconto = Decimal(request.POST.get('desconto', 0) or 0)
        cotacao_forn.valor_frete = Decimal(request.POST.get('frete', 0) or 0)
        cotacao_forn.nota_confiabilidade = int(request.POST.get('confiabilidade', 5) or 5)
        cotacao_forn.observacoes = request.POST.get('observacoes', '')
        cotacao_forn.status = 'processada'
        cotacao_forn.save()
        cotacao_forn.calcular_total()
        
        cotacao.status = 'respondida'
        cotacao.save()
        
        return JsonResponse({
            'success': True,
            'cotacao_fornecedor_id': cotacao_forn.pk,
            'fornecedor_nome': fornecedor.nome_fantasia or fornecedor.nome_razao_social,
            'total_itens': cotacao_forn.itens.count(),
            'valor_total': float(cotacao_forn.valor_total_liquido),
            'message': 'Cotação importada com sucesso!'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


def processar_arquivo_cotacao(cotacao_mae, cotacao_forn, arquivo):
    """Processa arquivo de cotação (CSV, Excel)"""
    nome_arquivo = arquivo.name.lower()
    cotacao_forn.itens.all().delete()
    
    if nome_arquivo.endswith('.csv'):
        processar_csv(cotacao_mae, cotacao_forn, arquivo)
    elif nome_arquivo.endswith(('.xlsx', '.xls')):
        processar_excel(cotacao_mae, cotacao_forn, arquivo)
    else:
        processar_csv(cotacao_mae, cotacao_forn, arquivo)


def processar_csv(cotacao_mae, cotacao_forn, arquivo):
    """Processa arquivo CSV"""
    try:
        conteudo = arquivo.read().decode('utf-8')
    except UnicodeDecodeError:
        arquivo.seek(0)
        conteudo = arquivo.read().decode('latin-1')
    
    primeira_linha = conteudo.split('\n')[0]
    delimitador = ';' if ';' in primeira_linha else ','
    
    leitor = csv.DictReader(io.StringIO(conteudo), delimiter=delimitador)
    
    if leitor.fieldnames:
        leitor.fieldnames = [normalizar_nome_coluna(col) for col in leitor.fieldnames]
    
    for row in leitor:
        criar_item_cotacao(cotacao_mae, cotacao_forn, row)


def processar_excel(cotacao_mae, cotacao_forn, arquivo):
    """Processa arquivo Excel"""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(arquivo, data_only=True)
        ws = wb.active
        headers = [normalizar_nome_coluna(str(cell.value or '')) for cell in ws[1]]
        for row in ws.iter_rows(min_row=2, values_only=True):
            row_dict = dict(zip(headers, row))
            criar_item_cotacao(cotacao_mae, cotacao_forn, row_dict)
    except ImportError:
        try:
            import pandas as pd
            df = pd.read_excel(arquivo)
            for _, row in df.iterrows():
                row_dict = {normalizar_nome_coluna(str(k)): v for k, v in row.items()}
                criar_item_cotacao(cotacao_mae, cotacao_forn, row_dict)
        except ImportError:
            pass


def normalizar_nome_coluna(nome):
    """Normaliza nome de coluna"""
    import unicodedata
    nome = str(nome).lower().strip()
    nome = unicodedata.normalize('NFD', nome)
    nome = ''.join(c for c in nome if not unicodedata.combining(c))
    return nome


def criar_item_cotacao(cotacao_mae, cotacao_forn, row):
    """Cria item de cotação a partir de uma linha do arquivo"""
    descricao = (
        row.get('descricao') or row.get('produto') or row.get('item') or 
        row.get('material') or row.get('nome') or ''
    )
    
    quantidade_str = str(row.get('quantidade') or row.get('qtd') or row.get('qtde') or 1)
    preco_str = str(row.get('preco_unitario') or row.get('preco') or row.get('valor_unitario') or row.get('valor') or 0)
    codigo = str(row.get('codigo') or row.get('cod') or row.get('ref') or '')
    unidade = str(row.get('unidade') or row.get('un') or row.get('und') or 'UN')
    
    descricao = str(descricao).strip() if descricao else ''
    if not descricao:
        return None
    
    try:
        quantidade = Decimal(str(quantidade_str).replace(',', '.').replace(' ', ''))
    except:
        quantidade = Decimal('1')
    
    try:
        preco = str(preco_str).replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
        preco_unitario = Decimal(preco)
    except:
        preco_unitario = Decimal('0')
    
    item_solicitado = None
    match_score = 0
    
    for item_sol in cotacao_mae.itens_solicitados.select_related('produto').all():
        desc_sol = item_sol.descricao_display.lower()
        desc_forn = descricao.lower()
        
        if desc_sol == desc_forn:
            item_solicitado = item_sol
            match_score = 100
            break
        
        if desc_sol in desc_forn or desc_forn in desc_sol:
            if match_score < 80:
                item_solicitado = item_sol
                match_score = 80
        
        if item_sol.produto and codigo:
            if item_sol.produto.codigo.lower() == codigo.lower():
                item_solicitado = item_sol
                match_score = 95
                break
    
    ItemCotacaoFornecedor.objects.create(
        cotacao_fornecedor=cotacao_forn,
        item_solicitado=item_solicitado,
        descricao_fornecedor=descricao,
        codigo_fornecedor=codigo,
        quantidade=quantidade,
        unidade_medida=unidade,
        preco_unitario=preco_unitario,
        preco_total=quantidade * preco_unitario,
        disponivel=True,
        match_automatico=(item_solicitado is not None),
        match_score=match_score
    )


@login_required
@require_POST
def cotacao_remover_fornecedor(request, pk, fornecedor_pk):
    """Remove cotação de um fornecedor"""
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        cotacao_forn = get_object_or_404(CotacaoFornecedor, cotacao_mae=cotacao, fornecedor_id=fornecedor_pk)
        cotacao_forn.delete()
        return JsonResponse({'success': True, 'message': 'Fornecedor removido com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def cotacao_calcular_sugestoes(request, pk):
    """Calcula sugestões automáticas baseado em preço, prazo e confiabilidade"""
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        peso_preco = float(request.POST.get('peso_preco', 50)) / 100
        peso_prazo = float(request.POST.get('peso_prazo', 30)) / 100
        peso_confiabilidade = float(request.POST.get('peso_confiabilidade', 20)) / 100
        
        with transaction.atomic():
            ItemCotacaoFornecedor.objects.filter(
                cotacao_fornecedor__cotacao_mae=cotacao
            ).update(melhor_preco=False, melhor_prazo=False, sugerido=False)
            
            for item_sol in cotacao.itens_solicitados.all():
                itens_cot = ItemCotacaoFornecedor.objects.filter(
                    cotacao_fornecedor__cotacao_mae=cotacao,
                    item_solicitado=item_sol,
                    disponivel=True
                ).select_related('cotacao_fornecedor')
                
                if not itens_cot.exists():
                    continue
                
                menor_preco = itens_cot.order_by('preco_unitario').first()
                if menor_preco:
                    menor_preco.melhor_preco = True
                    menor_preco.save()
                
                itens_com_prazo = []
                for item in itens_cot:
                    prazo = item.prazo_entrega_item or item.cotacao_fornecedor.prazo_entrega_dias
                    if prazo:
                        itens_com_prazo.append((item, prazo))
                
                if itens_com_prazo:
                    menor_prazo_item = min(itens_com_prazo, key=lambda x: x[1])[0]
                    menor_prazo_item.melhor_prazo = True
                    menor_prazo_item.save()
                
                scores = []
                precos = [float(i.preco_unitario) for i in itens_cot]
                max_preco = max(precos) if precos else 1
                min_preco = min(precos) if precos else 0
                range_preco = max_preco - min_preco if max_preco != min_preco else 1
                
                for item in itens_cot:
                    prazo = item.prazo_entrega_item or item.cotacao_fornecedor.prazo_entrega_dias or 30
                    confiabilidade = item.cotacao_fornecedor.nota_confiabilidade or 5
                    
                    score_preco = 1 - ((float(item.preco_unitario) - min_preco) / range_preco)
                    score_prazo = max(0, 1 - (prazo / 60))
                    score_conf = confiabilidade / 10
                    
                    score_final = (
                        score_preco * peso_preco +
                        score_prazo * peso_prazo +
                        score_conf * peso_confiabilidade
                    )
                    scores.append((item, score_final))
                
                if scores:
                    melhor = max(scores, key=lambda x: x[1])[0]
                    melhor.sugerido = True
                    melhor.save()
        
        cotacao.status = 'em_analise'
        cotacao.save()
        
        return JsonResponse({'success': True, 'message': 'Sugestões calculadas com sucesso!'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def cotacao_salvar_selecao(request, pk):
    """Salva itens selecionados para compra"""
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        data = json.loads(request.body)
        itens_selecionados = data.get('itens_selecionados', [])
        
        with transaction.atomic():
            ItemCotacaoFornecedor.objects.filter(
                cotacao_fornecedor__cotacao_mae=cotacao
            ).update(selecionado=False)
            
            ItemCotacaoFornecedor.objects.filter(
                id__in=itens_selecionados
            ).update(selecionado=True)
        
        return JsonResponse({'success': True, 'message': 'Seleção salva com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def cotacao_gerar_pedidos(request, pk):
    """Gera pedidos de compra a partir dos itens selecionados"""
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        
        itens_selecionados = ItemCotacaoFornecedor.objects.filter(
            cotacao_fornecedor__cotacao_mae=cotacao,
            selecionado=True
        ).select_related('cotacao_fornecedor__fornecedor', 'item_solicitado__produto')
        
        if not itens_selecionados.exists():
            return JsonResponse({'success': False, 'error': 'Nenhum item selecionado'}, status=400)
        
        itens_por_fornecedor = {}
        for item in itens_selecionados:
            forn_id = item.cotacao_fornecedor.fornecedor_id
            if forn_id not in itens_por_fornecedor:
                itens_por_fornecedor[forn_id] = {
                    'fornecedor': item.cotacao_fornecedor.fornecedor,
                    'cotacao_fornecedor': item.cotacao_fornecedor,
                    'itens': []
                }
            itens_por_fornecedor[forn_id]['itens'].append(item)
        
        pedidos_gerados = []
        
        with transaction.atomic():
            for forn_id, dados in itens_por_fornecedor.items():
                fornecedor = dados['fornecedor']
                cot_forn = dados['cotacao_fornecedor']
                itens = dados['itens']
                
                prazo = cot_forn.prazo_entrega_dias or 15
                data_entrega = timezone.now().date() + timedelta(days=prazo)
                
                pedido = PedidoCompra.objects.create(
                    fornecedor=fornecedor,
                    cotacao_mae=cotacao,
                    cotacao_fornecedor=cot_forn,
                    data_prevista_entrega=data_entrega,
                    condicao_pagamento=cot_forn.condicao_pagamento,
                    observacoes=f'Gerado a partir da cotação {cotacao.numero}',
                    status='pendente'
                )
                
                for item_cot in itens:
                    produto = None
                    if item_cot.item_solicitado and item_cot.item_solicitado.produto:
                        produto = item_cot.item_solicitado.produto
                    else:
                        produto, _ = Produto.objects.get_or_create(
                            descricao=item_cot.descricao_fornecedor[:255],
                            defaults={'unidade': item_cot.unidade_medida or 'UN', 'ativo': True}
                        )
                    
                    ItemPedidoCompra.objects.create(
                        pedido=pedido,
                        produto=produto,
                        item_cotacao_origem=item_cot,
                        descricao=item_cot.descricao_fornecedor,
                        quantidade=item_cot.quantidade,
                        preco_unitario=item_cot.preco_unitario
                    )
                    
                    item_cot.pedido_compra = pedido
                    item_cot.save()
                
                pedido.calcular_total()
                
                pedidos_gerados.append({
                    'id': pedido.pk,
                    'numero': pedido.numero,
                    'fornecedor': fornecedor.nome_fantasia or fornecedor.nome_razao_social,
                    'total_itens': len(itens),
                    'valor_total': float(pedido.valor_total)
                })
            
            cotacao.status = 'concluida'
            cotacao.save()
        
        return JsonResponse({
            'success': True,
            'pedidos': pedidos_gerados,
            'message': f'{len(pedidos_gerados)} pedido(s) gerado(s) com sucesso!'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def cotacao_excluir(request, pk):
    """Exclui cotação"""
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        cotacao.delete()
        return JsonResponse({'success': True, 'message': 'Cotação excluída com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_GET
def cotacao_copiar_lista_email(request, pk):
    """Gera texto formatado para email"""
    cotacao = get_object_or_404(CotacaoMae, pk=pk)
    
    linhas = [
        f"Solicitação de Cotação: {cotacao.numero}",
        f"Título: {cotacao.titulo}",
        f"Setor: {cotacao.setor}",
        f"Data Limite: {cotacao.data_limite_resposta.strftime('%d/%m/%Y') if cotacao.data_limite_resposta else 'Não definida'}",
        "",
        "ITENS SOLICITADOS:",
        "-" * 50,
    ]
    
    for i, item in enumerate(cotacao.itens_solicitados.all(), 1):
        linhas.append(f"{i}. {item.descricao_display}")
        linhas.append(f"   Quantidade: {item.quantidade} {item.unidade_medida}")
        if item.observacao:
            linhas.append(f"   Obs: {item.observacao}")
        linhas.append("")
    
    linhas.extend([
        "-" * 50,
        "Por favor, enviar cotação com preços unitários e prazo de entrega.",
        "",
        "Atenciosamente,",
        cotacao.solicitante.get_full_name() or cotacao.solicitante.username
    ])
    
    return JsonResponse({'success': True, 'texto': '\n'.join(linhas)})


@login_required
@require_GET
def cotacao_copiar_lista_whatsapp(request, pk):
    """Gera texto formatado para WhatsApp"""
    cotacao = get_object_or_404(CotacaoMae, pk=pk)
    
    linhas = [
        f"*Solicitação de Cotação: {cotacao.numero}*",
        f"📋 {cotacao.titulo}",
        f"🏢 Setor: {cotacao.setor}",
        "",
        "*ITENS:*",
    ]
    
    for i, item in enumerate(cotacao.itens_solicitados.all(), 1):
        linhas.append(f"{i}. {item.descricao_display} - {item.quantidade} {item.unidade_medida}")
    
    linhas.extend([
        "",
        "📅 Aguardo cotação com preços e prazo.",
        "Obrigado!"
    ])
    
    return JsonResponse({'success': True, 'texto': '\n'.join(linhas)})


# =============================================================================
# VENDAS - ORÇAMENTOS
# =============================================================================

@login_required
def orcamento_list(request):
    orcamentos = Orcamento.objects.select_related('cliente', 'vendedor').all().order_by('-data_orcamento')
    context = {'orcamentos': orcamentos}
    return render(request, 'vendas/orcamento_list.html', context)

@login_required
def orcamento_add(request):
    if request.method == 'POST':
        form = OrcamentoForm(request.POST)
        if form.is_valid():
            orcamento = form.save()
            messages.success(request, f'Orçamento {orcamento.numero} criado com sucesso!')
            return redirect('ERP_ServicesBI:orcamento_list')
    else:
        form = OrcamentoForm()
    context = {'form': form, 'titulo': 'Novo Orçamento'}
    return render(request, 'vendas/orcamento_form.html', context)

@login_required
def orcamento_edit(request, pk):
    orcamento = get_object_or_404(Orcamento, pk=pk)
    if request.method == 'POST':
        form = OrcamentoForm(request.POST, instance=orcamento)
        if form.is_valid():
            form.save()
            messages.success(request, 'Orçamento atualizado com sucesso!')
            return redirect('ERP_ServicesBI:orcamento_list')
    else:
        form = OrcamentoForm(instance=orcamento)
    context = {'form': form, 'titulo': 'Editar Orçamento', 'orcamento': orcamento}
    return render(request, 'vendas/orcamento_form.html', context)

@login_required
def orcamento_delete(request, pk):
    orcamento = get_object_or_404(Orcamento, pk=pk)
    if request.method == 'POST':
        numero = orcamento.numero
        orcamento.delete()
        messages.success(request, f'Orçamento {numero} excluído com sucesso!')
        return redirect('ERP_ServicesBI:orcamento_list')
    context = {'objeto': orcamento, 'titulo': 'Excluir Orçamento'}
    return render(request, 'vendas/confirm_delete.html', context)

@login_required
def orcamento_item_add(request, orcamento_pk):
    orcamento = get_object_or_404(Orcamento, pk=orcamento_pk)
    if request.method == 'POST':
        form = ItemOrcamentoForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.orcamento = orcamento
            item.save()
            orcamento.calcular_total()
            messages.success(request, 'Item adicionado com sucesso!')
            return redirect('ERP_ServicesBI:orcamento_edit', pk=orcamento.pk)
    else:
        form = ItemOrcamentoForm()
    context = {'form': form, 'orcamento': orcamento, 'titulo': 'Novo Item'}
    return render(request, 'vendas/item_form.html', context)

@login_required
@require_POST
def orcamento_item_delete(request, pk):
    item = get_object_or_404(ItemOrcamento, pk=pk)
    orcamento = item.orcamento
    item.delete()
    orcamento.calcular_total()
    messages.success(request, 'Item removido com sucesso!')
    return redirect('ERP_ServicesBI:orcamento_edit', pk=orcamento.pk)

@login_required
def orcamento_gerar_pedido(request, pk):
    orcamento = get_object_or_404(Orcamento, pk=pk)
    context = {'orcamento': orcamento}
    return render(request, 'vendas/gerar_pedido.html', context)


# =============================================================================
# VENDAS - PEDIDOS
# =============================================================================

@login_required
def pedidovenda_list(request):
    pedidos = PedidoVenda.objects.select_related('cliente', 'vendedor').all().order_by('-data_pedido')
    context = {'pedidos': pedidos}
    return render(request, 'vendas/pedidovenda_list.html', context)

@login_required
def pedidovenda_add(request):
    if request.method == 'POST':
        form = PedidoVendaForm(request.POST)
        if form.is_valid():
            pedido = form.save()
            messages.success(request, f'Pedido {pedido.numero} criado com sucesso!')
            return redirect('ERP_ServicesBI:pedidovenda_list')
    else:
        form = PedidoVendaForm()
    context = {'form': form, 'titulo': 'Novo Pedido de Venda'}
    return render(request, 'vendas/pedidovenda_form.html', context)

@login_required
def pedidovenda_edit(request, pk):
    pedido = get_object_or_404(PedidoVenda, pk=pk)
    if request.method == 'POST':
        form = PedidoVendaForm(request.POST, instance=pedido)
        if form.is_valid():
            form.save()
            messages.success(request, 'Pedido atualizado com sucesso!')
            return redirect('ERP_ServicesBI:pedidovenda_list')
    else:
        form = PedidoVendaForm(instance=pedido)
    context = {'form': form, 'titulo': 'Editar Pedido de Venda', 'pedido': pedido}
    return render(request, 'vendas/pedidovenda_form.html', context)

@login_required
def pedidovenda_delete(request, pk):
    pedido = get_object_or_404(PedidoVenda, pk=pk)
    if request.method == 'POST':
        numero = pedido.numero
        pedido.delete()
        messages.success(request, f'Pedido {numero} excluído com sucesso!')
        return redirect('ERP_ServicesBI:pedidovenda_list')
    context = {'objeto': pedido, 'titulo': 'Excluir Pedido de Venda'}
    return render(request, 'vendas/confirm_delete.html', context)

@login_required
def pedidovenda_item_add(request, pedido_pk):
    pedido = get_object_or_404(PedidoVenda, pk=pedido_pk)
    if request.method == 'POST':
        form = ItemPedidoVendaForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.pedido = pedido
            item.save()
            pedido.calcular_total()
            messages.success(request, 'Item adicionado com sucesso!')
            return redirect('ERP_ServicesBI:pedidovenda_edit', pk=pedido.pk)
    else:
        form = ItemPedidoVendaForm()
    context = {'form': form, 'pedido': pedido, 'titulo': 'Novo Item'}
    return render(request, 'vendas/item_form.html', context)

@login_required
@require_POST
def pedidovenda_item_delete(request, pk):
    item = get_object_or_404(ItemPedidoVenda, pk=pk)
    pedido = item.pedido
    item.delete()
    pedido.calcular_total()
    messages.success(request, 'Item removido com sucesso!')
    return redirect('ERP_ServicesBI:pedidovenda_edit', pk=pedido.pk)

@login_required
def pedidovenda_gerar_nfe(request, pk):
    pedido = get_object_or_404(PedidoVenda, pk=pk)
    context = {'pedido': pedido}
    return render(request, 'vendas/gerar_nfe.html', context)


# =============================================================================
# VENDAS - NOTAS FISCAIS
# =============================================================================

@login_required
def notafiscalsaida_list(request):
    notas = NotaFiscalSaida.objects.select_related('cliente').all().order_by('-data_emissao')
    context = {'notas': notas}
    return render(request, 'vendas/notafiscal_list.html', context)

@login_required
def notafiscalsaida_add(request):
    if request.method == 'POST':
        form = NotaFiscalSaidaForm(request.POST)
        if form.is_valid():
            nota = form.save()
            messages.success(request, f'NF {nota.numero_nf} criada com sucesso!')
            return redirect('ERP_ServicesBI:notafiscalsaida_list')
    else:
        form = NotaFiscalSaidaForm()
    context = {'form': form, 'titulo': 'Nova Nota Fiscal de Saída'}
    return render(request, 'vendas/notafiscal_form.html', context)

@login_required
def notafiscalsaida_edit(request, pk):
    nota = get_object_or_404(NotaFiscalSaida, pk=pk)
    if request.method == 'POST':
        form = NotaFiscalSaidaForm(request.POST, instance=nota)
        if form.is_valid():
            form.save()
            messages.success(request, 'Nota fiscal atualizada com sucesso!')
            return redirect('ERP_ServicesBI:notafiscalsaida_list')
    else:
        form = NotaFiscalSaidaForm(instance=nota)
    context = {'form': form, 'titulo': 'Editar Nota Fiscal de Saída', 'nota': nota}
    return render(request, 'vendas/notafiscal_form.html', context)

@login_required
def notafiscalsaida_delete(request, pk):
    nota = get_object_or_404(NotaFiscalSaida, pk=pk)
    if request.method == 'POST':
        numero = nota.numero_nf
        nota.delete()
        messages.success(request, f'NF {numero} excluída com sucesso!')
        return redirect('ERP_ServicesBI:notafiscalsaida_list')
    context = {'objeto': nota, 'titulo': 'Excluir Nota Fiscal de Saída'}
    return render(request, 'vendas/confirm_delete.html', context)

@login_required
def notafiscalsaida_item_add(request, nota_pk):
    nota = get_object_or_404(NotaFiscalSaida, pk=nota_pk)
    if request.method == 'POST':
        form = ItemNotaFiscalSaidaForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.nota_fiscal = nota
            item.save()
            nota.calcular_total()
            messages.success(request, 'Item adicionado com sucesso!')
            return redirect('ERP_ServicesBI:notafiscalsaida_edit', pk=nota.pk)
    else:
        form = ItemNotaFiscalSaidaForm()
    context = {'form': form, 'nota': nota, 'titulo': 'Novo Item'}
    return render(request, 'vendas/item_form.html', context)

@login_required
@require_POST
def notafiscalsaida_item_delete(request, pk):
    item = get_object_or_404(ItemNotaFiscalSaida, pk=pk)
    nota = item.nota_fiscal
    item.delete()
    nota.calcular_total()
    messages.success(request, 'Item removido com sucesso!')
    return redirect('ERP_ServicesBI:notafiscalsaida_edit', pk=nota.pk)

@login_required
def relatorio_vendas(request):
    context = {}
    return render(request, 'vendas/relatorio.html', context)


# =============================================================================
# FINANCEIRO
# =============================================================================

@login_required
def contareceber_list(request):
    contas = ContaReceber.objects.select_related('cliente').all().order_by('data_vencimento')
    context = {'contas': contas}
    return render(request, 'financeiro/contareceber_list.html', context)

@login_required
def contareceber_add(request):
    if request.method == 'POST':
        form = ContaReceberForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conta a receber criada com sucesso!')
            return redirect('ERP_ServicesBI:contareceber_list')
    else:
        form = ContaReceberForm()
    context = {'form': form, 'titulo': 'Nova Conta a Receber'}
    return render(request, 'financeiro/contareceber_form.html', context)

@login_required
def contareceber_edit(request, pk):
    conta = get_object_or_404(ContaReceber, pk=pk)
    if request.method == 'POST':
        form = ContaReceberForm(request.POST, instance=conta)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conta atualizada com sucesso!')
            return redirect('ERP_ServicesBI:contareceber_list')
    else:
        form = ContaReceberForm(instance=conta)
    context = {'form': form, 'titulo': 'Editar Conta a Receber', 'conta': conta}
    return render(request, 'financeiro/contareceber_form.html', context)

@login_required
def contareceber_delete(request, pk):
    conta = get_object_or_404(ContaReceber, pk=pk)
    if request.method == 'POST':
        conta.delete()
        messages.success(request, 'Conta excluída com sucesso!')
        return redirect('ERP_ServicesBI:contareceber_list')
    context = {'objeto': conta, 'titulo': 'Excluir Conta a Receber'}
    return render(request, 'financeiro/confirm_delete.html', context)

@login_required
def contareceber_baixar(request, pk):
    conta = get_object_or_404(ContaReceber, pk=pk)
    context = {'conta': conta}
    return render(request, 'financeiro/contareceber_baixar.html', context)

@login_required
def contapagar_list(request):
    contas = ContaPagar.objects.select_related('fornecedor').all().order_by('data_vencimento')
    context = {'contas': contas}
    return render(request, 'financeiro/contapagar_list.html', context)

@login_required
def contapagar_add(request):
    if request.method == 'POST':
        form = ContaPagarForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conta a pagar criada com sucesso!')
            return redirect('ERP_ServicesBI:contapagar_list')
    else:
        form = ContaPagarForm()
    context = {'form': form, 'titulo': 'Nova Conta a Pagar'}
    return render(request, 'financeiro/contapagar_form.html', context)

@login_required
def contapagar_edit(request, pk):
    conta = get_object_or_404(ContaPagar, pk=pk)
    if request.method == 'POST':
        form = ContaPagarForm(request.POST, instance=conta)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conta atualizada com sucesso!')
            return redirect('ERP_ServicesBI:contapagar_list')
    else:
        form = ContaPagarForm(instance=conta)
    context = {'form': form, 'titulo': 'Editar Conta a Pagar', 'conta': conta}
    return render(request, 'financeiro/contapagar_form.html', context)

@login_required
def contapagar_delete(request, pk):
    conta = get_object_or_404(ContaPagar, pk=pk)
    if request.method == 'POST':
        conta.delete()
        messages.success(request, 'Conta excluída com sucesso!')
        return redirect('ERP_ServicesBI:contapagar_list')
    context = {'objeto': conta, 'titulo': 'Excluir Conta a Pagar'}
    return render(request, 'financeiro/confirm_delete.html', context)

@login_required
def contapagar_baixar(request, pk):
    conta = get_object_or_404(ContaPagar, pk=pk)
    context = {'conta': conta}
    return render(request, 'financeiro/contapagar_baixar.html', context)

@login_required
def movimentocaixa_add(request):
    if request.method == 'POST':
        form = MovimentoCaixaForm(request.POST)
        if form.is_valid():
            movimentacao = form.save(commit=False)
            movimentacao.usuario = request.user
            movimentacao.save()
            messages.success(request, 'Movimento registrado com sucesso!')
            return redirect('ERP_ServicesBI:fluxo_caixa')
    else:
        form = MovimentoCaixaForm()
    context = {'form': form, 'titulo': 'Novo Movimento de Caixa'}
    return render(request, 'financeiro/movimentocaixa_form.html', context)

@login_required
def categoriafinanceira_list(request):
    categorias = CategoriaFinanceira.objects.all().order_by('codigo')
    context = {'categorias': categorias}
    return render(request, 'financeiro/categoriafinanceira_list.html', context)

@login_required
def categoriafinanceira_add(request):
    if request.method == 'POST':
        form = CategoriaFinanceiraForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoria criada com sucesso!')
            return redirect('ERP_ServicesBI:categoriafinanceira_list')
    else:
        form = CategoriaFinanceiraForm()
    context = {'form': form, 'titulo': 'Nova Categoria Financeira'}
    return render(request, 'financeiro/categoriafinanceira_form.html', context)

@login_required
def categoriafinanceira_edit(request, pk):
    categoria = get_object_or_404(CategoriaFinanceira, pk=pk)
    if request.method == 'POST':
        form = CategoriaFinanceiraForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoria atualizada com sucesso!')
            return redirect('ERP_ServicesBI:categoriafinanceira_list')
    else:
        form = CategoriaFinanceiraForm(instance=categoria)
    context = {'form': form, 'titulo': 'Editar Categoria Financeira', 'categoria': categoria}
    return render(request, 'financeiro/categoriafinanceira_form.html', context)

@login_required
def categoriafinanceira_delete(request, pk):
    categoria = get_object_or_404(CategoriaFinanceira, pk=pk)
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, 'Categoria excluída com sucesso!')
        return redirect('ERP_ServicesBI:categoriafinanceira_list')
    context = {'objeto': categoria, 'titulo': 'Excluir Categoria Financeira'}
    return render(request, 'financeiro/confirm_delete.html', context)

@login_required
def centrocusto_list(request):
    centros = CentroCusto.objects.all().order_by('nome')
    context = {'centros': centros}
    return render(request, 'financeiro/centrocusto_list.html', context)

@login_required
def centrocusto_add(request):
    if request.method == 'POST':
        form = CentroCustoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Centro de custo criado com sucesso!')
            return redirect('ERP_ServicesBI:centrocusto_list')
    else:
        form = CentroCustoForm()
    context = {'form': form, 'titulo': 'Novo Centro de Custo'}
    return render(request, 'financeiro/centrocusto_form.html', context)

@login_required
def centrocusto_edit(request, pk):
    centro = get_object_or_404(CentroCusto, pk=pk)
    if request.method == 'POST':
        form = CentroCustoForm(request.POST, instance=centro)
        if form.is_valid():
            form.save()
            messages.success(request, 'Centro de custo atualizado com sucesso!')
            return redirect('ERP_ServicesBI:centrocusto_list')
    else:
        form = CentroCustoForm(instance=centro)
    context = {'form': form, 'titulo': 'Editar Centro de Custo', 'centro': centro}
    return render(request, 'financeiro/centrocusto_form.html', context)

@login_required
def centrocusto_delete(request, pk):
    centro = get_object_or_404(CentroCusto, pk=pk)
    if request.method == 'POST':
        centro.delete()
        messages.success(request, 'Centro de custo excluído com sucesso!')
        return redirect('ERP_ServicesBI:centrocusto_list')
    context = {'objeto': centro, 'titulo': 'Excluir Centro de Custo'}
    return render(request, 'financeiro/confirm_delete.html', context)

@login_required
def fluxo_caixa(request):
    context = {}
    return render(request, 'financeiro/fluxo_caixa.html', context)

@login_required
def orcamentofinanceiro_list(request):
    orcamentos = OrcamentoFinanceiro.objects.select_related('categoria').all().order_by('-ano', '-mes')
    context = {'orcamentos': orcamentos}
    return render(request, 'financeiro/orcamentofinanceiro_list.html', context)

@login_required
def orcamentofinanceiro_add(request):
    if request.method == 'POST':
        form = OrcamentoFinanceiroForm(request.POST)
        if form.is_valid():
            orcamento = form.save(commit=False)
            orcamento.criado_por = request.user
            orcamento.save()
            messages.success(request, 'Orçamento criado com sucesso!')
            return redirect('ERP_ServicesBI:orcamentofinanceiro_list')
    else:
        form = OrcamentoFinanceiroForm()
    context = {'form': form, 'titulo': 'Novo Orçamento Financeiro'}
    return render(request, 'financeiro/orcamentofinanceiro_form.html', context)

@login_required
def orcamentofinanceiro_edit(request, pk):
    orcamento = get_object_or_404(OrcamentoFinanceiro, pk=pk)
    if request.method == 'POST':
        form = OrcamentoFinanceiroForm(request.POST, instance=orcamento)
        if form.is_valid():
            form.save()
            messages.success(request, 'Orçamento atualizado com sucesso!')
            return redirect('ERP_ServicesBI:orcamentofinanceiro_list')
    else:
        form = OrcamentoFinanceiroForm(instance=orcamento)
    context = {'form': form, 'titulo': 'Editar Orçamento Financeiro', 'orcamento': orcamento}
    return render(request, 'financeiro/orcamentofinanceiro_form.html', context)

@login_required
def orcamentofinanceiro_delete(request, pk):
    orcamento = get_object_or_404(OrcamentoFinanceiro, pk=pk)
    if request.method == 'POST':
        orcamento.delete()
        messages.success(request, 'Orçamento excluído com sucesso!')
        return redirect('ERP_ServicesBI:orcamentofinanceiro_list')
    context = {'objeto': orcamento, 'titulo': 'Excluir Orçamento Financeiro'}
    return render(request, 'financeiro/confirm_delete.html', context)

@login_required
def conciliacao_list(request):
    extratos = ExtratoBancario.objects.all().order_by('-data_arquivo')
    context = {'extratos': extratos}
    return render(request, 'financeiro/conciliacao_list.html', context)

@login_required
def conciliacao_add(request):
    context = {}
    return render(request, 'financeiro/conciliacao_form.html', context)

@login_required
def conciliacao_edit(request, pk):
    context = {}
    return render(request, 'financeiro/conciliacao_form.html', context)

@login_required
def conciliacao_delete(request, pk):
    context = {}
    return render(request, 'financeiro/confirm_delete.html', context)

@login_required
def dre_gerencial(request):
    context = {}
    return render(request, 'financeiro/dre.html', context)


# =============================================================================
# ESTOQUE
# =============================================================================

@login_required
def movimentacaoestoque_list(request):
    movimentacoes = MovimentacaoEstoque.objects.select_related('produto').all().order_by('-data')
    context = {'movimentacoes': movimentacoes}
    return render(request, 'estoque/movimentacao_list.html', context)

@login_required
def movimentacaoestoque_add(request):
    if request.method == 'POST':
        form = MovimentacaoEstoqueForm(request.POST)
        if form.is_valid():
            movimentacao = form.save(commit=False)
            movimentacao.usuario = request.user
            movimentacao.save()
            messages.success(request, 'Movimentação registrada com sucesso!')
            return redirect('ERP_ServicesBI:movimentacaoestoque_list')
    else:
        form = MovimentacaoEstoqueForm()
    context = {'form': form, 'titulo': 'Nova Movimentação de Estoque'}
    return render(request, 'estoque/movimentacao_form.html', context)

@login_required
def movimentacaoestoque_edit(request, pk):
    movimentacao = get_object_or_404(MovimentacaoEstoque, pk=pk)
    if request.method == 'POST':
        form = MovimentacaoEstoqueForm(request.POST, instance=movimentacao)
        if form.is_valid():
            form.save()
            messages.success(request, 'Movimentação atualizada com sucesso!')
            return redirect('ERP_ServicesBI:movimentacaoestoque_list')
    else:
        form = MovimentacaoEstoqueForm(instance=movimentacao)
    context = {'form': form, 'titulo': 'Editar Movimentação', 'movimentacao': movimentacao}
    return render(request, 'estoque/movimentacao_form.html', context)

@login_required
def movimentacaoestoque_delete(request, pk):
    movimentacao = get_object_or_404(MovimentacaoEstoque, pk=pk)
    if request.method == 'POST':
        movimentacao.delete()
        messages.success(request, 'Movimentação excluída com sucesso!')
        return redirect('ERP_ServicesBI:movimentacaoestoque_list')
    context = {'objeto': movimentacao, 'titulo': 'Excluir Movimentação'}
    return render(request, 'estoque/confirm_delete.html', context)

@login_required
def inventario_list(request):
    inventarios = Inventario.objects.select_related('usuario').all().order_by('-data')
    context = {'inventarios': inventarios}
    return render(request, 'estoque/inventario_list.html', context)

@login_required
def inventario_add(request):
    if request.method == 'POST':
        form = InventarioForm(request.POST)
        if form.is_valid():
            inventario = form.save(commit=False)
            inventario.usuario = request.user
            inventario.save()
            messages.success(request, 'Inventário criado com sucesso!')
            return redirect('ERP_ServicesBI:inventario_list')
    else:
        form = InventarioForm()
    context = {'form': form, 'titulo': 'Novo Inventário'}
    return render(request, 'estoque/inventario_form.html', context)

@login_required
def inventario_edit(request, pk):
    inventario = get_object_or_404(Inventario, pk=pk)
    if request.method == 'POST':
        form = InventarioForm(request.POST, instance=inventario)
        if form.is_valid():
            form.save()
            messages.success(request, 'Inventário atualizado com sucesso!')
            return redirect('ERP_ServicesBI:inventario_list')
    else:
        form = InventarioForm(instance=inventario)
    context = {'form': form, 'titulo': 'Editar Inventário', 'inventario': inventario}
    return render(request, 'estoque/inventario_form.html', context)

@login_required
def inventario_delete(request, pk):
    inventario = get_object_or_404(Inventario, pk=pk)
    if request.method == 'POST':
        inventario.delete()
        messages.success(request, 'Inventário excluído com sucesso!')
        return redirect('ERP_ServicesBI:inventario_list')
    context = {'objeto': inventario, 'titulo': 'Excluir Inventário'}
    return render(request, 'estoque/confirm_delete.html', context)

@login_required
def transferencia_list(request):
    transferencias = TransferenciaEstoque.objects.select_related('usuario').all().order_by('-data')
    context = {'transferencias': transferencias}
    return render(request, 'estoque/transferencia_list.html', context)

@login_required
def transferencia_add(request):
    if request.method == 'POST':
        form = TransferenciaEstoqueForm(request.POST)
        if form.is_valid():
            transferencia = form.save(commit=False)
            transferencia.usuario = request.user
            transferencia.save()
            messages.success(request, 'Transferência criada com sucesso!')
            return redirect('ERP_ServicesBI:transferencia_list')
    else:
        form = TransferenciaEstoqueForm()
    context = {'form': form, 'titulo': 'Nova Transferência de Estoque'}
    return render(request, 'estoque/transferencia_form.html', context)

@login_required
def transferencia_edit(request, pk):
    transferencia = get_object_or_404(TransferenciaEstoque, pk=pk)
    if request.method == 'POST':
        form = TransferenciaEstoqueForm(request.POST, instance=transferencia)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transferência atualizada com sucesso!')
            return redirect('ERP_ServicesBI:transferencia_list')
    else:
        form = TransferenciaEstoqueForm(instance=transferencia)
    context = {'form': form, 'titulo': 'Editar Transferência', 'transferencia': transferencia}
    return render(request, 'estoque/transferencia_form.html', context)

@login_required
def transferencia_delete(request, pk):
    transferencia = get_object_or_404(TransferenciaEstoque, pk=pk)
    if request.method == 'POST':
        transferencia.delete()
        messages.success(request, 'Transferência excluída com sucesso!')
        return redirect('ERP_ServicesBI:transferencia_list')
    context = {'objeto': transferencia, 'titulo': 'Excluir Transferência'}
    return render(request, 'estoque/confirm_delete.html', context)

@login_required
def relatorio_estoque(request):
    context = {}
    return render(request, 'estoque/relatorio_posicao.html', context)

@login_required
def relatorio_movimentacoes(request):
    context = {}
    return render(request, 'estoque/relatorio_movimentacoes.html', context)