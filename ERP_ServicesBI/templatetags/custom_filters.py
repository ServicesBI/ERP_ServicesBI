# -*- coding: utf-8 -*-
"""
ERP_ServicesBI - Custom Filters
Filtros customizados para formatação de valores nos templates
"""
from django import template
from decimal import Decimal
from django.utils import formats
import locale

register = template.Library()


# ========================================================================
# FILTROS DE MOEDA E VALORES
# ========================================================================

@register.filter(name='currency_br')
def currency_br(value):
    """
    Formata valor em moeda brasileira (R$)
    Exemplo: 1000.50 -> R$ 1.000,50
    """
    if value is None or value == '':
        return 'R$ 0,00'
    
    try:
        value = float(value)
        return f'R$ {value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return 'R$ 0,00'


@register.filter(name='currency_compact')
def currency_compact(value):
    """
    Formata valor em moeda compacta (k, M, B)
    Exemplo: 1500000 -> R$ 1,5M
    """
    if value is None or value == '':
        return 'R$ 0'
    
    try:
        value = float(value)
        
        if abs(value) >= 1_000_000_000:
            return f'R$ {value / 1_000_000_000:.1f}B'
        elif abs(value) >= 1_000_000:
            return f'R$ {value / 1_000_000:.1f}M'
        elif abs(value) >= 1_000:
            return f'R$ {value / 1_000:.1f}k'
        else:
            return f'R$ {value:.0f}'
    except (ValueError, TypeError):
        return 'R$ 0'


@register.filter(name='percentage')
def percentage(value, decimals=1):
    """
    Formata valor como percentual
    Exemplo: 0.25 -> 25.0%
    """
    if value is None or value == '':
        return '0%'
    
    try:
        value = float(value) * 100
        return f'{value:.{decimals}f}%'
    except (ValueError, TypeError):
        return '0%'


@register.filter(name='abs_currency')
def abs_currency(value):
    """
    Formata valor absoluto em moeda
    Exemplo: -1000 -> R$ 1.000,00
    """
    if value is None or value == '':
        return 'R$ 0,00'
    
    try:
        value = abs(float(value))
        return currency_br(value)
    except (ValueError, TypeError):
        return 'R$ 0,00'


# ========================================================================
# FILTROS DE FORMATAÇÃO NUMÉRICA
# ========================================================================

@register.filter(name='number_format')
def number_format(value, decimals=2):
    """
    Formata número com separadores de milhar
    Exemplo: 1000000 -> 1.000.000,00
    """
    if value is None or value == '':
        return '0'
    
    try:
        value = float(value)
        return f'{value:,.{decimals}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return '0'


@register.filter(name='round_decimal')
def round_decimal(value, decimals=2):
    """
    Arredonda para N casas decimais
    """
    if value is None or value == '':
        return 0
    
    try:
        return round(float(value), int(decimals))
    except (ValueError, TypeError):
        return 0


# ========================================================================
# FILTROS DE TEXTO E STRINGS
# ========================================================================

@register.filter(name='truncate_word')
def truncate_word(value, length=10):
    """
    Trunca string para N caracteres com ellipsis
    Exemplo: "muito texto longo" -> "muito tex..."
    """
    if not value:
        return ''
    
    value = str(value)
    if len(value) > int(length):
        return f'{value[:int(length)]}...'
    return value


@register.filter(name='mask_phone')
def mask_phone(value):
    """
    Mascara número de telefone
    Exemplo: 1199999999 -> (11) 99999-999
    """
    if not value:
        return ''
    
    value = ''.join(filter(str.isdigit, str(value)))
    
    if len(value) == 10:
        return f'({value[:2]}) {value[2:7]}-{value[7:]}'
    elif len(value) == 11:
        return f'({value[:2]}) {value[2:7]}-{value[7:]}'
    else:
        return value


@register.filter(name='mask_cpf')
def mask_cpf(value):
    """
    Mascara CPF
    Exemplo: 12345678900 -> 123.456.789-00
    """
    if not value:
        return ''
    
    value = ''.join(filter(str.isdigit, str(value)))
    
    if len(value) == 11:
        return f'{value[:3]}.{value[3:6]}.{value[6:9]}-{value[9:]}'
    else:
        return value


@register.filter(name='mask_cnpj')
def mask_cnpj(value):
    """
    Mascara CNPJ
    Exemplo: 12345678901234 -> 12.345.678/9012-34
    """
    if not value:
        return ''
    
    value = ''.join(filter(str.isdigit, str(value)))
    
    if len(value) == 14:
        return f'{value[:2]}.{value[2:5]}.{value[5:8]}/{value[8:12]}-{value[12:]}'
    else:
        return value


