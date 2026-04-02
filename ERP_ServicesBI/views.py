# =============================================================================
# VIEWS.PY - BLOCO DE IMPORTS CORRIGIDO

# Django core
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import (
    Sum, Q, F, Min, Avg, Count, DecimalField, Prefetch, Max
)
from django.db import transaction, models
from django.utils import timezone
from django.contrib.auth.models import User, Group

# Python stdlib
import csv
import io
import json
import re
import calendar
import logging
import unicodedata
from datetime import date, timedelta, datetime
from decimal import Decimal, InvalidOperation

# Models - CORRIGIDO
from .models import (
    # Cadastros Base
    Cliente, Empresa, Fornecedor, Vendedor,

    # Produtos e Estoque
    Produto, CategoriaProduto, UnidadeMedida,
    Deposito, SaldoEstoque,
    MovimentacaoEstoque,
    EntradaNFE, ItemEntradaNFE,
    Inventario, ItemInventario,          # ← era ContagemInventario

    # Compras
    PedidoCompra, ItemPedidoCompra,
    NotaFiscalEntrada, ItemNotaFiscalEntrada,
    CotacaoMae, ItemSolicitado,
    CotacaoFornecedor, ItemCotacaoFornecedor,
    RegraAprovacao, PedidoAprovacao,

    # Vendas
    Orcamento, ItemOrcamento,
    PedidoVenda, ItemPedidoVenda,
    NotaFiscalSaida, ItemNotaFiscalSaida,

    # Financeiro - Contas
    ContaPagar, ContaReceber,
    CondicaoPagamento, FormaPagamento,

    # Financeiro - Categorias e Centro de Custo
    CategoriaFinanceira, CentroCusto, OrcamentoFinanceiro,

    # Financeiro - Fluxo de Caixa e Conciliação
    MovimentoCaixa, ExtratoBancario, LancamentoExtrato,

    # Financeiro - DRE e Configurações
    ConfiguracaoDRE, RelatorioDRE,
)

# Forms - CORRIGIDO
from .forms import (
    # Cadastros
    ClienteForm, EmpresaForm, FornecedorForm, VendedorForm,

    # Produtos e Estoque
    CategoriaProdutoForm, ProdutoForm, UnidadeMedidaForm,
    DepositoForm,
    MovimentacaoEstoqueForm,
    EntradaNFEForm, ItemEntradaNFEForm,
    InventarioForm, ItemInventarioForm,  # ← era ContagemInventarioForm

    # Compras
    PedidoCompraForm, ItemPedidoCompraForm,
    NotaFiscalEntradaForm, ItemNotaFiscalEntradaForm,
    CotacaoMaeForm, ItemSolicitadoForm, ItemSolicitadoFormSet,
    CotacaoFornecedorForm, ItemCotacaoFornecedorForm,
    ItemCotacaoFornecedorFormSet,

    # Vendas
    OrcamentoForm, ItemOrcamentoForm,
    PedidoVendaForm, ItemPedidoVendaForm,
    NotaFiscalSaidaForm, ItemNotaFiscalSaidaForm,

    # Financeiro - Contas
    ContaPagarForm, ContaReceberForm,
    BaixaContaPagarForm, BaixaContaReceberForm,

    # Financeiro - Categorias e Centro de Custo
    CategoriaFinanceiraForm, CentroCustoForm, OrcamentoFinanceiroForm,

    # Financeiro - Fluxo de Caixa e Conciliação
    MovimentoCaixaForm, ExtratoBancarioForm, LancamentoExtratoForm,

    # Financeiro - DRE
    ConfiguracaoDREForm,

    # Configurações
    CondicaoPagamentoForm, FormaPagamentoForm,
)

# Services (se existirem)
try:
    from .services.dre_service import DREService
except ImportError:
    DREService = None

# Logger seguro para o módulo
logger = logging.getLogger('erp.cotacoes')

# =============================================================================
# UTILITÁRIOS DE LOGGING SEGURO

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
# UTILITÁRIOS DE PERMISSÃO DE APROVAÇÃO (FASE 2)

def get_nivel_aprovacao_usuario(usuario):
    """
    Retorna o maior nível de aprovação que o usuário possui.
    Verifica grupos: aprovador_nivel_1, aprovador_nivel_2, aprovador_nivel_3
    """
    niveis = []
    if usuario.groups.filter(name='aprovador_nivel_1').exists() or usuario.has_perm('ERP_ServicesBI.pode_aprovar_pedido_nivel_1'):
        niveis.append(1)
    if usuario.groups.filter(name='aprovador_nivel_2').exists() or usuario.has_perm('ERP_ServicesBI.pode_aprovar_pedido_nivel_2'):
        niveis.append(2)
    if usuario.groups.filter(name='aprovador_nivel_3').exists() or usuario.has_perm('ERP_ServicesBI.pode_aprovar_pedido_nivel_3'):
        niveis.append(3)
    return max(niveis) if niveis else 0

def pode_aprovar_pedido_usuario(pedido, usuario):
    """
    Verifica se usuário pode aprovar o pedido no nível atual.
    """
    if pedido.status != 'em_aprovacao':
        return False, "Pedido não está em aprovação"
    
    nivel_usuario = get_nivel_aprovacao_usuario(usuario)
    proximo_nivel = pedido.nivel_aprovacao_atual + 1
    
    if nivel_usuario < proximo_nivel:
        return False, f"Requer nível {proximo_nivel}, usuário tem nível {nivel_usuario}"
    
    return True, None

def verificar_regras_aprovacao(pedido):
    """
    Verifica se pedido precisa de aprovação baseado nas Regras de Aprovação.
    Retorna (precisa_aprovacao, nivel_necessario)
    """
    regras = RegraAprovacao.objects.filter(
        ativo=True,
        valor_minimo__lte=pedido.valor_total,
        valor_maximo__gte=pedido.valor_total
    ).order_by('nivel')
    
    if regras.exists():
        maior_nivel = regras.last()
        return True, maior_nivel.nivel
    
    return False, 0

# =============================================================================
# CORREÇÃO: View dashboard com dados financeiros reais
# SUBSTITUIR a função dashboard existente no views.py
# =============================================================================

@login_required
def dashboard(request):
    """Dashboard principal do ERP - com dados financeiros reais"""
    
    hoje = timezone.now().date()
    inicio_mes = hoje.replace(day=1)
    
    # Calcula início do mês anterior
    if inicio_mes.month == 1:
        inicio_mes_anterior = inicio_mes.replace(year=inicio_mes.year - 1, month=12)
    else:
        inicio_mes_anterior = inicio_mes.replace(month=inicio_mes.month - 1)
    fim_mes_anterior = inicio_mes - timedelta(days=1)
    
    # Contadores de aprovação pendentes
    nivel_usuario = get_nivel_aprovacao_usuario(request.user)
    pedidos_pendentes_aprovacao = 0
    if nivel_usuario > 0:
        pedidos_pendentes_aprovacao = PedidoCompra.objects.filter(
            status='em_aprovacao',
            nivel_aprovacao_atual__lt=F('nivel_aprovacao_necessario'),
            nivel_aprovacao_atual__lte=nivel_usuario
        ).count()
    
    # =====================================================================
    # DADOS FINANCEIROS REAIS
    # =====================================================================
    
    # Receitas (Contas a Receber quitadas/recebidas no mês)
    receitas_mes = ContaReceber.objects.filter(
        status__in=['recebido', 'quitado'],
        data_recebimento__gte=inicio_mes,
        data_recebimento__lte=hoje
    ).aggregate(total=Sum('valor_recebido'))['total'] or Decimal('0')
    
    # Se não tem recebimentos, pega NFs de saída confirmadas
    if receitas_mes == 0:
        receitas_mes = NotaFiscalSaida.objects.filter(
            status='confirmada',
            data_emissao__gte=inicio_mes,
            data_emissao__lte=hoje
        ).aggregate(total=Sum('valor_total'))['total'] or Decimal('0')
    
    # Despesas (Contas a Pagar pagas no mês)
    despesas_mes = ContaPagar.objects.filter(
        status__in=['pago', 'quitado'],
        data_pagamento__gte=inicio_mes,
        data_pagamento__lte=hoje
    ).aggregate(total=Sum('valor_pago'))['total'] or Decimal('0')
    
    # Se não tem pagamentos, pega NFs de entrada confirmadas
    if despesas_mes == 0:
        despesas_mes = NotaFiscalEntrada.objects.filter(
            status='confirmada',
            data_entrada__gte=inicio_mes,
            data_entrada__lte=hoje
        ).aggregate(total=Sum('valor_total'))['total'] or Decimal('0')
    
    # Saldo líquido
    saldo_liquido = receitas_mes - despesas_mes
    
    # Contas a receber pendentes (previsão de entrada)
    contas_receber_pendentes = ContaReceber.objects.filter(
        status__in=['pendente', 'aberto', 'parcial']
    ).aggregate(total=Sum('valor_saldo'))['total'] or Decimal('0')
    
    # Contas a pagar pendentes (previsão de saída)
    contas_pagar_pendentes = ContaPagar.objects.filter(
        status__in=['pendente', 'aberto', 'parcial']
    ).aggregate(total=Sum('valor_saldo'))['total'] or Decimal('0')
    
    # Saldo previsto
    saldo_previsto = saldo_liquido + contas_receber_pendentes - contas_pagar_pendentes
    
    # =====================================================================
    # VARIAÇÕES (TRENDS) vs Mês Anterior
    # =====================================================================
    receitas_mes_anterior = ContaReceber.objects.filter(
        status__in=['recebido', 'quitado'],
        data_recebimento__gte=inicio_mes_anterior,
        data_recebimento__lte=fim_mes_anterior
    ).aggregate(total=Sum('valor_recebido'))['total'] or Decimal('0')
    
    if receitas_mes_anterior == 0:
        receitas_mes_anterior = NotaFiscalSaida.objects.filter(
            status='confirmada',
            data_emissao__gte=inicio_mes_anterior,
            data_emissao__lte=fim_mes_anterior
        ).aggregate(total=Sum('valor_total'))['total'] or Decimal('0')
    
    despesas_mes_anterior = ContaPagar.objects.filter(
        status__in=['pago', 'quitado'],
        data_pagamento__gte=inicio_mes_anterior,
        data_pagamento__lte=fim_mes_anterior
    ).aggregate(total=Sum('valor_pago'))['total'] or Decimal('0')
    
    if despesas_mes_anterior == 0:
        despesas_mes_anterior = NotaFiscalEntrada.objects.filter(
            status='confirmada',
            data_entrada__gte=inicio_mes_anterior,
            data_entrada__lte=fim_mes_anterior
        ).aggregate(total=Sum('valor_total'))['total'] or Decimal('0')
    
    trend_receitas = 0
    if receitas_mes_anterior > 0:
        trend_receitas = round(float((receitas_mes - receitas_mes_anterior) / receitas_mes_anterior * 100), 1)
    elif receitas_mes > 0:
        trend_receitas = 100.0
    
    trend_despesas = 0
    if despesas_mes_anterior > 0:
        trend_despesas = round(float((despesas_mes - despesas_mes_anterior) / despesas_mes_anterior * 100), 1)
    elif despesas_mes > 0:
        trend_despesas = 100.0
    
    # =====================================================================
    # DADOS MENSAIS PARA GRÁFICOS (últimos 6 meses)
    # =====================================================================
    meses_labels = []
    receitas_mensal = []
    despesas_mensal = []
    
    nomes_meses = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
                   'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    
    for i in range(5, -1, -1):
        # Calcula mês
        mes_ref = hoje.month - i
        ano_ref = hoje.year
        while mes_ref <= 0:
            mes_ref += 12
            ano_ref -= 1
        
        meses_labels.append(nomes_meses[mes_ref])
        
        # Início e fim do mês
        inicio_ref = date(ano_ref, mes_ref, 1)
        if mes_ref == 12:
            fim_ref = date(ano_ref + 1, 1, 1) - timedelta(days=1)
        else:
            fim_ref = date(ano_ref, mes_ref + 1, 1) - timedelta(days=1)
        
        # Receitas do mês
        rec = ContaReceber.objects.filter(
            status__in=['recebido', 'quitado'],
            data_recebimento__gte=inicio_ref,
            data_recebimento__lte=fim_ref
        ).aggregate(total=Sum('valor_recebido'))['total'] or Decimal('0')
        
        if rec == 0:
            rec = NotaFiscalSaida.objects.filter(
                status='confirmada',
                data_emissao__gte=inicio_ref,
                data_emissao__lte=fim_ref
            ).aggregate(total=Sum('valor_total'))['total'] or Decimal('0')
        
        # Despesas do mês
        desp = ContaPagar.objects.filter(
            status__in=['pago', 'quitado'],
            data_pagamento__gte=inicio_ref,
            data_pagamento__lte=fim_ref
        ).aggregate(total=Sum('valor_pago'))['total'] or Decimal('0')
        
        if desp == 0:
            desp = NotaFiscalEntrada.objects.filter(
                status='confirmada',
                data_entrada__gte=inicio_ref,
                data_entrada__lte=fim_ref
            ).aggregate(total=Sum('valor_total'))['total'] or Decimal('0')
        
        receitas_mensal.append(float(rec))
        despesas_mensal.append(float(desp))
    
    # =====================================================================
    # TOP CATEGORIAS DE DESPESA
    # =====================================================================
    top_categorias = []
    
    # Tenta pegar de ContaPagar com categoria
    categorias_raw = ContaPagar.objects.filter(
        status__in=['pago', 'quitado'],
        data_pagamento__gte=inicio_mes - timedelta(days=90),
        categoria__isnull=False
    ).values(
        'categoria__nome'
    ).annotate(
        total=Sum('valor_pago')
    ).order_by('-total')[:5]
    
    if categorias_raw:
        max_valor = float(categorias_raw[0]['total']) if categorias_raw else 1
        for cat in categorias_raw:
            top_categorias.append({
                'nome': cat['categoria__nome'],
                'valor': float(cat['total']),
                'percentual': round(float(cat['total']) / max_valor * 100) if max_valor > 0 else 0
            })
    
    # Se não tem categorias, usa dados das NFs de entrada por fornecedor
    if not top_categorias:
        fornecedores_raw = NotaFiscalEntrada.objects.filter(
            status='confirmada',
            data_entrada__gte=inicio_mes - timedelta(days=90)
        ).values(
            'fornecedor__nome_razao_social'
        ).annotate(
            total=Sum('valor_total')
        ).order_by('-total')[:5]
        
        max_valor = float(fornecedores_raw[0]['total']) if fornecedores_raw else 1
        for f in fornecedores_raw:
            top_categorias.append({
                'nome': f['fornecedor__nome_razao_social'][:25],
                'valor': float(f['total']),
                'percentual': round(float(f['total']) / max_valor * 100) if max_valor > 0 else 0
            })
    
    # =====================================================================
    # DESPESAS POR CATEGORIA (para gráfico donut)
    # =====================================================================
    despesas_categorias = []
    cores_donut = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6']
    
    if top_categorias:
        for i, cat in enumerate(top_categorias):
            despesas_categorias.append({
                'nome': cat['nome'],
                'valor': cat['valor'],
                'cor': cores_donut[i % len(cores_donut)]
            })
    
    # =====================================================================
    # MOVIMENTAÇÕES RECENTES
    # =====================================================================
    movimentacoes_recentes = []
    
    # Contas pagas recentemente
    for cp in ContaPagar.objects.filter(
        status__in=['pago', 'quitado']
    ).select_related('fornecedor', 'categoria').order_by('-data_pagamento')[:5]:
        movimentacoes_recentes.append({
            'data': cp.data_pagamento.isoformat() if cp.data_pagamento else '',
            'descricao': cp.descricao[:50],
            'categoria': cp.categoria.nome if cp.categoria else 'Despesa',
            'tipo': 'despesa',
            'valor': float(cp.valor_pago or cp.valor_original),
            'status': cp.get_status_display(),
        })
    
    # Contas recebidas recentemente
    for cr in ContaReceber.objects.filter(
        status__in=['recebido', 'quitado']
    ).select_related('cliente', 'categoria').order_by('-data_recebimento')[:5]:
        movimentacoes_recentes.append({
            'data': cr.data_recebimento.isoformat() if cr.data_recebimento else '',
            'descricao': cr.descricao[:50],
            'categoria': cr.categoria.nome if cr.categoria else 'Receita',
            'tipo': 'receita',
            'valor': float(cr.valor_recebido or cr.valor_original),
            'status': cr.get_status_display(),
        })
    
    # Ordena por data mais recente
    movimentacoes_recentes.sort(key=lambda x: x['data'], reverse=True)
    movimentacoes_recentes = movimentacoes_recentes[:10]
    
    # =====================================================================
    # CONTEXTO FINAL
    # =====================================================================
    import json as json_module
    
    context = {
        # Contadores gerais
        'total_clientes': Cliente.objects.filter(ativo=True).count(),
        'total_fornecedores': Fornecedor.objects.filter(ativo=True).count(),
        'total_produtos': Produto.objects.filter(ativo=True).count(),
        'pedidos_pendentes': PedidoCompra.objects.filter(status='pendente_entrega').count(),
        'pedidos_pendentes_aprovacao': pedidos_pendentes_aprovacao,
        'nivel_aprovacao_usuario': nivel_usuario,
        'vendas_pendentes': PedidoVenda.objects.filter(status='pendente').count(),
        'contas_vencer': ContaReceber.objects.filter(status__in=['pendente', 'aberto']).count(),
        'contas_pagar_vencer': ContaPagar.objects.filter(status__in=['pendente', 'aberto']).count(),
        'valor_pedidos_abertos': PedidoCompra.objects.filter(
            status__in=['pendente_entrega', 'aprovado', 'em_aprovacao']
        ).aggregate(total=Sum('valor_total'))['total'] or 0,
        'valor_vendas_aberto': PedidoVenda.objects.filter(
            status__in=['pendente', 'aprovado']
        ).aggregate(total=Sum('valor_total'))['total'] or 0,
        
        # Dados financeiros
        'total_receitas': float(receitas_mes),
        'total_despesas': float(despesas_mes),
        'saldo_liquido': float(saldo_liquido),
        'saldo_previsto': float(saldo_previsto),
        'contas_receber_pendentes': float(contas_receber_pendentes),
        'contas_pagar_pendentes': float(contas_pagar_pendentes),
        
        # Trends
        'trend_receitas': trend_receitas,
        'trend_despesas': trend_despesas,
        
        # Dados para gráficos (JSON safe)
        'meses_labels': json_module.dumps(meses_labels),
        'receitas_mensal': json_module.dumps(receitas_mensal),
        'despesas_mensal': json_module.dumps(despesas_mensal),
        
        # Top categorias e movimentações
        'top_categorias': top_categorias,
        'despesas_categorias': json_module.dumps(despesas_categorias),
        'movimentacoes_recentes': json_module.dumps(movimentacoes_recentes),
    }
    return render(request, 'dashboard_novo.html', context)
# =============================================================================
# PARTE 2: MÓDULO CADASTRO
# =============================================================================

# -----------------------------------------------------------------------------
# CADASTRO - CLIENTES
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# CADASTRO - FORNECEDORES
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# CADASTRO - VENDEDORES
# -----------------------------------------------------------------------------

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

    comissao_media = vendedores_list.filter(ativo=True).aggregate(
        media=Avg('comissao_padrao')
    )['media'] or 0

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
        'comissao_media': round(comissao_media, 2),
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

# -----------------------------------------------------------------------------
# CADASTRO - EMPRESAS
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# CADASTRO - PRODUTOS
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# CADASTRO - CATEGORIA DE PRODUTO (APIs AJAX)
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# CADASTRO - CONDIÇÃO DE PAGAMENTO (APIs)
# -----------------------------------------------------------------------------

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

# Aliases para compatibilidade
condicao_pagamento_criar_api = api_condicao_pagamento_criar
condicao_pagamento_excluir_api = api_condicao_pagamento_excluir

# -----------------------------------------------------------------------------
# CADASTRO - FORMA DE PAGAMENTO (APIs)
# -----------------------------------------------------------------------------

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
# PARTE 3: COMPRAS - COTAÇÕES
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
        em_andamento=Count('id', filter=Q(status__in=['rascunho', 'enviada'])),
        respondidas=Count('id', filter=Q(status='respondida')),
        concluidas=Count('id', filter=Q(status='concluida'))
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

# -----------------------------------------------------------------------------
# APIs DE COTAÇÃO
# -----------------------------------------------------------------------------

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

            # ✅ CORREÇÃO: Status minúsculo
            status_enviado = data.get('status', 'rascunho').lower()
            if status_enviado in ['rascunho', 'enviada', 'respondida', 'em_analise', 'concluida', 'cancelada']:
                cotacao.status = status_enviado
            else:
                cotacao.status = 'rascunho'
            
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
    """
    API para buscar dados completos da cotação.
    CORREÇÃO: Não usa .values() para evitar problemas com @property
    """
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        
        # CORREÇÃO PRINCIPAL: Iterar objetos ao invés de usar .values()
        itens_list = []
        for item in cotacao.itens_solicitados.select_related('produto').all():
            try:
                descricao = item.descricao_display if item.descricao_display else (
                    item.descricao_manual or 'Item sem descrição'
                )
                
                itens_list.append({
                    'id': item.id,
                    'produto_id': item.produto_id,
                    'descricao_manual': item.descricao_manual or '',
                    'descricao_display': descricao,
                    'quantidade': float(item.quantidade) if item.quantidade else 0.0,
                    'unidade_medida': item.unidade_medida or 'UN',
                    'observacao': item.observacao or ''
                })
            except Exception as item_error:
                logger.warning(f"Erro ao processar item {item.id}: {str(item_error)}")
                continue
        
        fornecedores_ids = list(
            cotacao.cotacoes_fornecedor.values_list('fornecedor_id', flat=True)
        )
        
        data_limite = None
        if cotacao.data_limite_resposta:
            try:
                data_limite = cotacao.data_limite_resposta.isoformat()
            except (AttributeError, ValueError):
                data_limite = str(cotacao.data_limite_resposta)

        return JsonResponse({
            'success': True,
            'id': cotacao.id,
            'numero': cotacao.numero,
            'titulo': cotacao.titulo or '',
            'setor': cotacao.setor or '',
            'status': cotacao.status or 'rascunho',
            'data_limite': data_limite,
            'observacoes': cotacao.observacoes or '',
            'itens': itens_list,
            'fornecedores': fornecedores_ids,
        })
        
    except CotacaoMae.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Cotação não encontrada'
        }, status=404)
        
    except Exception as e:
        logger.error(f"Erro em cotacao_dados_api: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Erro ao buscar dados da cotação: {str(e)}'
        }, status=500)

