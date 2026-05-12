
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
pagina = st.sidebar.selectbox("Selecione a página:", ["📊 Dashboard Financeiro", "📥 Realizar Lançamento (Cartão Crédito)", 'Lançamento Receita'])
mes_atual = datetime.now().month
ano_atual = datetime.now().year

mes_selecionado = st.sidebar.slider('Mês', 1, 12, mes_atual)
ano_selecionado = st.sidebar.slider('Ano', 2025, 2030, ano_atual)

with st.sidebar.expander("Filtros Avançados", expanded=False):
    
    tipo_selecionado = st.multiselect('Tipo', df['tipo'].unique(), placeholder="Todos")
    categoria_selecionada = st.multiselect('Categoria', df['categoria'].unique(), placeholder="Todas")
    origem_selecionada = st.multiselect('origem', df['origem'].unique(), placeholder="Todas")
    valor_selecionado = st.slider('Valor', -6000, 10000, (-6000, 10000))


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
            st.caption(f"{progresso_receitas*100:.0f}% preenchido")
        
        with col_desp_m:
            st.metric("💸 Despesas", f"R$ {abs(total_despesas_pagas):,.2f}", f"de R$ {abs(total_despesas_previstas):,.2f}")
            if abs(total_despesas_previstas) > 0:
                progresso_despesas = abs(total_despesas_pagas) / abs(total_despesas_previstas)
            else:
                progresso_despesas = 0
            st.progress(progresso_despesas)
            st.caption(f"{progresso_despesas*100:.0f}% preenchido")
        
        with col_lucro:
            lucro_realizado = total_receitas_recebidas + total_despesas_pagas
            lucro_previsto = total_receitas_previstas + total_despesas_previstas
            st.metric("📈 Lucro", f"R$ {lucro_realizado:,.2f}", f"de R$ {lucro_previsto:,.2f}")
            # calcular progresso do lucro apenas quando o lucro previsto for positivo
            if lucro_previsto and lucro_previsto != 0:
                if lucro_previsto > 0:
                    progresso_lucro = lucro_realizado / lucro_previsto
                    progresso_lucro = max(0, min(1, progresso_lucro))
                else:
                    progresso_lucro = 0
            else:
                progresso_lucro = 0
            st.progress(progresso_lucro)
            st.caption(f"{progresso_lucro*100:.0f}% preenchido")
        
        st.divider()

        # --- Métricas de Despesas por Origem ---
        st.subheader("Despesas por Origem")

        despesas_cartao = despesas[despesas['origem'] == 'Cartão de Crédito']
        despesas_fixas = despesas[despesas['origem'] == 'Conta Corrente/PIX']
        col_cartao, col_fixas = st.columns(2)

        with col_cartao:
            st.write("**💳 Cartão de Crédito**")
            total_cartao_previsto = despesas_cartao['valor'].sum()
            total_cartao_pago = despesas_cartao[despesas_cartao['confirmado'] == True]['valor'].sum()
            st.metric("Total Cartão", f"R$ {abs(total_cartao_pago):,.2f}", f"de R$ {abs(total_cartao_previsto):,.2f}")
            if abs(total_cartao_previsto) > 0:
                progresso_cartao = abs(total_cartao_pago) / abs(total_cartao_previsto)
            else:
                progresso_cartao = 0
            st.progress(progresso_cartao)
            st.caption(f"{progresso_cartao*100:.0f}% preenchido")

        with col_fixas:
            st.write("**🏠 Despesas Fixas**")
            total_fixas_previsto = despesas_fixas['valor'].sum()
            total_fixas_pago = despesas_fixas[despesas_fixas['confirmado'] == True]['valor'].sum()
            st.metric("Total Fixas", f"R$ {abs(total_fixas_pago):,.2f}", f"de R$ {abs(total_fixas_previsto):,.2f}")
            if abs(total_fixas_previsto) > 0:
                progresso_fixas = abs(total_fixas_pago) / abs(total_fixas_previsto)
            else:
                progresso_fixas = 0
            st.progress(progresso_fixas)
            st.caption(f"{progresso_fixas*100:.0f}% preenchido")

        # --- Depesas por Cartões ---
        st.subheader("💳 Despesas por Cartão"
        )
        despesas_cartao = despesas[despesas['origem'] == 'Cartão de Crédito']
        if not despesas_cartao.empty:
            bancos = ['Nubank', 'Itaú', 'Mercado Pago']
            for banco in bancos:
                df_banco = despesas_cartao[despesas_cartao['banco_do_cartao'].str.contains(banco, case=False, na=False)]
                if not df_banco.empty:
                    total_banco_previsto = df_banco['valor'].sum()
                    total_banco_pago = df_banco[df_banco['confirmado'] == True]['valor'].sum()
                    st.metric(f"🏢 {banco}", f"R$ {abs(total_banco_pago):,.2f}", f"de R$ {abs(total_banco_previsto):,.2f}")
                    if abs(total_banco_previsto) > 0:
                        progresso_banco = abs(total_banco_pago) / abs(total_banco_previsto)
                    else:
                        progresso_banco = 0
                    st.progress(progresso_banco)
                    st.caption(f"{progresso_banco*100:.0f}% preenchido")


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
                with st.expander('Depesas de moradia, assinaturas, contas mensais, etc.', expanded=False):
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
                        st.caption(f"🏢 {banco}  | R$ {df_banco['valor'].sum():,.2f}")
                        with st.expander(f"Despesas do {banco}", expanded=False):
                            col_b1, col_b2 = st.columns(2)
                            
                            df_pend = df_banco[df_banco['confirmado'] == False]
                            df_conf = df_banco[df_banco['confirmado'] == True]
                            
                            with col_b1:
                                st.caption("Não Pago")
                                if st.button("Pagar Tudo", key=f"pagar_tudo_{banco}", help="Confirmar pagamento de todas as despesas deste cartão"):
                                    for idx, row in df_pend.iterrows():
                                        atualizar_confirmacao('cartao_credito', row['data'], row['descricao'], row['valor'], True)
                                    st.cache_data.clear()
                                    time.sleep(1)
                                    st.rerun()
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
        st.subheader("📊 Gastos por Categoria"
                     )
        df_despesas_categoria = despesas.groupby('categoria')['valor'].sum().reset_index()
        st.dataframe(df_despesas_categoria.style.format({"valor": "R$ {0:,.2f}"}), hide_index=True)

