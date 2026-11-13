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

# =========================================================
# 3. VALIDACOES E OPERACOES NA PLANILHA
# =========================================================
TOTAL_CHROMEBOOKS = 90
DOMINIOS = ("@gdv.com.br", "@gdv.pro.br")
COLUNAS = ["id", "professor", "email", "email_copia", "unidade", "data", "inicio", "fim", "quantidade", "obs"]

def validar_email_gdv(email_str):
    e = email_str.strip().lower()
    return "@" in e and not e.startswith("@") and e.endswith(DOMINIOS)

def normalizar_data(valor):
    s = str(valor).strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d"):
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

    dia = df[df["d_norm"] == normalizar_data(nova["data"])]
    if dia.empty:
        return False, ""

    dup = dia[(dia["em"] == nova["email"]) & (dia["un"] == nova["unidade"]) & (dia["ini"] == nova["inicio"]) & (dia["fim"] == nova["fim"])]
    if not dup.empty:
        return True, "Voce ja possui uma reserva identica cadastrada para esta data, local e horario."

    if tipo == "CHROMEBOOK":
        ocupados = 0
        for _, r in dia[dia["ob"].str.contains("[CHROMEBOOK]", regex=False)].iterrows():
            if nova["inicio"] < r["fim"] and nova["fim"] > r["ini"]:
                try:
                    ocupados += int(r["quantidade"])
                except (ValueError, TypeError):
                    pass
        disp = TOTAL_CHROMEBOOKS - ocupados
        if nova["quantidade"] > disp:
            return True, f"Estoque insuficiente. Ja existem {ocupados} Chromebooks reservados (restam {max(0, disp)} de {TOTAL_CHROMEBOOKS})."

    if tipo == "AUDITORIO":
        for _, r in dia[dia["un"] == "Auditório GDV"].iterrows():
            if nova["inicio"] < r["fim"] and nova["fim"] > r["ini"]:
                return True, f"O Auditorio ja esta reservado das {r['ini']} as {r['fim']} por {r['professor']}."

    return False, ""

def salvar_reserva(nova):
    if sheet is None:
        return False
    try:
        df_tmp = carregar_dados_planilha()
        headers = sheet.row_values(1) if not df_tmp.empty else list(COLUNAS)
        if not headers:
            headers = list(COLUNAS)
            sheet.append_row(headers)
        elif "email_copia" not in headers:
            sheet.update_cell(1, len(headers) + 1, "email_copia")
            headers.append("email_copia")
        sheet.append_row([nova.get(h, "") for h in headers])
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar reserva: {e}")
        return False

def remover_reserva_por_id(id_reserva):
    if sheet is None:
        return False
    try:
        data = sheet.get_all_values()
        if not data or len(data) <= 1 or "id" not in data[0]:
            return False
        col_id = data[0].index("id")
        for idx, row in enumerate(data[1:], start=2):
            if len(row) > col_id and str(row[col_id]).strip() == str(id_reserva).strip():
                sheet.delete_rows(idx)
                st.cache_data.clear()
                return True
        return False
    except Exception as e:
        st.error(f"Erro ao remover reserva: {e}")
        return False

# =========================================================
# 4. CABECALHO E ABAS
# =========================================================
col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    try:
        st.image("Logo.png", width=160)
    except Exception:
        st.write("🏫 **Colégio GDV**")
with col_titulo:
    st.title("Portal de Reservas - GDV")
    st.caption("Gerenciamento integrado de Chromebooks e Auditório para professores e colaboradores.")

aba_chr, aba_aud, aba_painel, aba_canc = st.tabs([
    "💻 Reservar Chromebooks",
    "🎭 Reservar Auditório",
    "📋 Painel de Reservas",
    "❌ Cancelar Reserva"
])

# =========================================================
# ABA 1: CHROMEBOOKS
# =========================================================
with aba_chr:
    st.subheader("💻 Agendamento de Carrinho de Chromebooks")
    with st.form("form_chromebook", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            prof_c = st.text_area("Nome do Professor / Solicitante*", height=68, key="c_prof")
            email_c = st.text_area("E-mail principal (@gdv.com.br ou @gdv.pro.br)*", height=68, key="c_email")
            copia_c = st.text_area("E-mail em copia (Opcional - @gdv.com.br ou @gdv.pro.br)", height=68, key="c_copia")
            unid_c = st.selectbox("Unidade / Bloco*", ["Unidade Play", "Bloco 2", "Bloco 3", "Bloco 7"], key="c_unid")
        with c2:
            data_c = st.date_input("Data do uso*", value=date.today(), format="DD/MM/YYYY", key="c_data")
            ch1, ch2 = st.columns(2)
            ini_c = ch1.time_input("Horario Inicio*", value=time(7, 50), step=300, key="c_ini")
            fim_c = ch2.time_input("Horario Fim*", value=time(8, 40), step=300, key="c_fim")
            qtd_c = st.number_input("Quantidade de Chromebooks*", min_value=1, max_value=TOTAL_CHROMEBOOKS, value=30, key="c_qtd")
            obs_c = st.text_area("Observacoes / Solicitacoes especiais", height=68, key="c_obs")
        sub_c = st.form_submit_button("Confirmar Reserva de Chromebooks")

    if sub_c:
        p_clean = prof_c.strip()
        e_clean = email_c.strip().lower()
        cp_clean = copia_c.strip().lower()
        d_clean = data_c.strftime("%d/%m/%Y")
        i_str = ini_c.strftime("%H:%M")
        f_str = fim_c.strftime("%H:%M")

        if not p_clean or not e_clean:
            st.error("Preencha os campos obrigatorios (Nome e E-mail principal).")
        elif not validar_email_gdv(e_clean):
            st.error("O e-mail principal deve terminar com @gdv.com.br ou @gdv.pro.br.")
        elif cp_clean and not validar_email_gdv(cp_clean):
            st.error("O e-mail em copia deve terminar com @gdv.com.br ou @gdv.pro.br.")
        elif ini_c >= fim_c:
            st.error("O horario de termino deve ser maior que o horario de inicio.")
        else:
            id_res = f"CHR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            obs_txt = f"[CHROMEBOOK] {obs_c}" if obs_c else "[CHROMEBOOK]"
            if cp_clean:
                obs_txt = f"{obs_txt} | Copia: {cp_clean}"
            dados = {
                "id": id_res, "professor": p_clean, "email": e_clean, "email_copia": cp_clean,
                "unidade": unid_c, "data": d_clean, "inicio": i_str, "fim": f_str,
                "quantidade": int(qtd_c), "obs": obs_txt
            }
            bloq, mot = verificar_conflito(dados, "CHROMEBOOK")
            if bloq:
                st.warning(f"⚠️ Reserva nao realizada: {mot}")
            else:
                with st.spinner("Registrando reserva na planilha..."):
                    if salvar_reserva(dados):
                        st.session_state["msg_sucesso"] = f"Reserva de {qtd_c} Chromebooks ({id