# -*- coding: utf-8 -*-
"""
ERP SERVICES BI - VIEWS COMPLETAS (PADRONIZADAS COM UNDERLINE)
Corrigido em 30/03/2026:
- Módulo de cotações extraído da string (era código morto)
- Imports unificados e organizados
- Removidos prints de debug
- Removidas duplicatas de APIs (condicao/forma pagamento)
- traceback.print_exc() substituído por logging seguro
"""

# =============================================================================
# IMPORTS - ORGANIZADOS POR CATEGORIA
# =============================================================================

# Django core
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import (
    Sum, Q, F, Min, Avg, Count, DecimalField, Prefetch
)
from django.db import transaction
from django.utils import timezone

# Python stdlib
import csv
import io
import json
import logging
import unicodedata
from datetime import date, timedelta, datetime
from decimal import Decimal, InvalidOperation

# Models
from .models import (
    Cliente, Empresa, Fornecedor, Produto, CategoriaProduto, Vendedor,
    PedidoCompra, ItemPedidoCompra, NotaFiscalEntrada, ItemNotaFiscalEntrada,
    Orcamento, ItemOrcamento, PedidoVenda, ItemPedidoVenda,
    NotaFiscalSaida, ItemNotaFiscalSaida,
    ContaPagar, ContaReceber, MovimentoCaixa,
    CategoriaFinanceira, CentroCusto, OrcamentoFinanceiro,
    CondicaoPagamento, FormaPagamento,
    ExtratoBancario, LancamentoExtrato,
    MovimentacaoEstoque, Inventario, ItemInventario,
    TransferenciaEstoque, ItemTransferencia,
    CotacaoMae, ItemSolicitado, CotacaoFornecedor, ItemCotacaoFornecedor,
)

# Forms
from .forms import (
    ClienteForm, EmpresaForm, FornecedorForm, CategoriaProdutoForm,
    ProdutoForm, VendedorForm,
    CondicaoPagamentoForm, FormaPagamentoForm,
    PedidoCompraForm, ItemPedidoCompraForm,
    NotaFiscalEntradaForm, ItemNotaFiscalEntradaForm,
    OrcamentoForm, ItemOrcamentoForm,
    PedidoVendaForm, ItemPedidoVendaForm,
    NotaFiscalSaidaForm, ItemNotaFiscalSaidaForm,
    ContaPagarForm, ContaReceberForm, MovimentoCaixaForm,
    CategoriaFinanceiraForm, CentroCustoForm, OrcamentoFinanceiroForm,
    ExtratoBancarioForm, LancamentoExtratoForm,
    MovimentacaoEstoqueForm, InventarioForm, ItemInventarioForm,
    TransferenciaEstoqueForm, ItemTransferenciaForm,
    CotacaoMaeForm, ItemSolicitadoForm, ItemSolicitadoFormSet,
    CotacaoFornecedorForm, ItemCotacaoFornecedorForm,
    ItemCotacaoFornecedorFormSet,
)

# Logger seguro para o módulo
logger = logging.getLogger('erp.cotacoes')


# =============================================================================
# UTILITÁRIOS DE LOGGING SEGURO
# =============================================================================

def log_erro_seguro(funcao_nome, exception, request=None, extra_data=None):
    """Loga erros de forma segura, sem expor informações sensíveis."""
    user_id = request.user.id if request and hasattr(request, 'user') and request.user.is_authenticated else 'anonymous'
    ip = request.META.get('REMOTE_ADDR', 'unknown') if request else 'unknown'
    mensagem = f"Erro em {funcao_nome}: {type(exception).__name__}: {str(exception)} | User: {user_id} | IP: {ip}"
    if extra_data:
        mensagem += f" | Extra: {extra_data}"
    logger.error(mensagem, exc_info=True)


def resposta_erro_segura(mensagem_usuario, status=400):
    """Retorna resposta de erro padronizada, sem expor detalhes internos."""
    return JsonResponse({'success': False, 'message': mensagem_usuario}, status=status)


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
        'valor_pedidos_abertos': PedidoCompra.objects.filter(
            status__in=['pendente', 'aprovado']
        ).aggregate(total=Sum('valor_total'))['total'] or 0,
        'valor_vendas_aberto': PedidoVenda.objects.filter(
            status__in=['pendente', 'aprovado']
        ).aggregate(total=Sum('valor_total'))['total'] or 0,
    }
    return render(request, 'dashboard_novo.html', context)


# =============================================================================
# MÓDULO: CADASTRO - CLIENTES
# =============================================================================

@login_required
def cliente_manager(request):
    """View unificada para LISTAR clientes com estatísticas comparativas"""
    hoje = timezone.now()
    inicio_mes_atual = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    inicio_mes_anterior = (inicio_mes_atual - timedelta(days=1)).replace(day=1)

    clientes_list = Cliente.objects.all().order_by('nome_razao_social')

    search = request.GET.get('search', '')
    if search:
        clientes_list = clientes_list.filter(
            Q(nome_razao_social__icontains=search) |
            Q(nome_fantasia__icontains=search) |
            Q(cpf_cnpj__icontains=search)
        )

    total = clientes_list.count()
    total_ativos = clientes_list.filter(ativo=True).count()
    total_inativos = total - total_ativos
    percentual_ativos = (total_ativos / total * 100) if total > 0 else 0
    percentual_inativos = (total_inativos / total * 100) if total > 0 else 0

    # Crescimento vs mês anterior
    clientes_mes_atual = Cliente.objects.filter(criado_em__gte=inicio_mes_atual).count()
    clientes_mes_anterior = Cliente.objects.filter(
        criado_em__gte=inicio_mes_anterior,
        criado_em__lt=inicio_mes_atual
    ).count()
    if clientes_mes_anterior > 0:
        taxa_crescimento = ((clientes_mes_atual - clientes_mes_anterior) / clientes_mes_anterior) * 100
    else:
        taxa_crescimento = 100 if clientes_mes_atual > 0 else 0

    # Ativos - variação
    ativos_mes_atual = Cliente.objects.filter(ativo=True, criado_em__gte=inicio_mes_atual).count()
    ativos_mes_anterior = Cliente.objects.filter(
        ativo=True,
        criado_em__gte=inicio_mes_anterior,
        criado_em__lt=inicio_mes_atual
    ).count()
    if ativos_mes_anterior > 0:
        taxa_ativos = ((ativos_mes_atual - ativos_mes_anterior) / ativos_mes_anterior) * 100
    else:
        taxa_ativos = 100 if ativos_mes_atual > 0 else 0

    # Inativos - variação
    inativos_mes_atual = Cliente.objects.filter(ativo=False, criado_em__gte=inicio_mes_atual).count()
    inativos_mes_anterior = Cliente.objects.filter(
        ativo=False,
        criado_em__gte=inicio_mes_anterior,
        criado_em__lt=inicio_mes_atual
    ).count()
    if inativos_mes_anterior > 0:
        taxa_inativos = ((inativos_mes_atual - inativos_mes_anterior) / inativos_mes_anterior) * 100
    else:
        taxa_inativos = 100 if inativos_mes_atual > 0 else 0

    # Limite de crédito
    limite_total = clientes_list.aggregate(total=Sum('limite_credito'))['total'] or 0
    limite_mes_anterior = Cliente.objects.filter(
        criado_em__lt=inicio_mes_atual
    ).aggregate(total=Sum('limite_credito'))['total'] or 0
    if limite_mes_anterior > 0:
        variacao_limite = ((limite_total - limite_mes_anterior) / limite_mes_anterior) * 100
    else:
        variacao_limite = 100 if limite_total > 0 else 0

    limite_utilizado = 0
    percentual_uso_limite = 0

    # Paginação
    per_page = request.GET.get('per_page', 25)
    try:
        per_page = int(per_page)
        if per_page not in [10, 25, 50, 100]:
            per_page = 25
    except ValueError:
        per_page = 25

    paginator = Paginator(clientes_list, per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'clientes': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'per_page': per_page,
        'search': search,
        'total': total,
        'total_ativos': total_ativos,
        'total_inativos': total_inativos,
        'percentual_ativos': round(percentual_ativos, 1),
        'percentual_inativos': round(percentual_inativos, 1),
        'taxa_crescimento': round(taxa_crescimento, 1),
        'taxa_ativos': round(taxa_ativos, 1),
        'taxa_inativos': round(taxa_inativos, 1),
        'limite_total': limite_total,
        'limite_utilizado': limite_utilizado,
        'percentual_uso_limite': round(percentual_uso_limite, 1),
        'variacao_limite': round(variacao_limite, 1),
    }
    return render(request, 'cadastro/cliente_manager.html', context)


@login_required
def cliente_form(request, pk=None):
    """View separada para formulário de cliente (ADD/EDIT)"""
    cliente = get_object_or_404(Cliente, pk=pk) if pk else None

    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            cliente_salvo = form.save()
            messages.success(request, f'Cliente "{cliente_salvo.nome_razao_social}" salvo com sucesso!')
            return redirect('ERP_ServicesBI:cliente_manager')
        else:
            messages.error(request, 'Corrija os erros no formulário.')
    else:
        form = ClienteForm(instance=cliente)

    return render(request, 'cadastro/cliente_form.html', {
        'form': form,
        'cliente': cliente,
    })


@login_required
@require_http_methods(["POST"])
def cliente_excluir(request, pk):
    """Exclusão AJAX de cliente"""
    cliente = get_object_or_404(Cliente, pk=pk)
    nome = cliente.nome_razao_social
    try:
        cliente.delete()
        return JsonResponse({'success': True, 'message': f'Cliente "{nome}" excluído com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao excluir cliente: {str(e)}'}, status=500)


# =============================================================================
# MÓDULO: CADASTRO - FORNECEDORES
# =============================================================================

@login_required
def fornecedor_manager(request):
    """Listagem de fornecedores com cards de resumo"""
    search = request.GET.get('search', '')
    per_page = request.GET.get('per_page', 25)
    try:
        per_page = int(per_page)
    except (ValueError, TypeError):
        per_page = 25

    fornecedores = Fornecedor.objects.all()
    if search:
        fornecedores = fornecedores.filter(
            Q(nome_razao_social__icontains=search) |
            Q(nome_fantasia__icontains=search) |
            Q(cpf_cnpj__icontains=search)
        )

    total = fornecedores.count()
    total_ativos = fornecedores.filter(ativo=True).count()
    total_inativos = total - total_ativos
    percentual_ativos = round((total_ativos / total * 100), 1) if total > 0 else 0
    percentual_inativos = round((total_inativos / total * 100), 1) if total > 0 else 0

    paginator = Paginator(fornecedores.order_by('nome_razao_social'), per_page)
    page = request.GET.get('page', 1)
    try:
        fornecedores_page = paginator.page(page)
    except PageNotAnInteger:
        fornecedores_page = paginator.page(1)
    except EmptyPage:
        fornecedores_page = paginator.page(paginator.num_pages)

    context = {
        'fornecedores': fornecedores_page,
        'total': total,
        'total_ativos': total_ativos,
        'total_inativos': total_inativos,
        'percentual_ativos': percentual_ativos,
        'percentual_inativos': percentual_inativos,
        'search': search,
        'per_page': per_page,
    }
    return render(request, 'cadastro/fornecedor_manager.html', context)


