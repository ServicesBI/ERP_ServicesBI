# -*- coding: utf-8 -*-
"""
=============================================================================
ERP SERVICES BI - VIEWS COMPLETAS E ORGANIZADAS
=============================================================================
Arquivo único com todas as views do sistema, organizadas por módulos
na ordem do menu lateral.
=============================================================================
"""

# =============================================================================
# IMPORTS PADRÃO DO PYTHON
# =============================================================================
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from urllib.parse import parse_qs

# =============================================================================
# IMPORTS DO DJANGO
# =============================================================================
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum, F, Value, DecimalField, Count, Avg
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt

# =============================================================================
# IMPORTS DE MODELOS - CADASTRO
# =============================================================================
from .models import (
    Empresa, 
    Cliente, 
    Fornecedor, 
    Produto, 
    Categoria
)

# =============================================================================
# IMPORTS DE MODELOS - COMPRAS
# =============================================================================
from .models import (
    Cotacao,
    Produto,
    ItemCotacao, 
    PedidoCompra, 
    ItemPedidoCompra,
    NotaFiscalEntrada, 
    ItemNotaFiscalEntrada,
)

# =============================================================================
# IMPORTS DE MODELOS - VENDAS
# =============================================================================
from .models import (
    Orcamento, 
    ItemOrcamento,
    PedidoVenda, 
    ItemPedidoVenda,
    NotaFiscalSaida, 
    ItemNotaFiscalSaida,
)

# =============================================================================
# IMPORTS DE MODELOS - FINANCEIRO
# =============================================================================
from .models import (
    CategoriaFinanceira, 
    CentroCusto, 
    OrcamentoFinanceiro,
    ContaReceber, 
    ContaPagar, 
    MovimentoCaixa,
    ExtratoBancario, 
    LancamentoExtrato,
)

# =============================================================================
# IMPORTS DE MODELOS - ESTOQUE
# =============================================================================
from .models import (
    MovimentacaoEstoque, 
    Inventario, 
    ItemInventario,
    TransferenciaEstoque, 
    ItemTransferencia,
)

# =============================================================================
# IMPORTS DE FORMS - CADASTRO
# =============================================================================
from .forms import (
    EmpresaForm, 
    ClienteForm, 
    FornecedorForm, 
    ProdutoForm, 
    CategoriaForm,
)

# =============================================================================
# IMPORTS DE FORMS - COMPRAS
# =============================================================================
from .forms import (
    CotacaoForm, 
    ItemCotacaoForm,
    PedidoCompraForm, 
    ItemPedidoCompraForm,
    NotaFiscalEntradaForm, 
    ItemNotaFiscalEntradaForm,
)

# =============================================================================
# IMPORTS DE FORMS - VENDAS
# =============================================================================
from .forms import (
    OrcamentoForm, 
    ItemOrcamentoForm,
    PedidoVendaForm, 
    ItemPedidoVendaForm,
    NotaFiscalSaidaForm, 
    ItemNotaFiscalSaidaForm,
)

# =============================================================================
# IMPORTS DE FORMS - FINANCEIRO
# =============================================================================
from .forms import (
    CategoriaFinanceiraForm, 
    CentroCustoForm, 
    OrcamentoFinanceiroForm,
    ContaReceberForm, 
    ContaPagarForm, 
    MovimentoCaixaForm,
    ExtratoBancarioForm, 
    LancamentoExtratoForm,
)

# =============================================================================
# IMPORTS DE FORMS - ESTOQUE
# =============================================================================
from .forms import (
    MovimentacaoEstoqueForm, 
    InventarioForm, 
    ItemInventarioForm,
    TransferenciaEstoqueForm, 
    ItemTransferenciaForm,
)

# =============================================================================
# CONFIGURAÇÃO DE LOGGING
# =============================================================================
logger = logging.getLogger(__name__)

# =============================================================================
# WEASYPINT PARA PDFs (OPCIONAL)
# =============================================================================
try:
    from weasyprint import HTML, FontConfiguration
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False


# =============================================================================
# UTILITÁRIOS GLOBAIS
# =============================================================================

def gerar_pdf_html(request, template_name, context, filename="documento.pdf"):
    """
    Função utilitária para gerar PDF a partir de template HTML
    """
    if not WEASYPRINT_AVAILABLE:
        messages.error(request, 'WeasyPrint não está instalado. PDF não pode ser gerado.')
        return redirect(request.META.get('HTTP_REFERER', '/'))

    html_string = render_to_string(template_name, context, request=request)
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf = html.write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

# =============================================================================
# DASHBOARD / HOME
# =============================================================================

@login_required
def dashboard(request):
    """Dashboard principal do sistema"""
    hoje = timezone.now().date()
    mes_atual = hoje.month
    ano_atual = hoje.year
    
    # Resumo de vendas
    vendas_mes = NotaFiscalSaida.objects.filter(
        data_emissao__month=mes_atual,
        data_emissao__year=ano_atual
    ).aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')
    
    # Resumo de compras
    compras_mes = NotaFiscalEntrada.objects.filter(
        data_entrada__month=mes_atual,
        data_entrada__year=ano_atual
    ).aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')
    
    # Contas a receber/receber hoje
    contas_receber_hoje = ContaReceber.objects.filter(
        data_vencimento=hoje,
        status='pendente'
    ).aggregate(total=Sum('valor_original'))['total'] or Decimal('0.00')
    
    # Contas a pagar/pagar hoje
    contas_pagar_hoje = ContaPagar.objects.filter(
        data_vencimento=hoje,
        status='pendente'
    ).aggregate(total=Sum('valor_original'))['total'] or Decimal('0.00')
    
    # Produtos com estoque baixo
    produtos_estoque_baixo = Produto.objects.filter(
        estoque_atual__lte=F('estoque_minimo')
    ).count()
    
    # Últimos pedidos
    ultimos_pedidos = PedidoVenda.objects.all().order_by('-data_pedido')[:5]
    
    context = {
        'vendas_mes': vendas_mes,
        'compras_mes': compras_mes,
        'contas_receber_hoje': contas_receber_hoje,
        'contas_pagar_hoje': contas_pagar_hoje,
        'produtos_estoque_baixo': produtos_estoque_baixo,
        'ultimos_pedidos': ultimos_pedidos,
    }
    
    return render(request, 'dashboard.html', context)


# =============================================================================
# 1. CADASTRO > CLIENTES (CRUD COMPLETO)
# =============================================================================

@login_required
def cliente_list(request):
    """Lista de clientes com paginação avançada (25/50 itens)"""
    search = request.GET.get('search', '')
    clientes = Cliente.objects.all().order_by('nome_razao_social')

    if search:
        clientes = clientes.filter(
            Q(nome_razao_social__icontains=search) |
            Q(nome_fantasia__icontains=search) |
            Q(cpf_cnpj__icontains=search)
        )

    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [25, 50]:
            per_page = 25
    except ValueError:
        per_page = 25

    paginator = Paginator(clientes, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'cadastro/cliente_list.html', {
        'clientes': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'search': search,
        'per_page': per_page,
        'total': paginator.count,
    })


@login_required
def cliente_add(request):
    """Adicionar novo cliente"""
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente cadastrado com sucesso!')
            return redirect('ERP_ServicesBI:cliente_list')
    else:
        form = ClienteForm()

    return render(request, 'cadastro/cliente_form.html', {
        'form': form,
        'titulo': 'Novo Cliente',
        'action': 'Adicionar'
    })


@login_required
def cliente_edit(request, pk):
    """Editar cliente existente"""
    cliente = get_object_or_404(Cliente, pk=pk)

    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente atualizado com sucesso!')
            return redirect('ERP_ServicesBI:cliente_list')
    else:
        form = ClienteForm(instance=cliente)

    return render(request, 'cadastro/cliente_form.html', {
        'form': form,
        'titulo': 'Editar Cliente',
        'action': 'Salvar Alterações',
        'cliente': cliente
    })


@login_required
def cliente_delete(request, pk):
    """Excluir cliente"""
    cliente = get_object_or_404(Cliente, pk=pk)

    if request.method == 'POST':
        cliente.delete()
        messages.success(request, 'Cliente excluído com sucesso!')
        return redirect('ERP_ServicesBI:cliente_list')

    return render(request, 'cadastro/cliente_confirm_delete.html', {
        'cliente': cliente
    })


# =============================================================================
# 2. CADASTRO > EMPRESAS (CRUD COMPLETO)
# =============================================================================

@login_required
def empresa_list(request):
    """Lista de empresas com paginação avançada (25/50 itens)"""
    search = request.GET.get('search', '')
    empresas = Empresa.objects.all().order_by('razao_social')

    if search:
        empresas = empresas.filter(
            Q(razao_social__icontains=search) |
            Q(nome_fantasia__icontains=search) |
            Q(cnpj__icontains=search)
        )

    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [25, 50]:
            per_page = 25
    except ValueError:
        per_page = 25

    paginator = Paginator(empresas, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'cadastro/empresa_list.html', {
        'empresas': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'search': search,
        'per_page': per_page,
        'total': paginator.count,
    })


@login_required
def empresa_add(request):
    """Adicionar nova empresa"""
    if request.method == 'POST':
        form = EmpresaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Empresa cadastrada com sucesso!')
            return redirect('ERP_ServicesBI:empresa_list')
    else:
        form = EmpresaForm()

    return render(request, 'cadastro/empresa_form.html', {
        'form': form,
        'titulo': 'Nova Empresa',
        'action': 'Adicionar'
    })


