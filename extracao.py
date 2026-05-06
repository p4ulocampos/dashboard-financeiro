import pandas as pd
from supabase import create_client
import streamlit as st
import numpy as np

# Inicialize o cliente aqui
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

@st.cache_data(ttl=60)
# Crie uma função para buscar os dados
def buscar_dados():
    
    dfreceitas = supabase.table('receitas').select("*").execute()
    dfcartao = supabase.table('cartao_credito').select("*").execute()
    dffixas = supabase.table('despesas_fixas').select("*").execute()

    dffixas['categoria'] = 'Despesa Fixa'

    # excluindo pagamentos do cartao
    dfcartao = dfcartao[dfcartao['categoria'] != 'Pagamento']
    dfcartao = dfcartao.rename(columns={'nome_titular': 'nome'})

    dfs = [dfcartao, dffixas]

    for df in dfs:
        df['tipo'] = 'Despesas'
        df['valor'] = df['valor'] * -1

    dfreceitas['tipo'] = 'Receitas'

    colunas = ['data', 'descricao', 'categoria', 'valor', 'tipo', 'nome', 'dia_vencimento']

    df = pd.concat([dfreceitas, dfcartao, dffixas], ignore_index=True)
    df = df[colunas]

    df['categoria'] = np.where(df['descricao'].str.startswith('Salário'), 'Salário', df['categoria'])
    df['categoria'] = np.where(df['descricao'].str.startswith('Pensão'), 'Pensão', df['categoria'])
    df['categoria'] = np.where(df['descricao'].str.startswith('Férias'), 'Férias', df['categoria'])
    df['categoria'] = df['categoria'].fillna('Outros')

    df['data'] = pd.to_datetime(df['data'])
    df['dia_vencimento'] = pd.to_datetime(df['dia_vencimento'])

    df['dia_vencimento'] = df['dia_vencimento'].fillna(df['data'])

    df['mes'] = df['data'].dt.month
    df['ano'] = df['data'].dt.year

    df['mes_vencimento'] = df['dia_vencimento'].dt.month
    df['ano_vencimento'] = df['dia_vencimento'].dt.year

    df['id'] = df.index
    return df