@login_required
@require_GET
def cotacao_comparativo_api(request, pk):
    """
    API CORRIGIDA para buscar dados do comparativo de preços.
    """
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
 
        cotacoes_forn = list(
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
 
        # Coletar TODOS os itens únicos
        itens_unificados = []
        itens_por_sol_id = {}
        itens_por_desc = {}
 
        # Itens solicitados (fonte primária)
        for item_sol in cotacao.itens_solicitados.select_related('produto').all():
            idx = len(itens_unificados)
            desc = item_sol.descricao_display or ''
            desc_norm = _normalizar_para_match(desc)
 
            itens_unificados.append({
                'id': f'sol_{item_sol.id}',
                'item_solicitado_id': item_sol.id,
                'nome': desc,
                'quantidade': float(item_sol.quantidade),
                'unidade': item_sol.unidade_medida or 'UN',
            })
            itens_por_sol_id[item_sol.id] = idx
            if desc_norm:
                itens_por_desc[desc_norm] = idx
 
        # Itens importados órfãos
        for cf in cotacoes_forn:
            for item_cot in getattr(cf, 'itens_pre_carregados', []):
                if item_cot.item_solicitado_id and item_cot.item_solicitado_id in itens_por_sol_id:
                    continue
 
                desc = item_cot.descricao_fornecedor or ''
                desc_norm = _normalizar_para_match(desc)
                if not desc_norm:
                    continue
 
                if desc_norm in itens_por_desc:
                    continue
 
                encontrou = False
                for existing_desc in itens_por_desc:
                    if existing_desc in desc_norm or desc_norm in existing_desc:
                        encontrou = True
                        break
 
                if not encontrou:
                    palavras_novo = {p for p in desc_norm.split() if len(p) > 2}
                    for existing_desc in itens_por_desc:
                        palavras_exist = {p for p in existing_desc.split() if len(p) > 2}
                        if len(palavras_novo & palavras_exist) >= 2:
                            encontrou = True
                            break
 
                if encontrou:
                    continue
 
                idx = len(itens_unificados)
                itens_unificados.append({
                    'id': f'orf_{item_cot.id}',
                    'item_solicitado_id': None,
                    'nome': desc,
                    'quantidade': float(item_cot.quantidade or 1),
                    'unidade': item_cot.unidade_medida or 'UN',
                })
                itens_por_desc[desc_norm] = idx
 
        # Montar lista de fornecedores com resumo
        fornecedores_list = []
        total_itens_base = len(itens_unificados) or 1
 
        for cf in cotacoes_forn:
            nome = cf.fornecedor.nome_fantasia or cf.fornecedor.nome_razao_social
            itens_cotados = sum(
                1 for i in getattr(cf, 'itens_pre_carregados', [])
                if i.disponivel and i.preco_unitario and i.preco_unitario > 0
            )
            pct = round((itens_cotados / total_itens_base) * 100)
 
            fornecedores_list.append({
                'id': cf.id,
                'fornecedor_id': cf.fornecedor_id,
                'nome': nome,
                'contato': cf.contato_nome or '',
                'email': cf.contato_email or '',
                'telefone': cf.contato_telefone or '',
                'valor_total_bruto': float(cf.valor_total_bruto or 0),
                'percentual_desconto': float(cf.percentual_desconto or 0),
                'valor_frete': float(cf.valor_frete or 0),
                'valor_total_liquido': float(cf.valor_total_liquido or 0),
                'condicao_pagamento': cf.condicao_pagamento or 'À vista',
                'forma_pagamento': cf.forma_pagamento or '',
                'prazo_entrega_dias': cf.prazo_entrega_dias or 0,
                'disponibilidade': f'{pct}%',
                'disponibilidade_pct': pct,
                'nota_confiabilidade': cf.nota_confiabilidade or 5,
                'total_itens_cotados': itens_cotados,
                'status': cf.status,
            })
 
        # Cruzar itens × fornecedores
        respostas = {cf.id: {} for cf in cotacoes_forn}
 
        lookup_por_sol = {}
        lookup_por_desc = {}
 
        for cf in cotacoes_forn:
            for item_cot in getattr(cf, 'itens_pre_carregados', []):
                if item_cot.item_solicitado_id:
                    lookup_por_sol[(cf.id, item_cot.item_solicitado_id)] = item_cot
                dn = _normalizar_para_match(item_cot.descricao_fornecedor or '')
                if dn:
                    lookup_por_desc[(cf.id, dn)] = item_cot
 
        for item in itens_unificados:
            sol_id = item.get('item_solicitado_id')
            item_desc_norm = _normalizar_para_match(item['nome'])
 
            for cf in cotacoes_forn:
                item_cot = None
 
                # Match 1: por item_solicitado_id
                if sol_id:
                    item_cot = lookup_por_sol.get((cf.id, sol_id))
 
                # Match 2: por descrição exata
                if not item_cot and item_desc_norm:
                    item_cot = lookup_por_desc.get((cf.id, item_desc_norm))
 
                # Match 3: descrição parcial
                if not item_cot and item_desc_norm:
                    for (cf_key, desc_key), ic in lookup_por_desc.items():
                        if cf_key == cf.id:
                            if desc_key in item_desc_norm or item_desc_norm in desc_key:
                                item_cot = ic
                                break
 
                # Match 4: palavras em comum
                if not item_cot and item_desc_norm:
                    palavras_item = {p for p in item_desc_norm.split() if len(p) > 2}
                    melhor_score = 0
                    melhor_ic = None
                    for (cf_key, desc_key), ic in lookup_por_desc.items():
                        if cf_key == cf.id:
                            palavras_forn = {p for p in desc_key.split() if len(p) > 2}
                            comuns = len(palavras_item & palavras_forn)
                            if comuns >= 2 and comuns > melhor_score:
                                melhor_score = comuns
                                melhor_ic = ic
                    item_cot = melhor_ic
 
                # Montar resposta
                if item_cot and item_cot.disponivel and item_cot.preco_unitario and item_cot.preco_unitario > 0:
                    prazo = item_cot.prazo_entrega_item or cf.prazo_entrega_dias or 0
                    respostas[cf.id][item['id']] = {
                        'item_cotacao_id': item_cot.id,
                        'preco_unitario': float(item_cot.preco_unitario),
                        'preco_total': float(item_cot.preco_total or 0),
                        'descricao_fornecedor': item_cot.descricao_fornecedor or '',
                        'disponivel': True,
                        'prazo': prazo,
                        'melhor_preco': False,
                        'melhor_prazo': False,
                        'selecionado': item_cot.selecionado,
                        'sugerido': item_cot.sugerido,
                    }
                elif item_cot and not item_cot.disponivel:
                    respostas[cf.id][item['id']] = {
                        'item_cotacao_id': item_cot.id,
                        'preco_unitario': 0,
                        'preco_total': 0,
                        'descricao_fornecedor': item_cot.descricao_fornecedor or '',
                        'disponivel': False,
                        'prazo': 0,
                        'melhor_preco': False,
                        'melhor_prazo': False,
                        'selecionado': False,
                        'sugerido': False,
                    }
 
        # Calcular melhor preço / prazo por item
        for item in itens_unificados:
            precos = []
            prazos = []
            for cf in cotacoes_forn:
                r = respostas[cf.id].get(item['id'])
                if r and r['disponivel'] and r['preco_unitario'] > 0:
                    precos.append((cf.id, r['preco_unitario']))
                    if r.get('prazo') and r['prazo'] > 0:
                        prazos.append((cf.id, r['prazo']))
 
            if precos:
                menor_cf = min(precos, key=lambda x: x[1])[0]
                respostas[menor_cf][item['id']]['melhor_preco'] = True
 
            if prazos:
                menor_prazo_cf = min(prazos, key=lambda x: x[1])[0]
                respostas[menor_prazo_cf][item['id']]['melhor_prazo'] = True
 
        # Menor total líquido global
        menor_total_id = None
        forn_com_valor = [f for f in fornecedores_list if f['valor_total_liquido'] > 0]
        if forn_com_valor:
            menor_total_id = min(forn_com_valor, key=lambda f: f['valor_total_liquido'])['id']
 
        return JsonResponse({
            'success': True,
            'itens': itens_unificados,
            'fornecedores': fornecedores_list,
            'respostas': respostas,
            'menor_total_id': menor_total_id,
        })
 
    except Exception as e:
        log_erro_seguro('cotacao_comparativo_api', e, request, {'cotacao_id': pk})
        return resposta_erro_segura('Erro ao gerar comparativo', 500)

def _normalizar_para_match(texto):
    """Normaliza texto para matching no comparativo."""
    if not texto:
        return ''
    texto = str(texto).lower().strip()
    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    return ' '.join(texto.split())

# -----------------------------------------------------------------------------
# APIs DE AÇÃO - COTAÇÕES
# -----------------------------------------------------------------------------

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
        # ✅ CORREÇÃO: Status minúsculo
        cotacao.status = 'enviada'
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
        # ✅ CORREÇÃO: Status minúsculo
        cotacao.status = 'concluida'
        cotacao.save()
        return JsonResponse({'success': True, 'message': 'Cotação concluída!'})
    except Exception as e:
        log_erro_seguro('cotacao_concluir_api', e, request, {'cotacao_id': pk})
        return resposta_erro_segura('Erro ao concluir cotação', 500)

# -----------------------------------------------------------------------------
# IMPORTAÇÃO DE ARQUIVOS DE COTAÇÃO
# -----------------------------------------------------------------------------

@login_required
@require_POST
def cotacao_importar_fornecedor(request, pk):
    """
    Importa arquivo de cotação do fornecedor (CSV/Excel/PDF).
    """
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)

        fornecedor_id = request.POST.get('fornecedor_id')
        arquivo = request.FILES.get('arquivo')

        if not fornecedor_id:
            return resposta_erro_segura('Selecione um fornecedor', 400)
        if not arquivo:
            return resposta_erro_segura('Selecione um arquivo', 400)

        nome_arquivo = arquivo.name.lower()

        extensoes_permitidas = ('.csv', '.xlsx', '.xls', '.pdf')
        if not nome_arquivo.endswith(extensoes_permitidas):
            return resposta_erro_segura(
                'Apenas arquivos CSV, Excel ou PDF são permitidos', 400
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
                processar_arquivo_cotacao_seguro(cotacao, cotacao_forn, arquivo)
                sincronizar_itens_cotacao(cotacao)
                cotacao_forn.calcular_total()
            except Exception as e:
                log_erro_seguro('processar_arquivo_cotacao', e, request, {
                    'arquivo': nome_arquivo,
                    'fornecedor_id': fornecedor_id
                })
                return resposta_erro_segura(
                    'Erro ao processar arquivo. Verifique o formato.', 400
                )

        try:
            cotacao_forn.prazo_entrega_dias = int(
                request.POST.get('prazo_entrega', 0) or 0
            )
        except (ValueError, TypeError):
            cotacao_forn.prazo_entrega_dias = 0

        cotacao_forn.condicao_pagamento = request.POST.get(
            'condicao_pagamento', ''
        )[:100]
        cotacao_forn.forma_pagamento = request.POST.get(
            'forma_pagamento', ''
        )[:100]

        try:
            cotacao_forn.percentual_desconto = Decimal(
                request.POST.get('desconto', 0) or 0
            )
        except (InvalidOperation, ValueError):
            cotacao_forn.percentual_desconto = Decimal('0')

        try:
            cotacao_forn.valor_frete = Decimal(
                request.POST.get('frete', 0) or 0
            )
        except (InvalidOperation, ValueError):
            cotacao_forn.valor_frete = Decimal('0')

        try:
            cotacao_forn.nota_confiabilidade = int(
                request.POST.get('confiabilidade', 5) or 5
            )
        except (ValueError, TypeError):
            cotacao_forn.nota_confiabilidade = 5

        cotacao_forn.observacoes = request.POST.get('observacoes', '')[:1000]
        # ✅ CORREÇÃO: Status minúsculo
        cotacao_forn.status = 'processada'
        cotacao_forn.save()
        cotacao_forn.calcular_total()

        # ✅ CORREÇÃO: Status minúsculo
        cotacao.status = 'respondida'
        cotacao.save()

        return JsonResponse({
            'success': True,
            'cotacao_fornecedor_id': cotacao_forn.pk,
            'fornecedor_nome': (
                fornecedor.nome_fantasia or fornecedor.nome_razao_social
            ),
            'total_itens': cotacao_forn.itens.count(),
            'valor_total': float(cotacao_forn.valor_total_liquido or 0),
            'message': 'Cotação importada com sucesso!'
        })
    except Exception as e:
        log_erro_seguro(
            'cotacao_importar_fornecedor', e, request, {'cotacao_id': pk}
        )
        return resposta_erro_segura('Erro ao importar cotação', 500)

# -----------------------------------------------------------------------------
# SINCRONIZAÇÃO DE ITENS
# -----------------------------------------------------------------------------

def sincronizar_itens_cotacao(cotacao_mae):
    """
    Função principal que garante que TODOS os itens importados estejam vinculados.
    """
    logger.info(f"Sincronizando itens da cotação {cotacao_mae.id}")
    
    todos_itens_forn = ItemCotacaoFornecedor.objects.filter(
        cotacao_fornecedor__cotacao_mae=cotacao_mae,
        item_solicitado__isnull=True
    ).select_related('cotacao_fornecedor__fornecedor')
 
    descricoes_unicas = {}
    for item_cf in todos_itens_forn:
        desc = (item_cf.descricao_fornecedor or '').strip()
        if not desc:
            continue
        desc_normalizada = normalizar_texto(desc)
        if desc_normalizada not in descricoes_unicas:
            descricoes_unicas[desc_normalizada] = []
        descricoes_unicas[desc_normalizada].append(item_cf)
    
    if not descricoes_unicas:
        logger.info("Nenhum item órfão para processar")
        return
 
    logger.info(f"Processando {len(descricoes_unicas)} descrições únicas")
 
    itens_solicitados = list(
        cotacao_mae.itens_solicitados.select_related('produto').all()
    )
 
    idx_por_desc = {}
    for item_sol in itens_solicitados:
        desc = normalizar_texto(item_sol.descricao_display)
        idx_por_desc[desc] = item_sol
 
    vinculacoes = []
 
    for desc_normalizada, itens_cf_list in descricoes_unicas.items():
        item_sol_encontrado = _encontrar_item_solicitado(
            desc_normalizada, idx_por_desc, itens_solicitados
        )
 
        if item_sol_encontrado:
            for icf in itens_cf_list:
                vinculacoes.append((icf.id, item_sol_encontrado, 80))
        else:
            primeiro = itens_cf_list[0]
            forn_nome = (
                primeiro.cotacao_fornecedor.fornecedor.nome_fantasia or 
                primeiro.cotacao_fornecedor.fornecedor.nome_razao_social
            )
            
            try:
                novo_item = ItemSolicitado.objects.create(
                    cotacao_mae=cotacao_mae,
                    produto=None,
                    descricao_manual=primeiro.descricao_fornecedor[:500],
                    quantidade=primeiro.quantidade or Decimal('1'),
                    unidade_medida=primeiro.unidade_medida or 'UN',
                    observacao=f'Auto-criado da importação de {forn_nome}'
                )
                
                idx_por_desc[desc_normalizada] = novo_item
                itens_solicitados.append(novo_item)
                
                for icf in itens_cf_list:
                    vinculacoes.append((icf.id, novo_item, 50))
                    
                logger.info(f"Criado novo ItemSolicitado: {novo_item.descricao_display}")
                
            except Exception as e:
                logger.error(f"Erro ao criar ItemSolicitado: {e}")
                continue
 
    if vinculacoes:
        try:
            for item_cf_id, item_sol, score in vinculacoes:
                ItemCotacaoFornecedor.objects.filter(id=item_cf_id).update(
                    item_solicitado=item_sol,
                    match_automatico=True,
                    match_score=score
                )
            logger.info(f"Vinculados {len(vinculacoes)} itens")
        except Exception as e:
            logger.error(f"Erro ao vincular itens: {e}")
 
    orfaos_restantes = ItemCotacaoFornecedor.objects.filter(
        cotacao_fornecedor__cotacao_mae=cotacao_mae,
        item_solicitado__isnull=True
    )
 
    if orfaos_restantes.exists():
        logger.info(f"Tentando vincular {orfaos_restantes.count()} órfãos restantes")
        
        for orfao in orfaos_restantes:
            desc = normalizar_texto(orfao.descricao_fornecedor or '')
            if not desc:
                continue
 
            item_sol = _encontrar_item_solicitado(desc, idx_por_desc, itens_solicitados)
            if item_sol:
                orfao.item_solicitado = item_sol
                orfao.match_automatico = True
                orfao.match_score = 60
                orfao.save(update_fields=[
                    'item_solicitado', 'match_automatico', 'match_score'
                ])
 
    if hasattr(cotacao_mae, '_itens_solicitados_cache'):
        delattr(cotacao_mae, '_itens_solicitados_cache')
    
    total_vinculados = ItemCotacaoFornecedor.objects.filter(
        cotacao_fornecedor__cotacao_mae=cotacao_mae,
        item_solicitado__isnull=False
    ).count()
    logger.info(f"Sincronização finalizada. Total vinculados: {total_vinculados}")

def _encontrar_item_solicitado(desc_lower, idx_por_desc, itens_solicitados):
    """
    Tenta encontrar um ItemSolicitado que corresponda à descrição.
    """
    if desc_lower in idx_por_desc:
        return idx_por_desc[desc_lower]
 
    for desc_sol, item_sol in idx_por_desc.items():
        if desc_sol in desc_lower or desc_lower in desc_sol:
            return item_sol
 
    palavras_desc = {p for p in desc_lower.split() if len(p) > 2}
    melhor_match = None
    melhor_score = 0
 
    for item_sol in itens_solicitados:
        desc_sol = normalizar_texto(item_sol.descricao_display)
        palavras_sol = {p for p in desc_sol.split() if len(p) > 2}
        comuns = palavras_desc & palavras_sol
 
        if len(comuns) >= 2:
            score = len(comuns) / max(len(palavras_desc), len(palavras_sol), 1)
            if score > melhor_score and score >= 0.3:
                melhor_score = score
                melhor_match = item_sol
 
    return melhor_match

# -----------------------------------------------------------------------------
# PROCESSAMENTO DE ARQUIVOS (CSV/Excel/PDF)
# -----------------------------------------------------------------------------

def processar_arquivo_cotacao_seguro(cotacao_mae, cotacao_forn, arquivo):
    """Processa arquivo de cotação (CSV, Excel ou PDF)."""
    nome_arquivo = arquivo.name.lower()
 
    cotacao_forn.itens.all().delete()
 
    if hasattr(cotacao_mae, '_itens_solicitados_cache'):
        delattr(cotacao_mae, '_itens_solicitados_cache')
 
    if nome_arquivo.endswith('.csv'):
        processar_csv_seguro(cotacao_mae, cotacao_forn, arquivo)
    elif nome_arquivo.endswith(('.xlsx', '.xls')):
        processar_excel_seguro(cotacao_mae, cotacao_forn, arquivo)
    elif nome_arquivo.endswith('.pdf'):
        processar_pdf_seguro(cotacao_mae, cotacao_forn, arquivo)


def processar_csv_seguro(cotacao_mae, cotacao_forn, arquivo):
    """Processa arquivo CSV com detecção automática de delimitador."""
    try:
        conteudo = arquivo.read().decode('utf-8-sig')
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
        
        primeira_linha_idx = 1
        for idx, row in enumerate(ws.iter_rows(min_row=1, max_row=10, values_only=True), start=1):
            if any(cell is not None and str(cell).strip() != '' for cell in row):
                primeira_linha_idx = idx
                break
        
        headers = [normalizar_nome_coluna(str(cell.value or '')) for cell in ws[primeira_linha_idx]]

        itens_criar = []
        for i, row in enumerate(ws.iter_rows(min_row=primeira_linha_idx + 1, values_only=True), start=1):
            if i > 1000:
                break
            
            if not any(cell is not None and str(cell).strip() != '' for cell in row):
                continue
            
            row_dict = {}
            for j, (header, value) in enumerate(zip(headers, row)):
                if isinstance(value, (int, float)):
                    row_dict[header] = value
                elif value is not None:
                    row_dict[header] = str(value).strip()
                else:
                    row_dict[header] = ''
            
            item = criar_item_cotacao_seguro(cotacao_mae, cotacao_forn, row_dict)
            if item:
                itens_criar.append(item)

        if itens_criar:
            ItemCotacaoFornecedor.objects.bulk_create(itens_criar, batch_size=100)
        wb.close()

    except ImportError:
        import pandas as pd
        df = pd.read_excel(arquivo, header=None)
        
        header_row = 0
        for idx, row in df.iterrows():
            if idx > 10:
                break
            row_str = ' '.join([str(x) for x in row if pd.notna(x)])
            if any(term in row_str.lower() for term in ['produto', 'descricao', 'item', 'preco', 'valor']):
                header_row = idx
                break
        
        df = pd.read_excel(arquivo, header=header_row)
        itens_criar = []
        for i, (_, row) in enumerate(df.iterrows(), start=1):
            if i > 1000:
                break
            
            row_dict = {}
            for k, v in row.items():
                key_norm = normalizar_nome_coluna(str(k))
                if pd.isna(v):
                    row_dict[key_norm] = ''
                elif isinstance(v, (int, float)):
                    row_dict[key_norm] = v
                else:
                    row_dict[key_norm] = str(v).strip()
            
            item = criar_item_cotacao_seguro(cotacao_mae, cotacao_forn, row_dict)
            if item:
                itens_criar.append(item)
        
        if itens_criar:
            ItemCotacaoFornecedor.objects.bulk_create(itens_criar, batch_size=100)

def processar_pdf_seguro(cotacao_mae, cotacao_forn, arquivo):
    """
    Processa arquivo PDF extraindo tabelas de cotação.
    """
    import tempfile
    import os
 
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        for chunk in arquivo.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name
 
    itens_criar = []
 
    try:
        try:
            import pdfplumber
 
            with pdfplumber.open(tmp_path) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        if not table or len(table) < 2:
                            continue
 
                        headers = [
                            normalizar_nome_coluna(str(h or ''))
                            for h in table[0]
                        ]
 
                        for row_values in table[1:]:
                            if not row_values or all(
                                not v or str(v).strip() == ''
                                for v in row_values
                            ):
                                continue
                            row_dict = dict(zip(headers, row_values))
                            item = criar_item_cotacao_seguro(
                                cotacao_mae, cotacao_forn, row_dict
                            )
                            if item:
                                itens_criar.append(item)
 
                if not itens_criar:
                    for page in pdf.pages:
                        texto = page.extract_text() or ''
                        itens_criar.extend(
                            _extrair_itens_de_texto_bruto(
                                texto, cotacao_mae, cotacao_forn
                            )
                        )
 
            if itens_criar:
                ItemCotacaoFornecedor.objects.bulk_create(
                    itens_criar, batch_size=100
                )
                return
 
        except ImportError:
            logger.info("pdfplumber não disponível, tentando alternativa")
 
        try:
            import tabula
            dfs = tabula.read_pdf(
                tmp_path, pages='all', multiple_tables=True,
                lattice=True, pandas_options={'header': 0}
            )
            if not dfs:
                dfs = tabula.read_pdf(
                    tmp_path, pages='all', multiple_tables=True,
                    stream=True, pandas_options={'header': 0}
                )
            for df in dfs:
                if df.empty:
                    continue
                for _, row in df.iterrows():
                    row_dict = {
                        normalizar_nome_coluna(str(k)): v
                        for k, v in row.items()
                    }
                    item = criar_item_cotacao_seguro(
                        cotacao_mae, cotacao_forn, row_dict
                    )
                    if item:
                        itens_criar.append(item)
 
            if itens_criar:
                ItemCotacaoFornecedor.objects.bulk_create(
                    itens_criar, batch_size=100
                )
                return
        except ImportError:
            pass
 
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(tmp_path)
            texto = ''
            for page in reader.pages:
                texto += (page.extract_text() or '') + '\n'
            itens_criar = _extrair_itens_de_texto_bruto(
                texto, cotacao_mae, cotacao_forn
            )
        except ImportError:
            raise ValueError(
                "Nenhuma biblioteca de PDF disponível. "
                "Instale: pip install pdfplumber"
            )
 
        if itens_criar:
            ItemCotacaoFornecedor.objects.bulk_create(
                itens_criar, batch_size=100
            )
 
        if not itens_criar:
            raise ValueError(
                "Não foi possível extrair itens do PDF. "
                "Verifique se contém tabela com descrição, quantidade e preço."
            )
 
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

def _extrair_itens_de_texto_bruto(texto, cotacao_mae, cotacao_forn):
    """Extrai itens de texto bruto usando regex."""
    itens_criar = []
    linhas = texto.strip().split('\n')
 
    padrao1 = re.compile(
        r'^\s*\d+\s+'
        r'(.+?)\s+'
        r'(UN|PC|KG|CX|LT|MT|M2|M3|PCT|PAR|JG|RL|FD|SC|GL|FR|TB|CT|DZ|MIL)\s+'
        r'([\d.,]+)\s+'
        r'R?\$?\s*([\d.,]+)',
        re.IGNORECASE
    )
 
    padrao2 = re.compile(
        r'^(.{5,60}?)\s+'
        r'([\d.,]+)\s+'
        r'R?\$?\s*([\d.,]+)\s*$',
        re.IGNORECASE
    )
 
    ignorar = [
        'descricao', 'produto', 'item', 'total', 'subtotal',
        'frete', 'desconto', 'observa', 'condic', 'pagamento',
        '---', '===', 'cotacao', 'orcamento', 'proposta',
        'cnpj', 'razao', 'endereco', 'telefone', 'email',
        'validade', 'prazo'
    ]
 
    for linha in linhas:
        linha = linha.strip()
        if not linha or len(linha) < 5:
            continue
 
        linha_lower = linha.lower()
        if any(h in linha_lower for h in ignorar):
            continue
 
        match = padrao1.match(linha)
        if match:
            descricao = match.group(1).strip()
            unidade = match.group(2).upper()
            quantidade_str = match.group(3)
            preco_str = match.group(4)
        else:
            match = padrao2.match(linha)
            if match:
                descricao = match.group(1).strip()
                unidade = 'UN'
                quantidade_str = match.group(2)
                preco_str = match.group(3)
            else:
                continue
 
        try:
            quantidade = Decimal(
                quantidade_str.replace('.', '').replace(',', '.')
            )
            if quantidade <= 0 or quantidade > 999999:
                continue
        except (InvalidOperation, ValueError):
            continue
 
        try:
            preco_unitario = Decimal(
                preco_str.replace('.', '').replace(',', '.')
            )
            if preco_unitario <= 0 or preco_unitario > 999999999:
                continue
        except (InvalidOperation, ValueError):
            continue
 
        if descricao.replace(' ', '').replace('.', '').replace(',', '').isdigit():
            continue
 
        row_dict = {
            'descricao': descricao,
            'unidade': unidade,
            'quantidade': str(quantidade),
            'preco_unitario': str(preco_unitario),
        }
        item = criar_item_cotacao_seguro(cotacao_mae, cotacao_forn, row_dict)
        if item:
            itens_criar.append(item)
 
    return itens_criar

# -----------------------------------------------------------------------------
# FUNÇÕES UTILITÁRIAS
# -----------------------------------------------------------------------------

def normalizar_texto(texto):
    """Normaliza texto para comparação: lowercase, sem acentos, espaços únicos"""
    if not texto:
        return ''
    texto = str(texto).lower().strip()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) 
                   if unicodedata.category(c) != 'Mn')
    return ' '.join(texto.split())

def normalizar_nome_coluna(nome):
    """Normaliza nome de coluna: lowercase, sem acentos, espaços→underscore."""
    import re
    
    nome = str(nome).lower().strip()
    nome = unicodedata.normalize('NFD', nome)
    nome = ''.join(c for c in nome if not unicodedata.combining(c))
    nome = re.sub(r'[^\w\s]', '', nome)
    nome = re.sub(r'\s+', '_', nome)
    nome = nome.strip('_')
    
    return nome