@login_required
def empresa_edit(request, pk):
    """Editar empresa existente"""
    empresa = get_object_or_404(Empresa, pk=pk)

    if request.method == 'POST':
        form = EmpresaForm(request.POST, instance=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Empresa atualizada com sucesso!')
            return redirect('ERP_ServicesBI:empresa_list')
    else:
        form = EmpresaForm(instance=empresa)

    return render(request, 'cadastro/empresa_form.html', {
        'form': form,
        'titulo': 'Editar Empresa',
        'action': 'Salvar Alterações',
        'empresa': empresa
    })


@login_required
def empresa_delete(request, pk):
    """Excluir empresa"""
    empresa = get_object_or_404(Empresa, pk=pk)

    if request.method == 'POST':
        empresa.delete()
        messages.success(request, 'Empresa excluída com sucesso!')
        return redirect('ERP_ServicesBI:empresa_list')

    return render(request, 'cadastro/empresa_confirm_delete.html', {
        'empresa': empresa
    })


# =============================================================================
# 3. CADASTRO > FORNECEDORES (CRUD COMPLETO)
# =============================================================================

@login_required
def fornecedor_list(request):
    """Lista de fornecedores com paginação avançada (25/50 itens)"""
    search = request.GET.get('search', '')
    fornecedores = Fornecedor.objects.filter(ativo=True).order_by('nome_razao_social')

    if search:
        fornecedores = fornecedores.filter(
            Q(nome_razao_social__icontains=search) |
            Q(nome_fantasia__icontains=search) |
            Q(cpf_cnpj__icontains=search)
        )

    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [25, 50]:
            per_page = 25
    except ValueError:
        per_page = 25

    paginator = Paginator(fornecedores, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'cadastro/fornecedor_list.html', {
        'fornecedores': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'search': search,
        'per_page': per_page,
        'total': paginator.count,
    })


@login_required
def fornecedor_add(request):
    """Adicionar novo fornecedor"""
    if request.method == 'POST':
        form = FornecedorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fornecedor cadastrado com sucesso!')
            return redirect('ERP_ServicesBI:fornecedor_list')
    else:
        form = FornecedorForm()

    return render(request, 'cadastro/fornecedor_form.html', {
        'form': form,
        'titulo': 'Novo Fornecedor',
        'action': 'Adicionar'
    })


@login_required
def fornecedor_edit(request, pk):
    """Editar fornecedor existente"""
    fornecedor = get_object_or_404(Fornecedor, pk=pk)

    if request.method == 'POST':
        form = FornecedorForm(request.POST, instance=fornecedor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fornecedor atualizado com sucesso!')
            return redirect('ERP_ServicesBI:fornecedor_list')
    else:
        form = FornecedorForm(instance=fornecedor)

    return render(request, 'cadastro/fornecedor_form.html', {
        'form': form,
        'titulo': 'Editar Fornecedor',
        'action': 'Salvar Alterações',
        'fornecedor': fornecedor
    })


@login_required
def fornecedor_delete(request, pk):
    """Excluir fornecedor - com soft delete se estiver em uso"""
    from django.db.models import ProtectedError
    
    fornecedor = get_object_or_404(Fornecedor, pk=pk)

    if request.method == 'POST':
        try:
            # Tenta excluir fisicamente
            fornecedor.delete()
            messages.success(request, 'Fornecedor excluído com sucesso!')
            
        except ProtectedError:
            # Se não pode excluir, faz SOFT DELETE (desativa)
            fornecedor.ativo = False
            fornecedor.save()
            messages.warning(request, 
                f'O fornecedor "{fornecedor.nome_razao_social}" não pode ser excluído '
                f'porque está em uso. Ele foi desativado.'
            )
        
        return redirect('ERP_ServicesBI:fornecedor_list')

    return render(request, 'cadastro/fornecedor_confirm_delete.html', {
        'fornecedor': fornecedor
    })
# =============================================================================
# 4. CADASTRO > CATEGORIAS (CRUD COMPLETO + AJAX)
# =============================================================================

@login_required
def categoria_list(request):
    """Lista de categorias com paginação avançada (25/50 itens)"""
    search = request.GET.get('search', '')
    categorias = Categoria.objects.all().order_by('nome')

    if search:
        categorias = categorias.filter(
            Q(nome__icontains=search) |
            Q(descricao__icontains=search)
        )

    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [25, 50]:
            per_page = 25
    except ValueError:
        per_page = 25

    paginator = Paginator(categorias, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'cadastro/categoria_list.html', {
        'categorias': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'search': search,
        'per_page': per_page,
        'total': paginator.count,
    })


@login_required
def categoria_add(request):
    """Adicionar nova categoria"""
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoria cadastrada com sucesso!')
            return redirect('ERP_ServicesBI:categoria_list')
    else:
        form = CategoriaForm()

    return render(request, 'cadastro/categoria_form.html', {
        'form': form,
        'titulo': 'Nova Categoria',
        'action': 'Adicionar'
    })


@login_required
def categoria_edit(request, pk):
    """Editar categoria existente"""
    categoria = get_object_or_404(Categoria, pk=pk)

    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoria atualizada com sucesso!')
            return redirect('ERP_ServicesBI:categoria_list')
    else:
        form = CategoriaForm(instance=categoria)

    return render(request, 'cadastro/categoria_form.html', {
        'form': form,
        'titulo': 'Editar Categoria',
        'action': 'Salvar Alterações',
        'categoria': categoria
    })


@login_required
def categoria_delete(request, pk):
    """Excluir categoria"""
    categoria = get_object_or_404(Categoria, pk=pk)

    if request.method == 'POST':
        categoria.delete()
        messages.success(request, 'Categoria excluída com sucesso!')
        return redirect('ERP_ServicesBI:categoria_list')

    return render(request, 'cadastro/categoria_confirm_delete.html', {
        'categoria': categoria
    })


@csrf_exempt
@login_required
def categoria_create_ajax(request):
    """
    Criar categoria via AJAX - VERSÃO CORRIGIDA
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método não permitido'}, status=405)
    
    # Tenta pegar dados do POST (FormData)
    nome = request.POST.get('nome', '').strip()
    descricao = request.POST.get('descricao', '').strip()
    
    # Se não achou no POST, tenta JSON
    if not nome and request.body:
        try:
            data = json.loads(request.body.decode('utf-8'))
            nome = data.get('nome', '').strip()
            descricao = data.get('descricao', '').strip()
        except:
            pass
    
    # Validação
    if not nome:
        return JsonResponse({
            'success': False,
            'error': 'Nome da categoria é obrigatório'
        }, status=400)
    
    # Verifica duplicidade
    if Categoria.objects.filter(nome__iexact=nome).exists():
        return JsonResponse({
            'success': False,
            'error': 'Já existe uma categoria com este nome'
        }, status=400)
    
    # Cria
    try:
        categoria = Categoria.objects.create(nome=nome, descricao=descricao)
        return JsonResponse({
            'success': True,
            'categoria': {
                'id': categoria.id,
                'nome': categoria.nome,
                'descricao': categoria.descricao
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao criar categoria: {str(e)}'
        }, status=500)


# =============================================================================
# 5. CADASTRO > PRODUTOS (CRUD COMPLETO + API JSON)
# =============================================================================

@login_required
def produto_list(request):
    """Lista de produtos com paginação avançada (25/50 itens) e filtros"""
    search = request.GET.get('search', '')
    categoria_id = request.GET.get('categoria', '')
    
    produtos = Produto.objects.filter(ativo=True).order_by('descricao')
    
    if search:
        produtos = produtos.filter(
            Q(descricao__icontains=search) |
            Q(codigo__icontains=search))
        
    
    if categoria_id:
        produtos = produtos.filter(categoria_id=categoria_id)
    
    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [25, 50]:
            per_page = 25
    except ValueError:
        per_page = 25
    
    paginator = Paginator(produtos, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Lista de categorias para o filtro
    categorias = Categoria.objects.all().order_by('nome')
    
    return render(request, 'cadastro/produto_list.html', {
        'produtos': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'search': search,
        'categoria_id': categoria_id,
        'categorias': categorias,
        'per_page': per_page,
        'total': paginator.count,
    })


@login_required
def produto_add(request):
    """Adicionar novo produto"""
    if request.method == 'POST':
        form = ProdutoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produto cadastrado com sucesso!')
            return redirect('ERP_ServicesBI:produto_list')
    else:
        form = ProdutoForm()
    
    # Categorias e fornecedores para os selects
    categorias = Categoria.objects.all().order_by('nome')
    fornecedores = Fornecedor.objects.all().order_by('nome_razao_social')
    
    return render(request, 'cadastro/produto_form.html', {
        'form': form,
        'titulo': 'Novo Produto',
        'action': 'Adicionar',
        'categorias': categorias,
        'fornecedores': fornecedores
    })



@login_required
def produto_edit(request, pk):
    """Editar produto existente"""
    produto = get_object_or_404(Produto, pk=pk)
    
    if request.method == 'POST':
        form = ProdutoForm(request.POST, instance=produto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produto atualizado com sucesso!')
            return redirect('ERP_ServicesBI:produto_list')
    else:
        form = ProdutoForm(instance=produto)
    
    # Categorias e fornecedores para os selects
    categorias = Categoria.objects.all().order_by('nome')
    fornecedores = Fornecedor.objects.all().order_by('nome_razao_social')
    
    return render(request, 'cadastro/produto_form.html', {
        'form': form,
        'titulo': 'Editar Produto',
        'action': 'Salvar Alterações',
        'produto': produto,
        'categorias': categorias,
        'fornecedores': fornecedores
    })

@login_required
def produto_delete(request, pk):
    """Excluir produto - com soft delete se estiver em uso"""
    from django.db.models import ProtectedError
    
    produto = get_object_or_404(Produto, pk=pk)
    
    if request.method == 'POST':
        try:
            # Tenta excluir fisicamente
            produto.delete()
            messages.success(request, 'Produto excluído com sucesso!')
            
        except ProtectedError:
            # Se não pode excluir, faz SOFT DELETE (desativa)
            produto.ativo = False
            produto.save()
            messages.warning(request, 
                f'O produto "{produto.descricao}" não pode ser excluído '
                f'porque está em uso. Ele foi desativado.'
            )
        
        return redirect('ERP_ServicesBI:produto_list')
    
    return render(request, 'cadastro/produto_confirm_delete.html', {
        'produto': produto
    })


@login_required
def produto_json(request):
    """API JSON para busca de produtos (autocomplete, etc)"""
    termo = request.GET.get('q', '').strip()
    categoria_id = request.GET.get('categoria', '')
    
    produtos = Produto.objects.all()
    
    if termo:
        produtos = produtos.filter(
            Q(descricao__icontains=termo) |
            Q(codigo__icontains=termo)
        )
    
    if categoria_id:
        produtos = produtos.filter(categoria_id=categoria_id)
    
    # Limitar resultados para performance
    produtos = produtos[:50]
    
    data = []
    for produto in produtos:
        data.append({
            'id': produto.id,
            'codigo': produto.codigo,
            'descricao': produto.descricao,
            'categoria': produto.categoria.nome if produto.categoria else None,
            'categoria_id': produto.categoria_id,
            'unidade': produto.unidade,
            'preco_venda': str(produto.preco_venda) if produto.preco_venda else None,
            'preco_custo': str(produto.preco_custo) if produto.preco_custo else None,
            'estoque_atual': produto.estoque_atual if hasattr(produto, 'estoque_atual') else None,
        })
    
    return JsonResponse({'produtos': data})


# =============================================================================
# AJAX: EXCLUIR CATEGORIA (USADO NO FORM DE PRODUTO)
# =============================================================================

@login_required
def categoria_delete_ajax(request, pk):
    """Excluir categoria via AJAX com verificação de uso em produtos"""
    categoria = get_object_or_404(Categoria, pk=pk)
    
    # Verifica se há produtos usando esta categoria
    if Produto.objects.filter(categoria=categoria).exists():
        return JsonResponse({
            'success': False,
            'error': 'Não é possível excluir. Esta categoria está sendo usada em produtos.'
        }, status=400)
    
    categoria.delete()
    return JsonResponse({'success': True})


# ================================================================================================================================================================

# MÓDULO: COMPRAS
# -----------------------------------------------------------------------------
# COMPRAS > COTAÇÕES
# -----------------------------------------------------------------------------

# =============================================================================
# COMPRAS > COTAÇÕES
# =============================================================================

@login_required
def cotacao_list(request):
    """Lista de cotações com paginação avançada (25/50 itens)"""
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    cotacoes = Cotacao.objects.all().order_by('-data_solicitacao')
    
    if search:
        cotacoes = cotacoes.filter(
            Q(numero__icontains=search) |
            Q(fornecedor__nome_razao_social__icontains=search)
        )
    
    if status:
        cotacoes = cotacoes.filter(status=status)
    
    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [25, 50]:
            per_page = 25
    except ValueError:
        per_page = 25
    
    paginator = Paginator(cotacoes, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'compras/cotacao_list.html', {
        'cotacoes': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'search': search,
        'status': status,
        'per_page': per_page,
        'total': paginator.count,
        'status_choices': Cotacao.STATUS_CHOICES if hasattr(Cotacao, 'STATUS_CHOICES') else [],
    })


@login_required
def cotacao_add(request):
    """Adicionar nova cotação"""
    if request.method == 'POST':
        form = CotacaoForm(request.POST)
        if form.is_valid():
            cotacao = form.save()
            messages.success(request, 'Cotação criada com sucesso!')
            return redirect('ERP_ServicesBI:cotacao_edit', pk=cotacao.pk)
    else:
        form = CotacaoForm()
    
    return render(request, 'compras/cotacao_form.html', {
        'form': form, 
        'cotacao': None,
        'titulo': 'Nova Cotação'
    })


@login_required
def cotacao_edit(request, pk):
    """Editar cotação - processa ações de itens separadamente"""
    cotacao = get_object_or_404(Cotacao, pk=pk)
    
    # AÇÃO: Adicionar item (vem do form inline no template)
    if request.method == 'POST' and request.POST.get('action') == 'add_item':
        produto_id = request.POST.get('produto')
        quantidade = request.POST.get('quantidade')
        preco_unitario = request.POST.get('preco_unitario', '0')
        
        if produto_id and quantidade:
            try:
                # Converter preço: remove pontos de milhar, troca vírgula por ponto
                preco_limpo = preco_unitario.replace('.', '').replace(',', '.')
                preco_decimal = Decimal(preco_limpo) if preco_limpo else Decimal('0')
                
                ItemCotacao.objects.create(
                    cotacao=cotacao,
                    produto_id=produto_id,
                    quantidade=Decimal(quantidade),
                    preco_unitario=preco_decimal
                )
                cotacao.calcular_total()
                messages.success(request, 'Item adicionado com sucesso!')
            except Exception as e:
                messages.error(request, f'Erro ao adicionar item: {str(e)}')
        else:
            messages.error(request, 'Preencha produto e quantidade.')
        
        return redirect('ERP_ServicesBI:cotacao_edit', pk=cotacao.pk)
    
    # AÇÃO: Remover item individual
    elif request.method == 'POST' and request.POST.get('action') == 'remove_item':
        item_id = request.POST.get('item_id')
        if item_id:
            try:
                item = ItemCotacao.objects.get(pk=item_id, cotacao=cotacao)
                item.delete()
                cotacao.calcular_total()
                messages.success(request, 'Item removido com sucesso!')
            except ItemCotacao.DoesNotExist:
                messages.error(request, 'Item não encontrado.')
        return redirect('ERP_ServicesBI:cotacao_edit', pk=cotacao.pk)
    
    # AÇÃO: Remover múltiplos itens (lote)
    elif request.method == 'POST' and request.POST.get('action') == 'remove_items_lote':
        itens_ids = request.POST.get('itens_ids', '')
        if itens_ids:
            ids_list = [int(id.strip()) for id in itens_ids.split(',') if id.strip().isdigit()]
            if ids_list:
                itens_removidos = ItemCotacao.objects.filter(
                    pk__in=ids_list, 
                    cotacao=cotacao
                ).delete()[0]
                cotacao.calcular_total()
                messages.success(request, f'{itens_removidos} item(s) removido(s) com sucesso!')
        return redirect('ERP_ServicesBI:cotacao_edit', pk=cotacao.pk)
    
    # AÇÃO: Atualizar cotação (form principal)
    elif request.method == 'POST':
        form = CotacaoForm(request.POST, instance=cotacao)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cotação atualizada com sucesso!')
            return redirect('ERP_ServicesBI:cotacao_list')
        else:
            messages.error(request, 'Corrija os erros no formulário.')
    else:
        form = CotacaoForm(instance=cotacao)
    
    return render(request, 'compras/cotacao_form.html', {
        'form': form, 
        'cotacao': cotacao,
        'itens': cotacao.itens.select_related('produto').all(),
        'produtos': Produto.objects.filter(ativo=True).order_by('descricao'),
        'titulo': f'Cotação #{cotacao.numero}'
    })


@login_required
def cotacao_item_add(request, cotacao_pk):
    """Adicionar item à cotação - View separada (alternativa ao inline)"""
    cotacao = get_object_or_404(Cotacao, pk=cotacao_pk)
    
    if request.method == 'POST':
        form = ItemCotacaoForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.cotacao = cotacao
            item.save()
            cotacao.calcular_total()
            messages.success(request, 'Item adicionado com sucesso!')
            return redirect('ERP_ServicesBI:cotacao_edit', pk=cotacao.pk)
    else:
        form = ItemCotacaoForm()
    
    return render(request, 'compras/cotacao_item_form.html', {
        'form': form,
        'cotacao': cotacao,
        'titulo': 'Adicionar Item'
    })


@login_required
def cotacao_item_edit(request, cotacao_pk, item_pk):
    """Editar item da cotação - usa mesmo template de adicionar"""
    cotacao = get_object_or_404(Cotacao, pk=cotacao_pk)
    item = get_object_or_404(ItemCotacao, pk=item_pk, cotacao=cotacao)
    
    if request.method == 'POST':
        quantidade = request.POST.get('quantidade')
        preco_unitario = request.POST.get('preco_unitario', '0')
        
        if quantidade:
            try:
                preco_limpo = preco_unitario.replace('.', '').replace(',', '.')
                preco_decimal = Decimal(preco_limpo) if preco_limpo else Decimal('0')
                
                item.quantidade = Decimal(quantidade)
                item.preco_unitario = preco_decimal
                item.save()
                cotacao.calcular_total()
                
                messages.success(request, 'Item atualizado com sucesso!')
                return redirect('ERP_ServicesBI:cotacao_edit', pk=cotacao_pk)
            except Exception as e:
                messages.error(request, f'Erro ao atualizar item: {str(e)}')
        else:
            messages.error(request, 'Quantidade é obrigatória.')
        
        return redirect('ERP_ServicesBI:cotacao_edit', pk=cotacao_pk)
    
    # Usa o mesmo template de adicionar
    return render(request, 'compras/cotacao_item_form.html', {
        'cotacao': cotacao,
        'item': item,
        'produtos': Produto.objects.filter(ativo=True).order_by('descricao'),  # Para compatibilidade
        'titulo': f'Editar Item - {item.produto.descricao[:30]}'
    })


@login_required
def cotacao_item_delete(request, cotacao_pk, item_pk):
    """Excluir item da cotação"""
    cotacao = get_object_or_404(Cotacao, pk=cotacao_pk)
    item = get_object_or_404(ItemCotacao, pk=item_pk, cotacao=cotacao)
    
    if request.method == 'POST':
        item.delete()
        cotacao.calcular_total()
        messages.success(request, 'Item removido com sucesso!')
    
    return redirect('ERP_ServicesBI:cotacao_edit', pk=cotacao.pk)


@login_required
def cotacao_gerar_pedido(request, pk):
    """Gerar pedido de compra a partir de cotação aprovada"""
    cotacao = get_object_or_404(Cotacao, pk=pk)
    
    # Verifica se já foi convertida
    if cotacao.status == 'convertida':
        messages.warning(request, 'Esta cotação já foi convertida em pedido!')
        pedido_existente = PedidoCompra.objects.filter(cotacao_origem=cotacao).first()
        if pedido_existente:
            return redirect('ERP_ServicesBI:pedidocompra_edit', pk=pedido_existente.pk)
        return redirect('ERP_ServicesBI:cotacao_edit', pk=pk)
    
    if cotacao.status != 'aprovada':
        messages.error(request, 'A cotação precisa estar aprovada para gerar pedido!')
        return redirect('ERP_ServicesBI:cotacao_edit', pk=pk)
    
    # Verifica se tem itens
    if not cotacao.itens.exists():
        messages.error(request, 'A cotação precisa ter pelo menos um item!')
        return redirect('ERP_ServicesBI:cotacao_edit', pk=pk)
    
    with transaction.atomic():
        pedido = PedidoCompra.objects.create(
            fornecedor=cotacao.fornecedor,
            cotacao_origem=cotacao,
            data_prevista_entrega=timezone.now().date() + timezone.timedelta(days=7),
            status='pendente',
            valor_total=cotacao.valor_total
        )
        
        for item_cot in cotacao.itens.all():
            ItemPedidoCompra.objects.create(
                pedido=pedido,
                produto=item_cot.produto,
                quantidade=item_cot.quantidade,
                preco_unitario=item_cot.preco_unitario,
                subtotal=item_cot.subtotal
            )
        
        cotacao.status = 'convertida'
        cotacao.save()
    
    messages.success(request, f'Pedido #{pedido.numero} gerado com sucesso!')
    return redirect('ERP_ServicesBI:pedidocompra_edit', pk=pedido.pk)


@login_required
def cotacao_delete(request, pk):
    """Excluir cotação"""
    cotacao = get_object_or_404(Cotacao, pk=pk)
    
    # Não permite excluir cotações convertidas
    if cotacao.status == 'convertida':
        messages.error(request, 'Não é possível excluir cotação já convertida em pedido!')
        return redirect('ERP_ServicesBI:cotacao_edit', pk=pk)
    
    if request.method == 'POST':
        cotacao.delete()
        messages.success(request, 'Cotação excluída com sucesso!')
        return redirect('ERP_ServicesBI:cotacao_list')
    
    return render(request, 'compras/cotacao_confirm_delete.html', {
        'cotacao': cotacao
    })


# -----------------------------------------------------------------------------
# COMPRAS > PEDIDOS DE COMPRA
# -----------------------------------------------------------------------------

@login_required
def pedidocompra_list(request):
    """Lista de pedidos de compra com paginação avançada (25/50 itens)"""
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    pedidos = PedidoCompra.objects.all().order_by('-data_pedido')
    
    if search:
        pedidos = pedidos.filter(
            Q(numero__icontains=search) |
            Q(fornecedor__nome_razao_social__icontains=search)
        )
    
    if status:
        pedidos = pedidos.filter(status=status)
    
    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [25, 50]:
            per_page = 25
    except ValueError:
        per_page = 25
    
    paginator = Paginator(pedidos, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'compras/pedido_compra_list.html', {
        'pedidos': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'search': search,
        'status': status,
        'per_page': per_page,
        'total': paginator.count,
        'status_choices': PedidoCompra.STATUS_CHOICES if hasattr(PedidoCompra, 'STATUS_CHOICES') else [],
    })


@login_required
def pedidocompra_add(request):
    """Adicionar novo pedido de compra"""
    if request.method == 'POST':
        form = PedidoCompraForm(request.POST)
        if form.is_valid():
            pedido = form.save()
            messages.success(request, 'Pedido criado com sucesso!')
            return redirect('ERP_ServicesBI:pedidocompra_edit', pk=pedido.pk)
    else:
        form = PedidoCompraForm()
    
    return render(request, 'compras/pedido_compra_form.html', {
        'form': form,
        'titulo': 'Novo Pedido'
    })

@login_required
def pedidocompra_edit(request, pk):
    """Editar pedido de compra"""
    pedido = get_object_or_404(PedidoCompra, pk=pk)
    
    # AÇÃO: Adicionar item
    if request.method == 'POST' and request.POST.get('action') == 'add_item':
        produto_id = request.POST.get('produto')
        quantidade = request.POST.get('quantidade')
        preco_unitario = request.POST.get('preco_unitario', '0')
        
        if produto_id and quantidade:
            try:
                preco_limpo = preco_unitario.replace('.', '').replace(',', '.')
                preco_decimal = Decimal(preco_limpo) if preco_limpo else Decimal('0')
                
                ItemPedidoCompra.objects.create(
                    pedido=pedido,
                    produto_id=produto_id,
                    quantidade=Decimal(quantidade),
                    preco_unitario=preco_decimal,
                    preco_total=Decimal(quantidade) * preco_decimal
                )
                pedido.calcular_total()
                messages.success(request, 'Item adicionado com sucesso!')
            except Exception as e:
                messages.error(request, f'Erro ao adicionar item: {str(e)}')
        else:
            messages.error(request, 'Preencha produto e quantidade.')
        
        return redirect('ERP_ServicesBI:pedidocompra_edit', pk=pedido.pk)
    
    # AÇÃO: Remover item individual
    elif request.method == 'POST' and request.POST.get('action') == 'remove_item':
        item_id = request.POST.get('item_id')
        if item_id:
            try:
                item = ItemPedidoCompra.objects.get(pk=item_id, pedido=pedido)
                item.delete()
                pedido.calcular_total()
                messages.success(request, 'Item removido com sucesso!')
            except ItemPedidoCompra.DoesNotExist:
                messages.error(request, 'Item não encontrado.')
        return redirect('ERP_ServicesBI:pedidocompra_edit', pk=pedido.pk)
    
    # AÇÃO: Remover múltiplos itens (lote)
    elif request.method == 'POST' and request.POST.get('action') == 'remove_items_lote':
        itens_ids = request.POST.get('itens_ids', '')
        if itens_ids:
            ids_list = [int(id.strip()) for id in itens_ids.split(',') if id.strip().isdigit()]
            if ids_list:
                itens_removidos = ItemPedidoCompra.objects.filter(
                    pk__in=ids_list, 
                    pedido=pedido
                ).delete()[0]
                pedido.calcular_total()
                messages.success(request, f'{itens_removidos} item(s) removido(s) com sucesso!')
        return redirect('ERP_ServicesBI:pedidocompra_edit', pk=pedido.pk)
    
    # AÇÃO: Atualizar pedido (form principal)
    elif request.method == 'POST':
        form = PedidoCompraForm(request.POST, instance=pedido)
        if form.is_valid():
            form.save()
            messages.success(request, 'Pedido atualizado com sucesso!')
            return redirect('ERP_ServicesBI:pedidocompra_list')
        else:
            messages.error(request, 'Corrija os erros no formulário.')
    else:
        form = PedidoCompraForm(instance=pedido)
    
    return render(request, 'compras/pedido_compra_form.html', {
        'form': form,
        'pedido': pedido,
        'itens': pedido.itens.select_related('produto').all(),
        'produtos': Produto.objects.filter(ativo=True).order_by('descricao'),
        'titulo': f'Pedido #{pedido.numero}'
    })


@login_required
def pedidocompra_item_add(request, pedido_pk):
    """Adicionar item ao pedido de compra"""
    pedido = get_object_or_404(PedidoCompra, pk=pedido_pk)
    
    if request.method == 'POST':
        form = ItemPedidoCompraForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.pedido = pedido
            item.subtotal = item.quantidade * item.preco_unitario
            item.save()
            pedido.calcular_total()
            messages.success(request, 'Item adicionado com sucesso!')
            return redirect('ERP_ServicesBI:pedidocompra_edit', pk=pedido.pk)
    else:
        form = ItemPedidoCompraForm()
    
    return render(request, 'compras/pedido_compra_item_form.html', {
        'form': form,
        'pedido': pedido,
        'titulo': 'Adicionar Item'
    })

@login_required
def pedidocompra_item_edit(request, pedido_pk, item_pk):
    """Editar item do pedido de compra"""
    pedido = get_object_or_404(PedidoCompra, pk=pedido_pk)
    item = get_object_or_404(ItemPedidoCompra, pk=item_pk, pedido=pedido)
    
    if request.method == 'POST':
        form = ItemPedidoCompraForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save(commit=False)
            item.subtotal = item.quantidade * item.preco_unitario
            item.save()
            pedido.calcular_total()
            messages.success(request, 'Item atualizado com sucesso!')
            return redirect('ERP_ServicesBI:pedidocompra_edit', pk=pedido.pk)
    else:
        form = ItemPedidoCompraForm(instance=item)
    
    return render(request, 'compras/pedido_compra_item_form.html', {
        'form': form,
        'pedido': pedido,
        'item': item,
        'titulo': 'Editar Item'
    })

@login_required
def pedidocompra_item_delete(request, pk):
    """Excluir item do pedido de compra"""
    item = get_object_or_404(ItemPedidoCompra, pk=pk)
    pedido_pk = item.pedido.pk
    item.delete()
    item.pedido.calcular_total()
    messages.success(request, 'Item removido com sucesso!')
    return redirect('ERP_ServicesBI:pedidocompra_edit', pk=pedido_pk)


@login_required
def pedidocompra_gerar_nfe(request, pk):
    """Gerar nota fiscal de entrada a partir de pedido de compra"""
    pedido = get_object_or_404(PedidoCompra, pk=pk)
    
    if pedido.status not in ['aprovado', 'parcial']:
        messages.error(request, 'O pedido precisa estar aprovado para gerar nota fiscal!')
        return redirect('ERP_ServicesBI:pedidocompra_edit', pk=pk)
    
    with transaction.atomic():
        nota = NotaFiscalEntrada.objects.create(
            fornecedor=pedido.fornecedor,
            pedido_origem=pedido,
            data_entrada=timezone.now().date(),
            valor_total=pedido.valor_total
        )
        
        for item_ped in pedido.itens.all():
            ItemNotaFiscalEntrada.objects.create(
                nota=nota,
                produto=item_ped.produto,
                quantidade=item_ped.quantidade,
                valor_unitario=item_ped.preco_unitario,
                valor_total=item_ped.subtotal
            )
        
        pedido.status = 'convertido'
        pedido.save()
    
    messages.success(request, f'Nota Fiscal #{nota.numero} gerada com sucesso!')
    return redirect('ERP_ServicesBI:notafiscalentrada_edit', pk=nota.pk)


@login_required
def pedidocompra_delete(request, pk):
    """Excluir pedido de compra"""
    pedido = get_object_or_404(PedidoCompra, pk=pk)
    if request.method == 'POST':
        pedido.delete()
        messages.success(request, 'Pedido excluído com sucesso!')
        return redirect('ERP_ServicesBI:pedidocompra_list')
    return render(request, 'compras/pedido_compra_confirm_delete.html', {
        'pedido': pedido
    })
# -----------------------------------------------------------------------------
# COMPRAS > NOTAS FISCAIS DE ENTRADA
# -----------------------------------------------------------------------------

@login_required
def notafiscalentrada_list(request):
    """Lista de notas fiscais de entrada com paginação avançada (25/50 itens)"""
    search = request.GET.get('search', '')
    
    notas = NotaFiscalEntrada.objects.all().order_by('-data_entrada')
    
    if search:
        notas = notas.filter(
            Q(numero__icontains=search) |
            Q(fornecedor__nome_razao_social__icontains=search) |
            Q(chave_acesso__icontains=search)
        )
    
    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [25, 50]:
            per_page = 25
    except ValueError:
        per_page = 25
    
    paginator = Paginator(notas, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'compras/nota_fiscal_entrada_list.html', {
        'notas': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'search': search,
        'per_page': per_page,
        'total': paginator.count,
    })


@login_required
def notafiscalentrada_add(request):
    """Adicionar nova nota fiscal de entrada"""
    if request.method == 'POST':
        form = NotaFiscalEntradaForm(request.POST)
        if form.is_valid():
            nota = form.save()
            messages.success(request, 'Nota Fiscal criada com sucesso!')
            return redirect('ERP_ServicesBI:notafiscalentrada_edit', pk=nota.pk)
    else:
        form = NotaFiscalEntradaForm()
    return render(request, 'compras/nota_fiscal_entrada_form.html', {
        'form': form, 
        'titulo': 'Nova Nota Fiscal'
    })


@login_required
def notafiscalentrada_edit(request, pk):
    """Editar nota fiscal de entrada"""
    nota = get_object_or_404(NotaFiscalEntrada, pk=pk)
    itens = nota.itens.all()
    status_anterior = nota.status

    if request.method == 'POST':
        form = NotaFiscalEntradaForm(request.POST, instance=nota)
        if form.is_valid():
            nota_salva = form.save()
            # Integração: ao confirmar NF de entrada, atualiza estoque e gera conta a pagar
            if status_anterior != 'confirmada' and nota_salva.status == 'confirmada':
                try:
                    with transaction.atomic():
                        nota_salva.atualizar_estoque()
                        # Gera conta a pagar automaticamente
                        ContaPagar.objects.create(
                            descricao=f'NF Entrada {nota_salva.numero_nf} - {nota_salva.fornecedor.nome_razao_social}',
                            fornecedor=nota_salva.fornecedor,
                            nota_fiscal=nota_salva,
                            data_vencimento=timezone.now().date() + timedelta(days=30),
                            valor_original=nota_salva.valor_total,
                            valor=nota_salva.valor_total,
                            status='pendente'
                        )
                    messages.success(request, 'Nota Fiscal confirmada! Estoque e Contas a Pagar atualizados.')
                except Exception as e:
                    messages.warning(request, f'NF salva, mas erro na integração: {e}')
            else:
                messages.success(request, 'Nota Fiscal atualizada com sucesso!')
            return redirect('ERP_ServicesBI:notafiscalentrada_list')
    else:
        form = NotaFiscalEntradaForm(instance=nota)

    return render(request, 'compras/nota_fiscal_entrada_form.html', {
        'form': form,
        'nota': nota,
        'itens': itens,
        'titulo': f'Nota Fiscal #{nota.numero}'
    })


@login_required
def notafiscalentrada_item_add(request, nota_pk):
    """Adicionar item à nota fiscal de entrada"""
    nota = get_object_or_404(NotaFiscalEntrada, pk=nota_pk)
    
    if request.method == 'POST':
        form = ItemNotaFiscalEntradaForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.nota = nota
            item.valor_total = item.quantidade * item.valor_unitario
            item.save()
            nota.calcular_total()
            messages.success(request, 'Item adicionado com sucesso!')
            return redirect('ERP_ServicesBI:notafiscalentrada_edit', pk=nota.pk)
    else:
        form = ItemNotaFiscalEntradaForm()
    
    return render(request, 'compras/nota_fiscal_entrada_item_form.html', {
        'form': form,
        'nota': nota,
        'titulo': 'Adicionar Item'
    })


@login_required
def notafiscalentrada_item_delete(request, pk):
    """Excluir item da nota fiscal de entrada"""
    item = get_object_or_404(ItemNotaFiscalEntrada, pk=pk)
    nota_pk = item.nota.pk
    item.delete()
    item.nota.calcular_total()
    messages.success(request, 'Item removido com sucesso!')
    return redirect('ERP_ServicesBI:notafiscalentrada_edit', pk=nota_pk)


@login_required
def notafiscalentrada_delete(request, pk):
    """Excluir nota fiscal de entrada"""
    nota = get_object_or_404(NotaFiscalEntrada, pk=pk)
    if request.method == 'POST':
        nota.delete()
        messages.success(request, 'Nota Fiscal excluída com sucesso!')
        return redirect('ERP_ServicesBI:notafiscalentrada_list')
    return render(request, 'compras/nota_fiscal_entrada_confirm_delete.html', {
        'nota': nota
    })
# =============================================================================
# RELATÓRIOS - COMPRAS
# =============================================================================

@login_required
def relatorio_compras(request):
    """Relatório de compras com dados completos para gráficos"""
    from django.db.models import Count  # Adicionar import se não tiver
    
    # Filtros
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    fornecedor_id = request.GET.get('fornecedor', '')
    
    notas = NotaFiscalEntrada.objects.select_related('fornecedor').prefetch_related('itens').all()
    
    if data_inicio:
        notas = notas.filter(data_entrada__gte=data_inicio)
    if data_fim:
        notas = notas.filter(data_entrada__lte=data_fim)
    if fornecedor_id:
        notas = notas.filter(fornecedor_id=fornecedor_id)
    
    # Totais
    total_compras = notas.aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')
    total_nfs = notas.count()
    ticket_medio = total_compras / total_nfs if total_nfs > 0 else Decimal('0.00')
    fornecedores_ativos = notas.values('fornecedor').distinct().count()
    
    # Comparação com período anterior (para variações)
    # Calcular período anterior do mesmo tamanho
    if data_inicio and data_fim:
        from datetime import datetime, timedelta
        dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
        dt_fim = datetime.strptime(data_fim, '%Y-%m-%d')
        dias = (dt_fim - dt_inicio).days
        
        periodo_ant_inicio = (dt_inicio - timedelta(days=dias+1)).strftime('%Y-%m-%d')
        periodo_ant_fim = (dt_inicio - timedelta(days=1)).strftime('%Y-%m-%d')
        
        notas_ant = NotaFiscalEntrada.objects.filter(data_entrada__range=[periodo_ant_inicio, periodo_ant_fim])
        total_ant = notas_ant.aggregate(total=Sum('valor_total'))['total'] or Decimal('0.01')  # Evitar div por zero
        nfs_ant = notas_ant.count() or 1
        
        var_compras = float(((total_compras - total_ant) / total_ant) * 100) if total_ant else 0
        var_nfs = float(((total_nfs - nfs_ant) / nfs_ant) * 100) if nfs_ant else 0
    else:
        var_compras = 0
        var_nfs = 0
    
    # Dados para gráfico de linha (evolução mensal)
    from django.db.models.functions import TruncMonth
    compras_por_mes = notas.annotate(
        mes=TruncMonth('data_entrada')
    ).values('mes').annotate(
        total=Sum('valor_total'),
        qtd=Count('id')
    ).order_by('mes')
    
    meses_labels = [c['mes'].strftime('%b/%Y') if c['mes'] else '' for c in compras_por_mes]
    meses_valores = [float(c['total']) for c in compras_por_mes]
    meses_qtd = [c['qtd'] for c in compras_por_mes]
    
    # Dados para gráfico de rosca (top fornecedores)
    top_fornecedores = notas.values('fornecedor__nome_razao_social').annotate(
        total=Sum('valor_total')
    ).order_by('-total')[:5]
    
    fornecedores_labels = [f['fornecedor__nome_razao_social'][:20] for f in top_fornecedores]  # Limitar nome
    fornecedores_valores = [float(f['total']) for f in top_fornecedores]
    fornecedores_zip = zip(fornecedores_labels, fornecedores_valores)
    
    # Dados para gráfico de barras (top produtos)
    from django.db.models import F
    top_produtos = ItemNotaFiscalEntrada.objects.filter(
        nota_fiscal__in=notas
    ).values('produto__descricao').annotate(
        total=Sum(F('quantidade') * F('preco_unitario'))
    ).order_by('-total')[:5]
    
    produtos_labels = [p['produto__descricao'][:25] for p in top_produtos]
    produtos_valores = [float(p['total']) for p in top_produtos]
    
    # Lista de fornecedores para filtro
    fornecedores = Fornecedor.objects.filter(ativo=True).order_by('nome_razao_social')
    
    # Contexto completo
    context = {
        'notas': notas[:100],  # Limitar para performance
        'total_compras': total_compras,
        'total_nfs': total_nfs,
        'ticket_medio': ticket_medio,
        'fornecedores_ativos': fornecedores_ativos,
        'var_compras': var_compras,
        'var_nfs': var_nfs,
        'meses_labels': meses_labels,
        'meses_valores': meses_valores,
        'meses_qtd': meses_qtd,
        'fornecedores_zip': fornecedores_zip,
        'produtos_labels': produtos_labels,
        'produtos_valores': produtos_valores,
        'fornecedores': fornecedores,
        'filtros': {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'fornecedor': fornecedor_id,
        }
    }
    
    return render(request, 'compras/relatorio_compras.html', context)


# ================================================================================================================================================================

# MÓDULO: VENDAS
# -----------------------------------------------------------------------------
# VENDAS > ORÇAMENTOS
# -----------------------------------------------------------------------------

@login_required
def orcamento_list(request):
    """Lista de orçamentos com paginação avançada (25/50 itens)"""
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    orcamentos = Orcamento.objects.all().order_by('-data_orcamento')
    
    if search:
        orcamentos = orcamentos.filter(
            Q(numero__icontains=search) |
            Q(cliente__nome_razao_social__icontains=search)
        )
    
    if status:
        orcamentos = orcamentos.filter(status=status)
    
    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [25, 50]:
            per_page = 25
    except ValueError:
        per_page = 25
    
    paginator = Paginator(orcamentos, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'vendas/orcamento_list.html', {
        'orcamentos': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'search': search,
        'status': status,
        'per_page': per_page,
        'total': paginator.count,
        'status_choices': Orcamento.STATUS_CHOICES if hasattr(Orcamento, 'STATUS_CHOICES') else [],
    })


@login_required
def orcamento_add(request):
    """Adicionar novo orçamento"""
    if request.method == 'POST':
        form = OrcamentoForm(request.POST)
        if form.is_valid():
            orcamento = form.save()
            messages.success(request, 'Orçamento criado com sucesso!')
            return redirect('ERP_ServicesBI:orcamento_edit', pk=orcamento.pk)
    else:
        form = OrcamentoForm()
    return render(request, 'vendas/orcamento_form.html', {
        'form': form, 
        'titulo': 'Novo Orçamento'
    })


@login_required
def orcamento_edit(request, pk):
    """Editar orçamento"""
    orcamento = get_object_or_404(Orcamento, pk=pk)
    itens = orcamento.itens.all()
    
    if request.method == 'POST':
        form = OrcamentoForm(request.POST, instance=orcamento)
        if form.is_valid():
            form.save()
            messages.success(request, 'Orçamento atualizado com sucesso!')
            return redirect('ERP_ServicesBI:orcamento_list')
    else:
        form = OrcamentoForm(instance=orcamento)
    
    return render(request, 'vendas/orcamento_form.html', {
        'form': form,
        'orcamento': orcamento,
        'itens': itens,
        'titulo': f'Orçamento #{orcamento.numero}'
    })


@login_required
def orcamento_item_add(request, orcamento_pk):
    """Adicionar item ao orçamento"""
    orcamento = get_object_or_404(Orcamento, pk=orcamento_pk)
    
    if request.method == 'POST':
        form = ItemOrcamentoForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.orcamento = orcamento
            item.subtotal = item.quantidade * item.preco_unitario
            item.save()
            orcamento.calcular_total()
            messages.success(request, 'Item adicionado com sucesso!')
            return redirect('ERP_ServicesBI:orcamento_edit', pk=orcamento.pk)
    else:
        form = ItemOrcamentoForm()
    
    return render(request, 'vendas/orcamento_item_form.html', {
        'form': form,
        'orcamento': orcamento,
        'titulo': 'Adicionar Item'
    })


@login_required
def orcamento_item_delete(request, pk):
    """Excluir item do orçamento"""
    item = get_object_or_404(ItemOrcamento, pk=pk)
    orcamento_pk = item.orcamento.pk
    item.delete()
    item.orcamento.calcular_total()
    messages.success(request, 'Item removido com sucesso!')
    return redirect('ERP_ServicesBI:orcamento_edit', pk=orcamento_pk)


@login_required
def orcamento_gerar_pedido(request, pk):
    """Gerar pedido de venda a partir de orçamento aprovado"""
    orcamento = get_object_or_404(Orcamento, pk=pk)
    
    if orcamento.status != 'aprovado':
        messages.error(request, 'O orçamento precisa estar aprovado para gerar pedido!')
        return redirect('ERP_ServicesBI:orcamento_edit', pk=pk)
    
    with transaction.atomic():
        pedido = PedidoVenda.objects.create(
            cliente=orcamento.cliente,
            orcamento_origem=orcamento,
            data_prevista_entrega=timezone.now().date() + timezone.timedelta(days=7),
            status='pendente',
            valor_total=orcamento.valor_total
        )
        
        for item_orc in orcamento.itens.all():
            ItemPedidoVenda.objects.create(
                pedido=pedido,
                produto=item_orc.produto,
                quantidade=item_orc.quantidade,
                preco_unitario=item_orc.preco_unitario,
                subtotal=item_orc.subtotal
            )
        
        orcamento.status = 'convertido'
        orcamento.save()
    
    messages.success(request, f'Pedido #{pedido.numero} gerado com sucesso!')
    return redirect('ERP_ServicesBI:pedidovenda_edit', pk=pedido.pk)


@login_required
def orcamento_delete(request, pk):
    """Excluir orçamento"""
    orcamento = get_object_or_404(Orcamento, pk=pk)
    if request.method == 'POST':
        orcamento.delete()
        messages.success(request, 'Orçamento excluído com sucesso!')
        return redirect('ERP_ServicesBI:orcamento_list')
    return render(request, 'vendas/orcamento_confirm_delete.html', {
        'orcamento': orcamento
    })


# -----------------------------------------------------------------------------
# VENDAS > PEDIDOS DE VENDA
# -----------------------------------------------------------------------------

@login_required
def pedidovenda_list(request):
    """Lista de pedidos de venda com paginação avançada (25/50 itens)"""
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    pedidos = PedidoVenda.objects.all().order_by('-data_pedido')
    
    if search:
        pedidos = pedidos.filter(
            Q(numero__icontains=search) |
            Q(cliente__nome_razao_social__icontains=search)
        )
    
    if status:
        pedidos = pedidos.filter(status=status)
    
    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [25, 50]:
            per_page = 25
    except ValueError:
        per_page = 25
    
    paginator = Paginator(pedidos, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'vendas/pedido_venda_list.html', {
        'pedidos': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'search': search,
        'status': status,
        'per_page': per_page,
        'total': paginator.count,
        'status_choices': PedidoVenda.STATUS_CHOICES if hasattr(PedidoVenda, 'STATUS_CHOICES') else [],
    })


@login_required
def pedidovenda_add(request):
    """Adicionar novo pedido de venda"""
    if request.method == 'POST':
        form = PedidoVendaForm(request.POST)
        if form.is_valid():
            pedido = form.save()
            messages.success(request, 'Pedido criado com sucesso!')
            return redirect('ERP_ServicesBI:pedidovenda_edit', pk=pedido.pk)
    else:
        form = PedidoVendaForm()
    return render(request, 'vendas/pedido_venda_form.html', {
        'form': form, 
        'titulo': 'Novo Pedido'
    })


@login_required
def pedidovenda_edit(request, pk):
    """Editar pedido de venda"""
    pedido = get_object_or_404(PedidoVenda, pk=pk)
    itens = pedido.itens.all()
    
    if request.method == 'POST':
        form = PedidoVendaForm(request.POST, instance=pedido)
        if form.is_valid():
            form.save()
            messages.success(request, 'Pedido atualizado com sucesso!')
            return redirect('ERP_ServicesBI:pedidovenda_list')
    else:
        form = PedidoVendaForm(instance=pedido)
    
    return render(request, 'vendas/pedido_venda_form.html', {
        'form': form,
        'pedido': pedido,
        'itens': itens,
        'titulo': f'Pedido #{pedido.numero}'
    })


@login_required
def pedidovenda_item_add(request, pedido_pk):
    """Adicionar item ao pedido de venda"""
    pedido = get_object_or_404(PedidoVenda, pk=pedido_pk)
    
    if request.method == 'POST':
        form = ItemPedidoVendaForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.pedido = pedido
            item.subtotal = item.quantidade * item.preco_unitario
            item.save()
            pedido.calcular_total()
            messages.success(request, 'Item adicionado com sucesso!')
            return redirect('ERP_ServicesBI:pedidovenda_edit', pk=pedido.pk)
    else:
        form = ItemPedidoVendaForm()
    
    return render(request, 'vendas/pedido_venda_item_form.html', {
        'form': form,
        'pedido': pedido,
        'titulo': 'Adicionar Item'
    })


@login_required
def pedidovenda_item_delete(request, pk):
    """Excluir item do pedido de venda"""
    item = get_object_or_404(ItemPedidoVenda, pk=pk)
    pedido_pk = item.pedido.pk
    item.delete()
    item.pedido.calcular_total()
    messages.success(request, 'Item removido com sucesso!')
    return redirect('ERP_ServicesBI:pedidovenda_edit', pk=pedido_pk)


@login_required
def pedidovenda_gerar_nfe(request, pk):
    """Gerar nota fiscal de saída a partir de pedido de venda"""
    pedido = get_object_or_404(PedidoVenda, pk=pk)
    
    if pedido.status not in ['aprovado', 'parcial']:
        messages.error(request, 'O pedido precisa estar aprovado para gerar nota fiscal!')
        return redirect('ERP_ServicesBI:pedidovenda_edit', pk=pk)
    
    with transaction.atomic():
        nota = NotaFiscalSaida.objects.create(
            cliente=pedido.cliente,
            pedido_origem=pedido,
            data_emissao=timezone.now().date(),
            valor_total=pedido.valor_total
        )
        
        for item_ped in pedido.itens.all():
            ItemNotaFiscalSaida.objects.create(
                nota=nota,
                produto=item_ped.produto,
                quantidade=item_ped.quantidade,
                valor_unitario=item_ped.preco_unitario,
                valor_total=item_ped.subtotal
            )
        
        pedido.status = 'convertido'
        pedido.save()
    
    messages.success(request, f'Nota Fiscal #{nota.numero} gerada com sucesso!')
    return redirect('ERP_ServicesBI:notafiscalsaida_edit', pk=nota.pk)


@login_required
def pedidovenda_delete(request, pk):
    """Excluir pedido de venda"""
    pedido = get_object_or_404(PedidoVenda, pk=pk)
    if request.method == 'POST':
        pedido.delete()
        messages.success(request, 'Pedido excluído com sucesso!')
        return redirect('ERP_ServicesBI:pedidovenda_list')
    return render(request, 'vendas/pedido_venda_confirm_delete.html', {
        'pedido': pedido
    })


# -----------------------------------------------------------------------------
# VENDAS > NOTAS FISCAIS DE SAÍDA
# -----------------------------------------------------------------------------

@login_required
def notafiscalsaida_list(request):
    """Lista de notas fiscais de saída com paginação avançada (25/50 itens)"""
    search = request.GET.get('search', '')
    
    notas = NotaFiscalSaida.objects.all().order_by('-data_emissao')
    
    if search:
        notas = notas.filter(
            Q(numero__icontains=search) |
            Q(cliente__nome_razao_social__icontains=search) |
            Q(chave_acesso__icontains=search)
        )
    
    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [25, 50]:
            per_page = 25
    except ValueError:
        per_page = 25
    
    paginator = Paginator(notas, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'vendas/nota_fiscal_saida_list.html', {
        'notas': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'search': search,
        'per_page': per_page,
        'total': paginator.count,
    })


@login_required
def notafiscalsaida_add(request):
    """Adicionar nova nota fiscal de saída"""
    if request.method == 'POST':
        form = NotaFiscalSaidaForm(request.POST)
        if form.is_valid():
            nota = form.save()
            messages.success(request, 'Nota Fiscal criada com sucesso!')
            return redirect('ERP_ServicesBI:notafiscalsaida_edit', pk=nota.pk)
    else:
        form = NotaFiscalSaidaForm()
    return render(request, 'vendas/nota_fiscal_saida_form.html', {
        'form': form, 
        'titulo': 'Nova Nota Fiscal'
    })


@login_required
def notafiscalsaida_edit(request, pk):
    """Editar nota fiscal de saída"""
    nota = get_object_or_404(NotaFiscalSaida, pk=pk)
    itens = nota.itens.all()
    status_anterior = nota.status

    if request.method == 'POST':
        form = NotaFiscalSaidaForm(request.POST, instance=nota)
        if form.is_valid():
            nota_salva = form.save()
            # Integração: ao confirmar NF, atualiza estoque e gera conta a receber
            if status_anterior != 'confirmada' and nota_salva.status == 'confirmada':
                try:
                    with transaction.atomic():
                        nota_salva.atualizar_estoque()
                        nota_salva.gerar_contas_receber()
                    messages.success(request, 'Nota Fiscal confirmada! Estoque e Contas a Receber atualizados.')
                except Exception as e:
                    messages.warning(request, f'NF salva, mas erro na integração: {e}')
            else:
                messages.success(request, 'Nota Fiscal atualizada com sucesso!')
            return redirect('ERP_ServicesBI:notafiscalsaida_list')
    else:
        form = NotaFiscalSaidaForm(instance=nota)

    return render(request, 'vendas/nota_fiscal_saida_form.html', {
        'form': form,
        'nota': nota,
        'itens': itens,
        'titulo': f'Nota Fiscal #{nota.numero}'
    })


@login_required
def notafiscalsaida_item_add(request, nota_pk):
    """Adicionar item à nota fiscal de saída"""
    nota = get_object_or_404(NotaFiscalSaida, pk=nota_pk)
    
    if request.method == 'POST':
        form = ItemNotaFiscalSaidaForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.nota = nota
            item.valor_total = item.quantidade * item.valor_unitario
            item.save()
            nota.calcular_total()
            messages.success(request, 'Item adicionado com sucesso!')
            return redirect('ERP_ServicesBI:notafiscalsaida_edit', pk=nota.pk)
    else:
        form = ItemNotaFiscalSaidaForm()
    
    return render(request, 'vendas/nota_fiscal_saida_item_form.html', {
        'form': form,
        'nota': nota,
        'titulo': 'Adicionar Item'
    })


@login_required
def notafiscalsaida_item_delete(request, pk):
    """Excluir item da nota fiscal de saída"""
    item = get_object_or_404(ItemNotaFiscalSaida, pk=pk)
    nota_pk = item.nota.pk
    item.delete()
    item.nota.calcular_total()
    messages.success(request, 'Item removido com sucesso!')
    return redirect('ERP_ServicesBI:notafiscalsaida_edit', pk=nota_pk)


@login_required
def notafiscalsaida_delete(request, pk):
    """Excluir nota fiscal de saída"""
    nota = get_object_or_404(NotaFiscalSaida, pk=pk)
    if request.method == 'POST':
        nota.delete()
        messages.success(request, 'Nota Fiscal excluída com sucesso!')
        return redirect('ERP_ServicesBI:notafiscalsaida_list')
    return render(request, 'vendas/nota_fiscal_saida_confirm_delete.html', {
        'nota': nota
    })

# =============================================================================
# RELATÓRIOS - VENDAS
# =============================================================================

@login_required
def relatorio_vendas(request):
    """Relatório de vendas"""
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    cliente_id = request.GET.get('cliente', '')
    
    notas = NotaFiscalSaida.objects.all()
    
    if data_inicio:
        notas = notas.filter(data_emissao__gte=data_inicio)
    if data_fim:
        notas = notas.filter(data_emissao__lte=data_fim)
    if cliente_id:
        notas = notas.filter(cliente_id=cliente_id)
    
    total_vendas = notas.aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')
    
    # Gráfico por mês
    vendas_por_mes = notas.annotate(
        mes=TruncMonth('data_emissao')
    ).values('mes').annotate(
        total=Sum('valor_total')
    ).order_by('mes')
    
    clientes = Cliente.objects.all().order_by('nome_razao_social')
    
    return render(request, 'vendas/relatorio_vendas.html', {
        'notas': notas[:100],  # Limitar para performance
        'total_vendas': total_vendas,
        'vendas_por_mes': vendas_por_mes,
        'clientes': clientes,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'cliente_id': cliente_id,
    })
# ================================================================================================================================================================

# MÓDULO: FINANCEIRO
# -----------------------------------------------------------------------------
# FINANCEIRO > CATEGORIAS FINANCEIRAS
# -----------------------------------------------------------------------------

@login_required
def categoriafinanceira_list(request):
    """Lista de categorias financeiras com paginação avançada (25/50 itens)"""
    search = request.GET.get('search', '')
    tipo = request.GET.get('tipo', '')
    
    categorias = CategoriaFinanceira.objects.all().order_by('nome')
    
    if search:
        categorias = categorias.filter(
            Q(nome__icontains=search) |
            Q(descricao__icontains=search)
        )
    
    if tipo:
        categorias = categorias.filter(tipo=tipo)
    
    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [25, 50]:
            per_page = 25
    except ValueError:
        per_page = 25
    
    paginator = Paginator(categorias, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'financeiro/categoriafinanceira_list.html', {
        'categorias': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'search': search,
        'tipo': tipo,
        'per_page': per_page,
        'total': paginator.count,
    })


@login_required
def categoriafinanceira_add(request):
    """Adicionar nova categoria financeira"""
    if request.method == 'POST':
        form = CategoriaFinanceiraForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoria financeira cadastrada com sucesso!')
            return redirect('ERP_ServicesBI:categoriafinanceira_list')
    else:
        form = CategoriaFinanceiraForm()
    
    return render(request, 'financeiro/categoriafinanceira_form.html', {
        'form': form,
        'titulo': 'Nova Categoria Financeira',
        'action': 'Adicionar'
    })


@login_required
def categoriafinanceira_edit(request, pk):
    """Editar categoria financeira"""
    categoria = get_object_or_404(CategoriaFinanceira, pk=pk)
    
    if request.method == 'POST':
        form = CategoriaFinanceiraForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoria financeira atualizada com sucesso!')
            return redirect('ERP_ServicesBI:categoriafinanceira_list')
    else:
        form = CategoriaFinanceiraForm(instance=categoria)
    
    return render(request, 'financeiro/categoriafinanceira_form.html', {
        'form': form,
        'titulo': 'Editar Categoria Financeira',
        'action': 'Salvar Alterações',
        'categoria': categoria
    })


@login_required
def categoriafinanceira_delete(request, pk):
    """Excluir categoria financeira"""
    categoria = get_object_or_404(CategoriaFinanceira, pk=pk)
    
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, 'Categoria financeira excluída com sucesso!')
        return redirect('ERP_ServicesBI:categoriafinanceira_list')
    
    return render(request, 'financeiro/categoriafinanceira_confirm_delete.html', {
        'categoria': categoria
    })


# -----------------------------------------------------------------------------
# FINANCEIRO > CENTROS DE CUSTO
# -----------------------------------------------------------------------------

@login_required
def centrocusto_list(request):
    """Lista de centros de custo com paginação avançada (25/50 itens)"""
    search = request.GET.get('search', '')
    
    centros = CentroCusto.objects.all().order_by('nome')
    
    if search:
        centros = centros.filter(
            Q(nome__icontains=search) |
            Q(codigo__icontains=search)
        )
    
    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [25, 50]:
            per_page = 25
    except ValueError:
        per_page = 25
    
    paginator = Paginator(centros, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'financeiro/centrocusto_list.html', {
        'centros': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'search': search,
        'per_page': per_page,
        'total': paginator.count,
    })


@login_required
def centrocusto_add(request):
    """Adicionar novo centro de custo"""
    if request.method == 'POST':
        form = CentroCustoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Centro de custo cadastrado com sucesso!')
            return redirect('ERP_ServicesBI:centrocusto_list')
    else:
        form = CentroCustoForm()
    
    return render(request, 'financeiro/centrocusto_form.html', {
        'form': form,
        'titulo': 'Novo Centro de Custo',
        'action': 'Adicionar'
    })


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
    
    return render(request, 'financeiro/centrocusto_form.html', {
        'form': form,
        'titulo': 'Editar Centro de Custo',
        'action': 'Salvar Alterações',
        'centro': centro
    })


@login_required
def centrocusto_delete(request, pk):
    """Excluir centro de custo"""
    centro = get_object_or_404(CentroCusto, pk=pk)
    
    if request.method == 'POST':
        centro.delete()
        messages.success(request, 'Centro de custo excluído com sucesso!')
        return redirect('ERP_ServicesBI:centrocusto_list')
    
    return render(request, 'financeiro/centrocusto_confirm_delete.html', {
        'centro': centro
    })


# -----------------------------------------------------------------------------
# FINANCEIRO > CONTAS A RECEBER
# -----------------------------------------------------------------------------

@login_required
def contareceber_list(request):
    """Lista de contas a receber com paginação avançada (25/50 itens)"""
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    vencimento_de = request.GET.get('vencimento_de', '')
    vencimento_ate = request.GET.get('vencimento_ate', '')
    
    contas = ContaReceber.objects.all().order_by('data_vencimento')
    
    if search:
        contas = contas.filter(
            Q(cliente__nome_razao_social__icontains=search) |
            Q(descricao__icontains=search) |
            Q(numero_documento__icontains=search)
        )
    
    if status:
        contas = contas.filter(status=status)
    
    if vencimento_de:
        contas = contas.filter(data_vencimento__gte=vencimento_de)
    
    if vencimento_ate:
        contas = contas.filter(data_vencimento__lte=vencimento_ate)
    
    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [25, 50]:
            per_page = 25
    except ValueError:
        per_page = 25
    
    paginator = Paginator(contas, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'financeiro/contareceber_list.html', {
        'contas': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'search': search,
        'status': status,
        'vencimento_de': vencimento_de,
        'vencimento_ate': vencimento_ate,
        'per_page': per_page,
        'total': paginator.count,
    })


@login_required
def contareceber_add(request):
    """Adicionar nova conta a receber"""
    if request.method == 'POST':
        form = ContaReceberForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conta a receber cadastrada com sucesso!')
            return redirect('ERP_ServicesBI:contareceber_list')
    else:
        form = ContaReceberForm()
    
    return render(request, 'financeiro/contareceber_form.html', {
        'form': form,
        'titulo': 'Nova Conta a Receber',
        'action': 'Adicionar'
    })


@login_required
def contareceber_edit(request, pk):
    """Editar conta a receber"""
    conta = get_object_or_404(ContaReceber, pk=pk)
    
    if request.method == 'POST':
        form = ContaReceberForm(request.POST, instance=conta)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conta a receber atualizada com sucesso!')
            return redirect('ERP_ServicesBI:contareceber_list')
    else:
        form = ContaReceberForm(instance=conta)
    
    return render(request, 'financeiro/contareceber_form.html', {
        'form': form,
        'titulo': 'Editar Conta a Receber',
        'action': 'Salvar Alterações',
        'conta': conta
    })


@login_required
def contareceber_baixar(request, pk):
    """Baixar conta a receber"""
    conta = get_object_or_404(ContaReceber, pk=pk)
    
    if request.method == 'POST':
        conta.data_pagamento = request.POST.get('data_pagamento') or timezone.now().date()
        conta.valor_pago = request.POST.get('valor_pago', conta.valor_original)
        conta.status = 'pago'
        conta.save()
        messages.success(request, 'Conta a receber baixada com sucesso!')
        return redirect('ERP_ServicesBI:contareceber_list')
    
    return render(request, 'financeiro/contareceber_baixar.html', {
        'conta': conta
    })


@login_required
def contareceber_delete(request, pk):
    """Excluir conta a receber"""
    conta = get_object_or_404(ContaReceber, pk=pk)
    
    if request.method == 'POST':
        conta.delete()
        messages.success(request, 'Conta a receber excluída com sucesso!')
        return redirect('ERP_ServicesBI:contareceber_list')
    
    return render(request, 'financeiro/contareceber_confirm_delete.html', {
        'conta': conta
    })


# -----------------------------------------------------------------------------
# FINANCEIRO > CONTAS A PAGAR
# -----------------------------------------------------------------------------

@login_required
def contapagar_list(request):
    """Lista de contas a pagar com paginação avançada (25/50 itens)"""
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    vencimento_de = request.GET.get('vencimento_de', '')
    vencimento_ate = request.GET.get('vencimento_ate', '')
    
    contas = ContaPagar.objects.all().order_by('data_vencimento')
    
    if search:
        contas = contas.filter(
            Q(fornecedor__nome_razao_social__icontains=search) |
            Q(descricao__icontains=search) |
            Q(numero_documento__icontains=search)
        )
    
    if status:
        contas = contas.filter(status=status)
    
    if vencimento_de:
        contas = contas.filter(data_vencimento__gte=vencimento_de)
    
    if vencimento_ate:
        contas = contas.filter(data_vencimento__lte=vencimento_ate)
    
    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [25, 50]:
            per_page = 25
    except ValueError:
        per_page = 25
    
    paginator = Paginator(contas, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'financeiro/contapagar_list.html', {
        'contas': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'search': search,
        'status': status,
        'vencimento_de': vencimento_de,
        'vencimento_ate': vencimento_ate,
        'per_page': per_page,
        'total': paginator.count,
    })


@login_required
def contapagar_add(request):
    """Adicionar nova conta a pagar"""
    if request.method == 'POST':
        form = ContaPagarForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conta a pagar cadastrada com sucesso!')
            return redirect('ERP_ServicesBI:contapagar_list')
    else:
        form = ContaPagarForm()
    
    return render(request, 'financeiro/contapagar_form.html', {
        'form': form,
        'titulo': 'Nova Conta a Pagar',
        'action': 'Adicionar'
    })


@login_required
def contapagar_edit(request, pk):
    """Editar conta a pagar"""
    conta = get_object_or_404(ContaPagar, pk=pk)
    
    if request.method == 'POST':
        form = ContaPagarForm(request.POST, instance=conta)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conta a pagar atualizada com sucesso!')
            return redirect('ERP_ServicesBI:contapagar_list')
    else:
        form = ContaPagarForm(instance=conta)
    
    return render(request, 'financeiro/contapagar_form.html', {
        'form': form,
        'titulo': 'Editar Conta a Pagar',
        'action': 'Salvar Alterações',
        'conta': conta
    })


@login_required
def contapagar_baixar(request, pk):
    """Baixar conta a pagar"""
    conta = get_object_or_404(ContaPagar, pk=pk)
    
    if request.method == 'POST':
        conta.data_pagamento = request.POST.get('data_pagamento') or timezone.now().date()
        conta.valor_pago = request.POST.get('valor_pago', conta.valor_original)
        conta.status = 'pago'
        conta.save()
        messages.success(request, 'Conta a pagar baixada com sucesso!')
        return redirect('ERP_ServicesBI:contapagar_list')
    
    return render(request, 'financeiro/contapagar_baixar.html', {
        'conta': conta
    })


@login_required
def contapagar_delete(request, pk):
    """Excluir conta a pagar"""
    conta = get_object_or_404(ContaPagar, pk=pk)
    
    if request.method == 'POST':
        conta.delete()
        messages.success(request, 'Conta a pagar excluída com sucesso!')
        return redirect('ERP_ServicesBI:contapagar_list')
    
    return render(request, 'financeiro/contapagar_confirm_delete.html', {
        'conta': conta
    })


# -----------------------------------------------------------------------------
# FINANCEIRO > ORÇAMENTO FINANCEIRO
# -----------------------------------------------------------------------------

@login_required
def orcamentofinanceiro_list(request):
    """Lista de orçamentos financeiros com paginação avançada (25/50 itens)"""
    search = request.GET.get('search', '')
    ano = request.GET.get('ano', '')
    
    orcamentos = OrcamentoFinanceiro.objects.all().order_by('-ano', 'mes')
    
    if search:
        orcamentos = orcamentos.filter(
            Q(centro_custo__nome__icontains=search) |
            Q(categoria__nome__icontains=search)
        )
    
    if ano:
        orcamentos = orcamentos.filter(ano=ano)
    
    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [25, 50]:
            per_page = 25
    except ValueError:
        per_page = 25
    
    paginator = Paginator(orcamentos, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'financeiro/orcamentofinanceiro_list.html', {
        'orcamentos': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'search': search,
        'ano': ano,
        'per_page': per_page,
        'total': paginator.count,
    })


@login_required
def orcamentofinanceiro_add(request):
    """Adicionar novo orçamento financeiro"""
    if request.method == 'POST':
        form = OrcamentoFinanceiroForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Orçamento financeiro cadastrado com sucesso!')
            return redirect('ERP_ServicesBI:orcamentofinanceiro_list')
    else:
        form = OrcamentoFinanceiroForm()
    
    return render(request, 'financeiro/orcamento_form.html', {
        'form': form,
        'titulo': 'Novo Orçamento Financeiro',
        'action': 'Adicionar'
    })


@login_required
def orcamentofinanceiro_edit(request, pk):
    """Editar orçamento financeiro"""
    orcamento = get_object_or_404(OrcamentoFinanceiro, pk=pk)
    
    if request.method == 'POST':
        form = OrcamentoFinanceiroForm(request.POST, instance=orcamento)
        if form.is_valid():
            form.save()
            messages.success(request, 'Orçamento financeiro atualizado com sucesso!')
            return redirect('ERP_ServicesBI:orcamentofinanceiro_list')
    else:
        form = OrcamentoFinanceiroForm(instance=orcamento)
    
    return render(request, 'financeiro/orcamento_form.html', {
        'form': form,
        'titulo': 'Editar Orçamento Financeiro',
        'action': 'Salvar Alterações',
        'orcamento': orcamento
    })


@login_required
def orcamentofinanceiro_delete(request, pk):
    """Excluir orçamento financeiro"""
    orcamento = get_object_or_404(OrcamentoFinanceiro, pk=pk)
    
    if request.method == 'POST':
        orcamento.delete()
        messages.success(request, 'Orçamento financeiro excluído com sucesso!')
        return redirect('ERP_ServicesBI:orcamentofinanceiro_list')
    
    return render(request, 'financeiro/orcamento_confirm_delete.html', {
        'orcamento': orcamento
    })


# -----------------------------------------------------------------------------
# FINANCEIRO > CONCILIAÇÃO BANCÁRIA
# -----------------------------------------------------------------------------

@login_required
def conciliacao_list(request):
    """Lista de extratos bancários para conciliação com paginação avançada (25/50 itens)"""
    search = request.GET.get('search', '')
    data_de = request.GET.get('data_de', '')
    data_ate = request.GET.get('data_ate', '')
    conciliado = request.GET.get('conciliado', '')
    
    extratos = ExtratoBancario.objects.all().order_by('-data')
    
    if search:
        extratos = extratos.filter(
            Q(descricao__icontains=search) |
            Q(numero_documento__icontains=search)
        )
    
    if data_de:
        extratos = extratos.filter(data__gte=data_de)
    
    if data_ate:
        extratos = extratos.filter(data__lte=data_ate)
    
    if conciliado == 'sim':
        extratos = extratos.filter(conciliado=True)
    elif conciliado == 'nao':
        extratos = extratos.filter(conciliado=False)
    
    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [25, 50]:
            per_page = 25
    except ValueError:
        per_page = 25
    
    paginator = Paginator(extratos, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'financeiro/conciliacao_list.html', {
        'extratos': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'search': search,
        'data_de': data_de,
        'data_ate': data_ate,
        'conciliado': conciliado,
        'per_page': per_page,
        'total': paginator.count,
    })


@login_required
def conciliacao_gerar(request):
    """Gerar lançamentos de conciliação"""
    if request.method == 'POST':
        # Lógica para gerar lançamentos de conciliação
        messages.success(request, 'Conciliação gerada com sucesso!')
        return redirect('ERP_ServicesBI:conciliacao_list')
    
    return render(request, 'financeiro/conciliacao_gerar.html')


# ================================================================================================================================================================

# MÓDULO: ESTOQUE
# -----------------------------------------------------------------------------
# ESTOQUE > MOVIMENTAÇÕES
# -----------------------------------------------------------------------------

@login_required
def movimentacaoestoque_list(request):
    """Lista de movimentações de estoque com paginação avançada (25/50 itens)"""
    search = request.GET.get('search', '')
    tipo = request.GET.get('tipo', '')
    data_de = request.GET.get('data_de', '')
    data_ate = request.GET.get('data_ate', '')
    
    movimentacoes = MovimentacaoEstoque.objects.all().order_by('-data_movimentacao')
    
    if search:
        movimentacoes = movimentacoes.filter(
            Q(produto__descricao__icontains=search) |
            Q(observacao__icontains=search)
        )
    
    if tipo:
        movimentacoes = movimentacoes.filter(tipo=tipo)
    
    if data_de:
        movimentacoes = movimentacoes.filter(data_movimentacao__gte=data_de)
    
    if data_ate:
        movimentacoes = movimentacoes.filter(data_movimentacao__lte=data_ate)
    
    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [25, 50]:
            per_page = 25
    except ValueError:
        per_page = 25
    
    paginator = Paginator(movimentacoes, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'estoque/movimentacaoestoque_list.html', {
        'movimentacoes': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'search': search,
        'tipo': tipo,
        'data_de': data_de,
        'data_ate': data_ate,
        'per_page': per_page,
        'total': paginator.count,
    })


@login_required
def movimentacaoestoque_add(request):
    """Adicionar nova movimentação de estoque"""
    if request.method == 'POST':
        form = MovimentacaoEstoqueForm(request.POST)
        if form.is_valid():
            movimentacao = form.save()
            messages.success(request, 'Movimentação de estoque registrada com sucesso!')
            return redirect('ERP_ServicesBI:movimentacaoestoque_list')
    else:
        form = MovimentacaoEstoqueForm()
    
    return render(request, 'estoque/movimentacaoestoque_form.html', {
        'form': form,
        'titulo': 'Nova Movimentação',
        'action': 'Adicionar'
    })


@login_required
def movimentacaoestoque_delete(request, pk):
    """Excluir movimentação de estoque"""
    movimentacao = get_object_or_404(MovimentacaoEstoque, pk=pk)
    
    if request.method == 'POST':
        movimentacao.delete()
        messages.success(request, 'Movimentação excluída com sucesso!')
        return redirect('ERP_ServicesBI:movimentacaoestoque_list')
    
    return render(request, 'estoque/movimentacaoestoque_confirm_delete.html', {
        'movimentacao': movimentacao
    })


# -----------------------------------------------------------------------------
# ESTOQUE > INVENTÁRIO
# -----------------------------------------------------------------------------

@login_required
def inventario_list(request):
    """Lista de inventários com paginação avançada (25/50 itens)"""
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    inventarios = Inventario.objects.all().order_by('-data_inventario')
    
    if search:
        inventarios = inventarios.filter(
            Q(descricao__icontains=search) |
            Q(responsavel__icontains=search)
        )
    
    if status:
        inventarios = inventarios.filter(status=status)
    
    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [25, 50]:
            per_page = 25
    except ValueError:
        per_page = 25
    
    paginator = Paginator(inventarios, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'estoque/inventario_list.html', {
        'inventarios': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'search': search,
        'status': status,
        'per_page': per_page,
        'total': paginator.count,
    })


@login_required
def inventario_add(request):
    """Adicionar novo inventário"""
    if request.method == 'POST':
        form = InventarioForm(request.POST)
        if form.is_valid():
            inventario = form.save()
            messages.success(request, 'Inventário criado com sucesso!')
            return redirect('ERP_ServicesBI:inventario_edit', pk=inventario.pk)
    else:
        form = InventarioForm()
    
    return render(request, 'estoque/inventario_form.html', {
        'form': form,
        'titulo': 'Novo Inventário',
        'action': 'Adicionar'
    })


@login_required
def inventario_edit(request, pk):
    """Editar inventário"""
    inventario = get_object_or_404(Inventario, pk=pk)
    itens = inventario.itens.all()
    
    if request.method == 'POST':
        form = InventarioForm(request.POST, instance=inventario)
        if form.is_valid():
            form.save()
            messages.success(request, 'Inventário atualizado com sucesso!')
            return redirect('ERP_ServicesBI:inventario_list')
    else:
        form = InventarioForm(instance=inventario)
    
    return render(request, 'estoque/inventario_form.html', {
        'form': form,
        'inventario': inventario,
        'itens': itens,
        'titulo': f'Inventário #{inventario.id}'
    })


@login_required
def inventario_item_add(request, inventario_pk):
    """Adicionar item ao inventário"""
    inventario = get_object_or_404(Inventario, pk=inventario_pk)
    
    if request.method == 'POST':
        form = ItemInventarioForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.inventario = inventario
            item.save()
            messages.success(request, 'Item adicionado com sucesso!')
            return redirect('ERP_ServicesBI:inventario_edit', pk=inventario.pk)
    else:
        form = ItemInventarioForm()
    
    return render(request, 'estoque/inventario_item_form.html', {
        'form': form,
        'inventario': inventario,
        'titulo': 'Adicionar Item'
    })


@login_required
def inventario_item_delete(request, pk):
    """Excluir item do inventário"""
    item = get_object_or_404(ItemInventario, pk=pk)
    inventario_pk = item.inventario.pk
    item.delete()
    messages.success(request, 'Item removido com sucesso!')
    return redirect('ERP_ServicesBI:inventario_edit', pk=inventario_pk)


@login_required
def inventario_finalizar(request, pk):
    """Finalizar inventário"""
    inventario = get_object_or_404(Inventario, pk=pk)
    
    if request.method == 'POST':
        inventario.status = 'finalizado'
        inventario.save()
        messages.success(request, 'Inventário finalizado com sucesso!')
        return redirect('ERP_ServicesBI:inventario_list')
    
    return render(request, 'estoque/inventario_finalizar.html', {
        'inventario': inventario
    })


@login_required
def inventario_delete(request, pk):
    """Excluir inventário"""
    inventario = get_object_or_404(Inventario, pk=pk)
    
    if request.method == 'POST':
        inventario.delete()
        messages.success(request, 'Inventário excluído com sucesso!')
        return redirect('ERP_ServicesBI:inventario_list')
    
    return render(request, 'estoque/inventario_confirm_delete.html', {
        'inventario': inventario
    })


# -----------------------------------------------------------------------------
# ESTOQUE > TRANSFERÊNCIAS
# -----------------------------------------------------------------------------

@login_required
def transferencia_list(request):
    """Lista de transferências de estoque com paginação avançada (25/50 itens)"""
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    transferencias = TransferenciaEstoque.objects.all().order_by('-data_transferencia')
    
    if search:
        transferencias = transferencias.filter(
            Q(observacao__icontains=search) |
            Q(responsavel__icontains=search)
        )
    
    if status:
        transferencias = transferencias.filter(status=status)
    
    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [25, 50]:
            per_page = 25
    except ValueError:
        per_page = 25
    
    paginator = Paginator(transferencias, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'estoque/transferencia_list.html', {
        'transferencias': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'search': search,
        'status': status,
        'per_page': per_page,
        'total': paginator.count,
    })


@login_required
def transferencia_add(request):
    """Adicionar nova transferência de estoque"""
    if request.method == 'POST':
        form = TransferenciaEstoqueForm(request.POST)
        if form.is_valid():
            transferencia = form.save()
            messages.success(request, 'Transferência criada com sucesso!')
            return redirect('ERP_ServicesBI:transferencia_edit', pk=transferencia.pk)
    else:
        form = TransferenciaEstoqueForm()
    
    return render(request, 'estoque/transferencia_form.html', {
        'form': form,
        'titulo': 'Nova Transferência',
        'action': 'Adicionar'
    })


@login_required
def transferencia_edit(request, pk):
    """Editar transferência de estoque"""
    transferencia = get_object_or_404(TransferenciaEstoque, pk=pk)
    itens = transferencia.itens.all()
    
    if request.method == 'POST':
        form = TransferenciaEstoqueForm(request.POST, instance=transferencia)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transferência atualizada com sucesso!')
            return redirect('ERP_ServicesBI:transferencia_list')
    else:
        form = TransferenciaEstoqueForm(instance=transferencia)
    
    return render(request, 'estoque/transferencia_form.html', {
        'form': form,
        'transferencia': transferencia,
        'itens': itens,
        'titulo': f'Transferência #{transferencia.id}'
    })


@login_required
def transferencia_item_add(request, transferencia_pk):
    """Adicionar item à transferência"""
    transferencia = get_object_or_404(TransferenciaEstoque, pk=transferencia_pk)
    
    if request.method == 'POST':
        form = ItemTransferenciaForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.transferencia = transferencia
            item.save()
            messages.success(request, 'Item adicionado com sucesso!')
            return redirect('ERP_ServicesBI:transferencia_edit', pk=transferencia.pk)
    else:
        form = ItemTransferenciaForm()
    
    return render(request, 'estoque/transferencia_item_form.html', {
        'form': form,
        'transferencia': transferencia,
        'titulo': 'Adicionar Item'
    })


@login_required
def transferencia_item_delete(request, pk):
    """Excluir item da transferência"""
    item = get_object_or_404(ItemTransferencia, pk=pk)
    transferencia_pk = item.transferencia.pk
    item.delete()
    messages.success(request, 'Item removido com sucesso!')
    return redirect('ERP_ServicesBI:transferencia_edit', pk=transferencia_pk)


@login_required
def transferencia_efetivar(request, pk):
    """Efetivar transferência de estoque"""
    transferencia = get_object_or_404(TransferenciaEstoque, pk=pk)
    
    if request.method == 'POST':
        with transaction.atomic():
            # Lógica para efetivar a transferência (movimentar estoque)
            for item in transferencia.itens.all():
                # Registrar saída do origem
                MovimentacaoEstoque.objects.create(
                    produto=item.produto,
                    tipo='saida',
                    quantidade=item.quantidade,
                    observacao=f'Transferência #{transferencia.id} - Saída'
                )
                # Registrar entrada no destino
                MovimentacaoEstoque.objects.create(
                    produto=item.produto,
                    tipo='entrada',
                    quantidade=item.quantidade,
                    observacao=f'Transferência #{transferencia.id} - Entrada'
                )
            
            transferencia.status = 'efetivada'
            transferencia.save()
        
        messages.success(request, 'Transferência efetivada com sucesso!')
        return redirect('ERP_ServicesBI:transferencia_list')
    
    return render(request, 'estoque/transferencia_efetivar.html', {
        'transferencia': transferencia
    })


@login_required
def transferencia_delete(request, pk):
    """Excluir transferência de estoque"""
    transferencia = get_object_or_404(TransferenciaEstoque, pk=pk)
    
    if request.method == 'POST':
        transferencia.delete()
        messages.success(request, 'Transferência excluída com sucesso!')
        return redirect('ERP_ServicesBI:transferencia_list')
    
    return render(request, 'estoque/transferencia_confirm_delete.html', {
        'transferencia': transferencia
    })
# =============================================================================
# RELATÓRIOS - ESTOQUE
# =============================================================================

@login_required
def relatorio_estoque(request):
    """Relatório de posição de estoque"""
    categoria_id = request.GET.get('categoria', '')
    estoque_baixo = request.GET.get('estoque_baixo', '')
    
    produtos = Produto.objects.all().order_by('descricao')
    
    if categoria_id:
        produtos = produtos.filter(categoria_id=categoria_id)
    
    if estoque_baixo:
        produtos = produtos.filter(estoque_atual__lte=F('estoque_minimo'))
    
    # Totais
    total_produtos = produtos.count()
    valor_total_estoque = sum([
        (p.estoque_atual or 0) * (p.preco_custo or 0) 
        for p in produtos
    ])
    
    categorias = Categoria.objects.all().order_by('nome')
    
    return render(request, 'estoque/relatorio_estoque.html', {
        'produtos': produtos,
        'total_produtos': total_produtos,
        'valor_total_estoque': valor_total_estoque,
        'categorias': categorias,
        'categoria_id': categoria_id,
        'estoque_baixo': estoque_baixo,
    })


@login_required
def relatorio_movimentacoes(request):
    """Relatório de movimentações de estoque"""
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    tipo = request.GET.get('tipo', '')
    produto_id = request.GET.get('produto', '')
    
    movimentacoes = MovimentacaoEstoque.objects.all().order_by('-data_movimentacao')
    
    if data_inicio:
        movimentacoes = movimentacoes.filter(data_movimentacao__gte=data_inicio)
    if data_fim:
        movimentacoes = movimentacoes.filter(data_movimentacao__lte=data_fim)
    if tipo:
        movimentacoes = movimentacoes.filter(tipo=tipo)
    if produto_id:
        movimentacoes = movimentacoes.filter(produto_id=produto_id)
    
    # Totais por tipo
    total_entradas = movimentacoes.filter(tipo='entrada').aggregate(
        total=Sum('quantidade')
    )['total'] or 0
    
    total_saidas = movimentacoes.filter(tipo='saida').aggregate(
        total=Sum('quantidade')
    )['total'] or 0
    
    produtos = Produto.objects.all().order_by('descricao')
    
    return render(request, 'estoque/relatorio_movimentacoes.html', {
        'movimentacoes': movimentacoes[:200],  # Limitar para performance
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'produtos': produtos,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'tipo': tipo,
        'produto_id': produto_id,
    })
# =============================================================================
# FINANCEIRO - VIEWS ADICIONAIS
# =============================================================================

@login_required
def fluxo_caixa(request):
    """Fluxo de caixa"""
    data_inicio = request.GET.get('data_inicio', timezone.now().replace(day=1).strftime('%Y-%m-%d'))
    data_fim = request.GET.get('data_fim', timezone.now().strftime('%Y-%m-%d'))
    
    # Movimentos do período
    movimentos = MovimentoCaixa.objects.filter(
        data__gte=data_inicio,
        data__lte=data_fim
    ).order_by('data')
    
    # Totais
    total_entradas = movimentos.filter(tipo='entrada').aggregate(
        total=Sum('valor')
    )['total'] or Decimal('0.00')
    
    total_saidas = movimentos.filter(tipo='saida').aggregate(
        total=Sum('valor')
    )['total'] or Decimal('0.00')
    
    saldo = total_entradas - total_saidas
    
    return render(request, 'financeiro/fluxo_caixa.html', {
        'movimentos': movimentos,
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'saldo': saldo,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
    })


@login_required
def movimentocaixa_add(request):
    """Adicionar lançamento no fluxo de caixa"""
    if request.method == 'POST':
        form = MovimentoCaixaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Lançamento adicionado com sucesso!')
            return redirect('ERP_ServicesBI:fluxo_caixa')
    else:
        form = MovimentoCaixaForm()
    
    return render(request, 'financeiro/movimentocaixa_form.html', {
        'form': form,
        'titulo': 'Novo Lançamento',
        'action': 'Adicionar'
    })


@login_required
def conciliacao_add(request):
    """Adicionar novo extrato bancário"""
    if request.method == 'POST':
        form = ExtratoBancarioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Extrato adicionado com sucesso!')
            return redirect('ERP_ServicesBI:conciliacao_list')
    else:
        form = ExtratoBancarioForm()
    
    return render(request, 'financeiro/conciliacao_importar.html', {
        'form': form,
        'titulo': 'Novo Extrato',
        'action': 'Adicionar'
    })


@login_required
def conciliacao_edit(request, pk):
    """Editar extrato bancário"""
    extrato = get_object_or_404(ExtratoBancario, pk=pk)
    
    if request.method == 'POST':
        form = ExtratoBancarioForm(request.POST, instance=extrato)
        if form.is_valid():
            form.save()
            messages.success(request, 'Extrato atualizado com sucesso!')
            return redirect('ERP_ServicesBI:conciliacao_list')
    else:
        form = ExtratoBancarioForm(instance=extrato)
    
    return render(request, 'financeiro/conciliacao_importar.html', {
        'form': form,
        'titulo': 'Editar Extrato',
        'action': 'Salvar Alterações',
        'extrato': extrato
    })


@login_required
def conciliacao_delete(request, pk):
    """Excluir extrato bancário"""
    extrato = get_object_or_404(ExtratoBancario, pk=pk)
    
    if request.method == 'POST':
        extrato.delete()
        messages.success(request, 'Extrato excluído com sucesso!')
        return redirect('ERP_ServicesBI:conciliacao_list')
    
    return render(request, 'financeiro/conciliacao_confirm_delete.html', {
        'extrato': extrato
    })


@login_required
def dre_gerencial(request):
    """DRE Gerencial (Demonstração do Resultado do Exercício)"""
    mes = request.GET.get('mes', timezone.now().month)
    ano = request.GET.get('ano', timezone.now().year)
    
    try:
        mes = int(mes)
        ano = int(ano)
    except (ValueError, TypeError):
        mes = timezone.now().month
        ano = timezone.now().year
    
    # Receitas (vendas)
    receitas = NotaFiscalSaida.objects.filter(
        data_emissao__month=mes,
        data_emissao__year=ano
    ).aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')
    
    # Custos (compras)
    custos = NotaFiscalEntrada.objects.filter(
        data_entrada__month=mes,
        data_entrada__year=ano
    ).aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')
    
    # Despesas (contas pagas)
    despesas = ContaPagar.objects.filter(
        data_pagamento__month=mes,
        data_pagamento__year=ano,
        status='pago'
    ).aggregate(total=Sum('valor_pago'))['total'] or Decimal('0.00')
    
    # Resultado
    lucro_bruto = receitas - custos
    lucro_liquido = lucro_bruto - despesas
    
    context = {
        'mes': mes,
        'ano': ano,
        'receitas': receitas,
        'custos': custos,
        'despesas': despesas,
        'lucro_bruto': lucro_bruto,
        'lucro_liquido': lucro_liquido,
        'meses': range(1, 13),
        'anos': range(ano - 2, ano + 2),
    }
    
    return render(request, 'financeiro/dre_gerencial.html', context)


# =============================================================================
# ESTOQUE - VIEWS ADICIONAIS
# =============================================================================

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
    
    return render(request, 'estoque/movimentacaoestoque_form.html', {
        'form': form,
        'titulo': 'Editar Movimentação',
        'action': 'Salvar Alterações',
        'movimentacao': movimentacao
    })