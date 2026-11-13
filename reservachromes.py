import streamlit as st
from datetime import datetime, date, time
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# =========================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# =========================================================
st.set_page_config(
    page_title="Portal de Reservas - GDV",
    page_icon="🏫",
    layout="wide"
)

st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Exibe mensagem persistente no topo após st.rerun()
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
    """Verifica se o e-mail possui formato básico e termina com os domínios institucionais."""
    email_limpo = email_str.strip().lower()
    if "@" not in email_limpo or email_limpo.startswith("@"):
        return False
    return email_limpo.endswith(DOMINIOS_PERMITIDOS)

def normalizar_data(valor):
    """Converte datas em DD/MM/YYYY, DD-MM-YYYY ou YYYY-MM-DD para o padrão DD/MM/YYYY."""
    s = str(valor).strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return s

def verificar_duplicidade_ou_conflito(nova_reserva, tipo_recurso):
    """
    Retorna (True, motivo) se houver duplicidade, conflito de horário ou falta de estoque.
    Retorna (False, "") se estiver livre para reservar.
    """
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

    # 1. Bloqueio de reserva idêntica (clique duplo / reenvio)
    duplicada = mesmo_dia[
        (mesmo_dia["email_str"] == nova_reserva["email"]) &
        (mesmo_dia["unidade_str"] == nova_reserva["unidade"]) &
        (mesmo_dia["inicio_str"] == nova_reserva["inicio"]) &
        (mesmo_dia["fim_str"] == nova_reserva["fim"])
    ]
    if not duplicada.empty:
        return True, "Você já possui uma reserva idêntica cadastrada para esta data, local e horário."

    # 2. Verificação de estoque máximo de 90 Chromebooks no mesmo intervalo
    if tipo_recurso == "CHROMEBOOK":
        chromes_dia = mesmo_dia[mesmo_dia["obs_str"].str.contains(r"[CHROMEBOOK]", regex=True)]
        qtd_ocupada = 0
        for _, row in chromes_dia.iterrows():
            if nova_reserva["inicio"] < row["fim_str"] and nova_reserva["fim"] > row["inicio_str"]:
                try:
                    qtd_ocupada += int(row["quantidade"])
                except (ValueError, TypeError):
                    pass

        disponiveis = TOTAL_CHROMEBOOKS_ESCOLA - qtd_ocupada
        if nova_reserva["quantidade"] > disponiveis:
            return True, f"Estoque insuficiente para este horário. Já existem {qtd_ocupada} Chromebooks reservados (restam {max(0, disponiveis)} de {TOTAL_CHROMEBOOKS_ESCOLA})."

    # 3. Bloqueio de sobreposição de horário no Auditório (espaço único)
    if tipo_recurso == "AUDITORIO":
        aud_dia = mesmo_dia[mesmo_dia["unidade_str"] == "Auditório GDV"]
        for _, row in aud_dia.iterrows():
            if nova_reserva["inicio"] < row["fim_str"] and nova_reserva["fim"] > row["inicio_str"]:
                return True, f"O Auditório já está reservado neste intervalo ({row['inicio_str']} às {row['fim_str']}) por {row['professor']}."

    return False, ""

# =========================================================
# 4. OPERAÇÕES NA PLANILHA
# =========================================================
def salvar_reserva(nova_reserva):
    if sheet is None:
        return False
    try:
        df_tmp = carregar_dados_planilha()
        headers = sheet.row_values(1) if not df_tmp.empty else ["id", "professor", "email", "email_copia", "unidade", "data", "inicio", "fim", "quantidade", "obs"]
        
        if not headers:
            headers = ["id", "professor", "email", "email_copia", "unidade", "data", "inicio", "fim", "quantidade", "obs"]
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
            if len(row) > id_col_idx and str(row[id_col_idx]).strip() == str(id_reserva).strip():
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
# 5. CABEÇALHO DA APLICAÇÃO
# =========================================================
col_logo, col_titulo = st.columns([1, 4])

with col_logo:
    try:
        st.image("Logo.png", width=160)
    except:
        st.write("🏫 **Colégio GDV**")

with col_titulo:
    st.title("Portal de Reservas - GDV")
    st.caption("Gerenciamento integrado de Chromebooks e Auditório para professores e colaboradores.")

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
            prof_chrome = st.text_area("Nome do Professor / Solicitante*", height=68, key="c_prof_ta")
            email_chrome = st.text_area("E-mail institucional principal (@gdv.com.br ou @gdv.pro.br)*", height=68, key="c_email_ta")
            email_copia_chrome = st.text_area("E-mail em cópia (Opcional - @gdv.com.br ou @gdv.pro.br)", height=68, key="c_email_copia_ta")
            unidade_chrome = st.selectbox("Unidade / Bloco*", [
                "Unidade Play", "Bloco 2", "Bloco 3", "Bloco 7"
            ], key="c_unidade")
            
        with col2:
            data_chrome_date = st.date_input(
                "Data do uso (Clique para abrir o calendário)*",
                value=date.today(),
                format="DD/MM/YYYY",
                key="c_data_cal"
            )
            col_h1, col_h2 = st.columns(2)
            with col_h1:
                inicio_chrome_time = st.time_input("
