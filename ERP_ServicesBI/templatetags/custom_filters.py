from django import template
from decimal import Decimal
import re

register = template.Library()

@register.filter
def currency_br(value):
    """Formata valor para moeda brasileira: R$ 1.562,25"""
    if value is None:
        return "R$ 0,00"
    try:
        valor = Decimal(str(value))
        valor_formatado = f"{valor:,.2f}"
        valor_formatado = valor_formatado.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {valor_formatado}"
    except:
        return f"R$ {value}"

@register.filter
def number_br(value):
    """Formata número com separador de milhar brasileiro: 1.562,25"""
    if value is None:
        return "0,00"
    try:
        valor = Decimal(str(value))
        valor_formatado = f"{valor:,.2f}"
        valor_formatado = valor_formatado.replace(",", "X").replace(".", ",").replace("X", ".")
        return valor_formatado
    except:
        return str(value)

@register.filter
def format_cpf_cnpj(value):
    """Formata CPF ou CNPJ automaticamente"""
    if not value:
        return '-'
    
    # Remove tudo que não é dígito
    numeros = re.sub(r'\D', '', str(value))
    
    if len(numeros) == 11:
        # CPF: 000.000.000-00
        return f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:]}"
    elif len(numeros) == 14:
        # CNPJ: 00.000.000/0000-00
        return f"{numeros[:2]}.{numeros[2:5]}.{numeros[5:8]}/{numeros[8:12]}-{numeros[12:]}"
    else:
        return value

@register.filter
def format_telefone(value):
    """Formata telefone fixo ou celular: (00) 00000-0000 ou (00) 0000-0000"""
    if not value:
        return '-'
    
    # Remove tudo que não é dígito
    numeros = re.sub(r'\D', '', str(value))
    
    if len(numeros) == 11:
        # Celular: (00) 00000-0000
        return f"({numeros[:2]}) {numeros[2:7]}-{numeros[7:]}"
    elif len(numeros) == 10:
        # Fixo: (00) 0000-0000
        return f"({numeros[:2]}) {numeros[2:6]}-{numeros[6:]}"
    else:
        return value