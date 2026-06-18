# 🟡 A/B Cashback Analyzer

Solução reutilizável para análise automática de testes A/B de cashback do time de Growth.

Duas formas de usar, mesma metodologia:

| | Script (`analyze.py`) | Prompt Mestre (`PROMPT_MESTRE.md`) |
|---|---|---|
| **Como roda** | `python analyze.py dataset.csv` | Cola o prompt + CSV em qualquer IA (Claude, ChatGPT, Gemini...) |
| **Requer instalar algo** | Sim (Python + pandas + scipy) | Não |
| **Precisão estatística** | Exata (scipy real) | Aproximada, salvo se a IA executar código |
| **Saída** | HTML + linha de CSV, automaticamente | Markdown + linha de CSV, no próprio chat |
| **Melhor para** | Decisões de alto risco, rodar em lote, time técnico | Exploração rápida, perguntas de follow-up, time não-técnico |

> Veja a seção [Qual opção usar](#-qual-opção-usar) para o detalhamento completo do trade-off.

---

## Opção 1 — Script Python (`analyze.py`)

### O que faz

Recebe qualquer CSV de teste A/B no schema padrão e entrega:

- **Relatório HTML completo** — apresentável para gestores, com métricas consolidadas, gráficos SVG inline e testes de significância estatística
- **Decisão acionável** — qual variante escalar para 100% do tráfego, com justificativa quantitativa
- **Registro automático** em `resultados_testes.csv` — planilha de acompanhamento de todos os testes rodados

### Requisitos

```bash
pip install pandas scipy
```

Python 3.8+

### Como usar

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

### Usando com IA (Claude Code / Cursor / ChatGPT com terminal)

Esta solução foi desenhada para ser acionada em linguagem natural por um agente
com acesso a terminal:

> "Analise o teste A/B do Parceiro D usando o arquivo dataset_04_parceiroD.csv"

O agente roda:
```bash
python analyze.py dataset_04_parceiroD.csv
```

E retorna o relatório HTML + decisão. Nenhuma alteração de código necessária — basta indicar o novo arquivo.

---

## Opção 2 — Prompt Mestre (`PROMPT_MESTRE.md`)

Para quem quer rodar a análise **sem instalar nada**, direto em uma IA de chat
(Claude, ChatGPT, Gemini) ou em um agente (Claude Code, Cursor).

### Como usar

1. Abra [`PROMPT_MESTRE.md`](./PROMPT_MESTRE.md)
2. Copie o conteúdo do bloco de código (entre as crases)
3. Cole em qualquer IA, anexando o CSV do teste a ser analisado
4. Receba: validação de qualidade dos dados, métricas comparativas, teste de
   significância, decisão recomendada e a linha pronta para colar na planilha
   de acompanhamento

O mesmo texto do prompt funciona para qualquer parceiro, período e número de
grupos — não precisa editar nada, só trocar o CSV anexado.

**Dica:** se a IA usada tiver execução de código (Code Interpreter / Claude
com bash / agentes com terminal), peça explicitamente para ela rodar o cálculo
em Python — isso garante que o p-value seja exato, em vez de estimado.

---

## 🎯 Qual opção usar

| Cenário | Recomendado |
|---|---|
| Decisão de alto risco / orçamento grande | `analyze.py` (cálculo exato, reprodutível) |
| Exploração rápida, perguntas de follow-up, "e se..." | Prompt Mestre |
| Volume alto de testes (rodar em lote) | `analyze.py` |
| Pessoa não-técnica do time quer rodar sozinha | Prompt Mestre (sem precisar instalar Python) |
| Precisão estatística é crítica (p-value exato) | `analyze.py` (usa scipy de verdade, IA pode estimar errado) |

Na prática, o ideal é usar as duas de forma complementar: o script para o
registro oficial na planilha de acompanhamento, e o prompt mestre para
qualquer pessoa do time investigar um teste rapidamente sem esperar alguém
"técnico" rodar um script.

---

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

## Metodologia (comum às duas opções)

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

### Robustez a dados ruins
Ambas as opções foram desenhadas para lidar com datasets imperfeitos: valores
nulos, grupos desbalanceados, inconsistências contábeis (comissão/cashback
maior que vendas) e amostras pequenas. O Prompt Mestre inclui um passo
explícito de validação que reporta esses problemas antes de qualquer cálculo;
o script assume dados já no formato especificado, mas pode ser estendido com
validações adicionais se necessário.

## Resultados dos 3 Datasets

| Parceiro | Período | Decisão | Margem | Cashback | Significância |
|---|---|---|---|---|---|
| Parceiro A | Jan–Abr 2011 | Escalar Grupo 1 (4,16% cashback) | 7,22% | 4,16% | ★★ Significativo |
| Parceiro B | Mai–Jun 2011 | Escalar Grupo 1 (4,00% cashback) | 7,00% | 4,00% | ★★★ Altamente Significativo |
| Parceiro C | Jul–Ago 2011 | Escalar Grupo 1 (5,00% cashback) | 2,00% | 5,00% | ✗ Não significativo* |

*Parceiro C: diferença não significativa entre grupos. Recomendar extensão do teste ou manter menor cashback pela margem superior.

## Estrutura do projeto

```
├── analyze.py              # Opção 1: script reutilizável
├── PROMPT_MESTRE.md         # Opção 2: prompt para usar em qualquer IA
├── README.md                # Este arquivo
├── resultados_testes.csv    # Planilha de acompanhamento (gerada automaticamente)
└── reports/
    ├── relatorio_parceiro_a.html
    ├── relatorio_parceiro_b.html
    └── relatorio_parceiro_c.html
```
