import pandas as pd
from supabase import create_client
import streamlit as st
import numpy as np
import ssl
import os

# Temporarily disable SSL verification when DISABLE_SSL_VERIFY is set
if os.environ.get("DISABLE_SSL_VERIFY", "0").lower() in ("1", "true", "yes"):
    ssl._create_default_https_context = ssl._create_unverified_context

#testando branch

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

    dfreceitas = pd.DataFrame(dfreceitas.data)
    dfcartao = pd.DataFrame(dfcartao.data)
    dffixas = pd.DataFrame(dffixas.data)

    # Garantir que coluna 'confirmado' existe (preenchida com False se não existir)
    for df in [dfreceitas, dfcartao, dffixas]:
        if 'confirmado' not in df.columns:
            df['confirmado'] = False
        else:
            df['confirmado'] = df['confirmado'].fillna(False)

    dffixas['categoria'] = 'Despesa Fixa'

    dfcartao['origem'] = 'Cartão de Crédito'
    dffixas['origem'] = 'Conta Corrente/PIX'
    dfreceitas['origem'] = 'Débito'

    # excluindo pagamentos do cartao
    dfcartao = dfcartao[dfcartao['categoria'] != 'Pagamento']
    dfcartao = dfcartao.rename(columns={'nome_titular': 'nome'})

    dfs = [dfcartao, dffixas]

    for df in dfs:
        df['tipo'] = 'Despesas'
        df['valor'] = df['valor'] * -1

    dfreceitas['tipo'] = 'Receitas'

    # Garantir que 'nome_do_banco' existe em todas as tabelas
    if 'banco_do_cartao' not in dfreceitas.columns:
        dfreceitas['banco_do_cartao'] = None
    if 'banco_do_cartao' not in dffixas.columns:
        dffixas['banco_do_cartao'] = None

    colunas = ['data', 'descricao', 'categoria', 'valor', 'tipo', 'nome', 'dia_vencimento', 'origem', 'confirmado', 'banco_do_cartao']

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

def atualizar_confirmacao(tipo_tabela, data, descricao, valor_original, confirmado):
    """Atualiza o status de confirmação usando data + descricao + valor como identificador"""
    try:
        # Para despesas, o valor foi multiplicado por -1, precisamos reverter para buscar o original
        valor_banco = abs(float(valor_original))
        
        response = supabase.table(tipo_tabela).update({'confirmado': confirmado}).eq('data', str(data)).eq('descricao', descricao).eq('valor', valor_banco).execute()
        
        if response.data:
            return True
        else:
            st.warning(f"Nenhum registro encontrado para atualizar")
            return False
    except Exception as e:
        st.error(f"Erro ao atualizar confirmação: {e}")
        return False