import streamlit as st
import pandas as pd
from supabase import create_client, Client  # Biblioteca para conectar ao Supabase
import plotly.express as px # Biblioteca para gráficos profissionais
from extracao import df, supabase


st.set_page_config(page_title="Portal de Planejamento", layout="wide")


# --- MENU LATERAL (A nossa Navegação) ---
st.sidebar.title("📌 Navegação")
pagina = st.sidebar.selectbox("Selecione a página:", ["📊 Dashboard Financeiro", "📥 Realizar Lançamento"])
mes_selecionado = st.sidebar.slider('Selecione o Mês', min_value=1, max_value=12)
ano_selecionado = st.sidebar.slider('Selecione o Mês', min_value=2024, max_value=2027)

# --- PÁGINA 1: DASHBOARD ---
if pagina == "📊 Dashboard Financeiro":
    st.title("📊 Dashboard de Controle Financeiro")

    df_filtrado = df[(df['mes_vencimento'] == mes_selecionado) & (df['ano_vencimento'] == ano_selecionado)]


    if not df.empty:
        # Tratamento de dados rápido (Data Engineering)
        df_filtrado['valor'] = pd.to_numeric(df_filtrado['valor'])
        
        # KPIs - Os indicadores que o seu gestor quer ver
        total_gasto = df_filtrado[df_filtrado['tipo'] == 'Despesas']['valor'].sum()
        qtd_lancamentos = len(df_filtrado[df_filtrado['tipo'] == 'Despesas'])
        total_receitas = df_filtrado[df_filtrado['tipo'] == 'Receitas']['valor'].sum()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Gasto Total", f"R$ {total_gasto:,.2f}")
        col2.metric("Nº de Lançamentos (Despesas)", qtd_lancamentos)
        col3.metric("Receitas Totais", f"R$ {(total_receitas):,.2f}")
        col4.metric("Lucro", f"R$ {(total_receitas - (total_gasto *-1)):,.2f}")
        
        st.divider()
        
        # Gráficos com Plotly (Visualização de dados avançada)
        c1, c2 = st.columns(2)
        
        with c1:
            st.write("### Gastos por Categoria")
            df_cat = df_filtrado[df_filtrado['tipo'] == 'Despesas'].groupby('categoria')['valor'].sum().reset_index()
            df_cat['valor'] = df_cat['valor'] *-1
            fig = px.bar(df_cat, x='categoria', y='valor', color='categoria', template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            st.write("### Evolução dos Lançamentos")
            st.dataframe(df_filtrado.sort_values('id', ascending=False), hide_index=True)

    else:
        st.warning("O banco de dados está vazio. Vá para a página de lançamentos!")

# --- PÁGINA 2: LANÇAMENTOS ---
elif pagina == "📥 Realizar Lançamento":
    st.title("📥 Novo Lançamento")
    
    # Colocando a senha que criamos no desafio anterior
    senha = st.sidebar.text_input("Senha de Acesso", type="password")
    
    if senha == "analista2026":
        with st.form("form_registro", clear_on_submit=True):
            data = st.date_input("Data")
            cat = st.text_input("Categoria", type="text")
            val = st.number_input("Valor do Gasto", min_value=0.0)
            desc = st.text_input("Descrição", type="text")
            nome = st.text_input("Nome do Titular", type="text")
            dia_vencimento = st.date_input("Dia de Vencimento")
            banco_cartao = st.text_input("Banco/Cartão", type="text")

            
            sub = st.form_submit_button("Registrar no Banco")
            
            if sub:
                if val > 0:
                    try:
                        novo_item = {'data': data, 'valor' : val, 'descricao': desc, 'categoria': cat, 'nome_titular': nome, 'dia_vencimento': dia_vencimento, 'banco_cartao': banco_cartao}
                        supabase.table("cartao_credito").insert(novo_item).execute()
                        st.success("Lançamento realizado! Verifique o Dashboard.")
                    except Exception as e:
                        st.error(f"Erro: {e}")
                else:
                    st.error("Verifique se o campo 'Valor do Gasto' o valor é maior que 0.")
    else:
        st.error("Por favor, insira a senha correta na barra lateral para liberar o formulário.")