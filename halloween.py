import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Configuração da página
st.set_page_config(page_title="Halloween Colégio GDV", page_icon="🎃", layout="wide")

st.title("🎃 Halloween Colégio GDV")
st.subheader("Formulário de Votação do Concurso")

# URL da planilha do Google Sheets
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1RGh0FRMgZGJTE-aXWGfHqYsdl0mzxZ5Qr-uXgKtcmmY/edit?gid=0#gid=0"

# Inicialização da conexão com o Google Sheets através da Service Account
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        # Lê os dados da planilha usando a URL explicitada
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
lista_jurados = ["Beatriz", "Caio", "Sting", "Outro..."]

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
        exec = st.number_input("2. Execução", min_value=0.0, max_value=2.5
