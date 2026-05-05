import pandas as pd
from supabase import create_client, Client
import numpy as np
from dotenv import load_dotenv
import os

load_dotenv()

# Configuração do Supabase
URL = os.getenv('SUPABASE_URL')
KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(URL, KEY)

# Extração dos dados
def extracao(nome_tabela):
    response = supabase.table(nome_tabela).select('*').execute()
    data = response.data
    df = pd.DataFrame(data)
    return df


# Salvar os dados em um arquivo CSV
dfreceitas = extracao('receitas')
dfcartao = extracao('cartao_credito')
dffixas = extracao('despesas_fixas')

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