def criar_item_cotacao_seguro(cotacao_mae, cotacao_forn, row):
    """
    Cria item de cotação a partir de uma linha do arquivo.
    """
    # Extração de descrição
    descricao = ''
    for key in ['descricao', 'produto', 'item', 'material', 'nome', 
                'descricao_produto', 'servico', 'mercadoria', 'prod', 'desc']:
        if key in row and row[key]:
            descricao = str(row[key]).strip()
            if descricao:
                break
    
    if not descricao:
        for key, value in row.items():
            if value and str(value).strip() and len(str(value).strip()) > 3:
                key_lower = str(key).lower()
                if any(term in key_lower for term in ['preco', 'valor', 'qtd', 'quant', 'cod', 'unid']):
                    continue
                descricao = str(value).strip()
                break

    descricao = descricao[:500] if descricao else ''
    if not descricao:
        return None
 
    desc_lower_check = descricao.lower()
    ignorar = ('total', 'subtotal', 'frete', 'desconto', 'observacao', 
               'condicoes', 'pagamento', 'entrega')
    if any(p in desc_lower_check for p in ignorar):
        return None
 
    # Quantidade
    quantidade_str = str(
        row.get('quantidade') or row.get('qtd') or row.get('qtde') or 
        row.get('quant') or row.get('qty') or 1
    )
    try:
        qtd_str = str(quantidade_str).replace(' ', '')
        if ',' in qtd_str and '.' in qtd_str:
            if qtd_str.rfind(',') > qtd_str.rfind('.'):
                qtd_str = qtd_str.replace('.', '').replace(',', '.')
            else:
                qtd_str = qtd_str.replace(',', '')
        elif ',' in qtd_str:
            qtd_str = qtd_str.replace(',', '.')
        quantidade = Decimal(qtd_str)
        if quantidade <= 0 or quantidade > 999999:
            quantidade = Decimal('1')
    except (InvalidOperation, ValueError):
        quantidade = Decimal('1')
 
    # Preço unitário
    preco_str = None
    for key in ['preco_unitario', 'preco', 'valor_unitario', 'valor', 
                'unitario', 'vl_unitario', 'vlr_unitario', 'preco_un',
                'valor_un', 'p_unit', 'unit_price', 'preco_unit']:
        if key in row and row[key] is not None:
            preco_str = str(row[key])
            if preco_str and preco_str not in ('0', '0.0', '0,00', ''):
                break
    
    preco_str = preco_str or '0'
    
    try:
        preco_clean = preco_str.replace('R$', '').replace(' ', '')
        if ',' in preco_clean and '.' in preco_clean:
            if preco_clean.rfind(',') > preco_clean.rfind('.'):
                preco_clean = preco_clean.replace('.', '').replace(',', '.')
            else:
                preco_clean = preco_clean.replace(',', '')
        elif ',' in preco_clean:
            preco_clean = preco_clean.replace(',', '.')
        preco_unitario = Decimal(preco_clean)
        if preco_unitario < 0 or preco_unitario > 999999999:
            preco_unitario = Decimal('0')
    except (InvalidOperation, ValueError):
        preco_unitario = Decimal('0')
 
    codigo = str(
        row.get('codigo') or row.get('cod') or row.get('ref') or 
        row.get('sku') or ''
    )[:50]
    
    unidade = str(
        row.get('unidade') or row.get('un') or row.get('und') or 'UN'
    )[:10].upper()
 
    # Matching com ItemSolicitado existente
    item_solicitado = None
    match_score = 0
 
    if not hasattr(cotacao_mae, '_itens_solicitados_cache'):
        cotacao_mae._itens_solicitados_cache = list(
            cotacao_mae.itens_solicitados.select_related('produto').all()
        )
 
    descricao_lower = normalizar_texto(descricao)
 
    for item_sol in cotacao_mae._itens_solicitados_cache:
        desc_sol = normalizar_texto(item_sol.descricao_display)
 
        if desc_sol == descricao_lower:
            item_solicitado = item_sol
            match_score = 100
            break
 
        if item_sol.produto and codigo:
            cod_prod = (item_sol.produto.codigo or '').lower()
            if cod_prod and codigo.lower() in cod_prod:
                item_solicitado = item_sol
                match_score = 95
                break
 
        if desc_sol in descricao_lower or descricao_lower in desc_sol:
            if match_score < 80:
                item_solicitado = item_sol
                match_score = 80
 
        if match_score < 60:
            palavras_sol = {p for p in desc_sol.split() if len(p) > 2}
            palavras_desc = {p for p in descricao_lower.split() if len(p) > 2}
            comuns = palavras_sol & palavras_desc
            if len(comuns) >= 2:
                score = len(comuns) / max(len(palavras_sol), len(palavras_desc), 1)
                if score > 0.3 and match_score < 60:
                    item_solicitado = item_sol
                    match_score = int(score * 100)
 
    return ItemCotacaoFornecedor(
        cotacao_fornecedor=cotacao_forn,
        item_solicitado=item_solicitado,
        descricao_fornecedor=descricao,
        codigo_fornecedor=codigo,
        quantidade=quantidade,
        unidade_medida=unidade,
        preco_unitario=preco_unitario,
        preco_total=quantidade * preco_unitario,
        disponivel=preco_unitario > 0,
        match_automatico=(item_solicitado is not None),
        match_score=match_score
    )

# -----------------------------------------------------------------------------
# GERAÇÃO DE PEDIDOS A PARTIR DA COTAÇÃO
# -----------------------------------------------------------------------------

@login_required
@require_POST
def cotacao_gerar_pedidos(request, pk):
    """Gera pedidos de compra a partir dos itens selecionados."""
    logger.info(f"[DEBUG] cotacao_gerar_pedidos chamada para pk={pk}")
    
    try:
        if len(request.body) > 5 * 1024 * 1024:
            return resposta_erro_segura('Payload muito grande', 413)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            return resposta_erro_segura('JSON inválido', 400)

        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        pedidos_data = data.get('pedidos', [])
        
        if not pedidos_data:
            return resposta_erro_segura('Nenhum pedido para gerar', 400)

        pedidos_gerados = []

        with transaction.atomic():
            for idx, pedido_data in enumerate(pedidos_data[:50]):
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

                # ✅ Cria pedido com verificação automática de aprovação (FASE 2)
                pedido = PedidoCompra.objects.create(
                    fornecedor=fornecedor,
                    cotacao_mae=cotacao,
                    cotacao_fornecedor=cotacao_forn,
                    data_prevista_entrega=data_entrega,
                    condicao_pagamento=cotacao_forn.condicao_pagamento if cotacao_forn else '',
                    forma_pagamento=cotacao_forn.forma_pagamento if cotacao_forn else '',
                    observacoes=f'Gerado a partir da cotação {cotacao.numero}',
                    status='rascunho',  # Começa como rascunho, verificação acontece depois
                    solicitante=request.user,
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
                
                # ✅ FASE 2: Verifica se precisa de aprovação
                precisa_aprovacao, nivel_necessario = verificar_regras_aprovacao(pedido)
                if precisa_aprovacao:
                    pedido.nivel_aprovacao_necessario = nivel_necessario
                    pedido.status = 'em_aprovacao'
                    pedido.save(update_fields=['nivel_aprovacao_necessario', 'status'])
                else:
                    pedido.status = 'aprovado'
                    pedido.data_aprovacao = timezone.now()
                    pedido.save(update_fields=['status', 'data_aprovacao'])

                pedidos_gerados.append({
                    'id': pedido.pk,
                    'numero': pedido.numero,
                    'fornecedor': fornecedor.nome_fantasia or fornecedor.nome_razao_social,
                    'total_itens': len(itens_pedido),
                    'valor_total': float(pedido.valor_total),
                    'status': pedido.status,
                    'precisa_aprovacao': precisa_aprovacao
                })

            # ✅ CORREÇÃO: Status minúsculo
            if pedidos_gerados:
                cotacao.status = 'concluida'
                cotacao.save(update_fields=['status'])

        return JsonResponse({
            'success': True,
            'pedidos': pedidos_gerados,
            'message': f'{len(pedidos_gerados)} pedido(s) gerado(s) com sucesso!'
        })
        
    except Exception as e:
        logger.error(f"[DEBUG] EXCEÇÃO: {type(e).__name__}: {str(e)}", exc_info=True)
        log_erro_seguro('cotacao_gerar_pedidos', e, request, {'cotacao_id': pk})
        return resposta_erro_segura('Erro ao gerar pedidos', 500)

# -----------------------------------------------------------------------------
# OUTRAS APIs DE COTAÇÃO
# -----------------------------------------------------------------------------

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

        # ✅ CORREÇÃO: Status minúsculo
        cotacao.status = 'em_analise'
        cotacao.save(update_fields=['status'])
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

# -----------------------------------------------------------------------------
# FUNÇÕES DE TEXTO (EMAIL/WHATSAPP)
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# CONFIRMAÇÕES DE DELETE
# -----------------------------------------------------------------------------

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
# =============================================================================
# PARTE 4: COMPRAS - PEDIDOS E WORKFLOW DE APROVAÇÃO (FASE 2)
# =============================================================================

# -----------------------------------------------------------------------------
# VIEWS DE PEDIDOS DE COMPRA
# -----------------------------------------------------------------------------

@login_required
def pedido_compra_manager(request):
    """Manager unificado de pedidos de compra com filtros de aprovação"""
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    # FASE 2: Filtro de aprovação
    filtro_aprovacao = request.GET.get('filtro_aprovacao', '')

    pedidos = PedidoCompra.objects.select_related('fornecedor').order_by('-data_pedido')
    
    if search:
        pedidos = pedidos.filter(
            Q(numero__icontains=search) |
            Q(fornecedor__nome_razao_social__icontains=search)
        )
    if status:
        pedidos = pedidos.filter(status=status)
    
    # FASE 2: Filtros especiais de aprovação
    if filtro_aprovacao == 'minha_aprovacao':
        # Pedidos que o usuário logado pode aprovar
        nivel_usuario = get_nivel_aprovacao_usuario(request.user)
        pedidos = pedidos.filter(
            status='em_aprovacao',
            nivel_aprovacao_atual__lt=F('nivel_aprovacao_necessario'),  # ← lt (menor que necessário)
            nivel_aprovacao_atual__lte=nivel_usuario                     # ← lte (menor ou igual ao usuário)
        )
    elif filtro_aprovacao == 'em_aprovacao':
        pedidos = pedidos.filter(status='em_aprovacao')
    elif filtro_aprovacao == 'aprovados':
        pedidos = pedidos.filter(status='aprovado')
    elif filtro_aprovacao == 'rejeitados':
        pedidos = pedidos.filter(status='rejeitado')

    paginator = Paginator(pedidos, 25)
    page_number = request.GET.get('page')
    pedidos_page = paginator.get_page(page_number)

    # Contadores para cards
    total_pedidos = PedidoCompra.objects.count()
    em_aprovacao = PedidoCompra.objects.filter(status='em_aprovacao').count()
    aprovados = PedidoCompra.objects.filter(status='aprovado').count()
    pendentes_entrega = PedidoCompra.objects.filter(status='pendente_entrega').count()
    recebidos = PedidoCompra.objects.filter(status='recebido').count()
    cancelados = PedidoCompra.objects.filter(status='cancelado').count()
    
    # FASE 2: Contador de pedidos aguardando aprovação do usuário
    nivel_usuario = get_nivel_aprovacao_usuario(request.user)
    minha_aprovacao = 0
    if nivel_usuario > 0:
        minha_aprovacao = PedidoCompra.objects.filter(
            status='em_aprovacao',
            nivel_aprovacao_atual__lt=F('nivel_aprovacao_necessario'),
            nivel_aprovacao_atual__lte=nivel_usuario
        ).count()

    fornecedores = Fornecedor.objects.filter(ativo=True).order_by('nome_razao_social')
    condicoes = CondicaoPagamento.objects.filter(ativo=True).order_by('descricao')
    formas = FormaPagamento.objects.filter(ativo=True).order_by('descricao')
    pedidos_abertos = PedidoCompra.objects.filter(
        status__in=['pendente_entrega', 'aprovado']
    ).order_by('-data_pedido')
    cotacoes_concluidas = CotacaoMae.objects.filter(
        status='concluida'
    ).order_by('-data_solicitacao')

    context = {
        'pedidos': pedidos_page,
        'total_pedidos': total_pedidos,
        'em_aprovacao': em_aprovacao,
        'aprovados': aprovados,
        'pendentes_entrega': pendentes_entrega,
        'recebidos': recebidos,
        'cancelados': cancelados,
        'minha_aprovacao': minha_aprovacao,  # FASE 2
        'nivel_usuario': nivel_usuario,  # FASE 2
        'fornecedores': fornecedores,
        'condicoes_pagamento': condicoes,
        'formas_pagamento': formas,
        'pedidos_abertos': pedidos_abertos,
        'cotacoes_concluidas': cotacoes_concluidas,
        'search': search,
        'status': status,
        'filtro_aprovacao': filtro_aprovacao,
    }
    return render(request, 'compras/pedido_compra_manager.html', context)

# -----------------------------------------------------------------------------
# VIEWS DE APROVAÇÃO (FASE 2 - NOVAS)
# -----------------------------------------------------------------------------

@login_required
def pedido_aprovacao_list(request):
    """
    Lista de pedidos pendentes de aprovação para o usuário logado.
    Filtra por alçada/nível de aprovação do usuário.
    """
    nivel_usuario = get_nivel_aprovacao_usuario(request.user)
    
    if nivel_usuario == 0:
        messages.warning(request, 'Você não possui permissão para aprovar pedidos.')
        return redirect('ERP_ServicesBI:pedido_compra_manager')
    
    # Busca pedidos que o usuário pode aprovar
    pedidos = PedidoCompra.objects.filter(
        status='em_aprovacao',
        nivel_aprovacao_atual__lt=F('nivel_aprovacao_necessario'),
        nivel_aprovacao_atual__lte=nivel_usuario
    ).select_related('fornecedor', 'solicitante').order_by('-data_pedido')
    
    # Estatísticas
    stats = {
        'total_pendentes': pedidos.count(),
        'valor_total_pendentes': pedidos.aggregate(
            total=Sum('valor_total')
        )['total'] or 0,
        'por_nivel': {}
    }
    
    for nivel in range(1, 4):
        stats['por_nivel'][nivel] = PedidoCompra.objects.filter(
            status='em_aprovacao',
            nivel_aprovacao_atual=nivel-1,
            nivel_aprovacao_necessario__gte=nivel
        ).count()
    
    # Histórico de aprovações do usuário
    minhas_aprovacoes = PedidoAprovacao.objects.filter(
        usuario=request.user
    ).select_related('pedido').order_by('-data')[:10]
    
    context = {
        'pedidos': pedidos,
        'stats': stats,
        'nivel_usuario': nivel_usuario,
        'minhas_aprovacoes': minhas_aprovacoes,
    }
    return render(request, 'compras/pedido_aprovacao_list.html', context)


@login_required
def pedido_aprovacao_detail(request, pk):
    """
    Detalhes do pedido para tela de aprovação.
    Mostra informações completas + histórico de aprovações.
    """
    pedido = get_object_or_404(
        PedidoCompra.objects.select_related('fornecedor', 'solicitante', 'aprovador_atual'),
        pk=pk
    )
    
    # Verifica se usuário pode aprovar este pedido
    pode_aprovar, motivo = pode_aprovar_pedido_usuario(pedido, request.user)
    
    # Histórico de aprovações
    historico = pedido.historico_aprovacoes.select_related('usuario').all()
    
    # Itens do pedido
    itens = pedido.itens.select_related('produto').all()
    
    # Verificação de 3-Way Matching (se já houver NF ou recebimento)
    divergencias_3way = []
    if pedido.status in ['pendente_entrega', 'parcial', 'recebido']:
        divergencias_3way = _verificar_divergencias_pedido(pedido)
    
    context = {
        'pedido': pedido,
        'itens': itens,
        'historico': historico,
        'pode_aprovar': pode_aprovar,
        'motivo_nao_pode_aprovar': motivo,
        'divergencias_3way': divergencias_3way,
        'proximo_nivel': pedido.nivel_aprovacao_atual + 1,
        'niveis_restantes': pedido.nivel_aprovacao_necessario - pedido.nivel_aprovacao_atual,
    }
    return render(request, 'compras/pedido_aprovacao_detail.html', context)


@login_required
@require_POST
def pedido_aprovacao_approve(request, pk):
    """
    Aprova pedido no nível atual.
    Registra no histórico e avança workflow.
    """
    pedido = get_object_or_404(PedidoCompra, pk=pk)
    
    pode_aprovar, motivo = pode_aprovar_pedido_usuario(pedido, request.user)
    if not pode_aprovar:
        messages.error(request, f'Não é possível aprovar: {motivo}')
        return redirect('ERP_ServicesBI:pedido_aprovacao_detail', pk=pk)
    
    observacao = request.POST.get('observacao', '').strip()
    
    try:
        with transaction.atomic():
            # Usa método do modelo para aprovar
            pedido.aprovar(request.user, observacao)
            
            # Preparar notificação (placeholder para implementação futura)
            _preparar_notificacao_aprovacao(pedido, 'aprovado', request.user)
            
            messages.success(
                request, 
                f'Pedido {pedido.numero} aprovado com sucesso! '
                f'Nível {pedido.nivel_aprovacao_atual}/{pedido.nivel_aprovacao_necessario}'
            )
            
            # Se ainda precisa de mais aprovações, redireciona para lista
            if pedido.status == 'em_aprovacao':
                messages.info(request, 'Pedido aguardando próximo nível de aprovação.')
                return redirect('ERP_ServicesBI:pedido_aprovacao_list')
            else:
                messages.success(request, 'Pedido totalmente aprovado!')
                return redirect('ERP_ServicesBI:pedido_compra_manager')
                
    except PermissionError as e:
        messages.error(request, str(e))
        return redirect('ERP_ServicesBI:pedido_aprovacao_detail', pk=pk)
    except Exception as e:
        log_erro_seguro('pedido_aprovacao_approve', e, request, {'pedido_id': pk})
        messages.error(request, 'Erro ao aprovar pedido. Tente novamente.')
        return redirect('ERP_ServicesBI:pedido_aprovacao_detail', pk=pk)


@login_required
@require_POST
def pedido_aprovacao_reject(request, pk):
    """
    Rejeita pedido. Exige motivo obrigatório.
    """
    pedido = get_object_or_404(PedidoCompra, pk=pk)
    
    if pedido.status != 'em_aprovacao':
        messages.error(request, 'Apenas pedidos em aprovação podem ser rejeitados.')
        return redirect('ERP_ServicesBI:pedido_aprovacao_detail', pk=pk)
    
    motivo = request.POST.get('motivo', '').strip()
    if not motivo:
        messages.error(request, 'O motivo da rejeição é obrigatório.')
        return redirect('ERP_ServicesBI:pedido_aprovacao_detail', pk=pk)
    
    try:
        with transaction.atomic():
            pedido.rejeitar(request.user, motivo)
            
            # Preparar notificação
            _preparar_notificacao_aprovacao(pedido, 'rejeitado', request.user)
            
            messages.success(request, f'Pedido {pedido.numero} rejeitado.')
            return redirect('ERP_ServicesBI:pedido_aprovacao_list')
            
    except Exception as e:
        log_erro_seguro('pedido_aprovacao_reject', e, request, {'pedido_id': pk})
        messages.error(request, 'Erro ao rejeitar pedido.')
        return redirect('ERP_ServicesBI:pedido_aprovacao_detail', pk=pk)

# -----------------------------------------------------------------------------
# APIs DE APROVAÇÃO (FASE 2 - NOVAS)
# -----------------------------------------------------------------------------

@login_required
@require_GET
def api_pedidos_pendentes_alcada(request):
    """
    API REST: Lista pedidos pendentes por alçada do usuário logado.
    Retorna JSON para uso em AJAX/datatables.
    """
    try:
        nivel_usuario = get_nivel_aprovacao_usuario(request.user)
        
        if nivel_usuario == 0:
            return JsonResponse({
                'success': False,
                'message': 'Usuário sem permissão de aprovação'
            }, status=403)
        
        pedidos = PedidoCompra.objects.filter(
            status='em_aprovacao',
            nivel_aprovacao_atual__lt=F('nivel_aprovacao_necessario'),
            nivel_aprovacao_atual__lte=nivel_usuario
        ).select_related('fornecedor', 'solicitante')
        
        data = []
        for pedido in pedidos:
            data.append({
                'id': pedido.id,
                'numero': pedido.numero,
                'fornecedor': pedido.fornecedor.nome_razao_social,
                'valor_total': float(pedido.valor_total),
                'data_pedido': pedido.data_pedido.isoformat(),
                'solicitante': pedido.solicitante.get_full_name() if pedido.solicitante else 'Sistema',
                'nivel_atual': pedido.nivel_aprovacao_atual,
                'nivel_necessario': pedido.nivel_aprovacao_necessario,
                'proximo_nivel': pedido.nivel_aprovacao_atual + 1,
            })
        
        return JsonResponse({
            'success': True,
            'pedidos': data,
            'nivel_usuario': nivel_usuario,
            'total': len(data)
        })
        
    except Exception as e:
        log_erro_seguro('api_pedidos_pendentes_alcada', e, request)
        return resposta_erro_segura('Erro ao buscar pedidos', 500)


@login_required
@require_POST
def api_aprovar_pedido(request, pk):
    """
    API REST: Aprovar pedido com validação de permissões.
    """
    try:
        pedido = get_object_or_404(PedidoCompra, pk=pk)
        
        pode_aprovar, motivo = pode_aprovar_pedido_usuario(pedido, request.user)
        if not pode_aprovar:
            return JsonResponse({
                'success': False,
                'message': motivo
            }, status=403)
        
        data = json.loads(request.body) if request.body else {}
        observacao = data.get('observacao', '')
        
        with transaction.atomic():
            pedido.aprovar(request.user, observacao)
            
            # Preparar notificação
            _preparar_notificacao_aprovacao(pedido, 'aprovado', request.user)
        
        return JsonResponse({
            'success': True,
            'message': 'Pedido aprovado com sucesso',
            'novo_status': pedido.status,
            'nivel_aprovacao_atual': pedido.nivel_aprovacao_atual,
            'aprovacao_completa': pedido.status == 'aprovado'
        })
        
    except PermissionError as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=403)
    except Exception as e:
        log_erro_seguro('api_aprovar_pedido', e, request, {'pedido_id': pk})
        return resposta_erro_segura('Erro ao aprovar pedido', 500)


@login_required
@require_POST
def api_rejeitar_pedido(request, pk):
    """
    API REST: Rejeitar pedido com validação de permissões.
    """
    try:
        pedido = get_object_or_404(PedidoCompra, pk=pk)
        
        if pedido.status != 'em_aprovacao':
            return JsonResponse({
                'success': False,
                'message': 'Pedido não está em aprovação'
            }, status=400)
        
        data = json.loads(request.body) if request.body else {}
        motivo = data.get('motivo', '').strip()
        
        if not motivo:
            return JsonResponse({
                'success': False,
                'message': 'Motivo da rejeição é obrigatório'
            }, status=400)
        
        with transaction.atomic():
            pedido.rejeitar(request.user, motivo)
            
            # Preparar notificação
            _preparar_notificacao_aprovacao(pedido, 'rejeitado', request.user)
        
        return JsonResponse({
            'success': True,
            'message': 'Pedido rejeitado com sucesso',
            'novo_status': pedido.status
        })
        
    except Exception as e:
        log_erro_seguro('api_rejeitar_pedido', e, request, {'pedido_id': pk})
        return resposta_erro_segura('Erro ao rejeitar pedido', 500)


@login_required
@require_GET
def api_historico_aprovacoes(request, pk):
    """
    API REST: Retorna histórico de aprovações de um pedido.
    """
    try:
        pedido = get_object_or_404(PedidoCompra, pk=pk)
        
        historico = pedido.historico_aprovacoes.select_related('usuario').all()
        
        data = []
        for item in historico:
            data.append({
                'id': item.id,
                'usuario': item.usuario.get_full_name() if item.usuario else 'Sistema',
                'acao': item.get_acao_display(),
                'nivel': item.nivel,
                'data': item.data.isoformat(),
                'observacao': item.observacao,
            })
        
        return JsonResponse({
            'success': True,
            'historico': data,
            'pedido': {
                'id': pedido.id,
                'numero': pedido.numero,
                'status': pedido.status,
                'nivel_aprovacao_atual': pedido.nivel_aprovacao_atual,
                'nivel_aprovacao_necessario': pedido.nivel_aprovacao_necessario,
            }
        })
        
    except Exception as e:
        log_erro_seguro('api_historico_aprovacoes', e, request, {'pedido_id': pk})
        return resposta_erro_segura('Erro ao buscar histórico', 500)