@login_required
def fornecedor_form(request, pk=None):
    """Cadastro/edição de fornecedor"""
    fornecedor = get_object_or_404(Fornecedor, pk=pk) if pk else None

    if request.method == 'POST':
        form = FornecedorForm(request.POST, instance=fornecedor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fornecedor salvo com sucesso!')
            return redirect('ERP_ServicesBI:fornecedor_manager')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = FornecedorForm(instance=fornecedor)

    return render(request, 'cadastro/fornecedor_form.html', {
        'form': form,
        'fornecedor': fornecedor,
    })


@login_required
@require_http_methods(["POST"])
def fornecedor_excluir(request, pk):
    """Exclusão AJAX de fornecedor"""
    fornecedor = get_object_or_404(Fornecedor, pk=pk)
    try:
        nome = fornecedor.nome_razao_social
        fornecedor.delete()
        return JsonResponse({'success': True, 'message': f'Fornecedor "{nome}" excluído com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao excluir: {str(e)}'}, status=400)


# =============================================================================
# MÓDULO: CADASTRO - VENDEDORES
# =============================================================================

@login_required
def vendedor_manager(request):
    """View unificada para LISTAR vendedores com estatísticas comparativas"""
    hoje = timezone.now()
    inicio_mes_atual = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    inicio_mes_anterior = (inicio_mes_atual - timedelta(days=1)).replace(day=1)

    vendedores_list = Vendedor.objects.all().order_by('nome')

    search = request.GET.get('search', '')
    if search:
        vendedores_list = vendedores_list.filter(
            Q(nome__icontains=search) |
            Q(email__icontains=search) |
            Q(apelido__icontains=search)
        )

    total = vendedores_list.count()
    total_ativos = vendedores_list.filter(ativo=True).count()
    total_inativos = total - total_ativos
    percentual_ativos = (total_ativos / total * 100) if total > 0 else 0
    percentual_inativos = (total_inativos / total * 100) if total > 0 else 0

    vendedores_mes_atual = Vendedor.objects.filter(criado_em__gte=inicio_mes_atual).count()
    vendedores_mes_anterior = Vendedor.objects.filter(
        criado_em__gte=inicio_mes_anterior,
        criado_em__lt=inicio_mes_atual
    ).count()
    if vendedores_mes_anterior > 0:
        taxa_crescimento = ((vendedores_mes_atual - vendedores_mes_anterior) / vendedores_mes_anterior) * 100
    else:
        taxa_crescimento = 100 if vendedores_mes_atual > 0 else 0

    ativos_mes_atual = Vendedor.objects.filter(ativo=True, criado_em__gte=inicio_mes_atual).count()
    ativos_mes_anterior = Vendedor.objects.filter(
        ativo=True,
        criado_em__gte=inicio_mes_anterior,
        criado_em__lt=inicio_mes_atual
    ).count()
    if ativos_mes_anterior > 0:
        taxa_ativos = ((ativos_mes_atual - ativos_mes_anterior) / ativos_mes_anterior) * 100
    else:
        taxa_ativos = 100 if ativos_mes_atual > 0 else 0

    inativos_mes_atual = Vendedor.objects.filter(ativo=False, criado_em__gte=inicio_mes_atual).count()
    inativos_mes_anterior = Vendedor.objects.filter(
        ativo=False,
        criado_em__gte=inicio_mes_anterior,
        criado_em__lt=inicio_mes_atual
    ).count()
    if inativos_mes_anterior > 0:
        taxa_inativos = ((inativos_mes_atual - inativos_mes_anterior) / inativos_mes_anterior) * 100
    else:
        taxa_inativos = 100 if inativos_mes_atual > 0 else 0

    comissao_media = vendedores_list.filter(ativo=True).aggregate(
        media=Avg('comissao_padrao')
    )['media'] or 0

    comissao_mes_anterior = Vendedor.objects.filter(
        ativo=True,
        criado_em__lt=inicio_mes_atual
    ).aggregate(media=Avg('comissao_padrao'))['media'] or 0

    if comissao_mes_anterior > 0:
        taxa_comissao = ((comissao_media - comissao_mes_anterior) / comissao_mes_anterior) * 100
    else:
        taxa_comissao = 0

    per_page = request.GET.get('per_page', 25)
    try:
        per_page = int(per_page)
        if per_page not in [10, 25, 50, 100]:
            per_page = 25
    except ValueError:
        per_page = 25

    paginator = Paginator(vendedores_list, per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'vendedores': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'per_page': per_page,
        'search': search,
        'total': total,
        'total_ativos': total_ativos,
        'total_inativos': total_inativos,
        'percentual_ativos': round(percentual_ativos, 1),
        'percentual_inativos': round(percentual_inativos, 1),
        'taxa_crescimento': round(taxa_crescimento, 1),
        'taxa_ativos': round(taxa_ativos, 1),
        'taxa_inativos': round(taxa_inativos, 1),
        'comissao_media': round(comissao_media, 2),
        'taxa_comissao': round(taxa_comissao, 1),
    }
    return render(request, 'cadastro/vendedor_manager.html', context)


@login_required
def vendedor_form(request, pk=None):
    """Cadastro/edição de vendedor"""
    vendedor = get_object_or_404(Vendedor, pk=pk) if pk else None

    if request.method == 'POST':
        form = VendedorForm(request.POST, request.FILES, instance=vendedor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Vendedor salvo com sucesso!')
            return redirect('ERP_ServicesBI:vendedor_manager')
        return render(request, 'cadastro/vendedor_form.html', {
            'form': form,
            'vendedor': vendedor,
        })
    else:
        form = VendedorForm(instance=vendedor)

    return render(request, 'cadastro/vendedor_form.html', {
        'form': form,
        'vendedor': vendedor,
    })


@login_required
@require_http_methods(["POST"])
def vendedor_excluir(request, pk):
    """Exclusão AJAX de vendedor"""
    vendedor = get_object_or_404(Vendedor, pk=pk)
    nome = vendedor.nome
    try:
        if vendedor.foto:
            vendedor.foto.delete()
        vendedor.delete()
        return JsonResponse({'success': True, 'message': f'Vendedor "{nome}" excluído com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao excluir vendedor: {str(e)}'}, status=500)


# =============================================================================
# MÓDULO: CADASTRO - EMPRESAS
# =============================================================================

@login_required
def empresa_manager(request):
    """Listagem de empresas com cards de resumo"""
    search = request.GET.get('search', '')
    per_page = request.GET.get('per_page', 25)
    try:
        per_page = int(per_page)
    except (ValueError, TypeError):
        per_page = 25

    empresas = Empresa.objects.all()
    if search:
        empresas = empresas.filter(
            Q(nome_fantasia__icontains=search) |
            Q(razao_social__icontains=search) |
            Q(cnpj__icontains=search)
        )

    total = empresas.count()
    total_ativos = empresas.filter(ativo=True).count()
    total_inativos = total - total_ativos
    percentual_ativos = round((total_ativos / total * 100), 1) if total > 0 else 0
    percentual_inativos = round((total_inativos / total * 100), 1) if total > 0 else 0

    paginator = Paginator(empresas.order_by('nome_fantasia'), per_page)
    page = request.GET.get('page', 1)
    try:
        empresas_page = paginator.page(page)
    except PageNotAnInteger:
        empresas_page = paginator.page(1)
    except EmptyPage:
        empresas_page = paginator.page(paginator.num_pages)

    context = {
        'empresas': empresas_page,
        'total': total,
        'total_ativos': total_ativos,
        'total_inativos': total_inativos,
        'percentual_ativos': percentual_ativos,
        'percentual_inativos': percentual_inativos,
        'search': search,
        'per_page': per_page,
    }
    return render(request, 'cadastro/empresa_manager.html', context)


@login_required
def empresa_form(request, pk=None):
    """Cadastro/edição de empresa"""
    empresa = get_object_or_404(Empresa, pk=pk) if pk else None

    if request.method == 'POST':
        form = EmpresaForm(request.POST, instance=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Empresa salva com sucesso!')
            return redirect('ERP_ServicesBI:empresa_manager')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = EmpresaForm(instance=empresa)

    return render(request, 'cadastro/empresa_form.html', {
        'form': form,
        'empresa': empresa,
    })


@login_required
@require_http_methods(["POST"])
def empresa_excluir(request, pk):
    """Exclusão AJAX de empresa"""
    empresa = get_object_or_404(Empresa, pk=pk)
    try:
        nome = empresa.nome_fantasia or empresa.razao_social
        empresa.delete()
        return JsonResponse({'success': True, 'message': f'Empresa "{nome}" excluída com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao excluir: {str(e)}'}, status=400)


# =============================================================================
# MÓDULO: CADASTRO - PRODUTOS
# =============================================================================

@login_required
def produto_manager(request):
    """Manager de produtos com cards de resumo"""
    search = request.GET.get('search', '')
    categoria_id = request.GET.get('categoria')
    per_page = request.GET.get('per_page', 25)
    try:
        per_page = int(per_page)
    except (ValueError, TypeError):
        per_page = 25

    produtos = Produto.objects.all()
    if search:
        produtos = produtos.filter(
            Q(descricao__icontains=search) |
            Q(codigo__icontains=search) |
            Q(codigo_barras__icontains=search)
        )
    if categoria_id:
        produtos = produtos.filter(categoria_id=categoria_id)

    total = produtos.count()
    total_ativos = produtos.filter(ativo=True).count()
    total_inativos = total - total_ativos
    estoque_baixo = produtos.filter(estoque_atual__lte=F('estoque_minimo')).count()

    paginator = Paginator(produtos.order_by('descricao'), per_page)
    page = request.GET.get('page', 1)
    try:
        produtos_page = paginator.page(page)
    except PageNotAnInteger:
        produtos_page = paginator.page(1)
    except EmptyPage:
        produtos_page = paginator.page(paginator.num_pages)

    context = {
        'produtos': produtos_page,
        'total': total,
        'total_ativos': total_ativos,
        'total_inativos': total_inativos,
        'estoque_baixo': estoque_baixo,
        'search': search,
        'categoria_id': categoria_id,
        'categorias': CategoriaProduto.objects.filter(ativo=True),
        'per_page': per_page,
    }
    return render(request, 'cadastro/produto_manager.html', context)


@login_required
def produto_form(request, pk=None):
    """Cadastro/edição de produto"""
    produto = get_object_or_404(Produto, pk=pk) if pk else None

    if request.method == 'POST':
        form = ProdutoForm(request.POST, instance=produto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produto salvo com sucesso!')
            return redirect('ERP_ServicesBI:produto_manager')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = ProdutoForm(instance=produto)

    return render(request, 'cadastro/produto_form.html', {
        'form': form,
        'produto': produto,
        'categorias': CategoriaProduto.objects.filter(ativo=True),
    })


@login_required
@require_http_methods(["POST"])
def produto_excluir(request, pk):
    """Exclusão AJAX de produto"""
    produto = get_object_or_404(Produto, pk=pk)
    try:
        descricao = produto.descricao
        produto.delete()
        return JsonResponse({'success': True, 'message': f'Produto "{descricao}" excluído com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao excluir: {str(e)}'}, status=400)


# =============================================================================
# APIs AJAX - CATEGORIA DE PRODUTO (embutida no Produto)
# =============================================================================

@login_required
@require_http_methods(["POST"])
def categoria_produto_create_ajax(request):
    """Criação AJAX de Categoria de Produto"""
    try:
        nome = request.POST.get('nome', '').strip()
        descricao = request.POST.get('descricao', '')

        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'}, status=400)

        categoria = CategoriaProduto.objects.create(
            nome=nome,
            descricao=descricao,
            ativo=True
        )
        return JsonResponse({
            'success': True,
            'id': categoria.id,
            'nome': categoria.nome,
            'message': f'Categoria "{categoria.nome}" criada com sucesso!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao criar: {str(e)}'}, status=500)


@login_required
@require_http_methods(["POST"])
def categoria_produto_delete_ajax(request, pk):
    """Exclusão AJAX de Categoria de Produto"""
    try:
        categoria = get_object_or_404(CategoriaProduto, pk=pk)
        if Produto.objects.filter(categoria=categoria).exists():
            return JsonResponse({
                'success': False,
                'message': 'Não é possível excluir. Categoria está em uso por produtos.'
            }, status=400)
        nome = categoria.nome
        categoria.delete()
        return JsonResponse({'success': True, 'message': f'Categoria "{nome}" excluída com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao excluir: {str(e)}'}, status=500)


# =============================================================================
# APIs - CONDIÇÃO DE PAGAMENTO (versão única, sem duplicata)
# =============================================================================

@login_required
@require_http_methods(["POST"])
def api_condicao_pagamento_criar(request):
    """API para criar nova condição de pagamento via AJAX"""
    try:
        data = json.loads(request.body)

        descricao = data.get('descricao', '').strip()
        parcelas = data.get('parcelas', 1)
        periodicidade = data.get('periodicidade', 'mensal')
        dias_primeira_parcela = data.get('dias_primeira_parcela', 0)

        if not descricao:
            return JsonResponse({'success': False, 'message': 'Descrição é obrigatória'}, status=400)
        if not parcelas or int(parcelas) < 1:
            return JsonResponse({'success': False, 'message': 'Mínimo 1 parcela'}, status=400)
        if int(parcelas) > 24:
            return JsonResponse({'success': False, 'message': 'Máximo 24 parcelas'}, status=400)

        periodos_validos = [p[0] for p in CondicaoPagamento.PERIODICIDADE_CHOICES]
        if periodicidade not in periodos_validos:
            return JsonResponse({'success': False, 'message': 'Periodicidade inválida'}, status=400)

        condicao = CondicaoPagamento.objects.create(
            descricao=descricao,
            parcelas=int(parcelas),
            periodicidade=periodicidade,
            dias_primeira_parcela=int(dias_primeira_parcela),
            ativo=True
        )
        return JsonResponse({
            'success': True,
            'id': condicao.id,
            'descricao': condicao.descricao,
            'descricao_completa': f'{condicao.descricao} ({condicao.resumo})',
            'resumo': condicao.resumo,
            'prazo_total': condicao.prazo_total_dias,
            'message': f'Condição "{condicao.descricao}" criada com sucesso!'
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Dados inválidos'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao criar: {str(e)}'}, status=500)


@login_required
@require_http_methods(["POST"])
def api_condicao_pagamento_excluir(request, pk):
    """API para excluir condição de pagamento via AJAX"""
    try:
        condicao = get_object_or_404(CondicaoPagamento, pk=pk)
        descricao = condicao.descricao

        if condicao.clientes_condicao.exists():
            return JsonResponse({
                'success': False,
                'message': f'Não é possível excluir. Condição "{descricao}" está em uso por clientes.'
            }, status=400)

        condicao.delete()
        return JsonResponse({'success': True, 'message': f'Condição "{descricao}" excluída com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao excluir: {str(e)}'}, status=500)


# Aliases para compatibilidade com urls.py que referenciam ambos os nomes
condicao_pagamento_criar_api = api_condicao_pagamento_criar
condicao_pagamento_excluir_api = api_condicao_pagamento_excluir


# =============================================================================
# APIs - FORMA DE PAGAMENTO (versão única, sem duplicata)
# =============================================================================

@login_required
@require_http_methods(["POST"])
def api_forma_pagamento_criar(request):
    """API para criar nova forma de pagamento via AJAX"""
    try:
        data = json.loads(request.body)

        descricao = data.get('descricao', '').strip()
        tipo = data.get('tipo', '').strip()

        if not descricao:
            return JsonResponse({'success': False, 'message': 'Descrição é obrigatória'}, status=400)
        if not tipo:
            return JsonResponse({'success': False, 'message': 'Tipo é obrigatório'}, status=400)

        tipos_validos = [t[0] for t in FormaPagamento.TIPO_CHOICES]
        if tipo not in tipos_validos:
            return JsonResponse({'success': False, 'message': 'Tipo inválido'}, status=400)

        forma = FormaPagamento.objects.create(
            descricao=descricao,
            tipo=tipo,
            ativo=True
        )
        tipo_display = forma.get_tipo_display()
        return JsonResponse({
            'success': True,
            'id': forma.id,
            'descricao': f'{forma.descricao} ({tipo_display})',
            'message': f'Forma "{forma.descricao}" criada com sucesso!'
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Dados inválidos'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao criar: {str(e)}'}, status=500)


@login_required
@require_http_methods(["POST"])
def api_forma_pagamento_excluir(request, pk):
    """API para excluir forma de pagamento via AJAX"""
    try:
        forma = get_object_or_404(FormaPagamento, pk=pk)
        descricao = forma.descricao

        if forma.clientes_forma.exists():
            return JsonResponse({
                'success': False,
                'message': f'Não é possível excluir. Forma "{descricao}" está em uso por clientes.'
            }, status=400)

        forma.delete()
        return JsonResponse({'success': True, 'message': f'Forma "{descricao}" excluída com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao excluir: {str(e)}'}, status=500)


# Aliases para compatibilidade
forma_pagamento_criar_api = api_forma_pagamento_criar
forma_pagamento_excluir_api = api_forma_pagamento_excluir


# =============================================================================
# MÓDULO: COMPRAS - COTAÇÕES COMPARATIVAS
# =============================================================================
# NOTA: Este bloco inteiro estava dentro de uma string Python (views_corrigido = '''...''')
# e portanto NUNCA era executado. Agora está como código real.
# =============================================================================

@login_required
def cotacao_manager(request):
    """
    Manager unificado de cotações (lista + wizard embutido).
    Otimizado com prefetch_related para reduzir queries.
    """
    search = request.GET.get('search', '').strip()[:100]
    status = request.GET.get('status', '').strip()

    cotacoes = CotacaoMae.objects.select_related(
        'solicitante'
    ).prefetch_related(
        'itens_solicitados',
        'cotacoes_fornecedor'
    ).order_by('-data_solicitacao')

    if search:
        cotacoes = cotacoes.filter(
            Q(numero__icontains=search) | Q(titulo__icontains=search)
        )
    if status:
        cotacoes = cotacoes.filter(status=status)

    paginator = Paginator(cotacoes, 25)
    page_number = request.GET.get('page')
    cotacoes_page = paginator.get_page(page_number)

    contadores = CotacaoMae.objects.aggregate(
        total=Count('id'),
        em_andamento=Count('id', filter=Q(status__in=['RASCUNHO', 'ENVIADA'])),
        respondidas=Count('id', filter=Q(status='RESPONDIDA')),
        concluidas=Count('id', filter=Q(status='CONCLUIDA'))
    )

    produtos = Produto.objects.filter(ativo=True).order_by('descricao')[:500]
    fornecedores = Fornecedor.objects.filter(ativo=True).order_by('nome_fantasia', 'nome_razao_social')[:200]
    condicoes_pagamento = CondicaoPagamento.objects.filter(ativo=True).order_by('descricao')
    formas_pagamento = FormaPagamento.objects.filter(ativo=True).order_by('descricao')

    context = {
        'cotacoes': cotacoes_page,
        'total_cotacoes': contadores['total'],
        'em_andamento': contadores['em_andamento'],
        'respondidas': contadores['respondidas'],
        'concluidas': contadores['concluidas'],
        'produtos': produtos,
        'fornecedores': fornecedores,
        'condicoes_pagamento': condicoes_pagamento,
        'formas_pagamento': formas_pagamento,
        'search': search,
        'status': status,
    }
    return render(request, 'compras/cotacao_manager.html', context)


# =============================================================================
# APIs DE COTAÇÃO
# =============================================================================

@login_required
@require_POST
def cotacao_salvar_api(request):
    """API unificada para salvar cotação (dados + itens + fornecedores)."""
    try:
        if len(request.body) > 10 * 1024 * 1024:
            return resposta_erro_segura('Payload muito grande (máximo 10MB)', 413)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return resposta_erro_segura('Formato JSON inválido', 400)

        titulo = data.get('titulo', '').strip()
        if not titulo:
            return resposta_erro_segura('Título é obrigatório', 400)

        pk = data.get('id')

        with transaction.atomic():
            if pk:
                cotacao = get_object_or_404(CotacaoMae, pk=pk)
            else:
                cotacao = CotacaoMae(solicitante=request.user)

            cotacao.titulo = titulo[:255]
            cotacao.setor = data.get('setor', '').strip()[:100]
            cotacao.observacoes = data.get('observacoes', '').strip()[:2000]

            if data.get('data_limite'):
                try:
                    cotacao.data_limite_resposta = datetime.fromisoformat(
                        data['data_limite'].replace('Z', '+00:00')
                    ).date()
                except (ValueError, AttributeError):
                    pass

            cotacao.status = data.get('status', 'RASCUNHO')
            cotacao.save()

            # Salvar itens
            itens_data = data.get('itens', [])
            if itens_data:
                cotacao.itens_solicitados.all().delete()
                itens_criar = []
                for item_data in itens_data[:1000]:
                    produto_id = item_data.get('produto_id')
                    descricao_manual = item_data.get('descricao_manual', '').strip()[:500]

                    if not produto_id and not descricao_manual:
                        continue

                    try:
                        quantidade = Decimal(str(item_data.get('quantidade', 1)))
                        if quantidade <= 0 or quantidade > 999999:
                            quantidade = Decimal('1')
                    except (InvalidOperation, ValueError):
                        quantidade = Decimal('1')

                    itens_criar.append(ItemSolicitado(
                        cotacao_mae=cotacao,
                        produto_id=produto_id if produto_id else None,
                        descricao_manual=descricao_manual if not produto_id else '',
                        quantidade=quantidade,
                        unidade_medida=item_data.get('unidade_medida', 'UN').strip()[:10],
                        observacao=item_data.get('observacao', '').strip()[:500]
                    ))

                if itens_criar:
                    ItemSolicitado.objects.bulk_create(itens_criar)

            # Salvar fornecedores
            fornecedores_ids = data.get('fornecedores', [])
            if fornecedores_ids:
                fornecedores_validos = Fornecedor.objects.filter(
                    id__in=fornecedores_ids[:50],
                    ativo=True
                ).values_list('id', flat=True)

                cotacao.cotacoes_fornecedor.exclude(
                    fornecedor_id__in=fornecedores_validos
                ).delete()

                for forn_id in fornecedores_validos:
                    CotacaoFornecedor.objects.get_or_create(
                        cotacao_mae=cotacao,
                        fornecedor_id=forn_id,
                        defaults={
                            'status': 'pendente',
                            'condicao_pagamento': '',
                            'forma_pagamento': ''
                        }
                    )

            itens_salvos = list(cotacao.itens_solicitados.values(
                'id', 'produto_id', 'descricao_manual', 'quantidade', 'unidade_medida'
            ))
            fornecedores_salvos = list(cotacao.cotacoes_fornecedor.values_list(
                'fornecedor_id', flat=True
            ))

            return JsonResponse({
                'success': True,
                'id': cotacao.pk,
                'numero': cotacao.numero,
                'itens': itens_salvos,
                'fornecedores': fornecedores_salvos,
                'message': 'Cotação salva com sucesso!'
            })

    except Exception as e:
        log_erro_seguro('cotacao_salvar_api', e, request)
        return resposta_erro_segura('Erro interno ao salvar cotação. Tente novamente.', 500)


@login_required
@require_GET
def cotacao_dados_api(request, pk):
    """API para buscar dados completos da cotação."""
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)

        itens = list(cotacao.itens_solicitados.select_related('produto').values(
            'id', 'produto_id', 'descricao_manual', 'descricao_display',
            'quantidade', 'unidade_medida', 'observacao'
        ))
        fornecedores_ids = list(cotacao.cotacoes_fornecedor.values_list(
            'fornecedor_id', flat=True
        ))

        return JsonResponse({
            'success': True,
            'id': cotacao.id,
            'numero': cotacao.numero,
            'titulo': cotacao.titulo,
            'setor': cotacao.setor,
            'status': cotacao.status,
            'data_limite': cotacao.data_limite_resposta.isoformat() if cotacao.data_limite_resposta else None,
            'observacoes': cotacao.observacoes or '',
            'itens': itens,
            'fornecedores': fornecedores_ids,
        })
    except Exception as e:
        log_erro_seguro('cotacao_dados_api', e, request, {'cotacao_id': pk})
        return resposta_erro_segura('Erro ao buscar dados da cotação', 500)


@login_required
@require_GET
def cotacao_comparativo_api(request, pk):
    """API para buscar dados do comparativo de preços."""
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        comparativo = montar_comparativo_otimizado(cotacao)

        itens = []
        fornecedores_list = []
        respostas = {}

        forn_ids = set()
        for linha in comparativo:
            for f in linha['fornecedores']:
                forn_ids.add(f['cotacao_fornecedor'].id)

        for cf in cotacao.cotacoes_fornecedor.select_related('fornecedor').all():
            if cf.id in forn_ids:
                fornecedores_list.append({
                    'id': cf.id,
                    'nome': cf.fornecedor.nome_fantasia or cf.fornecedor.nome_razao_social,
                    'condicao': cf.condicao_pagamento or 'À vista',
                })
                respostas[cf.id] = {}

        for linha in comparativo:
            item = linha['item']
            itens.append({
                'id': item.id,
                'nome': item.descricao_display,
                'quantidade': float(item.quantidade),
                'unidade': item.unidade_medida,
            })
            for f in linha['fornecedores']:
                cf_id = f['cotacao_fornecedor'].id
                if f['item_cotacao'] and f['preco_unitario']:
                    respostas[cf_id][item.id] = {
                        'preco': float(f['preco_unitario']),
                        'prazo': f['prazo'] or 0,
                        'melhor_preco': f['melhor_preco'],
                        'melhor_prazo': f['melhor_prazo'],
                    }

        return JsonResponse({
            'success': True,
            'itens': itens,
            'fornecedores': fornecedores_list,
            'respostas': respostas,
        })
    except Exception as e:
        log_erro_seguro('cotacao_comparativo_api', e, request, {'cotacao_id': pk})
        return resposta_erro_segura('Erro ao gerar comparativo', 500)


# =============================================================================
# FUNÇÃO OTIMIZADA - montar_comparativo_otimizado
# =============================================================================

def montar_comparativo_otimizado(cotacao):
    """
    Monta estrutura de dados para o quadro comparativo.
    Otimizado: de O(n×m) queries para apenas 4 queries totais.
    """
    itens_solicitados = list(
        cotacao.itens_solicitados.select_related('produto').all()
    )

    cotacoes_fornecedor = (
        cotacao.cotacoes_fornecedor
        .select_related('fornecedor')
        .prefetch_related(
            Prefetch(
                'itens',
                queryset=ItemCotacaoFornecedor.objects.select_related('item_solicitado'),
                to_attr='itens_pre_carregados'
            )
        )
        .all()
    )
    cotacoes_list = list(cotacoes_fornecedor)

    # Lookup O(1) em memória
    itens_por_cotacao = {}
    for cf in cotacoes_list:
        for item_cot in getattr(cf, 'itens_pre_carregados', []):
            key = (cf.id, item_cot.item_solicitado_id)
            itens_por_cotacao[key] = item_cot

    comparativo = []

    for item in itens_solicitados:
        linha = {
            'item': item,
            'fornecedores': [],
            'menor_preco': None,
            'maior_preco': None,
            'menor_prazo': None,
        }

        precos = []
        prazos = []

        for cf in cotacoes_list:
            key = (cf.id, item.id)
            item_cot = itens_por_cotacao.get(key)

            prazo = None
            if item_cot:
                prazo = item_cot.prazo_entrega_item or cf.prazo_entrega_dias

            dados_fornecedor = {
                'cotacao_fornecedor': cf,
                'item_cotacao': item_cot,
                'preco_unitario': item_cot.preco_unitario if item_cot else None,
                'preco_total': item_cot.preco_total if item_cot else None,
                'disponivel': item_cot.disponivel if item_cot else False,
                'prazo': prazo,
                'selecionado': item_cot.selecionado if item_cot else False,
                'sugerido': item_cot.sugerido if item_cot else False,
                'melhor_preco': False,
                'maior_preco': False,
                'melhor_prazo': False,
            }

            if item_cot and item_cot.disponivel and item_cot.preco_unitario:
                precos.append((cf.id, float(item_cot.preco_unitario)))
                if prazo:
                    prazos.append((cf.id, prazo))

            linha['fornecedores'].append(dados_fornecedor)

        # Identificar melhores opções
        if precos:
            menor_preco_id = min(precos, key=lambda x: x[1])[0]
            linha['menor_preco'] = menor_preco_id
            for f in linha['fornecedores']:
                if f['cotacao_fornecedor'].id == menor_preco_id:
                    f['melhor_preco'] = True

            if len(precos) >= 3:
                maior_preco_id = max(precos, key=lambda x: x[1])[0]
                linha['maior_preco'] = maior_preco_id
                for f in linha['fornecedores']:
                    if f['cotacao_fornecedor'].id == maior_preco_id:
                        f['maior_preco'] = True

        if prazos:
            menor_prazo_id = min(prazos, key=lambda x: x[1])[0]
            linha['menor_prazo'] = menor_prazo_id
            for f in linha['fornecedores']:
                if f['cotacao_fornecedor'].id == menor_prazo_id:
                    f['melhor_prazo'] = True

        comparativo.append(linha)

    # Totais por fornecedor
    for cf in cotacoes_list:
        cf.menor_total = False

    if cotacoes_list:
        totais = [
            (cf.id, float(cf.valor_total_liquido or 0))
            for cf in cotacoes_list
        ]
        if totais:
            menor_total_id = min(totais, key=lambda x: x[1])[0]
            for cf in cotacoes_list:
                if cf.id == menor_total_id:
                    cf.menor_total = True

    return comparativo


# =============================================================================
# APIs DE AÇÃO - COTAÇÕES
# =============================================================================

@login_required
@require_POST
def cotacao_excluir_api(request, pk):
    """API para excluir cotação."""
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        cotacao.delete()
        return JsonResponse({'success': True, 'message': 'Cotação excluída com sucesso!'})
    except Exception as e:
        log_erro_seguro('cotacao_excluir_api', e, request, {'cotacao_id': pk})
        return resposta_erro_segura('Erro ao excluir cotação', 500)


@login_required
@require_POST
def cotacao_enviar_api(request, pk):
    """API para enviar cotação aos fornecedores."""
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        cotacao.status = 'ENVIADA'
        cotacao.save()
        return JsonResponse({'success': True, 'message': 'Cotação enviada aos fornecedores!'})
    except Exception as e:
        log_erro_seguro('cotacao_enviar_api', e, request, {'cotacao_id': pk})
        return resposta_erro_segura('Erro ao enviar cotação', 500)


@login_required
@require_POST
def cotacao_concluir_api(request, pk):
    """API para concluir cotação."""
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        cotacao.status = 'CONCLUIDA'
        cotacao.save()
        return JsonResponse({'success': True, 'message': 'Cotação concluída!'})
    except Exception as e:
        log_erro_seguro('cotacao_concluir_api', e, request, {'cotacao_id': pk})
        return resposta_erro_segura('Erro ao concluir cotação', 500)


# =============================================================================
# IMPORTAÇÃO DE ARQUIVOS DE COTAÇÃO
# =============================================================================

@login_required
@require_POST
def cotacao_importar_fornecedor(request, pk):
    """Importa arquivo de cotação do fornecedor (CSV/Excel/PDF)."""
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)

        fornecedor_id = request.POST.get('fornecedor_id')
        arquivo = request.FILES.get('arquivo')

        if not fornecedor_id:
            return resposta_erro_segura('Selecione um fornecedor', 400)
        if not arquivo:
            return resposta_erro_segura('Selecione um arquivo', 400)

        # ========== VALIDAÇÃO DE ARQUIVO ATUALIZADA ==========
        nome_arquivo = arquivo.name.lower()
        extensoes_validas = ('.csv', '.xlsx', '.xls', '.pdf')  # ← ADICIONADO .pdf
        
        if not nome_arquivo.endswith(extensoes_validas):
            return resposta_erro_segura(
                'Apenas arquivos CSV, Excel (.xlsx, .xls) ou PDF são permitidos', 
                400
            )
        
        if arquivo.size > 10 * 1024 * 1024:
            return resposta_erro_segura('Arquivo muito grande (máximo 10MB)', 413)

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
            try:
                # ========== PROCESSAMENTO ATUALIZADO ==========
                processar_arquivo_cotacao_seguro(cotacao, cotacao_forn, arquivo)
                cotacao_forn.calcular_total()
            except Exception as e:
                log_erro_seguro('processar_arquivo_cotacao', e, request, {
                    'arquivo': nome_arquivo,
                    'fornecedor_id': fornecedor_id
                })
                return resposta_erro_segura('Erro ao processar arquivo. Verifique o formato.', 400)

        # Restante dos campos (prazo, condição, etc.)
        try:
            cotacao_forn.prazo_entrega_dias = int(request.POST.get('prazo_entrega', 0) or 0)
        except (ValueError, TypeError):
            cotacao_forn.prazo_entrega_dias = 0

        cotacao_forn.condicao_pagamento = request.POST.get('condicao_pagamento', '')[:100]
        cotacao_forn.forma_pagamento = request.POST.get('forma_pagamento', '')[:100]

        try:
            cotacao_forn.percentual_desconto = Decimal(request.POST.get('desconto', 0) or 0)
        except (InvalidOperation, ValueError):
            cotacao_forn.percentual_desconto = Decimal('0')

        try:
            cotacao_forn.valor_frete = Decimal(request.POST.get('frete', 0) or 0)
        except (InvalidOperation, ValueError):
            cotacao_forn.valor_frete = Decimal('0')

        try:
            cotacao_forn.nota_confiabilidade = int(request.POST.get('confiabilidade', 5) or 5)
        except (ValueError, TypeError):
            cotacao_forn.nota_confiabilidade = 5

        cotacao_forn.observacoes = request.POST.get('observacoes', '')[:1000]
        cotacao_forn.status = 'processada'
        cotacao_forn.save()
        cotacao_forn.calcular_total()

        cotacao.status = 'RESPONDIDA'
        cotacao.save()

        return JsonResponse({
            'success': True,
            'cotacao_fornecedor_id': cotacao_forn.pk,
            'fornecedor_nome': fornecedor.nome_fantasia or fornecedor.nome_razao_social,
            'total_itens': cotacao_forn.itens.count(),
            'valor_total': float(cotacao_forn.valor_total_liquido or 0),
            'message': 'Cotação importada com sucesso!'
        })
    except Exception as e:
        log_erro_seguro('cotacao_importar_fornecedor', e, request, {'cotacao_id': pk})
        return resposta_erro_segura('Erro ao importar cotação', 500)


# =============================================================================
# PROCESSAMENTO DE ARQUIVOS (CSV/Excel/PDF)
# =============================================================================

def processar_arquivo_cotacao_seguro(cotacao_mae, cotacao_forn, arquivo):
    """Processa arquivo de cotação (CSV, Excel ou PDF)."""
    nome_arquivo = arquivo.name.lower()
    cotacao_forn.itens.all().delete()

    if nome_arquivo.endswith('.csv'):
        processar_csv_seguro(cotacao_mae, cotacao_forn, arquivo)
    elif nome_arquivo.endswith(('.xlsx', '.xls')):
        processar_excel_seguro(cotacao_mae, cotacao_forn, arquivo)
    elif nome_arquivo.endswith('.pdf'):  # ← NOVO!
        processar_pdf_seguro(cotacao_mae, cotacao_forn, arquivo)
    else:
        raise ValueError("Formato de arquivo não suportado")


def processar_csv_seguro(cotacao_mae, cotacao_forn, arquivo):
    """Processa arquivo CSV com detecção automática de delimitador."""
    try:
        conteudo = arquivo.read().decode('utf-8')
    except UnicodeDecodeError:
        arquivo.seek(0)
        conteudo = arquivo.read().decode('latin-1')

    if len(conteudo) > 5 * 1024 * 1024:
        raise ValueError("Arquivo CSV muito grande")

    primeira_linha = conteudo.split('\n')[0] if conteudo else ''
    delimitador = ';' if ';' in primeira_linha else ','

    leitor = csv.DictReader(io.StringIO(conteudo), delimiter=delimitador)
    if leitor.fieldnames:
        leitor.fieldnames = [normalizar_nome_coluna(col) for col in leitor.fieldnames]

    itens_criar = []
    for i, row in enumerate(leitor):
        if i >= 1000:
            break
        item = criar_item_cotacao_seguro(cotacao_mae, cotacao_forn, row)
        if item:
            itens_criar.append(item)

    if itens_criar:
        ItemCotacaoFornecedor.objects.bulk_create(itens_criar, batch_size=100)


def processar_excel_seguro(cotacao_mae, cotacao_forn, arquivo):
    """Processa arquivo Excel."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(arquivo, data_only=True, read_only=True)
        ws = wb.active
        headers = [normalizar_nome_coluna(str(cell.value or '')) for cell in ws[1]]

        itens_criar = []
        for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=1):
            if i > 1000:
                break
            row_dict = dict(zip(headers, row))
            item = criar_item_cotacao_seguro(cotacao_mae, cotacao_forn, row_dict)
            if item:
                itens_criar.append(item)

        if itens_criar:
            ItemCotacaoFornecedor.objects.bulk_create(itens_criar, batch_size=100)
        wb.close()

    except ImportError:
        import pandas as pd
        df = pd.read_excel(arquivo)
        itens_criar = []
        for i, (_, row) in enumerate(df.iterrows(), start=1):
            if i > 1000:
                break
            row_dict = {normalizar_nome_coluna(str(k)): v for k, v in row.items()}
            item = criar_item_cotacao_seguro(cotacao_mae, cotacao_forn, row_dict)
            if item:
                itens_criar.append(item)
        if itens_criar:
            ItemCotacaoFornecedor.objects.bulk_create(itens_criar, batch_size=100)

def processar_pdf_seguro(cotacao_mae, cotacao_forn, arquivo):
    """Processa arquivo PDF extraindo tabela de cotação."""
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("Biblioteca pdfplumber não instalada. Execute: pip install pdfplumber")
    
    cotacao_forn.itens.all().delete()
    itens_criar = []
    
    with pdfplumber.open(arquivo) as pdf:
        for pagina in pdf.pages:
            # Tenta extrair tabelas automaticamente
            tabelas = pagina.extract_tables()
            
            for tabela in tabelas:
                if not tabela or len(tabela) < 2:
                    continue
                
                # Detecta header (primeira linha)
                header = [normalizar_nome_coluna(str(col or '')) for col in tabela[0]]
                
                for linha in tabela[1:]:
                    if len(linha) != len(header):
                        continue
                    
                    row_dict = dict(zip(header, linha))
                    item = criar_item_cotacao_seguro(cotacao_mae, cotacao_forn, row_dict)
                    if item:
                        itens_criar.append(item)
    
    if itens_criar:
        ItemCotacaoFornecedor.objects.bulk_create(itens_criar, batch_size=100)
    else:
        raise ValueError("Não foi possível extrair dados do PDF. Verifique se contém tabela estruturada.")


def normalizar_nome_coluna(nome):
    """Normaliza nome de coluna removendo acentos e espaços."""
    nome = str(nome).lower().strip()
    nome = unicodedata.normalize('NFD', nome)
    nome = ''.join(c for c in nome if not unicodedata.combining(c))
    return nome


def criar_item_cotacao_seguro(cotacao_mae, cotacao_forn, row):
    """Cria item de cotação a partir de uma linha do arquivo."""
    descricao = (
        row.get('descricao') or row.get('produto') or row.get('item') or
        row.get('material') or row.get('nome') or ''
    )
    descricao = str(descricao).strip()[:500] if descricao else ''
    if not descricao:
        return None

    quantidade_str = str(row.get('quantidade') or row.get('qtd') or row.get('qtde') or 1)
    try:
        quantidade = Decimal(str(quantidade_str).replace(',', '.').replace(' ', ''))
        if quantidade <= 0 or quantidade > 999999:
            quantidade = Decimal('1')
    except (InvalidOperation, ValueError):
        quantidade = Decimal('1')

    preco_str = str(
        row.get('preco_unitario') or row.get('preco') or
        row.get('valor_unitario') or row.get('valor') or 0
    )
    try:
        preco = preco_str.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
        preco_unitario = Decimal(preco)
        if preco_unitario < 0 or preco_unitario > 999999999:
            preco_unitario = Decimal('0')
    except (InvalidOperation, ValueError):
        preco_unitario = Decimal('0')

    codigo = str(row.get('codigo') or row.get('cod') or row.get('ref') or '')[:50]
    unidade = str(row.get('unidade') or row.get('un') or row.get('und') or 'UN')[:10]

    # Matching com item solicitado
    item_solicitado = None
    match_score = 0

    if not hasattr(cotacao_mae, '_itens_solicitados_cache'):
        cotacao_mae._itens_solicitados_cache = list(
            cotacao_mae.itens_solicitados.select_related('produto').all()
        )

    descricao_lower = descricao.lower()
    for item_sol in cotacao_mae._itens_solicitados_cache:
        desc_sol = item_sol.descricao_display.lower()

        if desc_sol == descricao_lower:
            item_solicitado = item_sol
            match_score = 100
            break

        if desc_sol in descricao_lower or descricao_lower in desc_sol:
            if match_score < 80:
                item_solicitado = item_sol
                match_score = 80

        if item_sol.produto and codigo:
            if item_sol.produto.codigo and item_sol.produto.codigo.lower() == codigo.lower():
                item_solicitado = item_sol
                match_score = 95
                break

    return ItemCotacaoFornecedor(
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


# =============================================================================
# GERAÇÃO DE PEDIDOS A PARTIR DA COTAÇÃO
# =============================================================================

@login_required
@require_POST
def cotacao_gerar_pedidos(request, pk):
    """Gera pedidos de compra a partir dos itens selecionados."""
    try:
        if len(request.body) > 5 * 1024 * 1024:
            return resposta_erro_segura('Payload muito grande', 413)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return resposta_erro_segura('JSON inválido', 400)

        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        pedidos_data = data.get('pedidos', [])
        if not pedidos_data:
            return resposta_erro_segura('Nenhum pedido para gerar', 400)

        pedidos_gerados = []

        with transaction.atomic():
            for pedido_data in pedidos_data[:50]:
                fornecedor_id = pedido_data.get('fornecedor_id')
                itens_data = pedido_data.get('itens', [])
                if not fornecedor_id or not itens_data:
                    continue

                try:
                    fornecedor = Fornecedor.objects.get(id=fornecedor_id, ativo=True)
                except Fornecedor.DoesNotExist:
                    continue

                cotacao_forn = CotacaoFornecedor.objects.filter(
                    cotacao_mae=cotacao, fornecedor=fornecedor
                ).first()

                prazo = cotacao_forn.prazo_entrega_dias if cotacao_forn else 15
                data_entrega = timezone.now().date() + timedelta(days=prazo)

                pedido = PedidoCompra.objects.create(
                    fornecedor=fornecedor,
                    cotacao_mae=cotacao,
                    cotacao_fornecedor=cotacao_forn,
                    data_prevista_entrega=data_entrega,
                    condicao_pagamento=cotacao_forn.condicao_pagamento if cotacao_forn else '',
                    forma_pagamento=cotacao_forn.forma_pagamento if cotacao_forn else '',
                    observacoes=f'Gerado a partir da cotação {cotacao.numero}',
                    status='pendente',
                )

                itens_pedido = []
                for item_data in itens_data[:1000]:
                    produto_nome = item_data.get('produto_nome', '')[:255]
                    quantidade = Decimal(str(item_data.get('quantidade', 1)))
                    preco_unitario = Decimal(str(item_data.get('preco_unitario', 0)))

                    produto = Produto.objects.filter(
                        descricao__iexact=produto_nome
                    ).first()
                    if not produto:
                        produto = Produto.objects.create(
                            descricao=produto_nome,
                            unidade='UN',
                            ativo=True,
                        )

                    itens_pedido.append(ItemPedidoCompra(
                        pedido=pedido,
                        produto=produto,
                        descricao=produto_nome,
                        quantidade=quantidade,
                        preco_unitario=preco_unitario,
                        preco_total=quantidade * preco_unitario
                    ))

                if itens_pedido:
                    ItemPedidoCompra.objects.bulk_create(itens_pedido)

                pedido.calcular_total()
                pedidos_gerados.append({
                    'id': pedido.pk,
                    'numero': pedido.numero,
                    'fornecedor': fornecedor.nome_fantasia or fornecedor.nome_razao_social,
                    'total_itens': len(itens_pedido),
                    'valor_total': float(pedido.valor_total)
                })

            if pedidos_gerados:
                cotacao.status = 'CONCLUIDA'
                cotacao.save()

        return JsonResponse({
            'success': True,
            'pedidos': pedidos_gerados,
            'message': f'{len(pedidos_gerados)} pedido(s) gerado(s) com sucesso!'
        })
    except Exception as e:
        log_erro_seguro('cotacao_gerar_pedidos', e, request, {'cotacao_id': pk})
        return resposta_erro_segura('Erro ao gerar pedidos', 500)


# =============================================================================
# OUTRAS APIs DE COTAÇÃO
# =============================================================================

@login_required
@require_GET
def cotacao_fornecedores_importados_api(request, pk):
    """Retorna APENAS fornecedores que já importaram cotações."""
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        fornecedores_importados = cotacao.cotacoes_fornecedor.exclude(
            arquivo_origem=''
        ).exclude(
            arquivo_origem__isnull=True
        ).values_list('fornecedor_id', flat=True)
        return JsonResponse({'success': True, 'importados': [int(fid) for fid in fornecedores_importados]})
    except Exception as e:
        log_erro_seguro('cotacao_fornecedores_importados_api', e, request, {'cotacao_id': pk})
        return resposta_erro_segura('Erro ao buscar fornecedores', 500)


@login_required
@require_POST
def cotacao_remover_fornecedor(request, pk, fornecedor_pk):
    """Remove cotação de um fornecedor."""
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        cotacao_forn = get_object_or_404(CotacaoFornecedor, cotacao_mae=cotacao, fornecedor_id=fornecedor_pk)
        cotacao_forn.delete()
        return JsonResponse({'success': True, 'message': 'Fornecedor removido com sucesso!'})
    except Exception as e:
        log_erro_seguro('cotacao_remover_fornecedor', e, request)
        return resposta_erro_segura('Erro ao remover fornecedor', 500)


@login_required
@require_POST
def cotacao_calcular_sugestoes(request, pk):
    """Calcula sugestões automáticas baseado em preço, prazo e confiabilidade."""
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)

        try:
            peso_preco = float(request.POST.get('peso_preco', 50)) / 100
            peso_prazo = float(request.POST.get('peso_prazo', 30)) / 100
            peso_confiabilidade = float(request.POST.get('peso_confiabilidade', 20)) / 100
        except (ValueError, TypeError):
            peso_preco, peso_prazo, peso_confiabilidade = 0.5, 0.3, 0.2

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
                precos = [float(i.preco_unitario) for i in itens_cot if i.preco_unitario]
                if not precos:
                    continue

                max_preco = max(precos)
                min_preco = min(precos)
                range_preco = max_preco - min_preco if max_preco != min_preco else 1

                for item in itens_cot:
                    prazo = item.prazo_entrega_item or item.cotacao_fornecedor.prazo_entrega_dias or 30
                    confiabilidade = item.cotacao_fornecedor.nota_confiabilidade or 5

                    score_preco = 1 - ((float(item.preco_unitario) - min_preco) / range_preco) if range_preco else 1
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
        log_erro_seguro('cotacao_calcular_sugestoes', e, request, {'cotacao_id': pk})
        return resposta_erro_segura('Erro ao calcular sugestões', 500)


@login_required
@require_POST
def cotacao_salvar_selecao(request, pk):
    """Salva itens selecionados para compra."""
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        try:
            data = json.loads(request.body)
            itens_selecionados = data.get('itens_selecionados', [])
        except json.JSONDecodeError:
            return resposta_erro_segura('JSON inválido', 400)

        if not isinstance(itens_selecionados, list):
            return resposta_erro_segura('Formato inválido', 400)
        if len(itens_selecionados) > 1000:
            return resposta_erro_segura('Muitos itens selecionados', 400)

        with transaction.atomic():
            ItemCotacaoFornecedor.objects.filter(
                cotacao_fornecedor__cotacao_mae=cotacao
            ).update(selecionado=False)

            if itens_selecionados:
                itens_validos = ItemCotacaoFornecedor.objects.filter(
                    id__in=itens_selecionados,
                    cotacao_fornecedor__cotacao_mae=cotacao
                ).values_list('id', flat=True)
                ItemCotacaoFornecedor.objects.filter(id__in=list(itens_validos)).update(selecionado=True)

        return JsonResponse({'success': True, 'message': 'Seleção salva com sucesso!'})
    except Exception as e:
        log_erro_seguro('cotacao_salvar_selecao', e, request, {'cotacao_id': pk})
        return resposta_erro_segura('Erro ao salvar seleção', 500)


# =============================================================================
# FUNÇÕES DE TEXTO (EMAIL/WHATSAPP)
# =============================================================================

@login_required
@require_GET
def cotacao_copiar_lista_email(request, pk):
    """Gera texto formatado para email."""
    try:
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
    except Exception as e:
        log_erro_seguro('cotacao_copiar_lista_email', e, request, {'cotacao_id': pk})
        return resposta_erro_segura('Erro ao gerar texto', 500)


@login_required
@require_GET
def cotacao_copiar_lista_whatsapp(request, pk):
    """Gera texto formatado para WhatsApp."""
    try:
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
        linhas.extend(["", "📅 Aguardo cotação com preços e prazo.", "Obrigado!"])
        return JsonResponse({'success': True, 'texto': '\n'.join(linhas)})
    except Exception as e:
        log_erro_seguro('cotacao_copiar_lista_whatsapp', e, request, {'cotacao_id': pk})
        return resposta_erro_segura('Erro ao gerar texto', 500)


# =============================================================================
# MÓDULO: COMPRAS - PEDIDOS DE COMPRA
# =============================================================================

@login_required
def pedido_compra_manager(request):
    """Manager unificado de pedidos de compra"""
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')

    pedidos = PedidoCompra.objects.select_related('fornecedor').order_by('-data_pedido')
    if search:
        pedidos = pedidos.filter(
            Q(numero__icontains=search) |
            Q(fornecedor__nome_razao_social__icontains=search)
        )
    if status:
        pedidos = pedidos.filter(status=status)

    paginator = Paginator(pedidos, 25)
    page_number = request.GET.get('page')
    pedidos_page = paginator.get_page(page_number)

    total_pedidos = PedidoCompra.objects.count()
    em_aberto = PedidoCompra.objects.filter(status__in=['pendente', 'aprovado']).count()
    recebidos = PedidoCompra.objects.filter(status__in=['recebido', 'atendido']).count()
    cancelados = PedidoCompra.objects.filter(status='cancelado').count()

    fornecedores = Fornecedor.objects.filter(ativo=True).order_by('nome_razao_social')
    condicoes = CondicaoPagamento.objects.filter(ativo=True).order_by('descricao')
    formas = FormaPagamento.objects.filter(ativo=True).order_by('descricao')
    pedidos_abertos = PedidoCompra.objects.filter(status__in=['pendente', 'aprovado']).order_by('-data_pedido')
    cotacoes_concluidas = CotacaoMae.objects.filter(
        status__in=['CONCLUIDA', 'em_analise']
    ).order_by('-data_solicitacao')

    context = {
        'pedidos': pedidos_page,
        'total_pedidos': total_pedidos,
        'em_aberto': em_aberto,
        'recebidos': recebidos,
        'cancelados': cancelados,
        'fornecedores': fornecedores,
        'condicoes_pagamento': condicoes,
        'formas_pagamento': formas,
        'pedidos_abertos': pedidos_abertos,
        'cotacoes_concluidas': cotacoes_concluidas,
        'search': search,
        'status': status,
    }
    return render(request, 'compras/pedido_compra_manager.html', context)


@login_required
@require_POST
def pedido_salvar_api(request):
    """API unificada para salvar pedido de compra"""
    try:
        data = json.loads(request.body)
        pk = data.get('id')

        if pk:
            pedido = get_object_or_404(PedidoCompra, pk=pk)
        else:
            pedido = PedidoCompra()

        pedido.fornecedor_id = data.get('fornecedor_id')
        pedido.data_prevista_entrega = data.get('data_previsao_entrega') or None
        pedido.condicao_pagamento = data.get('condicao_pagamento', '')
        pedido.forma_pagamento = data.get('forma_pagamento', '')
        pedido.cotacao_mae_id = data.get('cotacao_id') or None
        pedido.observacoes = data.get('observacoes', '')
        pedido.status = data.get('status', 'pendente')

        if not pk:
            pedido.solicitante = request.user

        pedido.save()

        itens_data = data.get('itens', [])
        if itens_data:
            pedido.itens.all().delete()
            for item_data in itens_data:
                ItemPedidoCompra.objects.create(
                    pedido=pedido,
                    produto_id=item_data.get('produto_id') or None,
                    descricao=item_data.get('produto', '')[:255],
                    quantidade=Decimal(str(item_data.get('quantidade', 1))),
                    preco_unitario=Decimal(str(item_data.get('valor_unitario', 0)))
                )

        pedido.calcular_total()

        return JsonResponse({
            'success': True,
            'id': pedido.pk,
            'numero': pedido.numero,
            'message': 'Pedido salvo com sucesso!'
        })
    except Exception as e:
        log_erro_seguro('pedido_salvar_api', e, request)
        return resposta_erro_segura(f'Erro ao salvar pedido: {str(e)}', 400)


@login_required
@require_GET
def pedido_dados_api(request, pk):
    """API para buscar dados completos do pedido"""
    try:
        pedido = get_object_or_404(PedidoCompra, pk=pk)

        itens = []
        for item in pedido.itens.select_related('produto').all():
            unidade = 'UN'
            if item.produto and hasattr(item.produto, 'unidade_medida'):
                unidade = item.produto.unidade_medida or 'UN'
            itens.append({
                'id': item.id,
                'produto': item.descricao,
                'quantidade': float(item.quantidade),
                'unidade': unidade,
                'valor_unitario': float(item.preco_unitario),
                'valor_total': float(item.preco_total),
            })

        return JsonResponse({
            'success': True,
            'id': pedido.id,
            'numero': pedido.numero,
            'fornecedor_id': pedido.fornecedor_id,
            'data_previsao_entrega': pedido.data_prevista_entrega.isoformat() if pedido.data_prevista_entrega else None,
            'condicao_pagamento': pedido.condicao_pagamento,
            'forma_pagamento': pedido.forma_pagamento,
            'cotacao_id': pedido.cotacao_mae_id,
            'observacoes': pedido.observacoes or '',
            'status': pedido.status,
            'itens': itens,
            'valor_total': float(pedido.valor_total) if pedido.valor_total else 0,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@require_GET
def pedido_dados_simples_api(request, pk):
    """API para dados simplificados do pedido"""
    try:
        pedido = get_object_or_404(PedidoCompra, pk=pk)
        return JsonResponse({
            'success': True,
            'fornecedor_id': pedido.fornecedor_id,
            'condicao_pagamento': pedido.condicao_pagamento,
            'forma_pagamento': pedido.forma_pagamento,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@require_POST
def pedido_cancelar_api(request, pk):
    """API para cancelar pedido"""
    try:
        pedido = get_object_or_404(PedidoCompra, pk=pk)
        pedido.status = 'cancelado'
        pedido.save()
        return JsonResponse({'success': True, 'message': 'Pedido cancelado com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@require_GET
def pedido_dados_recebimento_api(request, pk):
    """API para dados de recebimento do pedido"""
    try:
        pedido = get_object_or_404(PedidoCompra, pk=pk)
        itens = []
        for item in pedido.itens.all():
            qtd_recebida = getattr(item, 'quantidade_recebida', 0) or 0
            unidade = 'UN'
            if item.produto and hasattr(item.produto, 'unidade_medida'):
                unidade = item.produto.unidade_medida or 'UN'
            itens.append({
                'id': item.id,
                'produto': item.descricao,
                'quantidade': float(item.quantidade),
                'quantidade_recebida': float(qtd_recebida),
                'unidade': unidade,
            })
        return JsonResponse({
            'success': True,
            'numero': pedido.numero,
            'fornecedor': pedido.fornecedor.nome_razao_social,
            'itens': itens,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@require_POST
def pedido_receber_api(request, pk):
    """API para dar entrada no pedido (recebimento)"""
    try:
        pedido = get_object_or_404(PedidoCompra, pk=pk)
        data = json.loads(request.body)
        itens_recebidos = data.get('itens', [])

        with transaction.atomic():
            total_recebido = 0
            total_pedido = pedido.itens.count()

            for item_data in itens_recebidos:
                item = get_object_or_404(ItemPedidoCompra, pk=item_data['item_id'], pedido=pedido)
                qtd_receber = Decimal(str(item_data.get('quantidade', 0)))

                if qtd_receber > 0:
                    qtd_atual = getattr(item, 'quantidade_recebida', 0) or 0
                    item.quantidade_recebida = qtd_atual + qtd_receber
                    item.save()
                    total_recebido += 1

            if total_recebido == 0:
                pedido.status = 'pendente'
            elif total_recebido < total_pedido:
                pedido.status = 'parcial'
            else:
                pedido.status = 'recebido'
            pedido.save()

        return JsonResponse({
            'success': True,
            'message': 'Entrada realizada com sucesso!',
            'novo_status': pedido.status,
        })
    except Exception as e:
        log_erro_seguro('pedido_receber_api', e, request)
        return resposta_erro_segura(f'Erro no recebimento: {str(e)}', 400)


@login_required
def pedido_compra_gerar_nfe(request, pk):
    """Geração de NF de entrada a partir do pedido"""
    pedido = get_object_or_404(PedidoCompra, pk=pk)
    return render(request, 'compras/gerar_nfe.html', {'pedido': pedido})


# =============================================================================
# MÓDULO: COMPRAS - NOTAS FISCAIS DE ENTRADA
# =============================================================================

@login_required
def nota_fiscal_entrada_manager(request):
    """Manager unificado de notas fiscais de entrada"""
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')

    notas = NotaFiscalEntrada.objects.select_related('fornecedor').order_by('-data_entrada')
    if search:
        notas = notas.filter(
            Q(numero_nf__icontains=search) |
            Q(fornecedor__nome_razao_social__icontains=search)
        )
    if status:
        notas = notas.filter(status=status)

    paginator = Paginator(notas, 25)
    page_number = request.GET.get('page')
    notas_page = paginator.get_page(page_number)

    hoje = timezone.now().date()
    semana_inicio = hoje - timedelta(days=hoje.weekday())

    total_notas = NotaFiscalEntrada.objects.count()
    entradas_hoje = NotaFiscalEntrada.objects.filter(data_entrada=hoje).count()
    entradas_semana = NotaFiscalEntrada.objects.filter(data_entrada__gte=semana_inicio).count()
    valor_mes = NotaFiscalEntrada.objects.filter(
        data_entrada__month=hoje.month,
        data_entrada__year=hoje.year
    ).aggregate(total=Sum('valor_total'))['total'] or 0

    fornecedores = Fornecedor.objects.filter(ativo=True).order_by('nome_razao_social')
    condicoes = CondicaoPagamento.objects.filter(ativo=True).order_by('descricao')
    formas = FormaPagamento.objects.filter(ativo=True).order_by('descricao')
    pedidos_abertos = PedidoCompra.objects.filter(status__in=['ABERTO', 'PARCIAL']).order_by('-data_pedido')

    context = {
        'notas': notas_page,
        'total_notas': total_notas,
        'entradas_hoje': entradas_hoje,
        'entradas_semana': entradas_semana,
        'valor_mes': valor_mes,
        'fornecedores': fornecedores,
        'condicoes_pagamento': condicoes,
        'formas_pagamento': formas,
        'pedidos_abertos': pedidos_abertos,
        'search': search,
        'status': status,
    }
    return render(request, 'compras/nota_fiscal_entrada_manager.html', context)


@login_required
@require_POST
def nota_fiscal_salvar_api(request):
    """API unificada para salvar nota fiscal de entrada"""
    try:
        data = json.loads(request.body)
        pk = data.get('id')

        if pk:
            nota = get_object_or_404(NotaFiscalEntrada, pk=pk)
        else:
            nota = NotaFiscalEntrada()

        nota.numero_nf = data.get('numero', '')
        nota.serie = data.get('serie', '')
        nota.chave_acesso = data.get('chave_acesso', '')
        nota.modelo = data.get('modelo', '55')
        nota.fornecedor_id = data.get('fornecedor_id')
        nota.pedido_compra_id = data.get('pedido_id') or None
        nota.data_emissao = data.get('data_emissao')
        nota.data_entrada = data.get('data_entrada') or timezone.now().date()
        nota.condicao_pagamento_id = data.get('condicao_pagamento_id') or None
        nota.forma_pagamento_id = data.get('forma_pagamento_id') or None
        nota.observacoes = data.get('observacoes', '')
        nota.status = data.get('status', 'PENDENTE')

        if not pk:
            nota.usuario_cadastro = request.user

        nota.save()

        itens_data = data.get('itens', [])
        if itens_data:
            nota.itens.all().delete()
            for item_data in itens_data:
                qtd = Decimal(str(item_data.get('quantidade', 1)))
                val_unit = Decimal(str(item_data.get('valor_unitario', 0)))
                val_total = Decimal(str(item_data.get('valor_total', 0))) if item_data.get('valor_total') else qtd * val_unit
                ItemNotaFiscalEntrada.objects.create(
                    nota_fiscal=nota,
                    produto_id=item_data.get('produto_id') or None,
                    descricao=item_data.get('produto', '')[:255],
                    quantidade=qtd,
                    unidade_medida=item_data.get('unidade', 'UN'),
                    valor_unitario=val_unit,
                    valor_total=val_total,
                )

        nota.calcular_totais()

        if nota.status == 'CONFIRMADA' and nota.pedido_compra:
            nota.pedido_compra.status = 'RECEBIDO'
            nota.pedido_compra.save()

        return JsonResponse({
            'success': True,
            'id': nota.pk,
            'numero': nota.numero_nf,
            'message': 'Nota fiscal salva com sucesso!'
        })
    except Exception as e:
        log_erro_seguro('nota_fiscal_salvar_api', e, request)
        return resposta_erro_segura(f'Erro ao salvar NF: {str(e)}', 400)


@login_required
@require_GET
def nota_fiscal_dados_api(request, pk):
    """API para buscar dados completos da nota fiscal"""
    try:
        nota = get_object_or_404(NotaFiscalEntrada, pk=pk)
        itens = []
        for item in nota.itens.select_related('produto').all():
            itens.append({
                'id': item.id,
                'produto': item.descricao,
                'quantidade': float(item.quantidade),
                'unidade': item.unidade_medida,
                'valor_unitario': float(item.valor_unitario),
                'valor_total': float(item.valor_total),
            })

        return JsonResponse({
            'success': True,
            'id': nota.id,
            'numero': nota.numero_nf,
            'serie': nota.serie,
            'chave_acesso': nota.chave_acesso or '',
            'modelo': nota.modelo,
            'fornecedor_id': nota.fornecedor_id,
            'pedido_id': nota.pedido_compra_id,
            'data_emissao': nota.data_emissao.isoformat() if nota.data_emissao else None,
            'data_entrada': nota.data_entrada.isoformat() if nota.data_entrada else None,
            'condicao_pagamento_id': nota.condicao_pagamento_id,
            'forma_pagamento_id': nota.forma_pagamento_id,
            'observacoes': nota.observacoes or '',
            'status': nota.status,
            'itens': itens,
            'valor_produtos': float(nota.valor_produtos) if nota.valor_produtos else 0,
            'valor_frete': float(nota.valor_frete) if nota.valor_frete else 0,
            'valor_impostos': float(nota.valor_impostos) if nota.valor_impostos else 0,
            'valor_total': float(nota.valor_total) if nota.valor_total else 0,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@require_POST
def nota_fiscal_excluir_api(request, pk):
    """API para excluir nota fiscal"""
    try:
        nota = get_object_or_404(NotaFiscalEntrada, pk=pk)
        if nota.status == 'CONFIRMADA':
            return JsonResponse({
                'success': False,
                'message': 'Nota fiscal confirmada não pode ser excluída. Cancele primeiro.'
            }, status=400)
        nota.delete()
        return JsonResponse({'success': True, 'message': 'Nota fiscal excluída com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@require_POST
def nota_fiscal_confirmar_api(request, pk):
    """API para confirmar nota fiscal"""
    try:
        nota = get_object_or_404(NotaFiscalEntrada, pk=pk)
        if nota.status == 'CONFIRMADA':
            return JsonResponse({'success': False, 'message': 'Nota fiscal já está confirmada'}, status=400)
        if nota.status == 'CANCELADA':
            return JsonResponse({'success': False, 'message': 'Nota fiscal está cancelada'}, status=400)

        with transaction.atomic():
            nota.status = 'CONFIRMADA'
            nota.data_confirmacao = timezone.now()
            nota.usuario_confirmacao = request.user
            nota.save()
            if nota.pedido_compra:
                nota.pedido_compra.status = 'RECEBIDO'
                nota.pedido_compra.save()

        return JsonResponse({'success': True, 'message': 'Nota fiscal confirmada com sucesso!'})
    except Exception as e:
        log_erro_seguro('nota_fiscal_confirmar_api', e, request)
        return resposta_erro_segura(f'Erro ao confirmar NF: {str(e)}', 400)


@login_required
@require_POST
def nota_fiscal_cancelar_api(request, pk):
    """API para cancelar nota fiscal"""
    try:
        nota = get_object_or_404(NotaFiscalEntrada, pk=pk)
        if nota.status == 'CANCELADA':
            return JsonResponse({'success': False, 'message': 'Nota fiscal já está cancelada'}, status=400)

        with transaction.atomic():
            nota.status = 'CANCELADA'
            nota.data_cancelamento = timezone.now()
            nota.usuario_cancelamento = request.user
            nota.save()

        return JsonResponse({'success': True, 'message': 'Nota fiscal cancelada com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


# =============================================================================
# MÓDULO: COMPRAS - RELATÓRIO
# =============================================================================

@login_required
def relatorio_compras(request):
    """Relatório de compras"""
    hoje = timezone.now().date()
    trinta_dias_atras = hoje - timedelta(days=30)

    data_inicio = request.GET.get('data_inicio', trinta_dias_atras.isoformat())
    data_fim = request.GET.get('data_fim', hoje.isoformat())
    fornecedor_id = request.GET.get('fornecedor', '')
    categoria_id = request.GET.get('categoria', '')

    fornecedores = Fornecedor.objects.filter(ativo=True).order_by('nome_razao_social')

    context = {
        'fornecedores': fornecedores,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'fornecedor_selecionado': fornecedor_id,
        'categoria_selecionada': categoria_id,
    }
    return render(request, 'compras/relatorio_compras.html', context)


@login_required
@require_GET
def relatorio_compras_dados_api(request):
    """API para dados do relatório de compras"""
    try:
        data_inicio = request.GET.get('data_inicio')
        data_fim = request.GET.get('data_fim')
        fornecedor_id = request.GET.get('fornecedor', '')

        notas = NotaFiscalEntrada.objects.filter(status='CONFIRMADA')
        if data_inicio:
            notas = notas.filter(data_entrada__gte=data_inicio)
        if data_fim:
            notas = notas.filter(data_entrada__lte=data_fim)
        if fornecedor_id:
            notas = notas.filter(fornecedor_id=fornecedor_id)

        totais = notas.aggregate(
            total_notas=Count('id'),
            total_valor=Sum('valor_total'),
            total_produtos=Sum('valor_produtos'),
            total_impostos=Sum('valor_impostos')
        )

        compras_por_mes = notas.extra(
            select={'mes': "DATE_TRUNC('month', data_entrada)"}
        ).values('mes').annotate(
            total=Sum('valor_total'),
            quantidade=Count('id')
        ).order_by('mes')

        top_fornecedores = notas.values(
            'fornecedor__nome_razao_social'
        ).annotate(
            total_compras=Sum('valor_total'),
            quantidade_notas=Count('id')
        ).order_by('-total_compras')[:10]

        return JsonResponse({
            'success': True,
            'totais': {
                'notas': totais['total_notas'] or 0,
                'valor_total': float(totais['total_valor'] or 0),
                'produtos': float(totais['total_produtos'] or 0),
                'impostos': float(totais['total_impostos'] or 0),
            },
            'compras_por_mes': list(compras_por_mes),
            'top_fornecedores': list(top_fornecedores),
        })
    except Exception as e:
        log_erro_seguro('relatorio_compras_dados_api', e, request)
        return resposta_erro_segura('Erro ao gerar relatório', 400)


@login_required
@require_GET
def relatorio_compras_exportar_api(request):
    """API para exportar relatório de compras (CSV)"""
    try:
        formato = request.GET.get('formato', 'csv')
        data_inicio = request.GET.get('data_inicio')
        data_fim = request.GET.get('data_fim')

        notas = NotaFiscalEntrada.objects.filter(status='CONFIRMADA')
        if data_inicio:
            notas = notas.filter(data_entrada__gte=data_inicio)
        if data_fim:
            notas = notas.filter(data_entrada__lte=data_fim)

        if formato == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="relatorio_compras.csv"'
            writer = csv.writer(response)
            writer.writerow(['Data Entrada', 'Número NF', 'Fornecedor', 'Valor Produtos', 'Valor Impostos', 'Valor Total'])
            for nota in notas.select_related('fornecedor'):
                writer.writerow([
                    nota.data_entrada.strftime('%d/%m/%Y'),
                    nota.numero_nf,
                    nota.fornecedor.nome_razao_social,
                    float(nota.valor_produtos or 0),
                    float(nota.valor_impostos or 0),
                    float(nota.valor_total or 0),
                ])
            return response

        return JsonResponse({'success': False, 'message': 'Formato não suportado'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


# =============================================================================
# CONFIRMAÇÕES DE DELETE (compatibilidade com templates antigos)
# =============================================================================

@login_required
def cotacao_confirm_delete(request, pk):
    """Confirmação de exclusão de cotação"""
    cotacao = get_object_or_404(CotacaoMae, pk=pk)
    if request.method == 'POST':
        cotacao.delete()
        messages.success(request, 'Cotação excluída com sucesso!')
        return redirect('ERP_ServicesBI:cotacao_manager')
    context = {
        'objeto': cotacao,
        'titulo': 'Excluir Cotação',
        'nome_objeto': f'Cotação {cotacao.numero}',
        'url_cancelar': 'ERP_ServicesBI:cotacao_manager',
        'url_confirmar': request.path,
    }
    return render(request, 'compras/cotacao_confirm_delete.html', context)


@login_required
def pedido_compra_confirm_delete(request, pk):
    """Confirmação de exclusão de pedido"""
    pedido = get_object_or_404(PedidoCompra, pk=pk)
    if request.method == 'POST':
        pedido.delete()
        messages.success(request, 'Pedido excluído com sucesso!')
        return redirect('ERP_ServicesBI:pedido_compra_manager')
    context = {
        'objeto': pedido,
        'titulo': 'Excluir Pedido de Compra',
        'nome_objeto': f'Pedido {pedido.numero}',
        'url_cancelar': 'ERP_ServicesBI:pedido_compra_manager',
        'url_confirmar': request.path,
    }
    return render(request, 'compras/pedido_compra_confirm_delete.html', context)


@login_required
def nota_fiscal_entrada_confirm_delete(request, pk):
    """Confirmação de exclusão de nota fiscal"""
    nota = get_object_or_404(NotaFiscalEntrada, pk=pk)
    if request.method == 'POST':
        nota.delete()
        messages.success(request, 'Nota fiscal excluída com sucesso!')
        return redirect('ERP_ServicesBI:nota_fiscal_entrada_manager')
    context = {
        'objeto': nota,
        'titulo': 'Excluir Nota Fiscal de Entrada',
        'nome_objeto': f'NF-e {nota.numero_nf}',
        'url_cancelar': 'ERP_ServicesBI:nota_fiscal_entrada_manager',
        'url_confirmar': request.path,
    }
    return render(request, 'compras/nota_fiscal_entrada_confirm_delete.html', context)


# =============================================================================
# MÓDULO: VENDAS - ORÇAMENTOS
# =============================================================================

@login_required
def orcamento_list(request):
    """Listagem de orçamentos"""
    orcamentos = Orcamento.objects.select_related('cliente', 'vendedor').all().order_by('-data_orcamento')
    return render(request, 'vendas/orcamento_list.html', {'orcamentos': orcamentos})


@login_required
def orcamento_add(request):
    """Cadastro de novo orçamento"""
    clientes = Cliente.objects.filter(ativo=True).order_by('nome_razao_social')
    vendedores = Vendedor.objects.filter(ativo=True).order_by('nome')
    try:
        condicoes_pagamento = CondicaoPagamento.objects.filter(ativo=True).order_by('descricao')
    except Exception:
        condicoes_pagamento = CondicaoPagamento.objects.all().order_by('descricao')
    produtos = Produto.objects.filter(ativo=True).order_by('descricao')

    status_choices = getattr(Orcamento, 'STATUS_CHOICES', [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
        ('convertido', 'Convertido em Pedido'),
    ])

    if request.method == 'POST':
        form = OrcamentoForm(request.POST)
        if form.is_valid():
            orcamento = form.save()
            messages.success(request, f'Orçamento {orcamento.numero} criado com sucesso!')
            return redirect('ERP_ServicesBI:orcamento_edit', pk=orcamento.pk)
    else:
        form = OrcamentoForm(initial={
            'data_orcamento': date.today(),
            'data_validade': date.today() + timedelta(days=7),
            'status': 'pendente'
        })

    context = {
        'form': form,
        'titulo': 'Novo Orçamento',
        'orcamento': None,
        'clientes': clientes,
        'vendedores': vendedores,
        'condicoes_pagamento': condicoes_pagamento,
        'produtos': produtos,
        'status_choices': status_choices,
        'itens': [],
    }
    return render(request, 'vendas/orcamento_form.html', context)


@login_required
def orcamento_edit(request, pk):
    """Edição de orçamento"""
    orcamento = get_object_or_404(Orcamento, pk=pk)
    clientes = Cliente.objects.filter(ativo=True).order_by('nome_razao_social')
    vendedores = Vendedor.objects.filter(ativo=True).order_by('nome')
    try:
        condicoes_pagamento = CondicaoPagamento.objects.filter(ativo=True).order_by('descricao')
    except Exception:
        condicoes_pagamento = CondicaoPagamento.objects.all().order_by('descricao')
    produtos = Produto.objects.filter(ativo=True).order_by('descricao')

    status_choices = getattr(Orcamento, 'STATUS_CHOICES', [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
        ('convertido', 'Convertido em Pedido'),
    ])
    itens = ItemOrcamento.objects.filter(orcamento=orcamento).select_related('produto')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_header':
            form = OrcamentoForm(request.POST, instance=orcamento)
            if form.is_valid():
                form.save()
                messages.success(request, 'Orçamento atualizado com sucesso!')
                return redirect('ERP_ServicesBI:orcamento_edit', pk=orcamento.pk)

        elif action == 'add_item':
            produto_id = request.POST.get('produto')
            quantidade = request.POST.get('quantidade')
            preco_unitario_str = request.POST.get('preco_unitario', '0').replace('.', '').replace(',', '.')
            preco_unitario = Decimal(preco_unitario_str)
            produto = get_object_or_404(Produto, pk=produto_id)
            ItemOrcamento.objects.create(
                orcamento=orcamento,
                produto=produto,
                quantidade=quantidade,
                preco_unitario=preco_unitario
            )
            orcamento.calcular_total()
            messages.success(request, 'Item adicionado com sucesso!')
            return redirect('ERP_ServicesBI:orcamento_edit', pk=orcamento.pk)

        elif action == 'update_item':
            item_id = request.POST.get('item_id')
            item = get_object_or_404(ItemOrcamento, pk=item_id, orcamento=orcamento)
            item.quantidade = request.POST.get('quantidade')
            preco_str = request.POST.get('preco_unitario', '0').replace('.', '').replace(',', '.')
            item.preco_unitario = Decimal(preco_str)
            item.save()
            orcamento.calcular_total()
            messages.success(request, 'Item atualizado com sucesso!')
            return redirect('ERP_ServicesBI:orcamento_edit', pk=orcamento.pk)

        elif action == 'remove_item':
            item_id = request.POST.get('item_id')
            item = get_object_or_404(ItemOrcamento, pk=item_id, orcamento=orcamento)
            item.delete()
            orcamento.calcular_total()
            messages.success(request, 'Item removido com sucesso!')
            return redirect('ERP_ServicesBI:orcamento_edit', pk=orcamento.pk)
    else:
        form = OrcamentoForm(instance=orcamento)

    context = {
        'form': form,
        'titulo': 'Editar Orçamento',
        'orcamento': orcamento,
        'clientes': clientes,
        'vendedores': vendedores,
        'condicoes_pagamento': condicoes_pagamento,
        'produtos': produtos,
        'status_choices': status_choices,
        'itens': itens,
    }
    return render(request, 'vendas/orcamento_form.html', context)


@login_required
def orcamento_delete(request, pk):
    """Exclusão de orçamento"""
    orcamento = get_object_or_404(Orcamento, pk=pk)
    if request.method == 'POST':
        numero = orcamento.numero
        orcamento.delete()
        messages.success(request, f'Orçamento {numero} excluído com sucesso!')
        return redirect('ERP_ServicesBI:orcamento_list')
    return render(request, 'vendas/orcamento_confirm_delete.html', {'objeto': orcamento, 'titulo': 'Excluir Orçamento'})


@login_required
def orcamento_item_add(request, orcamento_pk):
    """Adicionar item ao orçamento (form separado)"""
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
    produtos = Produto.objects.filter(ativo=True).order_by('descricao')
    context = {'form': form, 'orcamento': orcamento, 'titulo': 'Novo Item', 'produtos': produtos}
    return render(request, 'vendas/orcamento_item_form.html', context)


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
    """Geração de pedido a partir do orçamento"""
    orcamento = get_object_or_404(Orcamento, pk=pk)
    return render(request, 'vendas/gerar_pedido.html', {'orcamento': orcamento})


# =============================================================================
# MÓDULO: VENDAS - PEDIDOS DE VENDA
# =============================================================================

@login_required
def pedido_venda_list(request):
    """Listagem de pedidos de venda"""
    pedidos = PedidoVenda.objects.select_related('cliente', 'vendedor').all().order_by('-data_pedido')
    paginator = Paginator(pedidos, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'vendas/pedido_venda_list.html', {'page_obj': page_obj, 'total': paginator.count})


@login_required
def pedido_venda_add(request):
    """Cadastro de novo pedido de venda"""
    if request.method == 'POST':
        action = request.POST.get('action', 'update_header')
        if action == 'update_header':
            form = PedidoVendaForm(request.POST)
            if form.is_valid():
                pedido = form.save()
                messages.success(request, f'Pedido {pedido.numero} criado com sucesso!')
                return redirect('ERP_ServicesBI:pedido_venda_edit', pk=pedido.pk)
            else:
                messages.error(request, 'Erro ao criar pedido. Verifique os dados.')
        else:
            form = PedidoVendaForm()
    else:
        form = PedidoVendaForm()

    context = {
        'form': form,
        'titulo': 'Novo Pedido de Venda',
        'pedido': None,
        'itens': [],
        'clientes': Cliente.objects.filter(ativo=True).order_by('nome_razao_social'),
        'status_choices': PedidoVenda.STATUS_CHOICES,
        'produtos': Produto.objects.filter(ativo=True).order_by('descricao'),
    }
    return render(request, 'vendas/pedido_venda_form.html', context)


@login_required
def pedido_venda_edit(request, pk):
    """Edição de pedido de venda"""
    pedido = get_object_or_404(PedidoVenda, pk=pk)
    itens = pedido.itens.select_related('produto').all()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_header':
            form = PedidoVendaForm(request.POST, instance=pedido)
            if form.is_valid():
                form.save()
                messages.success(request, 'Cabeçalho atualizado com sucesso!')
                return redirect('ERP_ServicesBI:pedido_venda_edit', pk=pk)

        elif action == 'add_item':
            produto_id = request.POST.get('produto')
            quantidade = request.POST.get('quantidade')
            preco_unitario = request.POST.get('preco_unitario', '0')
            desconto = request.POST.get('desconto', '0')
            try:
                preco_unitario = float(preco_unitario.replace('.', '').replace(',', '.'))
                desconto = float(desconto.replace('.', '').replace(',', '.'))
                quantidade = float(quantidade.replace(',', '.'))
                produto = Produto.objects.get(pk=produto_id)
                ItemPedidoVenda.objects.create(
                    pedido=pedido,
                    produto=produto,
                    quantidade=quantidade,
                    preco_unitario=preco_unitario,
                    desconto=desconto
                )
                pedido.calcular_total()
                messages.success(request, 'Item adicionado com sucesso!')
            except Produto.DoesNotExist:
                messages.error(request, 'Produto não encontrado!')
            except Exception as e:
                messages.error(request, f'Erro ao adicionar item: {str(e)}')
            return redirect('ERP_ServicesBI:pedido_venda_edit', pk=pk)

        elif action == 'remove_item':
            item_id = request.POST.get('item_id')
            try:
                item = ItemPedidoVenda.objects.get(pk=item_id, pedido=pedido)
                item.delete()
                pedido.calcular_total()
                messages.success(request, 'Item removido com sucesso!')
            except ItemPedidoVenda.DoesNotExist:
                messages.error(request, 'Item não encontrado!')
            return redirect('ERP_ServicesBI:pedido_venda_edit', pk=pk)

        elif action == 'update_item':
            item_id = request.POST.get('item_id')
            try:
                item = ItemPedidoVenda.objects.get(pk=item_id, pedido=pedido)
                preco = request.POST.get('preco_unitario', '0').replace('.', '').replace(',', '.')
                desc = request.POST.get('desconto', '0').replace('.', '').replace(',', '.')
                qtd = request.POST.get('quantidade', '1').replace(',', '.')
                item.quantidade = float(qtd)
                item.preco_unitario = float(preco)
                item.desconto = float(desc)
                item.save()
                pedido.calcular_total()
                messages.success(request, 'Item atualizado com sucesso!')
            except Exception as e:
                messages.error(request, f'Erro ao atualizar item: {str(e)}')
            return redirect('ERP_ServicesBI:pedido_venda_edit', pk=pk)

        return redirect('ERP_ServicesBI:pedido_venda_edit', pk=pk)
    else:
        form = PedidoVendaForm(instance=pedido)

    context = {
        'form': form,
        'titulo': 'Editar Pedido de Venda',
        'pedido': pedido,
        'itens': itens,
        'clientes': Cliente.objects.filter(ativo=True).order_by('nome_razao_social'),
        'status_choices': PedidoVenda.STATUS_CHOICES,
        'produtos': Produto.objects.filter(ativo=True).order_by('descricao'),
    }
    return render(request, 'vendas/pedido_venda_form.html', context)


@login_required
def pedido_venda_delete(request, pk):
    """Exclusão de pedido de venda"""
    pedido = get_object_or_404(PedidoVenda, pk=pk)
    if request.method == 'POST':
        numero = pedido.numero
        pedido.delete()
        messages.success(request, f'Pedido {numero} excluído com sucesso!')
        return redirect('ERP_ServicesBI:pedido_venda_list')
    return render(request, 'vendas/pedido_venda_confirm_delete.html', {'objeto': pedido, 'titulo': 'Excluir Pedido de Venda'})


@login_required
def pedido_venda_item_add(request, pedido_pk):
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
            return redirect('ERP_ServicesBI:pedido_venda_edit', pk=pedido.pk)
    else:
        form = ItemPedidoVendaForm()
    context = {
        'form': form,
        'pedido': pedido,
        'titulo': 'Novo Item',
        'produtos': Produto.objects.filter(ativo=True).order_by('descricao'),
    }
    return render(request, 'vendas/pedido_venda_item_form.html', context)


@login_required
@require_POST
def pedido_venda_item_delete(request, pk):
    """Excluir item do pedido de venda"""
    item = get_object_or_404(ItemPedidoVenda, pk=pk)
    pedido = item.pedido
    item.delete()
    pedido.calcular_total()
    messages.success(request, 'Item removido com sucesso!')
    return redirect('ERP_ServicesBI:pedido_venda_edit', pk=pedido.pk)


@login_required
def pedido_venda_gerar_nfe(request, pk):
    """Geração de NF de saída a partir do pedido"""
    pedido = get_object_or_404(PedidoVenda, pk=pk)
    return render(request, 'vendas/gerar_nfe.html', {'pedido': pedido})


# =============================================================================
# MÓDULO: VENDAS - NOTAS FISCAIS DE SAÍDA
# =============================================================================

@login_required
def nota_fiscal_saida_list(request):
    """Listagem de notas fiscais de saída"""
    notas = NotaFiscalSaida.objects.select_related('cliente').all().order_by('-data_emissao')
    paginator = Paginator(notas, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'vendas/nota_fiscal_saida_list.html', {'page_obj': page_obj, 'total': paginator.count})


@login_required
def nota_fiscal_saida_add(request):
    """Cadastro de nova NF de saída"""
    if request.method == 'POST':
        form = NotaFiscalSaidaForm(request.POST)
        if form.is_valid():
            nota = form.save()
            messages.success(request, f'NF {nota.numero_nf} criada com sucesso!')
            return redirect('ERP_ServicesBI:nota_fiscal_saida_list')
    else:
        form = NotaFiscalSaidaForm()
    return render(request, 'vendas/nota_fiscal_saida_form.html', {'form': form, 'titulo': 'Nova Nota Fiscal de Saída'})


@login_required
def nota_fiscal_saida_edit(request, pk):
    """Edição de NF de saída"""
    nota = get_object_or_404(NotaFiscalSaida, pk=pk)
    if request.method == 'POST':
        form = NotaFiscalSaidaForm(request.POST, instance=nota)
        if form.is_valid():
            form.save()
            messages.success(request, 'Nota fiscal atualizada com sucesso!')
            return redirect('ERP_ServicesBI:nota_fiscal_saida_list')
    else:
        form = NotaFiscalSaidaForm(instance=nota)
    return render(request, 'vendas/nota_fiscal_saida_form.html', {'form': form, 'titulo': 'Editar Nota Fiscal de Saída', 'nota': nota})


@login_required
def nota_fiscal_saida_delete(request, pk):
    """Exclusão de NF de saída"""
    nota = get_object_or_404(NotaFiscalSaida, pk=pk)
    if request.method == 'POST':
        numero = nota.numero_nf
        nota.delete()
        messages.success(request, f'NF {numero} excluída com sucesso!')
        return redirect('ERP_ServicesBI:nota_fiscal_saida_list')
    return render(request, 'vendas/nota_fiscal_saida_confirm_delete.html', {'objeto': nota, 'titulo': 'Excluir Nota Fiscal de Saída'})


@login_required
def nota_fiscal_saida_item_add(request, nota_pk):
    """Adicionar item à NF de saída"""
    nota = get_object_or_404(NotaFiscalSaida, pk=nota_pk)
    if request.method == 'POST':
        form = ItemNotaFiscalSaidaForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.nota_fiscal = nota
            item.save()
            nota.calcular_total()
            messages.success(request, 'Item adicionado com sucesso!')
            return redirect('ERP_ServicesBI:nota_fiscal_saida_edit', pk=nota.pk)
    else:
        form = ItemNotaFiscalSaidaForm()
    return render(request, 'vendas/nota_fiscal_saida_item_form.html', {'form': form, 'nota': nota, 'titulo': 'Novo Item'})


@login_required
@require_POST
def nota_fiscal_saida_item_delete(request, pk):
    """Excluir item da NF de saída"""
    item = get_object_or_404(ItemNotaFiscalSaida, pk=pk)
    nota = item.nota_fiscal
    item.delete()
    nota.calcular_total()
    messages.success(request, 'Item removido com sucesso!')
    return redirect('ERP_ServicesBI:nota_fiscal_saida_edit', pk=nota.pk)


@login_required
def relatorio_vendas(request):
    """Relatório de vendas"""
    return render(request, 'vendas/relatorio_vendas.html', {})


# =============================================================================
# MÓDULO: FINANCEIRO - CONTAS A RECEBER
# =============================================================================

@login_required
def conta_receber_list(request):
    """Listagem de contas a receber"""
    contas = ContaReceber.objects.select_related('cliente').all().order_by('data_vencimento')
    paginator = Paginator(contas, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'financeiro/conta_receber_list.html', {'page_obj': page_obj, 'total': paginator.count})


@login_required
def conta_receber_add(request):
    """Cadastro de conta a receber"""
    if request.method == 'POST':
        form = ContaReceberForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conta a receber criada com sucesso!')
            return redirect('ERP_ServicesBI:conta_receber_list')
    else:
        form = ContaReceberForm()
    context = {
        'form': form,
        'titulo': 'Nova Conta a Receber',
        'clientes': Cliente.objects.filter(ativo=True),
        'categorias': CategoriaFinanceira.objects.filter(tipo='receita'),
        'centros': CentroCusto.objects.all(),
    }
    return render(request, 'financeiro/conta_receber_form.html', context)


@login_required
def conta_receber_edit(request, pk):
    """Edição de conta a receber"""
    conta = get_object_or_404(ContaReceber, pk=pk)
    if request.method == 'POST':
        form = ContaReceberForm(request.POST, instance=conta)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conta atualizada com sucesso!')
            return redirect('ERP_ServicesBI:conta_receber_list')
    else:
        form = ContaReceberForm(instance=conta)
    return render(request, 'financeiro/conta_receber_form.html', {'form': form, 'titulo': 'Editar Conta a Receber', 'conta': conta})


@login_required
def conta_receber_delete(request, pk):
    """Exclusão de conta a receber"""
    conta = get_object_or_404(ContaReceber, pk=pk)
    if request.method == 'POST':
        conta.delete()
        messages.success(request, 'Conta excluída com sucesso!')
        return redirect('ERP_ServicesBI:conta_receber_list')
    return render(request, 'financeiro/conta_receber_confirm_delete.html', {'objeto': conta, 'titulo': 'Excluir Conta a Receber'})


@login_required
def conta_receber_baixar(request, pk):
    """Baixa de conta a receber"""
    conta = get_object_or_404(ContaReceber, pk=pk)
    return render(request, 'financeiro/conta_receber_baixar.html', {'conta': conta})


# =============================================================================
# MÓDULO: FINANCEIRO - CONTAS A PAGAR
# =============================================================================

@login_required
def conta_pagar_list(request):
    """Listagem de contas a pagar"""
    contas = ContaPagar.objects.select_related('fornecedor').all().order_by('data_vencimento')
    paginator = Paginator(contas, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'financeiro/conta_pagar_list.html', {'page_obj': page_obj, 'total': paginator.count})


@login_required
def conta_pagar_add(request):
    """Cadastro de conta a pagar"""
    if request.method == 'POST':
        form = ContaPagarForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conta a pagar criada com sucesso!')
            return redirect('ERP_ServicesBI:conta_pagar_list')
    else:
        form = ContaPagarForm()
    return render(request, 'financeiro/conta_pagar_form.html', {'form': form, 'titulo': 'Nova Conta a Pagar'})


@login_required
def conta_pagar_edit(request, pk):
    """Edição de conta a pagar"""
    conta = get_object_or_404(ContaPagar, pk=pk)
    if request.method == 'POST':
        form = ContaPagarForm(request.POST, instance=conta)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conta atualizada com sucesso!')
            return redirect('ERP_ServicesBI:conta_pagar_list')
    else:
        form = ContaPagarForm(instance=conta)
    return render(request, 'financeiro/conta_pagar_form.html', {'form': form, 'titulo': 'Editar Conta a Pagar', 'conta': conta})


@login_required
def conta_pagar_delete(request, pk):
    """Exclusão de conta a pagar"""
    conta = get_object_or_404(ContaPagar, pk=pk)
    if request.method == 'POST':
        conta.delete()
        messages.success(request, 'Conta excluída com sucesso!')
        return redirect('ERP_ServicesBI:conta_pagar_list')
    return render(request, 'financeiro/conta_pagar_confirm_delete.html', {'objeto': conta, 'titulo': 'Excluir Conta a Pagar'})


@login_required
def conta_pagar_baixar(request, pk):
    """Baixa de conta a pagar"""
    conta = get_object_or_404(ContaPagar, pk=pk)
    return render(request, 'financeiro/conta_pagar_baixar.html', {'conta': conta})


# =============================================================================
# MÓDULO: FINANCEIRO - CATEGORIAS FINANCEIRAS
# =============================================================================

@login_required
def categoria_financeira_list(request):
    """Listagem de categorias financeiras"""
    categorias = CategoriaFinanceira.objects.all().order_by('codigo')
    paginator = Paginator(categorias, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'financeiro/categoria_financeira_list.html', {'page_obj': page_obj, 'total': paginator.count})


@login_required
def categoria_financeira_add(request):
    """Cadastro de categoria financeira"""
    if request.method == 'POST':
        form = CategoriaFinanceiraForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoria criada com sucesso!')
            return redirect('ERP_ServicesBI:categoria_financeira_list')
    else:
        form = CategoriaFinanceiraForm()
    return render(request, 'financeiro/categoria_financeira_form.html', {'form': form, 'titulo': 'Nova Categoria Financeira'})


@login_required
def categoria_financeira_edit(request, pk):
    """Edição de categoria financeira"""
    categoria = get_object_or_404(CategoriaFinanceira, pk=pk)
    if request.method == 'POST':
        form = CategoriaFinanceiraForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoria atualizada com sucesso!')
            return redirect('ERP_ServicesBI:categoria_financeira_list')
    else:
        form = CategoriaFinanceiraForm(instance=categoria)
    return render(request, 'financeiro/categoria_financeira_form.html', {'form': form, 'titulo': 'Editar Categoria Financeira', 'categoria': categoria})


@login_required
def categoria_financeira_delete(request, pk):
    """Exclusão de categoria financeira"""
    categoria = get_object_or_404(CategoriaFinanceira, pk=pk)
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, 'Categoria excluída com sucesso!')
        return redirect('ERP_ServicesBI:categoria_financeira_list')
    return render(request, 'financeiro/categoria_financeira_confirm_delete.html', {'objeto': categoria, 'titulo': 'Excluir Categoria Financeira'})


# =============================================================================
# MÓDULO: FINANCEIRO - CENTROS DE CUSTO
# =============================================================================

@login_required
def centro_custo_list(request):
    categorias = CentroCusto.objects.all().order_by('nome')
    paginator = Paginator(categorias, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'financeiro/centro_custo_list.html', {'page_obj': page_obj, 'total': paginator.count})


@login_required
def centro_custo_add(request):
    if request.method == 'POST':
        form = CentroCustoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Centro de custo criado com sucesso!')
            return redirect('ERP_ServicesBI:centro_custo_list')
    else:
        form = CentroCustoForm()
    return render(request, 'financeiro/centro_custo_form.html', {'form': form, 'titulo': 'Novo Centro de Custo'})


@login_required
def centro_custo_edit(request, pk):
    centro = get_object_or_404(CentroCusto, pk=pk)
    if request.method == 'POST':
        form = CentroCustoForm(request.POST, instance=centro)
        if form.is_valid():
            form.save()
            messages.success(request, 'Centro de custo atualizado com sucesso!')
            return redirect('ERP_ServicesBI:centro_custo_list')
    else:
        form = CentroCustoForm(instance=centro)
    return render(request, 'financeiro/centro_custo_form.html', {'form': form, 'titulo': 'Editar Centro de Custo', 'centro': centro})


@login_required
def centro_custo_delete(request, pk):
    centro = get_object_or_404(CentroCusto, pk=pk)
    if request.method == 'POST':
        centro.delete()
        messages.success(request, 'Centro de custo excluído com sucesso!')
        return redirect('ERP_ServicesBI:centro_custo_list')
    return render(request, 'financeiro/centro_custo_confirm_delete.html', {'objeto': centro, 'titulo': 'Excluir Centro de Custo'})


# =============================================================================
# MÓDULO: FINANCEIRO - ORÇAMENTOS FINANCEIROS
# =============================================================================

@login_required
def orcamento_financeiro_list(request):
    orcamentos = OrcamentoFinanceiro.objects.select_related('categoria').all().order_by('-ano', '-mes')
    paginator = Paginator(orcamentos, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'financeiro/orcamento_financeiro_list.html', {'page_obj': page_obj, 'total': paginator.count})


@login_required
def orcamento_financeiro_add(request):
    if request.method == 'POST':
        form = OrcamentoFinanceiroForm(request.POST)
        if form.is_valid():
            orcamento = form.save(commit=False)
            orcamento.criado_por = request.user
            orcamento.save()
            messages.success(request, 'Orçamento criado com sucesso!')
            return redirect('ERP_ServicesBI:orcamento_financeiro_list')
    else:
        form = OrcamentoFinanceiroForm()
    return render(request, 'financeiro/orcamento_financeiro_form.html', {'form': form, 'titulo': 'Novo Orçamento Financeiro'})


@login_required
def orcamento_financeiro_edit(request, pk):
    orcamento = get_object_or_404(OrcamentoFinanceiro, pk=pk)
    if request.method == 'POST':
        form = OrcamentoFinanceiroForm(request.POST, instance=orcamento)
        if form.is_valid():
            form.save()
            messages.success(request, 'Orçamento atualizado com sucesso!')
            return redirect('ERP_ServicesBI:orcamento_financeiro_list')
    else:
        form = OrcamentoFinanceiroForm(instance=orcamento)
    return render(request, 'financeiro/orcamento_financeiro_form.html', {'form': form, 'titulo': 'Editar Orçamento Financeiro', 'orcamento': orcamento})


@login_required
def orcamento_financeiro_delete(request, pk):
    orcamento = get_object_or_404(OrcamentoFinanceiro, pk=pk)
    if request.method == 'POST':
        orcamento.delete()
        messages.success(request, 'Orçamento excluído com sucesso!')
        return redirect('ERP_ServicesBI:orcamento_financeiro_list')
    return render(request, 'financeiro/orcamento_financeiro_confirm_delete.html', {'objeto': orcamento, 'titulo': 'Excluir Orçamento Financeiro'})


# =============================================================================
# MÓDULO: FINANCEIRO - FLUXO DE CAIXA E CONCILIAÇÃO
# =============================================================================

@login_required
def fluxo_caixa(request):
    return render(request, 'financeiro/fluxo_caixa.html', {})


@login_required
def movimentacao_caixa_add(request):
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
    return render(request, 'financeiro/movimentacao_caixa_form.html', {'form': form, 'titulo': 'Novo Movimento de Caixa'})


@login_required
def conciliacao_list(request):
    extratos = ExtratoBancario.objects.all().order_by('-data_arquivo')
    paginator = Paginator(extratos, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'financeiro/conciliacao_list.html', {'page_obj': page_obj, 'total': paginator.count, 'extratos': page_obj})


@login_required
def conciliacao_add(request):
    return render(request, 'financeiro/conciliacao_form.html', {})


@login_required
def conciliacao_edit(request, pk):
    return render(request, 'financeiro/conciliacao_form.html', {})


@login_required
def conciliacao_delete(request, pk):
    return render(request, 'financeiro/confirm_delete.html', {})


# =============================================================================
# MÓDULO: FINANCEIRO - DRE GERENCIAL
# =============================================================================

@login_required
def dre_gerencial(request):
    """DRE Gerencial"""
    from .models import Empresa, ConfiguracaoDRE, RelatorioDRE

    empresas = Empresa.objects.filter(ativo=True).order_by('nome_fantasia')
    empresa_id = request.GET.get('empresa')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    regime = request.GET.get('regime')

    hoje = timezone.now().date()
    if not data_inicio:
        data_inicio = hoje.replace(day=1)
    else:
        data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
    if not data_fim:
        proximo_mes = hoje.replace(day=28) + timedelta(days=4)
        data_fim = proximo_mes - timedelta(days=proximo_mes.day)
    else:
        data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()

    context = {
        'empresas': empresas,
        'empresa_selecionada': None,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'regime_selecionado': regime,
        'regimes': ConfiguracaoDRE.REGIME_CHOICES,
        'dre_dados': None,
        'config': None,
    }

    if empresa_id:
        try:
            empresa = Empresa.objects.get(pk=empresa_id)
            context['empresa_selecionada'] = empresa
            config, created = ConfiguracaoDRE.objects.get_or_create(
                empresa=empresa,
                defaults={'regime_tributario': regime or 'simples'}
            )
            context['config'] = config
            regime_calc = regime or config.regime_tributario
            context['regime_selecionado'] = regime_calc

            from .services.dre_service import DREService
            service = DREService(empresa, data_inicio, data_fim, regime_calc)
            dre_dados = service.calcular_dre_completa()
            context['dre_dados'] = dre_dados
        except Empresa.DoesNotExist:
            messages.error(request, 'Empresa não encontrada.')
        except Exception as e:
            messages.error(request, f'Erro ao calcular DRE: {str(e)}')

    return render(request, 'financeiro/dre_gerencial.html', context)


@login_required
def dre_configuracao(request, empresa_id=None):
    """Configuração do DRE por empresa"""
    from .models import Empresa, ConfiguracaoDRE
    from .forms import ConfiguracaoDREForm

    if empresa_id:
        empresa = get_object_or_404(Empresa, pk=empresa_id)
        config, created = ConfiguracaoDRE.objects.get_or_create(empresa=empresa)
    else:
        config = None
        empresa = None

    if request.method == 'POST':
        form = ConfiguracaoDREForm(request.POST, instance=config) if config else ConfiguracaoDREForm(request.POST)
        if form.is_valid():
            config = form.save()
            messages.success(request, 'Configuração salva com sucesso!')
            return redirect('ERP_ServicesBI:dre_gerencial')
    else:
        form = ConfiguracaoDREForm(instance=config) if config else ConfiguracaoDREForm()

    context = {
        'form': form,
        'empresa': empresa,
        'config': config,
        'titulo': f'Configuração DRE - {empresa.nome_fantasia}' if empresa else 'Nova Configuração DRE',
    }
    return render(request, 'financeiro/dre_configuracao.html', context)


@login_required
@require_POST
def dre_alterar_regime(request):
    """Alterar regime tributário do DRE"""
    from .models import Empresa, ConfiguracaoDRE
    try:
        empresa_id = request.POST.get('empresa_id')
        novo_regime = request.POST.get('regime')
        empresa = get_object_or_404(Empresa, pk=empresa_id)
        config, created = ConfiguracaoDRE.objects.get_or_create(empresa=empresa)
        config.regime_tributario = novo_regime
        config.save()
        return JsonResponse({'success': True, 'message': f'Regime alterado para {config.get_regime_tributario_display()}'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def dre_exportar_pdf(request):
    messages.info(request, 'Exportação PDF em desenvolvimento.')
    return redirect('ERP_ServicesBI:dre_gerencial')


@login_required
def dre_exportar_excel(request):
    """Exportar DRE para Excel"""
    from .models import Empresa, ConfiguracaoDRE

    empresa_id = request.GET.get('empresa')
    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')
    regime = request.GET.get('regime')

    if not empresa_id:
        messages.error(request, 'Selecione uma empresa.')
        return redirect('ERP_ServicesBI:dre_gerencial')

    try:
        empresa = Empresa.objects.get(pk=empresa_id)
        di = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        df = datetime.strptime(data_fim_str, '%Y-%m-%d').date()

        from .services.dre_service import DREService
        service = DREService(empresa, di, df, regime)
        dre_dados = service.calcular_dre_completa()

        import openpyxl
        from openpyxl.styles import Font

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "DRE"
        ws['A1'] = f"DRE - {empresa.nome_fantasia}"
        ws['A1'].font = Font(bold=True, size=14)
        ws['A2'] = f"Período: {di.strftime('%d/%m/%Y')} a {df.strftime('%d/%m/%Y')}"
        ws['A3'] = f"Regime: {regime.upper()}"

        ws['A5'] = 'Código'
        ws['B5'] = 'Descrição'
        ws['C5'] = 'Valor (R$)'
        ws['D5'] = 'AV (%)'
        for col in ['A5', 'B5', 'C5', 'D5']:
            ws[col].font = Font(bold=True)

        row = 6
        for linha in dre_dados['linhas']:
            ws[f'A{row}'] = linha['codigo']
            ws[f'B{row}'] = ('  ' * linha['nivel']) + linha['descricao']
            ws[f'C{row}'] = float(linha['valor'])
            ws[f'D{row}'] = float(linha['percentual'])
            if linha['negrito']:
                ws[f'A{row}'].font = Font(bold=True)
                ws[f'B{row}'].font = Font(bold=True)
                ws[f'C{row}'].font = Font(bold=True)
            row += 1

        ws.column_dimensions['A'].width = 10
        ws.column_dimensions['B'].width = 45
        ws.column_dimensions['C'].width = 18
        ws.column_dimensions['D'].width = 12
        for r in range(6, row):
            ws[f'C{r}'].number_format = '#,##0.00'
            ws[f'D{r}'].number_format = '0.00'

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="DRE_{empresa.nome_fantasia}_{df.strftime("%Y%m")}.xlsx"'
        return response

    except ImportError:
        messages.error(request, 'Biblioteca openpyxl não instalada.')
        return redirect('ERP_ServicesBI:dre_gerencial')
    except Exception as e:
        messages.error(request, f'Erro ao exportar: {str(e)}')
        return redirect('ERP_ServicesBI:dre_gerencial')


@login_required
def dre_salvar_relatorio(request):
    from .models import Empresa
    empresa_id = request.GET.get('empresa')
    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')
    regime = request.GET.get('regime')
    if not empresa_id:
        messages.error(request, 'Selecione uma empresa.')
        return redirect('ERP_ServicesBI:dre_gerencial')
    try:
        empresa = Empresa.objects.get(pk=empresa_id)
        di = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        df = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        from .services.dre_service import DREService
        service = DREService(empresa, di, df, regime)
        relatorio = service.salvar_relatorio(user=request.user)
        messages.success(request, f'Relatório salvo com sucesso! ID: {relatorio.id}')
    except Exception as e:
        messages.error(request, f'Erro ao salvar: {str(e)}')
    return redirect('ERP_ServicesBI:dre_gerencial')


@login_required
def dre_historico(request):
    from .models import RelatorioDRE, Empresa
    empresa_id = request.GET.get('empresa')
    relatorios = RelatorioDRE.objects.select_related('empresa', 'gerado_por').order_by('-gerado_em')
    if empresa_id:
        relatorios = relatorios.filter(empresa_id=empresa_id)
    paginator = Paginator(relatorios, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'total': paginator.count,
        'empresas': Empresa.objects.filter(ativo=True),
        'empresa_filtro': empresa_id,
    }
    return render(request, 'financeiro/dre_historico.html', context)


@login_required
def dre_visualizar_relatorio(request, pk):
    from .models import RelatorioDRE
    relatorio = get_object_or_404(RelatorioDRE, pk=pk)
    return render(request, 'financeiro/dre_visualizar.html', {'relatorio': relatorio, 'dre_dados': relatorio.dados_json})


@login_required
def dre_comparativo(request):
    from .models import Empresa, ConfiguracaoDRE
    empresas = Empresa.objects.filter(ativo=True)
    empresa_id = request.GET.get('empresa')
    periodo1_inicio = request.GET.get('p1_inicio')
    periodo1_fim = request.GET.get('p1_fim')
    periodo2_inicio = request.GET.get('p2_inicio')
    periodo2_fim = request.GET.get('p2_fim')

    context = {'empresas': empresas, 'dre_periodo1': None, 'dre_periodo2': None, 'comparativo': None}

    if empresa_id and periodo1_inicio and periodo1_fim and periodo2_inicio and periodo2_fim:
        try:
            empresa = Empresa.objects.get(pk=empresa_id)
            p1_inicio = datetime.strptime(periodo1_inicio, '%Y-%m-%d').date()
            p1_fim = datetime.strptime(periodo1_fim, '%Y-%m-%d').date()
            p2_inicio = datetime.strptime(periodo2_inicio, '%Y-%m-%d').date()
            p2_fim = datetime.strptime(periodo2_fim, '%Y-%m-%d').date()

            from .services.dre_service import DREService
            service1 = DREService(empresa, p1_inicio, p1_fim)
            dre1 = service1.calcular_dre_completa()
            service2 = DREService(empresa, p2_inicio, p2_fim)
            dre2 = service2.calcular_dre_completa()

            comparativo = []
            for i, linha1 in enumerate(dre1['linhas']):
                linha2 = dre2['linhas'][i] if i < len(dre2['linhas']) else None
                valor1 = linha1['valor']
                valor2 = linha2['valor'] if linha2 else Decimal('0')
                variacao_abs = valor2 - valor1
                variacao_pct = ((valor2 - valor1) / valor1 * 100) if valor1 != 0 else Decimal('0')
                comparativo.append({
                    'codigo': linha1['codigo'],
                    'descricao': linha1['descricao'],
                    'valor_p1': valor1,
                    'valor_p2': valor2,
                    'variacao_abs': variacao_abs,
                    'variacao_pct': variacao_pct,
                    'nivel': linha1['nivel'],
                    'negrito': linha1['negrito'],
                })

            context['empresa_selecionada'] = empresa
            context['dre_periodo1'] = dre1
            context['dre_periodo2'] = dre2
            context['comparativo'] = comparativo
            context['p1_inicio'] = p1_inicio
            context['p1_fim'] = p1_fim
            context['p2_inicio'] = p2_inicio
            context['p2_fim'] = p2_fim
        except Exception as e:
            messages.error(request, f'Erro ao comparar: {str(e)}')

    return render(request, 'financeiro/dre_comparativo.html', context)


# =============================================================================
# MÓDULO: ESTOQUE - MOVIMENTAÇÕES
# =============================================================================

@login_required
def movimentacao_estoque_list(request):
    """Listagem de movimentações de estoque"""
    movimentacoes = MovimentacaoEstoque.objects.select_related('produto', 'usuario').all().order_by('-data')

    produto_id = request.GET.get('produto')
    tipo = request.GET.get('tipo')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    if produto_id:
        movimentacoes = movimentacoes.filter(produto_id=produto_id)
    if tipo:
        movimentacoes = movimentacoes.filter(tipo=tipo)
    if data_inicio:
        movimentacoes = movimentacoes.filter(data__gte=data_inicio)
    if data_fim:
        movimentacoes = movimentacoes.filter(data__lte=data_fim)

    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
    except (ValueError, TypeError):
        per_page = 25

    paginator = Paginator(movimentacoes, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'total': paginator.count,
        'produtos': Produto.objects.filter(ativo=True).order_by('descricao'),
        'tipos': MovimentacaoEstoque.TIPO_CHOICES,
        'filtros': {
            'produto': produto_id or '',
            'tipo': tipo or '',
            'data_inicio': data_inicio or '',
            'data_fim': data_fim or '',
        }
    }
    return render(request, 'estoque/movimentacao_estoque_list.html', context)


@login_required
def movimentacao_estoque_add(request):
    """Cadastro de movimentação de estoque"""
    if request.method == 'POST':
        form = MovimentacaoEstoqueForm(request.POST)
        if form.is_valid():
            movimentacao = form.save(commit=False)
            movimentacao.usuario = request.user
            movimentacao.save()
            messages.success(request, 'Movimentação registrada com sucesso!')
            return redirect('ERP_ServicesBI:movimentacao_estoque_list')
    else:
        initial = {}
        produto_id = request.GET.get('produto')
        if produto_id:
            initial['produto'] = produto_id
        form = MovimentacaoEstoqueForm(initial=initial)

    context = {
        'form': form,
        'titulo': 'Nova Movimentação de Estoque',
        'produtos': Produto.objects.filter(ativo=True).order_by('descricao'),
        'tipos': MovimentacaoEstoque.TIPO_CHOICES,
        'is_edit': False,
    }
    return render(request, 'estoque/movimentacao_estoque_form.html', context)


@login_required
def movimentacao_estoque_edit(request, pk):
    """Edição de movimentação de estoque"""
    movimentacao = get_object_or_404(MovimentacaoEstoque, pk=pk)
    if request.method == 'POST':
        form = MovimentacaoEstoqueForm(request.POST, instance=movimentacao)
        if form.is_valid():
            form.save()
            messages.success(request, 'Movimentação atualizada com sucesso!')
            return redirect('ERP_ServicesBI:movimentacao_estoque_list')
    else:
        form = MovimentacaoEstoqueForm(instance=movimentacao)

    context = {
        'form': form,
        'titulo': 'Editar Movimentação',
        'movimentacao': movimentacao,
        'produtos': Produto.objects.filter(ativo=True).order_by('descricao'),
        'tipos': MovimentacaoEstoque.TIPO_CHOICES,
        'is_edit': True,
    }
    return render(request, 'estoque/movimentacao_estoque_form.html', context)


@login_required
def movimentacao_estoque_delete(request, pk):
    """Exclusão de movimentação de estoque"""
    movimentacao = get_object_or_404(MovimentacaoEstoque, pk=pk)
    if request.method == 'POST':
        try:
            movimentacao.delete()
            messages.success(request, 'Movimentação excluída com sucesso!')
        except Exception as e:
            messages.error(request, f'Erro ao excluir: {str(e)}')
        return redirect('ERP_ServicesBI:movimentacao_estoque_list')

    context = {
        'objeto': movimentacao,
        'titulo': 'Excluir Movimentação',
        'tipo_objeto': 'movimentação de estoque',
        'voltar_url': 'ERP_ServicesBI:movimentacao_estoque_list',
    }
    return render(request, 'estoque/movimentacao_estoque_confirm_delete.html', context)


# =============================================================================
# MÓDULO: ESTOQUE - INVENTÁRIOS
# =============================================================================

@login_required
def inventario_list(request):
    inventarios = Inventario.objects.select_related('usuario').prefetch_related('itens').all().order_by('-data')

    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    order_by = request.GET.get('order_by', '-data')
    per_page = request.GET.get('per_page', '25')

    if search:
        inventarios = inventarios.filter(Q(numero__icontains=search) | Q(descricao__icontains=search))
    if status:
        inventarios = inventarios.filter(status=status)
    if data_inicio:
        inventarios = inventarios.filter(data__gte=data_inicio)
    if data_fim:
        inventarios = inventarios.filter(data__lte=data_fim)

    order_fields = ['data', '-data', 'id', '-id', 'numero', '-numero', 'status', '-status']
    if order_by in order_fields:
        inventarios = inventarios.order_by(order_by)

    try:
        per_page = int(per_page)
    except (ValueError, TypeError):
        per_page = 25

    paginator = Paginator(inventarios, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'total': paginator.count,
        'search': search,
        'status': status,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'order_by': order_by,
        'per_page': str(per_page),
        'status_choices': getattr(Inventario, 'STATUS_CHOICES', [
            ('em_andamento', 'Em Andamento'),
            ('finalizado', 'Finalizado'),
            ('cancelado', 'Cancelado'),
        ]),
    }
    return render(request, 'estoque/inventario_list.html', context)


@login_required
def inventario_add(request):
    if request.method == 'POST':
        form = InventarioForm(request.POST)
        if form.is_valid():
            try:
                inventario = form.save(commit=False)
                inventario.usuario = request.user
                if not hasattr(inventario, 'gerar_numero_sequencial'):
                    ultimo = Inventario.objects.order_by('-id').first()
                    proximo_num = (ultimo.id + 1) if ultimo else 1
                    inventario.numero = f"INV-{proximo_num:06d}"
                inventario.save()
                messages.success(request, f'Inventário #{inventario.numero} criado! Agora adicione os itens.')
                return redirect('ERP_ServicesBI:inventario_edit', pk=inventario.pk)
            except Exception as e:
                messages.error(request, f'Erro ao criar inventário: {str(e)}')
        else:
            messages.error(request, 'Erro no formulário. Verifique os dados.')
    else:
        form = InventarioForm()

    numero_sugerido = None
    try:
        ultimo = Inventario.objects.order_by('-id').first()
        proximo = (ultimo.id + 1) if ultimo else 1
        numero_sugerido = f"INV-{proximo:06d}"
    except Exception:
        pass

    context = {
        'form': form,
        'titulo': 'Novo Inventário',
        'numero_sugerido': numero_sugerido,
        'data_hoje': date.today().isoformat(),
        'is_edit': False,
    }
    return render(request, 'estoque/inventario_form.html', context)


@login_required
def inventario_edit(request, pk):
    inventario = get_object_or_404(Inventario.objects.select_related('usuario'), pk=pk)

    if request.method == 'POST':
        form = InventarioForm(request.POST, instance=inventario)
        if form.is_valid():
            form.save()
            messages.success(request, 'Inventário atualizado com sucesso!')
            return redirect('ERP_ServicesBI:inventario_list')
    else:
        form = InventarioForm(instance=inventario)

    itens = inventario.itens.select_related('produto').all()
    contados = itens.exclude(quantidade_contada__isnull=True).count()
    total_itens = itens.count()
    progresso = (contados / total_itens * 100) if total_itens > 0 else 0

    context = {
        'form': form,
        'titulo': f'Inventário #{inventario.numero}',
        'inventario': inventario,
        'itens': itens,
        'contados': contados,
        'total_itens': total_itens,
        'progresso': round(progresso, 1),
        'is_edit': True,
        'pode_finalizar': contados > 0 and inventario.status == 'em_andamento',
    }
    return render(request, 'estoque/inventario_form.html', context)


@login_required
def inventario_item_add(request, inventario_pk):
    inventario = get_object_or_404(Inventario, pk=inventario_pk)
    if request.method == 'POST':
        produto_id = request.POST.get('produto')
        quantidade = request.POST.get('quantidade_contada')
        try:
            produto = Produto.objects.get(pk=produto_id)
            ItemInventario.objects.update_or_create(
                inventario=inventario,
                produto=produto,
                defaults={
                    'quantidade_contada': quantidade,
                    'quantidade_sistema': produto.quantidade_estoque or 0,
                    'usuario': request.user,
                }
            )
            messages.success(request, f'{produto.descricao} atualizado!')
        except Exception as e:
            messages.error(request, f'Erro: {str(e)}')
        return redirect('ERP_ServicesBI:inventario_edit', pk=inventario_pk)

    produtos_disponiveis = Produto.objects.filter(ativo=True).exclude(
        id__in=inventario.itens.values_list('produto_id', flat=True)
    )
    context = {'inventario': inventario, 'produtos': produtos_disponiveis}
    return render(request, 'estoque/inventario_item_form.html', context)


@login_required
def inventario_finalizar(request, pk):
    inventario = get_object_or_404(Inventario, pk=pk)
    if request.method == 'POST':
        try:
            inventario.status = 'finalizado'
            inventario.data_finalizacao = timezone.now()
            inventario.save()

            if request.POST.get('ajustar_estoque') == 'on':
                for item in inventario.itens.exclude(quantidade_contada__isnull=True):
                    if item.quantidade_contada != item.quantidade_sistema:
                        MovimentacaoEstoque.objects.create(
                            produto=item.produto,
                            tipo='ajuste' if item.quantidade_contada > item.quantidade_sistema else 'ajuste_negativo',
                            quantidade=abs(item.quantidade_contada - item.quantidade_sistema),
                            motivo=f'Ajuste via Inventário #{inventario.numero}',
                            usuario=request.user,
                        )
                        item.produto.quantidade_estoque = item.quantidade_contada
                        item.produto.save()

            messages.success(request, f'Inventário #{inventario.numero} finalizado!')
        except Exception as e:
            messages.error(request, f'Erro ao finalizar: {str(e)}')
    return redirect('ERP_ServicesBI:inventario_list')


@login_required
def inventario_delete(request, pk):
    inventario = get_object_or_404(Inventario, pk=pk)
    if inventario.status == 'finalizado':
        messages.error(request, 'Não é possível excluir inventário finalizado!')
        return redirect('ERP_ServicesBI:inventario_list')

    if request.method == 'POST':
        try:
            inventario.itens.all().delete()
            inventario.delete()
            messages.success(request, 'Inventário excluído com sucesso!')
        except Exception as e:
            messages.error(request, f'Erro ao excluir: {str(e)}')
        return redirect('ERP_ServicesBI:inventario_list')

    context = {
        'objeto': inventario,
        'titulo': 'Excluir Inventário',
        'tipo_objeto': 'inventário de estoque',
        'mensagem_adicional': f'Este inventário possui {inventario.itens.count()} itens que também serão excluídos.',
        'voltar_url': 'ERP_ServicesBI:inventario_list',
    }
    return render(request, 'estoque/confirm_delete.html', context)


# =============================================================================
# MÓDULO: ESTOQUE - TRANSFERÊNCIAS
# =============================================================================

@login_required
def transferencia_list(request):
    transferencias = TransferenciaEstoque.objects.select_related('usuario').all().order_by('-data')

    status = request.GET.get('status', '')
    deposito = request.GET.get('deposito', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    per_page = request.GET.get('per_page', '25')

    if status:
        transferencias = transferencias.filter(status=status)
    if deposito:
        transferencias = transferencias.filter(Q(origem=deposito) | Q(destino=deposito))
    if data_inicio:
        transferencias = transferencias.filter(data__gte=data_inicio)
    if data_fim:
        transferencias = transferencias.filter(data__lte=data_fim)

    try:
        per_page = int(per_page)
    except (ValueError, TypeError):
        per_page = 25

    paginator = Paginator(transferencias, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'total': paginator.count,
        'status': status,
        'deposito': deposito,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'per_page': str(per_page),
        'status_choices': getattr(TransferenciaEstoque, 'STATUS_CHOICES', [
            ('pendente', 'Pendente'),
            ('concluida', 'Concluída'),
            ('cancelada', 'Cancelada'),
        ]),
    }
    return render(request, 'estoque/transferencia_list.html', context)


@login_required
def transferencia_add(request):
    if request.method == 'POST':
        form = TransferenciaEstoqueForm(request.POST)
        if form.is_valid():
            transferencia = form.save(commit=False)
            transferencia.usuario = request.user
            transferencia.status = 'pendente'
            transferencia.save()
            messages.success(request, 'Transferência criada com sucesso!')
            return redirect('ERP_ServicesBI:transferencia_list')
    else:
        form = TransferenciaEstoqueForm()

    context = {
        'form': form,
        'titulo': 'Nova Transferência de Estoque',
        'produtos': Produto.objects.filter(ativo=True).order_by('descricao'),
        'is_edit': False,
    }
    return render(request, 'estoque/transferencia_form.html', context)


@login_required
def transferencia_edit(request, pk):
    transferencia = get_object_or_404(TransferenciaEstoque, pk=pk)
    if transferencia.status != 'pendente':
        messages.error(request, 'Só é possível editar transferências pendentes!')
        return redirect('ERP_ServicesBI:transferencia_list')

    if request.method == 'POST':
        form = TransferenciaEstoqueForm(request.POST, instance=transferencia)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transferência atualizada com sucesso!')
            return redirect('ERP_ServicesBI:transferencia_list')
    else:
        form = TransferenciaEstoqueForm(instance=transferencia)

    context = {
        'form': form,
        'titulo': 'Editar Transferência',
        'transferencia': transferencia,
        'produtos': Produto.objects.filter(ativo=True).order_by('descricao'),
        'is_edit': True,
    }
    return render(request, 'estoque/transferencia_form.html', context)


@login_required
def transferencia_concluir(request, pk):
    transferencia = get_object_or_404(TransferenciaEstoque, pk=pk)
    if request.method == 'POST':
        try:
            transferencia.status = 'concluida'
            transferencia.data_conclusao = timezone.now()
            transferencia.save()
            messages.success(request, 'Transferência concluída!')
        except Exception as e:
            messages.error(request, f'Erro ao concluir: {str(e)}')
    return redirect('ERP_ServicesBI:transferencia_list')


@login_required
def transferencia_delete(request, pk):
    transferencia = get_object_or_404(TransferenciaEstoque, pk=pk)
    if transferencia.status == 'concluida':
        messages.error(request, 'Não é possível excluir transferência concluída!')
        return redirect('ERP_ServicesBI:transferencia_list')

    if request.method == 'POST':
        try:
            transferencia.delete()
            messages.success(request, 'Transferência excluída com sucesso!')
        except Exception as e:
            messages.error(request, f'Erro ao excluir: {str(e)}')
        return redirect('ERP_ServicesBI:transferencia_list')

    context = {
        'objeto': transferencia,
        'titulo': 'Excluir Transferência',
        'tipo_objeto': 'transferência de estoque',
        'voltar_url': 'ERP_ServicesBI:transferencia_list',
    }
    return render(request, 'estoque/confirm_delete.html', context)


# =============================================================================
# MÓDULO: ESTOQUE - RELATÓRIOS
# =============================================================================

@login_required
def relatorio_estoque(request):
    """Relatório de posição de estoque"""
    produtos = Produto.objects.select_related('categoria').filter(ativo=True)

    categoria_id = request.GET.get('categoria')
    estoque_baixo_filter = request.GET.get('estoque_baixo')

    if categoria_id:
        produtos = produtos.filter(categoria_id=categoria_id)
    if estoque_baixo_filter:
        produtos = produtos.filter(estoque_atual__lte=F('estoque_minimo'))

    total_produtos = produtos.count()
    valor_total_estoque = produtos.aggregate(
        total=Sum(F('estoque_atual') * F('preco_custo'), output_field=DecimalField())
    )['total'] or 0
    estoque_baixo_count = produtos.filter(estoque_atual__lte=F('estoque_minimo')).count()
    produtos_baixo = produtos.filter(estoque_atual__lte=F('estoque_minimo'))[:10]
    curva_abc = produtos.annotate(
        valor_estoque=F('estoque_atual') * F('preco_custo')
    ).order_by('-valor_estoque')[:10]

    context = {
        'produtos': produtos.order_by('descricao'),
        'total_produtos': total_produtos,
        'valor_total_estoque': valor_total_estoque,
        'estoque_baixo_count': estoque_baixo_count,
        'produtos_baixo': produtos_baixo,
        'curva_abc': curva_abc,
        'categorias': CategoriaProduto.objects.filter(ativo=True),
        'filtros': {
            'categoria': categoria_id or '',
            'estoque_baixo': estoque_baixo_filter or '',
        }
    }
    return render(request, 'estoque/relatorio_estoque.html', context)


@login_required
def relatorio_movimentacoes(request):
    """Relatório de movimentações de estoque"""
    movimentacoes = MovimentacaoEstoque.objects.select_related('produto', 'usuario').all()

    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    produto_id = request.GET.get('produto')
    tipo = request.GET.get('tipo')

    if data_inicio:
        movimentacoes = movimentacoes.filter(data__gte=data_inicio)
    if data_fim:
        movimentacoes = movimentacoes.filter(data__lte=data_fim)
    if produto_id:
        movimentacoes = movimentacoes.filter(produto_id=produto_id)
    if tipo:
        movimentacoes = movimentacoes.filter(tipo=tipo)

    resumo_tipo = movimentacoes.values('tipo').annotate(
        quantidade_movimentacoes=Count('id'),
        total_quantidade=Sum('quantidade')
    ).order_by('tipo')

    resumo_produto = movimentacoes.values('produto__descricao').annotate(
        total_movimentado=Sum('quantidade')
    ).order_by('-total_movimentado')[:20]

    context = {
        'movimentacoes': movimentacoes.order_by('-data')[:100],
        'resumo_tipo': resumo_tipo,
        'resumo_produto': resumo_produto,
        'total_registros': movimentacoes.count(),
        'produtos': Produto.objects.filter(ativo=True),
        'tipos': MovimentacaoEstoque.TIPO_CHOICES,
        'filtros': {
            'data_inicio': data_inicio or '',
            'data_fim': data_fim or '',
            'produto': produto_id or '',
            'tipo': tipo or '',
        }
    }
    return render(request, 'estoque/relatorio_movimentacoes.html', context)
