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
        
        # Identifica dinamicamente os grupos para testar (ex: pega o grupo de maior lucro vs maior volume)
        # Para simplificar na execução direta, vamos pegar o primeiro e o último grupo da lista
        grupos_unicos = sorted(df_limpo['Grupos de usuários'].unique())
        if len(grupos_unicos) >= 2:
            validar_teste_estatistico(df_limpo, grupo_controle=grupos_unicos[0], grupo_teste=grupos_unicos[-1])
        
    except FileNotFoundError:
        print(f"Erro: Arquivo '{caminho}' não encontrado.")
