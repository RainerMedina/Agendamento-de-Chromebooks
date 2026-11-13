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
# 2. CONEXAO DIRETA COM GOOGLE SHEETS
# =========================================================
@st.cache_resource
def conectar_gsheets():
    try:
        creds_dict = st.secrets["connections"]["gsheets"]
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        credentials = Credentials.from_service_account_info(
            creds_dict, scopes=scope
        )
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
# 3. VALIDACOES DE E-MAIL, DATA, DUPLICIDADE E ESTOQUE
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

    duplicada = mesmo_dia[
        (mesmo_dia["email_str"] == nova_reserva["email"]) &
        (mesmo_dia["unidade_str"] == nova_reserva["unidade"]) &
        (mesmo_dia["inicio_str"] == nova_reserva["inicio"]) &
        (mesmo_dia["fim_str"] == nova_reserva["fim"])
    ]
    if not duplicada.empty:
        return True, (
            "Voce ja possui uma reserva identica cadastrada para "
            "esta data, local e horario."
        )

    if tipo_recurso == "CHROMEBOOK":
        filtro_chr = mesmo_dia["obs_str"].str.contains(
            "[CHROMEBOOK]", regex=False
        )
        chromes_dia = mesmo_dia[filtro_chr]
        qtd_ocupada = 0
        for _, row in chromes_dia.iterrows():
            cond_inicio = nova_reserva["inicio"] < row["fim_str"]
            cond_fim = nova_reserva["fim"] > row["inicio_str"]
            if cond_inicio and cond_fim:
                try:
                    qtd_ocupada += int(row["quantidade"])
                except (ValueError, TypeError):
                    pass

        disponiveis = TOTAL_CHROMEBOOKS_ESCOLA - qtd_ocupada
        if nova_reserva["quantidade"] > disponiveis:
            restantes = max(0, disponiveis)
            return True, (
                f"Estoque insuficiente para este horario. Ja existem "
                f"{qtd_ocupada} Chromebooks reservados (restam "
                f"{restantes} de {TOTAL_CHROMEBOOKS_ESCOLA})."
            )

    if tipo_recurso == "AUDITORIO":
        aud_dia = mesmo_dia[mesmo_dia["unidade_str"] == "Auditório GDV"]
        for _, row in aud_dia.iterrows():
            cond_inicio = nova_reserva["inicio"] < row["fim_str"]
            cond_fim = nova_reserva["fim"] > row["inicio_str"]
            if cond_inicio and cond_fim:
                return True, (
                    f"O Auditorio ja esta reservado neste intervalo "
                    f"({row['inicio_str']} as {row['fim_str']}) "
                    f"por {row['professor']}."
                )

    return False, ""

# =========================================================
# 4. OPERACOES NA PLANILHA
# =========================================================
COLUNAS_PADRAO = [
    "id", "professor", "email", "email_copia",
    "unidade", "data", "inicio", "fim", "quantidade", "obs"
]

def salvar_reserva(nova_reserva):
    if sheet is None:
        return False
    try:
        df_tmp = carregar_dados_planilha()
        headers = sheet.row_values(1) if not df_tmp.empty else list(COLUNAS_PADRAO)
        
        if not headers:
            headers = list(COLUNAS_PADRAO)
            sheet.append_row(headers)
        elif "email_copia" not in headers:
            sheet.update_cell(1, len(headers) + 1, "email_copia")
            headers.append("email_copia")
            
        linha = [nova_reserva.get(h, "") for h in headers]
        sheet.append_row(linha)
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
        if not data or len(data) <= 1:
            return False
            
        headers = data[0]
        if "id" not in headers:
            return False
            
        id_col_idx = headers.index("id")
        row_to_delete = None
        
        for idx, row in enumerate(data[1:], start=2):
            if len(row) > id_col_idx:
                val_atual = str(row[id_col_idx]).strip()
                if val_atual == str(id_reserva).strip():
                    row_to_delete = idx
                    break
                
        if row_to_delete:
            sheet.delete_rows(row_to_delete)
            st.cache_data.clear()
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao remover reserva: {e}")
        return False

# =========================================================
# 5. CABECALHO DA APLICACAO
# =========================================================
col_logo, col_titulo = st.columns([1, 4])