# ========================================================================
# FILTROS DE DATA E HORA
# ========================================================================

@register.filter(name='date_br')
def date_br(value, format_str='d \d\e F \d\e Y'):
    """
    Formata data em português Brasil
    Exemplo: 2025-01-24 -> 24 de janeiro de 2025
    """
    if not value:
        return ''
    
    try:
        from datetime import datetime
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        
        months_pt = {
            1: 'janeiro', 2: 'fevereiro', 3: 'março', 4: 'abril',
            5: 'maio', 6: 'junho', 7: 'julho', 8: 'agosto',
            9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro'
        }
        
        return f'{value.day} de {months_pt[value.month]} de {value.year}'
    except (ValueError, AttributeError):
        return value


@register.filter(name='time_ago')
def time_ago(value):
    """
    Formata tempo decorrido (há X dias, horas, etc)
    Exemplo: 2025-01-20 (hoje: 2025-01-24) -> há 4 dias
    """
    if not value:
        return ''
    
    try:
        from datetime import datetime
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        
        now = datetime.now()
        if hasattr(value, 'tzinfo') and value.tzinfo is not None:
            from django.utils import timezone
            now = timezone.now()
        
        delta = now - value
        
        if delta.days > 0:
            return f'há {delta.days} dia{"s" if delta.days > 1 else ""}'
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            return f'há {hours} hora{"s" if hours > 1 else ""}'
        elif delta.seconds > 60:
            minutes = delta.seconds // 60
            return f'há {minutes} minuto{"s" if minutes > 1 else ""}'
        else:
            return 'agora mesmo'
    except (ValueError, AttributeError):
        return value


# ========================================================================
# FILTROS DE LISTA E DADOS
# ========================================================================

@register.filter(name='join_values')
def join_values(value, separator=', '):
    """
    Junta valores de lista com separador
    Exemplo: ['a', 'b', 'c'] -> "a, b, c"
    """
    if not value:
        return ''
    
    try:
        return separator.join(str(v) for v in value)
    except (TypeError, AttributeError):
        return str(value)


@register.filter(name='first_chars')
def first_chars(value, count=1):
    """
    Retorna N primeiros caracteres
    """
    if not value:
        return ''
    
    return str(value)[:int(count)]


# ========================================================================
# FILTROS DE VALIDAÇÃO E CHECAGEM
# ========================================================================

@register.filter(name='is_empty')
def is_empty(value):
    """
    Retorna True se valor está vazio
    """
    return not bool(value)


@register.filter(name='default_if_zero')
def default_if_zero(value, default='—'):
    """
    Retorna default se valor é zero
    """
    try:
        if float(value) == 0:
            return default
        return value
    except (ValueError, TypeError):
        return default


@register.filter(name='default_if_none')
def default_if_none(value, default='—'):
    """
    Retorna default se valor é None
    """
    return default if value is None else value


# ========================================================================
# FILTROS DE COR E STATUS
# ========================================================================

@register.filter(name='status_badge')
def status_badge(value):
    """
    Retorna classe CSS para status
    """
    status_map = {
        'pago': 'badge--success',
        'pendente': 'badge--warning',
        'cancelado': 'badge--danger',
        'recebido': 'badge--success',
        'atrasado': 'badge--danger',
        'aprovado': 'badge--success',
        'rejeitado': 'badge--danger',
        'processando': 'badge--info',
    }
    
    return status_map.get(str(value).lower(), 'badge--info')


@register.filter(name='trend_arrow')
def trend_arrow(value):
    """
    Retorna seta de tendência (↗ ou ↘)
    """
    try:
        value = float(value)
        if value > 0:
            return f'↗ {abs(value):.1f}%'
        elif value < 0:
            return f'↘ {abs(value):.1f}%'
        else:
            return '→ 0%'
    except (ValueError, TypeError):
        return '→ 0%'


# ========================================================================
# TEMPLATE TAGS (não são filtros, mas funções que retornam dados)
# ========================================================================

@register.simple_tag
def get_color_by_status(status):
    """
    Retorna cor para status
    """
    color_map = {
        'pago': '#10b981',
        'pendente': '#f59e0b',
        'cancelado': '#ef4444',
        'recebido': '#10b981',
        'atrasado': '#ef4444',
        'aprovado': '#10b981',
        'rejeitado': '#ef4444',
        'processando': '#06b6d4',
    }
    
    return color_map.get(str(status).lower(), '#06b6d4')


@register.simple_tag
def currency_br_inline(value):
    """
    Template tag simples para moeda em templates
    {% currency_br_inline 1000.50 %}
    """
    return currency_br(value)
