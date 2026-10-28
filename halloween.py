import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Halloween Colégio GDV", page_icon="🎃", layout="wide")

st.title("🎃 Halloween Colégio GDV")
st.subheader("Formulário de Votação do Concurso")

# Ligação ao Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# URL da sua planilha do Google Sheets
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1RGh0FRMgZGJTE-aXWGfHqYsdl0mzxZ5Qr-uXgKtcmmY/edit?gid=0#gid=0"

def carregar_dados():
    try:
        return conn.read(spreadsheet=URL_PLANILHA, ttl="0s")
    except Exception:
        return pd.DataFrame(columns=[
            "Jurado", "Série/Ano", "Aluno", 
            "Criatividade", "Execução", "Performance", "Adequação ao Tema", 
            "Nota Final"
        ])

df_votos = carregar_dados()

turmas = [
    "5º Ano", "6º Ano", "7º Ano", "8º Ano", "9º Ano",
    "1ª Série EM", "2ª Série EM", "3ª Série EM"
]

col_form, col_placar = st.columns([1, 1])

with col_form:
    st.subheader("📝 Avaliação do Jurado")
    
    with st.form("form_votacao", clear_on_submit=True):
        jurado = st.text_input("Nome do Jurado")
        serie = st.selectbox("Selecione a Série/Ano", options=turmas)
        aluno = st.text_input("Nome do Aluno")
        
        st.markdown("---")
        st.markdown("**Notas por Categoria (Cada uma vale de 0.0 a 2.5):**")
        
        cria = st.number_input("1. Criatividade", min_value=0.0, max_value=2.5, step=0.1, format="%.1f")
        exec = st.number_input("2. Execução", min_value=0.0, max_value=2.5, step=0.1, format="%.1f")
        perf = st.number_input("3. Performance", min_value=0.0, max_value=2.5, step=0.1, format="%.1f")
        adeq = st.number_input("4. Adequação ao Tema", min_value=0.0, max_value=2.5, step=0.1, format="%.1f")
        
        nota_final = cria + exec + perf + adeq
        st.markdown(f"### **Nota Total: :green[{nota_final:.1f} / 10.0]**")
        
        enviado = st.form_submit_button("💾 Enviar Voto")
        
        if enviado:
            if not jurado.strip() or not aluno.strip():
                st.error("Por favor, preencha o nome do jurado e do aluno!")
            else:
                novo_voto = pd.DataFrame([{
                    "Jurado": jurado,
                    "Série/Ano": serie,
                    "Aluno": aluno,
                    "Criatividade": cria,
                    "Execução": exec,
                    "Performance": perf,
                    "Adequação ao Tema": adeq,
                    "Nota Final": nota_final
                }])
                
                df_atualizado = pd.concat([df_votos, novo_voto], ignore_index=True)
                conn.update(spreadsheet=URL_PLANILHA, data=df_atualizado)
                
                st.success(f"Voto gravado para **{aluno}** ({serie}) com total de **{nota_final:.1f}** pontos!")
                st.rerun()

with col_placar:
    st.subheader("📊 Resultados Registrados")
    
    if not df_votos.empty:
        serie_filtro = st.selectbox("Filtrar Placar por Série", options=["Todas"] + turmas)
        
        if serie_filtro != "Todas":
            df_exibicao = df_votos[df_votos["Série/Ano"] == serie_filtro]
        else:
            df_exibicao = df_votos
            
        st.write("**Ranking por Média Geral:**")
        df_exibicao["Nota Final"] = pd.to_numeric(df_exibicao["Nota Final"], errors="coerce")
        ranking = df_exibicao.groupby(["Série/Ano", "Aluno"])["Nota Final"].mean().reset_index()
        ranking = ranking.sort_values(by="Nota Final", ascending=False)
        st.dataframe(ranking, use_container_width=True)
        
        with st.expander("Ver todos os lançamentos detalhados"):
            st.dataframe(df_exibicao, use_container_width=True)
    else:
        st.info("Nenhum voto registrado ainda na planilha.")