@login_required
@require_GET
def api_verificar_divergencias_3way(request, pk):
    """
    API REST: Verifica divergências no 3-Way Matching.
    Compara: Pedido vs Nota Fiscal vs Recebimento Físico
    """
    try:
        pedido = get_object_or_404(PedidoCompra, pk=pk)
        
        divergencias = _verificar_divergencias_pedido(pedido)
        
        # Estatísticas do 3-way
        stats = {
            'total_itens': pedido.itens.count(),
            'itens_com_divergencia': len([d for d in divergencias if d['tem_divergencia']]),
            'valor_pedido': float(pedido.valor_total),
            'valor_recebido': float(pedido.itens.aggregate(
                total=Sum(F('quantidade_recebida') * F('preco_unitario'), output_field=DecimalField())
            )['total'] or 0),
        }
        
        return JsonResponse({
            'success': True,
            'divergencias': divergencias,
            'stats': stats,
            'status_3way': 'divergente' if divergencias else 'ok'
        })
        
    except Exception as e:
        log_erro_seguro('api_verificar_divergencias_3way', e, request, {'pedido_id': pk})
        return resposta_erro_segura('Erro ao verificar divergências', 500)

# -----------------------------------------------------------------------------
# FUNÇÕES AUXILIARES DE 3-WAY MATCHING
# -----------------------------------------------------------------------------

def _verificar_divergencias_pedido(pedido):
    """
    Verifica divergências entre Pedido, NF e Recebimento.
    Retorna lista de dicionários com divergências por item.
    """
    divergencias = []
    
    for item in pedido.itens.select_related('produto').all():
        div_item = {
            'item_id': item.id,
            'produto': item.descricao,
            'quantidade_pedido': float(item.quantidade),
            'quantidade_recebida': float(item.quantidade_recebida),
            'quantidade_conferida': float(item.quantidade_conferida or 0),
            'preco_pedido': float(item.preco_unitario),
            'preco_recebido': float(item.preco_unitario_recebido or item.preco_unitario),
            'tem_divergencia': False,
            'tipos_divergencia': []
        }
        
        # Verifica divergência de quantidade
        if item.quantidade_recebida > item.quantidade:
            div_item['tem_divergencia'] = True
            div_item['tipos_divergencia'].append('quantidade_maior')
        elif item.quantidade_recebida < item.quantidade and item.quantidade_recebida > 0:
            div_item['tem_divergencia'] = True
            div_item['tipos_divergencia'].append('quantidade_menor')
        
        # Verifica divergência de preço
        if item.preco_unitario_recebido and item.preco_unitario_recebido != item.preco_unitario:
            div_item['tem_divergencia'] = True
            div_item['tipos_divergencia'].append('preco_diferente')
        
        # Verifica conferência física
        if item.quantidade_conferida > 0 and item.quantidade_conferida != item.quantidade_recebida:
            div_item['tem_divergencia'] = True
            div_item['tipos_divergencia'].append('divergencia_fisica')
        
        # Usa dados do modelo se já marcado
        if item.divergencia_encontrada:
            div_item['tem_divergencia'] = True
            if item.tipo_divergencia:
                div_item['tipos_divergencia'].append(item.tipo_divergencia)
        
        divergencias.append(div_item)
    
    return divergencias

# -----------------------------------------------------------------------------
# NOTIFICAÇÕES (PREPARADO PARA FUTURA IMPLEMENTAÇÃO)
# -----------------------------------------------------------------------------

def _preparar_notificacao_aprovacao(pedido, tipo_acao, usuario):
    """
    Prepara dados para notificação de aprovação/rejeição.
    Placeholder para implementação futura de email/push.
    """
    notificacao = {
        'tipo': f'pedido_{tipo_acao}',
        'pedido_id': pedido.id,
        'pedido_numero': pedido.numero,
        'usuario_acao': usuario.get_full_name() or usuario.username,
        'data_acao': timezone.now().isoformat(),
        'status_atual': pedido.status,
        'destinatarios': []
    }
    
    # Define destinatários baseado no workflow
    if tipo_acao == 'aprovado':
        if pedido.status == 'em_aprovacao':
            # Próximo aprovador
            notificacao['destinatarios'].append('proximo_aprovador')
        else:
            # Aprovado totalmente - notificar solicitante
            if pedido.solicitante:
                notificacao['destinatarios'].append(pedido.solicitante.email)
    elif tipo_acao == 'rejeitado':
        # Notificar solicitante da rejeição
        if pedido.solicitante:
            notificacao['destinatarios'].append(pedido.solicitante.email)
    
    # TODO: Implementar envio real de email/push aqui
    logger.info(f"Notificação preparada: {notificacao}")
    
    return notificacao

# -----------------------------------------------------------------------------
# APIs DE PEDIDOS (EXISTENTES - ATUALIZADAS)
# -----------------------------------------------------------------------------

