# -*- coding: utf-8 -*-
"""
ERP SERVICES BI - VIEWS LIMPAS (sem Cotacao antigo)
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Q, F
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import timedelta
import csv
import io

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
    """Lista de clientes"""
    clientes = Cliente.objects.all().order_by('nome_razao_social')
    context = {'clientes': clientes}
    return render(request, 'cadastro/cliente_list.html', context)


@login_required
def cliente_add(request):
    """Adicionar cliente"""
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
    """Editar cliente"""
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
    """Excluir cliente"""
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        cliente.delete()
        messages.success(request, 'Cliente excluído com sucesso!')
        return redirect('ERP_ServicesBI:cliente_list')
    context = {'objeto': cliente, 'titulo': 'Excluir Cliente'}
    return render(request, 'cadastro/confirm_delete.html', context)


# =============================================================================
# CADASTRO - EMPRESAS
# =============================================================================

@login_required
def empresa_list(request):
    """Lista de empresas"""
    empresas = Empresa.objects.all().order_by('nome_fantasia')
    context = {'empresas': empresas}
    return render(request, 'cadastro/empresa_list.html', context)


@login_required
def empresa_add(request):
    """Adicionar empresa"""
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
    """Editar empresa"""
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
    """Excluir empresa"""
    empresa = get_object_or_404(Empresa, pk=pk)
    if request.method == 'POST':
        empresa.delete()
        messages.success(request, 'Empresa excluída com sucesso!')
        return redirect('ERP_ServicesBI:empresa_list')
    context = {'objeto': empresa, 'titulo': 'Excluir Empresa'}
    return render(request, 'cadastro/confirm_delete.html', context)


# =============================================================================
# CADASTRO - FORNECEDORES
# =============================================================================

@login_required
def fornecedor_list(request):
    """Lista de fornecedores"""
    fornecedores = Fornecedor.objects.all().order_by('nome_razao_social')
    context = {'fornecedores': fornecedores}
    return render(request, 'cadastro/fornecedor_list.html', context)


@login_required
def fornecedor_add(request):
    """Adicionar fornecedor"""
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
    """Editar fornecedor"""
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
    """Excluir fornecedor"""
    fornecedor = get_object_or_404(Fornecedor, pk=pk)
    if request.method == 'POST':
        fornecedor.delete()
        messages.success(request, 'Fornecedor excluído com sucesso!')
        return redirect('ERP_ServicesBI:fornecedor_list')
    context = {'objeto': fornecedor, 'titulo': 'Excluir Fornecedor'}
    return render(request, 'cadastro/confirm_delete.html', context)


# =============================================================================
# CADASTRO - CATEGORIAS
# =============================================================================

@login_required
def categoria_list(request):
    """Lista de categorias"""
    categorias = Categoria.objects.all().order_by('nome')
    context = {'categorias': categorias}
    return render(request, 'cadastro/categoria_list.html', context)


@login_required
def categoria_add(request):
    """Adicionar categoria"""
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
    """Editar categoria"""
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
    """Excluir categoria"""
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, 'Categoria excluída com sucesso!')
        return redirect('ERP_ServicesBI:categoria_list')
    context = {'objeto': categoria, 'titulo': 'Excluir Categoria'}
    return render(request, 'cadastro/confirm_delete.html', context)


@login_required
def categoria_create_ajax(request):
    """Criar categoria via AJAX"""
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        if nome:
            categoria, created = Categoria.objects.get_or_create(nome=nome)
            return JsonResponse({
                'success': True,
                'id': categoria.id,
                'nome': categoria.nome
            })
    return JsonResponse({'success': False})


@login_required
def categoria_delete_ajax(request, pk):
    """Deletar categoria via AJAX"""
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
    """Lista de produtos"""
    produtos = Produto.objects.select_related('categoria', 'fornecedor').all().order_by('descricao')
    context = {'produtos': produtos}
    return render(request, 'cadastro/produto_list.html', context)


@login_required
def produto_add(request):
    """Adicionar produto"""
    if request.method == 'POST':
        form = ProdutoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produto adicionado com sucesso!')
            return redirect('ERP_ServicesBI:produto_list')
    else:
        form = ProdutoForm()
    context = {'form': form, 'titulo': 'Novo Produto'}
    return render(request, 'cadastro/produto_form.html', context)


@login_required
def produto_edit(request, pk):
    """Editar produto"""
    produto = get_object_or_404(Produto, pk=pk)
    if request.method == 'POST':
        form = ProdutoForm(request.POST, instance=produto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produto atualizado com sucesso!')
            return redirect('ERP_ServicesBI:produto_list')
    else:
        form = ProdutoForm(instance=produto)
    context = {'form': form, 'titulo': 'Editar Produto', 'produto': produto}
    return render(request, 'cadastro/produto_form.html', context)


@login_required
def produto_delete(request, pk):
    """Excluir produto"""
    produto = get_object_or_404(Produto, pk=pk)
    if request.method == 'POST':
        produto.delete()
        messages.success(request, 'Produto excluído com sucesso!')
        return redirect('ERP_ServicesBI:produto_list')
    context = {'objeto': produto, 'titulo': 'Excluir Produto'}
    return render(request, 'cadastro/confirm_delete.html', context)


@login_required
def produto_json(request, pk):
    """Retorna dados do produto em JSON"""
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
    """Lista de pedidos de compra"""
    pedidos = PedidoCompra.objects.select_related('fornecedor').all().order_by('-data_pedido')
    context = {'pedidos': pedidos}
    return render(request, 'compras/pedidocompra_list.html', context)


@login_required
def pedidocompra_add(request):
    """Adicionar pedido de compra"""
    if request.method == 'POST':
        form = PedidoCompraForm(request.POST)
        if form.is_valid():
            pedido = form.save()
            messages.success(request, f'Pedido {pedido.numero} criado com sucesso!')
            return redirect('ERP_ServicesBI:pedidocompra_list')
    else:
        form = PedidoCompraForm()
    context = {'form': form, 'titulo': 'Novo Pedido de Compra'}
    return render(request, 'compras/pedidocompra_form.html', context)


@login_required
def pedidocompra_edit(request, pk):
    """Editar pedido de compra"""
    pedido = get_object_or_404(PedidoCompra, pk=pk)
    if request.method == 'POST':
        form = PedidoCompraForm(request.POST, instance=pedido)
        if form.is_valid():
            form.save()
            messages.success(request, 'Pedido atualizado com sucesso!')
            return redirect('ERP_ServicesBI:pedidocompra_list')
    else:
        form = PedidoCompraForm(instance=pedido)
    context = {'form': form, 'titulo': 'Editar Pedido de Compra', 'pedido': pedido}
    return render(request, 'compras/pedidocompra_form.html', context)


@login_required
def pedidocompra_delete(request, pk):
    """Excluir pedido de compra"""
    pedido = get_object_or_404(PedidoCompra, pk=pk)
    if request.method == 'POST':
        numero = pedido.numero
        pedido.delete()
        messages.success(request, f'Pedido {numero} excluído com sucesso!')
        return redirect('ERP_ServicesBI:pedidocompra_list')
    context = {'objeto': pedido, 'titulo': 'Excluir Pedido de Compra'}
    return render(request, 'compras/confirm_delete.html', context)


@login_required
def pedidocompra_item_add(request, pedido_pk):
    """Adicionar item ao pedido"""
    pedido = get_object_or_404(PedidoCompra, pk=pedido_pk)
    if request.method == 'POST':
        form = ItemPedidoCompraForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.pedido = pedido
            item.save()
            pedido.calcular_total()
            messages.success(request, 'Item adicionado com sucesso!')
            return redirect('ERP_ServicesBI:pedidocompra_edit', pk=pedido.pk)
    else:
        form = ItemPedidoCompraForm()
    context = {'form': form, 'pedido': pedido, 'titulo': 'Novo Item'}
    return render(request, 'compras/item_form.html', context)


@login_required
def pedidocompra_item_edit(request, pedido_pk, item_pk):
    """Editar item do pedido"""
    pedido = get_object_or_404(PedidoCompra, pk=pedido_pk)
    item = get_object_or_404(ItemPedidoCompra, pk=item_pk, pedido=pedido)
    if request.method == 'POST':
        form = ItemPedidoCompraForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            pedido.calcular_total()
            messages.success(request, 'Item atualizado com sucesso!')
            return redirect('ERP_ServicesBI:pedidocompra_edit', pk=pedido.pk)
    else:
        form = ItemPedidoCompraForm(instance=item)
    context = {'form': form, 'pedido': pedido, 'titulo': 'Editar Item'}
    return render(request, 'compras/item_form.html', context)


@login_required
@require_POST
def pedidocompra_item_delete(request, pk):
    """Excluir item do pedido"""
    item = get_object_or_404(ItemPedidoCompra, pk=pk)
    pedido = item.pedido
    item.delete()
    pedido.calcular_total()
    messages.success(request, 'Item removido com sucesso!')
    return redirect('ERP_ServicesBI:pedidocompra_edit', pk=pedido.pk)


@login_required
def pedidocompra_gerar_nfe(request, pk):
    """Gerar NF de entrada do pedido"""
    pedido = get_object_or_404(PedidoCompra, pk=pk)
    context = {'pedido': pedido}
    return render(request, 'compras/gerar_nfe.html', context)


# =============================================================================
# COMPRAS - NOTAS FISCAIS
# =============================================================================

@login_required
def notafiscalentrada_list(request):
    """Lista de notas fiscais de entrada"""
    notas = NotaFiscalEntrada.objects.select_related('fornecedor').all().order_by('-data_entrada')
    context = {'notas': notas}
    return render(request, 'compras/notafiscal_list.html', context)


@login_required
def notafiscalentrada_add(request):
    """Adicionar nota fiscal de entrada"""
    if request.method == 'POST':
        form = NotaFiscalEntradaForm(request.POST)
        if form.is_valid():
            nota = form.save()
            messages.success(request, f'NF {nota.numero_nf} criada com sucesso!')
            return redirect('ERP_ServicesBI:notafiscalentrada_list')
    else:
        form = NotaFiscalEntradaForm()
    context = {'form': form, 'titulo': 'Nova Nota Fiscal de Entrada'}
    return render(request, 'compras/notafiscal_form.html', context)


@login_required
def notafiscalentrada_edit(request, pk):
    """Editar nota fiscal de entrada"""
    nota = get_object_or_404(NotaFiscalEntrada, pk=pk)
    if request.method == 'POST':
        form = NotaFiscalEntradaForm(request.POST, instance=nota)
        if form.is_valid():
            form.save()
            messages.success(request, 'Nota fiscal atualizada com sucesso!')
            return redirect('ERP_ServicesBI:notafiscalentrada_list')
    else:
        form = NotaFiscalEntradaForm(instance=nota)
    context = {'form': form, 'titulo': 'Editar Nota Fiscal de Entrada', 'nota': nota}
    return render(request, 'compras/notafiscal_form.html', context)


@login_required
def notafiscalentrada_delete(request, pk):
    """Excluir nota fiscal de entrada"""
    nota = get_object_or_404(NotaFiscalEntrada, pk=pk)
    if request.method == 'POST':
        numero = nota.numero_nf
        nota.delete()
        messages.success(request, f'NF {numero} excluída com sucesso!')
        return redirect('ERP_ServicesBI:notafiscalentrada_list')
    context = {'objeto': nota, 'titulo': 'Excluir Nota Fiscal de Entrada'}
    return render(request, 'compras/confirm_delete.html', context)


@login_required
def notafiscalentrada_item_add(request, nota_pk):
    """Adicionar item à nota fiscal"""
    nota = get_object_or_404(NotaFiscalEntrada, pk=nota_pk)
    if request.method == 'POST':
        form = ItemNotaFiscalEntradaForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.nota_fiscal = nota
            item.save()
            nota.calcular_total()
            messages.success(request, 'Item adicionado com sucesso!')
            return redirect('ERP_ServicesBI:notafiscalentrada_edit', pk=nota.pk)
    else:
        form = ItemNotaFiscalEntradaForm()
    context = {'form': form, 'nota': nota, 'titulo': 'Novo Item'}
    return render(request, 'compras/item_form.html', context)


@login_required
@require_POST
def notafiscalentrada_item_delete(request, pk):
    """Excluir item da nota fiscal"""
    item = get_object_or_404(ItemNotaFiscalEntrada, pk=pk)
    nota = item.nota_fiscal
    item.delete()
    nota.calcular_total()
    messages.success(request, 'Item removido com sucesso!')
    return redirect('ERP_ServicesBI:notafiscalentrada_edit', pk=nota.pk)


@login_required
def relatorio_compras(request):
    """Relatório de compras"""
    context = {}
    return render(request, 'compras/relatorio.html', context)


# =============================================================================
# VENDAS - ORÇAMENTOS
# =============================================================================

@login_required
def orcamento_list(request):
    """Lista de orçamentos"""
    orcamentos = Orcamento.objects.select_related('cliente', 'vendedor').all().order_by('-data_orcamento')
    context = {'orcamentos': orcamentos}
    return render(request, 'vendas/orcamento_list.html', context)


@login_required
def orcamento_add(request):
    """Adicionar orçamento"""
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
    """Editar orçamento"""
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
    """Excluir orçamento"""
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
    """Adicionar item ao orçamento"""
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
    """Excluir item do orçamento"""
    item = get_object_or_404(ItemOrcamento, pk=pk)
    orcamento = item.orcamento
    item.delete()
    orcamento.calcular_total()
    messages.success(request, 'Item removido com sucesso!')
    return redirect('ERP_ServicesBI:orcamento_edit', pk=orcamento.pk)


@login_required
def orcamento_gerar_pedido(request, pk):
    """Converter orçamento em pedido de venda"""
    orcamento = get_object_or_404(Orcamento, pk=pk)
    context = {'orcamento': orcamento}
    return render(request, 'vendas/gerar_pedido.html', context)


# =============================================================================
# VENDAS - PEDIDOS
# =============================================================================

@login_required
def pedidovenda_list(request):
    """Lista de pedidos de venda"""
    pedidos = PedidoVenda.objects.select_related('cliente', 'vendedor').all().order_by('-data_pedido')
    context = {'pedidos': pedidos}
    return render(request, 'vendas/pedidovenda_list.html', context)


@login_required
def pedidovenda_add(request):
    """Adicionar pedido de venda"""
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
    """Editar pedido de venda"""
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
    """Excluir pedido de venda"""
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
    """Adicionar item ao pedido de venda"""
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
    """Excluir item do pedido de venda"""
    item = get_object_or_404(ItemPedidoVenda, pk=pk)
    pedido = item.pedido
    item.delete()
    pedido.calcular_total()
    messages.success(request, 'Item removido com sucesso!')
    return redirect('ERP_ServicesBI:pedidovenda_edit', pk=pedido.pk)


@login_required
def pedidovenda_gerar_nfe(request, pk):
    """Gerar NF de saída do pedido"""
    pedido = get_object_or_404(PedidoVenda, pk=pk)
    context = {'pedido': pedido}
    return render(request, 'vendas/gerar_nfe.html', context)


# =============================================================================
# VENDAS - NOTAS FISCAIS
# =============================================================================

@login_required
def notafiscalsaida_list(request):
    """Lista de notas fiscais de saída"""
    notas = NotaFiscalSaida.objects.select_related('cliente').all().order_by('-data_emissao')
    context = {'notas': notas}
    return render(request, 'vendas/notafiscal_list.html', context)


@login_required
def notafiscalsaida_add(request):
    """Adicionar nota fiscal de saída"""
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
    """Editar nota fiscal de saída"""
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
    """Excluir nota fiscal de saída"""
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
    """Adicionar item à nota fiscal de saída"""
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
    """Excluir item da nota fiscal de saída"""
    item = get_object_or_404(ItemNotaFiscalSaida, pk=pk)
    nota = item.nota_fiscal
    item.delete()
    nota.calcular_total()
    messages.success(request, 'Item removido com sucesso!')
    return redirect('ERP_ServicesBI:notafiscalsaida_edit', pk=nota.pk)


@login_required
def relatorio_vendas(request):
    """Relatório de vendas"""
    context = {}
    return render(request, 'vendas/relatorio.html', context)


# =============================================================================
# FINANCEIRO - CONTAS
# =============================================================================

@login_required
def contareceber_list(request):
    """Lista de contas a receber"""
    contas = ContaReceber.objects.select_related('cliente').all().order_by('data_vencimento')
    context = {'contas': contas}
    return render(request, 'financeiro/contareceber_list.html', context)


@login_required
def contareceber_add(request):
    """Adicionar conta a receber"""
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
    """Editar conta a receber"""
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
    """Excluir conta a receber"""
    conta = get_object_or_404(ContaReceber, pk=pk)
    if request.method == 'POST':
        conta.delete()
        messages.success(request, 'Conta excluída com sucesso!')
        return redirect('ERP_ServicesBI:contareceber_list')
    context = {'objeto': conta, 'titulo': 'Excluir Conta a Receber'}
    return render(request, 'financeiro/confirm_delete.html', context)


@login_required
def contareceber_baixar(request, pk):
    """Baixar conta a receber"""
    conta = get_object_or_404(ContaReceber, pk=pk)
    context = {'conta': conta}
    return render(request, 'financeiro/contareceber_baixar.html', context)


@login_required
def contapagar_list(request):
    """Lista de contas a pagar"""
    contas = ContaPagar.objects.select_related('fornecedor').all().order_by('data_vencimento')
    context = {'contas': contas}
    return render(request, 'financeiro/contapagar_list.html', context)


@login_required
def contapagar_add(request):
    """Adicionar conta a pagar"""
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
    """Editar conta a pagar"""
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
    """Excluir conta a pagar"""
    conta = get_object_or_404(ContaPagar, pk=pk)
    if request.method == 'POST':
        conta.delete()
        messages.success(request, 'Conta excluída com sucesso!')
        return redirect('ERP_ServicesBI:contapagar_list')
    context = {'objeto': conta, 'titulo': 'Excluir Conta a Pagar'}
    return render(request, 'financeiro/confirm_delete.html', context)


@login_required
def contapagar_baixar(request, pk):
    """Baixar conta a pagar"""
    conta = get_object_or_404(ContaPagar, pk=pk)
    context = {'conta': conta}
    return render(request, 'financeiro/contapagar_baixar.html', context)


@login_required
def movimentocaixa_add(request):
    """Adicionar movimento de caixa"""
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


# =============================================================================
# FINANCEIRO - CATEGORIAS E CENTROS
# =============================================================================

@login_required
def categoriafinanceira_list(request):
    """Lista de categorias financeiras"""
    categorias = CategoriaFinanceira.objects.all().order_by('codigo')
    context = {'categorias': categorias}
    return render(request, 'financeiro/categoriafinanceira_list.html', context)


@login_required
def categoriafinanceira_add(request):
    """Adicionar categoria financeira"""
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
    """Editar categoria financeira"""
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
    """Excluir categoria financeira"""
    categoria = get_object_or_404(CategoriaFinanceira, pk=pk)
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, 'Categoria excluída com sucesso!')
        return redirect('ERP_ServicesBI:categoriafinanceira_list')
    context = {'objeto': categoria, 'titulo': 'Excluir Categoria Financeira'}
    return render(request, 'financeiro/confirm_delete.html', context)


@login_required
def centrocusto_list(request):
    """Lista de centros de custo"""
    centros = CentroCusto.objects.all().order_by('nome')
    context = {'centros': centros}
    return render(request, 'financeiro/centrocusto_list.html', context)


@login_required
def centrocusto_add(request):
    """Adicionar centro de custo"""
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
    """Editar centro de custo"""
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
    """Excluir centro de custo"""
    centro = get_object_or_404(CentroCusto, pk=pk)
    if request.method == 'POST':
        centro.delete()
        messages.success(request, 'Centro de custo excluído com sucesso!')
        return redirect('ERP_ServicesBI:centrocusto_list')
    context = {'objeto': centro, 'titulo': 'Excluir Centro de Custo'}
    return render(request, 'financeiro/confirm_delete.html', context)


@login_required
def fluxo_caixa(request):
    """Fluxo de caixa"""
    context = {}
    return render(request, 'financeiro/fluxo_caixa.html', context)


@login_required
def orcamentofinanceiro_list(request):
    """Lista de orçamentos financeiros"""
    orcamentos = OrcamentoFinanceiro.objects.select_related('categoria').all().order_by('-ano', '-mes')
    context = {'orcamentos': orcamentos}
    return render(request, 'financeiro/orcamentofinanceiro_list.html', context)


@login_required
def orcamentofinanceiro_add(request):
    """Adicionar orçamento financeiro"""
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
    """Editar orçamento financeiro"""
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
    """Excluir orçamento financeiro"""
    orcamento = get_object_or_404(OrcamentoFinanceiro, pk=pk)
    if request.method == 'POST':
        orcamento.delete()
        messages.success(request, 'Orçamento excluído com sucesso!')
        return redirect('ERP_ServicesBI:orcamentofinanceiro_list')
    context = {'objeto': orcamento, 'titulo': 'Excluir Orçamento Financeiro'}
    return render(request, 'financeiro/confirm_delete.html', context)


@login_required
def conciliacao_list(request):
    """Lista de conciliações bancárias"""
    extratos = ExtratoBancario.objects.all().order_by('-data_arquivo')
    context = {'extratos': extratos}
    return render(request, 'financeiro/conciliacao_list.html', context)


@login_required
def conciliacao_add(request):
    """Adicionar conciliação"""
    context = {}
    return render(request, 'financeiro/conciliacao_form.html', context)


@login_required
def conciliacao_edit(request, pk):
    """Editar conciliação"""
    context = {}
    return render(request, 'financeiro/conciliacao_form.html', context)


@login_required
def conciliacao_delete(request, pk):
    """Excluir conciliação"""
    context = {}
    return render(request, 'financeiro/confirm_delete.html', context)


@login_required
def dre_gerencial(request):
    """DRE Gerencial"""
    context = {}
    return render(request, 'financeiro/dre.html', context)


# =============================================================================
# ESTOQUE
# =============================================================================

@login_required
def movimentacaoestoque_list(request):
    """Lista de movimentações de estoque"""
    movimentacoes = MovimentacaoEstoque.objects.select_related('produto').all().order_by('-data')
    context = {'movimentacoes': movimentacoes}
    return render(request, 'estoque/movimentacao_list.html', context)


@login_required
def movimentacaoestoque_add(request):
    """Adicionar movimentação de estoque"""
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
    """Editar movimentação de estoque"""
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
    """Excluir movimentação de estoque"""
    movimentacao = get_object_or_404(MovimentacaoEstoque, pk=pk)
    if request.method == 'POST':
        movimentacao.delete()
        messages.success(request, 'Movimentação excluída com sucesso!')
        return redirect('ERP_ServicesBI:movimentacaoestoque_list')
    context = {'objeto': movimentacao, 'titulo': 'Excluir Movimentação'}
    return render(request, 'estoque/confirm_delete.html', context)


@login_required
def inventario_list(request):
    """Lista de inventários"""
    inventarios = Inventario.objects.select_related('usuario').all().order_by('-data')
    context = {'inventarios': inventarios}
    return render(request, 'estoque/inventario_list.html', context)


@login_required
def inventario_add(request):
    """Adicionar inventário"""
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
    """Editar inventário"""
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
    """Excluir inventário"""
    inventario = get_object_or_404(Inventario, pk=pk)
    if request.method == 'POST':
        inventario.delete()
        messages.success(request, 'Inventário excluído com sucesso!')
        return redirect('ERP_ServicesBI:inventario_list')
    context = {'objeto': inventario, 'titulo': 'Excluir Inventário'}
    return render(request, 'estoque/confirm_delete.html', context)


@login_required
def transferencia_list(request):
    """Lista de transferências de estoque"""
    transferencias = TransferenciaEstoque.objects.select_related('usuario').all().order_by('-data')
    context = {'transferencias': transferencias}
    return render(request, 'estoque/transferencia_list.html', context)


@login_required
def transferencia_add(request):
    """Adicionar transferência de estoque"""
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
    """Editar transferência de estoque"""
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
    """Excluir transferência de estoque"""
    transferencia = get_object_or_404(TransferenciaEstoque, pk=pk)
    if request.method == 'POST':
        transferencia.delete()
        messages.success(request, 'Transferência excluída com sucesso!')
        return redirect('ERP_ServicesBI:transferencia_list')
    context = {'objeto': transferencia, 'titulo': 'Excluir Transferência'}
    return render(request, 'estoque/confirm_delete.html', context)


@login_required
def relatorio_estoque(request):
    """Relatório de posição de estoque"""
    context = {}
    return render(request, 'estoque/relatorio_posicao.html', context)


@login_required
def relatorio_movimentacoes(request):
    """Relatório de movimentações de estoque"""
    context = {}
    return render(request, 'estoque/relatorio_movimentacoes.html', context)


# =============================================================================
# COTAÇÃO COMPARATIVA (NOVO)
# =============================================================================

@login_required
def cotacao_mae_list(request):
    """Lista de cotações mãe"""
    cotacoes = CotacaoMae.objects.select_related('solicitante').all().order_by('-data_solicitacao')
    context = {'cotacoes': cotacoes}
    return render(request, 'compras/cotacao_mae_list.html', context)


@login_required
def cotacao_mae_create(request):
    """Criar nova cotação mãe"""
    if request.method == 'POST':
        form = CotacaoMaeForm(request.POST)
        formset = ItemSolicitadoFormSet(request.POST, instance=None)
        
        if form.is_valid() and formset.is_valid():
            cotacao = form.save(commit=False)
            cotacao.solicitante = request.user
            cotacao.save()
            
            formset.instance = cotacao
            formset.save()
            
            messages.success(request, f'Cotação {cotacao.numero} criada com sucesso!')
            return redirect('ERP_ServicesBI:cotacao_mae_detail', pk=cotacao.pk)
    else:
        form = CotacaoMaeForm()
        formset = ItemSolicitadoFormSet(instance=None)
    
    context = {'form': form, 'formset': formset, 'titulo': 'Nova Cotação Mãe'}
    return render(request, 'compras/cotacao_mae_form.html', context)


@login_required
def cotacao_mae_detail(request, pk):
    """Detalhe da cotação mãe com comparativo"""
    cotacao = get_object_or_404(CotacaoMae, pk=pk)
    itens_solicitados = ItemSolicitado.objects.filter(cotacao_mae=cotacao).select_related('produto')
    cotacoes_fornecedor = CotacaoFornecedor.objects.filter(cotacao_mae=cotacao).select_related('fornecedor').prefetch_related('itens')
    
    # Montar tabela comparativa
    comparativo = []
    for item_solicitado in itens_solicitados:
        linha = {
            'item': item_solicitado,
            'fornecedores': []
        }
        
        for cot_fornecedor in cotacoes_fornecedor:
            item_cot = cot_fornecedor.itens.filter(item_solicitado=item_solicitado).first()
            linha['fornecedores'].append({
                'fornecedor': cot_fornecedor,
                'item': item_cot
            })
        
        comparativo.append(linha)
    
    context = {
        'cotacao': cotacao,
        'comparativo': comparativo,
        'cotacoes_fornecedor': cotacoes_fornecedor
    }
    return render(request, 'compras/cotacao_mae_detail.html', context)


@login_required
def cotacao_mae_edit(request, pk):
    """Editar cotação mãe"""
    cotacao = get_object_or_404(CotacaoMae, pk=pk)
    
    if request.method == 'POST':
        form = CotacaoMaeForm(request.POST, instance=cotacao)
        formset = ItemSolicitadoFormSet(request.POST, instance=cotacao)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Cotação atualizada com sucesso!')
            return redirect('ERP_ServicesBI:cotacao_mae_detail', pk=cotacao.pk)
    else:
        form = CotacaoMaeForm(instance=cotacao)
        formset = ItemSolicitadoFormSet(instance=cotacao)
    
    context = {'form': form, 'formset': formset, 'cotacao': cotacao, 'titulo': 'Editar Cotação Mãe'}
    return render(request, 'compras/cotacao_mae_form.html', context)


@login_required
def cotacao_mae_delete(request, pk):
    """Excluir cotação mãe"""
    cotacao = get_object_or_404(CotacaoMae, pk=pk)
    
    if request.method == 'POST':
        numero = cotacao.numero
        cotacao.delete()
        messages.success(request, f'Cotação {numero} excluída com sucesso!')
        return redirect('ERP_ServicesBI:cotacao_mae_list')
    
    context = {'objeto': cotacao, 'titulo': 'Excluir Cotação Mãe'}
    return render(request, 'compras/confirm_delete.html', context)


@login_required
def cotacao_fornecedor_importar(request, cotacao_mae_pk):
    """Importar cotação de fornecedor via arquivo"""
    cotacao_mae = get_object_or_404(CotacaoMae, pk=cotacao_mae_pk)
    
    if request.method == 'POST':
        arquivo = request.FILES.get('arquivo')
        fornecedor_id = request.POST.get('fornecedor_id')
        
        if arquivo and fornecedor_id:
            fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_id)
            
            # Processar arquivo CSV/XLSX
            try:
                cotacao_fornecedor = processar_arquivo_cotacao(
                    cotacao_mae, fornecedor, arquivo
                )
                messages.success(request, f'Cotação de {fornecedor.nome_fantasia} importada com sucesso!')
                return redirect('ERP_ServicesBI:cotacao_mae_detail', pk=cotacao_mae.pk)
            except Exception as e:
                messages.error(request, f'Erro ao processar arquivo: {str(e)}')
    
    fornecedores = Fornecedor.objects.filter(ativo=True).order_by('nome_fantasia')
    context = {
        'cotacao_mae': cotacao_mae,
        'fornecedores': fornecedores,
        'titulo': 'Importar Cotação de Fornecedor'
    }
    return render(request, 'compras/cotacao_fornecedor_importar.html', context)


def processar_arquivo_cotacao(cotacao_mae, fornecedor, arquivo):
    """
    Processa arquivo CSV/XLSX de cotação
    Cria/atualiza CotacaoFornecedor e ItemCotacaoFornecedor
    """
    # Verificar se já existe cotação deste fornecedor
    cotacao_fornecedor, created = CotacaoFornecedor.objects.get_or_create(
        cotacao_mae=cotacao_mae,
        fornecedor=fornecedor,
        defaults={
            'status': 'importada',
            'data_recebimento': timezone.now().date(),
            'arquivo_origem': arquivo
        }
    )
    
    # Limpar itens anteriores se estamos atualizando
    if not created:
        cotacao_fornecedor.itens.all().delete()
    
    # Ler e processar arquivo
    conteudo = arquivo.read().decode('utf-8')
    leitor = csv.DictReader(io.StringIO(conteudo))
    
    valor_total = 0
    for row in leitor:
        descricao = row.get('descricao', '').strip()
        quantidade = float(row.get('quantidade', 0))
        preco_unitario = float(row.get('preco_unitario', 0))
        
        if descricao and quantidade and preco_unitario:
            # Tentar fazer match automático com ItemSolicitado
            item_solicitado = None
            match_score = 0
            
            for item in cotacao_mae.itens_solicitados.all():
                descricao_item = item.descricao_display.lower()
                if descricao.lower() in descricao_item or descricao_item in descricao.lower():
                    item_solicitado = item
                    match_score = 95
                    break
            
            ItemCotacaoFornecedor.objects.create(
                cotacao_fornecedor=cotacao_fornecedor,
                item_solicitado=item_solicitado,
                descricao_fornecedor=descricao,
                quantidade=quantidade,
                preco_unitario=preco_unitario,
                preco_total=quantidade * preco_unitario,
                match_automatico=(item_solicitado is not None),
                match_score=match_score
            )
            valor_total += (quantidade * preco_unitario)
    
    # Atualizar valor total da cotação
    cotacao_fornecedor.valor_total_bruto = valor_total
    cotacao_fornecedor.save()
    
    return cotacao_fornecedor