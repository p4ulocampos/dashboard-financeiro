import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
import plotly.graph_objects as go
from extracao import buscar_dados, supabase, atualizar_confirmacao
from datetime import datetime
import time


st.set_page_config(page_title="Portal de Planejamento", layout="wide")

df = buscar_dados()

if st.button("🔄 Atualizar Dados"):
    st.cache_data.clear()
    st.rerun()

# --- MENU LATERAL ---
st.sidebar.title("📌 Navegação")
pagina = st.sidebar.selectbox("Selecione a página:", ["📊 Dashboard Financeiro", "📥 Realizar Lançamento"])
mes_atual = datetime.now().month
ano_atual = datetime.now().year

mes_selecionado = st.sidebar.slider('Mês', 1, 12, mes_atual)
ano_selecionado = st.sidebar.slider('Ano', 2025, 2030, ano_atual)

with st.sidebar.expander("🛠️ Filtros Avançados", expanded=False):
    tipo_selecionado = st.multiselect('Tipo', df['tipo'].unique(), placeholder="Todos")
    categoria_selecionada = st.multiselect('Categoria', df['categoria'].unique(), placeholder="Todas")
    origem_selecionada = st.multiselect('origem', df['origem'].unique(), placeholder="Todas")
    valor_selecionado = st.slider('Valor', -10000, 10000, (-10000, 10000))


