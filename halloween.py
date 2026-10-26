import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Halloween Colégio GDV", page_icon="🎃", layout="wide")

# Título principal
st.title("🎃 Halloween Colégio GDV")
st.subheader("Formulário de Votação do Concurso")

ARQUIVO_DADOS = "votos_halloween.csv"

# Inicializa o CSV se não existir
if not os.path.exists(ARQUIVO_DADOS):
    df_inicial = pd.DataFrame(columns=[
        "Jurado", "Série/Ano", "Aluno", 
        "Criatividade", "Execução", "Performance", "Adequação ao Tema", 
        "Nota Final"
    ])
    df_inicial.to_csv(ARQUIVO_DADOS, index=False)

# Lista de Turmas (5º Ano à 3ª Série)
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
        
        # 4 notas limitadas de 0.0 a 2.5
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
                
                novo_voto.to_csv(ARQUIVO_DADOS, mode='a', header=False, index=False)
                st.success(f"Voto gravado para **{aluno}** ({serie}) com total de **{nota_final:.1f}** pontos!")

with col_placar:
    st.subheader("📊 Resultados Registrados")
    
    if os.path.exists(ARQUIVO_DADOS):
        df = pd.read_csv(ARQUIVO_DADOS)
        
        if not df.empty:
            # Filtro por série para o placar
            serie_filtro = st.selectbox("Filtrar Placar por Série", options=["Todas"] + turmas)
            
            if serie_filtro != "Todas":
                df_exibicao = df[df["Série/Ano"] == serie_filtro]
            else:
                df_exibicao = df
                
            st.write("**Ranking por Média Geral:**")
            ranking = df_exibicao.groupby(["Série/Ano", "Aluno"])["Nota Final"].mean().reset_index()
            ranking = ranking.sort_values(by="Nota Final", ascending=False)
            st.dataframe(ranking, use_container_width=True)
            
            with st.expander("Ver todos os lançamentos detalhados"):
                st.dataframe(df_exibicao, use_container_width=True)
        else:
            st.info("Nenhum voto registrado ainda.")
