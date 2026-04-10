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
from django.db.models.functions import TruncDate, TruncMonth
from django.db import transaction, models
from django.db.models import ExpressionWrapper
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

# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------
from .models import (
    # Cadastros Base
    Cliente, Empresa, Fornecedor, Vendedor,

    # Produtos e Estoque
    Produto, CategoriaProduto, UnidadeMedida,
    Deposito, SaldoEstoque,
    MovimentacaoEstoque,
    EntradaNFE, ItemEntradaNFE,
    Inventario, ItemInventario,
    TransferenciaEstoque, ItemTransferencia,

    # Compras
    PedidoCompra, ItemPedidoCompra,
    NotaFiscalEntrada, ItemNotaFiscalEntrada,
    CotacaoMae, ItemSolicitado,
    CotacaoFornecedor, ItemCotacaoFornecedor,
    RegraAprovacao, PedidoAprovacao,
    CondicaoPagamento, FormaPagamento, CentroCusto,

    # Vendas
    Orcamento, ItemOrcamento,
    PedidoVenda, ItemPedidoVenda,
    NotaFiscalSaida, ItemNotaFiscalSaida,

    # Financeiro
    ContaPagar, ContaReceber,
    CategoriaFinanceira,
    MovimentoCaixa, ExtratoBancario, LancamentoExtrato,
    ContaBancaria,

    # DRE
    ConfiguracaoDRE, LinhaDRE, RelatorioDRE, ItemRelatorioDRE,

    # Planejado x Realizado
    OrcamentoProjeto, Projeto,
)

# -----------------------------------------------------------------------------
# Forms
# -----------------------------------------------------------------------------
from .forms import (
    # Cadastros
    ClienteForm, EmpresaForm, FornecedorForm, VendedorForm,

    # Produtos
    CategoriaProdutoForm, ProdutoForm, UnidadeMedidaForm,

    # Estoque
    DepositoForm,
    MovimentacaoEstoqueForm,
    EntradaNFEForm, ItemEntradaNFEForm,
    InventarioForm, ItemInventarioForm,
    TransferenciaEstoqueForm, ItemTransferenciaForm,

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

    # Financeiro
    ContaPagarForm, ContaReceberForm,
    BaixaContaPagarForm, BaixaContaReceberForm,
    CategoriaFinanceiraForm, CentroCustoForm, OrcamentoFinanceiroForm,
    MovimentoCaixaForm, ExtratoBancarioForm, LancamentoExtratoForm,

    # DRE
    LinhaDREForm, FiltroDREForm,

    # Configurações Pagamento
    CondicaoPagamentoForm, FormaPagamentoForm,

    # Planejado x Realizado
    OrcamentoProjetoForm,
)

# Services (opcional)
try:
    from .services.dre_service import DREService
except ImportError:
    DREService = None

# Logger
logger = logging.getLogger('erp')


# =============================================================================
# UTILITÁRIOS GLOBAIS
# =============================================================================

def log_erro_seguro(funcao_nome, exception, request=None, extra_data=None):
    """Loga erros de forma segura, sem expor informações sensíveis."""
    user_id = 'anonymous'
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        user_id = request.user.id
    ip = request.META.get('REMOTE_ADDR', 'unknown') if request else 'unknown'
    mensagem = f"Erro em {funcao_nome}: {type(exception).__name__}: {str(exception)} | User: {user_id} | IP: {ip}"
    if extra_data:
        mensagem += f" | Extra: {extra_data}"
    logger.error(mensagem, exc_info=True)


def resposta_erro_segura(mensagem_usuario, status=400):
    """Retorna resposta de erro padronizada."""
    return JsonResponse({'success': False, 'message': mensagem_usuario}, status=status)


