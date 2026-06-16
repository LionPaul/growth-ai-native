#!/usr/bin/env python3
"""
Méliuz A/B Cashback Test Analyzer
==================================
Uso:
    python analyze.py <caminho_do_csv>

Exemplo:
    python analyze.py dataset_01_parceiroA.csv
    python analyze.py dataset_02_parceiroB.csv
    python analyze.py dataset_03_parceiroC.csv

Saída:
    - Relatório HTML em reports/relatorio_<parceiro>.html
    - Linha adicionada em resultados_testes.csv
"""

import sys
import os
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime
import json

# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def parse_brl(series: pd.Series) -> pd.Series:
    """Converte strings R$ XX.XXX,XX → float."""
    return (
        series.astype(str)
        .str.replace("R$ ", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )


def significance_label(p: float) -> str:
    if p < 0.01:
        return "★★★ Altamente significativo (p<0.01)"
    elif p < 0.05:
        return "★★ Significativo (p<0.05)"
    elif p < 0.10:
        return "★ Tendência (p<0.10)"
    else:
        return "✗ Não significativo (p≥0.10)"


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ──────────────────────────────────────────────────────────────────────────────
# CORE ANALYSIS
# ──────────────────────────────────────────────────────────────────────────────

def analyze(csv_path: str) -> dict:
    df = pd.read_csv(csv_path)

    # Parsear valores monetários
    df["comissao"] = parse_brl(df["comissão"])
    df["cashback_val"] = parse_brl(df["cashback"])
    df["vendas"] = parse_brl(df["vendas totais"])
    df["lucro_liquido"] = df["comissao"] - df["cashback_val"]
    df["margem_liquida"] = df["lucro_liquido"] / df["vendas"]
    df["taxa_cashback"] = df["cashback_val"] / df["vendas"]
    df["taxa_comissao"] = df["comissao"] / df["vendas"]
    df["ticket_medio"] = df["vendas"] / df["compradores"]

    parceiro = df["Parceiro"].iloc[0]
    grupos = sorted(df["Grupos de usuários"].unique())
    periodo = f"{df['Data'].min()} → {df['Data'].max()}"
    n_grupos = len(grupos)

    # ── Métricas agregadas por grupo ──────────────────────────────────────────
    agg = df.groupby("Grupos de usuários").agg(
        dias=("Data", "count"),
        compradores_total=("compradores", "sum"),
        compradores_medio=("compradores", "mean"),
        vendas_total=("vendas", "sum"),
        comissao_total=("comissao", "sum"),
        cashback_total=("cashback_val", "sum"),
        lucro_total=("lucro_liquido", "sum"),
    ).reset_index()

    agg["margem_liquida"] = agg["lucro_total"] / agg["vendas_total"]
    agg["taxa_cashback"] = agg["cashback_total"] / agg["vendas_total"]
    agg["taxa_comissao"] = agg["comissao_total"] / agg["vendas_total"]
    agg["roi_cashback"] = agg["vendas_total"] / agg["cashback_total"]
    agg["ticket_medio"] = agg["vendas_total"] / agg["compradores_total"]

    # ── Testes estatísticos ───────────────────────────────────────────────────
    group_compradores = {g: df[df["Grupos de usuários"] == g]["compradores"].values for g in grupos}
    group_vendas = {g: df[df["Grupos de usuários"] == g]["vendas"].values for g in grupos}

    stat_results = {}

    if n_grupos == 2:
        g1, g2 = grupos
        t_comp, p_comp = stats.ttest_ind(group_compradores[g1], group_compradores[g2])
        t_vend, p_vend = stats.ttest_ind(group_vendas[g1], group_vendas[g2])
        stat_results["compradores"] = {
            "test": "t-test independente",
            "statistic": round(t_comp, 3),
            "p_value": round(p_comp, 4),
            "label": significance_label(p_comp),
        }
        stat_results["vendas"] = {
            "test": "t-test independente",
            "statistic": round(t_vend, 3),
            "p_value": round(p_vend, 4),
            "label": significance_label(p_vend),
        }
        comparisons = [(g1, g2)]
    else:
        vals = [group_compradores[g] for g in grupos]
        F, p_anova = stats.f_oneway(*vals)
        stat_results["compradores_anova"] = {
            "test": "ANOVA one-way",
            "statistic": round(F, 3),
            "p_value": round(p_anova, 4),
            "label": significance_label(p_anova),
        }
        comparisons = []
        for i in range(n_grupos):
            for j in range(i + 1, n_grupos):
                g1, g2 = grupos[i], grupos[j]
                t, p = stats.ttest_ind(group_compradores[g1], group_compradores[g2])
                tv, pv = stats.ttest_ind(group_vendas[g1], group_vendas[g2])
                comparisons.append((g1, g2))
                stat_results[f"{g1} vs {g2} - compradores"] = {
                    "test": "t-test",
                    "statistic": round(t, 3),
                    "p_value": round(p, 4),
                    "label": significance_label(p),
                }
                stat_results[f"{g1} vs {g2} - vendas"] = {
                    "test": "t-test",
                    "statistic": round(tv, 3),
                    "p_value": round(pv, 4),
                    "label": significance_label(pv),
                }

    # ── Decisão ───────────────────────────────────────────────────────────────
    # Regra: maximizar lucro líquido total com significância estatística
    best_grupo = agg.loc[agg["lucro_total"].idxmax(), "Grupos de usuários"]
    best_row = agg[agg["Grupos de usuários"] == best_grupo].iloc[0]

    # Verificar se há diferença significativa de compradores entre melhor e pior
    worst_grupo = agg.loc[agg["lucro_total"].idxmin(), "Grupos de usuários"]
    t_dec, p_dec = stats.ttest_ind(
        group_compradores[best_grupo], group_compradores[worst_grupo]
    )
    decisao_stat_label = significance_label(p_dec)

    # Montar decisão textual
    if best_row["margem_liquida"] <= 0:
        decisao = f"ATENÇÃO: Nenhum grupo apresenta lucro líquido positivo. Revisar estrutura de cashback antes de escalar."
        decisao_grupo = "Nenhum"
    else:
        decisao = (
            f"Escalar {best_grupo} para 100% do tráfego. "
            f"Margem líquida: {pct(best_row['margem_liquida'])} | "
            f"Lucro total no período: {brl(best_row['lucro_total'])} | "
            f"Taxa cashback: {pct(best_row['taxa_cashback'])}"
        )
        decisao_grupo = best_grupo

    return {
        "parceiro": parceiro,
        "periodo": periodo,
        "grupos": grupos,
        "n_grupos": n_grupos,
        "agg": agg,
        "stat_results": stat_results,
        "comparisons": comparisons,
        "best_grupo": best_grupo,
        "decisao": decisao,
        "decisao_grupo": decisao_grupo,
        "df": df,
        "p_decisao": p_dec,
        "decisao_stat_label": decisao_stat_label,
    }


# ──────────────────────────────────────────────────────────────────────────────
# HTML REPORT GENERATOR
# ──────────────────────────────────────────────────────────────────────────────

def generate_html_report(result: dict, output_path: str):
    agg = result["agg"]
    parceiro = result["parceiro"]
    grupos = result["grupos"]
    periodo = result["periodo"]
    stat_results = result["stat_results"]
    best_grupo = result["best_grupo"]
    decisao = result["decisao"]
    decisao_stat_label = result["decisao_stat_label"]

    # Paleta de cores por grupo
    cores = ["#4F81BD", "#C0504D", "#9BBB59", "#8064A2"]
    grupo_cores = {g: cores[i % len(cores)] for i, g in enumerate(grupos)}

    # ── Linhas da tabela resumo ───────────────────────────────────────────────
    rows_html = ""
    for _, row in agg.iterrows():
        grupo = row["Grupos de usuários"]
        destaque = ' style="background:#fffde7;font-weight:bold;"' if grupo == best_grupo else ""
        badge = ' <span style="background:#27ae60;color:#fff;padding:2px 7px;border-radius:10px;font-size:11px;">✓ RECOMENDADO</span>' if grupo == best_grupo else ""
        rows_html += f"""
        <tr{destaque}>
            <td>{grupo}{badge}</td>
            <td style="color:{grupo_cores[grupo]};font-weight:bold;">{pct(row['taxa_cashback'])}</td>
            <td style="color:{grupo_cores[grupo]};font-weight:bold;">{pct(row['taxa_comissao'])}</td>
            <td>{int(row['compradores_total']):,}</td>
            <td>{brl(row['vendas_total'])}</td>
            <td>{brl(row['comissao_total'])}</td>
            <td>{brl(row['cashback_total'])}</td>
            <td style="color:{'#27ae60' if row['lucro_total'] > 0 else '#e74c3c'};font-weight:bold;">{brl(row['lucro_total'])}</td>
            <td style="color:{'#27ae60' if row['margem_liquida'] > 0 else '#e74c3c'};font-weight:bold;">{pct(row['margem_liquida'])}</td>
            <td>{brl(row['ticket_medio'])}</td>
        </tr>"""

    # ── Linhas de testes estatísticos ────────────────────────────────────────
    stat_rows = ""
    for key, val in stat_results.items():
        stat_rows += f"""
        <tr>
            <td>{key}</td>
            <td>{val['test']}</td>
            <td>{val['statistic']}</td>
            <td>{val['p_value']}</td>
            <td>{val['label']}</td>
        </tr>"""

    # ── Bar chart SVG inline ──────────────────────────────────────────────────
    max_lucro = agg["lucro_total"].abs().max()
    bar_width = 80
    gap = 40
    chart_w = len(grupos) * (bar_width + gap) + gap
    max_bar_h = 140

    bars_svg = ""
    labels_svg = ""
    for i, row in agg.iterrows():
        g = row["Grupos de usuários"]
        lucro = row["lucro_total"]
        bar_h = max(5, abs(lucro) / max_lucro * max_bar_h) if max_lucro > 0 else 5
        x = gap + i * (bar_width + gap)
        y = 20 + max_bar_h - bar_h if lucro >= 0 else 20 + max_bar_h
        fill = "#27ae60" if lucro >= 0 else "#e74c3c"
        if g == best_grupo:
            fill = "#1a7a46"
        bars_svg += f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_h}" fill="{fill}" rx="4"/>'
        bars_svg += f'<text x="{x + bar_width/2}" y="{y - 5 if lucro >= 0 else y + bar_h + 14}" text-anchor="middle" font-size="11" fill="#333">{brl(lucro)}</text>'
        labels_svg += f'<text x="{x + bar_width/2}" y="{20 + max_bar_h + 30}" text-anchor="middle" font-size="12" fill="{grupo_cores[g]}" font-weight="bold">{g}</text>'

    svg_chart = f"""
    <svg viewBox="0 0 {chart_w} {max_bar_h + 70}" xmlns="http://www.w3.org/2000/svg" style="max-width:500px;display:block;margin:auto;">
        <line x1="0" y1="{20 + max_bar_h}" x2="{chart_w}" y2="{20 + max_bar_h}" stroke="#ccc" stroke-width="1"/>
        {bars_svg}
        {labels_svg}
        <text x="{chart_w/2}" y="{max_bar_h + 65}" text-anchor="middle" font-size="11" fill="#999">Lucro Líquido por Grupo (R$)</text>
    </svg>"""

    # ── Gráfico compradores ───────────────────────────────────────────────────
    max_comp = agg["compradores_total"].max()
    bars_comp = ""
    labels_comp = ""
    for i, row in agg.iterrows():
        g = row["Grupos de usuários"]
        val = row["compradores_total"]
        bar_h = max(5, val / max_comp * max_bar_h) if max_comp > 0 else 5
        x = gap + i * (bar_width + gap)
        y = 20 + max_bar_h - bar_h
        fill = grupo_cores[g]
        if g == best_grupo:
            fill = "#1a7a46"
        bars_comp += f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_h}" fill="{fill}" rx="4"/>'
        bars_comp += f'<text x="{x + bar_width/2}" y="{y - 5}" text-anchor="middle" font-size="11" fill="#333">{int(val):,}</text>'
        labels_comp += f'<text x="{x + bar_width/2}" y="{20 + max_bar_h + 30}" text-anchor="middle" font-size="12" fill="{grupo_cores[g]}" font-weight="bold">{g}</text>'

    svg_comp = f"""
    <svg viewBox="0 0 {chart_w} {max_bar_h + 70}" xmlns="http://www.w3.org/2000/svg" style="max-width:500px;display:block;margin:auto;">
        <line x1="0" y1="{20 + max_bar_h}" x2="{chart_w}" y2="{20 + max_bar_h}" stroke="#ccc" stroke-width="1"/>
        {bars_comp}
        {labels_comp}
        <text x="{chart_w/2}" y="{max_bar_h + 65}" text-anchor="middle" font-size="11" fill="#999">Total de Compradores por Grupo</text>
    </svg>"""

    # ── Cashback rate comparativo ─────────────────────────────────────────────
    cashback_rates = " | ".join(
        f'<span style="color:{grupo_cores[g]};font-weight:bold;">{g}: {pct(agg[agg["Grupos de usuários"]==g]["taxa_cashback"].iloc[0])}</span>'
        for g in grupos
    )

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Análise A/B — {parceiro} | Méliuz</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f4f6f9; color: #222; }}
  .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%); color: #fff; padding: 32px 40px; }}
  .header h1 {{ font-size: 26px; font-weight: 700; }}
  .header .sub {{ font-size: 14px; opacity: 0.75; margin-top: 6px; }}
  .badge-meliuz {{ display:inline-block; background:#e8b800; color:#1a1a2e; font-weight:700; font-size:12px; padding:3px 10px; border-radius:12px; margin-right:10px; }}
  .container {{ max-width: 1100px; margin: 32px auto; padding: 0 20px; }}
  .card {{ background: #fff; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.07); margin-bottom: 24px; overflow: hidden; }}
  .card-header {{ background: #f8f9fb; border-bottom: 1px solid #eee; padding: 16px 24px; font-size: 16px; font-weight: 600; color: #333; display:flex; align-items:center; gap:10px; }}
  .card-header .icon {{ font-size:20px; }}
  .card-body {{ padding: 24px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th {{ background: #1a1a2e; color: #fff; padding: 10px 14px; text-align: left; font-weight: 600; }}
  td {{ padding: 10px 14px; border-bottom: 1px solid #f0f0f0; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #fafafa; }}
  .decision-box {{ background: linear-gradient(135deg, #1a7a46, #27ae60); color: #fff; border-radius: 12px; padding: 24px 28px; margin-bottom: 24px; }}
  .decision-box h2 {{ font-size: 18px; margin-bottom: 10px; }}
  .decision-box p {{ font-size: 15px; line-height: 1.6; opacity: 0.95; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }}
  .kpi {{ background: #fff; border-radius: 10px; padding: 18px 20px; box-shadow: 0 1px 8px rgba(0,0,0,0.06); text-align:center; }}
  .kpi .label {{ font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }}
  .kpi .value {{ font-size: 22px; font-weight: 700; color: #1a1a2e; }}
  .kpi .grupo {{ font-size: 11px; color: #27ae60; margin-top: 4px; font-weight: 600; }}
  .stat-note {{ font-size: 13px; color: #666; margin-top: 8px; font-style:italic; }}
  .charts-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
  @media (max-width: 700px) {{ .charts-grid {{ grid-template-columns: 1fr; }} }}
  .footer {{ text-align:center; color:#aaa; font-size:12px; margin: 30px 0 20px; }}
  .tag {{ display:inline-block; padding:2px 8px; border-radius:8px; font-size:11px; font-weight:600; }}
  .tag-green {{ background:#e8f8f0; color:#27ae60; }}
  .tag-red {{ background:#fdecea; color:#e74c3c; }}
  .tag-yellow {{ background:#fefce8; color:#b7791f; }}
</style>
</head>
<body>

<div class="header">
  <h1><span class="badge-meliuz">Méliuz</span>Relatório de Teste A/B — {parceiro}</h1>
  <div class="sub">📅 Período: {periodo} &nbsp;|&nbsp; 📊 {result['n_grupos']} grupos testados &nbsp;|&nbsp; Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
</div>

<div class="container">

  <!-- DECISÃO -->
  <div class="decision-box">
    <h2>🎯 Decisão Recomendada</h2>
    <p>{decisao}</p>
    <p style="margin-top:10px;font-size:13px;opacity:0.85;">Significância estatística (melhor vs. pior): {decisao_stat_label}</p>
  </div>

  <!-- KPIs do melhor grupo -->
  {''.join([f"""
  <div class="kpi-grid">
    <div class="kpi">
      <div class="label">Taxa Cashback</div>
      <div class="value">{pct(agg[agg['Grupos de usuários']==best_grupo]['taxa_cashback'].iloc[0])}</div>
      <div class="grupo">✓ {best_grupo}</div>
    </div>
    <div class="kpi">
      <div class="label">Margem Líquida</div>
      <div class="value">{pct(agg[agg['Grupos de usuários']==best_grupo]['margem_liquida'].iloc[0])}</div>
      <div class="grupo">✓ {best_grupo}</div>
    </div>
    <div class="kpi">
      <div class="label">Lucro Total</div>
      <div class="value">{brl(agg[agg['Grupos de usuários']==best_grupo]['lucro_total'].iloc[0])}</div>
      <div class="grupo">✓ {best_grupo}</div>
    </div>
    <div class="kpi">
      <div class="label">Compradores</div>
      <div class="value">{int(agg[agg['Grupos de usuários']==best_grupo]['compradores_total'].iloc[0]):,}</div>
      <div class="grupo">✓ {best_grupo}</div>
    </div>
    <div class="kpi">
      <div class="label">ROI do Cashback</div>
      <div class="value">{agg[agg['Grupos de usuários']==best_grupo]['roi_cashback'].iloc[0]:.1f}x</div>
      <div class="grupo">✓ {best_grupo}</div>
    </div>
  </div>
  """])}

  <!-- TABELA COMPLETA -->
  <div class="card">
    <div class="card-header"><span class="icon">📋</span> Métricas Consolidadas por Grupo</div>
    <div class="card-body" style="overflow-x:auto;">
      <table>
        <thead>
          <tr>
            <th>Grupo</th>
            <th>Taxa Cashback</th>
            <th>Taxa Comissão</th>
            <th>Compradores</th>
            <th>Vendas Totais</th>
            <th>Comissão</th>
            <th>Cashback Gasto</th>
            <th>Lucro Líquido</th>
            <th>Margem Líquida</th>
            <th>Ticket Médio</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </div>
  </div>

  <!-- GRÁFICOS -->
  <div class="charts-grid">
    <div class="card">
      <div class="card-header"><span class="icon">💰</span> Lucro Líquido por Grupo</div>
      <div class="card-body">{svg_chart}</div>
    </div>
    <div class="card">
      <div class="card-header"><span class="icon">👥</span> Total de Compradores</div>
      <div class="card-body">{svg_comp}</div>
    </div>
  </div>

  <!-- TESTES ESTATÍSTICOS -->
  <div class="card">
    <div class="card-header"><span class="icon">🔬</span> Testes de Significância Estatística</div>
    <div class="card-body" style="overflow-x:auto;">
      <table>
        <thead>
          <tr>
            <th>Comparação</th>
            <th>Teste</th>
            <th>Estatística</th>
            <th>p-value</th>
            <th>Resultado</th>
          </tr>
        </thead>
        <tbody>
          {stat_rows}
        </tbody>
      </table>
      <p class="stat-note">* p &lt; 0.05 indica diferença estatisticamente significativa entre os grupos.</p>
    </div>
  </div>

  <!-- CONTEXTO E INTERPRETAÇÃO -->
  <div class="card">
    <div class="card-header"><span class="icon">💡</span> Interpretação & Contexto</div>
    <div class="card-body">
      <p style="margin-bottom:12px;"><strong>Taxas de cashback testadas:</strong> {cashback_rates}</p>
      <p style="line-height:1.8;">
        O teste mediu o impacto de diferentes percentuais de cashback sobre o comportamento de compra dos usuários.
        A métrica principal de decisão é o <strong>lucro líquido</strong> (comissão recebida do parceiro menos cashback distribuído aos usuários).
        A métrica secundária é o <strong>volume de compradores</strong>, que indica engajamento da base.
      </p>
      <p style="margin-top:12px;line-height:1.8;">
        <strong>Nota sobre significância:</strong> resultados com p &lt; 0.05 indicam que as diferenças observadas dificilmente ocorreram ao acaso.
        Resultados marginalmente significativos (0.05 &lt; p &lt; 0.10) devem ser tratados com cautela —
        pode ser necessário estender o teste ou aumentar o tamanho da amostra.
      </p>
    </div>
  </div>

</div>

<div class="footer">
  Méliuz · Time de Growth · Análise automatizada por Méliuz A/B Analyzer
</div>

</body>
</html>"""

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Relatório salvo em: {output_path}")


# ──────────────────────────────────────────────────────────────────────────────
# REGISTRO EM CSV DE ACOMPANHAMENTO
# ──────────────────────────────────────────────────────────────────────────────

def register_in_tracker(result: dict, tracker_path: str = "resultados_testes.csv"):
    agg = result["agg"]
    best_grupo = result["best_grupo"]
    best_row = agg[agg["Grupos de usuários"] == best_grupo].iloc[0]
    grupos_str = " / ".join(result["grupos"])

    # Extrair cashback rates
    cashback_rates = " | ".join(
        f"{g}: {pct(agg[agg['Grupos de usuários']==g]['taxa_cashback'].iloc[0])}"
        for g in result["grupos"]
    )

    new_row = {
        "data_analise": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "nome_teste": f"Teste A/B — {result['parceiro']}",
        "parceiro": result["parceiro"],
        "periodo": result["periodo"],
        "grupos_testados": grupos_str,
        "cashback_rates": cashback_rates,
        "descricao": f"Teste de variação de cashback com {result['n_grupos']} grupos. Período: {result['periodo']}.",
        "grupo_vencedor": best_grupo,
        "taxa_cashback_vencedor": pct(best_row["taxa_cashback"]),
        "margem_liquida_vencedor": pct(best_row["margem_liquida"]),
        "lucro_total_vencedor": brl(best_row["lucro_total"]),
        "compradores_vencedor": int(best_row["compradores_total"]),
        "vendas_totais_vencedor": brl(best_row["vendas_total"]),
        "significancia_estatistica": result["decisao_stat_label"],
        "decisao": result["decisao"],
    }

    file_exists = os.path.isfile(tracker_path)
    df_new = pd.DataFrame([new_row])
    if file_exists:
        df_existing = pd.read_csv(tracker_path)
        df_final = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_final = df_new
    df_final.to_csv(tracker_path, index=False, encoding="utf-8-sig")
    print(f"✅ Resultado registrado em: {tracker_path}")


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    csv_path = sys.argv[1]
    if not os.path.isfile(csv_path):
        print(f"❌ Arquivo não encontrado: {csv_path}")
        sys.exit(1)

    print(f"\n🔍 Analisando: {csv_path}")
    result = analyze(csv_path)

    parceiro_slug = result["parceiro"].lower().replace(" ", "_")
    os.makedirs("reports", exist_ok=True)
    report_path = f"reports/relatorio_{parceiro_slug}.html"

    generate_html_report(result, report_path)
    register_in_tracker(result, "resultados_testes.csv")

    print(f"\n{'='*60}")
    print(f"📊 PARCEIRO: {result['parceiro']}")
    print(f"📅 PERÍODO:  {result['periodo']}")
    print(f"🏆 DECISÃO:  {result['decisao']}")
    print(f"{'='*60}\n")