# --- PÁGINA 1: DASHBOARD ---
if pagina == "📊 Dashboard Financeiro":
    st.title("📊 Dashboard de Controle Financeiro")

    df_filtrado = df.copy()

    # Aplica filtros de data e valor obrigatórios
    df_filtrado = df_filtrado[
        (df_filtrado['mes_vencimento'] == mes_selecionado) &
        (df_filtrado['ano_vencimento'] == ano_selecionado) &
        (df_filtrado['valor'].between(valor_selecionado[0], valor_selecionado[1]))
    ]
    
    # Aplica filtros de listas APENAS se o usuário selecionou algo
    if categoria_selecionada:
        df_filtrado = df_filtrado[df_filtrado['categoria'].isin(categoria_selecionada)]
    if origem_selecionada:
        df_filtrado = df_filtrado[df_filtrado['origem'].isin(origem_selecionada)]
    if tipo_selecionado:
        df_filtrado = df_filtrado[df_filtrado['tipo'].isin(tipo_selecionado)]


    if not df_filtrado.empty:
        df_filtrado['valor'] = pd.to_numeric(df_filtrado['valor'])
        
        # KPIs
        receitas = df_filtrado[df_filtrado['tipo'] == 'Receitas']
        despesas = df_filtrado[df_filtrado['tipo'] == 'Despesas']
        
        total_receitas_previstas = receitas['valor'].sum()
        total_receitas_recebidas = receitas[receitas['confirmado'] == True]['valor'].sum()
        
        total_despesas_previstas = despesas['valor'].sum()
        total_despesas_pagas = despesas[despesas['confirmado'] == True]['valor'].sum()
        
        # --- LAYOUT MINIMALISTA ---
        col_rec_m, col_desp_m, col_lucro = st.columns(3)
        
        with col_rec_m:
            st.metric("💰 Receitas", f"R$ {total_receitas_recebidas:,.2f}", f"de R$ {total_receitas_previstas:,.2f}")
            if total_receitas_previstas > 0:
                progresso_receitas = total_receitas_recebidas / total_receitas_previstas
            else:
                progresso_receitas = 0
            st.progress(progresso_receitas)
        
        with col_desp_m:
            st.metric("💸 Despesas", f"R$ {abs(total_despesas_pagas):,.2f}", f"de R$ {abs(total_despesas_previstas):,.2f}")
            if abs(total_despesas_previstas) > 0:
                progresso_despesas = abs(total_despesas_pagas) / abs(total_despesas_previstas)
            else:
                progresso_despesas = 0
            st.progress(progresso_despesas)
        
        with col_lucro:
            lucro = total_receitas_recebidas + total_despesas_pagas
            st.metric("📈 Lucro", f"R$ {lucro:,.2f}")
        
        st.divider()

        # --- RECEITAS EM EXPANDER ---
        with st.expander("📥 Receitas", expanded=False):
            receitas_previstas = receitas[receitas['confirmado'] == False].copy()
            receitas_recebidas = receitas[receitas['confirmado'] == True].copy()
            
            col_rec1, col_rec2 = st.columns(2)
            
            with col_rec1:
                st.write("**Não Recebidas**")
                if not receitas_previstas.empty:
                    for idx, row in receitas_previstas.iterrows():
                        col_item, col_btn = st.columns([4, 1])
                        with col_item:
                            st.text(f"{row['descricao']} - R$ {row['valor']:,.2f}")
                        with col_btn:
                            if st.button("✓", key=f"confirm_receita_{idx}", help="Confirmar"):
                                tipo_tabela = 'receitas'
                                if atualizar_confirmacao(tipo_tabela, row['data'], row['descricao'], row['valor'], True):
                                    st.cache_data.clear()
                                    time.sleep(1)
                                    st.rerun()
                else:
                    st.caption("Nenhuma pendente")
            
            with col_rec2:
                st.write("**Recebidas** ✓")
                if not receitas_recebidas.empty:
                    for idx, row in receitas_recebidas.iterrows():
                        col_item, col_btn = st.columns([4, 1])
                        with col_item:
                            st.text(f"{row['descricao']} - R$ {row['valor']:,.2f}")
                        with col_btn:
                            if st.button("✗", key=f"unconfirm_receita_{idx}", help="Desconfirmar"):
                                tipo_tabela = 'receitas'
                                if atualizar_confirmacao(tipo_tabela, row['data'], row['descricao'], row['valor'], False):
                                    st.cache_data.clear()
                                    time.sleep(1)
                                    st.rerun()
                else:
                    st.caption("Nenhuma confirmada")
        
        # --- DESPESAS EM EXPANDER (AGRUPADAS) ---
        with st.expander("📤 Despesas", expanded=False):
            
            
            # Despesas Fixas
            despesas_fixas = despesas[despesas['origem'] == 'Conta Corrente/PIX'].copy()
            despesas_fixas_pend = despesas_fixas[despesas_fixas['confirmado'] == False]
            despesas_fixas_conf = despesas_fixas[despesas_fixas['confirmado'] == True]
            
            if not despesas_fixas.empty:
                st.write("**🏦 Despesas Fixas**")
                col_fix1, col_fix2 = st.columns(2)
                
                with col_fix1:
                    st.caption("Não Pagas")
                    if not despesas_fixas_pend.empty:
                        for idx, row in despesas_fixas_pend.iterrows():
                            col_item, col_btn = st.columns([4, 1])
                            with col_item:
                                st.text(f"{row['descricao']} - R$ {abs(row['valor']):,.2f}")
                            with col_btn:
                                if st.button("✓", key=f"fix_confirm_{idx}", help="Confirmar"):
                                    if atualizar_confirmacao('despesas_fixas', row['data'], row['descricao'], row['valor'], True):
                                        st.cache_data.clear()
                                        time.sleep(1)
                                        st.rerun()
                    else:
                        st.caption("Todas pagas ✓")
                
                with col_fix2:
                    st.caption("Pagas ✓")
                    if not despesas_fixas_conf.empty:
                        for idx, row in despesas_fixas_conf.iterrows():
                            col_item, col_btn = st.columns([4, 1])
                            with col_item:
                                st.text(f"{row['descricao']} - R$ {abs(row['valor']):,.2f}")
                            with col_btn:
                                if st.button("✗", key=f"fix_unconfirm_{idx}", help="Desfazer"):
                                    if atualizar_confirmacao('despesas_fixas', row['data'], row['descricao'], row['valor'], False):
                                        st.cache_data.clear()
                                        time.sleep(1)
                                        st.rerun()
                    else:
                        st.caption("Nenhuma confirmada")
                
                st.divider()
            
            # Despesas de Cartão (por banco)
            despesas_cartao = despesas[despesas['origem'] == 'Cartão de Crédito'].copy()
            
            if not despesas_cartao.empty:
                st.write("**💳 Despesas de Cartão**")
                
                bancos = ['Nubank', 'Itaú', 'Mercado Pago']
                
                for banco in bancos:
                    df_banco = despesas_cartao[despesas_cartao['banco_do_cartao'].str.contains(banco, case=False, na=False)]
                    
                    if not df_banco.empty:
                        st.caption(f"🏢 {banco}")
                        col_b1, col_b2 = st.columns(2)
                        
                        df_pend = df_banco[df_banco['confirmado'] == False]
                        df_conf = df_banco[df_banco['confirmado'] == True]
                        
                        with col_b1:
                            st.caption("Não Pago")
                            if not df_pend.empty:
                                for idx, row in df_pend.iterrows():
                                    col_item, col_btn = st.columns([4, 1])
                                    with col_item:
                                        st.text(f"{row['descricao']} - R$ {abs(row['valor']):,.2f}")
                                    with col_btn:
                                        if st.button("✓", key=f"cartao_confirm_{idx}", help="Confirmar"):
                                            if atualizar_confirmacao('cartao_credito', row['data'], row['descricao'], row['valor'], True):
                                                st.cache_data.clear()
                                                time.sleep(1)
                                                st.rerun()
                            else:
                                st.caption("Tudo pago ✓")
                        
                        with col_b2:
                            st.caption("Pago ✓")
                            if not df_conf.empty:
                                for idx, row in df_conf.iterrows():
                                    col_item, col_btn = st.columns([4, 1])
                                    with col_item:
                                        st.text(f"{row['descricao']} - R$ {abs(row['valor']):,.2f}")
                                    with col_btn:
                                        if st.button("✗", key=f"cartao_unconfirm_{idx}", help="Desfazer"):
                                            if atualizar_confirmacao('cartao_credito', row['data'], row['descricao'], row['valor'], False):
                                                st.cache_data.clear()
                                                time.sleep(1)
                                                st.rerun()
                            else:
                                st.caption("Nenhuma confirmada")
                        
                        st.divider()
        
        # --- GRÁFICO DE GASTOS POR CATEGORIA ---
        st.divider()
        st.subheader("📊 Gastos por Categoria")
        
        df_gastos = df_filtrado[df_filtrado['tipo'] == 'Despesas'].copy()
        if not df_gastos.empty:
            df_cat = df_gastos.groupby('categoria')['valor'].sum().reset_index()
            df_cat['valor'] = df_cat['valor'].abs()
            df_cat = df_cat.sort_values('valor', ascending=True)
            
            fig = px.bar(
                df_cat, 
                y='categoria', 
                x='valor', 
                orientation='h',
                color='valor',
                color_continuous_scale='Reds',
                labels={'valor': 'Valor (R$)', 'categoria': 'Categoria'},
                template='plotly_white'
            )
            fig.update_layout(
                height=400,
                showlegend=False,
                yaxis={'categoryorder': 'total ascending'}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhuma despesa registrada para este período")

    else:
        st.warning("O banco de dados está vazio ou não há registros para este período!")

# --- PÁGINA 2: LANÇAMENTOS ---
elif pagina == "📥 Realizar Lançamento":
    st.title("📥 Novo Lançamento")
    
    senha = st.sidebar.text_input("Senha de Acesso", type="password")
    
    if senha == "financeiro2026":
        with st.form("form_registro", clear_on_submit=True):
            data = st.date_input("Data")
            cat = st.text_input("Categoria")
            val = st.number_input("Valor do Gasto", min_value=0.0)
            desc = st.text_input("Descrição")
            nome = st.text_input("Nome do Titular")
            dia_vencimento = st.date_input("Dia de Vencimento")
            banco_cartao = st.selectbox("Banco/Cartão", ['Nubank', 'Itaú', 'Mercado Pago'])
            sub = st.form_submit_button("Registrar no Banco")
            
            if sub:
                if val > 0:
                    try:
                        novo_item ={
                        'data': str(data), 
                        'valor': val, 
                        'descricao': desc,      
                        'categoria': cat, 
                        'nome_titular': nome, 
                        'dia_vencimento': str(dia_vencimento), 
                        'banco_do_cartao': banco_cartao,
                        'confirmado': False
                        }
                        supabase.table("cartao_credito").insert(novo_item).execute()
                        st.success("Lançamento realizado! Verifique o Dashboard.")
                    except Exception as e:
                        st.error(f"Erro: {e}")
                else:
                    st.error("Verifique se o campo 'Valor do Gasto' o valor é maior que 0.")
    else:
        st.error("Por favor, insira a senha correta na barra lateral para liberar o formulário.")