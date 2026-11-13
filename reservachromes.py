import streamlit as st
from datetime import datetime, date, time
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
import os

# =========================================================
# 1. CONFIGURAÇÃO DA PÁGINA E IMAGEM DE FUNDO
# =========================================================
st.set_page_config(
    page_title="Portal de Reservas - GDV",
    page_icon="🏫",
    layout="wide"
)

def aplicar_imagem_fundo(caminho_imagem):
    if os.path.exists(caminho_imagem):
        with open(caminho_imagem, "rb") as img_file:
            b64_string = base64.b64encode(img_file.read()).decode()
        
        st.markdown(f"""
        <style>
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}

        .stApp {{
            background-image: url("data:image/jpeg;base64,{b64_string}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}

        /* Camada branca translúcida no bloco principal para manter a leitura nítida */
        .block-container {{
            background-color: rgba(255, 255, 255, 0.92);
            border-radius: 14px;
            padding: 2rem 2.5rem;
            margin-top: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        }}
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
        """, unsafe_allow_html=True)

aplicar_imagem_fundo("fundo_pag.jpeg")

if "msg_sucesso" in st.session_state:
    st.success(st.session_state["msg_sucesso"], icon="✅")
    st.toast(st.session_state["msg_sucesso"], icon="✅")
    del st.session_state["msg_sucesso"]

# =========================================================
# 2. CONEXÃO DIRETA COM GOOGLE SHEETS
# =========================================================
@st.cache_resource
def conectar_gsheets():
    try:
        creds_dict = st.secrets["connections"]["gsheets"]
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        spreadsheet_url = creds_dict.get("spreadsheet", "")
        if spreadsheet_url:
            sheet = client.open_by_url(spreadsheet_url).sheet1
        else:
            sheet = client.openall()[0].sheet1
        return sheet
    except Exception as e:
        st.error(f"Erro ao conectar ao Google Sheets: {e}")
        return None

sheet = conectar_gsheets()

@st.cache_data(ttl=10)
def carregar_dados_planilha():
    if sheet is None:
        return pd.DataFrame()
    try:
        records = sheet.get_all_records()
        return pd.DataFrame(records)
    except Exception:
        return pd.DataFrame()

# =========================================================
# 3. VALIDAÇÕES DE E-MAIL, DATA, DUPLICIDADE E ESTOQUE (90)
# =========================================================
TOTAL_CHROMEBOOKS_ESCOLA = 90
DOMINIOS_PERMITIDOS = ("@gdv.com.br", "@gdv.pro.br")

def validar_email_gdv(email_str):
    email_limpo = email_str.strip().lower()
    if "@" not in email_limpo or email_limpo.startswith("@"):
        return False
    return email_limpo.endswith(DOMINIOS_PERMITIDOS)

def normalizar_data(valor):
    s = str(valor).strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return s

def verificar_duplicidade_ou_conflito(nova_reserva, tipo_recurso):
    try:
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
    except Exception:
        df = carregar_dados_planilha()

    if df.empty:
        return False, ""

    df["data_norm"] = df["data"].apply(normalizar_data)
    df["inicio_str"] = df["inicio"].astype(str).str.strip()
    df["fim_str"] = df["fim"].astype(str).str.strip()
    df["email_str"] = df["email"].astype(str).str.strip().str.lower()
    df["unidade_str"] = df["unidade"].astype(str).str.strip()
    df["obs_str"] = df["obs"].astype(str)

    data_alvo = normalizar_data(nova_reserva["data"])
    mesmo_dia = df[df["data_norm"] == data_alvo]
    if mesmo_dia.empty:
        return False, ""

    # 1. Bloqueio de reserva idêntica
    duplicada = mesmo_dia[
        (mesmo_dia["email_str"] == nova_reserva["email"]) &
        (mesmo_dia["unidade_str"] == nova_reserva["unidade"]) &
        (mesmo_dia["inicio_str"] == nova_reserva["inicio"]) &
        (mesmo_dia["fim_str"] == nova_reserva["fim"])
    ]
    if not duplicada.empty:
        return True, "Voce ja possui uma reserva identica cadastrada para esta data, local e horario."

    # 2. Verificação de estoque máximo de 90 Chromebooks no mesmo intervalo
    if tipo_recurso == "CHROMEBOOK":
        chromes_dia = mesmo_dia[mesmo_dia["obs_str"].str.contains(r"\
