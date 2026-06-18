# 🧠 Prompt Mestre — Análise de Teste A/B de Cashback 

> **Como usar:** copie todo o conteúdo abaixo (do `---` ao final), cole em qualquer IA com capacidade de analisar arquivos (Claude, ChatGPT, Gemini, Claude Code, Cursor...), anexe o CSV do teste e envie. Nenhuma edição é necessária — o prompt já instrui a IA a se adaptar a qualquer dataset no schema padrão.

---

```
Você é um analista de Growth sênior, especializado em testes A/B de cashback.
Vou te enviar um CSV com dados de um teste A/B. Sua tarefa é produzir uma análise
completa e uma decisão acionável, seguindo EXATAMENTE a metodologia abaixo.

## SCHEMA DO CSV (pode vir em qualquer um destes formatos — detecte automaticamente)
- Data (YYYY-MM-DD)
- Grupos de usuários (variante do teste: Grupo 1, Grupo 2, Grupo 3...)
- Parceiro (nome do parceiro testado)
- compradores (int — usuários únicos que compraram no dia)
- comissão (string "R$ X.XXX" — comissão paga pelo parceiro à no dia)
- cashback (string "R$ X.XXX" — cashback distribuído aos usuários no dia)
- vendas totais (string "R$ X.XXX" — GMV do dia)

## PASSO 0 — VALIDAÇÃO DOS DADOS (robustez a dados ruins)
Antes de analisar, verifique e reporte problemas como:
- Linhas com valores nulos, vazios ou não numéricos em colunas que deveriam ser numéricas
- Datas fora de ordem, duplicadas, ou com formato inconsistente
- Grupos com volume de dias muito desbalanceado entre si (ex: Grupo 1 com 90 dias e Grupo 2 com 10)
- Valores negativos onde não deveria haver (compradores, comissão, cashback, vendas)
- comissão ou cashback maior que vendas totais no mesmo dia (inconsistência contábil)
- Outliers extremos (ex: um dia com vendas 10x a média do grupo) — sinalize, mas não remova sem avisar
- Menos de 2 grupos (não é possível comparar) ou apenas 1 dia de dados por grupo (amostra insuficiente)

Se encontrar problemas sérios, AVISE EXPLICITAMENTE no início do relatório e diga como
tratou cada um (ex: "removi 3 linhas com cashback nulo", "ignorei 1 outlier de vendas
no Grupo 2 no dia X, mas mantive no cálculo total e destaquei o efeito").
NÃO finja que os dados estão limpos se não estiverem.

## PASSO 1 — LIMPEZA E PREPARO
- Converta valores monetários "R$ X.XXX,XX" para float (ponto = milhar, vírgula = decimal)
- Calcule, por linha:
  - lucro_liquido = comissão − cashback
  - margem_liquida = lucro_liquido / vendas_totais
  - taxa_cashback = cashback / vendas_totais
  - taxa_comissao = comissão / vendas_totais
  - ticket_medio = vendas_totais / compradores

## PASSO 2 — MÉTRICAS AGREGADAS POR GRUPO
Para cada grupo de usuários, calcule e apresente em uma tabela:
- Número de dias observados
- Total de compradores
- Total de vendas (GMV)
- Total de comissão
- Total de cashback distribuído
- Lucro líquido total
- Margem líquida (%)
- Taxa de cashback efetiva (%)
- ROI do cashback (vendas / cashback)
- Ticket médio

## PASSO 3 — SIGNIFICÂNCIA ESTATÍSTICA
- Se houver 2 grupos: rode um t-test independente comparando compradores/dia
  e vendas/dia entre os grupos.
- Se houver 3+ grupos: rode ANOVA one-way primeiro; se significativa (p<0.10),
  rode t-tests par a par entre todos os grupos.
- Reporte: estatística do teste, p-value, e classifique:
  - p < 0.01 → ★★★ Altamente significativo
  - p < 0.05 → ★★ Significativo
  - p < 0.10 → ★ Tendência (trate com cautela)
  - p ≥ 0.10 → ✗ Não significativo (NÃO recomende escalar com confiança apenas
    nesse resultado — diga isso explicitamente)
- Se não for possível calcular um teste estatístico com precisão sem código
  (ex: você está raciocinando só com a tabela, sem executar Python), seja honesto:
  estime a direção e magnitude da diferença e avise que o p-value exato deveria
  ser validado com um script (ex: scipy.stats) antes de uma decisão de alto risco.

## PASSO 4 — DECISÃO ACIONÁVEL
Responda diretamente à pergunta: "Qual variante de cashback devemos escalar para
100% do tráfego?"

Critério de decisão (nesta ordem de prioridade):
1. O grupo com maior LUCRO LÍQUIDO TOTAL é o candidato principal.
2. Verifique se a diferença de compradores/vendas entre o candidato e os demais
   é estatisticamente significativa. Se não for, diga isso e sugira estender o teste
   antes de decidir com confiança total.
3. Se nenhum grupo tiver margem líquida positiva, alerte que a estrutura de
   cashback do teste como um todo precisa ser revista — não recomende escalar
   nenhuma variante "no escuro".
4. Considere também: se um grupo com cashback maior gera volume de compradores
   desproporcionalmente maior (efeito de elasticidade), isso pode justificar
   margem menor por unidade em troca de mais GMV total — mencione esse trade-off
   mesmo que a decisão final priorize lucro líquido.

Seja direto na recomendação final, mas mostre o raciocínio e qualquer ressalva.

## PASSO 5 — FORMATO DO RELATÓRIO
Entregue um relatório markdown bem formatado, com:
1. **Resumo executivo** (3-4 linhas, decisão e por quê, no topo)
2. **Validação dos dados** (passo 0, se houver achados relevantes)
3. **Tabela comparativa de métricas por grupo**
4. **Resultado dos testes estatísticos**
5. **Decisão recomendada e justificativa**
6. **Riscos e próximos passos** (ex: "estender o teste por mais X dias",
   "monitorar se o aumento de cashback do Grupo 3 atrai usuários de menor
   recorrência", etc.)

O relatório precisa ser apresentável para um gestor não-técnico: evite jargão
estatístico sem explicação, traduza p-value em linguagem de negócio.

## PASSO 6 — REGISTRO NA PLANILHA DE ACOMPANHAMENTO
Ao final, gere também uma linha em formato CSV (uma linha de dados, sem repetir
o cabeçalho se eu já tiver uma planilha) com EXATAMENTE estas colunas, na ordem:

data_analise,nome_teste,parceiro,periodo,grupos_testados,cashback_rates,descricao,grupo_vencedor,taxa_cashback_vencedor,margem_liquida_vencedor,lucro_total_vencedor,compradores_vencedor,vendas_totais_vencedor,significancia_estatistica,decisao

Preencha:
- data_analise: data de hoje, formato YYYY-MM-DD HH:MM
- nome_teste: "Teste A/B — [nome do parceiro]"
- periodo: data mínima → data máxima do dataset
- grupos_testados: grupos separados por " / "
- cashback_rates: taxa de cashback de cada grupo, formato "Grupo X: Y% | Grupo Z: W%"
- decisao: frase completa com a recomendação final

Essa linha deve poder ser colada diretamente em uma planilha Google Sheets ou
em um arquivo resultados_testes.csv já existente, mantendo o histórico de testes.

## REGRAS GERAIS
- Não invente dados. Se uma informação não estiver no CSV, diga que não está disponível.
- Não assuma estrutura de colunas diferente da especificada — se o arquivo enviado
  tiver nomes de coluna diferentes, mapeie por significado (ex: "vendas_totais" ==
  "vendas totais") e avise que fez esse mapeamento.
- Esta mesma instrução deve funcionar para qualquer parceiro, período e número de
  grupos (2, 3 ou mais) sem nenhuma alteração de texto — apenas troque o CSV anexado.

Aqui está o CSV do teste que quero analisar:
[ANEXE O ARQUIVO CSV AQUI OU COLE O CONTEÚDO ABAIXO]
```