@login_required
@require_POST
def pedido_salvar_api(request):
    """API unificada para salvar pedido de compra com verificação de aprovação"""
    try:
        data = json.loads(request.body)
        pk = data.get('id')
 
        if pk:
            pedido = get_object_or_404(PedidoCompra, pk=pk)
        else:
            pedido = PedidoCompra()
            pedido.solicitante = request.user
 
        pedido.fornecedor_id = data.get('fornecedor_id')
        pedido.data_prevista_entrega = data.get('data_previsao_entrega') or None
        pedido.condicao_pagamento = data.get('condicao_pagamento', '')
        pedido.forma_pagamento = data.get('forma_pagamento', '')
        pedido.cotacao_mae_id = data.get('cotacao_id') or None
        pedido.observacoes = data.get('observacoes', '')
        
        # Campos FASE 2
        pedido.prioridade = data.get('prioridade', 'media')
        centro_custo_id = data.get('centro_custo_id')
        pedido.centro_custo_id = centro_custo_id if centro_custo_id else None
        
        # Status só muda se for novo pedido
        if not pk:
            pedido.status = 'rascunho'
 
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
        
        # FASE 2: Verifica se precisa de aprovação ao salvar
        if not pk or pedido.status == 'rascunho':
            precisa_aprovacao, nivel_necessario = verificar_regras_aprovacao(pedido)
            if precisa_aprovacao:
                pedido.nivel_aprovacao_necessario = nivel_necessario
                pedido.status = 'em_aprovacao'
                pedido.save(update_fields=['nivel_aprovacao_necessario', 'status'])
 
        return JsonResponse({
            'success': True,
            'id': pedido.pk,
            'numero': pedido.numero,
            'status': pedido.status,
            'precisa_aprovacao': pedido.status == 'em_aprovacao',
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
            if item.produto and hasattr(item.produto, 'unidade'):
                unidade = item.produto.unidade or 'UN'
            itens.append({
                'id': item.id,
                'produto': item.descricao,
                'quantidade': float(item.quantidade),
                'unidade': unidade,
                'valor_unitario': float(item.preco_unitario),
                'valor_total': float(item.preco_total),
                'quantidade_recebida': float(item.quantidade_recebida),
                'divergencia': item.divergencia_encontrada,
            })
 
        return JsonResponse({
            'success': True,
            'id': pedido.id,
            'numero': pedido.numero,
            'fornecedor_id': pedido.fornecedor_id,
            'fornecedor': pedido.fornecedor.nome_razao_social,
            'data_previsao_entrega': pedido.data_prevista_entrega.isoformat() if pedido.data_prevista_entrega else None,
            'condicao_pagamento': pedido.condicao_pagamento,
            'forma_pagamento': pedido.forma_pagamento,
            'cotacao_id': pedido.cotacao_mae_id,
            'observacoes': pedido.observacoes or '',
            'status': pedido.status,
            # Campos FASE 2
            'prioridade': pedido.prioridade,
            'prioridade_display': pedido.get_prioridade_display(),
            'centro_custo_id': pedido.centro_custo_id,
            'solicitante': pedido.solicitante.get_full_name() if pedido.solicitante else 'Sistema',
            'nivel_aprovacao_atual': pedido.nivel_aprovacao_atual,
            'nivel_aprovacao_necessario': pedido.nivel_aprovacao_necessario,
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
        
        if pedido.status in ['recebido', 'cancelado']:
            return JsonResponse({
                'success': False,
                'message': 'Pedido já recebido ou cancelado não pode ser cancelado.'
            }, status=400)
        
        motivo = request.POST.get('motivo', '')
        pedido.cancelar(request.user, motivo)
        
        return JsonResponse({
            'success': True,
            'message': 'Pedido cancelado com sucesso!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@require_GET
def pedido_dados_recebimento_api(request, pk):
    """API para dados de recebimento do pedido"""
    try:
        pedido = get_object_or_404(
            PedidoCompra.objects.select_related(
                'fornecedor', 'condicao_pagamento', 'forma_pagamento'
            ), pk=pk
        )
        itens = []
        for item in pedido.itens.select_related('produto').all():
            qtd_recebida = getattr(item, 'quantidade_recebida', 0) or 0
            unidade = 'UN'
            if item.produto and hasattr(item.produto, 'unidade'):
                unidade = item.produto.unidade or 'UN'
            itens.append({
                'id':                item.id,
                'produto_nome':      item.produto.descricao if item.produto else item.descricao,
                'produto':           item.descricao,
                'quantidade':        float(item.quantidade),
                'quantidade_recebida': float(qtd_recebida),
                'saldo_receber':     float(item.saldo_receber()),
                'unidade':           unidade,
                'preco_unitario':    float(item.preco_unitario),
                'divergencia':       item.divergencia_encontrada,
                'tipo_divergencia':  item.tipo_divergencia,
            })

        return JsonResponse({
            'success':               True,
            'numero':                pedido.numero,
            'fornecedor':            pedido.fornecedor.nome_razao_social,
            # ✅ CAMPOS QUE FALTAVAM:
            'fornecedor_id':         pedido.fornecedor_id,
            'condicao_pagamento_id': pedido.condicao_pagamento_id,
            'forma_pagamento_id':    pedido.forma_pagamento_id,
            'status':                pedido.status,
            'valor_total':           float(pedido.valor_total or 0),
            'itens':                 itens,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@require_POST
def pedido_receber_api(request, pk):
    """
    API para dar entrada no pedido (recebimento) com 3-Way Matching.
    
    CORREÇÃO: Agora gera automaticamente a NF de Entrada vinculada ao pedido
    e prepara os itens para posterior confirmação e entrada no estoque.
    """
    try:
        pedido = get_object_or_404(PedidoCompra, pk=pk)
        data = json.loads(request.body)
        itens_recebidos = data.get('itens', [])
        observacao = data.get('observacao', '')
        
        # Dados opcionais da NF
        numero_nf = data.get('numero_nf', '')
        serie_nf = data.get('serie', '1')
        chave_acesso = data.get('chave_acesso', '')
        data_emissao = data.get('data_emissao', None)

        with transaction.atomic():
            total_recebido = 0
            total_pedido = pedido.itens.count()
            tem_divergencia = False
            itens_para_nf = []

            for item_data in itens_recebidos:
                item = get_object_or_404(ItemPedidoCompra, pk=item_data['item_id'], pedido=pedido)
                qtd_receber = Decimal(str(item_data.get('quantidade', 0)))
                qtd_conferida = Decimal(str(item_data.get('quantidade_conferida', 0)))
                preco_recebido = Decimal(str(item_data.get('preco_recebido', 0))) if item_data.get('preco_recebido') else None

                if qtd_receber > 0:
                    # Registra recebimento com verificação de divergência
                    item.registrar_recebimento(
                        quantidade=qtd_receber,
                        usuario=request.user,
                        preco_recebido=preco_recebido,
                        observacao=observacao
                    )
                    
                    # Atualiza conferência física se informada
                    if qtd_conferida > 0:
                        item.quantidade_conferida = qtd_conferida
                        item.save(update_fields=['quantidade_conferida'])
                    
                    if item.divergencia_encontrada:
                        tem_divergencia = True
                    
                    total_recebido += 1
                    
                    # ✅ NOVO: Coleta dados para gerar NF de Entrada
                    itens_para_nf.append({
                        'produto': item.produto,
                        'descricao': item.descricao,
                        'quantidade': qtd_receber,
                        'preco_unitario': preco_recebido or item.preco_unitario,
                    })

            # Atualiza status do pedido
            pedido.verificar_recebimento()
            pedido.data_recebimento = timezone.now()
            pedido.usuario_recebimento = request.user
            if observacao:
                pedido.observacao_recebimento = observacao
            pedido.save()

            # =============================================================
            # ✅ CORREÇÃO 1: Gerar NF de Entrada automaticamente
            # =============================================================
            nota_fiscal = None
            if itens_para_nf:
                # Gera número da NF automaticamente se não informado
                if not numero_nf:
                    ultima_nf = NotaFiscalEntrada.objects.order_by('-id').first()
                    if ultima_nf and ultima_nf.numero_nf:
                        try:
                            # Tenta extrair número sequencial
                            num = int(''.join(filter(str.isdigit, ultima_nf.numero_nf)))
                            numero_nf = str(num + 1).zfill(6)
                        except (ValueError, TypeError):
                            numero_nf = f"NF-{pedido.numero}"
                    else:
                        numero_nf = f"NF-{pedido.numero}"

                nota_fiscal = NotaFiscalEntrada.objects.create(
                    numero_nf=numero_nf,
                    numero=numero_nf,
                    serie=serie_nf,
                    chave_acesso=chave_acesso,
                    fornecedor=pedido.fornecedor,
                    pedido_compra=pedido,
                    data_emissao=data_emissao or timezone.now().date(),
                    status='pendente',  # Pendente até confirmação
                    usuario_cadastro=request.user,
                    observacoes=f'Gerada automaticamente do recebimento do Pedido {pedido.numero}',
                    valor_frete=pedido.valor_frete or 0,
                )
                
                # Vincula condição e forma de pagamento se disponíveis
                # Tenta buscar pelos nomes salvos no pedido
                if pedido.condicao_pagamento:
                    cond = CondicaoPagamento.objects.filter(
                        descricao__icontains=pedido.condicao_pagamento
                    ).first()
                    if cond:
                        nota_fiscal.condicao_pagamento = cond
                
                if pedido.forma_pagamento:
                    forma = FormaPagamento.objects.filter(
                        descricao__icontains=pedido.forma_pagamento
                    ).first()
                    if forma:
                        nota_fiscal.forma_pagamento = forma
                
                nota_fiscal.save()

                # Cria itens da NF a partir dos itens recebidos
                for item_nf_data in itens_para_nf:
                    ItemNotaFiscalEntrada.objects.create(
                        nota_fiscal=nota_fiscal,
                        produto=item_nf_data['produto'],
                        descricao=item_nf_data['descricao'],
                        quantidade=item_nf_data['quantidade'],
                        unidade_medida=item_nf_data['produto'].unidade if item_nf_data['produto'] else 'UN',
                        valor_unitario=item_nf_data['preco_unitario'],
                        preco_unitario=item_nf_data['preco_unitario'],
                    )

                # Calcula totais da NF
                nota_fiscal.calcular_totais()
                
                # Marca no pedido que NF foi vinculada
                pedido.nota_fiscal_vinculada = True
                pedido.save(update_fields=['nota_fiscal_vinculada'])

        return JsonResponse({
            'success': True,
            'message': 'Entrada realizada com sucesso!',
            'novo_status': pedido.status,
            'tem_divergencia': tem_divergencia,
            # ✅ NOVO: Retorna dados da NF gerada
            'nota_fiscal': {
                'id': nota_fiscal.id if nota_fiscal else None,
                'numero': nota_fiscal.numero_nf if nota_fiscal else None,
                'valor_total': float(nota_fiscal.valor_total) if nota_fiscal else 0,
                'status': 'pendente',
                'mensagem': 'NF de Entrada gerada. Confirme para dar entrada no estoque.',
            } if nota_fiscal else None,
        })
    except Exception as e:
        log_erro_seguro('pedido_receber_api', e, request)
        return resposta_erro_segura(f'Erro no recebimento: {str(e)}', 400)

@login_required
def pedido_compra_gerar_nfe(request, pk):
    """Redireciona para NF-e manager com pedido pré-selecionado"""
    pedido = get_object_or_404(PedidoCompra, pk=pk)
    if pedido.status not in ['recebido', 'parcial', 'aprovado']:
        messages.warning(request, 'Este pedido não está apto para gerar NF-e.')
        return redirect('ERP_ServicesBI:pedido_compra_manager')
    return redirect(
        f"{reverse('ERP_ServicesBI:nota_fiscal_entrada_manager')}?pedido_id={pk}"
    )



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
# =============================================================================
# PARTE 5: COMPRAS - NOTAS FISCAIS DE ENTRADA + VENDAS
# =============================================================================

# -----------------------------------------------------------------------------
# MÓDULO: COMPRAS - NOTAS FISCAIS DE ENTRADA
# -----------------------------------------------------------------------------

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
    # ✅ CORREÇÃO: Status minúsculos
    pedidos_abertos = PedidoCompra.objects.filter(
        status__in=['aprovado', 'pendente_entrega', 'parcial', 'recebido']
    ).order_by('-data_pedido')
    pedido_preselect = request.GET.get('pedido_id', '')


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
        'pedido_preselect': pedido_preselect,
    }
    return render(request, 'compras/nota_fiscal_entrada_manager.html', context)


@login_required
@require_POST
def nota_fiscal_salvar_api(request):
    """
    API unificada para salvar nota fiscal de entrada.
    
    CORREÇÃO: Quando pedido_id é informado e não há itens no payload,
    puxa automaticamente os itens do pedido de compra vinculado.
    """
    try:
        data = json.loads(request.body)
        pk = data.get('id')

        if pk:
            nota = get_object_or_404(NotaFiscalEntrada, pk=pk)
        else:
            nota = NotaFiscalEntrada()

        nota.numero_nf = data.get('numero', '')
        nota.numero = data.get('numero', '')
        nota.serie = data.get('serie', '1')
        nota.chave_acesso = data.get('chave_acesso', '')
        nota.modelo = data.get('modelo', '55')
        nota.fornecedor_id = data.get('fornecedor_id')
        nota.pedido_compra_id = data.get('pedido_id') or None
        nota.data_emissao = data.get('data_emissao')
        nota.condicao_pagamento_id = data.get('condicao_pagamento_id') or None
        nota.forma_pagamento_id = data.get('forma_pagamento_id') or None
        nota.observacoes = data.get('observacoes', '')
        nota.status = data.get('status', 'pendente')

        # Valores adicionais
        if data.get('valor_frete'):
            nota.valor_frete = Decimal(str(data['valor_frete']))
        if data.get('valor_impostos'):
            nota.valor_impostos = Decimal(str(data['valor_impostos']))

        if not pk:
            nota.usuario_cadastro = request.user

        nota.save()

        itens_data = data.get('itens', [])
        
        # =============================================================
        # ✅ CORREÇÃO 2: Se tem pedido vinculado e não enviou itens,
        # puxa automaticamente os itens do pedido
        # =============================================================
        if not itens_data and nota.pedido_compra_id:
            pedido = nota.pedido_compra
            if pedido:
                nota.itens.all().delete()
                for item_pedido in pedido.itens.select_related('produto').all():
                    # Usa quantidade recebida se disponível, senão usa quantidade do pedido
                    qtd = item_pedido.quantidade_recebida if item_pedido.quantidade_recebida > 0 else item_pedido.quantidade
                    preco = item_pedido.preco_unitario_recebido or item_pedido.preco_unitario
                    
                    ItemNotaFiscalEntrada.objects.create(
                        nota_fiscal=nota,
                        produto=item_pedido.produto,
                        descricao=item_pedido.descricao,
                        quantidade=qtd,
                        unidade_medida=item_pedido.produto.unidade if item_pedido.produto else 'UN',
                        valor_unitario=preco,
                        preco_unitario=preco,
                    )
                
                # Copia valor de frete do pedido se não informado
                if not nota.valor_frete and pedido.valor_frete:
                    nota.valor_frete = pedido.valor_frete
                    nota.save(update_fields=['valor_frete'])
                    
        elif itens_data:
            # Fluxo original: itens informados manualmente
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

        return JsonResponse({
            'success': True,
            'id': nota.pk,
            'numero': nota.numero_nf,
            'total_itens': nota.itens.count(),
            'valor_total': float(nota.valor_total),
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
        # ✅ CORREÇÃO: Status minúsculo
        if nota.status == 'confirmada':
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
    """
    API para confirmar nota fiscal.
    
    CORREÇÃO: Agora chama atualizar_estoque() para dar entrada no estoque
    e gera conta a pagar automaticamente.
    """
    try:
        nota = get_object_or_404(NotaFiscalEntrada, pk=pk)
        
        if nota.status == 'confirmada':
            return JsonResponse({'success': False, 'message': 'Nota fiscal já está confirmada'}, status=400)
        if nota.status == 'cancelada':
            return JsonResponse({'success': False, 'message': 'Nota fiscal está cancelada'}, status=400)
        
        # Validação: NF precisa ter itens
        if nota.itens.count() == 0:
            return JsonResponse({
                'success': False, 
                'message': 'Nota fiscal não possui itens. Adicione itens antes de confirmar.'
            }, status=400)

        with transaction.atomic():
            # 1. Atualiza status da NF
            nota.status = 'confirmada'
            nota.data_confirmacao = timezone.now()
            nota.usuario_confirmacao = request.user
            nota.save()
            
            # =============================================================
            # ✅ CORREÇÃO 3: Dar entrada no estoque
            # =============================================================
            nota.atualizar_estoque()
            
            # 2. Atualiza pedido de compra vinculado
            if nota.pedido_compra:
                pedido = nota.pedido_compra
                pedido.status = 'recebido'
                pedido.movimento_estoque_gerado = True
                pedido.nota_fiscal_vinculada = True
                pedido.save(update_fields=[
                    'status', 'movimento_estoque_gerado', 'nota_fiscal_vinculada'
                ])
            
            # =============================================================
            # ✅ NOVO: Gerar conta a pagar automaticamente
            # =============================================================
            conta_pagar = None
            if nota.valor_total > 0:
                # Verifica se já existe conta a pagar para esta NF
                conta_existente = ContaPagar.objects.filter(
                    nota_fiscal=nota
                ).first()
                
                if not conta_existente:
                    # Calcula vencimento baseado na condição de pagamento
                    dias_vencimento = 30  # padrão
                    if nota.condicao_pagamento:
                        dias_vencimento = nota.condicao_pagamento.dias_primeira_parcela or 30
                    
                    data_vencimento = timezone.now().date() + timedelta(days=dias_vencimento)
                    
                    conta_pagar = ContaPagar.objects.create(
                        descricao=f'NF {nota.numero_nf} - {nota.fornecedor.nome_razao_social}',
                        fornecedor=nota.fornecedor,
                        nota_fiscal=nota,
                        data_vencimento=data_vencimento,
                        valor_original=nota.valor_total,
                        status='pendente',
                        observacoes=f'Gerada automaticamente da NF de Entrada {nota.numero_nf}',
                    )
                    
                    # Marca no pedido que conta a pagar foi gerada
                    if nota.pedido_compra:
                        nota.pedido_compra.conta_pagar_gerada = True
                        nota.pedido_compra.save(update_fields=['conta_pagar_gerada'])

        # Monta resposta
        response_data = {
            'success': True,
            'message': 'Nota fiscal confirmada! Estoque atualizado.',
            'estoque_atualizado': True,
        }
        
        if conta_pagar:
            response_data['conta_pagar'] = {
                'id': conta_pagar.id,
                'descricao': conta_pagar.descricao,
                'valor': float(conta_pagar.valor_original),
                'vencimento': conta_pagar.data_vencimento.isoformat(),
            }
            response_data['message'] += ' Conta a pagar gerada.'
        
        return JsonResponse(response_data)
        
    except Exception as e:
        log_erro_seguro('nota_fiscal_confirmar_api', e, request)
        return resposta_erro_segura(f'Erro ao confirmar NF: {str(e)}', 400)


@login_required
@require_POST
def nota_fiscal_cancelar_api(request, pk):
    """API para cancelar nota fiscal"""
    try:
        nota = get_object_or_404(NotaFiscalEntrada, pk=pk)
        # ✅ CORREÇÃO: Status minúsculo
        if nota.status == 'cancelada':
            return JsonResponse({'success': False, 'message': 'Nota fiscal já está cancelada'}, status=400)

        with transaction.atomic():
            nota.status = 'cancelada'
            nota.data_cancelamento = timezone.now()
            nota.usuario_cancelamento = request.user
            nota.save()

        return JsonResponse({'success': True, 'message': 'Nota fiscal cancelada com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


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

@login_required
@require_GET
def api_pedido_dados_para_nfe(request, pk):
    """
    API que retorna dados do pedido de compra formatados para pré-popular
    o formulário de NF de Entrada.
    
    Usado quando o usuário clica "Gerar NF-e" a partir de um pedido.
    """
    try:
        pedido = get_object_or_404(
            PedidoCompra.objects.select_related('fornecedor'),
            pk=pk
        )
        
        # Verifica se pedido está apto
        if pedido.status not in ['aprovado', 'pendente_entrega', 'parcial', 'recebido']:
            return JsonResponse({
                'success': False,
                'message': f'Pedido com status "{pedido.get_status_display()}" não pode gerar NF-e.'
            }, status=400)
        
        # Verifica se já existe NF vinculada
        nf_existente = NotaFiscalEntrada.objects.filter(
            pedido_compra=pedido,
            status__in=['pendente', 'confirmada']
        ).first()
        
        if nf_existente:
            return JsonResponse({
                'success': True,
                'ja_existe_nf': True,
                'nf_existente': {
                    'id': nf_existente.id,
                    'numero': nf_existente.numero_nf,
                    'status': nf_existente.status,
                    'valor_total': float(nf_existente.valor_total),
                },
                'message': f'Já existe NF {nf_existente.numero_nf} vinculada a este pedido.'
            })
        
        # Monta dados para pré-popular o formulário
        itens = []
        for item in pedido.itens.select_related('produto').all():
            # Prioriza dados do recebimento se disponíveis
            qtd = item.quantidade_recebida if item.quantidade_recebida > 0 else item.quantidade
            preco = item.preco_unitario_recebido or item.preco_unitario
            
            itens.append({
                'produto_id': item.produto_id,
                'produto_nome': item.descricao or (item.produto.descricao if item.produto else ''),
                'produto_codigo': item.produto.codigo if item.produto else '',
                'quantidade': float(qtd),
                'quantidade_pedido': float(item.quantidade),
                'quantidade_recebida': float(item.quantidade_recebida),
                'unidade': item.produto.unidade if item.produto else 'UN',
                'valor_unitario': float(preco),
                'valor_total': float(qtd * preco),
                'tem_divergencia': item.divergencia_encontrada,
                'tipo_divergencia': item.tipo_divergencia,
            })
        
        # Busca IDs de condição/forma de pagamento
        condicao_id = None
        forma_id = None
        if pedido.condicao_pagamento:
            cond = CondicaoPagamento.objects.filter(
                descricao__icontains=pedido.condicao_pagamento
            ).first()
            condicao_id = cond.id if cond else None
        if pedido.forma_pagamento:
            forma = FormaPagamento.objects.filter(
                descricao__icontains=pedido.forma_pagamento
            ).first()
            forma_id = forma.id if forma else None
        
        return JsonResponse({
            'success': True,
            'ja_existe_nf': False,
            'pedido': {
                'id': pedido.id,
                'numero': pedido.numero,
                'fornecedor_id': pedido.fornecedor_id,
                'fornecedor_nome': pedido.fornecedor.nome_razao_social,
                'data_pedido': pedido.data_pedido.isoformat(),
                'condicao_pagamento': pedido.condicao_pagamento,
                'condicao_pagamento_id': condicao_id,
                'forma_pagamento': pedido.forma_pagamento,
                'forma_pagamento_id': forma_id,
                'valor_total': float(pedido.valor_total),
                'valor_frete': float(pedido.valor_frete or 0),
                'observacoes': pedido.observacoes or '',
            },
            'itens': itens,
        })
        
    except Exception as e:
        log_erro_seguro('api_pedido_dados_para_nfe', e, request, {'pedido_id': pk})
        return resposta_erro_segura('Erro ao buscar dados do pedido', 500)
    
@login_required
@require_POST
def api_gerar_nfe_from_pedido(request, pk):
    """
    API que gera uma NF de Entrada completa a partir de um pedido de compra.
    Fluxo de 1 clique: cria NF + itens + calcula totais.
    
    O usuário ainda precisa confirmar a NF para dar entrada no estoque.
    """
    try:
        pedido = get_object_or_404(PedidoCompra, pk=pk)
        
        # Validações
        if pedido.status not in ['aprovado', 'pendente_entrega', 'parcial', 'recebido']:
            return JsonResponse({
                'success': False,
                'message': f'Pedido com status "{pedido.get_status_display()}" não pode gerar NF-e.'
            }, status=400)
        
        # Verifica se já existe NF pendente/confirmada
        nf_existente = NotaFiscalEntrada.objects.filter(
            pedido_compra=pedido,
            status__in=['pendente', 'confirmada']
        ).first()
        
        if nf_existente:
            return JsonResponse({
                'success': False,
                'message': f'Já existe NF {nf_existente.numero_nf} vinculada a este pedido.',
                'nf_id': nf_existente.id,
            }, status=400)
        
        # Dados opcionais do body
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            data = {}
        
        numero_nf = data.get('numero_nf', '')
        serie = data.get('serie', '1')
        chave_acesso = data.get('chave_acesso', '')
        data_emissao = data.get('data_emissao', None)
        
        with transaction.atomic():
            # Gera número sequencial se não informado
            if not numero_nf:
                ultima_nf = NotaFiscalEntrada.objects.order_by('-id').first()
                if ultima_nf and ultima_nf.numero_nf:
                    try:
                        num = int(''.join(filter(str.isdigit, ultima_nf.numero_nf)))
                        numero_nf = str(num + 1).zfill(6)
                    except (ValueError, TypeError):
                        numero_nf = f"NF-{pedido.numero}"
                else:
                    numero_nf = '000001'
            
            # Cria a NF de Entrada
            nota = NotaFiscalEntrada.objects.create(
                numero_nf=numero_nf,
                numero=numero_nf,
                serie=serie,
                chave_acesso=chave_acesso,
                fornecedor=pedido.fornecedor,
                pedido_compra=pedido,
                data_emissao=data_emissao or timezone.now().date(),
                status='pendente',
                usuario_cadastro=request.user,
                observacoes=f'Gerada a partir do Pedido {pedido.numero}',
                valor_frete=pedido.valor_frete or 0,
            )
            
            # Vincula condição e forma de pagamento
            if pedido.condicao_pagamento:
                cond = CondicaoPagamento.objects.filter(
                    descricao__icontains=pedido.condicao_pagamento
                ).first()
                if cond:
                    nota.condicao_pagamento = cond
            
            if pedido.forma_pagamento:
                forma = FormaPagamento.objects.filter(
                    descricao__icontains=pedido.forma_pagamento
                ).first()
                if forma:
                    nota.forma_pagamento = forma
            
            nota.save()
            
            # Cria itens da NF a partir dos itens do pedido
            total_itens = 0
            for item_pedido in pedido.itens.select_related('produto').all():
                # Prioriza quantidade recebida e preço recebido
                qtd = item_pedido.quantidade_recebida if item_pedido.quantidade_recebida > 0 else item_pedido.quantidade
                preco = item_pedido.preco_unitario_recebido or item_pedido.preco_unitario
                
                ItemNotaFiscalEntrada.objects.create(
                    nota_fiscal=nota,
                    produto=item_pedido.produto,
                    descricao=item_pedido.descricao or (item_pedido.produto.descricao if item_pedido.produto else ''),
                    quantidade=qtd,
                    unidade_medida=item_pedido.produto.unidade if item_pedido.produto else 'UN',
                    valor_unitario=preco,
                    preco_unitario=preco,
                )
                total_itens += 1
            
            # Calcula totais
            nota.calcular_totais()
            
            # Marca no pedido
            pedido.nota_fiscal_vinculada = True
            pedido.save(update_fields=['nota_fiscal_vinculada'])
        
        return JsonResponse({
            'success': True,
            'message': f'NF {numero_nf} gerada com {total_itens} itens. Confirme para dar entrada no estoque.',
            'nota_fiscal': {
                'id': nota.id,
                'numero': nota.numero_nf,
                'fornecedor': pedido.fornecedor.nome_razao_social,
                'total_itens': total_itens,
                'valor_total': float(nota.valor_total),
                'status': 'pendente',
            }
        })
        
    except Exception as e:
        log_erro_seguro('api_gerar_nfe_from_pedido', e, request, {'pedido_id': pk})
        return resposta_erro_segura('Erro ao gerar NF de Entrada', 500)

# -----------------------------------------------------------------------------
# MÓDULO: COMPRAS - RELATÓRIO
# -----------------------------------------------------------------------------

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


# =============================================================================
# CORREÇÃO: relatorio_compras_dados_api
# SUBSTITUIR a função existente no views.py
# =============================================================================

@login_required
@require_GET
def relatorio_compras_dados_api(request):
    """
    API para dados do relatório de compras.
    CORREÇÃO: Retorna formato compatível com o template (metricas, compras, 
    evolucao_mensal, top_fornecedores, top_produtos).
    """
    try:
        data_inicio = request.GET.get('data_inicio')
        data_fim = request.GET.get('data_fim')
        fornecedor_id = request.GET.get('fornecedor', '')

        # Base query: NFs confirmadas
        notas = NotaFiscalEntrada.objects.filter(status='confirmada')
        
        if data_inicio:
            notas = notas.filter(data_entrada__gte=data_inicio)
        if data_fim:
            notas = notas.filter(data_entrada__lte=data_fim)
        if fornecedor_id:
            notas = notas.filter(fornecedor_id=fornecedor_id)

        # =====================================================================
        # MÉTRICAS PRINCIPAIS
        # =====================================================================
        totais = notas.aggregate(
            total_notas=Count('id'),
            total_valor=Sum('valor_total'),
            total_produtos=Sum('valor_produtos'),
            total_impostos=Sum('valor_impostos'),
        )
        
        total_nfs = totais['total_notas'] or 0
        total_compras = float(totais['total_valor'] or 0)
        ticket_medio = total_compras / total_nfs if total_nfs > 0 else 0
        
        fornecedores_ativos = notas.values('fornecedor').distinct().count()

        # Variação vs período anterior
        variacao_compras = None
        variacao_nfs = None
        if data_inicio and data_fim:
            try:
                dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                dt_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
                dias_periodo = (dt_fim - dt_inicio).days
                
                if dias_periodo > 0:
                    periodo_anterior_inicio = dt_inicio - timedelta(days=dias_periodo)
                    periodo_anterior_fim = dt_inicio - timedelta(days=1)
                    
                    notas_anterior = NotaFiscalEntrada.objects.filter(
                        status='confirmada',
                        data_entrada__gte=periodo_anterior_inicio,
                        data_entrada__lte=periodo_anterior_fim
                    )
                    if fornecedor_id:
                        notas_anterior = notas_anterior.filter(fornecedor_id=fornecedor_id)
                    
                    totais_anterior = notas_anterior.aggregate(
                        total_valor=Sum('valor_total'),
                        total_notas=Count('id')
                    )
                    
                    valor_anterior = float(totais_anterior['total_valor'] or 0)
                    nfs_anterior = totais_anterior['total_notas'] or 0
                    
                    if valor_anterior > 0:
                        variacao_compras = ((total_compras - valor_anterior) / valor_anterior) * 100
                    elif total_compras > 0:
                        variacao_compras = 100.0
                    
                    if nfs_anterior > 0:
                        variacao_nfs = ((total_nfs - nfs_anterior) / nfs_anterior) * 100
                    elif total_nfs > 0:
                        variacao_nfs = 100.0
            except (ValueError, TypeError):
                pass

        metricas = {
            'total_compras': total_compras,
            'total_nfs': total_nfs,
            'ticket_medio': ticket_medio,
            'fornecedores_ativos': fornecedores_ativos,
            'variacao_compras': variacao_compras,
            'variacao_nfs': variacao_nfs,
        }

        # =====================================================================
        # LISTA DE COMPRAS (DETALHAMENTO)
        # =====================================================================
        compras_list = []
        for nota in notas.select_related('fornecedor').prefetch_related('itens__produto').order_by('-data_entrada'):
            # Lista de produtos da NF
            produtos_nomes = []
            total_itens = 0
            for item in nota.itens.all():
                total_itens += 1
                nome = item.descricao or (item.produto.descricao if item.produto else 'Sem descrição')
                if nome not in produtos_nomes:
                    produtos_nomes.append(nome)
            
            produtos_str = ', '.join(produtos_nomes[:3])
            if len(produtos_nomes) > 3:
                produtos_str += f' +{len(produtos_nomes) - 3}'
            
            compras_list.append({
                'id': nota.id,
                'data_entrada': nota.data_entrada.isoformat() if nota.data_entrada else None,
                'fornecedor_nome': nota.fornecedor.nome_razao_social if nota.fornecedor else 'N/A',
                'numero_nf': nota.numero_nf,
                'total_itens': total_itens,
                'valor_total': float(nota.valor_total or 0),
                'produtos_list': produtos_str or '-',
            })

        # =====================================================================
        # EVOLUÇÃO MENSAL
        # =====================================================================
        evolucao_mensal = []
        try:
            from django.db.models.functions import TruncMonth
            
            compras_por_mes = notas.annotate(
                mes_trunc=TruncMonth('data_entrada')
            ).values('mes_trunc').annotate(
                total=Sum('valor_total'),
                quantidade=Count('id')
            ).order_by('mes_trunc')
            
            meses_nome = [
                '', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'
            ]
            
            for item in compras_por_mes:
                if item['mes_trunc']:
                    mes_dt = item['mes_trunc']
                    mes_label = f"{meses_nome[mes_dt.month]}/{mes_dt.year}"
                    evolucao_mensal.append({
                        'mes': mes_label,
                        'valor': float(item['total'] or 0),
                        'quantidade': item['quantidade'] or 0,
                    })
        except Exception as e:
            logger.warning(f"Erro ao calcular evolução mensal: {e}")

        # =====================================================================
        # TOP FORNECEDORES
        # =====================================================================
        top_fornecedores = []
        try:
            fornecedores_ranking = notas.values(
                'fornecedor__id',
                'fornecedor__nome_razao_social',
                'fornecedor__nome_fantasia'
            ).annotate(
                total_compras=Sum('valor_total'),
                quantidade_notas=Count('id')
            ).order_by('-total_compras')[:5]
            
            for f in fornecedores_ranking:
                nome = f['fornecedor__nome_fantasia'] or f['fornecedor__nome_razao_social'] or 'N/A'
                top_fornecedores.append({
                    'id': f['fornecedor__id'],
                    'nome': nome,
                    'valor': float(f['total_compras'] or 0),
                    'quantidade': f['quantidade_notas'] or 0,
                })
        except Exception as e:
            logger.warning(f"Erro ao calcular top fornecedores: {e}")

        # =====================================================================
        # TOP PRODUTOS
        # =====================================================================
        top_produtos = []
        try:
            produtos_ranking = ItemNotaFiscalEntrada.objects.filter(
                nota_fiscal__in=notas,
                produto__isnull=False
            ).values(
                'produto__id',
                'produto__descricao'
            ).annotate(
                total_quantidade=Sum('quantidade'),
                total_valor=Sum('preco_total')
            ).order_by('-total_quantidade')[:5]
            
            for p in produtos_ranking:
                top_produtos.append({
                    'id': p['produto__id'],
                    'nome': p['produto__descricao'] or 'Sem nome',
                    'quantidade': float(p['total_quantidade'] or 0),
                    'valor': float(p['total_valor'] or 0),
                })
        except Exception as e:
            logger.warning(f"Erro ao calcular top produtos: {e}")

        # =====================================================================
        # RESPOSTA FINAL
        # =====================================================================
        return JsonResponse({
            'success': True,
            'metricas': metricas,
            'compras': compras_list,
            'evolucao_mensal': evolucao_mensal,
            'top_fornecedores': top_fornecedores,
            'top_produtos': top_produtos,
            # Manter compatibilidade com formato antigo
            'totais': {
                'notas': total_nfs,
                'valor_total': total_compras,
                'produtos': float(totais['total_produtos'] or 0),
                'impostos': float(totais['total_impostos'] or 0),
            },
        })
        
    except Exception as e:
        log_erro_seguro('relatorio_compras_dados_api', e, request)
        return JsonResponse({
            'success': False,
            'message': f'Erro ao gerar relatório: {str(e)}',
            'metricas': {
                'total_compras': 0, 'total_nfs': 0,
                'ticket_medio': 0, 'fornecedores_ativos': 0,
            },
            'compras': [],
            'evolucao_mensal': [],
            'top_fornecedores': [],
            'top_produtos': [],
        }, status=400)


@login_required
@require_GET
def relatorio_compras_exportar_api(request):
    """API para exportar relatório de compras (CSV)"""
    try:
        formato = request.GET.get('formato', 'csv')
        data_inicio = request.GET.get('data_inicio')
        data_fim = request.GET.get('data_fim')

        # ✅ CORREÇÃO: Status minúsculo
        notas = NotaFiscalEntrada.objects.filter(status='confirmada')
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
# MÓDULO: VENDAS - ORÇAMENTOS (PADRÃO MANAGER + FORM)
# =============================================================================

@login_required
def orcamento_manager(request):
    """
    View consolidada para listar orçamentos.
    """
    from django.db import models
    
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    orcamentos = Orcamento.objects.select_related('cliente', 'vendedor').all().order_by('-data_orcamento')
    
    if search:
        orcamentos = orcamentos.filter(
            models.Q(numero__icontains=search) |
            models.Q(cliente__nome_razao_social__icontains=search)
        )
    
    if status:
        orcamentos = orcamentos.filter(status=status)
    
    paginator = Paginator(orcamentos, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Totais para cards de resumo
    total = orcamentos.count()
    total_pendentes = orcamentos.filter(status='pendente').count()
    total_aprovados = orcamentos.filter(status='aprovado').count()
    valor_total = sum(o.valor_total for o in orcamentos) if orcamentos else 0
    
    context = {
        'page_obj': page_obj,
        'total': total,
        'total_pendentes': total_pendentes,
        'total_aprovados': total_aprovados,
        'valor_total': valor_total,
        'search': search,
        'status': status,
    }
    return render(request, 'vendas/orcamento_manager.html', context)


@login_required
def orcamento_form(request, pk=None):
    """
    View consolidada para criar/editar orçamento com itens inline.
    """
    from decimal import Decimal, InvalidOperation
    
    orcamento = None
    if pk:
        orcamento = get_object_or_404(Orcamento, pk=pk)
    
    # Dados para selects
    clientes = Cliente.objects.filter(ativo=True).order_by('nome_razao_social')
    vendedores = Vendedor.objects.filter(ativo=True).order_by('nome')
    produtos = Produto.objects.filter(ativo=True).order_by('descricao')
    try:
        condicoes_pagamento = CondicaoPagamento.objects.filter(ativo=True).order_by('descricao')
    except Exception:
        condicoes_pagamento = CondicaoPagamento.objects.all().order_by('descricao')
    
    status_choices = getattr(Orcamento, 'STATUS_CHOICES', [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
        ('convertido', 'Convertido em Pedido'),
    ])
    
    if request.method == 'POST':
        action = request.POST.get('action', '')
        
        if action == 'update_header':
            if orcamento:
                form = OrcamentoForm(request.POST, instance=orcamento)
            else:
                form = OrcamentoForm(request.POST)
            
            if form.is_valid():
                orcamento = form.save()
                messages.success(request, f'Orçamento {orcamento.numero} {"atualizado" if pk else "criado"} com sucesso!')
                return redirect('ERP_ServicesBI:orcamento_form', pk=orcamento.pk)  # CORRIGIDO: nome consistente
        
        elif action == 'add_item' and orcamento:
            produto_id = request.POST.get('produto')
            quantidade = request.POST.get('quantidade', '1')
            preco_unitario_str = request.POST.get('preco_unitario', '0').replace('.', '').replace(',', '.')
            desconto_str = request.POST.get('desconto', '0').replace('.', '').replace(',', '.')
            
            try:
                preco_unitario = Decimal(preco_unitario_str)
                desconto = Decimal(desconto_str)
                quantidade = Decimal(quantidade.replace(',', '.'))
                produto = get_object_or_404(Produto, pk=produto_id)
                
                ItemOrcamento.objects.create(
                    orcamento=orcamento,
                    produto=produto,
                    quantidade=quantidade,
                    preco_unitario=preco_unitario,
                    desconto=desconto
                )
                orcamento.calcular_total()
                messages.success(request, 'Item adicionado com sucesso!')
            except (InvalidOperation, ValueError) as e:
                messages.error(request, f'Erro nos valores numéricos: {str(e)}')
            except Exception as e:
                messages.error(request, f'Erro ao adicionar item: {str(e)}')
            
            return redirect('ERP_ServicesBI:orcamento_form', pk=orcamento.pk)  # CORRIGIDO
        
        elif action == 'update_item' and orcamento:
            item_id = request.POST.get('item_id')
            item = get_object_or_404(ItemOrcamento, pk=item_id, orcamento=orcamento)
            
            preco_str = request.POST.get('preco_unitario', '0').replace('.', '').replace(',', '.')
            desc_str = request.POST.get('desconto', '0').replace('.', '').replace(',', '.')
            qtd_str = request.POST.get('quantidade', '1').replace(',', '.')
            
            try:
                item.quantidade = Decimal(qtd_str)
                item.preco_unitario = Decimal(preco_str)
                item.desconto = Decimal(desc_str)
                item.save()
                orcamento.calcular_total()
                messages.success(request, 'Item atualizado com sucesso!')
            except (InvalidOperation, ValueError) as e:
                messages.error(request, f'Erro nos valores numéricos: {str(e)}')
            except Exception as e:
                messages.error(request, f'Erro ao atualizar item: {str(e)}')
            
            return redirect('ERP_ServicesBI:orcamento_form', pk=orcamento.pk)  # CORRIGIDO
        
        elif action == 'remove_item' and orcamento:
            item_id = request.POST.get('item_id')
            item = get_object_or_404(ItemOrcamento, pk=item_id, orcamento=orcamento)
            item.delete()
            orcamento.calcular_total()
            messages.success(request, 'Item removido com sucesso!')
            return redirect('ERP_ServicesBI:orcamento_form', pk=orcamento.pk)  # CORRIGIDO
    
    if orcamento:
        form = OrcamentoForm(instance=orcamento)
        itens = ItemOrcamento.objects.filter(orcamento=orcamento).select_related('produto')
    else:
        form = OrcamentoForm(initial={
            'data_orcamento': date.today(),
            'data_validade': date.today() + timedelta(days=7),
            'status': 'pendente'
        })
        itens = []
    
    context = {
        'form': form,
        'orcamento': orcamento,
        'clientes': clientes,
        'vendedores': vendedores,
        'condicoes_pagamento': condicoes_pagamento,
        'produtos': produtos,
        'status_choices': status_choices,
        'itens': itens,
        'titulo': 'Editar Orçamento' if orcamento else 'Novo Orçamento',
    }
    return render(request, 'vendas/orcamento_form.html', context)


@login_required
@require_POST
def orcamento_excluir_api(request, pk):
    """API para exclusão AJAX de orçamento."""
    orcamento = get_object_or_404(Orcamento, pk=pk)
    
    try:
        numero = orcamento.numero
        orcamento.delete()
        return JsonResponse({
            'success': True, 
            'message': f'Orçamento {numero} excluído com sucesso!'
        })
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': f'Erro ao excluir: {str(e)}'
        })

@login_required
def orcamento_gerar_pedido(request, pk):
    """Geração de pedido a partir do orçamento"""
    orcamento = get_object_or_404(Orcamento, pk=pk)
    return render(request, 'vendas/gerar_pedido.html', {'orcamento': orcamento})

# =============================================================================
# MÓDULO: VENDAS - PEDIDOS DE VENDA (PADRÃO MANAGER + FORM - NOVO)
# =============================================================================

@login_required
def pedido_venda_manager(request):
    """
    View consolidada para listar pedidos de venda.
    Substitui: pedido_venda_list
    """
    from django.db import models
    
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    pedidos = PedidoVenda.objects.select_related('cliente', 'vendedor').all().order_by('-data_pedido')
    
    if search:
        pedidos = pedidos.filter(
            models.Q(numero__icontains=search) |
            models.Q(cliente__nome_razao_social__icontains=search)
        )
    
    if status:
        pedidos = pedidos.filter(status=status)
    
    paginator = Paginator(pedidos, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Totais para cards
    total = pedidos.count()
    total_pendentes = pedidos.filter(status='pendente').count()
    total_aprovados = pedidos.filter(status='aprovado').count()
    valor_total = sum(p.valor_total for p in pedidos) if pedidos else 0
    
    context = {
        'page_obj': page_obj,
        'total': total,
        'total_pendentes': total_pendentes,
        'total_aprovados': total_aprovados,
        'valor_total': valor_total,
        'search': search,
        'status': status,
    }
    return render(request, 'vendas/pedido_venda_manager.html', context)


@login_required
def pedido_venda_form(request, pk=None):
    """
    View consolidada para criar/editar pedido de venda com itens inline.
    Substitui: pedido_venda_add + pedido_venda_edit + pedido_venda_item_add
    """
    from decimal import Decimal, InvalidOperation
    
    pedido = None
    if pk:
        pedido = get_object_or_404(PedidoVenda, pk=pk)
    
    clientes = Cliente.objects.filter(ativo=True).order_by('nome_razao_social')
    vendedores = Vendedor.objects.filter(ativo=True).order_by('nome')
    produtos = Produto.objects.filter(ativo=True).order_by('descricao')
    try:
        condicoes_pagamento = CondicaoPagamento.objects.filter(ativo=True).order_by('descricao')
    except Exception:
        condicoes_pagamento = CondicaoPagamento.objects.all().order_by('descricao')
    
    status_choices = getattr(PedidoVenda, 'STATUS_CHOICES', [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('em_separacao', 'Em Separação'),
        ('faturado', 'Faturado'),
        ('entregue', 'Entregue'),
        ('cancelado', 'Cancelado'),
    ])
    
    if request.method == 'POST':
        action = request.POST.get('action', '')
        
        if action == 'update_header':
            if pedido:
                form = PedidoVendaForm(request.POST, instance=pedido)
            else:
                form = PedidoVendaForm(request.POST)
            
            if form.is_valid():
                pedido = form.save()
                messages.success(request, f'Pedido {pedido.numero} {"atualizado" if pk else "criado"} com sucesso!')
                return redirect('ERP_ServicesBI:pedido_venda_form', pk=pedido.pk)
        
        elif action == 'add_item' and pedido:
            produto_id = request.POST.get('produto')
            quantidade_str = request.POST.get('quantidade', '1')
            preco_str = request.POST.get('preco_unitario', '0').replace('.', '').replace(',', '.')
            desconto_str = request.POST.get('desconto', '0').replace('.', '').replace(',', '.')
            
            try:
                preco_unitario = Decimal(preco_str)
                desconto = Decimal(desconto_str)
                quantidade = Decimal(quantidade_str.replace(',', '.'))
                produto = get_object_or_404(Produto, pk=produto_id)
                
                ItemPedidoVenda.objects.create(
                    pedido=pedido,
                    produto=produto,
                    quantidade=quantidade,
                    preco_unitario=preco_unitario,
                    desconto=desconto
                )
                pedido.calcular_total()
                messages.success(request, 'Item adicionado com sucesso!')
            except (InvalidOperation, ValueError) as e:
                messages.error(request, f'Erro nos valores numéricos: verifique os valores inseridos.')
            except Exception as e:
                messages.error(request, f'Erro ao adicionar item: {str(e)}')
            
            return redirect('ERP_ServicesBI:pedido_venda_form', pk=pedido.pk)
        
        elif action == 'update_item' and pedido:
            item_id = request.POST.get('item_id')
            item = get_object_or_404(ItemPedidoVenda, pk=item_id, pedido=pedido)
            
            preco_str = request.POST.get('preco_unitario', '0').replace('.', '').replace(',', '.')
            desc_str = request.POST.get('desconto', '0').replace('.', '').replace(',', '.')
            qtd_str = request.POST.get('quantidade', '1').replace(',', '.')
            
            try:
                item.quantidade = Decimal(qtd_str)
                item.preco_unitario = Decimal(preco_str)
                item.desconto = Decimal(desc_str)
                item.save()
                pedido.calcular_total()
                messages.success(request, 'Item atualizado com sucesso!')
            except (InvalidOperation, ValueError) as e:
                messages.error(request, f'Erro nos valores numéricos: verifique os valores inseridos.')
            except Exception as e:
                messages.error(request, f'Erro ao atualizar item: {str(e)}')
            
            return redirect('ERP_ServicesBI:pedido_venda_form', pk=pedido.pk)
        
        elif action == 'remove_item' and pedido:
            item_id = request.POST.get('item_id')
            item = get_object_or_404(ItemPedidoVenda, pk=item_id, pedido=pedido)
            item.delete()
            pedido.calcular_total()
            messages.success(request, 'Item removido com sucesso!')
            return redirect('ERP_ServicesBI:pedido_venda_form', pk=pedido.pk)
    
    if pedido:
        form = PedidoVendaForm(instance=pedido)
        itens = ItemPedidoVenda.objects.filter(pedido=pedido).select_related('produto')
    else:
        form = PedidoVendaForm(initial={
            'data_pedido': date.today(),
            'status': 'pendente'
        })
        itens = []
    
    context = {
        'form': form,
        'pedido': pedido,
        'clientes': clientes,
        'vendedores': vendedores,
        'condicoes_pagamento': condicoes_pagamento,
        'produtos': produtos,
        'status_choices': status_choices,
        'itens': itens,
        'titulo': 'Editar Pedido de Venda' if pedido else 'Novo Pedido de Venda',
    }
    return render(request, 'vendas/pedido_venda_form.html', context)


@login_required
@require_POST
def pedido_venda_excluir_api(request, pk):
    """API para exclusão AJAX de pedido de venda."""
    pedido = get_object_or_404(PedidoVenda, pk=pk)
    
    try:
        numero = pedido.numero
        pedido.delete()
        return JsonResponse({
            'success': True, 
            'message': f'Pedido {numero} excluído com sucesso!'
        })
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': f'Erro ao excluir: {str(e)}'
        })

@login_required
def pedido_venda_gerar_nfe(request, pk):
    """Geração de NF de saída a partir do pedido de venda"""
    pedido = get_object_or_404(PedidoVenda, pk=pk)
    return render(request, 'vendas/gerar_nfe.html', {'pedido': pedido})

# =============================================================================
# MÓDULO: VENDAS - NOTAS FISCAIS DE SAÍDA (PADRÃO MANAGER + FORM - NOVO)
# =============================================================================

@login_required
def nota_fiscal_saida_manager(request):
    """
    View consolidada para listar notas fiscais de saída.
    Substitui: nota_fiscal_saida_list
    """
    from django.db import models
    
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    notas = NotaFiscalSaida.objects.select_related('cliente', 'pedido_origem').all().order_by('-data_emissao')
    
    if search:
        notas = notas.filter(
            models.Q(numero_nf__icontains=search) |
            models.Q(cliente__nome_razao_social__icontains=search) |
            models.Q(chave_acesso__icontains=search)
        )
    
    if status:
        notas = notas.filter(status=status)
    
    paginator = Paginator(notas, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    total = notas.count()
    total_emitidas = notas.filter(status='emitida').count()
    total_canceladas = notas.filter(status='cancelada').count()
    valor_total = sum(n.valor_total for n in notas) if notas else 0
    
    context = {
        'page_obj': page_obj,
        'total': total,
        'total_emitidas': total_emitidas,
        'total_canceladas': total_canceladas,
        'valor_total': valor_total,
        'search': search,
        'status': status,
    }
    return render(request, 'vendas/nota_fiscal_saida_manager.html', context)


@login_required
def nota_fiscal_saida_form(request, pk=None):
    """
    View consolidada para criar/editar NF de saída com itens inline.
    Substitui: nota_fiscal_saida_add + nota_fiscal_saida_edit + nota_fiscal_saida_item_add
    """
    from decimal import Decimal, InvalidOperation
    
    nota = None
    if pk:
        nota = get_object_or_404(NotaFiscalSaida, pk=pk)
    
    clientes = Cliente.objects.filter(ativo=True).order_by('nome_razao_social')
    produtos = Produto.objects.filter(ativo=True).order_by('descricao')
    pedidos = PedidoVenda.objects.filter(status='aprovado').order_by('-data_pedido')
    
    status_choices = getattr(NotaFiscalSaida, 'STATUS_CHOICES', [
        ('em_digitacao', 'Em Digitação'),
        ('emitida', 'Emitida'),
        ('cancelada', 'Cancelada'),
    ])
    
    if request.method == 'POST':
        action = request.POST.get('action', '')
        
        if action == 'update_header':
            if nota:
                form = NotaFiscalSaidaForm(request.POST, instance=nota)
            else:
                form = NotaFiscalSaidaForm(request.POST)
            
            if form.is_valid():
                nota = form.save()
                messages.success(request, f'NF {nota.numero_nf} {"atualizada" if pk else "criada"} com sucesso!')
                return redirect('ERP_ServicesBI:nota_fiscal_saida_form', pk=nota.pk)
        
        elif action == 'add_item' and nota:
            produto_id = request.POST.get('produto')
            quantidade_str = request.POST.get('quantidade', '1')
            preco_str = request.POST.get('preco_unitario', '0').replace('.', '').replace(',', '.')
            desconto_str = request.POST.get('desconto', '0').replace('.', '').replace(',', '.')
            
            try:
                preco_unitario = Decimal(preco_str)
                desconto = Decimal(desconto_str)
                quantidade = Decimal(quantidade_str.replace(',', '.'))
                produto = get_object_or_404(Produto, pk=produto_id)
                
                ItemNotaFiscalSaida.objects.create(
                    nota_fiscal=nota,
                    produto=produto,
                    quantidade=quantidade,
                    preco_unitario=preco_unitario,
                    desconto=desconto
                )
                nota.calcular_total()
                messages.success(request, 'Item adicionado com sucesso!')
            except (InvalidOperation, ValueError):
                messages.error(request, 'Erro nos valores numéricos: verifique os valores inseridos.')
            except Exception as e:
                messages.error(request, f'Erro ao adicionar item: {str(e)}')
            
            return redirect('ERP_ServicesBI:nota_fiscal_saida_form', pk=nota.pk)
        
        elif action == 'update_item' and nota:
            item_id = request.POST.get('item_id')
            item = get_object_or_404(ItemNotaFiscalSaida, pk=item_id, nota_fiscal=nota)
            
            preco_str = request.POST.get('preco_unitario', '0').replace('.', '').replace(',', '.')
            desc_str = request.POST.get('desconto', '0').replace('.', '').replace(',', '.')
            qtd_str = request.POST.get('quantidade', '1').replace(',', '.')
            
            try:
                item.quantidade = Decimal(qtd_str)
                item.preco_unitario = Decimal(preco_str)
                item.desconto = Decimal(desc_str)
                item.save()
                nota.calcular_total()
                messages.success(request, 'Item atualizado com sucesso!')
            except (InvalidOperation, ValueError):
                messages.error(request, 'Erro nos valores numéricos: verifique os valores inseridos.')
            except Exception as e:
                messages.error(request, f'Erro ao atualizar item: {str(e)}')
            
            return redirect('ERP_ServicesBI:nota_fiscal_saida_form', pk=nota.pk)
        
        elif action == 'remove_item' and nota:
            item_id = request.POST.get('item_id')
            item = get_object_or_404(ItemNotaFiscalSaida, pk=item_id, nota_fiscal=nota)
            item.delete()
            nota.calcular_total()
            messages.success(request, 'Item removido com sucesso!')
            return redirect('ERP_ServicesBI:nota_fiscal_saida_form', pk=nota.pk)
    
    if nota:
        form = NotaFiscalSaidaForm(instance=nota)
        itens = ItemNotaFiscalSaida.objects.filter(nota_fiscal=nota).select_related('produto')
    else:
        form = NotaFiscalSaidaForm(initial={
            'data_emissao': date.today(),
            'status': 'em_digitacao'
        })
        itens = []
    
    context = {
        'form': form,
        'nota': nota,
        'clientes': clientes,
        'produtos': produtos,
        'pedidos': pedidos,
        'status_choices': status_choices,
        'itens': itens,
        'titulo': 'Editar Nota Fiscal de Saída' if nota else 'Nova Nota Fiscal de Saída',
    }
    return render(request, 'vendas/nota_fiscal_saida_form.html', context)


@login_required
@require_POST
def nota_fiscal_saida_excluir_api(request, pk):
    """API para exclusão AJAX de NF de saída."""
    nota = get_object_or_404(NotaFiscalSaida, pk=pk)
    
    # Verificar se NF já foi emitida (não permitir exclusão)
    if nota.status == 'emitida':
        return JsonResponse({
            'success': False,
            'message': 'Não é possível excluir uma NF já emitida. Cancele primeiro.'
        })
    
    try:
        numero = nota.numero_nf
        nota.delete()
        return JsonResponse({
            'success': True, 
            'message': f'NF {numero} excluída com sucesso!'
        })
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': f'Erro ao excluir: {str(e)}'
        })


# =============================================================================
# MÓDULO: VENDAS - RELATÓRIOS
# =============================================================================

@login_required
def relatorio_vendas(request):
    """Relatório de vendas"""
    return render(request, 'vendas/relatorio_vendas.html', {})


# =============================================================================
# MÓDULO: FINANCEIRO 
# =============================================================================
# UTILITÁRIOS INTERNOS
# =============================================================================

def _parse_date(date_str):
    """Converte string YYYY-MM-DD para date object"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


def _format_currency_br(value):
    """Formata Decimal para string moeda brasileira (1.234,56)"""
    if value is None:
        return "0,00"
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _decimal_from_br(valor_str):
    """Converte string moeda brasileira (R$ 1.234,56) para Decimal"""
    if not valor_str:
        return Decimal('0')
    # Remove R$, espaços, troca pontos de milhar e vírgula decimal
    limpo = valor_str.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
    try:
        return Decimal(limpo)
    except:
        return Decimal('0')


# =============================================================================
# 1. RELATÓRIO FINANCEIRO (Dashboard Principal)
# =============================================================================

@login_required
def relatorio_financeiro(request):
    """
    Dashboard financeiro estilo Power BI
    Período padrão: mês atual
    """
    hoje = timezone.now().date()
    
    # Processar período
    data_inicial = request.GET.get('data_inicial')
    data_final = request.GET.get('data_final')
    tipo_relatorio = request.GET.get('tipo_relatorio', 'geral')
    
    if data_inicial:
        data_inicial = _parse_date(data_inicial)
    else:
        data_inicial = hoje.replace(day=1)
    
    if data_final:
        data_final = _parse_date(data_final)
    else:
        ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
        data_final = hoje.replace(day=ultimo_dia)
    
    # Calcular período anterior para comparação
    delta_dias = (data_final - data_inicial).days
    data_inicial_ant = data_inicial - timedelta(days=delta_dias + 1)
    data_final_ant = data_inicial - timedelta(days=1)
    
    # Movimentações do período
    movimentacoes = MovimentoCaixa.objects.filter(
        data__range=[data_inicial, data_final]
    ).order_by('-data')
    
    if tipo_relatorio == 'receitas':
        movimentacoes = movimentacoes.filter(tipo='entrada')
    elif tipo_relatorio == 'despesas':
        movimentacoes = movimentacoes.filter(tipo='saida')
    
    # KPIs Principais
    entradas = movimentacoes.filter(tipo='entrada').aggregate(
        total=Sum('valor')
    )['total'] or Decimal('0')
    
    saidas = movimentacoes.filter(tipo='saida').aggregate(
        total=Sum('valor')
    )['total'] or Decimal('0')
    
    saldo = entradas - saidas
    
    # Período anterior (trends)
    entradas_ant = MovimentoCaixa.objects.filter(
        data__range=[data_inicial_ant, data_final_ant],
        tipo='entrada'
    ).aggregate(total=Sum('valor'))['total'] or Decimal('0')
    
    saidas_ant = MovimentoCaixa.objects.filter(
        data__range=[data_inicial_ant, data_final_ant],
        tipo='saida'
    ).aggregate(total=Sum('valor'))['total'] or Decimal('0')
    
    # Variações percentuais
    var_entradas = ((entradas - entradas_ant) / entradas_ant * 100) if entradas_ant > 0 else 0
    var_saidas = ((saidas - saidas_ant) / saidas_ant * 100) if saidas_ant > 0 else 0
    
    # Contas em aberto
    contas_receber_aberto = ContaReceber.objects.filter(
        status__in=['pendente', 'parcial']
    ).aggregate(total=Sum('valor_saldo'))['total'] or Decimal('0')
    
    contas_receber_vencidas = ContaReceber.objects.filter(
        status__in=['pendente', 'parcial'],
        data_vencimento__lt=hoje
    ).aggregate(total=Sum('valor_saldo'))['total'] or Decimal('0')
    
    contas_pagar_aberto = ContaPagar.objects.filter(
        status__in=['pendente', 'parcial']
    ).aggregate(total=Sum('valor_saldo'))['total'] or Decimal('0')
    
    contas_pagar_vencidas = ContaPagar.objects.filter(
        status__in=['pendente', 'parcial'],
        data_vencimento__lt=hoje
    ).aggregate(total=Sum('valor_saldo'))['total'] or Decimal('0')
    
    # Dados para gráficos
    from django.db.models.functions import TruncDate, TruncMonth
    
    mov_diario = MovimentoCaixa.objects.filter(
        data__range=[data_inicial, data_final]
    ).annotate(
        dia=TruncDate('data')
    ).values('dia').annotate(
        entradas=Sum('valor', filter=Q(tipo='entrada')),
        saidas=Sum('valor', filter=Q(tipo='saida'))
    ).order_by('dia')
    
    datas_labels = [m['dia'].strftime('%d/%m') for m in mov_diario]
    entradas_diarias = [float(m['entradas'] or 0) for m in mov_diario]
    saidas_diarias = [float(m['saidas'] or 0) for m in mov_diario]
    
    # Gráfico mensal (últimos 6 meses)
    seis_meses_atras = hoje - timedelta(days=180)
    mov_mensal = MovimentoCaixa.objects.filter(
        data__gte=seis_meses_atras
    ).annotate(
        mes=TruncMonth('data')
    ).values('mes').annotate(
        entradas=Sum('valor', filter=Q(tipo='entrada')),
        saidas=Sum('valor', filter=Q(tipo='saida'))
    ).order_by('mes')
    
    meses_labels = [m['mes'].strftime('%b/%Y') for m in mov_mensal]
    entradas_mensais = [float(m['entradas'] or 0) for m in mov_mensal]
    saidas_mensais = [float(m['saidas'] or 0) for m in mov_mensal]
    
    # Top categorias de despesa
    categorias_despesa = CategoriaFinanceira.objects.filter(
    tipo='despesa',
    contas_pagar__data_pagamento__range=[data_inicial, data_final],
    contas_pagar__status__in=['pago', 'quitado']
    ).annotate(
            total=Sum('contas_pagar__valor_pago')
    ).order_by('-total')[:5]
    
    categorias_vendas = []
    total_cat = sum([c.total for c in categorias_despesa]) or Decimal('1')
    cores = ['#3b82f6', '#22c55e', '#f59e0b', '#8b5cf6', '#ef4444']
    for i, cat in enumerate(categorias_despesa):
        percentual = (cat.total / total_cat) * 100
        categorias_vendas.append({
            'nome': cat.nome,
            'valor': float(cat.total),
            'percentual': percentual,
            'cor': cores[i % len(cores)]
        })
    
    context = {
        'data_inicial': data_inicial.strftime('%Y-%m-%d'),
        'data_final': data_final.strftime('%Y-%m-%d'),
        'tipo_relatorio': tipo_relatorio,
        'entradas': entradas,
        'saidas': saidas,
        'saldo': saldo,
        'var_entradas': var_entradas,
        'var_saidas': var_saidas,
        'contas_receber_aberto': contas_receber_aberto,
        'contas_receber_vencidas': contas_receber_vencidas,
        'contas_pagar_aberto': contas_pagar_aberto,
        'contas_pagar_vencidas': contas_pagar_vencidas,
        'datas_labels': datas_labels,
        'entradas_diarias': entradas_diarias,
        'saidas_diarias': saidas_diarias,
        'meses_labels': meses_labels,
        'entradas_mensais': entradas_mensais,
        'saidas_mensais': saidas_mensais,
        'categorias_vendas': categorias_vendas,
        'movimentacoes': movimentacoes[:50],
    }
    
    return render(request, 'financeiro/relatorio_financeiro.html', context)


# =============================================================================
# 2. FLUXO DE CAIXA
# =============================================================================

@login_required
def fluxo_caixa_list(request):
    """
    Lista/Dashboard de fluxo de caixa
    URL: /financeiro/fluxo-caixa/
    Template: fluxo_caixa_manager.html
    """
    hoje = timezone.now().date()
    
    # Período: 30 dias para trás e 30 para frente
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    if data_inicio:
        data_inicio = _parse_date(data_inicio)
    else:
        data_inicio = hoje - timedelta(days=30)
    
    if data_fim:
        data_fim = _parse_date(data_fim)
    else:
        data_fim = hoje + timedelta(days=30)
    
    # Movimentações
    movimentacoes = MovimentoCaixa.objects.filter(
        data__range=[data_inicio, data_fim]
    ).order_by('-data')
    
    # Contas pendentes no período
    contas_receber = ContaReceber.objects.filter(
        data_vencimento__range=[data_inicio, data_fim],
        status__in=['pendente', 'parcial']
    )
    
    contas_pagar = ContaPagar.objects.filter(
        data_vencimento__range=[data_inicio, data_fim],
        status__in=['pendente', 'parcial']
    )
    
    # Saldo atual
    saldo_atual = MovimentoCaixa.objects.filter(
        data__lte=hoje
    ).values('tipo').annotate(total=Sum('valor'))
    
    entradas = sum([m['total'] for m in saldo_atual if m['tipo'] == 'entrada'])
    saidas = sum([m['total'] for m in saldo_atual if m['tipo'] == 'saida'])
    saldo = entradas - saidas
    
    context = {
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'movimentacoes': movimentacoes,
        'contas_receber': contas_receber,
        'contas_pagar': contas_pagar,
        'saldo_atual': saldo,
        'total_receber': contas_receber.aggregate(total=Sum('valor_saldo'))['total'] or 0,
        'total_pagar': contas_pagar.aggregate(total=Sum('valor_saldo'))['total'] or 0,
    }
    return render(request, 'financeiro/fluxo_caixa_manager.html', context)


@login_required
def fluxo_caixa_add(request):
    """
    Nova movimentação de caixa
    URL: /financeiro/fluxo-caixa/adicionar/
    Template: fluxo_caixa_form.html
    """
    if request.method == 'POST':
        form = MovimentoCaixaForm(request.POST)
        if form.is_valid():
            mov = form.save(commit=False)
            mov.usuario = request.user
            mov.save()
            messages.success(request, 'Movimentação registrada com sucesso!')
            return redirect('ERP_ServicesBI:fluxo_caixa_list')
    else:
        form = MovimentoCaixaForm()
    
    return render(request, 'financeiro/fluxo_caixa_form.html', {
        'form': form,
        'titulo': 'Nova Movimentação de Caixa',
        'movimentacao': None,
    })


@login_required
def fluxo_caixa_edit(request, pk):
    """
    Editar movimentação de caixa
    URL: /financeiro/fluxo-caixa/<pk>/editar/
    Template: fluxo_caixa_form.html
    """
    movimentacao = get_object_or_404(MovimentoCaixa, pk=pk)
    
    if request.method == 'POST':
        form = MovimentoCaixaForm(request.POST, instance=movimentacao)
        if form.is_valid():
            form.save()
            messages.success(request, 'Movimentação atualizada com sucesso!')
            return redirect('ERP_ServicesBI:fluxo_caixa_list')
    else:
        form = MovimentoCaixaForm(instance=movimentacao)
    
    return render(request, 'financeiro/fluxo_caixa_form.html', {
        'form': form,
        'titulo': 'Editar Movimentação de Caixa',
        'movimentacao': movimentacao,
    })


@login_required
@require_POST
def fluxo_caixa_delete(request, pk):
    """
    Excluir movimentação de caixa
    URL: /financeiro/fluxo-caixa/<pk>/excluir/
    """
    movimentacao = get_object_or_404(MovimentoCaixa, pk=pk)
    movimentacao.delete()
    messages.success(request, 'Movimentação excluída com sucesso!')
    return redirect('ERP_ServicesBI:fluxo_caixa_list')


# =============================================================================
# 3. CONTAS A RECEBER (Manager + Form com URLs compatíveis)
# =============================================================================

@login_required
def conta_receber_list(request):
    """
    Lista de contas a receber com filtros avançados
    URL: /financeiro/contas-receber/
    Template: conta_receber_manager.html
    """
    contas = ContaReceber.objects.select_related('cliente').all()
    
    # Filtros
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    vencimento_inicio = request.GET.get('vencimento_inicio', '')
    vencimento_fim = request.GET.get('vencimento_fim', '')
    order_by = request.GET.get('order_by', '-data_vencimento')
    per_page = request.GET.get('per_page', '25')
    
    if search:
        contas = contas.filter(
            Q(descricao__icontains=search) |
            Q(cliente__nome_razao_social__icontains=search)
        )
    
    if status:
        contas = contas.filter(status=status)
    
    if vencimento_inicio:
        contas = contas.filter(data_vencimento__gte=vencimento_inicio)
    if vencimento_fim:
        contas = contas.filter(data_vencimento__lte=vencimento_fim)
    
    # Ordenação
    contas = contas.order_by(order_by)
    
    # Paginação
    paginator = Paginator(contas, int(per_page))
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)
    
    # Dados JSON para JavaScript (cards e modais)
    contas_json = {}
    for conta in page_obj.object_list:
        contas_json[conta.id] = {
            'id': conta.id,
            'cliente': conta.cliente.nome_razao_social if conta.cliente else '-',
            'descricao': conta.descricao,
            'vencimento': conta.data_vencimento.strftime('%d/%m/%Y'),
            'valorOriginal': _format_currency_br(conta.valor_original),
            'valorSaldo': _format_currency_br(conta.valor_saldo or conta.valor_original),
            'valorRecebido': _format_currency_br(conta.valor_recebido or 0),
            'status': conta.status,
        }
    
    # Query string para paginação preservar filtros
    query_params = ''
    if search:
        query_params += f'&search={search}'
    if status:
        query_params += f'&status={status}'
    if vencimento_inicio:
        query_params += f'&vencimento_inicio={vencimento_inicio}'
    if vencimento_fim:
        query_params += f'&vencimento_fim={vencimento_fim}'
    if order_by:
        query_params += f'&order_by={order_by}'
    if per_page:
        query_params += f'&per_page={per_page}'
    
    context = {
        'page_obj': page_obj,
        'contas_json': json.dumps(contas_json),
        'status_choices': ContaReceber.STATUS_CHOICES if hasattr(ContaReceber, 'STATUS_CHOICES') else [],
        'search': search,
        'status': status,
        'vencimento_inicio': vencimento_inicio,
        'vencimento_fim': vencimento_fim,
        'order_by': order_by,
        'per_page': per_page,
        'query_params': query_params,
        'total': contas.count(),
    }
    return render(request, 'financeiro/conta_receber_manager.html', context)


@login_required
def conta_receber_add(request):
    """
    Nova conta a receber
    URL: /financeiro/contas-receber/adicionar/
    Template: conta_receber_form.html
    """
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
        'conta': None,  # Template usa {% if conta %} para diferenciar add/edit
        'clientes': [],  # Preencher com Cliente.objects.filter(ativo=True)
        'categorias': CategoriaFinanceira.objects.filter(tipo='receita'),
        'centros': CentroCusto.objects.all(),
    }
    return render(request, 'financeiro/conta_receber_form.html', context)


@login_required
def conta_receber_edit(request, pk):
    """
    Editar conta a receber
    URL: /financeiro/contas-receber/<pk>/editar/
    Template: conta_receber_form.html
    """
    conta = get_object_or_404(ContaReceber, pk=pk)
    
    if request.method == 'POST':
        form = ContaReceberForm(request.POST, instance=conta)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conta a receber atualizada com sucesso!')
            return redirect('ERP_ServicesBI:conta_receber_list')
    else:
        form = ContaReceberForm(instance=conta)
    
    context = {
        'form': form,
        'conta': conta,
        'clientes': [],  # Preencher com Cliente.objects.filter(ativo=True)
        'categorias': CategoriaFinanceira.objects.filter(tipo='receita'),
        'centros': CentroCusto.objects.all(),
    }
    return render(request, 'financeiro/conta_receber_form.html', context)


@login_required
@require_POST
def conta_receber_delete(request, pk):
    """
    Excluir conta a receber (via POST do modal)
    URL: /financeiro/contas-receber/<pk>/excluir/
    """
    conta = get_object_or_404(ContaReceber, pk=pk)
    conta.delete()
    messages.success(request, 'Conta excluída com sucesso!')
    return redirect('ERP_ServicesBI:conta_receber_list')


@login_required
@require_POST
def conta_receber_baixar(request, pk):
    """
    Baixar/Receber conta (via POST do modal)
    URL: /financeiro/contas-receber/<pk>/baixar/
    """
    conta = get_object_or_404(ContaReceber, pk=pk)
    
    data_recebimento = request.POST.get('data_recebimento')
    valor_recebido = request.POST.get('valor_recebido', '0')
    conta_bancaria = request.POST.get('conta_bancaria')
    observacoes = request.POST.get('observacoes', '')
    
    # Converter valor
    valor_recebido = _decimal_from_br(valor_recebido)
    
    # Atualizar conta
    conta.valor_recebido = (conta.valor_recebido or Decimal('0')) + valor_recebido
    conta.valor_saldo = conta.valor_original - conta.valor_recebido
    
    if conta.valor_saldo <= 0:
        conta.status = 'recebido'
    else:
        conta.status = 'parcial'
    
    conta.data_recebimento = _parse_date(data_recebimento) or timezone.now().date()
    conta.save()
    
    messages.success(request, 'Conta recebida com sucesso!')
    return redirect('ERP_ServicesBI:conta_receber_list')


# =============================================================================
# 4. CONTAS A PAGAR (Manager + Form com URLs compatíveis)
# =============================================================================

@login_required
def conta_pagar_list(request):
    """
    Lista de contas a pagar com filtros avançados
    URL: /financeiro/contas-pagar/
    Template: conta_pagar_manager.html
    """
    contas = ContaPagar.objects.select_related('fornecedor').all()
    
    # Filtros
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    vencimento_inicio = request.GET.get('vencimento_inicio', '')
    vencimento_fim = request.GET.get('vencimento_fim', '')
    order_by = request.GET.get('order_by', '-data_vencimento')
    per_page = request.GET.get('per_page', '25')
    
    if search:
        contas = contas.filter(
            Q(descricao__icontains=search) |
            Q(fornecedor__nome_razao_social__icontains=search)
        )
    
    if status:
        contas = contas.filter(status=status)
    
    if vencimento_inicio:
        contas = contas.filter(data_vencimento__gte=vencimento_inicio)
    if vencimento_fim:
        contas = contas.filter(data_vencimento__lte=vencimento_fim)
    
    # Ordenação
    contas = contas.order_by(order_by)
    
    # Paginação
    paginator = Paginator(contas, int(per_page))
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)
    
    # Dados JSON para JavaScript
    contas_json = {}
    for conta in page_obj.object_list:
        contas_json[conta.id] = {
            'id': conta.id,
            'fornecedor': conta.fornecedor.nome_razao_social if conta.fornecedor else '-',
            'descricao': conta.descricao,
            'vencimento': conta.data_vencimento.strftime('%d/%m/%Y'),
            'valorOriginal': _format_currency_br(conta.valor_original),
            'valorSaldo': _format_currency_br(conta.valor_saldo or conta.valor_original),
            'valorPago': _format_currency_br(conta.valor_pago or 0),
            'status': conta.status,
        }
    
    # Query string para paginação
    query_params = ''
    if search:
        query_params += f'&search={search}'
    if status:
        query_params += f'&status={status}'
    if vencimento_inicio:
        query_params += f'&vencimento_inicio={vencimento_inicio}'
    if vencimento_fim:
        query_params += f'&vencimento_fim={vencimento_fim}'
    if order_by:
        query_params += f'&order_by={order_by}'
    if per_page:
        query_params += f'&per_page={per_page}'
    
    context = {
        'page_obj': page_obj,
        'contas_json': json.dumps(contas_json),
        'status_choices': ContaPagar.STATUS_CHOICES if hasattr(ContaPagar, 'STATUS_CHOICES') else [],
        'search': search,
        'status': status,
        'vencimento_inicio': vencimento_inicio,
        'vencimento_fim': vencimento_fim,
        'order_by': order_by,
        'per_page': per_page,
        'query_params': query_params,
        'total': contas.count(),
    }
    return render(request, 'financeiro/conta_pagar_manager.html', context)


@login_required
def conta_pagar_add(request):
    """
    Nova conta a pagar
    URL: /financeiro/contas-pagar/adicionar/
    Template: conta_pagar_form.html
    """
    if request.method == 'POST':
        form = ContaPagarForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conta a pagar criada com sucesso!')
            return redirect('ERP_ServicesBI:conta_pagar_list')
    else:
        form = ContaPagarForm()
    
    context = {
        'form': form,
        'conta': None,
        'fornecedores': [],  # Preencher com Fornecedor.objects.filter(ativo=True)
        'categorias': CategoriaFinanceira.objects.filter(tipo='despesa'),
        'centros': CentroCusto.objects.all(),
    }
    return render(request, 'financeiro/conta_pagar_form.html', context)


@login_required
def conta_pagar_edit(request, pk):
    """
    Editar conta a pagar
    URL: /financeiro/contas-pagar/<pk>/editar/
    Template: conta_pagar_form.html
    """
    conta = get_object_or_404(ContaPagar, pk=pk)
    
    if request.method == 'POST':
        form = ContaPagarForm(request.POST, instance=conta)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conta a pagar atualizada com sucesso!')
            return redirect('ERP_ServicesBI:conta_pagar_list')
    else:
        form = ContaPagarForm(instance=conta)
    
    context = {
        'form': form,
        'conta': conta,
        'fornecedores': [],  # Preencher com Fornecedor.objects.filter(ativo=True)
        'categorias': CategoriaFinanceira.objects.filter(tipo='despesa'),
        'centros': CentroCusto.objects.all(),
    }
    return render(request, 'financeiro/conta_pagar_form.html', context)


@login_required
@require_POST
def conta_pagar_delete(request, pk):
    """
    Excluir conta a pagar (via POST do modal)
    URL: /financeiro/contas-pagar/<pk>/excluir/
    """
    conta = get_object_or_404(ContaPagar, pk=pk)
    conta.delete()
    messages.success(request, 'Conta excluída com sucesso!')
    return redirect('ERP_ServicesBI:conta_pagar_list')


@login_required
@require_POST
def conta_pagar_baixar(request, pk):
    """
    Baixar/Pagar conta (via POST do modal)
    URL: /financeiro/contas-pagar/<pk>/baixar/
    """
    conta = get_object_or_404(ContaPagar, pk=pk)
    
    data_baixa = request.POST.get('data_baixa')
    valor_pago = request.POST.get('valor_pago', '0')
    conta_bancaria = request.POST.get('conta_bancaria')
    observacoes = request.POST.get('observacoes', '')
    
    # Converter valor
    valor_pago = _decimal_from_br(valor_pago)
    
    # Atualizar conta
    conta.valor_pago = (conta.valor_pago or Decimal('0')) + valor_pago
    conta.valor_saldo = conta.valor_original - conta.valor_pago
    
    if conta.valor_saldo <= 0:
        conta.status = 'quitado'
    else:
        conta.status = 'parcial'
    
    conta.data_pagamento = _parse_date(data_baixa) or timezone.now().date()
    conta.save()
    
    messages.success(request, 'Conta paga com sucesso!')
    return redirect('ERP_ServicesBI:conta_pagar_list')


# =============================================================================
# 5. CONCILIAÇÃO BANCÁRIA
# =============================================================================

@login_required
def conciliacao_bancaria_list(request):
    """
    Lista de conciliações bancárias (MANAGER)
    URL: conciliacao_bancaria_list
    Template: conciliacao_bancaria_manager.html
    """
    extratos = ExtratoBancario.objects.all().order_by('-data_arquivo')
    
    # Filtros
    mes = request.GET.get('mes')
    status = request.GET.get('status')
    conta = request.GET.get('conta')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    if mes:
        try:
            ano, mes_num = mes.split('-')
            extratos = extratos.filter(data_arquivo__year=ano, data_arquivo__month=mes_num)
        except ValueError:
            pass
    if status:
        extratos = extratos.filter(status=status)
    if conta:
        extratos = extratos.filter(conta_bancaria_id=conta)
    if data_inicio:
        extratos = extratos.filter(data_arquivo__gte=data_inicio)
    if data_fim:
        extratos = extratos.filter(data_arquivo__lte=data_fim)
    
    # Contadores para cards de resumo
    total_extratos = extratos.count()
    conciliados = extratos.filter(status='conciliado').count()
    pendentes = extratos.filter(status='pendente').count()
    divergentes = extratos.filter(status='divergente').count()
    
    paginator = Paginator(extratos, 25)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)
    
    context = {
        'page_obj': page_obj,
        'total': total_extratos,
        'total_extratos': total_extratos,
        'conciliados': conciliados,
        'pendentes': pendentes,
        'divergentes': divergentes,
        'mes': mes,
        'status': status,
        'contas_bancarias': ContaBancaria.objects.filter(ativa=True),
    }
    return render(request, 'financeiro/conciliacao_bancaria_manager.html', context)


@login_required
def conciliacao_bancaria_add(request):
    """
    Nova conciliação/upload de extrato
    URL: conciliacao_bancaria_add
    Template: conciliacao_bancaria_form.html (modo criação)
    """
    if request.method == 'POST':
        form = ExtratoBancarioForm(request.POST, request.FILES)
        if form.is_valid():
            extrato = form.save(commit=False)
            extrato.usuario = request.user
            extrato.save()
            
            # Processar arquivo se houver
            if request.FILES.get('arquivo'):
                _processar_arquivo(extrato, request.FILES['arquivo'])
            
            messages.success(request, 'Extrato importado com sucesso!')
            return redirect('ERP_ServicesBI:conciliacao_bancaria_edit', pk=extrato.pk)
    else:
        form = ExtratoBancarioForm()
    
    context = {
        'form': form,
        'titulo': 'Importar Extrato Bancário',
        'extrato': None,
        'object': None,
        'extratos': [],
        'lancamentos_sistema': [],
        'conta': None,
    }
    return render(request, 'financeiro/conciliacao_bancaria_form.html', context)


@login_required
def conciliacao_bancaria_edit(request, pk):
    """
    Editar conciliação e realizar conciliação manual
    URL: conciliacao_bancaria_edit
    Template: conciliacao_bancaria_form.html (modo edição)
    """
    extrato = get_object_or_404(ExtratoBancario, pk=pk)
    
    if request.method == 'POST':
        form = ExtratoBancarioForm(request.POST, request.FILES, instance=extrato)
        if form.is_valid():
            extrato = form.save()
            if request.FILES.get('arquivo'):
                _processar_arquivo(extrato, request.FILES['arquivo'])
            messages.success(request, 'Conciliação atualizada com sucesso!')
            return redirect('ERP_ServicesBI:conciliacao_bancaria_edit', pk=extrato.pk)
    else:
        form = ExtratoBancarioForm(instance=extrato)
    
    # Lançamentos do extrato bancário
    extratos = LancamentoExtrato.objects.filter(extrato=extrato).order_by('data')
    
    # Lançamentos do sistema disponíveis para conciliação
    lancamentos_sistema = MovimentoCaixa.objects.filter(
        conta_bancaria=extrato.conta_bancaria,
        data__range=[extrato.data_inicial, extrato.data_final],
        conciliado=False
    ).order_by('data') if extrato.conta_bancaria else []
    
    context = {
        'form': form,
        'titulo': 'Editar Conciliação Bancária',
        'extrato': extrato,
        'object': extrato,
        'extratos': extratos,
        'lancamentos_sistema': lancamentos_sistema,
        'conta': extrato.conta_bancaria,
    }
    return render(request, 'financeiro/conciliacao_bancaria_form.html', context)


@login_required
def conciliacao_bancaria_detail(request, pk):
    """
    Visualizar detalhes da conciliação
    URL: conciliacao_bancaria_detail
    Template: conciliacao_bancaria_detail.html (ou reutilizar form em modo readonly)
    """
    extrato = get_object_or_404(ExtratoBancario, pk=pk)
    extratos = LancamentoExtrato.objects.filter(extrato=extrato).order_by('data')
    
    context = {
        'extrato': extrato,
        'object': extrato,
        'extratos': extratos,
    }
    return render(request, 'financeiro/conciliacao_bancaria_detail.html', context)


@login_required
def conciliacao_bancaria_delete(request, pk):
    """
    Excluir conciliação bancária
    URL: conciliacao_bancaria_delete
    """
    extrato = get_object_or_404(ExtratoBancario, pk=pk)
    
    if request.method == 'POST':
        extrato.delete()
        messages.success(request, 'Conciliação excluída com sucesso!')
    
    return redirect('ERP_ServicesBI:conciliacao_bancaria_list')


@login_required
def conciliacao_bancaria_processar(request, pk):
    """
    Reprocessar arquivo do extrato
    URL: conciliacao_bancaria_processar
    """
    extrato = get_object_or_404(ExtratoBancario, pk=pk)
    
    if extrato.arquivo:
        _processar_arquivo(extrato, extrato.arquivo)
        extrato.status = 'processando'
        extrato.save()
        messages.success(request, 'Extrato sendo reprocessado!')
    else:
        messages.error(request, 'Nenhum arquivo encontrado para processar.')
    
    return redirect('ERP_ServicesBI:conciliacao_bancaria_list')


@login_required
def conciliacao_bancaria_vincular(request, pk):
    """
    Tela de vinculação manual de lançamentos
    URL: conciliacao_bancaria_vincular
    Template: conciliacao_bancaria_vincular.html (ou edit com foco em vinculação)
    """
    extrato = get_object_or_404(ExtratoBancario, pk=pk)
    return redirect('ERP_ServicesBI:conciliacao_bancaria_edit', pk=extrato.pk)


@login_required
@require_http_methods(["POST"])
def conciliacao_importar_ofx(request):
    """
    Importar OFX via AJAX (para uso no form de edição)
    URL: conciliacao_importar_ofx
    """
    form = ExtratoBancarioForm(request.POST, request.FILES)
    
    if form.is_valid() and request.FILES.get('arquivo'):
        extrato = form.save(commit=False)
        extrato.usuario = request.user
        extrato.save()
        
        try:
            _processar_arquivo(extrato, request.FILES['arquivo'])
            return JsonResponse({
                'success': True,
                'extrato_id': extrato.id,
                'message': 'Arquivo importado com sucesso!'
            })
        except Exception as e:
            extrato.delete()
            return JsonResponse({
                'success': False,
                'message': f'Erro ao processar arquivo: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Arquivo inválido ou não fornecido.'
    })


@login_required
@require_http_methods(["GET"])
def conciliacao_buscar_lancamentos(request):
    """
    Buscar lançamentos do sistema para auto-conciliação (AJAX)
    URL: conciliacao_buscar_lancamentos
    """
    valor = request.GET.get('valor')
    conta_id = request.GET.get('conta_id')
    
    if not valor or not conta_id:
        return JsonResponse({'lancamentos': []})
    
    try:
        valor_decimal = Decimal(valor)
    except:
        return JsonResponse({'lancamentos': []})
    
    # Buscar lançamentos com valor similar e não conciliados
    lancamentos = MovimentoCaixa.objects.filter(
        conta_bancaria_id=conta_id,
        valor=valor_decimal,
        conciliado=False
    )[:10]
    
    data = [{
        'id': l.id,
        'data': l.data.strftime('%d/%m/%Y'),
        'descricao': l.descricao,
        'valor': str(l.valor)
    } for l in lancamentos]
    
    return JsonResponse({'lancamentos': data})


@login_required
@require_http_methods(["POST"])
def conciliacao_realizar(request):
    """
    Realizar conciliação entre extrato e lançamento do sistema (AJAX)
    URL: conciliacao_realizar
    """
    extrato_id = request.POST.get('extrato_id')
    lancamento_id = request.POST.get('lancamento_id')
    
    try:
        lancamento_extrato = LancamentoExtrato.objects.get(id=extrato_id)
        movimento = MovimentoCaixa.objects.get(id=lancamento_id)
        
        # Marcar como conciliado
        lancamento_extrato.conciliado = True
        lancamento_extrato.movimento_caixa = movimento
        lancamento_extrato.save()
        
        movimento.conciliado = True
        movimento.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Conciliação realizada com sucesso!'
        })
    except (LancamentoExtrato.DoesNotExist, MovimentoCaixa.DoesNotExist):
        return JsonResponse({
            'success': False,
            'message': 'Lançamento não encontrado.'
        })


@login_required
@require_http_methods(["POST"])
def conciliacao_auto(request):
    """
    Auto-conciliar lançamentos por valor e data (AJAX)
    URL: conciliacao_auto
    """
    conciliacao_id = request.POST.get('conciliacao_id')
    
    try:
        extrato = ExtratoBancario.objects.get(id=conciliacao_id)
    except ExtratoBancario.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Conciliação não encontrada.'
        })
    
    lancamentos_extrato = LancamentoExtrato.objects.filter(
        extrato=extrato,
        conciliado=False
    )
    
    conciliados = 0
    
    for lanc_ext in lancamentos_extrato:
        # Tentar encontrar correspondência exata
        correspondencia = MovimentoCaixa.objects.filter(
            conta_bancaria=extrato.conta_bancaria,
            data=lanc_ext.data,
            valor=lanc_ext.valor,
            conciliado=False
        ).first()
        
        if correspondencia:
            lanc_ext.conciliado = True
            lanc_ext.movimento_caixa = correspondencia
            lanc_ext.save()
            
            correspondencia.conciliado = True
            correspondencia.save()
            
            conciliados += 1
    
    return JsonResponse({
        'success': True,
        'conciliados': conciliados,
        'message': f'{conciliados} lançamentos conciliados automaticamente.'
    })


def _processar_arquivo(extrato, arquivo):
    """
    Processar arquivo (OFX, CSV, PDF, imagem)
    """
    nome_arquivo = arquivo.name.lower()
    
    if nome_arquivo.endswith('.ofx'):
        _processar_ofx(extrato, arquivo)
    elif nome_arquivo.endswith('.csv'):
        _processar_csv(extrato, arquivo)
    elif nome_arquivo.endswith(('.pdf', '.jpg', '.jpeg', '.png')):
        _processar_ocr(extrato, arquivo)
    else:
        raise ValueError('Formato de arquivo não suportado')


def _processar_ofx(extrato, arquivo):
    """Processar arquivo OFX"""
    # TODO: Implementar parser OFX
    pass


def _processar_csv(extrato, arquivo):
    """Processar arquivo CSV"""
    # TODO: Implementar parser CSV
    pass


def _processar_ocr(extrato, arquivo):
    """Processar PDF/Imagem com OCR"""
    # TODO: Implementar OCR
    pass


# =============================================================================
# 6. DRE GERENCIAL
# =============================================================================

@login_required
def dre_list(request):
    """
    Lista de empresas para DRE
    URL: /financeiro/dre/
    Template: dre_manager.html
    """
    empresas = Empresa.objects.filter(ativo=True).order_by('nome_fantasia')
    return render(request, 'financeiro/dre_manager.html', {'empresas': empresas})


@login_required
def dre_add(request):
    """
    Visualizar/Calcular DRE (form de seleção)
    URL: /financeiro/dre/adicionar/
    Template: dre_form.html
    """
    return dre_edit(request, pk=None)


@login_required
def dre_edit(request, pk=None):
    """
    Visualizar DRE de empresa específica
    URL: /financeiro/dre/<pk>/editar/
    Template: dre_form.html
    """
    from .services.dre_service import DREService
    
    hoje = timezone.now().date()
    
    # Parâmetros
    empresa_id = request.GET.get('empresa') or pk
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    regime = request.GET.get('regime', 'simples')
    
    if data_inicio:
        data_inicio = _parse_date(data_inicio)
    else:
        data_inicio = hoje.replace(day=1)
    
    if data_fim:
        data_fim = _parse_date(data_fim)
    else:
        proximo_mes = hoje.replace(day=28) + timedelta(days=4)
        data_fim = proximo_mes - timedelta(days=proximo_mes.day)
    
    empresas = Empresa.objects.filter(ativo=True).order_by('nome_fantasia')
    empresa_selecionada = None
    dre_dados = None
    config = None
    
    if empresa_id:
        empresa_selecionada = get_object_or_404(Empresa, pk=empresa_id)
        config, created = ConfiguracaoDRE.objects.get_or_create(
            empresa=empresa_selecionada,
            defaults={'regime_tributario': regime}
        )
        
        if not created and regime:
            config.regime_tributario = regime
            config.save()
        
        try:
            service = DREService(empresa_selecionada, data_inicio, data_fim, config.regime_tributario)
            dre_dados = service.calcular_dre_completa()
        except Exception as e:
            messages.error(request, f'Erro ao calcular DRE: {str(e)}')
    
    context = {
        'empresas': empresas,
        'empresa_selecionada': empresa_selecionada,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'regime_selecionado': config.regime_tributario if config else regime,
        'regimes': getattr(ConfiguracaoDRE, 'REGIME_CHOICES', []),
        'dre_dados': dre_dados,
        'config': config,
    }
    return render(request, 'financeiro/dre_form.html', context)


# =============================================================================
# 7. PLANEJADO X REALIZADO
# =============================================================================

@login_required
def planejado_x_realizado_list(request):
    """
    Dashboard Planejado x Realizado
    URL: /financeiro/planejado-realizado/
    Template: planejado_x_realizado_manager.html
    """
    ano = request.GET.get('ano', timezone.now().year)
    
    orcamentos = OrcamentoFinanceiro.objects.filter(
        ano=ano
    ).select_related('categoria').order_by('mes', 'categoria__nome')
    
    # Agrupar por mês
    meses = []
    for mes in range(1, 13):
        orcamentos_mes = orcamentos.filter(mes=mes)
        realizado = MovimentoCaixa.objects.filter(
            data__year=ano,
            data__month=mes
        ).aggregate(
            entradas=Sum('valor', filter=Q(tipo='entrada')),
            saidas=Sum('valor', filter=Q(tipo='saida'))
        )
        
        meses.append({
            'numero': mes,
            'nome': calendar.month_name[mes],
            'orcamentos': orcamentos_mes,
            'total_orcado': sum([o.valor_orcado for o in orcamentos_mes]),
            'total_realizado': realizado['entradas'] or 0,
        })
    
    return render(request, 'financeiro/planejado_x_realizado_manager.html', {
        'ano': ano,
        'meses': meses,
    })


@login_required
def planejado_x_realizado_add(request):
    """
    Novo orçamento
    URL: /financeiro/planejado-realizado/adicionar/
    Template: planejado_x_realizado_form.html
    """
    if request.method == 'POST':
        form = OrcamentoFinanceiroForm(request.POST)
        if form.is_valid():
            orcamento = form.save(commit=False)
            orcamento.criado_por = request.user
            orcamento.save()
            messages.success(request, 'Orçamento criado com sucesso!')
            return redirect('ERP_ServicesBI:planejado_x_realizado_list')
    else:
        form = OrcamentoFinanceiroForm()
    
    return render(request, 'financeiro/planejado_x_realizado_form.html', {
        'form': form,
        'titulo': 'Novo Orçamento',
        'orcamento': None,
        'categorias': CategoriaFinanceira.objects.all(),
    })


@login_required
def planejado_x_realizado_edit(request, pk):
    """
    Editar orçamento
    URL: /financeiro/planejado-realizado/<pk>/editar/
    Template: planejado_x_realizado_form.html
    """
    orcamento = get_object_or_404(OrcamentoFinanceiro, pk=pk)
    
    if request.method == 'POST':
        form = OrcamentoFinanceiroForm(request.POST, instance=orcamento)
        if form.is_valid():
            form.save()
            messages.success(request, 'Orçamento atualizado com sucesso!')
            return redirect('ERP_ServicesBI:planejado_x_realizado_list')
    else:
        form = OrcamentoFinanceiroForm(instance=orcamento)
    
    return render(request, 'financeiro/planejado_x_realizado_form.html', {
        'form': form,
        'titulo': 'Editar Orçamento',
        'orcamento': orcamento,
        'categorias': CategoriaFinanceira.objects.all(),
    })


# =============================================================================
# 8. CATEGORIAS FINANCEIRAS → redireciona para planejado_x_realizado
# =============================================================================

@login_required
def categoria_financeira_list(request):
    return redirect('ERP_ServicesBI:planejado_x_realizado_list')

@login_required
def categoria_financeira_add(request):
    return redirect('ERP_ServicesBI:planejado_x_realizado_list')

@login_required
def categoria_financeira_edit(request, pk):
    return redirect('ERP_ServicesBI:planejado_x_realizado_list')

@login_required
@require_POST
def categoria_financeira_delete(request, pk):
    categoria = get_object_or_404(CategoriaFinanceira, pk=pk)
    try:
        categoria.delete()
        messages.success(request, 'Categoria excluída com sucesso!')
    except Exception as e:
        messages.error(request, f'Erro ao excluir: {str(e)}')
    return redirect('ERP_ServicesBI:planejado_x_realizado_list')


# =============================================================================
# 9. CENTROS DE CUSTO → redireciona para conta_pagar_list (form tem modal)
# =============================================================================

@login_required
def centro_custo_list(request):
    return redirect('ERP_ServicesBI:conta_pagar_list')

@login_required
def centro_custo_add(request):
    return redirect('ERP_ServicesBI:conta_pagar_list')

@login_required
def centro_custo_edit(request, pk):
    return redirect('ERP_ServicesBI:conta_pagar_list')

@login_required
@require_POST
def centro_custo_delete(request, pk):
    centro = get_object_or_404(CentroCusto, pk=pk)
    try:
        centro.delete()
        messages.success(request, 'Centro de custo excluído com sucesso!')
    except Exception as e:
        messages.error(request, f'Erro ao excluir: {str(e)}')
    return redirect('ERP_ServicesBI:conta_pagar_list')


# =============================================================================
# 10. APIs PARA AJAX (Categorias e Centros de Custo)
# =============================================================================

@login_required
@require_POST
def api_categoria_criar(request):
    """API para criar categoria via AJAX"""
    try:
        data = json.loads(request.body)
        categoria = CategoriaFinanceira.objects.create(
            nome=data.get('nome'),
            tipo=data.get('tipo', 'despesa'),
            descricao=data.get('descricao', '')
        )
        return JsonResponse({
            'success': True,
            'id': categoria.id,
            'nome': categoria.nome
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def api_categoria_excluir(request, pk):
    """API para excluir categoria via AJAX"""
    try:
        categoria = get_object_or_404(CategoriaFinanceira, pk=pk)
        categoria.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def api_centro_custo_criar(request):
    """API para criar centro de custo via AJAX"""
    try:
        data = json.loads(request.body)
        centro = CentroCusto.objects.create(
            nome=data.get('nome'),
            descricao=data.get('descricao', '')
        )
        return JsonResponse({
            'success': True,
            'id': centro.id,
            'nome': centro.nome
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def api_centro_custo_excluir(request, pk):
    """API para excluir centro de custo via AJAX"""
    try:
        centro = get_object_or_404(CentroCusto, pk=pk)
        centro.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# =============================================================================
# MÓDULO: ESTOQUE - PRODUTOS E GESTÃO
# =============================================================================

@login_required
def produto_list(request):
    """Listagem de produtos"""
    produtos = Produto.objects.select_related('categoria', 'unidade_medida').all()
    
    # Filtros
    categoria_id = request.GET.get('categoria')
    tipo = request.GET.get('tipo')
    busca = request.GET.get('busca')
    
    if categoria_id:
        produtos = produtos.filter(categoria_id=categoria_id)
    if tipo:
        produtos = produtos.filter(tipo=tipo)
    if busca:
        produtos = produtos.filter(
            models.Q(codigo__icontains=busca) | 
            models.Q(nome__icontains=busca) |
            models.Q(descricao__icontains=busca)
        )
    
    produtos = produtos.order_by('nome')
    paginator = Paginator(produtos, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total': paginator.count,
        'categorias': CategoriaProduto.objects.all(),
        'tipos': Produto.TIPO_CHOICES,
        'filtros': {
            'categoria': categoria_id,
            'tipo': tipo,
            'busca': busca,
        }
    }
    return render(request, 'estoque/produto_list.html', context)


@login_required
def produto_add(request):
    """Cadastro de produto"""
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES)
        if form.is_valid():
            produto = form.save(commit=False)
            produto.criado_por = request.user
            produto.save()
            messages.success(request, 'Produto criado com sucesso!')
            return redirect('ERP_ServicesBI:produto_list')
    else:
        form = ProdutoForm()
    return render(request, 'estoque/produto_form.html', {
        'form': form,
        'titulo': 'Novo Produto'
    })


@login_required
def produto_edit(request, pk):
    """Edição de produto"""
    produto = get_object_or_404(Produto, pk=pk)
    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES, instance=produto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produto atualizado com sucesso!')
            return redirect('ERP_ServicesBI:produto_list')
    else:
        form = ProdutoForm(instance=produto)
    return render(request, 'estoque/produto_form.html', {
        'form': form,
        'titulo': 'Editar Produto',
        'produto': produto
    })


@login_required
def produto_delete(request, pk):
    """Exclusão de produto"""
    produto = get_object_or_404(Produto, pk=pk)
    if request.method == 'POST':
        produto.delete()
        messages.success(request, 'Produto excluído com sucesso!')
        return redirect('ERP_ServicesBI:produto_list')
    return render(request, 'estoque/produto_confirm_delete.html', {
        'objeto': produto,
        'titulo': 'Excluir Produto'
    })


@login_required
def produto_detail(request, pk):
    """Detalhes do produto com histórico de movimentações"""
    produto = get_object_or_404(Produto, pk=pk)
    
    # Movimentações recentes
    movimentacoes = MovimentacaoEstoque.objects.filter(
        produto=produto
    ).select_related('usuario', 'pedido_compra').order_by('-data')[:50]
    
    # Saldo em cada depósito
    saldos = SaldoEstoque.objects.filter(
        produto=produto
    ).select_related('deposito')
    
    # Últimas cotações
    cotacoes = ItemSolicitado.objects.filter(
        produto=produto,
        cotacao__isnull=False
    ).select_related('cotacao', 'cotacao__fornecedor').order_by('-cotacao__data_cotacao')[:10]
    
    context = {
        'produto': produto,
        'movimentacoes': movimentacoes,
        'saldos': saldos,
        'cotacoes': cotacoes,
    }
    return render(request, 'estoque/produto_detail.html', context)


# =============================================================================
# MÓDULO: ESTOQUE - CATEGORIAS DE PRODUTOS
# =============================================================================

@login_required
def categoria_produto_list(request):
    """Listagem de categorias de produtos"""
    categorias = CategoriaProduto.objects.all().order_by('nome')
    paginator = Paginator(categorias, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'estoque/categoria_produto_list.html', {
        'page_obj': page_obj,
        'total': paginator.count
    })


@login_required
def categoria_produto_add(request):
    """Cadastro de categoria de produto"""
    if request.method == 'POST':
        form = CategoriaProdutoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoria criada com sucesso!')
            return redirect('ERP_ServicesBI:categoria_produto_list')
    else:
        form = CategoriaProdutoForm()
    return render(request, 'estoque/categoria_produto_form.html', {
        'form': form,
        'titulo': 'Nova Categoria'
    })


@login_required
def categoria_produto_edit(request, pk):
    """Edição de categoria de produto"""
    categoria = get_object_or_404(CategoriaProduto, pk=pk)
    if request.method == 'POST':
        form = CategoriaProdutoForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoria atualizada com sucesso!')
            return redirect('ERP_ServicesBI:categoria_produto_list')
    else:
        form = CategoriaProdutoForm(instance=categoria)
    return render(request, 'estoque/categoria_produto_form.html', {
        'form': form,
        'titulo': 'Editar Categoria',
        'categoria': categoria
    })


@login_required
def categoria_produto_delete(request, pk):
    """Exclusão de categoria de produto"""
    categoria = get_object_or_404(CategoriaProduto, pk=pk)
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, 'Categoria excluída com sucesso!')
        return redirect('ERP_ServicesBI:categoria_produto_list')
    return render(request, 'estoque/categoria_produto_confirm_delete.html', {
        'objeto': categoria,
        'titulo': 'Excluir Categoria'
    })


# =============================================================================
# MÓDULO: ESTOQUE - DEPÓSITOS/ARMAZÉNS
# =============================================================================

@login_required
def deposito_list(request):
    """Listagem de depósitos/armazéns"""
    depositos = Deposito.objects.all().order_by('nome')
    paginator = Paginator(depositos, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'estoque/deposito_list.html', {
        'page_obj': page_obj,
        'total': paginator.count
    })


@login_required
def deposito_add(request):
    """Cadastro de depósito"""
    if request.method == 'POST':
        form = DepositoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Depósito criado com sucesso!')
            return redirect('ERP_ServicesBI:deposito_list')
    else:
        form = DepositoForm()
    return render(request, 'estoque/deposito_form.html', {
        'form': form,
        'titulo': 'Novo Depósito'
    })


@login_required
def deposito_edit(request, pk):
    """Edição de depósito"""
    deposito = get_object_or_404(Deposito, pk=pk)
    if request.method == 'POST':
        form = DepositoForm(request.POST, instance=deposito)
        if form.is_valid():
            form.save()
            messages.success(request, 'Depósito atualizado com sucesso!')
            return redirect('ERP_ServicesBI:deposito_list')
    else:
        form = DepositoForm(instance=deposito)
    return render(request, 'estoque/deposito_form.html', {
        'form': form,
        'titulo': 'Editar Depósito',
        'deposito': deposito
    })


@login_required
def deposito_delete(request, pk):
    """Exclusão de depósito"""
    deposito = get_object_or_404(Deposito, pk=pk)
    if request.method == 'POST':
        deposito.delete()
        messages.success(request, 'Depósito excluído com sucesso!')
        return redirect('ERP_ServicesBI:deposito_list')
    return render(request, 'estoque/deposito_confirm_delete.html', {
        'objeto': deposito,
        'titulo': 'Excluir Depósito'
    })


# =============================================================================
# MÓDULO: ESTOQUE - MOVIMENTAÇÕES
# =============================================================================

@login_required
def movimentacao_estoque_list(request):
    """Listagem de movimentações de estoque"""
    movimentacoes = MovimentacaoEstoque.objects.select_related(
        'produto', 'deposito_origem', 'deposito_destino', 'usuario'
    ).all().order_by('-data')
    
    # Filtros
    tipo = request.GET.get('tipo')
    produto_id = request.GET.get('produto')
    deposito_id = request.GET.get('deposito')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    if tipo:
        movimentacoes = movimentacoes.filter(tipo=tipo)
    if produto_id:
        movimentacoes = movimentacoes.filter(produto_id=produto_id)
    if deposito_id:
        movimentacoes = movimentacoes.filter(
            models.Q(deposito_origem_id=deposito_id) | 
            models.Q(deposito_destino_id=deposito_id)
        )
    if data_inicio:
        movimentacoes = movimentacoes.filter(data__gte=data_inicio)
    if data_fim:
        movimentacoes = movimentacoes.filter(data__lte=data_fim)
    
    paginator = Paginator(movimentacoes, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total': paginator.count,
        'tipos': MovimentacaoEstoque.TIPO_CHOICES,
        'produtos': Produto.objects.filter(ativo=True),
        'depositos': Deposito.objects.filter(ativo=True),
    }
    return render(request, 'estoque/movimentacao_list.html', context)


@login_required
def movimentacao_estoque_add(request):
    """Registrar movimentação de estoque manual"""
    if request.method == 'POST':
        form = MovimentacaoEstoqueForm(request.POST)
        if form.is_valid():
            movimentacao = form.save(commit=False)
            movimentacao.usuario = request.user
            movimentacao.save()
            
            # Atualizar saldos
            movimentacao.atualizar_saldos()
            
            messages.success(request, 'Movimentação registrada com sucesso!')
            return redirect('ERP_ServicesBI:movimentacao_estoque_list')
    else:
        form = MovimentacaoEstoqueForm()
    return render(request, 'estoque/movimentacao_form.html', {
        'form': form,
        'titulo': 'Nova Movimentação'
    })


@login_required
def movimentacao_estoque_detail(request, pk):
    """Detalhes da movimentação"""
    movimentacao = get_object_or_404(MovimentacaoEstoque, pk=pk)
    return render(request, 'estoque/movimentacao_detail.html', {
        'movimentacao': movimentacao
    })


# =============================================================================
# MÓDULO: ESTOQUE - ENTRADA DE NOTA FISCAL
# =============================================================================

@login_required
def entrada_nfe_list(request):
    """Listagem de entradas de notas fiscais"""
    entradas = EntradaNFE.objects.select_related('fornecedor', 'pedido_compra', 'usuario').all().order_by('-data_entrada')
    paginator = Paginator(entradas, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'estoque/entrada_nfe_list.html', {
        'page_obj': page_obj,
        'total': paginator.count
    })


@login_required
def entrada_nfe_add(request):
    """Registrar entrada de nota fiscal"""
    if request.method == 'POST':
        form = EntradaNFEForm(request.POST)
        if form.is_valid():
            entrada = form.save(commit=False)
            entrada.usuario = request.user
            entrada.save()
            messages.success(request, 'Entrada registrada. Adicione os itens.')
            return redirect('ERP_ServicesBI:entrada_nfe_itens', pk=entrada.pk)
    else:
        form = EntradaNFEForm()
    return render(request, 'estoque/entrada_nfe_form.html', {
        'form': form,
        'titulo': 'Nova Entrada NF-e'
    })


@login_required
def entrada_nfe_itens(request, pk):
    """Gerenciar itens da entrada de NF-e"""
    entrada = get_object_or_404(EntradaNFE, pk=pk)
    
    if request.method == 'POST':
        form = ItemEntradaNFEForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.entrada = entrada
            item.save()
            
            # Registrar movimentação de entrada
            MovimentacaoEstoque.objects.create(
                tipo='entrada',
                produto=item.produto,
                deposito_destino=entrada.deposito,
                quantidade=item.quantidade,
                custo_unitario=item.valor_unitario,
                documento=f"NF-e {entrada.numero_nfe}",
                usuario=request.user,
                observacao=f"Entrada NF-e {entrada.numero_nfe} - {entrada.fornecedor}"
            )
            
            messages.success(request, 'Item adicionado com sucesso!')
            return redirect('ERP_ServicesBI:entrada_nfe_itens', pk=pk)
    else:
        form = ItemEntradaNFEForm()
    
    itens = ItemEntradaNFE.objects.filter(entrada=entrada).select_related('produto')
    
    return render(request, 'estoque/entrada_nfe_itens.html', {
        'entrada': entrada,
        'form': form,
        'itens': itens
    })


@login_required
def entrada_nfe_finalizar(request, pk):
    """Finalizar entrada de NF-e e atualizar pedido de compra"""
    entrada = get_object_or_404(EntradaNFE, pk=pk)
    
    if request.method == 'POST':
        entrada.status = 'finalizada'
        entrada.save()
        
        # Atualizar pedido de compra se vinculado
        if entrada.pedido_compra:
            pedido = entrada.pedido_compra
            
            # Verificar 3-Way Matching
            for item_entrada in entrada.itens.all():
                item_pedido = pedido.itens.filter(produto=item_entrada.produto).first()
                if item_pedido:
                    item_pedido.quantidade_recebida += item_entrada.quantidade
                    
                    # Verificar divergências
                    if item_entrada.quantidade != item_pedido.quantidade:
                        item_pedido.divergencia_quantidade = True
                    if item_entrada.valor_unitario != item_pedido.preco_unitario:
                        item_pedido.divergencia_preco = True
                        item_pedido.preco_recebido = item_entrada.valor_unitario
                    
                    item_pedido.save()
            
            # Verificar se pedido está completo
            pedido.verificar_recebimento()
        
        messages.success(request, 'Entrada finalizada com sucesso!')
        return redirect('ERP_ServicesBI:entrada_nfe_list')
    
    return render(request, 'estoque/entrada_nfe_finalizar.html', {
        'entrada': entrada
    })


# =============================================================================
# MÓDULO: ESTOQUE - INVENTÁRIO E AJUSTES
# =============================================================================

@login_required
def inventario_list(request):
    """Listagem de inventários"""
    inventarios = Inventario.objects.select_related('deposito', 'usuario_responsavel').all().order_by('-data_inicio')
    paginator = Paginator(inventarios, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'estoque/inventario_list.html', {
        'page_obj': page_obj,
        'total': paginator.count
    })


@login_required
def inventario_add(request):
    if request.method == 'POST':
        form = InventarioForm(request.POST)
        if form.is_valid():
            inventario = form.save(commit=False)
            inventario.usuario = request.user  # ← era usuario_responsavel
            inventario.save()

            # ← ItemInventario no lugar de ContagemInventario
            saldos = SaldoEstoque.objects.filter(deposito=inventario.deposito)
            for saldo in saldos:
                ItemInventario.objects.create(
                    inventario=inventario,
                    produto=saldo.produto,
                    quantidade_sistema=saldo.quantidade
                )

            messages.success(request, 'Inventário iniciado com sucesso!')
            return redirect('ERP_ServicesBI:inventario_contagem', pk=inventario.pk)
    else:
        form = InventarioForm()
    return render(request, 'estoque/inventario_form.html', {
        'form': form,
        'titulo': 'Novo Inventário'
    })


@login_required
def inventario_contagem(request, pk):
    inventario = get_object_or_404(Inventario, pk=pk)

    if inventario.status != 'em_andamento':
        messages.error(request, 'Este inventário não está em andamento.')
        return redirect('ERP_ServicesBI:inventario_list')

    # ← ItemInventario no lugar de ContagemInventario
    contagens = ItemInventario.objects.filter(
        inventario=inventario
    ).select_related('produto')

    if request.method == 'POST':
        contagem_id = request.POST.get('contagem_id')
        quantidade_contada = request.POST.get('quantidade_contada')

        if contagem_id and quantidade_contada:
            contagem = get_object_or_404(ItemInventario, pk=contagem_id)
            contagem.quantidade_contada = Decimal(quantidade_contada)
            contagem.save()
            messages.success(request, 'Contagem registrada!')
            return redirect('ERP_ServicesBI:inventario_contagem', pk=pk)

    return render(request, 'estoque/inventario_contagem.html', {
        'inventario': inventario,
        'contagens': contagens
    })


@login_required
def inventario_finalizar(request, pk):
    inventario = get_object_or_404(Inventario, pk=pk)

    if request.method == 'POST':
        # ← ItemInventario no lugar de ContagemInventario
        contagens_com_diferenca = ItemInventario.objects.filter(
            inventario=inventario,
        ).exclude(diferenca=0)

        for contagem in contagens_com_diferenca:
            tipo = 'ajuste' if contagem.diferenca > 0 else 'ajuste'
            MovimentacaoEstoque.objects.create(
                tipo='ajuste',
                produto=contagem.produto,
                quantidade=abs(contagem.diferenca),
                usuario=request.user,
                observacoes=f"Ajuste de inventário {inventario.numero} - diferença: {contagem.diferenca}"
            )

        inventario.status = 'concluido'
        inventario.save()

        messages.success(request, f'Inventário finalizado! {contagens_com_diferenca.count()} ajustes gerados.')
        return redirect('ERP_ServicesBI:inventario_list')

    return render(request, 'estoque/inventario_finalizar.html', {
        'inventario': inventario
    })


# =============================================================================
# MÓDULO: ESTOQUE - RELATÓRIOS E CONSULTAS
# =============================================================================

@login_required
def relatorio_estoque(request):
    """Relatório de posição de estoque"""
    deposito_id = request.GET.get('deposito')
    categoria_id = request.GET.get('categoria')
    
    saldos = SaldoEstoque.objects.select_related('produto', 'deposito')
    
    if deposito_id:
        saldos = saldos.filter(deposito_id=deposito_id)
    if categoria_id:
        saldos = saldos.filter(produto__categoria_id=categoria_id)
    
    saldos = saldos.filter(quantidade__gt=0).order_by('produto__nome')
    
    # Totais
    total_itens = saldos.count()
    valor_total = sum([s.quantidade * s.custo_medio for s in saldos if s.custo_medio])
    
    context = {
        'saldos': saldos,
        'total_itens': total_itens,
        'valor_total': valor_total,
        'depositos': Deposito.objects.filter(ativo=True),
        'categorias': CategoriaProduto.objects.all(),
        'filtros': {
            'deposito': deposito_id,
            'categoria': categoria_id,
        }
    }
    return render(request, 'estoque/relatorio_estoque.html', context)


@login_required
def relatorio_movimentacao(request):
    """Relatório de movimentações por período"""
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    produto_id = request.GET.get('produto')
    
    movimentacoes = MovimentacaoEstoque.objects.select_related('produto', 'usuario')
    
    if data_inicio:
        movimentacoes = movimentacoes.filter(data__gte=data_inicio)
    else:
        data_inicio = timezone.now().date().replace(day=1)
        movimentacoes = movimentacoes.filter(data__gte=data_inicio)
        
    if data_fim:
        movimentacoes = movimentacoes.filter(data__lte=data_fim)
    else:
        data_fim = timezone.now().date()
        movimentacoes = movimentacoes.filter(data__lte=data_fim)
    
    if produto_id:
        movimentacoes = movimentacoes.filter(produto_id=produto_id)
    
    # Resumo por tipo
    resumo = movimentacoes.values('tipo').annotate(
        total_quantidade=models.Sum('quantidade'),
        total_movimentacoes=models.Count('id')
    )
    
    context = {
        'movimentacoes': movimentacoes.order_by('-data'),
        'resumo': resumo,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'produtos': Produto.objects.filter(ativo=True),
        'produto_selecionado': produto_id,
    }
    return render(request, 'estoque/relatorio_movimentacao.html', context)


@login_required
def consulta_saldo(request):
    """Consulta rápida de saldo de produto"""
    resultado = None
    busca = request.GET.get('busca')
    
    if busca:
        produtos = Produto.objects.filter(
            models.Q(codigo__icontains=busca) | 
            models.Q(nome__icontains=busca),
            ativo=True
        )[:10]
        
        resultado = []
        for produto in produtos:
            saldos = SaldoEstoque.objects.filter(produto=produto)
            resultado.append({
                'produto': produto,
                'saldos': saldos,
                'total': sum([s.quantidade for s in saldos])
            })
    
    return render(request, 'estoque/consulta_saldo.html', {
        'resultado': resultado,
        'busca': busca
    })


# =============================================================================
# MÓDULO: ESTOQUE - API AJAX
# =============================================================================

@login_required
def api_produto_saldo(request, produto_id):
    """API para consultar saldo de produto em JSON"""
    produto = get_object_or_404(Produto, pk=produto_id)
    saldos = SaldoEstoque.objects.filter(produto=produto).select_related('deposito')
    
    data = {
        'produto': {
            'id': produto.id,
            'codigo': produto.codigo,
            'nome': produto.nome,
        },
        'saldos': [
            {
                'deposito': s.deposito.nome,
                'quantidade': float(s.quantidade),
                'custo_medio': float(s.custo_medio) if s.custo_medio else None,
            }
            for s in saldos
        ],
        'total': float(sum([s.quantidade for s in saldos]))
    }
    
    return JsonResponse(data)


@login_required
def api_produtos_busca(request):
    """API para busca de produtos em tempo real"""
    termo = request.GET.get('q', '')
    
    produtos = Produto.objects.filter(
        models.Q(codigo__icontains=termo) | 
        models.Q(nome__icontains=termo),
        ativo=True
    )[:20]
    
    data = {
        'results': [
            {
                'id': p.id,
                'codigo': p.codigo,
                'nome': p.nome,
                'unidade': p.unidade_medida.sigla if p.unidade_medida else 'UN',
                'text': f"{p.codigo} - {p.nome}"
            }
            for p in produtos
        ]
    }
    
    return JsonResponse(data)

def transferencia_list(request):
    from .models import TransferenciaEstoque
    transferencias = TransferenciaEstoque.objects.all().order_by('-data_transferencia')
    return render(request, 'transferencia/transferencia_list.html', {'transferencias': transferencias})

def transferencia_add(request):
    from .forms import TransferenciaEstoqueForm, ItemTransferenciaForm
    form = TransferenciaEstoqueForm()
    return render(request, 'transferencia/transferencia_form.html', {'form': form})

def transferencia_detail(request, pk):
    from .models import TransferenciaEstoque
    transferencia = get_object_or_404(TransferenciaEstoque, pk=pk)
    return render(request, 'transferencia/transferencia_detail.html', {'transferencia': transferencia})

def transferencia_edit(request, pk):
    from .models import TransferenciaEstoque
    transferencia = get_object_or_404(TransferenciaEstoque, pk=pk)
    from .forms import TransferenciaEstoqueForm
    form = TransferenciaEstoqueForm(instance=transferencia)
    return render(request, 'transferencia/transferencia_form.html', {'form': form})

def transferencia_delete(request, pk):
    from .models import TransferenciaEstoque
    transferencia = get_object_or_404(TransferenciaEstoque, pk=pk)
    if request.method == 'POST':
        transferencia.delete()
        return redirect('ERP_ServicesBI:transferencia_list')
    return render(request, 'transferencia/transferencia_confirm_delete.html', {'transferencia': transferencia})