with col_logo:
    try:
        st.image("Logo.png", width=160)
    except Exception:
        st.write("🏫 **Colégio GDV**")

with col_titulo:
    st.title("Portal de Reservas - GDV")
    st.caption(
        "Gerenciamento integrado de Chromebooks e Auditório "
        "para professores e colaboradores."
    )

aba_chromebook, aba_auditorio, aba_minhas_reservas, aba_cancelar = st.tabs([
    "💻 Reservar Chromebooks",
    "🎭 Reservar Auditório",
    "📋 Painel de Reservas",
    "❌ Cancelar Reserva"
])

# =========================================================
# ABA 1: RESERVA DE CHROMEBOOKS
# =========================================================
with aba_chromebook:
    st.subheader("💻 Agendamento de Carrinho de Chromebooks")
    
    with st.form("form_chromebook", clear_on_submit=False):
        col1, col2 = st.columns(2)
        
        with col1:
            prof_chrome = st.text_area(
                "Nome do Professor / Solicitante*",
                height=68,
                key="c_prof_ta"
            )
            email_chrome = st.text_area(
                "E-mail principal (@gdv.com.br ou @gdv.pro.br)*",
                height=68,
                key="c_email_ta"
            )
            email_copia_chrome = st.text_area(
                "E-mail em copia (Opcional - @gdv.com.br ou @gdv.pro.br)",
                height=68,
                key="c_email_copia_ta"
            )
            unidade_chrome = st.selectbox(
                "Unidade / Bloco*",
                ["Unidade Play", "Bloco 2", "Bloco 3", "Bloco 7"],
                key="c_unidade"
            )
            
        with col2:
            data_chrome_date = st.date_input(
                "Data do uso (Clique para abrir o calendario)*",
                value=date.today(),
                format="DD/MM/YYYY",
                key="c_data_cal"
            )
            col_h1, col_h2 = st.columns(2)
            with col_h1:
                inicio_chrome_time = st.time_input(
                    "Horario Inicio*",
                    value=time(7, 50),
                    step=300,
                    key="c_inicio_time"
                )
            with col_h2:
                fim_chrome_time = st.time_input(
                    "Horario Fim*",
                    value=time(8, 40),
                    step=300,
                    key="c_fim_time"
                )
            qtd_chrome = st.number_input(
                "Quantidade de Chromebooks*",
                min_value=1,
                max_value=TOTAL_CHROMEBOOKS_ESCOLA,
                value=30,
                key="c_qtd"
            )
            obs_chrome = st.text_area(
                "Observacoes / Solicitacoes especiais",
                height=68,
                key="c_obs"
            )
            
        submit_chrome = st.form_submit_button(
            "Confirmar Reserva de Chromebooks"
        )
        
    if submit_chrome:
        prof_chrome_clean = prof_chrome.strip()
        email_chrome_clean = email_chrome.strip().lower()
        email_copia_chrome_clean = email_copia_chrome.strip().lower()
        data_chrome_clean = data_chrome_date.strftime("%d/%m/%Y")
        inicio_chrome_str = inicio_chrome_time.strftime("%H:%M")
        fim_chrome_str = fim_chrome_time.strftime("%H:%M")
        
        if not prof_chrome_clean or not email_chrome_clean:
            st.error(
                "Por favor, preencha os campos obrigatorios "
                "(Nome e E-mail principal)."
            )
        elif not validar_email_gdv(email_chrome_clean):
            st.error(
                "O e-mail principal deve terminar com "
                "@gdv.com.br ou @gdv.pro.br."
            )
        elif email_copia_chrome_clean and not validar_email_gdv(email_copia_chrome_clean):
            st.error(
                "O e-mail em copia deve terminar com "
                "@gdv.com.br ou @gdv.pro.br."
            )
        elif inicio_chrome_time >= fim_chrome_time:
            st.error(
                "O horario de termino deve ser maior que o horario de inicio."
            )
        else:
            ts_agora = datetime.now().strftime("%Y%m%d%H%M%S")
            id_reserva = f"CHR-{ts_agora}"
            obs_base = (
                f"[CHROMEBOOK] {obs_chrome}"
                if obs_chrome else "[CHROMEBOOK]"
            )
            if email_copia_chrome_clean
