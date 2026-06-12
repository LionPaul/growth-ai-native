import pandas as pd
import scipy.stats as stats
import sys
import os
def carregar_e_limpar_dados(caminho_arquivo):
    """
    Carrega o dataset de testes A/B e limpa as colunas financeiras.
    """
    # Carrega o CSV
    df = pd.read_csv(caminho_arquivo)
    
    # Lista das colunas que contêm valores em Reais (R$)
    colunas_financeiras = ['comissão', 'cashback', 'vendas totais']
    
    for col in colunas_financeiras:
        if col in df.columns:
            # Remove o 'R$ ', os pontos de milhar e substitui vírgula por ponto (caso exista)
            # Ex: 'R$ 10.273' -> '10273.0'
            df[col] = (df[col]
                       .astype(str)
                       .str.replace('R\$', '', regex=True)
                       .str.replace('.', '', regex=False) # Remove ponto de milhar
                       .str.replace(',', '.', regex=False) # Ajusta decimal se houver
                       .str.strip()
                       .astype(float))
            
    # Converte a coluna de Data para datetime
    df['Data'] = pd.to_datetime(df['Data'])
    
    return df
def calcular_metricas_ab(df):
    """
    Agrupa os dados por variante e calcula as principais métricas de negócio.
    """
    # Agrupar por grupo de usuário e somar os valores absolutos
    df_agrupado = df.groupby('Grupos de usuários').agg({
        'compradores': 'sum',
        'comissão': 'sum',
        'cashback': 'sum',
        'vendas totais': 'sum'
    }).reset_index()
    # Calcular métricas derivadas
    # 1. Ticket Médio = Vendas Totais / Compradores
    df_agrupado['ticket_medio'] = df_agrupado['vendas totais'] / df_agrupado['compradores']
    
    # 2. Lucro da Méliuz = Comissão recebida - Cashback pago
    df_agrupado['lucro_meliuz'] = df_agrupado['comissão'] - df_agrupado['cashback']
    
    # 3. ROI do Cashback (%) = (Lucro / Cashback investido) * 100
    df_agrupado['roi_cashback_perc'] = (df_agrupado['lucro_meliuz'] / df_agrupado['cashback']) * 100
    
    # Formatação (opcional, para ficar bonito igual a print deles)
    # Arredondando para 2 casas decimais
    colunas_arredondar = ['ticket_medio', 'lucro_meliuz', 'roi_cashback_perc', 'comissão', 'cashback', 'vendas totais']
    for col in colunas_arredondar:
        df_agrupado[col] = df_agrupado[col].round(2)
        
    return df_agrupado
def validar_teste_estatistico(df, grupo_controle, grupo_teste):
    """
    Realiza um Teste T independente comparando dois grupos parametrizados.
    """
    df['lucro_diario'] = df['comissão'] - df['cashback']
    
    lucro_g1 = df[df['Grupos de usuários'] == grupo_controle]['lucro_diario'].dropna()
    lucro_g2 = df[df['Grupos de usuários'] == grupo_teste]['lucro_diario'].dropna()
    
    if lucro_g1.empty or lucro_g2.empty:
        print(f"Erro: Os grupos '{grupo_controle}' ou '{grupo_teste}' não foram encontrados no dataset.")
        return
    t_stat, p_valor = stats.ttest_ind(lucro_g1, lucro_g2, equal_var=False)
    
    print(f"--- RESULTADO DO TESTE ESTATÍSTICO ({grupo_controle} vs {grupo_teste}) ---")
    print(f"Média diária de lucro - {grupo_controle}: R$ {lucro_g1.mean():.2f}")
    print(f"Média diária de lucro - {grupo_teste}: R$ {lucro_g2.mean():.2f}")
    print(f"P-Valor (Probabilidade de ser acaso): {p_valor:.6f}\n")
    
    if p_valor < 0.05:
        print("💡 CONCLUSÃO ESTRATÉGICA: A diferença de lucro é ESTATISTICAMENTE SIGNIFICATIVA.")
    else:
        print("⚠️ CONCLUSÃO ESTRATÉGICA: A diferença NÃO é estatisticamente significativa.")