# --- PÁGINA 2: LANÇAMENTOS ---
elif pagina == "📥 Realizar Lançamento (Cartão Crédito)":
    st.title("📥 Realizar Lançamento (Cartão Crédito)")
    
    with st.form("form_registro", clear_on_submit=True):
        data = st.date_input("Data", value=datetime.now().date())
        cat = st.text_input("Categoria")
        val = st.number_input("Valor do Gasto", min_value=0.0)
        desc = st.text_input("Descrição")
        nome = st.selectbox("Nome do Titular da Compra", ['Paulo', 'Mariana', 'Dividido'])
        dia_vencimento = st.date_input("Dia de Vencimento", value=datetime(datetime.now().year, (datetime.now().month % 12) + 1, 9).date())
        banco_cartao = st.selectbox("Banco/Cartão", ['Nubank', 'Itaú', 'Mercado Pago'])
        titular_cartao = st.selectbox("Titular do Cartão", ['Paulo', 'Mariana'])
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
                    'confirmado': False,
                    'titular_cartao': titular_cartao
                    }
                    supabase.table("cartao_credito").insert(novo_item).execute()
                    st.success("Lançamento realizado! Verifique o Dashboard.")
                except Exception as e:
                    st.error(f"Erro: {e}")
            else:
                st.error("Verifique se o campo 'Valor do Gasto' o valor é maior que 0.")
        else:
            st.error("Por favor, insira a senha correta na barra lateral para liberar o formulário.")


# --- PÁGINA 3: LANÇAMENTOS RECEITAS---
elif pagina == "Lançamento Receita":
    st.title("Lançamento Receita")
    
    with st.form("form_registro", clear_on_submit=True):
        data = st.date_input("Data", value=datetime.now().date())
        desc = st.text_input("Descrição")
        val = st.number_input("Valor Recebido", min_value=0.0)
        nome = st.text_input("Nome")
        confirmado = st.selectbox("Recebido", [True, False])
        sub = st.form_submit_button("Registrar no Banco")
            
        if sub:
            if val > 0:
                try:
                    novo_item ={
                    'data': str(data), 
                    'descricao': desc, 
                    'valor': val, 
                    'nome': nome,
                    'confirmado': confirmado
                    }
                    supabase.table("receitas").insert(novo_item).execute()
                    st.success("Lançamento de Receita realizado! Verifique o Dashboard.")
                except Exception as e:
                    st.error(f"Erro: {e}")
            else:
                st.error("Verifique se o campo 'Valor Recebido' o valor é maior que 0.")