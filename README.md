# 🚀 Automação de Análise de Testes A/B - Growth

Este repositório contém a solução para o desafio técnico de Estágio em Growth AI-Native. O objetivo principal é automatizar e escalar a análise de testes A/B, reduzindo um gargalo de horas para poucos segundos, garantindo precisão estatística e foco no impacto real de negócio (Lucro vs. GMV).

## 🧠 A Arquitetura: Abordagem Híbrida (AI-Native)

Para garantir que a solução seja de fácil usabilidade para qualquer pessoa do time, mas sem abrir mão do rigor matemático, optei por uma **arquitetura híbrida**:

1. **O Cérebro (Linguagem Natural):** O arquivo `prompt_mestre.txt` atua como o orquestrador. Ele contém instruções sistêmicas claras para que IAs (como Claude, Cursor ou ChatGPT) entendam o papel de Analista de Growth e saibam exatamente o que fazer com os dados.
2. **O Motor (Código Determinístico):** O script `analise_teste_ab.py` executa o trabalho pesado de forma confiável. Como LLMs costumam falhar em cálculos complexos, o script garante o ETL seguro (limpando strings financeiras), a agregação das métricas e a aplicação do **Teste T de Welch** para validar a significância estatística dos resultados.

## 🛠️ Como Utilizar

Esta solução foi desenhada para ser agnóstica e rodar perfeitamente em ferramentas AI-Native.

**Opção 1: Via Cursor IDE / Claude Code (Recomendado)**
1. Abra a pasta deste projeto na sua ferramenta.
2. Abra o chat da IA e cole o conteúdo do `prompt_mestre.txt`.
3. Anexe o dataset desejado (ex: `@dataset_01_parceiroA.csv`).
4. A IA executará o script Python automaticamente de forma invisível e retornará o relatório gerencial em texto, além de gerar o CSV consolidado na pasta.

**Opção 2: Via Terminal (Execução Manual)**
Caso queira rodar a automação sem o intermédio de uma IA, basta executar:
\`\`\`bash
python analise_teste_ab.py <nome_do_arquivo.csv>
\`\`\`
O script irá processar os dados, cuspir a avaliação estatística no terminal e salvar o resumo em um novo arquivo CSV.

## 📊 Critérios de Decisão e Negócio

A análise não olha apenas para o aumento de vendas totais (GMV), pois grupos com taxas de cashback agressivas tendem a gerar volume, mas destruir a margem. 
O script foca em otimizar o **Lucro** (Comissão - Cashback) e aplica testes de significância estatística (P-Value < 0.05) para garantir que a variante vencedora não é fruto do acaso.

## 📈 Tracker de Histórico (Sheets / CSV)

Para garantir o acompanhamento gerencial e evitar a perda de histórico dos testes:
1. A cada execução, o script alimenta automaticamente o arquivo local `historico_testes_ab.csv` contendo o resumo consolidado, a conclusão estatística e a decisão recomendada. Esta abordagem evita problemas de autenticação e vazamento de chaves de API da Google Cloud.
