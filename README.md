# 🟡A/B Cashback Analyzer

Solução reutilizável para análise automática de testes A/B de cashback do time de Growth.

## O que faz

Recebe qualquer CSV de teste A/B no schema padrão da e entrega:

- **Relatório HTML completo** — apresentável para gestores, com métricas consolidadas, gráficos SVG inline e testes de significância estatística
- **Decisão acionável** — qual variante escalar para 100% do tráfego, com justificativa quantitativa
- **Registro automático** em `resultados_testes.csv` — planilha de acompanhamento de todos os testes rodados

## Requisitos

```bash
pip install pandas scipy
```

Python 3.8+

## Como usar

```bash
# Análise de um dataset
python analyze.py caminho/para/dataset.csv

# Exemplos com os 3 datasets do case
python analyze.py dataset_01_parceiroA.csv
python analyze.py dataset_02_parceiroB.csv
python analyze.py dataset_03_parceiroC.csv
```

Ao rodar, são gerados automaticamente:
- `reports/relatorio_parceiro_x.html` — relatório visual do teste
- `resultados_testes.csv` — linha adicionada com o resultado

## Schema esperado dos CSVs

| Coluna | Tipo | Descrição |
|---|---|---|
| Data | YYYY-MM-DD | Data da observação |
| Grupos de usuários | string | Variante do teste (Grupo 1, Grupo 2...) |
| Parceiro | string | Nome do parceiro |
| compradores | int | Usuários únicos que compraram no dia |
| comissão | string (R$) | Comissão paga pelo parceiro |
| cashback | string (R$) | Cashback distribuído aos usuários |
| vendas totais | string (R$) | GMV do dia |

## Metodologia

### Métricas principais
- **Lucro líquido** = comissão − cashback (métrica principal de decisão)
- **Margem líquida** = lucro líquido / vendas totais
- **Taxa de cashback** = cashback / vendas totais
- **ROI do cashback** = vendas totais / cashback

### Testes estatísticos
- **2 grupos:** t-test independente (Welch)
- **3+ grupos:** ANOVA one-way + t-tests par a par

### Critério de decisão
O grupo com maior **lucro líquido total** no período é recomendado para escalar.
A significância estatística é calculada comparando o melhor vs. o pior grupo em compradores/dia.

### Legenda de significância
- ★★★ p < 0.01 — Altamente significativo
- ★★ p < 0.05 — Significativo
- ★ p < 0.10 — Tendência
- ✗ p ≥ 0.10 — Não significativo

## Usando com IA (Claude Code / Cursor / ChatGPT)

Esta solução foi desenhada para ser acionada em linguagem natural:

> "Analise o teste A/B do Parceiro D usando o arquivo dataset_04_parceiroD.csv"

O agente roda:
```bash
python analyze.py dataset_04_parceiroD.csv
```

E retorna o relatório HTML + decisão. Nenhuma alteração de código necessária — basta indicar o novo arquivo.

## Resultados dos 3 Datasets

| Parceiro | Período | Decisão | Margem | Cashback | Significância |
|---|---|---|---|---|---|
| Parceiro A | Jan–Abr 2011 | Escalar Grupo 1 (4,16% cashback) | 7,22% | 4,16% | ★★ Significativo |
| Parceiro B | Mai–Jun 2011 | Escalar Grupo 1 (4,00% cashback) | 7,00% | 4,00% | ★★★ Altamente Significativo |
| Parceiro C | Jul–Ago 2011 | Escalar Grupo 1 (5,00% cashback) | 2,00% | 5,00% | ✗ Não significativo* |

*Parceiro C: diferença não significativa entre grupos. Recomendar extensão do teste ou manter menor cashback pela margem superior.

## Estrutura do projeto

```
meliuz_ab_analyzer/
├── analyze.py              # Script principal (único arquivo para rodar)
├── README.md               # Este arquivo
├── resultados_testes.csv   # Planilha de acompanhamento (gerada automaticamente)
└── reports/
    ├── relatorio_parceiro_a.html
    ├── relatorio_parceiro_b.html
    └── relatorio_parceiro_c.html
```