def _parse_date(date_str):
    """Converte string YYYY-MM-DD para date object."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


def _format_currency_br(value):
    """Formata Decimal para string moeda brasileira."""
    if value is None:
        return "0,00"
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _decimal_from_br(valor_str):
    """Converte string moeda brasileira para Decimal."""
    if not valor_str:
        return Decimal('0')
    limpo = valor_str.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
    try:
        return Decimal(limpo)
    except (InvalidOperation, ValueError):
        return Decimal('0')


def normalizar_texto(texto):
    """Normaliza texto para comparação: lowercase, sem acentos, espaços únicos."""
    if not texto:
        return ''
    texto = str(texto).lower().strip()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto)
                    if unicodedata.category(c) != 'Mn')
    return ' '.join(texto.split())


def normalizar_nome_coluna(nome):
    """Normaliza nome de coluna: lowercase, sem acentos, espaços→underscore."""
    nome = str(nome).lower().strip()
    nome = unicodedata.normalize('NFD', nome)
    nome = ''.join(c for c in nome if not unicodedata.combining(c))
    nome = re.sub(r'[^\w\s]', '', nome)
    nome = re.sub(r'\s+', '_', nome)
    return nome.strip('_')


# =============================================================================
# UTILITÁRIOS DE APROVAÇÃO DE PEDIDOS
# =============================================================================

def get_nivel_aprovacao_usuario(usuario):
    """Retorna o maior nível de aprovação que o usuário possui."""
    niveis = []
    if usuario.groups.filter(name='aprovador_nivel_1').exists() or usuario.has_perm('ERP_ServicesBI.pode_aprovar_pedido_nivel_1'):
        niveis.append(1)
    if usuario.groups.filter(name='aprovador_nivel_2').exists() or usuario.has_perm('ERP_ServicesBI.pode_aprovar_pedido_nivel_2'):
        niveis.append(2)
    if usuario.groups.filter(name='aprovador_nivel_3').exists() or usuario.has_perm('ERP_ServicesBI.pode_aprovar_pedido_nivel_3'):
        niveis.append(3)
    return max(niveis) if niveis else 0


def pode_aprovar_pedido_usuario(pedido, usuario):
    """Verifica se usuário pode aprovar o pedido no nível atual."""
    if pedido.status != 'em_aprovacao':
        return False, "Pedido não está em aprovação"
    nivel_usuario = get_nivel_aprovacao_usuario(usuario)
    proximo_nivel = pedido.nivel_aprovacao_atual + 1
    if nivel_usuario < proximo_nivel:
        return False, f"Requer nível {proximo_nivel}, usuário tem nível {nivel_usuario}"
    return True, None


def verificar_regras_aprovacao(pedido):
    """Verifica se pedido precisa de aprovação baseado nas Regras."""
    regras = RegraAprovacao.objects.filter(
        ativo=True,
        valor_minimo__lte=pedido.valor_total,
        valor_maximo__gte=pedido.valor_total
    ).order_by('nivel')
    if regras.exists():
        return True, regras.last().nivel
    return False, 0

# =============================================================================
# PARTE 2: DASHBOARD
# =============================================================================

@login_required
def dashboard(request):
    """Dashboard principal do ERP com dados financeiros reais."""
    hoje = timezone.now().date()
    inicio_mes = hoje.replace(day=1)

    if inicio_mes.month == 1:
        inicio_mes_anterior = inicio_mes.replace(year=inicio_mes.year - 1, month=12)
    else:
        inicio_mes_anterior = inicio_mes.replace(month=inicio_mes.month - 1)
    fim_mes_anterior = inicio_mes - timedelta(days=1)

    # Contadores de aprovação
    nivel_usuario = get_nivel_aprovacao_usuario(request.user)
    pedidos_pendentes_aprovacao = 0
    if nivel_usuario > 0:
        pedidos_pendentes_aprovacao = PedidoCompra.objects.filter(
            status='em_aprovacao',
            nivel_aprovacao_atual__lt=F('nivel_aprovacao_necessario'),
            nivel_aprovacao_atual__lte=nivel_usuario
        ).count()

    # ---- Receitas do mês ----
    receitas_mes = ContaReceber.objects.filter(
        status__in=['recebido', 'quitado'],
        data_recebimento__gte=inicio_mes,
        data_recebimento__lte=hoje
    ).aggregate(total=Sum('valor_recebido'))['total'] or Decimal('0')

    if receitas_mes == 0:
        receitas_mes = NotaFiscalSaida.objects.filter(
            status='confirmada',
            data_emissao__gte=inicio_mes,
            data_emissao__lte=hoje
        ).aggregate(total=Sum('valor_total'))['total'] or Decimal('0')

    # ---- Despesas do mês ----
    despesas_mes = ContaPagar.objects.filter(
        status__in=['pago', 'quitado'],
        data_pagamento__gte=inicio_mes,
        data_pagamento__lte=hoje
    ).aggregate(total=Sum('valor_pago'))['total'] or Decimal('0')

    if despesas_mes == 0:
        despesas_mes = NotaFiscalEntrada.objects.filter(
            status='confirmada',
            data_emissao__gte=inicio_mes,
            data_emissao__lte=hoje
        ).aggregate(total=Sum('valor_total'))['total'] or Decimal('0')

    saldo_liquido = receitas_mes - despesas_mes

    # Contas pendentes
    contas_receber_pendentes = ContaReceber.objects.filter(
        status__in=['pendente', 'aberto', 'parcial']
    ).aggregate(total=Sum('valor_saldo'))['total'] or Decimal('0')

    contas_pagar_pendentes = ContaPagar.objects.filter(
        status__in=['pendente', 'aberto', 'parcial']
    ).aggregate(total=Sum('valor_saldo'))['total'] or Decimal('0')

    saldo_previsto = saldo_liquido + contas_receber_pendentes - contas_pagar_pendentes

    # ---- Trends vs mês anterior ----
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
            data_emissao__gte=inicio_mes_anterior,
            data_emissao__lte=fim_mes_anterior
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

    # ---- Dados mensais para gráficos (últimos 6 meses) ----
    meses_labels = []
    receitas_mensal = []
    despesas_mensal = []
    nomes_meses = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                   'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

    for i in range(5, -1, -1):
        mes_ref = hoje.month - i
        ano_ref = hoje.year
        while mes_ref <= 0:
            mes_ref += 12
            ano_ref -= 1

        meses_labels.append(nomes_meses[mes_ref])
        inicio_ref = date(ano_ref, mes_ref, 1)
        if mes_ref == 12:
            fim_ref = date(ano_ref + 1, 1, 1) - timedelta(days=1)
        else:
            fim_ref = date(ano_ref, mes_ref + 1, 1) - timedelta(days=1)

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

        desp = ContaPagar.objects.filter(
            status__in=['pago', 'quitado'],
            data_pagamento__gte=inicio_ref,
            data_pagamento__lte=fim_ref
        ).aggregate(total=Sum('valor_pago'))['total'] or Decimal('0')
        if desp == 0:
            desp = NotaFiscalEntrada.objects.filter(
                status='confirmada',
                data_emissao__gte=inicio_ref,
                data_emissao__lte=fim_ref
            ).aggregate(total=Sum('valor_total'))['total'] or Decimal('0')

        receitas_mensal.append(float(rec))
        despesas_mensal.append(float(desp))

    # ---- Top categorias de despesa ----
    top_categorias = []
    categorias_raw = ContaPagar.objects.filter(
        status__in=['pago', 'quitado'],
        data_pagamento__gte=inicio_mes - timedelta(days=90),
        categoria__isnull=False
    ).values('categoria__nome').annotate(total=Sum('valor_pago')).order_by('-total')[:5]

    if categorias_raw:
        max_valor = float(categorias_raw[0]['total']) if categorias_raw else 1
        for cat in categorias_raw:
            top_categorias.append({
                'nome': cat['categoria__nome'],
                'valor': float(cat['total']),
                'percentual': round(float(cat['total']) / max_valor * 100) if max_valor > 0 else 0
            })

    if not top_categorias:
        fornecedores_raw = NotaFiscalEntrada.objects.filter(
            status='confirmada',
            data_emissao__gte=inicio_mes - timedelta(days=90)
        ).values('fornecedor__nome_razao_social').annotate(total=Sum('valor_total')).order_by('-total')[:5]
        max_valor = float(fornecedores_raw[0]['total']) if fornecedores_raw else 1
        for f in fornecedores_raw:
            top_categorias.append({
                'nome': f['fornecedor__nome_razao_social'][:25],
                'valor': float(f['total']),
                'percentual': round(float(f['total']) / max_valor * 100) if max_valor > 0 else 0
            })

    # ---- Despesas por categoria (gráfico donut) ----
    despesas_categorias = []
    cores_donut = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6']
    for i, cat in enumerate(top_categorias):
        despesas_categorias.append({
            'nome': cat['nome'], 'valor': cat['valor'],
            'cor': cores_donut[i % len(cores_donut)]
        })

    # ---- Movimentações recentes ----
    movimentacoes_recentes = []
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

    movimentacoes_recentes.sort(key=lambda x: x['data'], reverse=True)
    movimentacoes_recentes = movimentacoes_recentes[:10]

    context = {
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
        'total_receitas': float(receitas_mes),
        'total_despesas': float(despesas_mes),
        'saldo_liquido': float(saldo_liquido),
        'saldo_previsto': float(saldo_previsto),
        'contas_receber_pendentes': float(contas_receber_pendentes),
        'contas_pagar_pendentes': float(contas_pagar_pendentes),
        'trend_receitas': trend_receitas,
        'trend_despesas': trend_despesas,
        'meses_labels': json.dumps(meses_labels),
        'receitas_mensal': json.dumps(receitas_mensal),
        'despesas_mensal': json.dumps(despesas_mensal),
        'top_categorias': top_categorias,
        'despesas_categorias': json.dumps(despesas_categorias),
        'movimentacoes_recentes': json.dumps(movimentacoes_recentes),
    }
    return render(request, 'dashboard.html', context)
# =============================================================================
# PARTE 3: MÓDULO CADASTRO
# =============================================================================
# -----------------------------------------------------------------------------
# 3.1 CLIENTES
# -----------------------------------------------------------------------------

@login_required
def cliente_manager(request):
    """Listagem de clientes com estatísticas."""
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

    clientes_mes_atual = Cliente.objects.filter(criado_em__gte=inicio_mes_atual).count()
    clientes_mes_anterior = Cliente.objects.filter(
        criado_em__gte=inicio_mes_anterior, criado_em__lt=inicio_mes_atual
    ).count()
    taxa_crescimento = 0
    if clientes_mes_anterior > 0:
        taxa_crescimento = ((clientes_mes_atual - clientes_mes_anterior) / clientes_mes_anterior) * 100
    elif clientes_mes_atual > 0:
        taxa_crescimento = 100

    per_page = request.GET.get('per_page', 25)
    try:
        per_page = int(per_page)
        if per_page not in [10, 25, 50, 100]:
            per_page = 25
    except ValueError:
        per_page = 25

    paginator = Paginator(clientes_list, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'clientes': page_obj, 'page_obj': page_obj, 'paginator': paginator,
        'per_page': per_page, 'search': search, 'total': total,
        'total_ativos': total_ativos, 'total_inativos': total_inativos,
        'percentual_ativos': round(percentual_ativos, 1),
        'percentual_inativos': round(percentual_inativos, 1),
        'taxa_crescimento': round(taxa_crescimento, 1),
    }
    return render(request, 'cadastro/cliente_manager.html', context)


@login_required
def cliente_form(request, pk=None):
    """Formulário de cliente (ADD/EDIT)."""
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
    return render(request, 'cadastro/cliente_form.html', {'form': form, 'cliente': cliente})


@login_required
@require_POST
def cliente_excluir(request, pk):
    """Exclusão AJAX de cliente."""
    cliente = get_object_or_404(Cliente, pk=pk)
    nome = cliente.nome_razao_social
    try:
        cliente.delete()
        return JsonResponse({'success': True, 'message': f'Cliente "{nome}" excluído com sucesso!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao excluir: {str(e)}'}, status=500)


# -----------------------------------------------------------------------------
# 3.2 FORNECEDORES
# -----------------------------------------------------------------------------

@login_required
def fornecedor_manager(request):
    """Listagem de fornecedores."""
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
        'fornecedores': fornecedores_page, 'total': total,
        'total_ativos': total_ativos, 'total_inativos': total_inativos,
        'percentual_ativos': percentual_ativos, 'percentual_inativos': percentual_inativos,
        'search': search, 'per_page': per_page,
    }
    return render(request, 'cadastro/fornecedor_manager.html', context)


@login_required
def fornecedor_form(request, pk=None):
    """Cadastro/edição de fornecedor."""
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
    return render(request, 'cadastro/fornecedor_form.html', {'form': form, 'fornecedor': fornecedor})


@login_required
@require_POST
def fornecedor_excluir(request, pk):
    """Exclusão AJAX de fornecedor."""
    fornecedor = get_object_or_404(Fornecedor, pk=pk)
    try:
        nome = fornecedor.nome_razao_social
        fornecedor.delete()
        return JsonResponse({'success': True, 'message': f'Fornecedor "{nome}" excluído!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro: {str(e)}'}, status=400)


# -----------------------------------------------------------------------------
# 3.3 VENDEDORES
# -----------------------------------------------------------------------------

@login_required
def vendedor_manager(request):
    """Listagem de vendedores."""
    vendedores_list = Vendedor.objects.all().order_by('nome')
    search = request.GET.get('search', '')
    if search:
        vendedores_list = vendedores_list.filter(
            Q(nome__icontains=search) | Q(email__icontains=search) | Q(apelido__icontains=search)
        )

    total = vendedores_list.count()
    total_ativos = vendedores_list.filter(ativo=True).count()
    total_inativos = total - total_ativos
    percentual_ativos = (total_ativos / total * 100) if total > 0 else 0
    comissao_media = vendedores_list.filter(ativo=True).aggregate(media=Avg('comissao_padrao'))['media'] or 0

    per_page = request.GET.get('per_page', 25)
    try:
        per_page = int(per_page)
        if per_page not in [10, 25, 50, 100]:
            per_page = 25
    except ValueError:
        per_page = 25

    paginator = Paginator(vendedores_list, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'vendedores': page_obj, 'page_obj': page_obj, 'paginator': paginator,
        'per_page': per_page, 'search': search, 'total': total,
        'total_ativos': total_ativos, 'total_inativos': total_inativos,
        'percentual_ativos': round(percentual_ativos, 1),
        'percentual_inativos': round((total_inativos / total * 100) if total > 0 else 0, 1),
        'comissao_media': round(comissao_media, 2),
    }
    return render(request, 'cadastro/vendedor_manager.html', context)


@login_required
def vendedor_form(request, pk=None):
    """Cadastro/edição de vendedor."""
    vendedor = get_object_or_404(Vendedor, pk=pk) if pk else None
    if request.method == 'POST':
        form = VendedorForm(request.POST, request.FILES, instance=vendedor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Vendedor salvo com sucesso!')
            return redirect('ERP_ServicesBI:vendedor_manager')
    else:
        form = VendedorForm(instance=vendedor)
    return render(request, 'cadastro/vendedor_form.html', {'form': form, 'vendedor': vendedor})


@login_required
@require_POST
def vendedor_excluir(request, pk):
    """Exclusão AJAX de vendedor."""
    vendedor = get_object_or_404(Vendedor, pk=pk)
    nome = vendedor.nome
    try:
        if vendedor.foto:
            vendedor.foto.delete()
        vendedor.delete()
        return JsonResponse({'success': True, 'message': f'Vendedor "{nome}" excluído!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro: {str(e)}'}, status=500)


# -----------------------------------------------------------------------------
# 3.4 EMPRESAS
# -----------------------------------------------------------------------------

@login_required
def empresa_manager(request):
    """Listagem de empresas."""
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
    try:
        empresas_page = paginator.page(request.GET.get('page', 1))
    except PageNotAnInteger:
        empresas_page = paginator.page(1)
    except EmptyPage:
        empresas_page = paginator.page(paginator.num_pages)

    context = {
        'empresas': empresas_page, 'total': total,
        'total_ativos': total_ativos, 'total_inativos': total_inativos,
        'percentual_ativos': percentual_ativos, 'percentual_inativos': percentual_inativos,
        'search': search, 'per_page': per_page,
    }
    return render(request, 'cadastro/empresa_manager.html', context)


@login_required
def empresa_form(request, pk=None):
    """Cadastro/edição de empresa."""
    empresa = get_object_or_404(Empresa, pk=pk) if pk else None
    if request.method == 'POST':
        form = EmpresaForm(request.POST, instance=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Empresa salva com sucesso!')
            return redirect('ERP_ServicesBI:empresa_list')
        messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = EmpresaForm(instance=empresa)
    return render(request, 'cadastro/empresa_form.html', {'form': form, 'empresa': empresa})


@login_required
@require_POST
def empresa_excluir(request, pk):
    """Exclusão AJAX de empresa."""
    empresa = get_object_or_404(Empresa, pk=pk)
    try:
        nome = empresa.nome_fantasia or empresa.razao_social
        empresa.delete()
        return JsonResponse({'success': True, 'message': f'Empresa "{nome}" excluída!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro: {str(e)}'}, status=400)


# -----------------------------------------------------------------------------
# 3.5 PRODUTOS
# -----------------------------------------------------------------------------

@login_required
def produto_manager(request):
    """Manager de produtos."""
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
            Q(codigo__icontains=search)
        )
    if categoria_id:
        produtos = produtos.filter(categoria_id=categoria_id)

    total = produtos.count()
    total_ativos = produtos.filter(ativo=True).count()
    total_inativos = total - total_ativos
    estoque_baixo = produtos.filter(estoque_atual__lte=F('estoque_minimo')).count()

    paginator = Paginator(produtos.order_by('descricao'), per_page)
    try:
        produtos_page = paginator.page(request.GET.get('page', 1))
    except PageNotAnInteger:
        produtos_page = paginator.page(1)
    except EmptyPage:
        produtos_page = paginator.page(paginator.num_pages)

    context = {
        'produtos': produtos_page, 'total': total,
        'total_ativos': total_ativos, 'total_inativos': total_inativos,
        'estoque_baixo': estoque_baixo, 'search': search,
        'categoria_id': categoria_id,
        'categorias': CategoriaProduto.objects.filter(ativo=True),
        'per_page': per_page,
    }
    return render(request, 'cadastro/produto_manager.html', context)


@login_required
def produto_form(request, pk=None):
    """Cadastro/edição de produto."""
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
        'form': form, 'produto': produto,
        'categorias': CategoriaProduto.objects.filter(ativo=True),
    })


@login_required
@require_POST
def produto_excluir(request, pk):
    """Exclusão AJAX de produto."""
    produto = get_object_or_404(Produto, pk=pk)
    try:
        descricao = produto.descricao
        produto.delete()
        return JsonResponse({'success': True, 'message': f'Produto "{descricao}" excluído!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro: {str(e)}'}, status=400)


# -----------------------------------------------------------------------------
# 3.6 APIs AJAX — CATEGORIA DE PRODUTO
# -----------------------------------------------------------------------------

@login_required
@require_POST
def categoria_produto_create_ajax(request):
    """Criação AJAX de Categoria de Produto."""
    try:
        nome = request.POST.get('nome', '').strip()
        descricao = request.POST.get('descricao', '')
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome é obrigatório'}, status=400)
        categoria = CategoriaProduto.objects.create(nome=nome, descricao=descricao, ativo=True)
        return JsonResponse({
            'success': True, 'id': categoria.id, 'nome': categoria.nome,
            'message': f'Categoria "{categoria.nome}" criada!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro: {str(e)}'}, status=500)


@login_required
@require_POST
def categoria_produto_delete_ajax(request, pk):
    """Exclusão AJAX de Categoria de Produto."""
    try:
        categoria = get_object_or_404(CategoriaProduto, pk=pk)
        if Produto.objects.filter(categoria=categoria).exists():
            return JsonResponse({'success': False, 'message': 'Categoria em uso por produtos.'}, status=400)
        nome = categoria.nome
        categoria.delete()
        return JsonResponse({'success': True, 'message': f'Categoria "{nome}" excluída!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro: {str(e)}'}, status=500)


# -----------------------------------------------------------------------------
# 3.7 APIs AJAX — CONDIÇÃO DE PAGAMENTO
# -----------------------------------------------------------------------------

@login_required
@require_POST
def api_condicao_pagamento_criar(request):
    """API para criar condição de pagamento via AJAX."""
    try:
        data = json.loads(request.body)
        descricao = data.get('descricao', '').strip()
        parcelas = data.get('parcelas', 1)
        periodicidade = data.get('periodicidade', 'mensal')
        dias_primeira_parcela = data.get('dias_primeira_parcela', 0)

        if not descricao:
            return resposta_erro_segura('Descrição é obrigatória', 400)
        if not parcelas or int(parcelas) < 1 or int(parcelas) > 24:
            return resposta_erro_segura('Parcelas deve ser entre 1 e 24', 400)

        periodos_validos = [p[0] for p in CondicaoPagamento.PERIODICIDADE_CHOICES]
        if periodicidade not in periodos_validos:
            return resposta_erro_segura('Periodicidade inválida', 400)

        condicao = CondicaoPagamento.objects.create(
            descricao=descricao, parcelas=int(parcelas),
            periodicidade=periodicidade,
            dias_primeira_parcela=int(dias_primeira_parcela), ativo=True
        )
        return JsonResponse({
            'success': True, 'id': condicao.id, 'descricao': condicao.descricao,
            'descricao_completa': f'{condicao.descricao} ({condicao.resumo})',
            'resumo': condicao.resumo, 'prazo_total': condicao.prazo_total_dias,
            'message': f'Condição "{condicao.descricao}" criada!'
        })
    except json.JSONDecodeError:
        return resposta_erro_segura('Dados inválidos', 400)
    except Exception as e:
        return resposta_erro_segura(f'Erro: {str(e)}', 500)


@login_required
@require_POST
def api_condicao_pagamento_excluir(request, pk):
    """API para excluir condição de pagamento."""
    try:
        condicao = get_object_or_404(CondicaoPagamento, pk=pk)
        descricao = condicao.descricao
        if condicao.clientes_condicao.exists():
            return resposta_erro_segura(f'Condição "{descricao}" em uso por clientes.', 400)
        condicao.delete()
        return JsonResponse({'success': True, 'message': f'Condição "{descricao}" excluída!'})
    except Exception as e:
        return resposta_erro_segura(f'Erro: {str(e)}', 500)


# Aliases para compatibilidade
condicao_pagamento_criar_api = api_condicao_pagamento_criar
condicao_pagamento_excluir_api = api_condicao_pagamento_excluir


# -----------------------------------------------------------------------------
# 3.8 APIs AJAX — FORMA DE PAGAMENTO
# -----------------------------------------------------------------------------

@login_required
@require_POST
def api_forma_pagamento_criar(request):
    """API para criar forma de pagamento via AJAX."""
    try:
        data = json.loads(request.body)
        descricao = data.get('descricao', '').strip()
        tipo = data.get('tipo', '').strip()

        if not descricao:
            return resposta_erro_segura('Descrição é obrigatória', 400)
        if not tipo:
            return resposta_erro_segura('Tipo é obrigatório', 400)

        tipos_validos = [t[0] for t in FormaPagamento.TIPO_CHOICES]
        if tipo not in tipos_validos:
            return resposta_erro_segura('Tipo inválido', 400)

        forma = FormaPagamento.objects.create(descricao=descricao, tipo=tipo, ativo=True)
        return JsonResponse({
            'success': True, 'id': forma.id,
            'descricao': f'{forma.descricao} ({forma.get_tipo_display()})',
            'message': f'Forma "{forma.descricao}" criada!'
        })
    except json.JSONDecodeError:
        return resposta_erro_segura('Dados inválidos', 400)
    except Exception as e:
        return resposta_erro_segura(f'Erro: {str(e)}', 500)


@login_required
@require_POST
def api_forma_pagamento_excluir(request, pk):
    """API para excluir forma de pagamento."""
    try:
        forma = get_object_or_404(FormaPagamento, pk=pk)
        descricao = forma.descricao
        if forma.clientes_forma.exists():
            return resposta_erro_segura(f'Forma "{descricao}" em uso por clientes.', 400)
        forma.delete()
        return JsonResponse({'success': True, 'message': f'Forma "{descricao}" excluída!'})
    except Exception as e:
        return resposta_erro_segura(f'Erro: {str(e)}', 500)


# Aliases para compatibilidade
forma_pagamento_criar_api = api_forma_pagamento_criar
forma_pagamento_excluir_api = api_forma_pagamento_excluir

# =============================================================================
# PARTE 4: MÓDULO COMPRAS
# =============================================================================
# 4.1 COTAÇÕES — MANAGER
# -----------------------------------------------------------------------------

@login_required
def cotacao_manager(request):
    """Manager unificado de cotações."""
    search = request.GET.get('search', '').strip()[:100]
    status = request.GET.get('status', '').strip()

    cotacoes = CotacaoMae.objects.select_related('solicitante').prefetch_related(
        'itens_solicitados', 'cotacoes_fornecedor'
    ).order_by('-data_solicitacao')

    if search:
        cotacoes = cotacoes.filter(Q(numero__icontains=search) | Q(titulo__icontains=search))
    if status:
        cotacoes = cotacoes.filter(status=status)

    paginator = Paginator(cotacoes, 25)
    cotacoes_page = paginator.get_page(request.GET.get('page'))

    contadores = CotacaoMae.objects.aggregate(
        total=Count('id'),
        em_andamento=Count('id', filter=Q(status__in=['rascunho', 'enviada'])),
        respondidas=Count('id', filter=Q(status='respondida')),
        concluidas=Count('id', filter=Q(status='concluida'))
    )

    context = {
        'cotacoes': cotacoes_page,
        'total_cotacoes': contadores['total'],
        'em_andamento': contadores['em_andamento'],
        'respondidas': contadores['respondidas'],
        'concluidas': contadores['concluidas'],
        'produtos': Produto.objects.filter(ativo=True).order_by('descricao')[:500],
        'fornecedores': Fornecedor.objects.filter(ativo=True).order_by('nome_fantasia', 'nome_razao_social')[:200],
        'condicoes_pagamento': CondicaoPagamento.objects.filter(ativo=True).order_by('descricao'),
        'formas_pagamento': FormaPagamento.objects.filter(ativo=True).order_by('descricao'),
        'search': search, 'status': status,
    }
    return render(request, 'compras/cotacao_manager.html', context)

@login_required
def cotacao_form(request, pk=None):
    """Formulário de cotação (ADD/EDIT) - Padrão Manager+Form."""
    cotacao = get_object_or_404(CotacaoMae, pk=pk) if pk else None

    if request.method == 'POST':
        form = CotacaoMaeForm(request.POST, instance=cotacao)
        if form.is_valid():
            cotacao = form.save(commit=False)
            if not pk:
                cotacao.solicitante = request.user
            cotacao.save()

            # Processar itens do JSON
            itens_json = request.POST.get('itens_json', '[]')
            try:
                itens = json.loads(itens_json)
            except json.JSONDecodeError:
                itens = []

            # Remover itens antigos se for edição
            if pk:
                cotacao.itens_solicitados.all().delete()

            # Criar novos itens
            for item in itens[:1000]:  # Limite de segurança
                try:
                    ItemSolicitado.objects.create(
                        cotacao_mae=cotacao,
                        produto_id=item.get('produto_id') if item.get('produto_id') else None,
                        descricao_manual=item.get('descricao', '')[:500],
                        quantidade=Decimal(str(item.get('quantidade', 1))),
                        unidade_medida=item.get('unidade', 'UN')[:10],
                        observacao=item.get('observacao', '')[:500],
                    )
                except (ValueError, KeyError, TypeError):
                    continue

            # Processar fornecedores
            fornecedores_ids = request.POST.getlist('fornecedores') or []
            if fornecedores_ids:
                for forn_id in fornecedores_ids[:50]:  # Limite de segurança
                    try:
                        CotacaoFornecedor.objects.get_or_create(
                            cotacao_mae=cotacao,
                            fornecedor_id=int(forn_id),
                            defaults={'status': 'pendente'}
                        )
                    except (ValueError, TypeError):
                        continue

            messages.success(request, f'Cotação {cotacao.numero} salva com sucesso!')
            return redirect('ERP_ServicesBI:cotacao_manager')
        else:
            messages.error(request, 'Corrija os erros no formulário.')
    else:
        form = CotacaoMaeForm(instance=cotacao) if cotacao else CotacaoMaeForm()

    # Buscar itens existentes para edição
    itens = []
    if cotacao:
        itens = list(cotacao.itens_solicitados.select_related('produto').values(
            'id', 'produto_id', 'descricao_manual', 'quantidade', 'unidade_medida', 'observacao'
        ))

    context = {
        'form': form,
        'cotacao': cotacao,
        'itens': json.dumps(itens),
        'produtos': Produto.objects.filter(ativo=True).order_by('descricao')[:500],
        'fornecedores': Fornecedor.objects.filter(ativo=True).order_by('nome_fantasia', 'nome_razao_social')[:200],
        'condicoes_pagamento': CondicaoPagamento.objects.filter(ativo=True).order_by('descricao'),
        'formas_pagamento': FormaPagamento.objects.filter(ativo=True).order_by('descricao'),
        'titulo': 'Editar Cotação' if cotacao else 'Nova Cotação',
    }
    return render(request, 'compras/cotacao_form.html', context)




# -----------------------------------------------------------------------------
# 4.2 COTAÇÕES — APIs
# -----------------------------------------------------------------------------

@login_required
@require_POST
def cotacao_salvar_api(request):
    """API unificada para salvar cotação."""
    try:
        if len(request.body) > 10 * 1024 * 1024:
            return resposta_erro_segura('Payload muito grande', 413)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return resposta_erro_segura('JSON inválido', 400)

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

            status_enviado = data.get('status', 'rascunho').lower()
            status_validos = ['rascunho', 'enviada', 'respondida', 'em_analise', 'concluida', 'cancelada']
            cotacao.status = status_enviado if status_enviado in status_validos else 'rascunho'
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
                    id__in=fornecedores_ids[:50], ativo=True
                ).values_list('id', flat=True)
                cotacao.cotacoes_fornecedor.exclude(fornecedor_id__in=fornecedores_validos).delete()
                for forn_id in fornecedores_validos:
                    CotacaoFornecedor.objects.get_or_create(
                        cotacao_mae=cotacao, fornecedor_id=forn_id,
                        defaults={'status': 'pendente', 'condicao_pagamento': '', 'forma_pagamento': ''}
                    )

            return JsonResponse({
                'success': True, 'id': cotacao.pk, 'numero': cotacao.numero,
                'itens': list(cotacao.itens_solicitados.values('id', 'produto_id', 'descricao_manual', 'quantidade', 'unidade_medida')),
                'fornecedores': list(cotacao.cotacoes_fornecedor.values_list('fornecedor_id', flat=True)),
                'message': 'Cotação salva com sucesso!'
            })
    except Exception as e:
        log_erro_seguro('cotacao_salvar_api', e, request)
        return resposta_erro_segura('Erro interno ao salvar cotação.', 500)


@login_required
@require_GET
def cotacao_dados_api(request, pk):
    """API para buscar dados completos da cotação."""
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        itens_list = []
        for item in cotacao.itens_solicitados.select_related('produto').all():
            try:
                descricao = item.descricao_display or item.descricao_manual or 'Item sem descrição'
                itens_list.append({
                    'id': item.id, 'produto_id': item.produto_id,
                    'descricao_manual': item.descricao_manual or '',
                    'descricao_display': descricao,
                    'quantidade': float(item.quantidade) if item.quantidade else 0.0,
                    'unidade_medida': item.unidade_medida or 'UN',
                    'observacao': item.observacao or ''
                })
            except Exception:
                continue

        data_limite = None
        if cotacao.data_limite_resposta:
            try:
                data_limite = cotacao.data_limite_resposta.isoformat()
            except (AttributeError, ValueError):
                data_limite = str(cotacao.data_limite_resposta)

        return JsonResponse({
            'success': True, 'id': cotacao.id, 'numero': cotacao.numero,
            'titulo': cotacao.titulo or '', 'setor': cotacao.setor or '',
            'status': cotacao.status or 'rascunho', 'data_limite': data_limite,
            'observacoes': cotacao.observacoes or '', 'itens': itens_list,
            'fornecedores': list(cotacao.cotacoes_fornecedor.values_list('fornecedor_id', flat=True)),
        })
    except CotacaoMae.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Cotação não encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def _normalizar_para_match(texto):
    """Normaliza texto para matching no comparativo."""
    if not texto:
        return ''
    texto = str(texto).lower().strip()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return ' '.join(texto.split())


@login_required
@require_GET
def cotacao_comparativo_api(request, pk):
    """API para buscar dados do comparativo de preços."""
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        cotacoes_forn = list(
            cotacao.cotacoes_fornecedor.select_related('fornecedor').prefetch_related(
                Prefetch('itens', queryset=ItemCotacaoFornecedor.objects.select_related('item_solicitado'), to_attr='itens_pre_carregados')
            ).all()
        )

        # Coletar itens únicos
        itens_unificados = []
        itens_por_sol_id = {}
        itens_por_desc = {}

        for item_sol in cotacao.itens_solicitados.select_related('produto').all():
            idx = len(itens_unificados)
            desc = item_sol.descricao_display or ''
            desc_norm = _normalizar_para_match(desc)
            itens_unificados.append({
                'id': f'sol_{item_sol.id}', 'item_solicitado_id': item_sol.id,
                'nome': desc, 'quantidade': float(item_sol.quantidade),
                'unidade': item_sol.unidade_medida or 'UN',
            })
            itens_por_sol_id[item_sol.id] = idx
            if desc_norm:
                itens_por_desc[desc_norm] = idx

        # Itens órfãos
        for cf in cotacoes_forn:
            for item_cot in getattr(cf, 'itens_pre_carregados', []):
                if item_cot.item_solicitado_id and item_cot.item_solicitado_id in itens_por_sol_id:
                    continue
                desc = item_cot.descricao_fornecedor or ''
                desc_norm = _normalizar_para_match(desc)
                if not desc_norm or desc_norm in itens_por_desc:
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
                    'id': f'orf_{item_cot.id}', 'item_solicitado_id': None,
                    'nome': desc, 'quantidade': float(item_cot.quantidade or 1),
                    'unidade': item_cot.unidade_medida or 'UN',
                })
                itens_por_desc[desc_norm] = idx

        # Montar fornecedores
        fornecedores_list = []
        total_itens_base = len(itens_unificados) or 1
        for cf in cotacoes_forn:
            nome = cf.fornecedor.nome_fantasia or cf.fornecedor.nome_razao_social
            itens_cotados = sum(1 for i in getattr(cf, 'itens_pre_carregados', [])
                                if i.disponivel and i.preco_unitario and i.preco_unitario > 0)
            pct = round((itens_cotados / total_itens_base) * 100)
            fornecedores_list.append({
                'id': cf.id, 'fornecedor_id': cf.fornecedor_id, 'nome': nome,
                'contato': cf.contato_nome or '', 'email': cf.contato_email or '',
                'telefone': cf.contato_telefone or '',
                'valor_total_bruto': float(cf.valor_total_bruto or 0),
                'percentual_desconto': float(cf.percentual_desconto or 0),
                'valor_frete': float(cf.valor_frete or 0),
                'valor_total_liquido': float(cf.valor_total_liquido or 0),
                'condicao_pagamento': cf.condicao_pagamento or 'À vista',
                'forma_pagamento': cf.forma_pagamento or '',
                'prazo_entrega_dias': cf.prazo_entrega_dias or 0,
                'disponibilidade': f'{pct}%', 'disponibilidade_pct': pct,
                'nota_confiabilidade': cf.nota_confiabilidade or 5,
                'total_itens_cotados': itens_cotados, 'status': cf.status,
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
                if sol_id:
                    item_cot = lookup_por_sol.get((cf.id, sol_id))
                if not item_cot and item_desc_norm:
                    item_cot = lookup_por_desc.get((cf.id, item_desc_norm))
                if not item_cot and item_desc_norm:
                    for (cf_key, desc_key), ic in lookup_por_desc.items():
                        if cf_key == cf.id and (desc_key in item_desc_norm or item_desc_norm in desc_key):
                            item_cot = ic
                            break
                if not item_cot and item_desc_norm:
                    palavras_item = {p for p in item_desc_norm.split() if len(p) > 2}
                    melhor_score = 0
                    for (cf_key, desc_key), ic in lookup_por_desc.items():
                        if cf_key == cf.id:
                            comuns = len(palavras_item & {p for p in desc_key.split() if len(p) > 2})
                            if comuns >= 2 and comuns > melhor_score:
                                melhor_score = comuns
                                item_cot = ic

                if item_cot and item_cot.disponivel and item_cot.preco_unitario and item_cot.preco_unitario > 0:
                    respostas[cf.id][item['id']] = {
                        'item_cotacao_id': item_cot.id,
                        'preco_unitario': float(item_cot.preco_unitario),
                        'preco_total': float(item_cot.preco_total or 0),
                        'descricao_fornecedor': item_cot.descricao_fornecedor or '',
                        'disponivel': True,
                        'prazo': item_cot.prazo_entrega_item or cf.prazo_entrega_dias or 0,
                        'melhor_preco': False, 'melhor_prazo': False,
                        'selecionado': item_cot.selecionado, 'sugerido': item_cot.sugerido,
                    }
                elif item_cot and not item_cot.disponivel:
                    respostas[cf.id][item['id']] = {
                        'item_cotacao_id': item_cot.id, 'preco_unitario': 0, 'preco_total': 0,
                        'descricao_fornecedor': item_cot.descricao_fornecedor or '',
                        'disponivel': False, 'prazo': 0,
                        'melhor_preco': False, 'melhor_prazo': False,
                        'selecionado': False, 'sugerido': False,
                    }

        # Melhor preço/prazo por item
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
                respostas[min(precos, key=lambda x: x[1])[0]][item['id']]['melhor_preco'] = True
            if prazos:
                respostas[min(prazos, key=lambda x: x[1])[0]][item['id']]['melhor_prazo'] = True

        menor_total_id = None
        forn_com_valor = [f for f in fornecedores_list if f['valor_total_liquido'] > 0]
        if forn_com_valor:
            menor_total_id = min(forn_com_valor, key=lambda f: f['valor_total_liquido'])['id']

        return JsonResponse({
            'success': True, 'itens': itens_unificados, 'fornecedores': fornecedores_list,
            'respostas': respostas, 'menor_total_id': menor_total_id,
        })
    except Exception as e:
        log_erro_seguro('cotacao_comparativo_api', e, request, {'cotacao_id': pk})
        return resposta_erro_segura('Erro ao gerar comparativo', 500)


# -----------------------------------------------------------------------------
# 4.3 COTAÇÕES — AÇÕES (Excluir, Enviar, Concluir, etc.)
# -----------------------------------------------------------------------------

@login_required
@require_POST
def cotacao_excluir_api(request, pk):
    try:
        get_object_or_404(CotacaoMae, pk=pk).delete()
        return JsonResponse({'success': True, 'message': 'Cotação excluída!'})
    except Exception as e:
        log_erro_seguro('cotacao_excluir_api', e, request)
        return resposta_erro_segura('Erro ao excluir cotação', 500)


@login_required
@require_POST
def cotacao_enviar_api(request, pk):
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        cotacao.status = 'enviada'
        cotacao.save()
        return JsonResponse({'success': True, 'message': 'Cotação enviada!'})
    except Exception as e:
        log_erro_seguro('cotacao_enviar_api', e, request)
        return resposta_erro_segura('Erro ao enviar cotação', 500)


@login_required
@require_POST
def cotacao_concluir_api(request, pk):
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        cotacao.status = 'concluida'
        cotacao.save()
        return JsonResponse({'success': True, 'message': 'Cotação concluída!'})
    except Exception as e:
        log_erro_seguro('cotacao_concluir_api', e, request)
        return resposta_erro_segura('Erro ao concluir cotação', 500)


@login_required
def cotacao_confirm_delete(request, pk):
    cotacao = get_object_or_404(CotacaoMae, pk=pk)
    if request.method == 'POST':
        cotacao.delete()
        messages.success(request, 'Cotação excluída!')
        return redirect('ERP_ServicesBI:cotacao_manager')
    return render(request, 'compras/cotacao_confirm_delete.html', {
        'objeto': cotacao, 'titulo': 'Excluir Cotação',
        'nome_objeto': f'Cotação {cotacao.numero}',
        'url_cancelar': 'ERP_ServicesBI:cotacao_manager',
    })


@login_required
@require_GET
def cotacao_fornecedores_importados_api(request, pk):
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        importados = cotacao.cotacoes_fornecedor.exclude(
            arquivo_origem=''
        ).exclude(
            arquivo_origem__isnull=True
        ).values_list('fornecedor_id', flat=True)
        return JsonResponse({'success': True, 'importados': [int(fid) for fid in importados]})
    except Exception as e:
        return resposta_erro_segura('Erro ao buscar fornecedores', 500)


@login_required
@require_POST
def cotacao_remover_fornecedor(request, pk, fornecedor_pk):
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        get_object_or_404(CotacaoFornecedor, cotacao_mae=cotacao, fornecedor_id=fornecedor_pk).delete()
        return JsonResponse({'success': True, 'message': 'Fornecedor removido!'})
    except Exception as e:
        return resposta_erro_segura('Erro ao remover fornecedor', 500)


@login_required
@require_GET
def cotacao_copiar_lista_email(request, pk):
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        linhas = [
            f"Solicitação de Cotação: {cotacao.numero}", f"Título: {cotacao.titulo}",
            f"Setor: {cotacao.setor}",
            f"Data Limite: {cotacao.data_limite_resposta.strftime('%d/%m/%Y') if cotacao.data_limite_resposta else 'Não definida'}",
            "", "ITENS SOLICITADOS:", "-" * 50,
        ]
        for i, item in enumerate(cotacao.itens_solicitados.all(), 1):
            linhas.append(f"{i}. {item.descricao_display}")
            linhas.append(f"   Quantidade: {item.quantidade} {item.unidade_medida}")
            if item.observacao:
                linhas.append(f"   Obs: {item.observacao}")
            linhas.append("")
        linhas.extend(["-" * 50, "Por favor, enviar cotação com preços unitários e prazo de entrega.", "",
                       "Atenciosamente,", cotacao.solicitante.get_full_name() or cotacao.solicitante.username])
        return JsonResponse({'success': True, 'texto': '\n'.join(linhas)})
    except Exception as e:
        return resposta_erro_segura('Erro ao gerar texto', 500)


@login_required
@require_GET
def cotacao_copiar_lista_whatsapp(request, pk):
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        linhas = [f"*Solicitação de Cotação: {cotacao.numero}*", f"📋 {cotacao.titulo}",
                  f"🏢 Setor: {cotacao.setor}", "", "*ITENS:*"]
        for i, item in enumerate(cotacao.itens_solicitados.all(), 1):
            linhas.append(f"{i}. {item.descricao_display} - {item.quantidade} {item.unidade_medida}")
        linhas.extend(["", "📅 Aguardo cotação com preços e prazo.", "Obrigado!"])
        return JsonResponse({'success': True, 'texto': '\n'.join(linhas)})
    except Exception as e:
        return resposta_erro_segura('Erro ao gerar texto', 500)


# -----------------------------------------------------------------------------
# 4.4 COTAÇÕES — IMPORTAÇÃO DE ARQUIVOS
# -----------------------------------------------------------------------------

@login_required
@require_POST
def cotacao_importar_fornecedor(request, pk):
    """Importa arquivo de cotação do fornecedor."""
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        fornecedor_id = request.POST.get('fornecedor_id')
        arquivo = request.FILES.get('arquivo')

        if not fornecedor_id:
            return resposta_erro_segura('Selecione um fornecedor', 400)
        if not arquivo:
            return resposta_erro_segura('Selecione um arquivo', 400)

        nome_arquivo = arquivo.name.lower()
        if not nome_arquivo.endswith(('.csv', '.xlsx', '.xls', '.pdf')):
            return resposta_erro_segura('Apenas CSV, Excel ou PDF', 400)
        if arquivo.size > 10 * 1024 * 1024:
            return resposta_erro_segura('Arquivo muito grande (máx 10MB)', 413)

        fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_id)
        cotacao_forn, created = CotacaoFornecedor.objects.get_or_create(
            cotacao_mae=cotacao, fornecedor=fornecedor,
            defaults={'status': 'importada', 'data_recebimento': timezone.now().date()}
        )

        if arquivo:
            cotacao_forn.arquivo_origem = arquivo
            cotacao_forn.save()
            try:
                _processar_arquivo_cotacao(cotacao, cotacao_forn, arquivo)
                _sincronizar_itens_cotacao(cotacao)
                cotacao_forn.calcular_total()
            except Exception as e:
                log_erro_seguro('processar_arquivo_cotacao', e, request)
                return resposta_erro_segura('Erro ao processar arquivo.', 400)

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

        cotacao.status = 'respondida'
        cotacao.save()

        return JsonResponse({
            'success': True, 'cotacao_fornecedor_id': cotacao_forn.pk,
            'fornecedor_nome': fornecedor.nome_fantasia or fornecedor.nome_razao_social,
            'total_itens': cotacao_forn.itens.count(),
            'valor_total': float(cotacao_forn.valor_total_liquido or 0),
            'message': 'Cotação importada!'
        })
    except Exception as e:
        log_erro_seguro('cotacao_importar_fornecedor', e, request)
        return resposta_erro_segura('Erro ao importar cotação', 500)


# -- Funções auxiliares de processamento de arquivo (CSV, Excel, PDF) --

def _processar_arquivo_cotacao(cotacao_mae, cotacao_forn, arquivo):
    """Processa arquivo de cotação."""
    nome = arquivo.name.lower()
    cotacao_forn.itens.all().delete()
    if hasattr(cotacao_mae, '_itens_solicitados_cache'):
        delattr(cotacao_mae, '_itens_solicitados_cache')

    if nome.endswith('.csv'):
        _processar_csv_cotacao(cotacao_mae, cotacao_forn, arquivo)
    elif nome.endswith(('.xlsx', '.xls')):
        _processar_excel_cotacao(cotacao_mae, cotacao_forn, arquivo)
    elif nome.endswith('.pdf'):
        _processar_pdf_cotacao(cotacao_mae, cotacao_forn, arquivo)


def _processar_csv_cotacao(cotacao_mae, cotacao_forn, arquivo):
    try:
        conteudo = arquivo.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        arquivo.seek(0)
        conteudo = arquivo.read().decode('latin-1')

    primeira_linha = conteudo.split('\n')[0] if conteudo else ''
    delimitador = ';' if ';' in primeira_linha else ','
    leitor = csv.DictReader(io.StringIO(conteudo), delimiter=delimitador)
    if leitor.fieldnames:
        leitor.fieldnames = [normalizar_nome_coluna(col) for col in leitor.fieldnames]

    itens_criar = []
    for i, row in enumerate(leitor):
        if i >= 1000:
            break
        item = _criar_item_cotacao(cotacao_mae, cotacao_forn, row)
        if item:
            itens_criar.append(item)
    if itens_criar:
        ItemCotacaoFornecedor.objects.bulk_create(itens_criar, batch_size=100)


def _processar_excel_cotacao(cotacao_mae, cotacao_forn, arquivo):
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
                row_dict[header] = value if isinstance(value, (int, float)) else (str(value).strip() if value else '')
            item = _criar_item_cotacao(cotacao_mae, cotacao_forn, row_dict)
            if item:
                itens_criar.append(item)
        if itens_criar:
            ItemCotacaoFornecedor.objects.bulk_create(itens_criar, batch_size=100)
        wb.close()
    except ImportError:
        import pandas as pd
        df = pd.read_excel(arquivo)
        itens_criar = []
        for _, row in df.iterrows():
            row_dict = {normalizar_nome_coluna(str(k)): ('' if pd.isna(v) else v) for k, v in row.items()}
            item = _criar_item_cotacao(cotacao_mae, cotacao_forn, row_dict)
            if item:
                itens_criar.append(item)
        if itens_criar:
            ItemCotacaoFornecedor.objects.bulk_create(itens_criar, batch_size=100)


def _processar_pdf_cotacao(cotacao_mae, cotacao_forn, arquivo):
    import tempfile, os
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
                        headers = [normalizar_nome_coluna(str(h or '')) for h in table[0]]
                        for row_values in table[1:]:
                            if not row_values or all(not v or str(v).strip() == '' for v in row_values):
                                continue
                            row_dict = dict(zip(headers, row_values))
                            item = _criar_item_cotacao(cotacao_mae, cotacao_forn, row_dict)
                            if item:
                                itens_criar.append(item)
                if not itens_criar:
                    for page in pdf.pages:
                        texto = page.extract_text() or ''
                        itens_criar.extend(_extrair_itens_texto(texto, cotacao_mae, cotacao_forn))
        except ImportError:
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(tmp_path)
                texto = '\n'.join(page.extract_text() or '' for page in reader.pages)
                itens_criar = _extrair_itens_texto(texto, cotacao_mae, cotacao_forn)
            except ImportError:
                raise ValueError("Nenhuma biblioteca de PDF disponível. Instale pdfplumber.")

        if itens_criar:
            ItemCotacaoFornecedor.objects.bulk_create(itens_criar, batch_size=100)
        if not itens_criar:
            raise ValueError("Não foi possível extrair itens do PDF.")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _extrair_itens_texto(texto, cotacao_mae, cotacao_forn):
    """Extrai itens de texto bruto usando regex."""
    itens = []
    padrao1 = re.compile(
        r'^\s*\d+\s+(.+?)\s+(UN|PC|KG|CX|LT|MT|M2|M3|PCT|PAR|JG|RL|FD|SC|GL|FR|TB|CT|DZ|MIL)\s+'
        r'([\d.,]+)\s+R?\$?\s*([\d.,]+)', re.IGNORECASE)
    padrao2 = re.compile(r'^(.{5,60}?)\s+([\d.,]+)\s+R?\$?\s*([\d.,]+)\s*$', re.IGNORECASE)
    ignorar = ['descricao', 'produto', 'item', 'total', 'subtotal', 'frete', 'desconto',
               'observa', 'condic', 'pagamento', '---', '===', 'cotacao', 'cnpj', 'telefone']

    for linha in texto.strip().split('\n'):
        linha = linha.strip()
        if not linha or len(linha) < 5:
            continue
        if any(h in linha.lower() for h in ignorar):
            continue
        match = padrao1.match(linha)
        if match:
            desc, unidade, qtd_str, preco_str = match.group(1).strip(), match.group(2).upper(), match.group(3), match.group(4)
        else:
            match = padrao2.match(linha)
            if match:
                desc, unidade, qtd_str, preco_str = match.group(1).strip(), 'UN', match.group(2), match.group(3)
            else:
                continue
        try:
            qtd = Decimal(qtd_str.replace('.', '').replace(',', '.'))
            preco = Decimal(preco_str.replace('.', '').replace(',', '.'))
            if qtd <= 0 or preco <= 0:
                continue
        except (InvalidOperation, ValueError):
            continue
        item = _criar_item_cotacao(cotacao_mae, cotacao_forn,
                                    {'descricao': desc, 'unidade': unidade, 'quantidade': str(qtd), 'preco_unitario': str(preco)})
        if item:
            itens.append(item)
    return itens


def _criar_item_cotacao(cotacao_mae, cotacao_forn, row):
    """Cria item de cotação a partir de uma linha do arquivo."""
    # Extração de descrição
    descricao = ''
    for key in ['descricao', 'produto', 'item', 'material', 'nome', 'descricao_produto', 'servico', 'prod', 'desc']:
        if key in row and row[key]:
            descricao = str(row[key]).strip()
            if descricao:
                break
    if not descricao:
        for key, value in row.items():
            if value and str(value).strip() and len(str(value).strip()) > 3:
                if any(term in str(key).lower() for term in ['preco', 'valor', 'qtd', 'quant', 'cod', 'unid']):
                    continue
                descricao = str(value).strip()
                break
    descricao = descricao[:500]
    if not descricao:
        return None
    if any(p in descricao.lower() for p in ('total', 'subtotal', 'frete', 'desconto', 'observacao', 'condicoes')):
        return None

    # Quantidade
    qtd_str = str(row.get('quantidade') or row.get('qtd') or row.get('qtde') or row.get('quant') or row.get('qty') or 1)
    try:
        qtd_clean = str(qtd_str).replace(' ', '')
        if ',' in qtd_clean and '.' in qtd_clean:
            qtd_clean = qtd_clean.replace('.', '').replace(',', '.') if qtd_clean.rfind(',') > qtd_clean.rfind('.') else qtd_clean.replace(',', '')
        elif ',' in qtd_clean:
            qtd_clean = qtd_clean.replace(',', '.')
        quantidade = Decimal(qtd_clean)
        if quantidade <= 0 or quantidade > 999999:
            quantidade = Decimal('1')
    except (InvalidOperation, ValueError):
        quantidade = Decimal('1')

    # Preço
    preco_str = None
    for key in ['preco_unitario', 'preco', 'valor_unitario', 'valor', 'unitario', 'vl_unitario', 'preco_un', 'valor_un']:
        if key in row and row[key] is not None and str(row[key]) not in ('0', '0.0', '0,00', ''):
            preco_str = str(row[key])
            break
    preco_str = preco_str or '0'
    try:
        preco_clean = preco_str.replace('R$', '').replace(' ', '')
        if ',' in preco_clean and '.' in preco_clean:
            preco_clean = preco_clean.replace('.', '').replace(',', '.') if preco_clean.rfind(',') > preco_clean.rfind('.') else preco_clean.replace(',', '')
        elif ',' in preco_clean:
            preco_clean = preco_clean.replace(',', '.')
        preco_unitario = Decimal(preco_clean)
        if preco_unitario < 0 or preco_unitario > 999999999:
            preco_unitario = Decimal('0')
    except (InvalidOperation, ValueError):
        preco_unitario = Decimal('0')

    codigo = str(row.get('codigo') or row.get('cod') or row.get('ref') or row.get('sku') or '')[:50]
    unidade = str(row.get('unidade') or row.get('un') or row.get('und') or 'UN')[:10].upper()

    # Matching com ItemSolicitado
    item_solicitado = None
    match_score = 0
    if not hasattr(cotacao_mae, '_itens_solicitados_cache'):
        cotacao_mae._itens_solicitados_cache = list(cotacao_mae.itens_solicitados.select_related('produto').all())

    descricao_lower = normalizar_texto(descricao)
    for item_sol in cotacao_mae._itens_solicitados_cache:
        desc_sol = normalizar_texto(item_sol.descricao_display)
        if desc_sol == descricao_lower:
            item_solicitado, match_score = item_sol, 100
            break
        if item_sol.produto and codigo and (item_sol.produto.codigo or '').lower() in codigo.lower():
            item_solicitado, match_score = item_sol, 95
            break
        if desc_sol in descricao_lower or descricao_lower in desc_sol:
            if match_score < 80:
                item_solicitado, match_score = item_sol, 80
        if match_score < 60:
            palavras_sol = {p for p in desc_sol.split() if len(p) > 2}
            palavras_desc = {p for p in descricao_lower.split() if len(p) > 2}
            comuns = palavras_sol & palavras_desc
            if len(comuns) >= 2:
                score = int(len(comuns) / max(len(palavras_sol), len(palavras_desc), 1) * 100)
                if score > match_score:
                    item_solicitado, match_score = item_sol, score

    return ItemCotacaoFornecedor(
        cotacao_fornecedor=cotacao_forn, item_solicitado=item_solicitado,
        descricao_fornecedor=descricao, codigo_fornecedor=codigo,
        quantidade=quantidade, unidade_medida=unidade,
        preco_unitario=preco_unitario, preco_total=quantidade * preco_unitario,
        disponivel=preco_unitario > 0, match_automatico=(item_solicitado is not None),
        match_score=match_score
    )


# -- Sincronização de itens --

def _sincronizar_itens_cotacao(cotacao_mae):
    """Sincroniza itens importados com itens solicitados."""
    todos_orfaos = ItemCotacaoFornecedor.objects.filter(
        cotacao_fornecedor__cotacao_mae=cotacao_mae, item_solicitado__isnull=True
    ).select_related('cotacao_fornecedor__fornecedor')

    descricoes_unicas = {}
    for item_cf in todos_orfaos:
        desc = (item_cf.descricao_fornecedor or '').strip()
        if not desc:
            continue
        desc_norm = normalizar_texto(desc)
        descricoes_unicas.setdefault(desc_norm, []).append(item_cf)

    if not descricoes_unicas:
        return

    itens_solicitados = list(cotacao_mae.itens_solicitados.select_related('produto').all())
    idx_por_desc = {normalizar_texto(item_sol.descricao_display): item_sol for item_sol in itens_solicitados}
    vinculacoes = []

    for desc_norm, itens_cf_list in descricoes_unicas.items():
        item_sol = _encontrar_item_solicitado(desc_norm, idx_por_desc, itens_solicitados)
        if item_sol:
            for icf in itens_cf_list:
                vinculacoes.append((icf.id, item_sol, 80))
        else:
            primeiro = itens_cf_list[0]
            forn_nome = primeiro.cotacao_fornecedor.fornecedor.nome_fantasia or primeiro.cotacao_fornecedor.fornecedor.nome_razao_social
            try:
                novo_item = ItemSolicitado.objects.create(
                    cotacao_mae=cotacao_mae, produto=None,
                    descricao_manual=primeiro.descricao_fornecedor[:500],
                    quantidade=primeiro.quantidade or Decimal('1'),
                    unidade_medida=primeiro.unidade_medida or 'UN',
                    observacao=f'Auto-criado da importação de {forn_nome}'
                )
                idx_por_desc[desc_norm] = novo_item
                itens_solicitados.append(novo_item)
                for icf in itens_cf_list:
                    vinculacoes.append((icf.id, novo_item, 50))
            except Exception:
                continue

    for item_cf_id, item_sol, score in vinculacoes:
        ItemCotacaoFornecedor.objects.filter(id=item_cf_id).update(
            item_solicitado=item_sol, match_automatico=True, match_score=score
        )

    if hasattr(cotacao_mae, '_itens_solicitados_cache'):
        delattr(cotacao_mae, '_itens_solicitados_cache')


def _encontrar_item_solicitado(desc_lower, idx_por_desc, itens_solicitados):
    """Tenta encontrar ItemSolicitado correspondente."""
    if desc_lower in idx_por_desc:
        return idx_por_desc[desc_lower]
    for desc_sol, item_sol in idx_por_desc.items():
        if desc_sol in desc_lower or desc_lower in desc_sol:
            return item_sol
    palavras_desc = {p for p in desc_lower.split() if len(p) > 2}
    melhor_match, melhor_score = None, 0
    for item_sol in itens_solicitados:
        desc_sol = normalizar_texto(item_sol.descricao_display)
        palavras_sol = {p for p in desc_sol.split() if len(p) > 2}
        comuns = palavras_desc & palavras_sol
        if len(comuns) >= 2:
            score = len(comuns) / max(len(palavras_desc), len(palavras_sol), 1)
            if score > melhor_score and score >= 0.3:
                melhor_score, melhor_match = score, item_sol
    return melhor_match


# -----------------------------------------------------------------------------
# 4.5 COTAÇÕES — SUGESTÕES E SELEÇÃO
# -----------------------------------------------------------------------------

@login_required
@require_POST
def cotacao_calcular_sugestoes(request, pk):
    """Calcula sugestões automáticas."""
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        try:
            peso_preco = float(request.POST.get('peso_preco', 50)) / 100
            peso_prazo = float(request.POST.get('peso_prazo', 30)) / 100
            peso_conf = float(request.POST.get('peso_confiabilidade', 20)) / 100
        except (ValueError, TypeError):
            peso_preco, peso_prazo, peso_conf = 0.5, 0.3, 0.2

        with transaction.atomic():
            ItemCotacaoFornecedor.objects.filter(
                cotacao_fornecedor__cotacao_mae=cotacao
            ).update(melhor_preco=False, melhor_prazo=False, sugerido=False)

            for item_sol in cotacao.itens_solicitados.all():
                itens_cot = ItemCotacaoFornecedor.objects.filter(
                    cotacao_fornecedor__cotacao_mae=cotacao,
                    item_solicitado=item_sol, disponivel=True
                ).select_related('cotacao_fornecedor')
                if not itens_cot.exists():
                    continue

                menor_preco = itens_cot.order_by('preco_unitario').first()
                if menor_preco:
                    menor_preco.melhor_preco = True
                    menor_preco.save()

                itens_com_prazo = [(i, i.prazo_entrega_item or i.cotacao_fornecedor.prazo_entrega_dias)
                                   for i in itens_cot if (i.prazo_entrega_item or i.cotacao_fornecedor.prazo_entrega_dias)]
                if itens_com_prazo:
                    mp = min(itens_com_prazo, key=lambda x: x[1])[0]
                    mp.melhor_prazo = True
                    mp.save()

                precos = [float(i.preco_unitario) for i in itens_cot if i.preco_unitario]
                if not precos:
                    continue
                max_p, min_p = max(precos), min(precos)
                range_p = max_p - min_p if max_p != min_p else 1
                scores = []
                for item in itens_cot:
                    prazo = item.prazo_entrega_item or item.cotacao_fornecedor.prazo_entrega_dias or 30
                    conf = item.cotacao_fornecedor.nota_confiabilidade or 5
                    sp = 1 - ((float(item.preco_unitario) - min_p) / range_p) if range_p else 1
                    st = max(0, 1 - (prazo / 60))
                    sc = conf / 10
                    scores.append((item, sp * peso_preco + st * peso_prazo + sc * peso_conf))
                if scores:
                    melhor = max(scores, key=lambda x: x[1])[0]
                    melhor.sugerido = True
                    melhor.save()

        cotacao.status = 'em_analise'
        cotacao.save(update_fields=['status'])
        return JsonResponse({'success': True, 'message': 'Sugestões calculadas!'})
    except Exception as e:
        log_erro_seguro('cotacao_calcular_sugestoes', e, request)
        return resposta_erro_segura('Erro ao calcular sugestões', 500)


@login_required
@require_POST
def cotacao_salvar_selecao(request, pk):
    """Salva itens selecionados para compra."""
    try:
        cotacao = get_object_or_404(CotacaoMae, pk=pk)
        data = json.loads(request.body)
        itens_selecionados = data.get('itens_selecionados', [])
        if not isinstance(itens_selecionados, list) or len(itens_selecionados) > 1000:
            return resposta_erro_segura('Formato inválido', 400)

        with transaction.atomic():
            ItemCotacaoFornecedor.objects.filter(cotacao_fornecedor__cotacao_mae=cotacao).update(selecionado=False)
            if itens_selecionados:
                ids_validos = ItemCotacaoFornecedor.objects.filter(
                    id__in=itens_selecionados, cotacao_fornecedor__cotacao_mae=cotacao
                ).values_list('id', flat=True)
                ItemCotacaoFornecedor.objects.filter(id__in=list(ids_validos)).update(selecionado=True)

        return JsonResponse({'success': True, 'message': 'Seleção salva!'})
    except Exception as e:
        log_erro_seguro('cotacao_salvar_selecao', e, request)
        return resposta_erro_segura('Erro ao salvar seleção', 500)


# -----------------------------------------------------------------------------
# 4.6 COTAÇÕES — GERAÇÃO DE PEDIDOS
# -----------------------------------------------------------------------------

@login_required
@require_POST
def cotacao_gerar_pedidos(request, pk):
    """Gera pedidos de compra a partir dos itens selecionados."""
    try:
        data = json.loads(request.body)
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

                cotacao_forn = CotacaoFornecedor.objects.filter(cotacao_mae=cotacao, fornecedor=fornecedor).first()
                prazo = cotacao_forn.prazo_entrega_dias if cotacao_forn else 15

                pedido = PedidoCompra.objects.create(
                    fornecedor=fornecedor, cotacao_mae=cotacao, cotacao_fornecedor=cotacao_forn,
                    data_prevista_entrega=timezone.now().date() + timedelta(days=prazo),
                    condicao_pagamento=cotacao_forn.condicao_pagamento if cotacao_forn else '',
                    forma_pagamento=cotacao_forn.forma_pagamento if cotacao_forn else '',
                    observacoes=f'Gerado da cotação {cotacao.numero}',
                    status='rascunho', solicitante=request.user,
                )

                itens_pedido = []
                for item_data in itens_data[:1000]:
                    produto_nome = item_data.get('produto_nome', '')[:255]
                    quantidade = Decimal(str(item_data.get('quantidade', 1)))
                    preco_unitario = Decimal(str(item_data.get('preco_unitario', 0)))
                    produto = Produto.objects.filter(descricao__iexact=produto_nome).first()
                    if not produto:
                        produto = Produto.objects.create(descricao=produto_nome, unidade='UN', ativo=True)
                    itens_pedido.append(ItemPedidoCompra(
                        pedido=pedido, produto=produto, descricao=produto_nome,
                        quantidade=quantidade, preco_unitario=preco_unitario,
                        preco_total=quantidade * preco_unitario
                    ))

                if itens_pedido:
                    ItemPedidoCompra.objects.bulk_create(itens_pedido)

                pedido.calcular_total()
                precisa_aprovacao, nivel = verificar_regras_aprovacao(pedido)
                if precisa_aprovacao:
                    pedido.nivel_aprovacao_necessario = nivel
                    pedido.status = 'em_aprovacao'
                else:
                    pedido.status = 'aprovado'
                    pedido.data_aprovacao = timezone.now()
                pedido.save()

                pedidos_gerados.append({
                    'id': pedido.pk, 'numero': pedido.numero,
                    'fornecedor': fornecedor.nome_fantasia or fornecedor.nome_razao_social,
                    'total_itens': len(itens_pedido), 'valor_total': float(pedido.valor_total),
                    'status': pedido.status, 'precisa_aprovacao': precisa_aprovacao
                })

            if pedidos_gerados:
                cotacao.status = 'concluida'
                cotacao.save(update_fields=['status'])

        return JsonResponse({
            'success': True, 'pedidos': pedidos_gerados,
            'message': f'{len(pedidos_gerados)} pedido(s) gerado(s)!'
        })
    except Exception as e:
        log_erro_seguro('cotacao_gerar_pedidos', e, request)
        return resposta_erro_segura('Erro ao gerar pedidos', 500)


# -----------------------------------------------------------------------------
# 4.7 PEDIDOS DE COMPRA — MANAGER
# -----------------------------------------------------------------------------

@login_required
def pedido_compra_manager(request):
    """Manager unificado de pedidos de compra."""
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    filtro_aprovacao = request.GET.get('filtro_aprovacao', '')

    pedidos = PedidoCompra.objects.select_related('fornecedor').order_by('-data_pedido')
    if search:
        pedidos = pedidos.filter(
            Q(numero__icontains=search) | Q(fornecedor__nome_razao_social__icontains=search))
    if status:
        pedidos = pedidos.filter(status=status)

    nivel_usuario = get_nivel_aprovacao_usuario(request.user)

    if filtro_aprovacao == 'minha_aprovacao':
        pedidos = pedidos.filter(
            status='em_aprovacao',
            nivel_aprovacao_atual__lt=F('nivel_aprovacao_necessario'),
            nivel_aprovacao_atual__lte=nivel_usuario
        )
    elif filtro_aprovacao == 'em_aprovacao':
        pedidos = pedidos.filter(status='em_aprovacao')
    elif filtro_aprovacao == 'aprovados':
        pedidos = pedidos.filter(status='aprovado')
    elif filtro_aprovacao == 'rejeitados':
        pedidos = pedidos.filter(status='rejeitado')

    paginator = Paginator(pedidos, 25)
    pedidos_page = paginator.get_page(request.GET.get('page'))

    minha_aprovacao = 0
    if nivel_usuario > 0:
        minha_aprovacao = PedidoCompra.objects.filter(
            status='em_aprovacao',
            nivel_aprovacao_atual__lt=F('nivel_aprovacao_necessario'),
            nivel_aprovacao_atual__lte=nivel_usuario
        ).count()

    context = {
        'pedidos': pedidos_page,
        'total_pedidos': PedidoCompra.objects.count(),
        'em_aprovacao': PedidoCompra.objects.filter(status='em_aprovacao').count(),
        'aprovados': PedidoCompra.objects.filter(status='aprovado').count(),
        'pendentes_entrega': PedidoCompra.objects.filter(status='pendente_entrega').count(),
        'recebidos': PedidoCompra.objects.filter(status='recebido').count(),
        'cancelados': PedidoCompra.objects.filter(status='cancelado').count(),
        'minha_aprovacao': minha_aprovacao, 'nivel_usuario': nivel_usuario,
        'fornecedores': Fornecedor.objects.filter(ativo=True).order_by('nome_razao_social'),
        'condicoes_pagamento': CondicaoPagamento.objects.filter(ativo=True).order_by('descricao'),
        'formas_pagamento': FormaPagamento.objects.filter(ativo=True).order_by('descricao'),
        'pedidos_abertos': PedidoCompra.objects.filter(status__in=['pendente_entrega', 'aprovado']).order_by('-data_pedido'),
        'cotacoes_concluidas': CotacaoMae.objects.filter(status='concluida').order_by('-data_solicitacao'),
        'search': search, 'status': status, 'filtro_aprovacao': filtro_aprovacao,
    }
    return render(request, 'compras/pedido_compra_manager.html', context)

@login_required
def pedido_compra_form(request, pk=None):
    """Formulário de pedido de compra (ADD/EDIT) - Padrão Manager+Form."""
    pedido = get_object_or_404(PedidoCompra, pk=pk) if pk else None

    if request.method == 'POST':
        form = PedidoCompraForm(request.POST, instance=pedido)
        if form.is_valid():
            pedido = form.save(commit=False)
            if not pk:
                pedido.solicitante = request.user
                pedido.status = 'rascunho'
            pedido.save()

            # Processar itens do JSON
            itens_json = request.POST.get('itens_json', '[]')
            try:
                itens = json.loads(itens_json)
            except json.JSONDecodeError:
                itens = []

            # Remover itens antigos se for edição
            if pk:
                pedido.itens.all().delete()

            # Criar novos itens
            for item in itens[:1000]:
                try:
                    ItemPedidoCompra.objects.create(
                        pedido=pedido,
                        produto_id=item.get('produto_id') if item.get('produto_id') else None,
                        descricao=item.get('descricao', '')[:255],
                        quantidade=Decimal(str(item.get('quantidade', 1))),
                        preco_unitario=Decimal(str(item.get('preco_unitario', 0))),
                        preco_total=Decimal(str(item.get('quantidade', 1))) * Decimal(str(item.get('preco_unitario', 0))),
                    )
                except (ValueError, KeyError, TypeError):
                    continue

            pedido.calcular_total()

            # Verificar regras de aprovação
            if not pk or pedido.status == 'rascunho':
                precisa, nivel = verificar_regras_aprovacao(pedido)
                if precisa:
                    pedido.nivel_aprovacao_necessario = nivel
                    pedido.status = 'em_aprovacao'
                    pedido.save(update_fields=['nivel_aprovacao_necessario', 'status'])

            messages.success(request, f'Pedido {pedido.numero} salvo com sucesso!')
            return redirect('ERP_ServicesBI:pedido_compra_manager')
        else:
            messages.error(request, 'Corrija os erros no formulário.')
    else:
        form = PedidoCompraForm(instance=pedido) if pedido else PedidoCompraForm()

    # Buscar itens existentes
    itens = []
    if pedido:
        itens = list(pedido.itens.select_related('produto').values(
            'id', 'produto_id', 'descricao', 'quantidade', 'preco_unitario', 'preco_total'
        ))

    context = {
        'form': form,
        'pedido': pedido,
        'itens': json.dumps(itens),
        'fornecedores': Fornecedor.objects.filter(ativo=True).order_by('nome_razao_social'),
        'produtos': Produto.objects.filter(ativo=True).order_by('descricao'),
        'condicoes_pagamento': CondicaoPagamento.objects.filter(ativo=True).order_by('descricao'),
        'formas_pagamento': FormaPagamento.objects.filter(ativo=True).order_by('descricao'),
        'cotacoes_concluidas': CotacaoMae.objects.filter(status='concluida').order_by('-data_solicitacao'),
        'titulo': 'Editar Pedido de Compra' if pedido else 'Novo Pedido de Compra',
    }
    return render(request, 'compras/pedido_compra_form.html', context)




# -----------------------------------------------------------------------------
# 4.8 PEDIDOS DE COMPRA — APIs
# -----------------------------------------------------------------------------

@login_required
@require_POST
def pedido_salvar_api(request):
    """API unificada para salvar pedido de compra."""
    try:
        data = json.loads(request.body)
        pk = data.get('id')
        pedido = get_object_or_404(PedidoCompra, pk=pk) if pk else PedidoCompra(solicitante=request.user)

        pedido.fornecedor_id = data.get('fornecedor_id')
        pedido.data_prevista_entrega = data.get('data_previsao_entrega') or None
        pedido.condicao_pagamento = data.get('condicao_pagamento', '')
        pedido.forma_pagamento = data.get('forma_pagamento', '')
        pedido.cotacao_mae_id = data.get('cotacao_id') or None
        pedido.observacoes = data.get('observacoes', '')
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

        if not pk or pedido.status == 'rascunho':
            precisa, nivel = verificar_regras_aprovacao(pedido)
            if precisa:
                pedido.nivel_aprovacao_necessario = nivel
                pedido.status = 'em_aprovacao'
                pedido.save(update_fields=['nivel_aprovacao_necessario', 'status'])

        return JsonResponse({
            'success': True, 'id': pedido.pk, 'numero': pedido.numero,
            'status': pedido.status, 'precisa_aprovacao': pedido.status == 'em_aprovacao',
            'message': 'Pedido salvo!'
        })
    except Exception as e:
        log_erro_seguro('pedido_salvar_api', e, request)
        return resposta_erro_segura(f'Erro ao salvar: {str(e)}', 400)


@login_required
@require_GET
def pedido_dados_api(request, pk):
    """API para buscar dados completos do pedido."""
    try:
        pedido = get_object_or_404(PedidoCompra, pk=pk)
        itens = []
        for item in pedido.itens.select_related('produto').all():
            unidade = item.produto.unidade if item.produto and hasattr(item.produto, 'unidade') else 'UN'
            itens.append({
                'id': item.id, 'produto': item.descricao,
                'quantidade': float(item.quantidade), 'unidade': unidade,
                'valor_unitario': float(item.preco_unitario),
                'valor_total': float(item.preco_total),
                'quantidade_recebida': float(item.quantidade_recebida),
                'divergencia': item.divergencia_encontrada,
            })
        return JsonResponse({
            'success': True, 'id': pedido.id, 'numero': pedido.numero,
            'fornecedor_id': pedido.fornecedor_id,
            'fornecedor': pedido.fornecedor.nome_razao_social,
            'data_previsao_entrega': pedido.data_prevista_entrega.isoformat() if pedido.data_prevista_entrega else None,
            'condicao_pagamento': pedido.condicao_pagamento,
            'forma_pagamento': pedido.forma_pagamento,
            'cotacao_id': pedido.cotacao_mae_id,
            'observacoes': pedido.observacoes or '',
            'status': pedido.status,
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
    try:
        pedido = get_object_or_404(PedidoCompra, pk=pk)
        return JsonResponse({
            'success': True, 'fornecedor_id': pedido.fornecedor_id,
            'condicao_pagamento': pedido.condicao_pagamento,
            'forma_pagamento': pedido.forma_pagamento,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@require_POST
def pedido_cancelar_api(request, pk):
    try:
        pedido = get_object_or_404(PedidoCompra, pk=pk)
        if pedido.status in ['recebido', 'cancelado']:
            return JsonResponse({'success': False, 'message': 'Pedido já recebido/cancelado.'}, status=400)
        motivo = request.POST.get('motivo', '')
        pedido.cancelar(request.user, motivo)
        return JsonResponse({'success': True, 'message': 'Pedido cancelado!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@require_GET
def pedido_dados_recebimento_api(request, pk):
    """API para dados de recebimento do pedido."""
    try:
        pedido = get_object_or_404(PedidoCompra.objects.select_related('fornecedor'), pk=pk)
        itens = []
        for item in pedido.itens.select_related('produto').all():
            qtd_rec = getattr(item, 'quantidade_recebida', 0) or 0
            unidade = item.produto.unidade if item.produto and hasattr(item.produto, 'unidade') else 'UN'
            itens.append({
                'id': item.id,
                'produto_nome': item.produto.descricao if item.produto else item.descricao,
                'produto': item.descricao, 'quantidade': float(item.quantidade),
                'quantidade_recebida': float(qtd_rec),
                'saldo_receber': float(item.saldo_receber()),
                'unidade': unidade, 'preco_unitario': float(item.preco_unitario),
                'divergencia': item.divergencia_encontrada,
                'tipo_divergencia': item.tipo_divergencia,
            })
        return JsonResponse({
            'success': True, 'numero': pedido.numero,
            'fornecedor': pedido.fornecedor.nome_razao_social,
            'fornecedor_id': pedido.fornecedor_id,
            'status': pedido.status,
            'valor_total': float(pedido.valor_total or 0),
            'itens': itens,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@require_POST
def pedido_receber_api(request, pk):
    """API para dar entrada no pedido (recebimento)."""
    try:
        pedido = get_object_or_404(PedidoCompra, pk=pk)
        data = json.loads(request.body)
        itens_recebidos = data.get('itens', [])
        observacao = data.get('observacao', '')

        with transaction.atomic():
            tem_divergencia = False
            for item_data in itens_recebidos:
                item = get_object_or_404(ItemPedidoCompra, pk=item_data['item_id'], pedido=pedido)
                qtd_receber = Decimal(str(item_data.get('quantidade', 0)))
                preco_recebido = Decimal(str(item_data.get('preco_recebido', 0))) if item_data.get('preco_recebido') else None

                if qtd_receber > 0:
                    item.registrar_recebimento(
                        quantidade=qtd_receber, usuario=request.user,
                        preco_recebido=preco_recebido, observacao=observacao
                    )
                    if item.divergencia_encontrada:
                        tem_divergencia = True

            # Atualizar status do pedido
            total_itens = pedido.itens.count()
            itens_completos = pedido.itens.filter(quantidade_recebida__gte=F('quantidade')).count()
            if total_itens > 0 and itens_completos == total_itens:
                pedido.status = 'recebido'
                pedido.data_recebimento = timezone.now()
            elif itens_completos > 0:
                pedido.status = 'parcial'
            pedido.usuario_recebimento = request.user
            if observacao:
                pedido.observacao_recebimento = observacao
            pedido.save()

        return JsonResponse({
            'success': True, 'message': 'Entrada realizada!',
            'novo_status': pedido.status, 'tem_divergencia': tem_divergencia,
        })
    except Exception as e:
        log_erro_seguro('pedido_receber_api', e, request)
        return resposta_erro_segura(f'Erro no recebimento: {str(e)}', 400)


@login_required
def pedido_compra_gerar_nfe(request, pk):
    pedido = get_object_or_404(PedidoCompra, pk=pk)
    if pedido.status not in ['recebido', 'parcial', 'aprovado']:
        messages.warning(request, 'Pedido não apto para gerar NF-e.')
        return redirect('ERP_ServicesBI:pedido_compra_manager')
    return redirect(f"{reverse('ERP_ServicesBI:nota_fiscal_entrada_manager')}?pedido_id={pk}")


@login_required
def pedido_compra_confirm_delete(request, pk):
    pedido = get_object_or_404(PedidoCompra, pk=pk)
    if request.method == 'POST':
        pedido.delete()
        messages.success(request, 'Pedido excluído!')
        return redirect('ERP_ServicesBI:pedido_compra_manager')
    return render(request, 'compras/pedido_compra_confirm_delete.html', {
        'objeto': pedido, 'titulo': 'Excluir Pedido',
        'nome_objeto': f'Pedido {pedido.numero}',
    })


# -----------------------------------------------------------------------------
# 4.9 APROVAÇÃO DE PEDIDOS
# -----------------------------------------------------------------------------

@login_required
def pedido_aprovacao_list(request):
    """Lista de pedidos pendentes de aprovação."""
    nivel_usuario = get_nivel_aprovacao_usuario(request.user)
    if nivel_usuario == 0:
        messages.warning(request, 'Sem permissão para aprovar pedidos.')
        return redirect('ERP_ServicesBI:pedido_compra_manager')

    pedidos = PedidoCompra.objects.filter(
        status='em_aprovacao',
        nivel_aprovacao_atual__lt=F('nivel_aprovacao_necessario'),
        nivel_aprovacao_atual__lte=nivel_usuario
    ).select_related('fornecedor', 'solicitante').order_by('-data_pedido')

    minhas_aprovacoes = PedidoAprovacao.objects.filter(
        usuario=request.user
    ).select_related('pedido').order_by('-data')[:10]

    context = {
        'pedidos': pedidos,
        'stats': {
            'total_pendentes': pedidos.count(),
            'valor_total_pendentes': pedidos.aggregate(total=Sum('valor_total'))['total'] or 0,
        },
        'nivel_usuario': nivel_usuario,
        'minhas_aprovacoes': minhas_aprovacoes,
    }
    return render(request, 'compras/pedido_aprovacao_list.html', context)


@login_required
def pedido_aprovacao_detail(request, pk):
    """Detalhes do pedido para aprovação."""
    pedido = get_object_or_404(
        PedidoCompra.objects.select_related('fornecedor', 'solicitante'), pk=pk)
    pode_aprovar, motivo = pode_aprovar_pedido_usuario(pedido, request.user)
    historico = pedido.historico_aprovacoes.select_related('usuario').all()
    itens = pedido.itens.select_related('produto').all()

    context = {
        'pedido': pedido, 'itens': itens, 'historico': historico,
        'pode_aprovar': pode_aprovar, 'motivo_nao_pode_aprovar': motivo,
        'proximo_nivel': pedido.nivel_aprovacao_atual + 1,
        'niveis_restantes': pedido.nivel_aprovacao_necessario - pedido.nivel_aprovacao_atual,
    }
    return render(request, 'compras/pedido_aprovacao_detail.html', context)


@login_required
@require_POST
def pedido_aprovacao_approve(request, pk):
    """Aprova pedido no nível atual."""
    pedido = get_object_or_404(PedidoCompra, pk=pk)
    pode, motivo = pode_aprovar_pedido_usuario(pedido, request.user)
    if not pode:
        messages.error(request, f'Não é possível aprovar: {motivo}')
        return redirect('ERP_ServicesBI:pedido_aprovacao_detail', pk=pk)

    try:
        with transaction.atomic():
            pedido.aprovar(request.user, request.POST.get('observacao', '').strip())
            messages.success(request, f'Pedido {pedido.numero} aprovado!')
            if pedido.status == 'em_aprovacao':
                return redirect('ERP_ServicesBI:pedido_aprovacao_list')
            return redirect('ERP_ServicesBI:pedido_compra_manager')
    except PermissionError as e:
        messages.error(request, str(e))
    except Exception as e:
        log_erro_seguro('pedido_aprovacao_approve', e, request)
        messages.error(request, 'Erro ao aprovar.')
    return redirect('ERP_ServicesBI:pedido_aprovacao_detail', pk=pk)


@login_required
@require_POST
def pedido_aprovacao_reject(request, pk):
    """Rejeita pedido."""
    pedido = get_object_or_404(PedidoCompra, pk=pk)
    if pedido.status != 'em_aprovacao':
        messages.error(request, 'Apenas pedidos em aprovação podem ser rejeitados.')
        return redirect('ERP_ServicesBI:pedido_aprovacao_detail', pk=pk)

    motivo = request.POST.get('motivo', '').strip()
    if not motivo:
        messages.error(request, 'Motivo da rejeição é obrigatório.')
        return redirect('ERP_ServicesBI:pedido_aprovacao_detail', pk=pk)

    try:
        with transaction.atomic():
            pedido.rejeitar(request.user, motivo)
            messages.success(request, f'Pedido {pedido.numero} rejeitado.')
            return redirect('ERP_ServicesBI:pedido_aprovacao_list')
    except Exception as e:
        log_erro_seguro('pedido_aprovacao_reject', e, request)
        messages.error(request, 'Erro ao rejeitar.')
    return redirect('ERP_ServicesBI:pedido_aprovacao_detail', pk=pk)


# -- APIs REST de Aprovação --

@login_required
@require_GET
def api_pedidos_pendentes_alcada(request):
    try:
        nivel = get_nivel_aprovacao_usuario(request.user)
        if nivel == 0:
            return JsonResponse({'success': False, 'message': 'Sem permissão'}, status=403)

        pedidos = PedidoCompra.objects.filter(
            status='em_aprovacao',
            nivel_aprovacao_atual__lt=F('nivel_aprovacao_necessario'),
            nivel_aprovacao_atual__lte=nivel
        ).select_related('fornecedor', 'solicitante')

        data = [{
            'id': p.id, 'numero': p.numero,
            'fornecedor': p.fornecedor.nome_razao_social,
            'valor_total': float(p.valor_total),
            'data_pedido': p.data_pedido.isoformat(),
            'solicitante': p.solicitante.get_full_name() if p.solicitante else 'Sistema',
            'nivel_atual': p.nivel_aprovacao_atual,
            'nivel_necessario': p.nivel_aprovacao_necessario,
        } for p in pedidos]

        return JsonResponse({'success': True, 'pedidos': data, 'nivel_usuario': nivel, 'total': len(data)})
    except Exception as e:
        return resposta_erro_segura('Erro ao buscar pedidos', 500)


@login_required
@require_POST
def api_aprovar_pedido(request, pk):
    try:
        pedido = get_object_or_404(PedidoCompra, pk=pk)
        pode, motivo = pode_aprovar_pedido_usuario(pedido, request.user)
        if not pode:
            return JsonResponse({'success': False, 'message': motivo}, status=403)

        data = json.loads(request.body) if request.body else {}
        with transaction.atomic():
            pedido.aprovar(request.user, data.get('observacao', ''))

        return JsonResponse({
            'success': True, 'message': 'Pedido aprovado!',
            'novo_status': pedido.status,
            'aprovacao_completa': pedido.status == 'aprovado'
        })
    except Exception as e:
        return resposta_erro_segura('Erro ao aprovar', 500)


@login_required
@require_POST
def api_rejeitar_pedido(request, pk):
    try:
        pedido = get_object_or_404(PedidoCompra, pk=pk)
        if pedido.status != 'em_aprovacao':
            return JsonResponse({'success': False, 'message': 'Não está em aprovação'}, status=400)

        data = json.loads(request.body) if request.body else {}
        motivo = data.get('motivo', '').strip()
        if not motivo:
            return JsonResponse({'success': False, 'message': 'Motivo obrigatório'}, status=400)

        with transaction.atomic():
            pedido.rejeitar(request.user, motivo)

        return JsonResponse({'success': True, 'message': 'Pedido rejeitado!', 'novo_status': pedido.status})
    except Exception as e:
        return resposta_erro_segura('Erro ao rejeitar', 500)


@login_required
@require_GET
def api_historico_aprovacoes(request, pk):
    try:
        pedido = get_object_or_404(PedidoCompra, pk=pk)
        data = [{
            'usuario': h.usuario.get_full_name() if h.usuario else 'Sistema',
            'acao': h.get_acao_display(), 'nivel': h.nivel,
            'data': h.data.isoformat(), 'observacao': h.observacao,
        } for h in pedido.historico_aprovacoes.select_related('usuario').all()]

        return JsonResponse({'success': True, 'historico': data, 'pedido': {
            'numero': pedido.numero, 'status': pedido.status,
            'nivel_aprovacao_atual': pedido.nivel_aprovacao_atual,
            'nivel_aprovacao_necessario': pedido.nivel_aprovacao_necessario,
        }})
    except Exception as e:
        return resposta_erro_segura('Erro ao buscar histórico', 500)


@login_required
@require_GET
def api_verificar_divergencias_3way(request, pk):
    """API para verificar divergências 3-Way Matching."""
    try:
        pedido = get_object_or_404(PedidoCompra, pk=pk)
        divergencias = []
        for item in pedido.itens.select_related('produto').all():
            div_item = {
                'item_id': item.id, 'produto': item.descricao,
                'quantidade_pedido': float(item.quantidade),
                'quantidade_recebida': float(item.quantidade_recebida),
                'preco_pedido': float(item.preco_unitario),
                'preco_recebido': float(item.preco_unitario_recebido or item.preco_unitario),
                'tem_divergencia': False, 'tipos_divergencia': []
            }
            if item.quantidade_recebida > item.quantidade:
                div_item['tem_divergencia'] = True
                div_item['tipos_divergencia'].append('quantidade_maior')
            elif 0 < item.quantidade_recebida < item.quantidade:
                div_item['tem_divergencia'] = True
                div_item['tipos_divergencia'].append('quantidade_menor')
            if item.preco_unitario_recebido and item.preco_unitario_recebido != item.preco_unitario:
                div_item['tem_divergencia'] = True
                div_item['tipos_divergencia'].append('preco_diferente')
            if item.divergencia_encontrada:
                div_item['tem_divergencia'] = True
                if item.tipo_divergencia:
                    div_item['tipos_divergencia'].append(item.tipo_divergencia)
            divergencias.append(div_item)

        return JsonResponse({'success': True, 'divergencias': divergencias})
    except Exception as e:
        return resposta_erro_segura('Erro ao verificar divergências', 500)

@login_required
@require_POST
def api_enviar_aprovacao(request, pk):
    """API para enviar pedido para aprovação."""
    try:
        pedido = get_object_or_404(PedidoCompra, pk=pk)

        # Verificar se pode ser enviado para aprovação
        if pedido.status not in ['rascunho', 'rejeitado']:
            return JsonResponse({
                'success': False, 
                'message': f'Pedido não pode ser enviado. Status atual: {pedido.get_status_display()}'
            }, status=400)

        with transaction.atomic():
            # Verificar regras de aprovação
            precisa_aprovacao, nivel_necessario = verificar_regras_aprovacao(pedido)

            if precisa_aprovacao:
                pedido.nivel_aprovacao_necessario = nivel_necessario
                pedido.nivel_aprovacao_atual = 0
                pedido.status = 'em_aprovacao'
                pedido.save(update_fields=['nivel_aprovacao_necessario', 'nivel_aprovacao_atual', 'status'])

                # Registrar no histórico
                PedidoAprovacao.objects.create(
                    pedido=pedido,
                    usuario=request.user,
                    acao='envio',
                    nivel=0,
                    observacao='Pedido enviado para aprovação'
                )

                return JsonResponse({
                    'success': True,
                    'message': f'Pedido enviado para aprovação! Necessário nível {nivel_necessario}.',
                    'precisa_aprovacao': True,
                    'nivel_necessario': nivel_necessario
                })
            else:
                # Aprovação automática
                pedido.status = 'aprovado'
                pedido.data_aprovacao = timezone.now()
                pedido.aprovado_por = request.user
                pedido.save(update_fields=['status', 'data_aprovacao', 'aprovado_por'])

                return JsonResponse({
                    'success': True,
                    'message': 'Pedido aprovado automaticamente (abaixo do limite de aprovação).',
                    'precisa_aprovacao': False
                })

    except Exception as e:
        log_erro_seguro('api_enviar_aprovacao', e, request)
        return resposta_erro_segura(f'Erro ao enviar para aprovação: {str(e)}', 500)




# -----------------------------------------------------------------------------
# 4.10 NOTAS FISCAIS DE ENTRADA
# -----------------------------------------------------------------------------

@login_required
def nota_fiscal_entrada_manager(request):
    """Manager de notas fiscais de entrada."""
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')

    notas = NotaFiscalEntrada.objects.select_related('fornecedor').order_by('-data_emissao')
    if search:
        notas = notas.filter(
            Q(numero_nf__icontains=search) | Q(fornecedor__nome_razao_social__icontains=search))
    if status:
        notas = notas.filter(status=status)

    paginator = Paginator(notas, 25)
    notas_page = paginator.get_page(request.GET.get('page'))

    hoje = timezone.now().date()
    context = {
        'notas': notas_page,
        'total_notas': NotaFiscalEntrada.objects.count(),
        'entradas_hoje': NotaFiscalEntrada.objects.filter(data_emissao=hoje).count(),
        'entradas_semana': NotaFiscalEntrada.objects.filter(
            data_emissao__gte=hoje - timedelta(days=hoje.weekday())).count(),
        'valor_mes': NotaFiscalEntrada.objects.filter(
            data_emissao__month=hoje.month, data_emissao__year=hoje.year
        ).aggregate(total=Sum('valor_total'))['total'] or 0,
        'fornecedores': Fornecedor.objects.filter(ativo=True).order_by('nome_razao_social'),
        'condicoes_pagamento': CondicaoPagamento.objects.filter(ativo=True),
        'formas_pagamento': FormaPagamento.objects.filter(ativo=True),
        'pedidos_abertos': PedidoCompra.objects.filter(
            status__in=['aprovado', 'pendente_entrega', 'parcial', 'recebido']).order_by('-data_pedido'),
        'search': search, 'status': status,
        'pedido_preselect': request.GET.get('pedido_id', ''),
    }
    return render(request, 'compras/nota_fiscal_entrada_manager.html', context)

@login_required
def nota_fiscal_entrada_form(request, pk=None):
    """Formulário de nota fiscal de entrada (ADD/EDIT) - Padrão Manager+Form."""
    nota = get_object_or_404(NotaFiscalEntrada, pk=pk) if pk else None

    if request.method == 'POST':
        form = NotaFiscalEntradaForm(request.POST, instance=nota)
        if form.is_valid():
            nota = form.save(commit=False)
            nota.save()

            # Processar itens do JSON
            itens_json = request.POST.get('itens_json', '[]')
            try:
                itens = json.loads(itens_json)
            except json.JSONDecodeError:
                itens = []

            # Remover itens antigos se for edição
            if pk:
                nota.itens.all().delete()

            # Criar novos itens
            for item in itens[:1000]:
                try:
                    ItemNotaFiscalEntrada.objects.create(
                        nota_fiscal=nota,
                        produto_id=item.get('produto_id') if item.get('produto_id') else None,
                        quantidade=Decimal(str(item.get('quantidade', 1))),
                        preco_unitario=Decimal(str(item.get('preco_unitario', 0))),
                        preco_total=Decimal(str(item.get('quantidade', 1))) * Decimal(str(item.get('preco_unitario', 0))),
                    )
                except (ValueError, KeyError, TypeError):
                    continue

            nota.calcular_total()

            messages.success(request, f'Nota Fiscal {nota.numero_nf} salva com sucesso!')
            return redirect('ERP_ServicesBI:nota_fiscal_entrada_manager')
        else:
            messages.error(request, 'Corrija os erros no formulário.')
    else:
        form = NotaFiscalEntradaForm(instance=nota) if nota else NotaFiscalEntradaForm()

    # Buscar itens existentes
    itens = []
    if nota:
        itens = list(nota.itens.select_related('produto').values(
            'id', 'produto_id', 'produto__descricao', 'quantidade', 'preco_unitario', 'preco_total'
        ))
        # Renomear produto__descricao para produto_descricao
        for item in itens:
            item['produto_descricao'] = item.pop('produto__descricao', '')

    context = {
        'form': form,
        'nota': nota,
        'itens': json.dumps(itens),
        'fornecedores': Fornecedor.objects.filter(ativo=True).order_by('nome_razao_social'),
        'produtos': Produto.objects.filter(ativo=True).order_by('descricao'),
        'pedidos_abertos': PedidoCompra.objects.filter(
            status__in=['aprovado', 'pendente_entrega', 'parcial', 'recebido']
        ).order_by('-data_pedido'),
        'titulo': 'Editar NF de Entrada' if nota else 'Nova NF de Entrada',
    }
    return render(request, 'compras/nota_fiscal_entrada_form.html', context)



@login_required
@require_POST
def nota_fiscal_salvar_api(request):
    """API para salvar nota fiscal de entrada.
    NOTA: Usa campos que existem no model atual (numero_nf, fornecedor, valor_total, etc.)
    Campos extras como serie, chave_acesso precisam ser adicionados ao model primeiro.
    """
    try:
        data = json.loads(request.body)
        pk = data.get('id')
        nota = get_object_or_404(NotaFiscalEntrada, pk=pk) if pk else NotaFiscalEntrada()

        nota.numero_nf = data.get('numero', '')
        nota.numero = data.get('numero', '')
        nota.fornecedor_id = data.get('fornecedor_id')
        nota.pedido_origem_id = data.get('pedido_id') or None
        nota.observacoes = data.get('observacoes', '')
        nota.status = data.get('status', 'pendente')

        if data.get('data_emissao'):
            nota.data_emissao = data['data_emissao']

        nota.save()

        itens_data = data.get('itens', [])
        if itens_data:
            nota.itens.all().delete()
            for item_data in itens_data:
                qtd = Decimal(str(item_data.get('quantidade', 1)))
                val_unit = Decimal(str(item_data.get('valor_unitario', 0)))
                ItemNotaFiscalEntrada.objects.create(
                    nota_fiscal=nota,
                    produto_id=item_data.get('produto_id') or None,
                    quantidade=qtd,
                    preco_unitario=val_unit,
                    preco_total=qtd * val_unit,
                )
        elif nota.pedido_origem_id:
            # Puxa itens do pedido automaticamente
            pedido = nota.pedido_origem
            if pedido:
                nota.itens.all().delete()
                for item_pedido in pedido.itens.select_related('produto').all():
                    qtd = item_pedido.quantidade_recebida if item_pedido.quantidade_recebida > 0 else item_pedido.quantidade
                    preco = item_pedido.preco_unitario_recebido or item_pedido.preco_unitario
                    ItemNotaFiscalEntrada.objects.create(
                        nota_fiscal=nota, produto=item_pedido.produto,
                        quantidade=qtd, preco_unitario=preco, preco_total=qtd * preco,
                    )

        nota.calcular_total()

        return JsonResponse({
            'success': True, 'id': nota.pk, 'numero': nota.numero_nf,
            'total_itens': nota.itens.count(), 'valor_total': float(nota.valor_total),
            'message': 'Nota fiscal salva!'
        })
    except Exception as e:
        log_erro_seguro('nota_fiscal_salvar_api', e, request)
        return resposta_erro_segura(f'Erro: {str(e)}', 400)


@login_required
@require_GET
def nota_fiscal_dados_api(request, pk):
    """API para buscar dados da nota fiscal."""
    try:
        nota = get_object_or_404(NotaFiscalEntrada, pk=pk)
        itens = [{
            'id': item.id,
            'produto': item.produto.descricao if item.produto else 'Sem produto',
            'quantidade': float(item.quantidade),
            'valor_unitario': float(item.preco_unitario),
            'valor_total': float(item.preco_total),
        } for item in nota.itens.select_related('produto').all()]

        return JsonResponse({
            'success': True, 'id': nota.id, 'numero': nota.numero_nf,
            'fornecedor_id': nota.fornecedor_id,
            'pedido_id': nota.pedido_origem_id,
            'data_emissao': nota.data_emissao.isoformat() if nota.data_emissao else None,
            'observacoes': nota.observacoes or '',
            'status': nota.status, 'itens': itens,
            'valor_total': float(nota.valor_total) if nota.valor_total else 0,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@require_POST
def nota_fiscal_excluir_api(request, pk):
    try:
        nota = get_object_or_404(NotaFiscalEntrada, pk=pk)
        if nota.status == 'confirmada':
            return JsonResponse({'success': False, 'message': 'NF confirmada. Cancele primeiro.'}, status=400)
        nota.delete()
        return JsonResponse({'success': True, 'message': 'NF excluída!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@require_POST
def nota_fiscal_confirmar_api(request, pk):
    """Confirma NF e atualiza estoque."""
    try:
        nota = get_object_or_404(NotaFiscalEntrada, pk=pk)
        if nota.status == 'confirmada':
            return JsonResponse({'success': False, 'message': 'Já confirmada'}, status=400)
        if nota.itens.count() == 0:
            return JsonResponse({'success': False, 'message': 'NF sem itens'}, status=400)

        with transaction.atomic():
            nota.status = 'confirmada'
            nota.save()
            nota.atualizar_estoque()

            if nota.pedido_origem:
                nota.pedido_origem.status = 'recebido'
                nota.pedido_origem.movimento_estoque_gerado = True
                nota.pedido_origem.nota_fiscal_vinculada = True
                nota.pedido_origem.save()

            # Gerar conta a pagar
            if nota.valor_total > 0 and not ContaPagar.objects.filter(nota_fiscal=nota).exists():
                ContaPagar.objects.create(
                    descricao=f'NF {nota.numero_nf} - {nota.fornecedor.nome_razao_social}',
                    fornecedor=nota.fornecedor, nota_fiscal=nota,
                    data_vencimento=timezone.now().date() + timedelta(days=30),
                    valor_original=nota.valor_total, status='pendente',
                )

        return JsonResponse({'success': True, 'message': 'NF confirmada! Estoque atualizado.'})
    except Exception as e:
        log_erro_seguro('nota_fiscal_confirmar_api', e, request)
        return resposta_erro_segura(f'Erro: {str(e)}', 400)


@login_required
@require_POST
def nota_fiscal_cancelar_api(request, pk):
    try:
        nota = get_object_or_404(NotaFiscalEntrada, pk=pk)
        if nota.status == 'cancelada':
            return JsonResponse({'success': False, 'message': 'Já cancelada'}, status=400)
        nota.status = 'cancelada'
        nota.save()
        return JsonResponse({'success': True, 'message': 'NF cancelada!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
def nota_fiscal_entrada_confirm_delete(request, pk):
    nota = get_object_or_404(NotaFiscalEntrada, pk=pk)
    if request.method == 'POST':
        nota.delete()
        messages.success(request, 'NF excluída!')
        return redirect('ERP_ServicesBI:nota_fiscal_entrada_manager')
    return render(request, 'compras/nota_fiscal_entrada_confirm_delete.html', {
        'objeto': nota, 'titulo': 'Excluir NF Entrada',
        'nome_objeto': f'NF {nota.numero_nf}',
    })


@login_required
@require_GET
def api_pedido_dados_para_nfe(request, pk):
    """Dados do pedido formatados para NF de Entrada."""
    try:
        pedido = get_object_or_404(PedidoCompra.objects.select_related('fornecedor'), pk=pk)
        if pedido.status not in ['aprovado', 'pendente_entrega', 'parcial', 'recebido']:
            return JsonResponse({'success': False, 'message': 'Pedido não apto para NF-e.'}, status=400)

        itens = []
        for item in pedido.itens.select_related('produto').all():
            qtd = item.quantidade_recebida if item.quantidade_recebida > 0 else item.quantidade
            preco = item.preco_unitario_recebido or item.preco_unitario
            itens.append({
                'produto_id': item.produto_id,
                'produto_nome': item.descricao or (item.produto.descricao if item.produto else ''),
                'quantidade': float(qtd), 'quantidade_pedido': float(item.quantidade),
                'unidade': item.produto.unidade if item.produto else 'UN',
                'valor_unitario': float(preco), 'valor_total': float(qtd * preco),
            })

        return JsonResponse({
            'success': True,
            'pedido': {
                'id': pedido.id, 'numero': pedido.numero,
                'fornecedor_id': pedido.fornecedor_id,
                'fornecedor_nome': pedido.fornecedor.nome_razao_social,
                'valor_total': float(pedido.valor_total),
            },
            'itens': itens,
        })
    except Exception as e:
        return resposta_erro_segura('Erro ao buscar dados', 500)


@login_required
@require_POST
def api_gerar_nfe_from_pedido(request, pk):
    """Gera NF de Entrada a partir de um pedido."""
    try:
        pedido = get_object_or_404(PedidoCompra, pk=pk)
        if pedido.status not in ['aprovado', 'pendente_entrega', 'parcial', 'recebido']:
            return JsonResponse({'success': False, 'message': 'Pedido não apto.'}, status=400)

        nf_existente = NotaFiscalEntrada.objects.filter(
            pedido_origem=pedido, status__in=['pendente', 'confirmada']).first()
        if nf_existente:
            return JsonResponse({'success': False, 'message': f'Já existe NF {nf_existente.numero_nf}.'}, status=400)

        with transaction.atomic():
            ultima_nf = NotaFiscalEntrada.objects.order_by('-id').first()
            try:
                num = int(''.join(filter(str.isdigit, ultima_nf.numero_nf))) + 1 if ultima_nf else 1
                numero_nf = str(num).zfill(6)
            except (ValueError, TypeError):
                numero_nf = f"NF-{pedido.numero}"

            nota = NotaFiscalEntrada.objects.create(
                numero_nf=numero_nf, numero=numero_nf,
                fornecedor=pedido.fornecedor, pedido_origem=pedido,
                data_emissao=timezone.now().date(), status='pendente',
                observacoes=f'Gerada do Pedido {pedido.numero}',
            )

            total_itens = 0
            for item_pedido in pedido.itens.select_related('produto').all():
                qtd = item_pedido.quantidade_recebida if item_pedido.quantidade_recebida > 0 else item_pedido.quantidade
                preco = item_pedido.preco_unitario_recebido or item_pedido.preco_unitario
                ItemNotaFiscalEntrada.objects.create(
                    nota_fiscal=nota, produto=item_pedido.produto,
                    quantidade=qtd, preco_unitario=preco, preco_total=qtd * preco,
                )
                total_itens += 1

            nota.calcular_total()

        return JsonResponse({
            'success': True,
            'message': f'NF {numero_nf} gerada com {total_itens} itens.',
            'nota_fiscal': {
                'id': nota.id, 'numero': nota.numero_nf,
                'total_itens': total_itens, 'valor_total': float(nota.valor_total),
            }
        })
    except Exception as e:
        log_erro_seguro('api_gerar_nfe_from_pedido', e, request)
        return resposta_erro_segura('Erro ao gerar NF', 500)


# -----------------------------------------------------------------------------
# 4.11 RELATÓRIOS DE COMPRAS
# -----------------------------------------------------------------------------

@login_required
def relatorio_compras(request):
    """Relatório de compras."""
    hoje = timezone.now().date()
    context = {
        'fornecedores': Fornecedor.objects.filter(ativo=True).order_by('nome_razao_social'),
        'data_inicio': request.GET.get('data_inicio', (hoje - timedelta(days=30)).isoformat()),
        'data_fim': request.GET.get('data_fim', hoje.isoformat()),
    }
    return render(request, 'compras/relatorio_compras.html', context)


@login_required
@require_GET
def relatorio_compras_dados_api(request):
    """API para dados do relatório de compras."""
    try:
        data_inicio = request.GET.get('data_inicio')
        data_fim = request.GET.get('data_fim')
        fornecedor_id = request.GET.get('fornecedor', '')

        notas = NotaFiscalEntrada.objects.filter(status='confirmada')
        if data_inicio:
            notas = notas.filter(data_entrada__gte=data_inicio)
        if data_fim:
            notas = notas.filter(data_entrada__lte=data_fim)
        if fornecedor_id:
            notas = notas.filter(fornecedor_id=fornecedor_id)

        totais = notas.aggregate(total_notas=Count('id'), total_valor=Sum('valor_total'))
        total_nfs = totais['total_notas'] or 0
        total_compras = float(totais['total_valor'] or 0)

        compras_list = []
        for nota in notas.select_related('fornecedor').order_by('-data_entrada')[:100]:
            compras_list.append({
                'id': nota.id,
                'data_entrada': nota.data_entrada.isoformat() if nota.data_entrada else None,
                'fornecedor_nome': nota.fornecedor.nome_razao_social if nota.fornecedor else 'N/A',
                'numero_nf': nota.numero_nf,
                'total_itens': nota.itens.count(),
                'valor_total': float(nota.valor_total or 0),
            })

        evolucao_mensal = []
        compras_por_mes = notas.annotate(mes_trunc=TruncMonth('data_entrada')).values('mes_trunc').annotate(
            total=Sum('valor_total'), quantidade=Count('id')).order_by('mes_trunc')
        nomes_meses = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        for item in compras_por_mes:
            if item['mes_trunc']:
                evolucao_mensal.append({
                    'mes': f"{nomes_meses[item['mes_trunc'].month]}/{item['mes_trunc'].year}",
                    'valor': float(item['total'] or 0), 'quantidade': item['quantidade'] or 0,
                })

        top_fornecedores = []
        for f in notas.values('fornecedor__nome_razao_social', 'fornecedor__nome_fantasia').annotate(
            total_compras=Sum('valor_total'), quantidade_notas=Count('id')).order_by('-total_compras')[:5]:
            top_fornecedores.append({
                'nome': f['fornecedor__nome_fantasia'] or f['fornecedor__nome_razao_social'] or 'N/A',
                'valor': float(f['total_compras'] or 0), 'quantidade': f['quantidade_notas'] or 0,
            })

        return JsonResponse({
            'success': True,
            'metricas': {
                'total_compras': total_compras, 'total_nfs': total_nfs,
                'ticket_medio': total_compras / total_nfs if total_nfs > 0 else 0,
                'fornecedores_ativos': notas.values('fornecedor').distinct().count(),
            },
            'compras': compras_list, 'evolucao_mensal': evolucao_mensal,
            'top_fornecedores': top_fornecedores,
        })
    except Exception as e:
        log_erro_seguro('relatorio_compras_dados_api', e, request)
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@require_GET
def relatorio_compras_exportar_api(request):
    """Exportar relatório de compras (CSV)."""
    try:
        notas = NotaFiscalEntrada.objects.filter(status='confirmada')
        if request.GET.get('data_inicio'):
            notas = notas.filter(data_entrada__gte=request.GET['data_inicio'])
        if request.GET.get('data_fim'):
            notas = notas.filter(data_entrada__lte=request.GET['data_fim'])

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="relatorio_compras.csv"'
        writer = csv.writer(response)
        writer.writerow(['Data Entrada', 'Número NF', 'Fornecedor', 'Valor Total'])
        for nota in notas.select_related('fornecedor'):
            writer.writerow([
                nota.data_entrada.strftime('%d/%m/%Y') if nota.data_entrada else '',
                nota.numero_nf, nota.fornecedor.nome_razao_social, float(nota.valor_total or 0),
            ])
        return response
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

# =============================================================================
# PARTE 5: MÓDULO VENDAS
# =============================================================================
# -----------------------------------------------------------------------------
# 5.1 ORÇAMENTOS
# -----------------------------------------------------------------------------

@login_required
def orcamento_manager(request):
    """Listagem de orçamentos."""
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')

    orcamentos = Orcamento.objects.select_related('cliente', 'vendedor').all().order_by('-data_orcamento')
    if search:
        orcamentos = orcamentos.filter(
            Q(numero__icontains=search) | Q(cliente__nome_razao_social__icontains=search))
    if status:
        orcamentos = orcamentos.filter(status=status)

    paginator = Paginator(orcamentos, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'total': orcamentos.count(),
        'total_pendentes': orcamentos.filter(status='pendente').count(),
        'total_aprovados': orcamentos.filter(status='aprovado').count(),
        'valor_total': orcamentos.aggregate(total=Sum('valor_total'))['total'] or 0,
        'search': search, 'status': status,
    }
    return render(request, 'vendas/orcamento_manager.html', context)


@login_required
def orcamento_form(request, pk=None):
    """Criar/editar orçamento com itens inline."""
    orcamento = get_object_or_404(Orcamento, pk=pk) if pk else None
    clientes = Cliente.objects.filter(ativo=True).order_by('nome_razao_social')
    vendedores = Vendedor.objects.filter(ativo=True).order_by('nome')
    produtos = Produto.objects.filter(ativo=True).order_by('descricao')
    condicoes_pagamento = CondicaoPagamento.objects.filter(ativo=True).order_by('descricao')

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'update_header':
            form = OrcamentoForm(request.POST, instance=orcamento)
            if form.is_valid():
                orcamento = form.save()
                messages.success(request, f'Orçamento {orcamento.numero} salvo!')
                return redirect('ERP_ServicesBI:orcamento_form_edit', pk=orcamento.pk)

        elif action == 'add_item' and orcamento:
            try:
                produto = get_object_or_404(Produto, pk=request.POST.get('produto'))
                ItemOrcamento.objects.create(
                    orcamento=orcamento, produto=produto,
                    quantidade=Decimal(request.POST.get('quantidade', '1').replace(',', '.')),
                    preco_unitario=Decimal(request.POST.get('preco_unitario', '0').replace('.', '').replace(',', '.')),
                    desconto=Decimal(request.POST.get('desconto', '0').replace('.', '').replace(',', '.'))
                )
                orcamento.calcular_total()
                messages.success(request, 'Item adicionado!')
            except (InvalidOperation, ValueError) as e:
                messages.error(request, f'Erro nos valores: {e}')
            return redirect('ERP_ServicesBI:orcamento_form_edit', pk=orcamento.pk)

        elif action == 'update_item' and orcamento:
            item = get_object_or_404(ItemOrcamento, pk=request.POST.get('item_id'), orcamento=orcamento)
            try:
                item.quantidade = Decimal(request.POST.get('quantidade', '1').replace(',', '.'))
                item.preco_unitario = Decimal(request.POST.get('preco_unitario', '0').replace('.', '').replace(',', '.'))
                item.desconto = Decimal(request.POST.get('desconto', '0').replace('.', '').replace(',', '.'))
                item.save()
                orcamento.calcular_total()
                messages.success(request, 'Item atualizado!')
            except (InvalidOperation, ValueError):
                messages.error(request, 'Erro nos valores.')
            return redirect('ERP_ServicesBI:orcamento_form_edit', pk=orcamento.pk)

        elif action == 'remove_item' and orcamento:
            get_object_or_404(ItemOrcamento, pk=request.POST.get('item_id'), orcamento=orcamento).delete()
            orcamento.calcular_total()
            messages.success(request, 'Item removido!')
            return redirect('ERP_ServicesBI:orcamento_form_edit', pk=orcamento.pk)

    form = OrcamentoForm(instance=orcamento) if orcamento else OrcamentoForm(initial={
        'data_validade': date.today() + timedelta(days=7), 'status': 'pendente'})
    itens = ItemOrcamento.objects.filter(orcamento=orcamento).select_related('produto') if orcamento else []

    context = {
        'form': form, 'orcamento': orcamento, 'clientes': clientes, 'vendedores': vendedores,
        'condicoes_pagamento': condicoes_pagamento, 'produtos': produtos,
        'status_choices': Orcamento.STATUS_CHOICES, 'itens': itens,
        'titulo': 'Editar Orçamento' if orcamento else 'Novo Orçamento',
    }
    return render(request, 'vendas/orcamento_form.html', context)


@login_required
@require_POST
def orcamento_excluir_api(request, pk):
    orcamento = get_object_or_404(Orcamento, pk=pk)
    try:
        numero = orcamento.numero
        orcamento.delete()
        return JsonResponse({'success': True, 'message': f'Orçamento {numero} excluído!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def orcamento_gerar_pedido(request, pk):
    orcamento = get_object_or_404(Orcamento, pk=pk)
    return render(request, 'vendas/gerar_pedido.html', {'orcamento': orcamento})


# -----------------------------------------------------------------------------
# 5.2 PEDIDOS DE VENDA
# -----------------------------------------------------------------------------

@login_required
def pedido_venda_manager(request):
    """Listagem de pedidos de venda."""
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')

    pedidos = PedidoVenda.objects.select_related('cliente', 'vendedor').all().order_by('-data_pedido')
    if search:
        pedidos = pedidos.filter(
            Q(numero__icontains=search) | Q(cliente__nome_razao_social__icontains=search))
    if status:
        pedidos = pedidos.filter(status=status)

    paginator = Paginator(pedidos, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'total': pedidos.count(),
        'total_pendentes': pedidos.filter(status='pendente').count(),
        'total_aprovados': pedidos.filter(status='aprovado').count(),
        'valor_total': pedidos.aggregate(total=Sum('valor_total'))['total'] or 0,
        'search': search, 'status': status,
    }
    return render(request, 'vendas/pedido_venda_manager.html', context)


@login_required
def pedido_venda_form(request, pk=None):
    """Criar/editar pedido de venda com itens inline."""
    pedido = get_object_or_404(PedidoVenda, pk=pk) if pk else None
    clientes = Cliente.objects.filter(ativo=True).order_by('nome_razao_social')
    vendedores = Vendedor.objects.filter(ativo=True).order_by('nome')
    produtos = Produto.objects.filter(ativo=True).order_by('descricao')
    condicoes_pagamento = CondicaoPagamento.objects.filter(ativo=True).order_by('descricao')

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'update_header':
            form = PedidoVendaForm(request.POST, instance=pedido)
            if form.is_valid():
                pedido = form.save()
                messages.success(request, f'Pedido {pedido.numero} salvo!')
                return redirect('ERP_ServicesBI:pedido_venda_form_edit', pk=pedido.pk)

        elif action == 'add_item' and pedido:
            try:
                produto = get_object_or_404(Produto, pk=request.POST.get('produto'))
                ItemPedidoVenda.objects.create(
                    pedido=pedido, produto=produto,
                    quantidade=Decimal(request.POST.get('quantidade', '1').replace(',', '.')),
                    preco_unitario=Decimal(request.POST.get('preco_unitario', '0').replace('.', '').replace(',', '.')),
                    desconto=Decimal(request.POST.get('desconto', '0').replace('.', '').replace(',', '.'))
                )
                pedido.calcular_total()
                messages.success(request, 'Item adicionado!')
            except (InvalidOperation, ValueError):
                messages.error(request, 'Erro nos valores.')
            return redirect('ERP_ServicesBI:pedido_venda_form_edit', pk=pedido.pk)

        elif action == 'update_item' and pedido:
            item = get_object_or_404(ItemPedidoVenda, pk=request.POST.get('item_id'), pedido=pedido)
            try:
                item.quantidade = Decimal(request.POST.get('quantidade', '1').replace(',', '.'))
                item.preco_unitario = Decimal(request.POST.get('preco_unitario', '0').replace('.', '').replace(',', '.'))
                item.desconto = Decimal(request.POST.get('desconto', '0').replace('.', '').replace(',', '.'))
                item.save()
                pedido.calcular_total()
                messages.success(request, 'Item atualizado!')
            except (InvalidOperation, ValueError):
                messages.error(request, 'Erro nos valores.')
            return redirect('ERP_ServicesBI:pedido_venda_form_edit', pk=pedido.pk)

        elif action == 'remove_item' and pedido:
            get_object_or_404(ItemPedidoVenda, pk=request.POST.get('item_id'), pedido=pedido).delete()
            pedido.calcular_total()
            messages.success(request, 'Item removido!')
            return redirect('ERP_ServicesBI:pedido_venda_form_edit', pk=pedido.pk)

    form = PedidoVendaForm(instance=pedido) if pedido else PedidoVendaForm(initial={'status': 'pendente'})
    itens = ItemPedidoVenda.objects.filter(pedido=pedido).select_related('produto') if pedido else []

    context = {
        'form': form, 'pedido': pedido, 'clientes': clientes, 'vendedores': vendedores,
        'condicoes_pagamento': condicoes_pagamento, 'produtos': produtos,
        'status_choices': PedidoVenda.STATUS_CHOICES, 'itens': itens,
        'titulo': 'Editar Pedido de Venda' if pedido else 'Novo Pedido de Venda',
    }
    return render(request, 'vendas/pedido_venda_form.html', context)


@login_required
@require_POST
def pedido_venda_excluir_api(request, pk):
    pedido = get_object_or_404(PedidoVenda, pk=pk)
    try:
        numero = pedido.numero
        pedido.delete()
        return JsonResponse({'success': True, 'message': f'Pedido {numero} excluído!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def pedido_venda_gerar_nfe(request, pk):
    pedido = get_object_or_404(PedidoVenda, pk=pk)
    return render(request, 'vendas/gerar_nfe.html', {'pedido': pedido})


# -----------------------------------------------------------------------------
# 5.3 NOTAS FISCAIS DE SAÍDA
# -----------------------------------------------------------------------------

@login_required
def nota_fiscal_saida_manager(request):
    """Listagem de NFs de saída."""
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')

    # ✅ CORRIGIDO: Usar 'pedido_venda' em vez de 'pedido_origem'
    notas = NotaFiscalSaida.objects.select_related('cliente', 'pedido_venda').all().order_by('-data_emissao')
    if search:
        notas = notas.filter(
            Q(numero_nf__icontains=search) | Q(cliente__nome_razao_social__icontains=search))
    if status:
        notas = notas.filter(status=status)

    paginator = Paginator(notas, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    hoje = timezone.now().date()
    
    context = {
        'page_obj': page_obj,
        'total': notas.count(),
        'total_emitidas': notas.filter(status='confirmada').count(),
        'total_canceladas': notas.filter(status='cancelada').count(),
        'valor_total': notas.aggregate(total=Sum('valor_total'))['total'] or 0,
        # ✅ NOVAS ESTATÍSTICAS PARA OS CARDS
        'emissoes_hoje': NotaFiscalSaida.objects.filter(data_emissao=hoje).count(),
        'saidas_semana': NotaFiscalSaida.objects.filter(
            data_emissao__gte=hoje - timedelta(days=hoje.weekday())).count(),
        'valor_mes': NotaFiscalSaida.objects.filter(
            data_emissao__month=hoje.month, data_emissao__year=hoje.year
        ).aggregate(total=Sum('valor_total'))['total'] or 0,
        'taxa_crescimento': 12,
        'taxa_emitidas': 8,
        'taxa_canceladas': 3,
        'taxa_valor': 15,
        'variacao_valor': 12,
        'search': search,
        'status': status,
    }
    return render(request, 'vendas/nota_fiscal_saida_manager.html', context)


@login_required
def nota_fiscal_saida_form(request, pk=None):
    """Criar/editar NF de saída com itens inline."""
    nota = get_object_or_404(NotaFiscalSaida, pk=pk) if pk else None
    clientes = Cliente.objects.filter(ativo=True).order_by('nome_razao_social')
    produtos = Produto.objects.filter(ativo=True).order_by('descricao')
    # ✅ CORRIGIDO: Usar 'pedido_venda' em vez de qualquer outro nome
    pedidos = PedidoVenda.objects.filter(status__in=['aprovado', 'pendente']).order_by('-data_pedido')

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'update_header':
            form = NotaFiscalSaidaForm(request.POST, instance=nota)
            if form.is_valid():
                nota = form.save()
                messages.success(request, f'NF {nota.numero_nf} salva!')
                return redirect('ERP_ServicesBI:nota_fiscal_saida_form_edit', pk=nota.pk)

        elif action == 'add_item' and nota:
            try:
                produto = get_object_or_404(Produto, pk=request.POST.get('produto'))
                ItemNotaFiscalSaida.objects.create(
                    nota_fiscal=nota, 
                    produto=produto,
                    quantidade=Decimal(request.POST.get('quantidade', '1').replace(',', '.')),
                    preco_unitario=Decimal(request.POST.get('preco_unitario', '0').replace('.', '').replace(',', '.')),
                )
                nota.calcular_total()
                messages.success(request, 'Item adicionado!')
            except (InvalidOperation, ValueError):
                messages.error(request, 'Erro nos valores.')
            return redirect('ERP_ServicesBI:nota_fiscal_saida_form_edit', pk=nota.pk)

        elif action == 'update_item' and nota:
            item = get_object_or_404(ItemNotaFiscalSaida, pk=request.POST.get('item_id'), nota_fiscal=nota)
            try:
                item.quantidade = Decimal(request.POST.get('quantidade', '1').replace(',', '.'))
                item.preco_unitario = Decimal(request.POST.get('preco_unitario', '0').replace('.', '').replace(',', '.'))
                item.save()
                nota.calcular_total()
                messages.success(request, 'Item atualizado!')
            except (InvalidOperation, ValueError):
                messages.error(request, 'Erro nos valores.')
            return redirect('ERP_ServicesBI:nota_fiscal_saida_form_edit', pk=nota.pk)

        elif action == 'remove_item' and nota:
            get_object_or_404(ItemNotaFiscalSaida, pk=request.POST.get('item_id'), nota_fiscal=nota).delete()
            nota.calcular_total()
            messages.success(request, 'Item removido!')
            return redirect('ERP_ServicesBI:nota_fiscal_saida_form_edit', pk=nota.pk)

    form = NotaFiscalSaidaForm(instance=nota) if nota else NotaFiscalSaidaForm(initial={'status': 'rascunho'})
    itens = ItemNotaFiscalSaida.objects.filter(nota_fiscal=nota).select_related('produto') if nota else []

    context = {
        'form': form,
        'nota': nota,
        'clientes': clientes,
        'produtos': produtos,
        'pedidos': pedidos,
        'status_choices': NotaFiscalSaida.STATUS_CHOICES,
        'itens': itens,
        'titulo': 'Editar NF de Saída' if nota else 'Nova NF de Saída',
    }
    return render(request, 'vendas/nota_fiscal_saida_form.html', context)


@login_required
@require_POST
def nota_fiscal_saida_excluir_api(request, pk):
    """Excluir NF de saída via API."""
    nota = get_object_or_404(NotaFiscalSaida, pk=pk)
    if nota.status == 'confirmada':
        return JsonResponse({'success': False, 'message': 'NF emitida. Cancele primeiro.'})
    try:
        numero = nota.numero_nf
        nota.delete()
        return JsonResponse({'success': True, 'message': f'NF {numero} excluída!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


# ============================================================================
# NOVAS APIs PARA OPERAÇÕES COMPLETAS
# ============================================================================

@login_required
@require_POST
def nota_fiscal_saida_salvar_api(request):
    """API para salvar nota fiscal de saída."""
    try:
        data = json.loads(request.body)
        pk = data.get('id')
        nota = get_object_or_404(NotaFiscalSaida, pk=pk) if pk else NotaFiscalSaida()

        nota.numero_nf = data.get('numero', '')
        nota.cliente_id = data.get('cliente_id')
        # ✅ NOVO: Suporte a pedido_venda
        nota.pedido_venda_id = data.get('pedido_venda_id') or None
        nota.deposito_origem_id = data.get('deposito_id') or None
        nota.status = data.get('status', 'rascunho')

        if data.get('data_emissao'):
            nota.data_emissao = data['data_emissao']
        
        # ✅ NOVO: data_saida
        if data.get('data_saida'):
            nota.data_saida = data['data_saida']

        nota.save()

        itens_data = data.get('itens', [])
        if itens_data:
            nota.itens.all().delete()
            for item_data in itens_data:
                qtd = Decimal(str(item_data.get('quantidade', 1)))
                val_unit = Decimal(str(item_data.get('valor_unitario', 0)))
                ItemNotaFiscalSaida.objects.create(
                    nota_fiscal=nota,
                    produto_id=item_data.get('produto_id') or None,
                    quantidade=qtd,
                    preco_unitario=val_unit,
                    valor_total=qtd * val_unit,
                )
        elif nota.pedido_venda_id:
            # ✅ NOVO: Puxa itens do pedido automaticamente
            pedido = nota.pedido_venda
            if pedido:
                nota.itens.all().delete()
                for item_pedido in pedido.itens.select_related('produto').all():
                    qtd = item_pedido.quantidade
                    preco = item_pedido.preco_unitario
                    ItemNotaFiscalSaida.objects.create(
                        nota_fiscal=nota,
                        produto=item_pedido.produto,
                        quantidade=qtd,
                        preco_unitario=preco,
                        valor_total=qtd * preco,
                    )

        nota.calcular_total()

        return JsonResponse({
            'success': True,
            'id': nota.pk,
            'numero': nota.numero_nf,
            'total_itens': nota.itens.count(),
            'valor_total': float(nota.valor_total),
            'message': 'Nota fiscal salva!'
        })
    except Exception as e:
        log_erro_seguro('nota_fiscal_saida_salvar_api', e, request)
        return resposta_erro_segura(f'Erro: {str(e)}', 400)


@login_required
@require_GET
def nota_fiscal_saida_dados_api(request, pk):
    """API para buscar dados da nota fiscal de saída."""
    try:
        # ✅ CORRIGIDO: select_related com 'cliente' e 'pedido_venda'
        nota = get_object_or_404(NotaFiscalSaida.objects.select_related('cliente', 'pedido_venda'), pk=pk)
        itens = [{
            'id': item.id,
            'produto': item.produto.descricao if item.produto else 'Sem produto',
            'quantidade': float(item.quantidade),
            'valor_unitario': float(item.preco_unitario),
            'valor_total': float(item.valor_total),
        } for item in nota.itens.select_related('produto').all()]

        return JsonResponse({
            'success': True,
            'id': nota.id,
            'numero': nota.numero_nf,
            'cliente_id': nota.cliente_id,
            # ✅ NOVO: pedido_venda_id
            'pedido_venda_id': nota.pedido_venda_id,
            'data_emissao': nota.data_emissao.isoformat() if nota.data_emissao else None,
            # ✅ NOVO: data_saida
            'data_saida': nota.data_saida.isoformat() if nota.data_saida else None,
            'status': nota.status,
            'itens': itens,
            'valor_total': float(nota.valor_total) if nota.valor_total else 0,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@require_POST
def nota_fiscal_saida_confirmar_api(request, pk):
    """Confirma NF de saída e atualiza estoque."""
    try:
        nota = get_object_or_404(NotaFiscalSaida, pk=pk)
        if nota.status == 'confirmada':
            return JsonResponse({'success': False, 'message': 'Já confirmada'}, status=400)
        if nota.itens.count() == 0:
            return JsonResponse({'success': False, 'message': 'NF sem itens'}, status=400)

        with transaction.atomic():
            nota.status = 'confirmada'
            # ✅ NOVO: Define data de saída
            nota.data_saida = timezone.now().date()
            nota.save()
            nota._confirmar_saida()  # Baixa estoque

            # ✅ NOVO: Atualizar pedido de venda se existir
            if nota.pedido_venda:
                nota.pedido_venda.status = 'entregue'
                nota.pedido_venda.nota_fiscal_vinculada = True
                nota.pedido_venda.save()

            # Gerar conta a receber
            if nota.valor_total > 0 and not ContaReceber.objects.filter(nota_fiscal_saida=nota).exists():
                ContaReceber.objects.create(
                    descricao=f'NF {nota.numero_nf} - {nota.cliente.nome_razao_social}',
                    cliente=nota.cliente,
                    nota_fiscal_saida=nota,
                    data_vencimento=timezone.now().date() + timedelta(days=30),
                    valor_original=nota.valor_total,
                    status='pendente',
                )

        return JsonResponse({'success': True, 'message': 'NF confirmada! Estoque atualizado.'})
    except Exception as e:
        log_erro_seguro('nota_fiscal_saida_confirmar_api', e, request)
        return resposta_erro_segura(f'Erro: {str(e)}', 400)


@login_required
@require_POST
def nota_fiscal_saida_cancelar_api(request, pk):
    """Cancelar nota fiscal de saída."""
    try:
        nota = get_object_or_404(NotaFiscalSaida, pk=pk)
        if nota.status == 'cancelada':
            return JsonResponse({'success': False, 'message': 'Já cancelada'}, status=400)
        
        with transaction.atomic():
            nota.status = 'cancelada'
            nota.save()
            nota._estornar_saida()  # Devolve estoque

            # ✅ NOVO: Restaurar pedido se estiver vinculado
            if nota.pedido_venda:
                nota.pedido_venda.status = 'aprovado'
                nota.pedido_venda.nota_fiscal_vinculada = False
                nota.pedido_venda.save()

        return JsonResponse({'success': True, 'message': 'NF cancelada! Estoque restaurado.'})
    except Exception as e:
        log_erro_seguro('nota_fiscal_saida_cancelar_api', e, request)
        return resposta_erro_segura(f'Erro: {str(e)}', 400)


@login_required
def nota_fiscal_saida_confirm_delete(request, pk):
    """Confirmação de exclusão de NF de saída."""
    nota = get_object_or_404(NotaFiscalSaida, pk=pk)
    if request.method == 'POST':
        nota.delete()
        messages.success(request, 'NF excluída!')
        return redirect('ERP_ServicesBI:nota_fiscal_saida_manager')
    return render(request, 'vendas/nota_fiscal_saida_confirm_delete.html', {
        'objeto': nota,
        'titulo': 'Excluir NF Saída',
        'nome_objeto': f'NF {nota.numero_nf}',
    })


@login_required
@require_GET
def api_pedido_dados_para_nfe_saida(request, pk):
    """Dados do pedido de venda formatados para NF de Saída."""
    try:
        # ✅ CORRIGIDO: usar PedidoVenda
        pedido = get_object_or_404(PedidoVenda.objects.select_related('cliente'), pk=pk)
        if pedido.status not in ['aprovado', 'pendente', 'parcial', 'entregue']:
            return JsonResponse({'success': False, 'message': 'Pedido não apto para NF-e.'}, status=400)

        itens = []
        for item in pedido.itens.select_related('produto').all():
            qtd = item.quantidade
            preco = item.preco_unitario
            itens.append({
                'produto_id': item.produto_id,
                'produto_nome': item.descricao or (item.produto.descricao if item.produto else ''),
                'quantidade': float(qtd),
                'unidade': item.produto.unidade if item.produto else 'UN',
                'valor_unitario': float(preco),
                'valor_total': float(qtd * preco),
            })

        return JsonResponse({
            'success': True,
            'pedido': {
                'id': pedido.id,
                'numero': pedido.numero,
                'cliente_id': pedido.cliente_id,
                'cliente_nome': pedido.cliente.nome_razao_social,
                'valor_total': float(pedido.valor_total),
            },
            'itens': itens,
        })
    except Exception as e:
        return resposta_erro_segura('Erro ao buscar dados', 500)


@login_required
@require_POST
def api_gerar_nfe_from_pedido_venda(request, pk):
    """Gera NF de Saída a partir de um pedido de venda."""
    try:
        # ✅ CORRIGIDO: usar PedidoVenda
        pedido = get_object_or_404(PedidoVenda, pk=pk)
        if pedido.status not in ['aprovado', 'pendente', 'parcial', 'entregue']:
            return JsonResponse({'success': False, 'message': 'Pedido não apto.'}, status=400)

        # ✅ CORRIGIDO: procurar por pedido_venda
        nf_existente = NotaFiscalSaida.objects.filter(
            pedido_venda=pedido, status__in=['rascunho', 'confirmada']).first()
        if nf_existente:
            return JsonResponse({'success': False, 'message': f'Já existe NF {nf_existente.numero_nf}.'}, status=400)

        with transaction.atomic():
            ultima_nf = NotaFiscalSaida.objects.order_by('-id').first()
            try:
                num = int(''.join(filter(str.isdigit, ultima_nf.numero_nf))) + 1 if ultima_nf else 1
                numero_nf = str(num).zfill(6)
            except (ValueError, TypeError):
                numero_nf = f"NF-{pedido.numero}"

            # ✅ CORRIGIDO: usar pedido_venda na criação
            nota = NotaFiscalSaida.objects.create(
                numero_nf=numero_nf,
                cliente=pedido.cliente,
                pedido_venda=pedido,  # ✅ NOVO - Vincula ao pedido
                data_emissao=timezone.now().date(),
                status='rascunho',
            )

            total_itens = 0
            for item_pedido in pedido.itens.select_related('produto').all():
                qtd = item_pedido.quantidade
                preco = item_pedido.preco_unitario
                ItemNotaFiscalSaida.objects.create(
                    nota_fiscal=nota,
                    produto=item_pedido.produto,
                    quantidade=qtd,
                    preco_unitario=preco,
                    valor_total=qtd * preco,
                )
                total_itens += 1

            nota.calcular_total()

        return JsonResponse({
            'success': True,
            'message': f'NF {numero_nf} gerada com {total_itens} itens.',
            'nota_fiscal': {
                'id': nota.id,
                'numero': nota.numero_nf,
                'total_itens': total_itens,
                'valor_total': float(nota.valor_total),
            }
        })
    except Exception as e:
        log_erro_seguro('api_gerar_nfe_from_pedido_venda', e, request)
        return resposta_erro_segura('Erro ao gerar NF', 500)

# -----------------------------------------------------------------------------
# 5.4 RELATÓRIOS DE VENDAS
# -----------------------------------------------------------------------------

@login_required
def relatorio_vendas(request):
    return render(request, 'vendas/relatorio_vendas.html', {})

# =============================================================================
# PARTE 6: MÓDULO FINANCEIRO
# =============================================================================
# Relatório, Fluxo de Caixa, Contas a Receber, Contas a Pagar,
# Categorias Financeiras, Centros de Custo
# =============================================================================

# -----------------------------------------------------------------------------
# 6.1 RELATÓRIO FINANCEIRO (Dashboard)
# -----------------------------------------------------------------------------

@login_required
def relatorio_financeiro(request):
    """Dashboard financeiro."""
    hoje = timezone.now().date()
    data_inicial = _parse_date(request.GET.get('data_inicial')) or hoje.replace(day=1)
    ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
    data_final = _parse_date(request.GET.get('data_final')) or hoje.replace(day=ultimo_dia)
    tipo_relatorio = request.GET.get('tipo_relatorio', 'geral')

    delta_dias = (data_final - data_inicial).days
    data_inicial_ant = data_inicial - timedelta(days=delta_dias + 1)
    data_final_ant = data_inicial - timedelta(days=1)

    movimentacoes = MovimentoCaixa.objects.filter(data__range=[data_inicial, data_final]).order_by('-data')
    if tipo_relatorio == 'receitas':
        movimentacoes = movimentacoes.filter(tipo='entrada')
    elif tipo_relatorio == 'despesas':
        movimentacoes = movimentacoes.filter(tipo='saida')

    entradas = movimentacoes.filter(tipo='entrada').aggregate(total=Sum('valor'))['total'] or Decimal('0')
    saidas = movimentacoes.filter(tipo='saida').aggregate(total=Sum('valor'))['total'] or Decimal('0')
    saldo = entradas - saidas

    entradas_ant = MovimentoCaixa.objects.filter(data__range=[data_inicial_ant, data_final_ant], tipo='entrada').aggregate(total=Sum('valor'))['total'] or Decimal('0')
    saidas_ant = MovimentoCaixa.objects.filter(data__range=[data_inicial_ant, data_final_ant], tipo='saida').aggregate(total=Sum('valor'))['total'] or Decimal('0')
    var_entradas = ((entradas - entradas_ant) / entradas_ant * 100) if entradas_ant > 0 else 0
    var_saidas = ((saidas - saidas_ant) / saidas_ant * 100) if saidas_ant > 0 else 0

    contas_receber_aberto = ContaReceber.objects.filter(status__in=['pendente', 'parcial']).aggregate(total=Sum('valor_saldo'))['total'] or Decimal('0')
    contas_receber_vencidas = ContaReceber.objects.filter(status__in=['pendente', 'parcial'], data_vencimento__lt=hoje).aggregate(total=Sum('valor_saldo'))['total'] or Decimal('0')
    contas_pagar_aberto = ContaPagar.objects.filter(status__in=['pendente', 'parcial']).aggregate(total=Sum('valor_saldo'))['total'] or Decimal('0')
    contas_pagar_vencidas = ContaPagar.objects.filter(status__in=['pendente', 'parcial'], data_vencimento__lt=hoje).aggregate(total=Sum('valor_saldo'))['total'] or Decimal('0')

    mov_diario = MovimentoCaixa.objects.filter(data__range=[data_inicial, data_final]).annotate(
        dia=TruncDate('data')
    ).values('dia').annotate(
        entradas=Sum('valor', filter=Q(tipo='entrada')), saidas=Sum('valor', filter=Q(tipo='saida'))
    ).order_by('dia')

    seis_meses_atras = hoje - timedelta(days=180)
    mov_mensal = MovimentoCaixa.objects.filter(data__gte=seis_meses_atras).annotate(
        mes=TruncMonth('data')
    ).values('mes').annotate(
        entradas=Sum('valor', filter=Q(tipo='entrada')), saidas=Sum('valor', filter=Q(tipo='saida'))
    ).order_by('mes')

    context = {
        'data_inicial': data_inicial.strftime('%Y-%m-%d'),
        'data_final': data_final.strftime('%Y-%m-%d'),
        'tipo_relatorio': tipo_relatorio,
        'entradas': entradas, 'saidas': saidas, 'saldo': saldo,
        'var_entradas': var_entradas, 'var_saidas': var_saidas,
        'contas_receber_aberto': contas_receber_aberto,
        'contas_receber_vencidas': contas_receber_vencidas,
        'contas_pagar_aberto': contas_pagar_aberto,
        'contas_pagar_vencidas': contas_pagar_vencidas,
        'datas_labels': [m['dia'].strftime('%d/%m') for m in mov_diario],
        'entradas_diarias': [float(m['entradas'] or 0) for m in mov_diario],
        'saidas_diarias': [float(m['saidas'] or 0) for m in mov_diario],
        'meses_labels': [m['mes'].strftime('%b/%Y') for m in mov_mensal],
        'entradas_mensais': [float(m['entradas'] or 0) for m in mov_mensal],
        'saidas_mensais': [float(m['saidas'] or 0) for m in mov_mensal],
        'movimentacoes': movimentacoes[:50],
    }
    return render(request, 'financeiro/relatorio_financeiro.html', context)


# -----------------------------------------------------------------------------
# 6.2 FLUXO DE CAIXA
# -----------------------------------------------------------------------------

@login_required
def fluxo_caixa_list(request):
    hoje = timezone.now().date()
    data_inicio = _parse_date(request.GET.get('data_inicio')) or (hoje - timedelta(days=30))
    data_fim = _parse_date(request.GET.get('data_fim')) or (hoje + timedelta(days=30))

    movimentacoes = MovimentoCaixa.objects.filter(data__range=[data_inicio, data_fim]).order_by('-data')
    contas_receber = ContaReceber.objects.filter(data_vencimento__range=[data_inicio, data_fim], status__in=['pendente', 'parcial'])
    contas_pagar = ContaPagar.objects.filter(data_vencimento__range=[data_inicio, data_fim], status__in=['pendente', 'parcial'])

    saldo_data = MovimentoCaixa.objects.filter(data__lte=hoje).values('tipo').annotate(total=Sum('valor'))
    ent = sum(m['total'] for m in saldo_data if m['tipo'] == 'entrada')
    sai = sum(m['total'] for m in saldo_data if m['tipo'] == 'saida')

    context = {
        'data_inicio': data_inicio, 'data_fim': data_fim,
        'movimentacoes': movimentacoes, 'contas_receber': contas_receber,
        'contas_pagar': contas_pagar, 'saldo_atual': ent - sai,
        'total_receber': contas_receber.aggregate(total=Sum('valor_saldo'))['total'] or 0,
        'total_pagar': contas_pagar.aggregate(total=Sum('valor_saldo'))['total'] or 0,
    }
    return render(request, 'financeiro/fluxo_caixa_manager.html', context)


@login_required
def fluxo_caixa_add(request):
    if request.method == 'POST':
        form = MovimentoCaixaForm(request.POST)
        if form.is_valid():
            mov = form.save(commit=False)
            mov.usuario = request.user
            mov.save()
            messages.success(request, 'Movimentação registrada!')
            return redirect('ERP_ServicesBI:fluxo_caixa_list')
    else:
        form = MovimentoCaixaForm()
    return render(request, 'financeiro/fluxo_caixa_form.html', {'form': form, 'titulo': 'Nova Movimentação', 'movimentacao': None})


@login_required
def fluxo_caixa_edit(request, pk):
    movimentacao = get_object_or_404(MovimentoCaixa, pk=pk)
    if request.method == 'POST':
        form = MovimentoCaixaForm(request.POST, instance=movimentacao)
        if form.is_valid():
            form.save()
            messages.success(request, 'Movimentação atualizada!')
            return redirect('ERP_ServicesBI:fluxo_caixa_list')
    else:
        form = MovimentoCaixaForm(instance=movimentacao)
    return render(request, 'financeiro/fluxo_caixa_form.html', {'form': form, 'titulo': 'Editar Movimentação', 'movimentacao': movimentacao})


@login_required
@require_POST
def fluxo_caixa_delete(request, pk):
    get_object_or_404(MovimentoCaixa, pk=pk).delete()
    messages.success(request, 'Movimentação excluída!')
    return redirect('ERP_ServicesBI:fluxo_caixa_list')


# -----------------------------------------------------------------------------
# 6.3 CONTAS A RECEBER
# -----------------------------------------------------------------------------

@login_required
def conta_receber_list(request):
    contas = ContaReceber.objects.select_related('cliente').all()
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    order_by = request.GET.get('order_by', '-data_vencimento')
    per_page = request.GET.get('per_page', '25')

    if search:
        contas = contas.filter(Q(descricao__icontains=search) | Q(cliente__nome_razao_social__icontains=search))
    if status:
        contas = contas.filter(status=status)
    if request.GET.get('vencimento_inicio'):
        contas = contas.filter(data_vencimento__gte=request.GET['vencimento_inicio'])
    if request.GET.get('vencimento_fim'):
        contas = contas.filter(data_vencimento__lte=request.GET['vencimento_fim'])

    contas = contas.order_by(order_by)
    paginator = Paginator(contas, int(per_page))
    page_obj = paginator.get_page(request.GET.get('page'))

    contas_json = {}
    for conta in page_obj.object_list:
        contas_json[conta.id] = {
            'id': conta.id, 'cliente': conta.cliente.nome_razao_social if conta.cliente else '-',
            'descricao': conta.descricao,
            'vencimento': conta.data_vencimento.strftime('%d/%m/%Y'),
            'valorOriginal': _format_currency_br(conta.valor_original),
            'valorSaldo': _format_currency_br(conta.valor_saldo or conta.valor_original),
            'valorRecebido': _format_currency_br(conta.valor_recebido or 0),
            'status': conta.status,
        }

    context = {
        'page_obj': page_obj, 'contas_json': json.dumps(contas_json),
        'status_choices': ContaReceber.STATUS_CHOICES,
        'search': search, 'status': status, 'order_by': order_by, 'per_page': per_page,
        'total': contas.count(),
    }
    return render(request, 'financeiro/conta_receber_manager.html', context)


@login_required
def conta_receber_add(request):
    if request.method == 'POST':
        form = ContaReceberForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conta a receber criada!')
            return redirect('ERP_ServicesBI:conta_receber_list')
    else:
        form = ContaReceberForm()
    return render(request, 'financeiro/conta_receber_form.html', {
        'form': form, 'conta': None,
        'categorias': CategoriaFinanceira.objects.filter(tipo='receita'),
        'centros': CentroCusto.objects.all(),
    })


@login_required
def conta_receber_edit(request, pk):
    conta = get_object_or_404(ContaReceber, pk=pk)
    if request.method == 'POST':
        form = ContaReceberForm(request.POST, instance=conta)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conta atualizada!')
            return redirect('ERP_ServicesBI:conta_receber_list')
    else:
        form = ContaReceberForm(instance=conta)
    return render(request, 'financeiro/conta_receber_form.html', {
        'form': form, 'conta': conta,
        'categorias': CategoriaFinanceira.objects.filter(tipo='receita'),
        'centros': CentroCusto.objects.all(),
    })


@login_required
@require_POST
def conta_receber_delete(request, pk):
    get_object_or_404(ContaReceber, pk=pk).delete()
    messages.success(request, 'Conta excluída!')
    return redirect('ERP_ServicesBI:conta_receber_list')


@login_required
@require_POST
def conta_receber_baixar(request, pk):
    conta = get_object_or_404(ContaReceber, pk=pk)
    valor_recebido = _decimal_from_br(request.POST.get('valor_recebido', '0'))
    conta.valor_recebido = (conta.valor_recebido or Decimal('0')) + valor_recebido
    conta.valor_saldo = conta.valor_original - conta.valor_recebido
    conta.status = 'recebido' if conta.valor_saldo <= 0 else 'parcial'
    conta.data_recebimento = _parse_date(request.POST.get('data_recebimento')) or timezone.now().date()
    conta.save()
    messages.success(request, 'Conta recebida!')
    return redirect('ERP_ServicesBI:conta_receber_list')


# -----------------------------------------------------------------------------
# 6.4 CONTAS A PAGAR
# -----------------------------------------------------------------------------

@login_required
def conta_pagar_list(request):
    contas = ContaPagar.objects.select_related('fornecedor').all()
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    order_by = request.GET.get('order_by', '-data_vencimento')
    per_page = request.GET.get('per_page', '25')

    if search:
        contas = contas.filter(Q(descricao__icontains=search) | Q(fornecedor__nome_razao_social__icontains=search))
    if status:
        contas = contas.filter(status=status)
    if request.GET.get('vencimento_inicio'):
        contas = contas.filter(data_vencimento__gte=request.GET['vencimento_inicio'])
    if request.GET.get('vencimento_fim'):
        contas = contas.filter(data_vencimento__lte=request.GET['vencimento_fim'])

    contas = contas.order_by(order_by)
    paginator = Paginator(contas, int(per_page))
    page_obj = paginator.get_page(request.GET.get('page'))

    contas_json = {}
    for conta in page_obj.object_list:
        contas_json[conta.id] = {
            'id': conta.id, 'fornecedor': conta.fornecedor.nome_razao_social if conta.fornecedor else '-',
            'descricao': conta.descricao,
            'vencimento': conta.data_vencimento.strftime('%d/%m/%Y'),
            'valorOriginal': _format_currency_br(conta.valor_original),
            'valorSaldo': _format_currency_br(conta.valor_saldo or conta.valor_original),
            'valorPago': _format_currency_br(conta.valor_pago or 0),
            'status': conta.status,
        }

    context = {
        'page_obj': page_obj, 'contas_json': json.dumps(contas_json),
        'status_choices': ContaPagar.STATUS_CHOICES,
        'search': search, 'status': status, 'order_by': order_by, 'per_page': per_page,
        'total': contas.count(),
    }
    return render(request, 'financeiro/conta_pagar_manager.html', context)


@login_required
def conta_pagar_add(request):
    if request.method == 'POST':
        form = ContaPagarForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conta a pagar criada!')
            return redirect('ERP_ServicesBI:conta_pagar_list')
    else:
        form = ContaPagarForm()
    return render(request, 'financeiro/conta_pagar_form.html', {
        'form': form, 'conta': None,
        'categorias': CategoriaFinanceira.objects.filter(tipo='despesa'),
        'centros': CentroCusto.objects.all(),
    })


@login_required
def conta_pagar_edit(request, pk):
    conta = get_object_or_404(ContaPagar, pk=pk)
    if request.method == 'POST':
        form = ContaPagarForm(request.POST, instance=conta)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conta atualizada!')
            return redirect('ERP_ServicesBI:conta_pagar_list')
    else:
        form = ContaPagarForm(instance=conta)
    return render(request, 'financeiro/conta_pagar_form.html', {
        'form': form, 'conta': conta,
        'categorias': CategoriaFinanceira.objects.filter(tipo='despesa'),
        'centros': CentroCusto.objects.all(),
    })


@login_required
@require_POST
def conta_pagar_delete(request, pk):
    get_object_or_404(ContaPagar, pk=pk).delete()
    messages.success(request, 'Conta excluída!')
    return redirect('ERP_ServicesBI:conta_pagar_list')


@login_required
@require_POST
def conta_pagar_baixar(request, pk):
    conta = get_object_or_404(ContaPagar, pk=pk)
    valor_pago = _decimal_from_br(request.POST.get('valor_pago', '0'))
    conta.valor_pago = (conta.valor_pago or Decimal('0')) + valor_pago
    conta.valor_saldo = conta.valor_original - conta.valor_pago
    conta.status = 'quitado' if conta.valor_saldo <= 0 else 'parcial'
    conta.data_pagamento = _parse_date(request.POST.get('data_baixa')) or timezone.now().date()
    conta.save()
    messages.success(request, 'Conta paga!')
    return redirect('ERP_ServicesBI:conta_pagar_list')


# -----------------------------------------------------------------------------
# 6.5 CATEGORIAS FINANCEIRAS (CRUD COMPLETO)
# -----------------------------------------------------------------------------

@login_required
def categoria_financeira_list(request):
    """Listagem de categorias financeiras."""
    categorias = CategoriaFinanceira.objects.all().order_by('codigo')
    return render(request, 'financeiro/categoria_financeira_list.html', {'categorias': categorias})


@login_required
def categoria_financeira_add(request):
    """Criar categoria financeira."""
    if request.method == 'POST':
        form = CategoriaFinanceiraForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoria criada!')
            return redirect('ERP_ServicesBI:categoria_financeira_list')
    else:
        form = CategoriaFinanceiraForm()
    return render(request, 'financeiro/categoria_financeira_form.html', {'form': form, 'categoria': None})


@login_required
def categoria_financeira_edit(request, pk):
    """Editar categoria financeira."""
    categoria = get_object_or_404(CategoriaFinanceira, pk=pk)
    if request.method == 'POST':
        form = CategoriaFinanceiraForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoria atualizada!')
            return redirect('ERP_ServicesBI:categoria_financeira_list')
    else:
        form = CategoriaFinanceiraForm(instance=categoria)
    return render(request, 'financeiro/categoria_financeira_form.html', {'form': form, 'categoria': categoria})


@login_required
@require_POST
def categoria_financeira_delete(request, pk):
    """Excluir categoria financeira."""
    categoria = get_object_or_404(CategoriaFinanceira, pk=pk)
    try:
        categoria.delete()
        messages.success(request, 'Categoria excluída!')
    except Exception as e:
        messages.error(request, f'Erro: {str(e)}')
    return redirect('ERP_ServicesBI:categoria_financeira_list')


# -----------------------------------------------------------------------------
# 6.6 CENTROS DE CUSTO
# -----------------------------------------------------------------------------

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
        messages.success(request, 'Centro de custo excluído!')
    except Exception as e:
        messages.error(request, f'Erro: {str(e)}')
    return redirect('ERP_ServicesBI:conta_pagar_list')


# -----------------------------------------------------------------------------
# 6.7 APIs AJAX — CATEGORIAS E CENTROS DE CUSTO
# -----------------------------------------------------------------------------

@login_required
@require_POST
def api_categoria_criar(request):
    try:
        data = json.loads(request.body)
        categoria = CategoriaFinanceira.objects.create(
            nome=data.get('nome'), tipo=data.get('tipo', 'despesa'), descricao=data.get('descricao', ''))
        return JsonResponse({'success': True, 'id': categoria.id, 'nome': categoria.nome})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def api_categoria_excluir(request, pk):
    try:
        get_object_or_404(CategoriaFinanceira, pk=pk).delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def api_centro_custo_criar(request):
    try:
        data = json.loads(request.body)
        centro = CentroCusto.objects.create(nome=data.get('nome'), tipo=data.get('tipo', 'outros'))
        return JsonResponse({'success': True, 'id': centro.id, 'nome': centro.nome})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def api_centro_custo_excluir(request, pk):
    try:
        get_object_or_404(CentroCusto, pk=pk).delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
# =============================================================================
# PARTE 7: MÓDULO FINANCEIRO — DRE
# =============================================================================

def _calcular_indicadores_dre(dre_dados):
    """Calcula indicadores financeiros baseados nos dados da DRE."""
    totais = dre_dados.get('totais', {})
    receita = totais.get('receita_liquida', 0) or 1
    return {
        'margem_bruta': (totais.get('lucro_bruto', 0) / receita * 100),
        'margem_operacional': (totais.get('resultado_operacional', 0) / receita * 100),
        'margem_liquida': (totais.get('lucro_liquido', 0) / receita * 100),
        'ebitda': totais.get('resultado_operacional', 0),
    }


def _get_configuracao_dre_form_class():
    """Retorna ConfiguracaoDREForm dinamicamente (evita import circular)."""
    from django import forms as django_forms

    class ConfiguracaoDREForm(django_forms.ModelForm):
        class Meta:
            model = ConfiguracaoDRE
            fields = ['regime_tributario', 'atividade_principal', 'aliquota_simples',
                       'percentual_presuncao_comercio', 'percentual_presuncao_servico',
                       'aliquota_irpj', 'aliquota_irpj_adicional', 'aliquota_csll', 'ativo']
            widgets = {f: django_forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
                       for f in ['aliquota_simples', 'percentual_presuncao_comercio',
                                 'percentual_presuncao_servico', 'aliquota_irpj',
                                 'aliquota_irpj_adicional', 'aliquota_csll']}
    return ConfiguracaoDREForm


@login_required
def configuracao_dre_list(request):
    from ERP_ServicesBI.models import Empresa
    return render(request, 'dre/configuracao_dre_list.html', {
        'configuracoes': ConfiguracaoDRE.objects.select_related('empresa').all(),
    })


@login_required
def configuracao_dre_form(request, pk=None):
    
    configuracao = get_object_or_404(ConfiguracaoDRE, pk=pk) if pk else None
    empresa_id = request.GET.get('empresa') or request.POST.get('empresa_id')
    empresa = None

    if empresa_id:
        try:
            empresa = Empresa.objects.get(pk=empresa_id)
        except Empresa.DoesNotExist:
            messages.error(request, "Empresa não encontrada.")
            return redirect('ERP_ServicesBI:configuracao_dre_list')
    elif configuracao:
        empresa = configuracao.empresa

    FormClass = _get_configuracao_dre_form_class()
    if request.method == 'POST':
        form = FormClass(request.POST, instance=configuracao)
        if form.is_valid():
            obj = form.save(commit=False)
            if empresa:
                obj.empresa = empresa
            obj.save()
            messages.success(request, "Configuração DRE salva!")
            return redirect('ERP_ServicesBI:configuracao_dre_list')
    else:
        form = FormClass(instance=configuracao)

    return render(request, 'dre/configuracao_dre_form.html', {
        'form': form, 'configuracao': configuracao, 'empresa': empresa,
        'titulo': f"Editar Config DRE - {empresa}" if configuracao else "Nova Config DRE",
    })


@login_required
def dre_list(request):
    from ERP_ServicesBI.models import Empresa
    return render(request, 'financeiro/dre_manager.html', {
        'empresas': Empresa.objects.filter(ativo=True).order_by('nome_fantasia'),
        'historico': RelatorioDRE.objects.select_related('empresa').all().order_by('-gerado_em')[:10],
    })

@login_required
def dre_add(request):
    """Adicionar nova configuração DRE."""
    return dre_edit(request, pk=None)


@login_required
def dre_edit(request, pk=None):
    
    hoje = timezone.now().date()
    empresa_id = request.GET.get('empresa') or pk
    data_inicio = _parse_date(request.GET.get('data_inicio')) or hoje.replace(day=1)
    proximo_mes = hoje.replace(day=28) + timedelta(days=4)
    data_fim = _parse_date(request.GET.get('data_fim')) or (proximo_mes - timedelta(days=proximo_mes.day))
    regime = request.GET.get('regime', 'simples')

    empresas = Empresa.objects.filter(ativo=True).order_by('nome_fantasia')
    empresa_selecionada = None
    dre_dados = None
    config = None

    if empresa_id and DREService:
        empresa_selecionada = get_object_or_404(Empresa, pk=empresa_id)
        config, _ = ConfiguracaoDRE.objects.get_or_create(empresa=empresa_selecionada, defaults={'regime_tributario': regime})
        try:
            service = DREService(empresa_selecionada, data_inicio, data_fim, config.regime_tributario)
            dre_dados = service.calcular_dre_completa()
            if 'indicadores' not in dre_dados:
                dre_dados['indicadores'] = _calcular_indicadores_dre(dre_dados)
        except Exception as e:
            messages.error(request, f'Erro ao calcular DRE: {str(e)}')

    historico = RelatorioDRE.objects.filter(empresa=empresa_selecionada).order_by('-gerado_em')[:10] if empresa_selecionada else []

    context = {
        'empresas': empresas, 'empresa_selecionada': empresa_selecionada,
        'data_inicio': data_inicio, 'data_fim': data_fim,
        'regime_selecionado': config.regime_tributario if config else regime,
        'regimes': [('simples', 'Simples Nacional'), ('presumido', 'Lucro Presumido'), ('real', 'Lucro Real')],
        'dre_dados': json.dumps(dre_dados) if dre_dados else None,
        'dre_dados_raw': dre_dados, 'config': config, 'historico': historico,
        'historico_dados': json.dumps([]),
    }
    return render(request, 'financeiro/dre_form.html', context)


@login_required
def dre_salvar(request):
    from ERP_ServicesBI.models import Empresa
    empresa_id = request.GET.get('empresa')
    data_inicio = _parse_date(request.GET.get('data_inicio'))
    data_fim = _parse_date(request.GET.get('data_fim'))
    regime = request.GET.get('regime', 'simples')

    if not all([empresa_id, data_inicio, data_fim]) or not DREService:
        messages.error(request, 'Parâmetros incompletos.')
        return redirect('ERP_ServicesBI:dre_list')

    empresa = get_object_or_404(Empresa, pk=empresa_id)
    config, _ = ConfiguracaoDRE.objects.get_or_create(empresa=empresa, defaults={'regime_tributario': regime})

    try:
        service = DREService(empresa, data_inicio, data_fim, config.regime_tributario)
        dre_dados = service.calcular_dre_completa()
        dre_dados['indicadores'] = _calcular_indicadores_dre(dre_dados)

        relatorio, _ = RelatorioDRE.objects.update_or_create(
            empresa=empresa, data_inicio=data_inicio, data_fim=data_fim,
            defaults={
                'regime_tributario': config.regime_tributario,
                'receita_bruta': dre_dados['totais'].get('receita_bruta', 0),
                'receita_liquida': dre_dados['totais'].get('receita_liquida', 0),
                'lucro_bruto': dre_dados['totais'].get('lucro_bruto', 0),
                'resultado_operacional': dre_dados['totais'].get('resultado_operacional', 0),
                'lucro_liquido': dre_dados['totais'].get('lucro_liquido', 0),
                'dados_json': dre_dados, 'status': 'finalizado', 'gerado_por': request.user,
            })
        messages.success(request, f'DRE salva! ID: {relatorio.id}')
    except Exception as e:
        messages.error(request, f'Erro: {str(e)}')

    return redirect(f'/financeiro/dre/?empresa={empresa_id}&data_inicio={data_inicio}&data_fim={data_fim}&regime={regime}')


@login_required
def dre_relatorio(request, pk):
    
    relatorio = get_object_or_404(RelatorioDRE.objects.select_related('empresa'), pk=pk)
    dre_dados = relatorio.dados_json or {}
    return render(request, 'financeiro/dre_form.html', {
        'empresas': Empresa.objects.filter(ativo=True),
        'empresa_selecionada': relatorio.empresa,
        'data_inicio': relatorio.data_inicio, 'data_fim': relatorio.data_fim,
        'regime_selecionado': relatorio.regime_tributario,
        'regimes': [('simples', 'Simples Nacional'), ('presumido', 'Lucro Presumido'), ('real', 'Lucro Real')],
        'dre_dados': json.dumps(dre_dados), 'dre_dados_raw': dre_dados,
        'historico': RelatorioDRE.objects.all().order_by('-gerado_em')[:10],
        'historico_dados': json.dumps([]), 'relatorio_salvo': relatorio,
    })


@login_required
def dre_comparativo(request):
    from ERP_ServicesBI.models import Empresa
    if not DREService:
        messages.error(request, 'DREService não disponível.')
        return redirect('ERP_ServicesBI:dre_list')

    p1_inicio = _parse_date(request.GET.get('p1_inicio'))
    p1_fim = _parse_date(request.GET.get('p1_fim'))
    p2_inicio = _parse_date(request.GET.get('p2_inicio'))
    p2_fim = _parse_date(request.GET.get('p2_fim'))
    empresa_id = request.GET.get('empresa')

    if not all([empresa_id, p1_inicio, p1_fim, p2_inicio, p2_fim]):
        messages.error(request, 'Selecione os dois períodos.')
        return redirect('ERP_ServicesBI:dre_list')

    empresa = get_object_or_404(Empresa, pk=empresa_id)
    config = ConfiguracaoDRE.objects.filter(empresa=empresa, ativo=True).first()
    regime = config.regime_tributario if config else 'simples'

    try:
        dre1 = DREService(empresa, p1_inicio, p1_fim, regime).calcular_dre_completa()
        dre2 = DREService(empresa, p2_inicio, p2_fim, regime).calcular_dre_completa()
        return render(request, 'financeiro/dre_form.html', {
            'empresas': Empresa.objects.filter(ativo=True),
            'empresa_selecionada': empresa,
            'dre_dados': json.dumps(dre1), 'dre_dados_raw': dre1,
            'dre_comparativo': json.dumps(dre2), 'modo_comparativo': True,
            'regimes': [('simples', 'Simples Nacional'), ('presumido', 'Lucro Presumido'), ('real', 'Lucro Real')],
            'historico': [], 'historico_dados': json.dumps([]),
        })
    except Exception as e:
        messages.error(request, f'Erro: {str(e)}')
        return redirect('ERP_ServicesBI:dre_list')


# =============================================================================
# PARTE 8: MÓDULO FINANCEIRO — PLANEJADO X REALIZADO
# =============================================================================

@login_required
def planejado_x_realizado_manager(request):
    """View principal do Planejado x Realizado."""
    ano = int(request.GET.get('ano', datetime.now().year))
    projeto_id = request.GET.get('projeto')

    query = OrcamentoProjeto.objects.filter(ano=ano)
    if projeto_id:
        query = query.filter(projeto_id=projeto_id)

    projetos_data = []
    projetos_ids = query.values_list('projeto_id', flat=True).distinct()

    for projeto in Projeto.objects.filter(id__in=projetos_ids):
        orcamentos_proj = query.filter(projeto=projeto)
        meses = []
        for mes_num in range(1, 13):
            orc = orcamentos_proj.filter(mes=mes_num).first()
            meses.append({
                'planejado': orc.valor_planejado if orc else 0,
                'realizado': orc.valor_realizado if orc else 0,
            })

        totais_proj = orcamentos_proj.aggregate(
            rec_plan=Sum('receitas_orcadas'), rec_real=Sum('realizado_receitas'),
            desp_plan=Sum('despesas_orcadas'), desp_real=Sum('realizado_despesas'))
        total_plan = (totais_proj['rec_plan'] or 0) - (totais_proj['desp_plan'] or 0)
        total_real = (totais_proj['rec_real'] or 0) - (totais_proj['desp_real'] or 0)
        variacao = total_real - total_plan

        projetos_data.append({
            'projeto': projeto, 'meses': meses,
            'total_planejado': total_plan, 'total_realizado': total_real,
            'variacao': variacao,
            'variacao_percentual': (variacao / total_plan * 100) if total_plan else 0,
        })

    # Totais gerais
    totais = query.aggregate(
        rec_plan=Sum('receitas_orcadas'), rec_real=Sum('realizado_receitas'),
        desp_plan=Sum('despesas_orcadas'), desp_real=Sum('realizado_despesas'))
    total_planejado = (totais['rec_plan'] or 0) - (totais['desp_plan'] or 0)
    total_realizado = (totais['rec_real'] or 0) - (totais['desp_real'] or 0)

    context = {
        'ano_selecionado': ano, 'ano': ano,
        'anos': [str(a) for a in range(datetime.now().year - 4, datetime.now().year + 3)],
        'projetos_lista': Projeto.objects.filter(status='ativo'),
        'projeto_selecionado': int(projeto_id) if projeto_id else None,
        'dados_projetos': projetos_data,
        'total_geral_planejado': total_planejado,
        'total_geral_realizado': total_realizado,
        'variacao_geral': total_realizado - total_planejado,
        'percentual_geral': ((total_realizado - total_planejado) / total_planejado * 100) if total_planejado else 0,
        'total_projetos': len(projetos_data),
        'meses_nomes': ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'],
    }
    return render(request, 'financeiro/planejado_x_realizado_manager.html', context)


# Alias de compatibilidade
@login_required

def planejado_x_realizado_list(request):
    return redirect('ERP_ServicesBI:planejado_x_realizado_manager')


@login_required
def planejado_x_realizado_add(request):
    if request.method == 'POST':
        form = OrcamentoProjetoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Orçamento criado!')
            return redirect('ERP_ServicesBI:planejado_x_realizado_manager')
    else:
        form = OrcamentoProjetoForm(initial={'ano': datetime.now().year})
    return render(request, 'financeiro/planejado_x_realizado_form.html', {
        'form': form, 'orcamento': None, 'projetos': Projeto.objects.filter(status='ativo'),
    })


@login_required
def planejado_x_realizado_edit(request, pk):
    orcamento = get_object_or_404(OrcamentoProjeto, pk=pk)
    if request.method == 'POST':
        form = OrcamentoProjetoForm(request.POST, instance=orcamento)
        if form.is_valid():
            form.save()
            messages.success(request, 'Orçamento atualizado!')
            return redirect('ERP_ServicesBI:planejado_x_realizado_manager')
    else:
        form = OrcamentoProjetoForm(instance=orcamento)
    return render(request, 'financeiro/planejado_x_realizado_form.html', {
        'form': form, 'orcamento': orcamento, 'projetos': Projeto.objects.filter(status='ativo'),
    })


@login_required
def planejado_x_realizado_excel(request):
    """Exportar para Excel."""
    
    from openpyxl.styles import Font, PatternFill

    ano = int(request.GET.get('ano', datetime.now().year))
    query = OrcamentoProjeto.objects.filter(ano=ano).select_related('projeto').order_by('projeto__nome', 'mes')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Planejado x Realizado"
    headers = ['Projeto', 'Mês', 'Receitas Orçadas', 'Despesas Orçadas', 'Planejado',
               'Receitas Realizadas', 'Despesas Realizadas', 'Realizado', 'Variação']
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")

    for orc in query:
        ws.append([str(orc.projeto), orc.mes,
                   float(orc.receitas_orcadas), float(orc.despesas_orcadas), float(orc.valor_planejado),
                   float(orc.realizado_receitas), float(orc.realizado_despesas),
                   float(orc.valor_realizado), float(orc.variacao)])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="planejado_x_realizado_{ano}.xlsx"'
    wb.save(response)
    return response


# APIs de Projeto
@login_required
@csrf_exempt
def api_criar_projeto(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método não permitido'})
    try:
        data = json.loads(request.body)
        nome = data.get('nome', '').strip()
        if not nome:
            return JsonResponse({'success': False, 'error': 'Nome obrigatório'})
        projeto = Projeto.objects.create(nome=nome, codigo=data.get('codigo', '').strip() or None)
        return JsonResponse({'success': True, 'projeto': {'id': projeto.id, 'nome': projeto.nome, 'codigo': projeto.codigo}})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@csrf_exempt
def projeto_create_ajax(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método não permitido'})
    try:
        nome = request.POST.get('nome', '').strip()
        if not nome:
            return JsonResponse({'success': False, 'message': 'Nome obrigatório'})
        projeto = Projeto.objects.create(nome=nome, codigo=request.POST.get('codigo', '').strip() or None)
        return JsonResponse({'success': True, 'id': projeto.id, 'nome': projeto.nome, 'codigo': projeto.codigo})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@csrf_exempt
def projeto_delete_ajax(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método não permitido'})
    try:
        Projeto.objects.get(pk=pk).delete()
        return JsonResponse({'success': True})
    except Projeto.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Projeto não encontrado'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


# =============================================================================
# PARTE 9: MÓDULO FINANCEIRO — CONCILIAÇÃO BANCÁRIA
# =============================================================================

@login_required
def conciliacao_bancaria_list(request):
    extratos = ExtratoBancario.objects.all().order_by('-data_arquivo')
    status = request.GET.get('status')
    if status:
        extratos = extratos.filter(status=status)

    paginator = Paginator(extratos, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'total_extratos': extratos.count(),
        'conciliados': extratos.filter(status='conciliado').count(),
        'pendentes': extratos.filter(status='pendente').count(),
        'divergentes': extratos.filter(status='divergente').count(),
        'contas_bancarias': ContaBancaria.objects.filter(ativa=True),
    }
    return render(request, 'financeiro/conciliacao_bancaria_manager.html', context)


@login_required
def conciliacao_bancaria_add(request):
    if request.method == 'POST':
        form = ExtratoBancarioForm(request.POST, request.FILES)
        if form.is_valid():
            extrato = form.save(commit=False)
            extrato.save()
            messages.success(request, 'Extrato importado!')
            return redirect('ERP_ServicesBI:conciliacao_bancaria_edit', pk=extrato.pk)
    else:
        form = ExtratoBancarioForm()
    return render(request, 'financeiro/conciliacao_bancaria_form.html', {'form': form, 'extrato': None})


@login_required
def conciliacao_bancaria_edit(request, pk):
    extrato = get_object_or_404(ExtratoBancario, pk=pk)
    if request.method == 'POST':
        form = ExtratoBancarioForm(request.POST, request.FILES, instance=extrato)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conciliação atualizada!')
    else:
        form = ExtratoBancarioForm(instance=extrato)

    lancamentos = LancamentoExtrato.objects.filter(extrato=extrato).order_by('data')
    return render(request, 'financeiro/conciliacao_bancaria_form.html', {
        'form': form, 'extrato': extrato, 'object': extrato, 'extratos': lancamentos,
    })


@login_required
def conciliacao_bancaria_detail(request, pk):
    extrato = get_object_or_404(ExtratoBancario, pk=pk)
    return render(request, 'financeiro/conciliacao_bancaria_detail.html', {
        'extrato': extrato, 'extratos': extrato.lancamentos.order_by('data'),
    })


@login_required
def conciliacao_bancaria_delete(request, pk):
    extrato = get_object_or_404(ExtratoBancario, pk=pk)
    if request.method == 'POST':
        extrato.delete()
        messages.success(request, 'Conciliação excluída!')
    return redirect('ERP_ServicesBI:conciliacao_bancaria_list')


@login_required
def conciliacao_bancaria_processar(request, pk):
    extrato = get_object_or_404(ExtratoBancario, pk=pk)
    if extrato.arquivo:
        extrato.status = 'processando'
        extrato.save()
        messages.success(request, 'Extrato sendo reprocessado!')
    else:
        messages.error(request, 'Nenhum arquivo para processar.')
    return redirect('ERP_ServicesBI:conciliacao_bancaria_list')


@login_required
def conciliacao_bancaria_vincular(request, pk):
    return redirect('ERP_ServicesBI:conciliacao_bancaria_edit', pk=pk)


@login_required
@require_POST
def conciliacao_importar_ofx(request):
    form = ExtratoBancarioForm(request.POST, request.FILES)
    if form.is_valid() and request.FILES.get('arquivo'):
        extrato = form.save()
        return JsonResponse({'success': True, 'extrato_id': extrato.id, 'message': 'Importado!'})
    return JsonResponse({'success': False, 'message': 'Arquivo inválido.'})


@login_required
@require_GET
def conciliacao_buscar_lancamentos(request):
    valor = request.GET.get('valor')
    if not valor:
        return JsonResponse({'lancamentos': []})
    try:
        valor_decimal = Decimal(valor)
    except (InvalidOperation, ValueError):
        return JsonResponse({'lancamentos': []})
    lancamentos = MovimentoCaixa.objects.filter(valor=valor_decimal)[:10]
    return JsonResponse({'lancamentos': [{'id': l.id, 'data': l.data.strftime('%d/%m/%Y'),
                                           'descricao': l.descricao, 'valor': str(l.valor)} for l in lancamentos]})


@login_required
@require_POST
def conciliacao_realizar(request):
    try:
        lanc = LancamentoExtrato.objects.get(id=request.POST.get('extrato_id'))
        lanc.conciliado = True
        lanc.status = 'conciliado'
        lanc.save()
        return JsonResponse({'success': True, 'message': 'Conciliação realizada!'})
    except LancamentoExtrato.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Lançamento não encontrado.'})


@login_required
@require_POST
def conciliacao_auto(request):
    return JsonResponse({'success': True, 'conciliados': 0, 'message': 'Auto-conciliação executada.'})


# =============================================================================
# PARTE 10: MÓDULO ESTOQUE (CORRIGIDO - Removidas duplicidades e vulnerabilidades)
# =============================================================================

# -----------------------------------------------------------------------------
# 10.1 MOVIMENTAÇÕES DE ESTOQUE (Manager+Form Pattern)
# -----------------------------------------------------------------------------

@login_required
def movimentacao_estoque_list(request):
    """Lista de movimentações de estoque com resumos e alertas"""
    from django.db.models import Sum, Q
    from datetime import date

    # Filtros
    search = request.GET.get('search', '')
    per_page = int(request.GET.get('per_page', 25))

    # Query base
    movimentacoes = MovimentacaoEstoque.objects.select_related(
        'produto', 'nota_fiscal_entrada', 'nota_fiscal_saida', 'deposito_origem', 'deposito_destino'
    ).all()

    if search:
        movimentacoes = movimentacoes.filter(
            Q(produto__descricao__icontains=search) |
            Q(nota_fiscal_entrada__numero_nf__icontains=search) |
            Q(nota_fiscal_saida__numero_nf__icontains=search) |
            Q(motivo__icontains=search)
        )

    # RESUMOS DOS CARDS
    hoje = date.today()

    # Total de movimentações
    total_movimentacoes = movimentacoes.count()
    movimentacoes_hoje = movimentacoes.filter(data__date=hoje).count()

    # Entradas
    entradas = movimentacoes.filter(tipo='entrada')
    total_entradas = entradas.count()
    quantidade_entradas = entradas.aggregate(total=Sum('quantidade'))['total'] or 0

    # Saídas
    saidas = movimentacoes.filter(tipo='saida')
    total_saidas = saidas.count()
    quantidade_saidas = saidas.aggregate(total=Sum('quantidade'))['total'] or 0

    # Saldo do período (entradas - saídas)
    saldo_periodo = (quantidade_entradas or 0) - (quantidade_saidas or 0)

    # ALERTAS DE ESTOQUE
    produtos_estoque_critico = Produto.objects.filter(
        estoque_minimo__gt=0,
        estoque_atual__lte=0,
        ativo=True
    ).order_by('descricao')[:10]

    produtos_estoque_alerta = Produto.objects.filter(
        estoque_minimo__gt=0,
        estoque_atual__gt=0,
        estoque_atual__lt=models.F('estoque_minimo'),
        ativo=True
    ).order_by('descricao')[:10]

    # Paginação
    paginator = Paginator(movimentacoes.order_by('-data'), per_page)
    page = request.GET.get('page')
    movimentacoes_page = paginator.get_page(page)

    context = {
        'movimentacoes': movimentacoes_page,
        'search': search,
        'per_page': per_page,
        # Cards de resumo
        'total_movimentacoes': total_movimentacoes,
        'movimentacoes_hoje': movimentacoes_hoje,
        'total_entradas': total_entradas,
        'quantidade_entradas': quantidade_entradas,
        'total_saidas': total_saidas,
        'quantidade_saidas': quantidade_saidas,
        'saldo_periodo': saldo_periodo,
        # Alertas de estoque
        'produtos_estoque_critico': produtos_estoque_critico,
        'produtos_estoque_alerta': produtos_estoque_alerta,
    }
    return render(request, 'estoque/movimentacao_estoque_manager.html', context)


@login_required
def movimentacao_estoque_add(request):
    """Criar nova movimentação de estoque"""
    
    from decimal import Decimal
    
    if request.method == 'POST':
        form = MovimentacaoEstoqueForm(request.POST)
        if form.is_valid():
            movimentacao = form.save(commit=False)
            movimentacao.usuario = request.user
            
            # Atualizar estoque do produto
            produto = movimentacao.produto
            if movimentacao.tipo == 'entrada':
                produto.estoque_atual += movimentacao.quantidade
            elif movimentacao.tipo == 'saida':
                produto.estoque_atual -= movimentacao.quantidade
            
            produto.save()
            movimentacao.save()
            
            messages.success(request, 'Movimentação registrada com sucesso!')
            return redirect('ERP_ServicesBI:movimentacao_estoque_list')
    else:
        form = MovimentacaoEstoqueForm()
    
    context = {
        'form': form,
        'produtos': Produto.objects.filter(ativo=True).order_by('descricao'),
        'depositos': Deposito.objects.filter(ativo=True).order_by('nome'),
        'notas_fiscais': NotaFiscalEntrada.objects.filter(status='confirmada').order_by('-data_entrada'),
        'hoje': timezone.now().strftime('%Y-%m-%dT%H:%M'),
    }
    return render(request, 'estoque/movimentacao_estoque_form.html', context)


@login_required

def movimentacao_estoque_edit(request, pk):
    """View para editar movimentação de estoque."""
    movimentacao = get_object_or_404(MovimentacaoEstoque, pk=pk)
    
    if request.method == 'POST':
        form = MovimentacaoEstoqueForm(request.POST, instance=movimentacao)
        if form.is_valid():
            form.save()
            messages.success(request, 'Movimentação atualizada com sucesso!')
            return redirect('ERP_ServicesBI:movimentacao_estoque_list')
        else:
            messages.error(request, 'Corrija os erros abaixo.')
    else:
        form = MovimentacaoEstoqueForm(instance=movimentacao)
    
    context = {
        'form': form,
        'movimentacao': movimentacao,
        'produtos': Produto.objects.filter(ativo=True),
        'depositos': Deposito.objects.filter(ativo=True),
        'today': timezone.now().date(),
    }
    return render(request, 'estoque/movimentacao_estoque_form.html', context)


@login_required
def movimentacao_estoque_delete(request, pk):
    """Modal de confirmação de exclusão."""
    movimentacao = get_object_or_404(MovimentacaoEstoque, pk=pk)
    
    if request.method == 'POST':
        # Reverter estoque antes de excluir
        movimentacao.reverter_estoque()
        movimentacao.delete()
        
        if request.headers.get('HX-Request'):
            return HttpResponse(
                '<script>document.body.dispatchEvent(new Event("movimentacaoUpdated"));'
                'document.querySelector(".modal.show").querySelector(".btn-close").click();</script>'
            )
        
        messages.success(request, 'Movimentação excluída!')
        return redirect('ERP_ServicesBI:movimentacao_estoque_list')
    
    return render(request, 'estoque/movimentacao_confirm_delete.html', {'movimentacao': movimentacao})


@login_required
def movimentacao_estoque_detail(request, pk):
    """Visualizar detalhes de uma movimentação."""
    movimentacao = get_object_or_404(MovimentacaoEstoque, pk=pk)
    return render(request, 'estoque/movimentacao_estoque_detail.html', {
        'movimentacao': movimentacao
    })


# -----------------------------------------------------------------------------
# 10.2 DEPÓSITOS (Manter padrão existente - não é Manager+Form)
# -----------------------------------------------------------------------------

@login_required
def deposito_list(request):
    depositos = Deposito.objects.all().order_by('nome')
    paginator = Paginator(depositos, 25)
    return render(request, 'estoque/deposito_list.html', {
        'page_obj': paginator.get_page(request.GET.get('page')), 
        'total': paginator.count
    })


@login_required
def deposito_add(request):
    if request.method == 'POST':
        form = DepositoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Depósito criado!')
            return redirect('ERP_ServicesBI:deposito_list')
    else:
        form = DepositoForm()
    return render(request, 'estoque/deposito_form.html', {'form': form, 'titulo': 'Novo Depósito'})


@login_required
def deposito_edit(request, pk):
    deposito = get_object_or_404(Deposito, pk=pk)
    if request.method == 'POST':
        form = DepositoForm(request.POST, instance=deposito)
        if form.is_valid():
            form.save()
            messages.success(request, 'Depósito atualizado!')
            return redirect('ERP_ServicesBI:deposito_list')
    else:
        form = DepositoForm(instance=deposito)
    return render(request, 'estoque/deposito_form.html', {'form': form, 'titulo': 'Editar Depósito', 'deposito': deposito})


@login_required
def deposito_delete(request, pk):
    deposito = get_object_or_404(Deposito, pk=pk)
    if request.method == 'POST':
        deposito.delete()
        messages.success(request, 'Depósito excluído!')
        return redirect('ERP_ServicesBI:deposito_list')
    return render(request, 'estoque/deposito_confirm_delete.html', {'objeto': deposito})


@login_required
@require_POST
def deposito_create_ajax(request):
    """
    Cria um novo depósito via AJAX para o modal do formulário de movimentação.
    ÚNICA função AJAX para criar depósito (consolidada).
    """
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'message': 'Requisição inválida'}, status=400)
    
    nome = request.POST.get('nome', '').strip()
    descricao = request.POST.get('descricao', '').strip()
    
    if not nome:
        return JsonResponse({'success': False, 'message': 'Nome do depósito é obrigatório'})
    
    # Verificar duplicidade
    if Deposito.objects.filter(nome__iexact=nome).exists():
        return JsonResponse({'success': False, 'message': 'Já existe um depósito com este nome'})
    
    try:
        deposito = Deposito.objects.create(
            nome=nome,
            descricao=descricao,
            ativo=True
        )
        return JsonResponse({
            'success': True,
            'id': deposito.id,
            'nome': deposito.nome,
            'message': 'Depósito criado com sucesso!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao criar depósito: {str(e)}'})


@login_required
@require_POST
def deposito_delete_ajax(request, pk):
    """
    Exclui um depósito via AJAX.
    ÚNICA função AJAX para excluir depósito (consolidada).
    """
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'message': 'Requisição inválida'}, status=400)
    
    try:
        deposito = Deposito.objects.get(pk=pk)
        nome = deposito.nome
        
        # Verificar se há movimentações vinculadas
        if MovimentacaoEstoque.objects.filter(
            Q(deposito_origem=deposito) | 
            Q(deposito_destino=deposito)
        ).exists():
            return JsonResponse({
                'success': False, 
                'message': 'Não é possível excluir: existem movimentações vinculadas a este depósito'
            })
        
        deposito.delete()
        return JsonResponse({
            'success': True,
            'message': f'Depósito "{nome}" excluído com sucesso!'
        })
    except Deposito.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Depósito não encontrado'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao excluir: {str(e)}'})

@login_required
def produtos_estoque_baixo(request):
    """Lista produtos com estoque abaixo do mínimo"""
    produtos_alerta = Produto.objects.filter(
        estoque_minimo__gt=0,
        estoque_atual__lt=models.F('estoque_minimo'),
        ativo=True
    ).order_by('descricao')
    
    produtos_critico = produtos_alerta.filter(estoque_atual__lte=0)
    produtos_alerta = produtos_alerta.filter(estoque_atual__gt=0)
    
    context = {
        'produtos_critico': produtos_critico,
        'produtos_alerta': produtos_alerta,
        'total_alerta': produtos_critico.count() + produtos_alerta.count(),
    }
    return render(request, 'estoque_baixo.html', context)


# -----------------------------------------------------------------------------
# 10.3 INVENTÁRIO (Manager+Form Pattern) - CORRIGIDO
# -----------------------------------------------------------------------------

@login_required
def inventario_list(request):
    """Listagem de inventários - Manager Pattern com Contagem integrada."""
    from django.utils import timezone
    from django.shortcuts import get_object_or_404

    # Verificar se está em modo contagem
    contagem_id = request.GET.get('contagem')

    if contagem_id:
        # MODO CONTAGEM - Mostrar tela de contagem do inventário
        inventario = get_object_or_404(Inventario, pk=contagem_id)
        itens = ItemInventario.objects.filter(inventario=inventario).select_related('produto')

        # Se for POST, salvar contagem
        if request.method == 'POST':
            item_id = request.POST.get('item_id')
            quantidade_contada = request.POST.get('quantidade_contada')

            if item_id and quantidade_contada:
                
                item = get_object_or_404(ItemInventario, pk=item_id)
                item.quantidade_contada = Decimal(quantidade_contada)
                item.save()

                # Retornar JSON para AJAX
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    from django.http import JsonResponse
                    return JsonResponse({'success': True, 'message': 'Contagem salva!'})

                messages.success(request, 'Contagem registrada!')
                return redirect('ERP_ServicesBI:inventario_list') + f'?contagem={contagem_id}'

        context = {
            'modo_contagem': True,
            'inventario': inventario,
            'itens': itens,
            'itens_contados': itens.exclude(quantidade_contada=0).count(),
            'itens_pendentes': itens.filter(quantidade_contada=0).count(),
            'depositos': Deposito.objects.filter(ativo=True),
        }

        return render(request, 'estoque/inventario_manager.html', context)

    # MODO LISTA - Listagem normal de inventários
    inventarios = Inventario.objects.all().order_by('-data')

    # Filtros
    status = request.GET.get('status')
    deposito_id = request.GET.get('deposito')
    search = request.GET.get('search')
    per_page = request.GET.get('per_page', 25)

    if status:
        inventarios = inventarios.filter(status=status)
    if deposito_id:
        inventarios = inventarios.filter(deposito_id=deposito_id)
    if search:
        inventarios = inventarios.filter(numero__icontains=search)

    # Cards de resumo
    hoje = timezone.now()
    total_inventarios = Inventario.objects.count()
    total_abertos = Inventario.objects.filter(status='aberto').count()
    total_andamento = Inventario.objects.filter(status='em_andamento').count()
    total_concluidos = Inventario.objects.filter(status='concluido').count()
    inventarios_mes = Inventario.objects.filter(
        data_criacao__year=hoje.year,
        data_criacao__month=hoje.month
    ).count()

    paginator = Paginator(inventarios, int(per_page))
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'inventarios': page_obj,
        'page_obj': page_obj,
        'total': paginator.count,
        'status_choices': Inventario.STATUS_CHOICES,
        'depositos': Deposito.objects.filter(ativo=True),
        # Cards de resumo
        'total_inventarios': total_inventarios,
        'total_abertos': total_abertos,
        'total_andamento': total_andamento,
        'total_concluidos': total_concluidos,
        'inventarios_mes': inventarios_mes,
        # Filtros ativos
        'status': status,
        'deposito_id': deposito_id,
        'search': search,
        'per_page': int(per_page),
        'hoje': hoje.strftime('%Y-%m-%d'),
        'modo_contagem': False,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'estoque/partials/inventario_table.html', context)

    return render(request, 'estoque/inventario_manager.html', context)


@login_required
def inventario_add(request):
    """Modal para novo inventário."""
    
    
    if request.method == 'POST':
        form = InventarioForm(request.POST)
        if form.is_valid():
            inventario = form.save(commit=False)
            inventario.usuario = request.user
            inventario.save()
            
            # Criar itens do inventário para todos os produtos do depósito
            inventario.gerar_itens_inventario()
            
            # ✅ CORREÇÃO: Redirecionar para list com parâmetro de contagem
            if request.headers.get('HX-Request'):
                return HttpResponse(
                    f'<script>window.location.href = "{reverse("ERP_ServicesBI:inventario_list")}?contagem={inventario.pk}";</script>'
                )
            
            messages.success(request, 'Inventário iniciado!')
            return redirect(f'{reverse("ERP_ServicesBI:inventario_list")}?contagem={inventario.pk}')
    else:
        form = InventarioForm()
    
    context = {
        'form': form,
        'depositos': Deposito.objects.filter(ativo=True),
        'hoje': timezone.now().strftime('%Y-%m-%d'),
    }
    return render(request, 'estoque/inventario_form.html', context)


@login_required
def inventario_contagem(request, pk):
    """
    ✅ CORREÇÃO: Redireciona para a listagem com modo contagem ativado.
    A contagem é renderizada dentro do inventario_manager.html
    """
    return redirect(f'{reverse("ERP_ServicesBI:inventario_list")}?contagem={pk}')


@login_required
def inventario_edit(request, pk):
    """Modal para editar inventário (apenas dados básicos)."""
    inventario = get_object_or_404(Inventario, pk=pk)
    
    if request.method == 'POST':
        form = InventarioForm(request.POST, instance=inventario)
        if form.is_valid():
            form.save()
            
            if request.headers.get('HX-Request'):
                return HttpResponse(
                    '<script>document.body.dispatchEvent(new Event("inventarioUpdated"));'
                    'document.querySelector(".modal.show")?.querySelector(".btn-close")?.click();</script>'
                )
            
            messages.success(request, 'Inventário atualizado!')
            return redirect('ERP_ServicesBI:inventario_list')
    else:
        form = InventarioForm(instance=inventario)
    
    context = {
        'inventario': inventario,
        'form': form,
        'depositos': Deposito.objects.filter(ativo=True),
    }
    return render(request, 'estoque/inventario_form.html', context)


@login_required
def inventario_delete(request, pk):
    """Modal de confirmação de exclusão."""
    inventario = get_object_or_404(Inventario, pk=pk)
    
    if request.method == 'POST':
        inventario.delete()
        
        if request.headers.get('HX-Request'):
            return HttpResponse(
                '<script>document.body.dispatchEvent(new Event("inventarioUpdated"));'
                'document.querySelector(".modal.show")?.querySelector(".btn-close")?.click();</script>'
            )
        
        messages.success(request, 'Inventário excluído!')
        return redirect('ERP_ServicesBI:inventario_list')
    
    return render(request, 'estoque/inventario_confirm_delete.html', {'inventario': inventario})


@login_required
def inventario_finalizar(request, pk):
    inventario = get_object_or_404(Inventario, pk=pk)
    if request.method == 'POST':
        inventario.aplicar_ajustes()
        inventario.status = 'concluido'
        inventario.save()
        ajustes = ItemInventario.objects.filter(inventario=inventario).exclude(diferenca=0).count()
        messages.success(request, f'Inventário finalizado! {ajustes} ajustes.')
        return redirect('ERP_ServicesBI:inventario_list')
    return render(request, 'estoque/inventario_finalizar.html', {'inventario': inventario})

# -----------------------------------------------------------------------------
# 10.4 ENTRADA NF-e (Manager+Form Pattern)
# -----------------------------------------------------------------------------

@login_required
def entrada_nfe_list(request):
    """Listagem de entradas de NF-e - Manager Pattern."""
    entradas = EntradaNFE.objects.select_related('fornecedor', 'pedido_compra').all().order_by('-data_entrada')
    
    # Filtros
    numero = request.GET.get('numero')
    serie = request.GET.get('serie')
    fornecedor_busca = request.GET.get('fornecedor')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    if numero:
        entradas = entradas.filter(numero__icontains=numero)
    if serie:
        entradas = entradas.filter(serie__icontains=serie)
    if fornecedor_busca:
        entradas = entradas.filter(
            Q(fornecedor__razao_social__icontains=fornecedor_busca) |
            Q(fornecedor__nome_fantasia__icontains=fornecedor_busca) |
            Q(fornecedor__cnpj__icontains=fornecedor_busca)
        )
    if data_inicio:
        entradas = entradas.filter(data_emissao__gte=data_inicio)
    if data_fim:
        entradas = entradas.filter(data_emissao__lte=data_fim)
    
    paginator = Paginator(entradas, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    context = {
        'notas_fiscais': page_obj,
        'page_obj': page_obj,
        'total': paginator.count,
        'fornecedores': Fornecedor.objects.filter(ativo=True),
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'estoque/partials/entrada_nfe_table.html', context)
    
    return render(request, 'estoque/entrada_nfe_manager.html', context)


@login_required
def entrada_nfe_add(request):
    """Modal para nova entrada de NF-e."""
    if request.method == 'POST':
        form = EntradaNFEForm(request.POST)
        if form.is_valid():
            entrada = form.save(commit=False)
            entrada.usuario = request.user
            entrada.save()
            
            if request.headers.get('HX-Request'):
                return HttpResponse(
                    f'<script>window.location.href = "{reverse("ERP_ServicesBI:entrada_nfe_itens", kwargs={"pk": entrada.pk})}";</script>'
                )
            
            messages.success(request, 'Entrada registrada. Adicione itens.')
            return redirect('ERP_ServicesBI:entrada_nfe_itens', pk=entrada.pk)
    else:
        form = EntradaNFEForm()
    
    context = {
        'form': form,
        'fornecedores': Fornecedor.objects.filter(ativo=True),
        'depositos': Deposito.objects.filter(ativo=True),
        'today': timezone.now().date(),
    }
    return render(request, 'estoque/entrada_nfe_manager_form.html', context)


@login_required
def entrada_nfe_edit(request, pk):
    """Modal para editar entrada de NF-e."""
    entrada = get_object_or_404(EntradaNFE, pk=pk)
    
    if request.method == 'POST':
        form = EntradaNFEForm(request.POST, instance=entrada)
        if form.is_valid():
            form.save()
            
            if request.headers.get('HX-Request'):
                return HttpResponse(
                    '<script>document.body.dispatchEvent(new Event("nfeUpdated"));'
                    'document.querySelector(".modal.show").querySelector(".btn-close").click();</script>'
                )
            
            messages.success(request, 'NF-e atualizada!')
            return redirect('ERP_ServicesBI:entrada_nfe_list')
    else:
        form = EntradaNFEForm(instance=entrada)
    
    # Buscar itens existentes para o JSON
    itens = ItemEntradaNFE.objects.filter(entrada=entrada).select_related('produto', 'deposito')
    itens_json = json.dumps([{
        'produto': item.produto_id,
        'cfop': item.cfop,
        'quantidade': float(item.quantidade),
        'valor_unitario': float(item.valor_unitario),
        'valor_total': float(item.valor_total),
        'deposito': item.deposito_id,
    } for item in itens])
    
    context = {
        'nota_fiscal': entrada,
        'form': form,
        'fornecedores': Fornecedor.objects.filter(ativo=True),
        'depositos': Deposito.objects.filter(ativo=True),
        'produtos': Produto.objects.filter(ativo=True),
        'itens_json': itens_json,
        'today': timezone.now().date(),
    }
    return render(request, 'estoque/entrada_nfe_manager_form.html', context)


@login_required
def entrada_nfe_detail(request, pk):
    """Modal de detalhes da NF-e."""
    entrada = get_object_or_404(
        EntradaNFE.objects.select_related('fornecedor', 'pedido_compra', 'usuario'),
        pk=pk
    )
    itens = ItemEntradaNFE.objects.filter(entrada=entrada).select_related('produto', 'deposito')
    
    return render(request, 'estoque/entrada_nfe_detail.html', {
        'entrada': entrada,
        'itens': itens,
    })


@login_required
def entrada_nfe_itens(request, pk):
    """Tela de itens da NF-e (não é modal - tela completa)."""
    entrada = get_object_or_404(EntradaNFE, pk=pk)
    
    if request.method == 'POST':
        form = ItemEntradaNFEForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.entrada = entrada
            item.save()
            messages.success(request, 'Item adicionado!')
            return redirect('ERP_ServicesBI:entrada_nfe_itens', pk=pk)
    else:
        form = ItemEntradaNFEForm()
    
    itens = ItemEntradaNFE.objects.filter(entrada=entrada).select_related('produto', 'deposito')
    
    return render(request, 'estoque/entrada_nfe_itens.html', {
        'entrada': entrada, 
        'form': form, 
        'itens': itens
    })


@login_required
def entrada_nfe_finalizar(request, pk):
    entrada = get_object_or_404(EntradaNFE, pk=pk)
    if request.method == 'POST':
        entrada.status = 'finalizada'
        entrada.save()
        messages.success(request, 'Entrada finalizada!')
        return redirect('ERP_ServicesBI:entrada_nfe_list')
    return render(request, 'estoque/entrada_nfe_finalizar.html', {'entrada': entrada})


@login_required
def entrada_nfe_importar_xml(request):
    """Modal para importar XML de NF-e."""
    if request.method == 'POST':
        xml_file = request.FILES.get('xml')
        if not xml_file:
            return JsonResponse({'success': False, 'message': 'Arquivo XML não enviado'})
        
        try:
            # Processar XML aqui
            # resultado = processar_xml_nfe(xml_file)
            messages.success(request, 'XML importado com sucesso!')
            
            if request.headers.get('HX-Request'):
                return HttpResponse(
                    '<script>document.body.dispatchEvent(new Event("nfeUpdated"));'
                    'document.querySelector(".modal.show").querySelector(".btn-close").click();</script>'
                )
            
            return redirect('ERP_ServicesBI:entrada_nfe_list')
        except Exception as e:
            if request.headers.get('HX-Request'):
                return HttpResponse(f'<div class="alert alert-danger">Erro: {str(e)}</div>')
            
            messages.error(request, f'Erro ao importar XML: {str(e)}')
    
    return render(request, 'estoque/entrada_nfe_importar_xml.html')


# =============================================================================
# MÓDULO: ESTOQUE - TRANSFERÊNCIA
# =============================================================================

@login_required
def transferencia_list(request):
    """Listagem de transferências - Manager Pattern."""
    # ✅ CORRIGIDO: Remover select_related de CharField (deposito_origem, deposito_destino)
    # Apenas usar select_related em ForeignKey (usuario) e prefetch_related em relacionamentos
    transferencias = TransferenciaEstoque.objects.select_related('usuario').prefetch_related('itens').all().order_by('-data')
    
    # Filtros
    status = request.GET.get('status')
    deposito_origem = request.GET.get('deposito_origem')
    deposito_destino = request.GET.get('deposito_destino')
    
    if status:
        transferencias = transferencias.filter(status=status)
    # ✅ CORRIGIDO: CharField usa filter direto, não _id
    if deposito_origem:
        transferencias = transferencias.filter(deposito_origem=deposito_origem)
    if deposito_destino:
        transferencias = transferencias.filter(deposito_destino=deposito_destino)
    
    paginator = Paginator(transferencias, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    context = {
        'transferencias': page_obj,
        'page_obj': page_obj,
        'total': paginator.count,
        'status_choices': TransferenciaEstoque.STATUS_CHOICES,
        'depositos': Deposito.objects.filter(ativo=True),
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'estoque/partials/transferencia_table.html', context)
    
    return render(request, 'estoque/transferencia_manager.html', context)


@login_required
def transferencia_add(request):
    """Modal para nova transferência."""
    if request.method == 'POST':
        form = TransferenciaEstoqueForm(request.POST)
        if form.is_valid():
            transferencia = form.save(commit=False)
            transferencia.usuario = request.user
            transferencia.save()
            
            # Processar itens do JSON
            itens_json = request.POST.get('itens_json', '[]')
            try:
                itens = json.loads(itens_json)
            except json.JSONDecodeError:
                itens = []
            
            for item in itens:
                try:
                    ItemTransferencia.objects.create(
                        transferencia=transferencia,
                        produto_id=int(item.get('produto')),
                        quantidade=Decimal(str(item.get('quantidade', 0))),
                    )
                except (ValueError, KeyError, TypeError):
                    continue
            
            if request.headers.get('HX-Request'):
                return HttpResponse(
                    '<script>'
                    'document.body.dispatchEvent(new Event("transferenciaUpdated"));'
                    'const modal = document.querySelector(".modal.show");'
                    'if(modal) modal.querySelector(".btn-close").click();'
                    '</script>'
                )
            
            messages.success(request, 'Transferência criada!')
            return redirect('ERP_ServicesBI:transferencia_list')
        else:
            if request.headers.get('HX-Request'):
                return render(request, 'estoque/transferencia_manager_form.html', {
                    'form': form,
                    'depositos': Deposito.objects.filter(ativo=True),
                    'produtos': Produto.objects.filter(ativo=True),
                })
    else:
        form = TransferenciaEstoqueForm()
    
    context = {
        'form': form,
        'transferencia': None,
        'depositos': Deposito.objects.filter(ativo=True),
        'produtos': Produto.objects.filter(ativo=True),
    }
    return render(request, 'estoque/transferencia_manager_form.html', context)


@login_required
def transferencia_edit(request, pk):
    """Modal para editar transferência (apenas se pendente)."""
    transferencia = get_object_or_404(TransferenciaEstoque, pk=pk)
    
    if transferencia.status != 'pendente':
        messages.error(request, 'Apenas transferências pendentes podem ser editadas!')
        return redirect('ERP_ServicesBI:transferencia_list')
    
    if request.method == 'POST':
        form = TransferenciaEstoqueForm(request.POST, instance=transferencia)
        if form.is_valid():
            form.save()
            
            # Atualizar itens
            ItemTransferencia.objects.filter(transferencia=transferencia).delete()
            itens_json = request.POST.get('itens_json', '[]')
            try:
                itens = json.loads(itens_json)
            except json.JSONDecodeError:
                itens = []
            
            for item in itens:
                try:
                    ItemTransferencia.objects.create(
                        transferencia=transferencia,
                        produto_id=int(item.get('produto')),
                        quantidade=Decimal(str(item.get('quantidade', 0))),
                    )
                except (ValueError, KeyError, TypeError):
                    continue
            
            if request.headers.get('HX-Request'):
                return HttpResponse(
                    '<script>'
                    'document.body.dispatchEvent(new Event("transferenciaUpdated"));'
                    'const modal = document.querySelector(".modal.show");'
                    'if(modal) modal.querySelector(".btn-close").click();'
                    '</script>'
                )
            
            messages.success(request, 'Transferência atualizada!')
            return redirect('ERP_ServicesBI:transferencia_list')
        else:
            if request.headers.get('HX-Request'):
                return render(request, 'estoque/transferencia_manager_form.html', {
                    'form': form,
                    'transferencia': transferencia,
                    'depositos': Deposito.objects.filter(ativo=True),
                    'produtos': Produto.objects.filter(ativo=True),
                })
    else:
        form = TransferenciaEstoqueForm(instance=transferencia)
    
    # Buscar itens existentes
    itens = ItemTransferencia.objects.filter(transferencia=transferencia).select_related('produto')
    
    context = {
        'transferencia': transferencia,
        'form': form,
        'depositos': Deposito.objects.filter(ativo=True),
        'produtos': Produto.objects.filter(ativo=True),
        'itens': itens,
    }
    return render(request, 'estoque/transferencia_manager_form.html', context)


@login_required
def transferencia_detail(request, pk):
    """Modal de detalhes da transferência."""
    # ✅ CORRIGIDO: select_related apenas em ForeignKey (usuario)
    transferencia = get_object_or_404(
        TransferenciaEstoque.objects.select_related('usuario'),
        pk=pk
    )
    itens = ItemTransferencia.objects.filter(transferencia=transferencia).select_related('produto')
    
    return render(request, 'estoque/transferencia_detail.html', {
        'transferencia': transferencia,
        'itens': itens,
    })


@login_required
def transferencia_delete(request, pk):
    """Modal de confirmação de exclusão."""
    transferencia = get_object_or_404(TransferenciaEstoque, pk=pk)
    
    if request.method == 'POST':
        if transferencia.status != 'pendente':
            return HttpResponse(
                '<div class="alert alert-danger">Apenas transferências pendentes podem ser excluídas!</div>'
            )
        
        transferencia.delete()
        
        if request.headers.get('HX-Request'):
            return HttpResponse(
                '<script>'
                'document.body.dispatchEvent(new Event("transferenciaUpdated"));'
                'const modal = document.querySelector(".modal.show");'
                'if(modal) modal.querySelector(".btn-close").click();'
                '</script>'
            )
        
        messages.success(request, 'Transferência excluída!')
        return redirect('ERP_ServicesBI:transferencia_list')
    
    return render(request, 'estoque/transferencia_confirm_delete.html', {'transferencia': transferencia})


@login_required
@require_http_methods(["POST"])
def transferencia_enviar(request, pk):
    """Ação de enviar transferência (HTMX)."""
    transferencia = get_object_or_404(TransferenciaEstoque, pk=pk)
    
    if transferencia.status != 'pendente':
        return HttpResponse('<span class="text-danger">Apenas pendentes podem ser enviadas!</span>')
    
    try:
        # ✅ Verificar se a transferência tem itens
        if not transferencia.itens.exists():
            return HttpResponse('<span class="text-danger">Transferência sem itens!</span>')
        
        # ✅ Atualizar status para concluída (ou outro status conforme sua lógica)
        transferencia.status = 'concluida'
        transferencia.save()
        
        messages.success(request, 'Transferência enviada!')
        
        # Retornar linha atualizada da tabela
        return render(request, 'estoque/partials/transferencia_row.html', {'transf': transferencia})
    except Exception as e:
        return HttpResponse(f'<span class="text-danger">Erro: {str(e)}</span>')


@login_required
@require_http_methods(["POST"])
def transferencia_receber(request, pk):
    """Ação de receber transferência (HTMX)."""
    transferencia = get_object_or_404(TransferenciaEstoque, pk=pk)
    
    # ✅ CORRIGIDO: Verificar status correto (concluida, não em_transito)
    if transferencia.status != 'concluida':
        return HttpResponse('<span class="text-danger">Status inválido! Apenas transferências concluídas podem ser recebidas.</span>')
    
    try:
        # ✅ Atualizar status para efetivada
        transferencia.status = 'efetivada'
        transferencia.data_efetivacao = timezone.now()
        transferencia.save()
        
        messages.success(request, 'Transferência recebida e efetivada!')
        
        # Retornar linha atualizada da tabela
        return render(request, 'estoque/partials/transferencia_row.html', {'transf': transferencia})
    except Exception as e:
        return HttpResponse(f'<span class="text-danger">Erro: {str(e)}</span>')


@login_required
@require_http_methods(["POST"])
def transferencia_cancelar(request, pk):
    """Ação de cancelar transferência (HTMX)."""
    transferencia = get_object_or_404(TransferenciaEstoque, pk=pk)
    
    # ✅ Apenas transferências pendentes podem ser canceladas
    if transferencia.status not in ['pendente', 'concluida']:
        return HttpResponse('<span class="text-danger">Apenas pendentes ou concluídas podem ser canceladas!</span>')
    
    try:
        transferencia.status = 'cancelada'
        transferencia.save()
        
        messages.success(request, 'Transferência cancelada!')
        
        # Retornar linha atualizada da tabela
        return render(request, 'estoque/partials/transferencia_row.html', {'transf': transferencia})
    except Exception as e:
        return HttpResponse(f'<span class="text-danger">Erro: {str(e)}</span>')

# =============================================================================
# 10.6 RELATÓRIOS DE ESTOQUE (Manter existentes)
# =============================================================================

@login_required
def relatorio_estoque(request):
    """Relatório de saldo de estoque por depósito."""
    deposito_id = request.GET.get('deposito')
    produto_id = request.GET.get('produto')
    
    saldos = SaldoEstoque.objects.select_related('produto', 'deposito').all()
    
    if deposito_id:
        saldos = saldos.filter(deposito_id=deposito_id)
    if produto_id:
        saldos = saldos.filter(produto_id=produto_id)
        
    # Produtos com estoque baixo
    estoque_baixo = Produto.objects.filter(
        ativo=True,
        estoque_atual__lte=F('estoque_minimo')
    ).exclude(estoque_minimo=0)
    
    # Movimentações recentes
    movimentacoes_recentes = MovimentacaoEstoque.objects.select_related(
        'produto', 'deposito_origem', 'deposito_destino', 'usuario'
    ).order_by('-data')[:50]
    
    # ✅ CORRIGIDO: Usar 'preco_custo' em vez de 'custo_medio'
    # Valor total do estoque
    valor_total_estoque = SaldoEstoque.objects.annotate(
        valor=ExpressionWrapper(
            F('quantidade') * F('produto__preco_custo'),
            output_field=DecimalField()
        )
    ).aggregate(total=Sum('valor'))['total'] or 0
    
    context = {
        'saldos': saldos,
        'depositos': Deposito.objects.filter(ativo=True),
        'produtos': Produto.objects.filter(ativo=True),
        'estoque_baixo': estoque_baixo,
        'movimentacoes_recentes': movimentacoes_recentes,
        'valor_total_estoque': valor_total_estoque,
        'deposito_selecionado': int(deposito_id) if deposito_id else None,
        'produto_selecionado': int(produto_id) if produto_id else None,
    }
    return render(request, 'estoque/relatorio_estoque.html', context)


@login_required
def relatorio_movimentacao(request):
    """Relatório detalhado de movimentações de estoque."""
    from django.utils.dateparse import parse_date
    
    data_inicio = parse_date(request.GET.get('data_inicio', ''))
    data_fim = parse_date(request.GET.get('data_fim', ''))
    tipo = request.GET.get('tipo', '')
    produto_id = request.GET.get('produto', '')
    deposito_id = request.GET.get('deposito', '')
    
    movimentacoes = MovimentacaoEstoque.objects.select_related(
        'produto', 'deposito_origem', 'deposito_destino', 'usuario', 'nota_fiscal_entrada'
    ).all().order_by('-data')
    
    if data_inicio:
        movimentacoes = movimentacoes.filter(data__gte=data_inicio)
    if data_fim:
        movimentacoes = movimentacoes.filter(data__lte=data_fim)
    if tipo:
        movimentacoes = movimentacoes.filter(tipo=tipo)
    if produto_id:
        movimentacoes = movimentacoes.filter(produto_id=produto_id)
    if deposito_id:
        movimentacoes = movimentacoes.filter(
            Q(deposito_origem_id=deposito_id) | Q(deposito_destino_id=deposito_id)
        )
    
    # Resumo por tipo
    resumo_tipo = movimentacoes.values('tipo').annotate(
        total=Count('id'),
        quantidade_total=Sum('quantidade')
    ).order_by('tipo')
    
    # Resumo por produto (top 20)
    resumo_produto = movimentacoes.values(
        'produto__descricao', 'produto__codigo'
    ).annotate(
        total_movimentacoes=Count('id'),
        quantidade_total=Sum('quantidade')
    ).order_by('-quantidade_total')[:20]
    
    context = {
        'movimentacoes': movimentacoes[:1000],  # Limitar para performance
        'resumo_tipo': resumo_tipo,
        'resumo_produto': resumo_produto,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'tipo_selecionado': tipo,
        'produto_selecionado': int(produto_id) if produto_id else None,
        'deposito_selecionado': int(deposito_id) if deposito_id else None,
        'tipos': MovimentacaoEstoque.TIPO_CHOICES,
        'produtos': Produto.objects.filter(ativo=True).order_by('descricao'),
        'depositos': Deposito.objects.filter(ativo=True).order_by('nome'),
        'total_registros': movimentacoes.count(),
    }
    return render(request, 'estoque/relatorio_movimentacoes.html', context)


# =============================================================================
# 10.7 CONSULTAS E APIs DE ESTOQUE (Consolidadas - Removidas duplicidades)
# =============================================================================

@login_required
def consulta_saldo(request):
    """View para consulta rápida de saldo de estoque."""
    produto_id = request.GET.get('produto')
    deposito_id = request.GET.get('deposito')
    
    saldos = []
    produto_selecionado = None
    deposito_selecionado = None
    
    if produto_id:
        try:
            produto_selecionado = Produto.objects.get(pk=produto_id)
            saldos_query = SaldoEstoque.objects.filter(produto=produto_selecionado)
            
            if deposito_id:
                saldos_query = saldos_query.filter(deposito_id=deposito_id)
                deposito_selecionado = Deposito.objects.filter(pk=deposito_id).first()
            
            saldos = saldos_query.select_related('deposito', 'produto')
        except Produto.DoesNotExist:
            messages.error(request, 'Produto não encontrado.')
    
    # Se não houver filtros, mostrar todos os saldos baixos
    if not produto_id and not deposito_id:
        saldos = SaldoEstoque.objects.filter(
            quantidade__lte=F('produto__estoque_minimo')
        ).select_related('deposito', 'produto')[:100]
    
    context = {
        'saldos': saldos,
        'produtos': Produto.objects.filter(ativo=True).order_by('descricao'),
        'depositos': Deposito.objects.filter(ativo=True).order_by('nome'),
        'produto_selecionado': produto_selecionado,
        'deposito_selecionado': deposito_selecionado,
    }
    return render(request, 'estoque/consulta_saldo.html', context)


@login_required
def api_estoque_saldo(request):
    """
    API para consultar saldo de estoque via query parameters.
    ÚNICA API para consulta de saldo (consolidada).
    """
    produto_id = request.GET.get('produto_id')
    deposito_id = request.GET.get('deposito_id')
    
    if not produto_id:
        return JsonResponse({'success': False, 'message': 'produto_id obrigatório'}, status=400)
    
    try:
        produto = Produto.objects.get(pk=produto_id)
        saldo_query = SaldoEstoque.objects.filter(produto=produto)
        
        if deposito_id:
            saldo_query = saldo_query.filter(deposito_id=deposito_id)
            saldo = saldo_query.first()
            # ✅ CORRIGIDO: Usar 'preco_custo' em vez de 'custo_medio'
            return JsonResponse({
                'success': True,
                'produto_id': produto_id,
                'deposito_id': deposito_id,
                'saldo': float(saldo.quantidade) if saldo else 0,
                'preco_custo': float(saldo.produto.preco_custo or 0) if saldo else float(produto.preco_custo or 0),
            })
        else:
            saldos = saldo_query.select_related('deposito')
            return JsonResponse({
                'success': True,
                'produto_id': produto_id,
                'saldo_total': float(sum(s.quantidade for s in saldos)),
                'depositos': [
                    {
                        'deposito_id': s.deposito_id,
                        'deposito_nome': s.deposito.nome,
                        'saldo': float(s.quantidade),
                        'preco_custo': float(s.produto.preco_custo or 0),
                    }
                    for s in saldos
                ]
            })
    except Produto.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Produto não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro: {str(e)}'}, status=500)


@login_required
def api_produto_saldo_disponivel(request, pk):
    """
    API para verificar saldo disponível de um produto específico via URL parameter.
    Mantida para compatibilidade com URLs existentes.
    """
    try:
        produto = get_object_or_404(Produto, pk=pk)
        deposito_id = request.GET.get('deposito_id')
        
        saldo_query = SaldoEstoque.objects.filter(produto=produto)
        if deposito_id:
            saldo_query = saldo_query.filter(deposito_id=deposito_id)
            saldo = saldo_query.first()
            quantidade = saldo.quantidade if saldo else 0
        else:
            quantidade = sum(s.quantidade for s in saldo_query)
            
        # ✅ CORRIGIDO: Usar 'preco_custo' em vez de 'custo_medio'
        return JsonResponse({
            'success': True,
            'produto_id': pk,
            'produto_nome': produto.descricao,
            'saldo_disponivel': float(quantidade),
            'unidade': produto.unidade or 'UN',
            'preco_custo': float(produto.preco_custo or 0),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro: {str(e)}'}, status=500)


@login_required
def api_produtos_busca(request):
    """API para busca AJAX de produtos."""
    try:
        termo = request.GET.get('q', '').strip()
        limit = int(request.GET.get('limit', 20))
        
        if not termo or len(termo) < 2:
            return JsonResponse({'success': True, 'produtos': []})
        
        produtos = Produto.objects.filter(
            Q(descricao__icontains=termo) | Q(codigo__icontains=termo),
            ativo=True
        ).values('id', 'descricao', 'codigo', 'unidade', 'preco_venda')[:limit]
        
        return JsonResponse({
            'success': True,
            'produtos': list(produtos)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro na busca: {str(e)}'}, status=500)