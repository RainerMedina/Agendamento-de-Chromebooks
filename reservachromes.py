import streamlit as st
from datetime import datetime, date, time
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
import os

# =========================================================
# 1. CONFIGURACAO DA PAGINA E IMAGEM DE FUNDO
# =========================================================
st.set_page_config(page_title="Portal de Reservas - GDV", page_icon="🏫", layout="wide")

def aplicar_imagem_fundo(caminho_imagem):
    bg_css = ""
    if os.path.exists(caminho_imagem):
        with open(caminho_imagem, "rb") as img_file:
            b64 = base64.b64encode(img_file.read()).decode()
        bg_css = f"""
        .stApp {{
            background-image: url("data:image/jpeg;base64,{b64}");
            background-size: cover;
            background-position: center top;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        .block-container {{
            background-color: rgba(255, 255, 255, 0.45);
            backdrop-filter: blur(4px);
            border-radius: 16px;
            padding: 2rem 2.5rem;
            margin-top: 1.5rem;
            margin-bottom: 1.5rem;
        }}
        [data-testid="stForm"], [data-testid="stDataFrame"] {{
            background-color: rgba(255, 255, 255, 0.92);
            border-radius: 12px;
            padding: 1.5rem;
        }}
        """
    st.markdown(f"""
    <style>
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    {bg_css}
    </style>
    """, unsafe_allow_html=True)

aplicar_imagem_fundo("fundo_pag.jpeg")

if "msg_sucesso" in st.session_state:
    st.success(st.session_state["msg_sucesso"], icon="✅")
    st.toast(st.session_state["msg_sucesso"], icon="✅")
    del st.session_state["msg_sucesso"]

# =========================================================
# 2. CONEXAO DIRETA COM GOOGLE SHEETS
# =========================================================
@st.cache_resource
def conectar_gsheets():
    try:
        creds_dict = st.secrets["connections"]["gsheets"]
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        url = creds_dict.get("spreadsheet", "")
        return client.open_by_url(url).sheet1 if url else client.openall()[0].sheet1
    except Exception as e:
        st.
