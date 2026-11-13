import streamlit as st
from datetime import datetime, date, time
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
import os

st.set_page_config(
    page_title="Portal de Reservas - GDV",
    page_icon="🏫",
    layout="wide"
)

def aplicar_imagem_fundo(caminho):
    bg = ""
    if os.path.exists(caminho):
        with open(caminho, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        bg = (
            '.stApp {'
            f'background-image: url("data:image/jpeg;base64,{b64}");'
            'background-size: cover;'
            'background-position: center top;'
            'background-repeat: no-repeat;'
            'background-attachment: fixed;'
            '}'
            '.block-container {'
            'background-color: rgba(255, 255, 255, 0.35);'
            'backdrop-filter: blur(2px);'
            'border-radius: 16px;'
            'padding: 2rem 2.5rem;'
            'margin-top: 1.5rem;'
            'margin-bottom: 1.5rem;'
            '}'
            '[data-testid="stForm"],'
            '[data-testid="stDataFrame"] {'
            'background-color: rgba(255, 255, 255, 0.94);'
            'border-radius: 12px;'
            'padding: 1.5rem;'
            '}'
        )
    css = (
        "<style>"
        "#MainMenu {visibility: hidden;}"
        "footer {visibility: hidden;}"
        "header {visibility: hidden;}"
        f"{bg}"
        "</style>"
    )
    st.markdown(css, unsafe_allow_html=True)

aplicar_imagem_fundo("fundo_pag.jpeg")

if "msg_sucesso" in st.session_state:
    msg = st.session_state["msg_sucesso"]
    st.success(msg, icon="✅")
    st.toast(msg, icon="✅")
    del st.session_state["msg_sucesso"]

@st.cache_resource
def conectar_gsheets():
    try:
        creds = st.secrets["connections"]["gsheets"]
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        cred_obj = Credentials.from_service_account_info(
            creds, scopes=scope
        )
        client = gspread.authorize(cred_obj)
        url = creds.get("spreadsheet", "")
        if url:
            return client.open_by_url(url).sheet1
        return client.openall()[0].sheet1
    except Exception as e:
        st.error(f"Erro ao conectar ao Google Sheets: {e}")
        return None

sheet = conectar_gsheets()

@st.cache_data(ttl=10)
def carregar_dados_planilha():
    if sheet is None:
        return pd.DataFrame()
    try:
        return pd.DataFrame(sheet.get_all_records())
    except Exception:
        return pd.DataFrame()

TOTAL_CHR = 90
DOMINIOS = ("@gdv.com.br", "@gdv.pro.br")
COLUNAS = [
    "id", "professor", "email", "email_copia",
    "unidade", "data", "inicio", "fim",
    "quantidade", "obs"
]

def validar_email_gdv(email_str):
    e = email_str.strip().lower()
    if "@" not in e or e.startswith("@"):
        return False
    return e.endswith(DOMINIOS)

def normalizar_data(valor):
    s = str(valor).strip()
    formatos = ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d")
    for fmt in formatos:
        try:
            return datetime.strptime(s, fmt).strftime("%d/%m/%Y")
        except ValueError:
            pass
    return s

def verificar_conflito(nova, tipo):
    try:
        df = pd.DataFrame(sheet.get_all_records())
    except Exception:
        df = carregar_dados_planilha()

    if df.empty:
        return False, ""

    df["d_norm"] = df["data"].apply(normalizar_data)
    df["ini"] = df["inicio"].astype(str).str.strip()
    df["fim"] = df["fim"].astype(str).str.strip()
    df["em"] = df["email"].astype(str).str.strip().str.lower()
    df["un"] = df["unidade"].astype(str).str.strip()
    df["ob"] = df["obs"].astype(str)

    alvo = normalizar_data(nova["data"])
    dia = df[df["d_norm"] == alvo]
    if dia.empty:
        return False, ""

    dup = dia[
        (dia["em"] == nova["email"]) &
        (dia["un"] == nova["unidade"]) &
        (dia["ini"] == nova["inicio"]) &
        (dia["fim"] == nova["fim"])
    ]
    if not dup.empty:
        return True, (
            "Voce ja possui uma reserva identica cadastrada "
            "para esta data, local e horario."
        )

    if tipo == "CHROMEBOOK":
        ocupados = 0
        filtro = dia["ob"].str.contains("[CHROMEBOOK]", regex=False)
        for _, r in dia[filtro].iterrows():
            if nova["inicio"] < r["fim"] and nova["fim"] > r["ini"]:
                try:
                    ocupados += int(r["quantidade"])
                except (ValueError, TypeError):
                    pass
        disp = TOTAL_CHR - ocupados
        if nova["quantidade"] > disp:
            rest = max(0, disp)
            return True, (
                f"Estoque insuficiente. Ja existem {ocupados} "
                f"Chromebooks reservados (restam {rest} de {TOTAL_CHR})."
            )

    if tipo == "AUDITORIO":
        for _, r in dia[dia["un"] == "Auditório GDV"].iterrows():
            if nova["inicio"] < r["fim"] and nova["fim"] > r["ini"]:
                return True, (
                    f"O Auditorio ja esta reservado das "
                    f"{r['ini']} as {r['fim']} por {r['professor']}."
                )

    return False, ""

def salvar_reserva(nova):
    if sheet is None:
        return False
    try:
        df_tmp = carregar_dados_planilha()
        if not df_tmp.empty:
            headers = sheet.row_values(1)
        else:
            headers = list(COLUNAS)

        if not headers:
            headers = list(COLUNAS)
            sheet.append_