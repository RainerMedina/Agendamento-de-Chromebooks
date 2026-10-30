import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Halloween Colégio GDV", page_icon="🎃", layout="wide")

st.title("🎃 Halloween Colégio GDV")
st.subheader("Formulário de Votação do Concurso")

# Conexão com o Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# URL da planilha do Google Sheets
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1RGh0FRMgZGJTE-aXWGfHqYsdl0mzxZ5Qr-uXgKtcmmY/edit?gid=0#gid=0"

def carregar_dados():
    try:
        df = conn.read(spreadsheet=URL_PLANILHA, ttl="0s")
        return df.dropna(how="all")
    except Exception:
        return pd.DataFrame(columns=[
            "Jurado", "Série/Ano", "Aluno", 
            "Criatividade", "Execução", "Performance", "Adequação ao Tema", 
            "Nota Final"
        ])

df_votos = carregar_dados()

# Turmas ativas do Ensino Médio
turmas = [
    "1ª Série EM", "2ª Série EM", "3ª Série EM"
]

# Lista pré-definida de Jurados
lista_jurados = ["Beatriz", "Portugal", "Rafaela", "Outro..."]

col_form, col_placar = st.columns([1, 1])

with col_form:
    st.subheader("📝 Avaliação do Jurado")
    
    with st.form("form_votacao", clear_on_submit=True):
        jurado_selecionado = st.selectbox("Selecione o Jurado", options=lista_jurados)
        
        if jurado_selecionado == "Outro...":
            jurado_nome = st.text_input("Digite o Nome do Jurado")
        else:
            jurado_nome = jurado_selecionado
            
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
            if not jurado_nome.strip() or not aluno.strip():
                st.error("Por favor, selecione/preencha o jurado e o nome do aluno!")
            else:
                novo_voto = pd.DataFrame([{
                    "Jurado": jurado_nome.strip(),
                    "Série/Ano": serie,
                    "Aluno": aluno.strip(),
                    "Criatividade": cria,
                    "Execução": exec,
                    "Performance": perf,
                    "Adequação ao Tema": adeq,
                    "Nota Final": nota_final
                }])
                
                # Re-lê os dados em tempo real antes de gravar para garantir que nenhum voto seja sobrescrito
                dados_mais_recentes = carregar_dados()
                df_atualizado = pd.concat([dados_mais_recentes, novo_voto], ignore_index=True)
                
                conn.update(spreadsheet=URL_PLANILHA, data=df_atualizado)
                
                st.success(f"Voto gravado para **{aluno}** ({serie}) com total de **{nota_final:.1f}** pontos!")
                st.rerun()

with col_placar:
    st.subheader("📊 Resultados Registrados")
    
    if not df_votos.empty:
        serie_filtro = st.selectbox("Filtrar Placar por Série", options=["Todas"] + turmas)
        
        if serie_filtro != "Todas":
            df_exibicao = df_votos[df_votos["Série/Ano"] == serie_filtro].copy()
        else:
            df_exibicao = df_votos[df_votos["Série/Ano"].isin(turmas)].copy()
            
        st.write("**Ranking por Média Geral:**")
        
        # Converte colunas numéricas
        df_exibicao["Nota Final"] = pd.to_numeric(df_exibicao["Nota Final"], errors="coerce")
        df_exibicao["Criatividade"] = pd.to_numeric(df_exibicao["Criatividade"], errors="coerce")
        
        # Agrupa calculando a Média Final, Qtd de Votos e Média de Criatividade
        ranking = df_exibicao.groupby(["Série/Ano", "Aluno"]).agg(
            Media_Final=("Nota Final", "mean"),
            Qtd_Votos=("Nota Final", "count"),
            Media_Criatividade=("Criatividade", "mean")
        ).reset_index()
        
        # Ordena: 1º Média Final, 2º Qtd Votos, 3º Criatividade (Desempate)
        ranking = ranking.sort_values(
            by=["Media_Final", "Qtd_Votos", "Media_Criatividade"], 
            ascending=[False, False, False]
        ).reset_index(drop=True)
        
        # Formata e exibe
        ranking_exibicao = pd.DataFrame({
            "Série/Ano": ranking["Série/Ano"],
            "Aluno": ranking["Aluno"],
            "Média Final": ranking["Media_Final"].round(2),
            "Nº Avaliações": ranking["Qtd_Votos"],
            "Média Criatividade (Desempate)": ranking["Media_Criatividade"].round(2)
        })
        
        ranking_exibicao.index = ranking_exibicao.index + 1
        st.dataframe(ranking_exibicao, use_container_width=True)
        
        with st.expander("Ver todos os lançamentos detalhados"):
            st.dataframe(df_exibicao, use_container_width=True)
    else:
        st.info("Nenhum voto registrado ainda na planilha.")