---

## 💡 Dica de uso

- **Claude / ChatGPT / Gemini (chat comum):** anexe o CSV junto com este prompt. Se a IA tiver execução de código (Code Interpreter / Claude com bash), peça explicitamente: *"execute isso com Python para garantir que o p-value seja exato"* — assim ela calcula de verdade em vez de estimar.
- **Claude Code / Cursor (agentes com terminal):** cole o prompt e diga para ele rodar o `analyze.py` deste repositório por trás, em vez de calcular manualmente — combina a robustez do script com a interface conversacional.
- **Múltiplos testes:** depois de cada análise, peça *"adicione essa linha no resultados_testes.csv"* para manter a planilha de acompanhamento sempre atualizada.

## ⚠️ Quando preferir o script (`analyze.py`) em vez do prompt

| Cenário | Recomendado |
|---|---|
| Decisão de alto risco / orçamento grande | `analyze.py` (cálculo exato, reprodutível) |
| Exploração rápida, perguntas de follow-up, "e se..." | Prompt Mestre |
| Volume alto de testes (rodar em lote) | `analyze.py` |
| Pessoa não-técnica do time quer rodar sozinha | Prompt Mestre (sem precisar instalar Python) |
| Precisão estatística é crítica (p-value exato) | `analyze.py` (usa scipy de verdade, IA pode estimar errado) |