def registrar_historico(nome_parceiro, grupo_controle, grupo_teste, df_resultados, p_valor):
    """
    Registra o resultado do teste no arquivo de tracker consolidado.
    """
    # Extrai o lucro de cada grupo para saber quem ganhou
    lucro_controle = df_resultados[df_resultados['Grupos de usuários'] == grupo_controle]['lucro_meliuz'].values[0]
    lucro_teste = df_resultados[df_resultados['Grupos de usuários'] == grupo_teste]['lucro_meliuz'].values[0]
    # Define o resultado e a decisão baseados na estatística
    if p_valor < 0.05:
        vencedor = grupo_controle if lucro_controle > lucro_teste else grupo_teste
        perdedor = grupo_teste if lucro_controle > lucro_teste else grupo_controle
        resultado = f"Significativo (p-valor: {p_valor:.4f}). {vencedor} gerou mais lucro."
        decisao = f"Manter {vencedor} e descontinuar {perdedor}."
    else:
        resultado = f"Inconclusivo (p-valor: {p_valor:.4f}). Sem diferença estatística."
        decisao = "Manter o teste rodando para coletar mais dados."
    # Cria a linha do registro
    novo_registro = pd.DataFrame([{
        'Data da Análise': pd.Timestamp.now().strftime('%Y-%m-%d'),
        'Nome do Teste': f"Teste de Growth - {nome_parceiro.capitalize()}",
        'Descrição': f"Análise de rentabilidade: {grupo_controle} vs {grupo_teste}",
        'Resultado': resultado,
        'Decisão Tomada': decisao
    }])
    arquivo_historico = 'historico_testes_ab.csv'
    
    # Se o arquivo já existe, anexa (append). Se não, cria um novo.
    if os.path.exists(arquivo_historico):
        novo_registro.to_csv(arquivo_historico, mode='a', header=False, index=False, sep=';')
    else:
        novo_registro.to_csv(arquivo_historico, mode='w', header=True, index=False, sep=';')
        
    print(f"✅ Resultado consolidado salvo com sucesso no tracker: '{arquivo_historico}'")
if __name__ == "__main__":
    # Permite passar o nome do arquivo direto no terminal: python script.py dataset_02_parceiroB.csv
    if len(sys.argv) > 1:
        caminho = sys.argv[1]
    else:
        caminho = 'dataset_01_parceiroA.csv' # Fallback para o Parceiro A se nada for passado
    
    try:
        df_limpo = carregar_e_limpar_dados(caminho)
        
        print("\n--- RESUMO DOS DADOS ---")
        df_resultados = calcular_metricas_ab(df_limpo)
        try:
            display(df_resultados)
        except NameError:
            print(df_resultados)
            
        # Gera o arquivo dinamicamente baseado no nome do arquivo de entrada
        nome_base = os.path.basename(caminho).replace('.csv', '')
        nome_arquivo_saida = f'resumo_{nome_base}.csv'
        df_resultados.to_csv(nome_arquivo_saida, index=False, sep=';')
        print(f"\nSucesso! O arquivo '{nome_arquivo_saida}' foi gerado e salvo.")
        
        # Identifica dinamicamente os grupos
        grupos_unicos = sorted(df_limpo['Grupos de usuários'].unique())
        if len(grupos_unicos) >= 2:
            grupo_controle = grupos_unicos[0]
            grupo_teste = grupos_unicos[-1]
            
            # Adiciona lucro_diario caso ainda não exista no df_limpo para extrair p_valor
            if 'lucro_diario' not in df_limpo.columns:
                df_limpo['lucro_diario'] = df_limpo['comissão'] - df_limpo['cashback']
            # Precisamos extrair o p_valor do teste para tomar a decisão
            lucro_g1 = df_limpo[df_limpo['Grupos de usuários'] == grupo_controle]['lucro_diario'].dropna()
            lucro_g2 = df_limpo[df_limpo['Grupos de usuários'] == grupo_teste]['lucro_diario'].dropna()
            t_stat, p_valor = stats.ttest_ind(lucro_g1, lucro_g2, equal_var=False)
            
            validar_teste_estatistico(df_limpo, grupo_controle, grupo_teste)
            
            # Aqui chamamos a nova função que cria a linha na planilha de tracker!
            registrar_historico(nome_base, grupo_controle, grupo_teste, df_resultados, p_valor)
        
    except FileNotFoundError:
        print(f"Erro: Arquivo '{caminho}' não encontrado.")
