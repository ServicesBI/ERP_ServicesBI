#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para renomear templates do ERP_ServicesBI
Padroniza todos os nomes para snake_case com underline
"""

import os
import shutil
from pathlib import Path

# Configurações
BASE_DIR = Path("ERP_ServicesBI/templates")  # Ajuste conforme sua estrutura

# Mapeamento de renomeação: (nome_antigo, nome_novo)
RENAMES = {
    # COMPRAS - Pedidos
    "pedidocompra_list.html": "pedido_compra_list.html",
    "pedidocompra_form.html": "pedido_compra_form.html",
    "pedidocompra_confirm_delete.html": "pedido_compra_confirm_delete.html",
    "pedidocompra_item_form.html": "pedido_compra_item_form.html",
    
    # COMPRAS - Notas Fiscais de Entrada
    "notafiscalentrada_list.html": "nota_fiscal_entrada_list.html",
    "notafiscalentrada_form.html": "nota_fiscal_entrada_form.html",
    "notafiscalentrada_confirm_delete.html": "nota_fiscal_entrada_confirm_delete.html",
    "notafiscalentrada_item_form.html": "nota_fiscal_entrada_item_form.html",
    
    # VENDAS - Notas Fiscais de Saída (views já atualizadas, templates precisam seguir)
    "notafiscalsaida_list.html": "nota_fiscal_saida_list.html",
    "notafiscalsaida_form.html": "nota_fiscal_saida_form.html",
    "notafiscalsaida_confirm_delete.html": "nota_fiscal_saida_confirm_delete.html",
    "notafiscalsaida_item_form.html": "nota_fiscal_saida_item_form.html",
    
    # FINANCEIRO - Contas a Receber
    "contareceber_list.html": "conta_receber_list.html",
    "contareceber_form.html": "conta_receber_form.html",
    "contareceber_confirm_delete.html": "conta_receber_confirm_delete.html",
    "contareceber_baixar.html": "conta_receber_baixar.html",
    
    # FINANCEIRO - Contas a Pagar
    "contapagar_list.html": "conta_pagar_list.html",
    "contapagar_form.html": "conta_pagar_form.html",
    "contapagar_confirm_delete.html": "conta_pagar_confirm_delete.html",
    "contapagar_baixar.html": "conta_pagar_baixar.html",
    
    # FINANCEIRO - Movimentação de Caixa
    "movimentocaixa_form.html": "movimentacao_caixa_form.html",
    
    # FINANCEIRO - Categoria Financeira
    "categoriafinanceira_list.html": "categoria_financeira_list.html",
    "categoriafinanceira_form.html": "categoria_financeira_form.html",
    "categoriafinanceira_confirm_delete.html": "categoria_financeira_confirm_delete.html",
    
    # FINANCEIRO - Centro de Custo
    "centrocusto_list.html": "centro_custo_list.html",
    "centrocusto_form.html": "centro_custo_form.html",
    "centrocusto_confirm_delete.html": "centro_custo_confirm_delete.html",
    
    # FINANCEIRO - Orçamento Financeiro
    "orcamentofinanceiro_list.html": "orcamento_financeiro_list.html",
    "orcamentofinanceiro_form.html": "orcamento_financeiro_form.html",
    "orcamentofinanceiro_confirm_delete.html": "orcamento_financeiro_confirm_delete.html",
    
    # ESTOQUE - Movimentação de Estoque
    "movimentacao_list.html": "movimentacao_estoque_list.html",
    "movimentacao_form.html": "movimentacao_estoque_form.html",
    "movimentacao_confirm_delete.html": "movimentacao_estoque_confirm_delete.html",
}


def find_template_dirs(base_dir):
    """Encontra todos os diretórios de templates"""
    template_dirs = []
    for root, dirs, files in os.walk(base_dir):
        if any(f.endswith('.html') for f in files):
            template_dirs.append(Path(root))
    return template_dirs


def rename_templates(base_dir):
    """Executa a renomeação dos templates"""
    base_path = Path(base_dir)
    
    if not base_path.exists():
        print(f"❌ Diretório não encontrado: {base_path}")
        print("Ajuste a variável BASE_DIR no script")
        return
    
    print(f"🔍 Procurando templates em: {base_path.absolute()}")
    print("-" * 60)
    
    renomeados = []
    nao_encontrados = []
    
    for root, dirs, files in os.walk(base_path):
        for old_name, new_name in RENAMES.items():
            old_path = Path(root) / old_name
            new_path = Path(root) / new_name
            
            if old_path.exists():
                try:
                    # Renomear o arquivo
                    shutil.move(str(old_path), str(new_path))
                    rel_path = old_path.relative_to(base_path)
                    print(f"✅ {rel_path} → {new_name}")
                    renomeados.append((old_name, new_name))
                except Exception as e:
                    print(f"❌ Erro ao renomear {old_name}: {e}")
            else:
                # Só adiciona a lista de não encontrados se o novo também não existe
                # (pode já ter sido renomeado)
                if not new_path.exists():
                    nao_encontrados.append(old_name)
    
    print("-" * 60)
    print(f"\n📊 Resumo da Renomeação:")
    print(f"   ✅ Renomeados: {len(renomeados)}")
    print(f"   ⏭️  Já existentes ou não encontrados: {len(nao_encontrados)}")
    
    if renomeados:
        print(f"\n📝 Arquivos renomeados:")
        for old, new in renomeados:
            print(f"   • {old} → {new}")
    
    return renomeados


def update_url_tags_in_templates(base_dir):
    """Atualiza os {% url %} nos templates para os novos nomes"""
    base_path = Path(base_dir)
    
    # Mapeamento de URL names antigos para novos
    URL_RENAMES = {
        # Compras
        "'pedidocompra_list'": "'pedido_compra_list'",
        '"pedidocompra_list"': '"pedido_compra_list"',
        "'pedidocompra_add'": "'pedido_compra_add'",
        '"pedidocompra_add"': '"pedido_compra_add"',
        "'pedidocompra_edit'": "'pedido_compra_edit'",
        '"pedidocompra_edit"': '"pedido_compra_edit"',
        "'pedidocompra_delete'": "'pedido_compra_delete'",
        '"pedidocompra_delete"': '"pedido_compra_delete"',
        "'pedidocompra_item_add'": "'pedido_compra_item_add'",
        '"pedidocompra_item_add"': '"pedido_compra_item_add"',
        "'pedidocompra_item_edit'": "'pedido_compra_item_edit'",
        '"pedidocompra_item_edit"': '"pedido_compra_item_edit"',
        "'pedidocompra_item_delete'": "'pedido_compra_item_delete'",
        '"pedidocompra_item_delete"': '"pedido_compra_item_delete"',
        "'pedidocompra_gerar_nfe'": "'pedido_compra_gerar_nfe'",
        '"pedidocompra_gerar_nfe"': '"pedido_compra_gerar_nfe"',
        
        "'notafiscalentrada_list'": "'nota_fiscal_entrada_list'",
        '"notafiscalentrada_list"': '"nota_fiscal_entrada_list"',
        "'notafiscalentrada_add'": "'nota_fiscal_entrada_add'",
        '"notafiscalentrada_add"': '"nota_fiscal_entrada_add"',
        "'notafiscalentrada_edit'": "'nota_fiscal_entrada_edit'",
        '"notafiscalentrada_edit"': '"nota_fiscal_entrada_edit"',
        "'notafiscalentrada_delete'": "'nota_fiscal_entrada_delete'",
        '"notafiscalentrada_delete"': '"nota_fiscal_entrada_delete"',
        "'notafiscalentrada_item_add'": "'nota_fiscal_entrada_item_add'",
        '"notafiscalentrada_item_add"': '"nota_fiscal_entrada_item_add"',
        "'notafiscalentrada_item_delete'": "'nota_fiscal_entrada_item_delete'",
        '"notafiscalentrada_item_delete"': '"nota_fiscal_entrada_item_delete"',
        
        # Vendas
        "'notafiscalsaida_list'": "'nota_fiscal_saida_list'",
        '"notafiscalsaida_list"': '"nota_fiscal_saida_list"',
        "'notafiscalsaida_add'": "'nota_fiscal_saida_add'",
        '"notafiscalsaida_add"': '"nota_fiscal_saida_add"',
        "'notafiscalsaida_edit'": "'nota_fiscal_saida_edit'",
        '"notafiscalsaida_edit"': '"nota_fiscal_saida_edit"',
        "'notafiscalsaida_delete'": "'nota_fiscal_saida_delete'",
        '"notafiscalsaida_delete"': '"nota_fiscal_saida_delete"',
        "'notafiscalsaida_item_add'": "'nota_fiscal_saida_item_add'",
        '"notafiscalsaida_item_add"': '"nota_fiscal_saida_item_add"',
        "'notafiscalsaida_item_delete'": "'nota_fiscal_saida_item_delete'",
        '"notafiscalsaida_item_delete"': '"nota_fiscal_saida_item_delete"',
        
        # Financeiro
        "'contareceber_list'": "'conta_receber_list'",
        '"contareceber_list"': '"conta_receber_list"',
        "'contareceber_add'": "'conta_receber_add'",
        '"contareceber_add"': '"conta_receber_add"',
        "'contareceber_edit'": "'conta_receber_edit'",
        '"contareceber_edit"': '"conta_receber_edit"',
        "'contareceber_delete'": "'conta_receber_delete'",
        '"contareceber_delete"': '"conta_receber_delete"',
        "'contareceber_baixar'": "'conta_receber_baixar'",
        '"contareceber_baixar"': '"conta_receber_baixar"',
        
        "'contapagar_list'": "'conta_pagar_list'",
        '"contapagar_list"': '"conta_pagar_list"',
        "'contapagar_add'": "'conta_pagar_add'",
        '"contapagar_add"': '"conta_pagar_add"',
        "'contapagar_edit'": "'conta_pagar_edit'",
        '"contapagar_edit"': '"conta_pagar_edit"',
        "'contapagar_delete'": "'conta_pagar_delete'",
        '"contapagar_delete"': '"conta_pagar_delete"',
        "'contapagar_baixar'": "'conta_pagar_baixar'",
        '"contapagar_baixar"': '"conta_pagar_baixar"',
        
        "'movimentocaixa_add'": "'movimentacao_caixa_add'",
        '"movimentocaixa_add"': '"movimentacao_caixa_add"',
        
        "'categoriafinanceira_list'": "'categoria_financeira_list'",
        '"categoriafinanceira_list"': '"categoria_financeira_list"',
        "'categoriafinanceira_add'": "'categoria_financeira_add'",
        '"categoriafinanceira_add"': '"categoria_financeira_add"',
        "'categoriafinanceira_edit'": "'categoria_financeira_edit'",
        '"categoriafinanceira_edit"': '"categoria_financeira_edit"',
        "'categoriafinanceira_delete'": "'categoria_financeira_delete'",
        '"categoriafinanceira_delete"': '"categoria_financeira_delete"',
        
        "'centrocusto_list'": "'centro_custo_list'",
        '"centrocusto_list"': '"centro_custo_list"',
        "'centrocusto_add'": "'centro_custo_add'",
        '"centrocusto_add"': '"centro_custo_add"',
        "'centrocusto_edit'": "'centro_custo_edit'",
        '"centrocusto_edit"': '"centro_custo_edit"',
        "'centrocusto_delete'": "'centro_custo_delete'",
        '"centrocusto_delete"': '"centro_custo_delete"',
        
        "'orcamentofinanceiro_list'": "'orcamento_financeiro_list'",
        '"orcamentofinanceiro_list"': '"orcamento_financeiro_list"',
        "'orcamentofinanceiro_add'": "'orcamento_financeiro_add'",
        '"orcamentofinanceiro_add"': '"orcamento_financeiro_add"',
        "'orcamentofinanceiro_edit'": "'orcamento_financeiro_edit'",
        '"orcamentofinanceiro_edit"': '"orcamento_financeiro_edit"',
        "'orcamentofinanceiro_delete'": "'orcamento_financeiro_delete'",
        '"orcamentofinanceiro_delete"': '"orcamento_financeiro_delete"',
        
        # Estoque
        "'movimentacaoestoque_list'": "'movimentacao_estoque_list'",
        '"movimentacaoestoque_list"': '"movimentacao_estoque_list"',
        "'movimentacaoestoque_add'": "'movimentacao_estoque_add'",
        '"movimentacaoestoque_add"': '"movimentacao_estoque_add"',
        "'movimentacaoestoque_edit'": "'movimentacao_estoque_edit'",
        '"movimentacaoestoque_edit"': '"movimentacao_estoque_edit"',
        "'movimentacaoestoque_delete'": "'movimentacao_estoque_delete'",
        '"movimentacaoestoque_delete"': '"movimentacao_estoque_delete"',
    }
    
    print("\n" + "=" * 60)
    print("🔄 Atualizando {% url %} nos templates...")
    print("=" * 60)
    
    arquivos_modificados = 0
    total_substituicoes = 0
    
    for html_file in base_path.rglob("*.html"):
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            substituicoes_no_arquivo = 0
            
            for old_url, new_url in URL_RENAMES.items():
                count = content.count(old_url)
                if count > 0:
                    content = content.replace(old_url, new_url)
                    substituicoes_no_arquivo += count
                    total_substituicoes += count
            
            if content != original_content:
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                rel_path = html_file.relative_to(base_path)
                print(f"✅ {rel_path} ({substituicoes_no_arquivo} substituições)")
                arquivos_modificados += 1
                
        except Exception as e:
            print(f"❌ Erro em {html_file}: {e}")
    
    print("-" * 60)
    print(f"📊 Resumo das URLs:")
    print(f"   ✅ Arquivos modificados: {arquivos_modificados}")
    print(f"   🔄 Total de substituições: {total_substituicoes}")
    
    return arquivos_modificados


def main():
    """Função principal"""
    print("=" * 60)
    print("🚀 ERP SERVICES BI - RENOMEADOR DE TEMPLATES")
    print("=" * 60)
    print()
    
    # 1. Renomear arquivos (se ainda existirem com nome antigo)
    rename_templates(BASE_DIR)
    
    # 2. SEMPRE atualizar URLs nos templates (independente de renomeação)
    print("\n" + "-" * 60)
    print("🔄 Atualizando referências de URL nos templates...")
    print("-" * 60)
    update_url_tags_in_templates(BASE_DIR)
    
    print("\n" + "=" * 60)
    print("✨ Processo concluído!")
    print("=" * 60)
    print("\n⚠️  Lembre-se de:")
    print("   1. Verificar se todos os templates foram renomeados corretamente")
    print("   2. Testar as páginas no navegador")
    print("   3. Commitar as mudanças no git")
    print()


if __name__ == "__main__":
    main()