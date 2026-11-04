import streamlit as st
from datetime import datetime, date
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

# =========================================================
# 2. CONEXÃO DIRETA COM GOOGLE SHEETS (GSPREAD NATIVO)
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

def salvar_reserva(nova_reserva):
    if sheet is None:
        return False
    try:
        df_tmp = carregar_dados_planilha()
        headers = sheet.row_values(1) if not df_tmp.empty else ["id", "professor", "email", "unidade", "data", "inicio", "fim", "quantidade", "obs"]
        
        if not headers:
            headers = ["id", "professor", "email", "unidade", "data", "inicio", "fim", "quantidade", "obs"]
            sheet.append_row(headers)
            
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

# Lista de horários padrão para seleções sem falhas no frontend
HORARIOS_DISPONIVEIS = [
    "07:00", "07:50", "08:40", "09:30", "10:40", "11:30", "12:20",
    "13:10", "14:00", "14:50", "15:40", "16:30", "17:20", "18:10", "19:00"
]

# =========================================================
# 3. CABEÇALHO DA APLICAÇÃO
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
    
    with st.form("form_chromebook"):
        col1, col2 = st.columns(2)
        
        with col1:
            prof_chrome = st.text_input("Nome do Professor / Solicitante*", key="c_prof")
            email_chrome = st.text_input("E-mail institucional*", key="c_email")
            unidade_chrome = st.selectbox("Unidade / Bloco*", [
                "Unidade Play", "Bloco 2", "Bloco 3", "Bloco 7"
            ], key="c_unidade")
            
        with col2:
            data_chrome = st.text_input("Data do uso (AAAA-MM-DD)*", value=str(date.today()), key="c_data")
            col_h1, col_h2 = st.columns(2)
            with col_h1:
                inicio_chrome = st.selectbox("Horário Início*", HORARIOS_DISPONIVEIS, index=1, key="c_inicio")
            with col_h2:
                fim_chrome = st.selectbox("Horário Fim*", HORARIOS_DISPONIVEIS, index=2, key="c_fim")
            qtd_chrome = st.number_input("Quantidade de Chromebooks*", min_value=1, max_value=50, value=30, key="c_qtd")
            
        obs_chrome = st.text_area("Observações / Solicitações especiais", key="c_obs")
        submit_chrome = st.form_submit_button("Confirmar Reserva de Chromebooks")
        
    if submit_chrome:
        if not prof_chrome or not email_chrome:
            st.error("Por favor, preencha os campos obrigatórios (Nome e E-mail).")
        else:
            id_reserva = f"CHR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            dados = {
                "id": str(id_reserva),
                "professor": prof_chrome,
                "email": email_chrome.strip().lower(),
                "unidade": unidade_chrome,
                "data": str(data_chrome),
                "inicio": str(inicio_chrome),
                "fim": str(fim_chrome),
                "quantidade": int(qtd_chrome),
                "obs": f"[CHROMEBOOK] {obs_chrome}" if obs_chrome else "[CHROMEBOOK]"
            }
            if salvar_reserva(dados):
                st.success("Reserva de Chromebooks realizada com sucesso!")
                st.rerun()

# =========================================================
# ABA 2: RESERVA DE AUDITÓRIO
# =========================================================
with aba_auditorio:
    st.subheader("🎭 Agendamento do Auditório GDV")
    
    with st.form("form_auditorio"):
        col1, col2 = st.columns(2)
        
        with col1:
            prof_aud = st.text_input("Nome do Solicitante / Responsável*", key="a_prof")
            email_aud = st.text_input("E-mail institucional*", key="a_email")
            unidade_aud = st.text_input("Local*", value="Auditório GDV", disabled=True, key="a_unidade")
            data_aud = st.text_input("Data do Evento / Aula (AAAA-MM-DD)*", value=str(date.today()), key="a_data")
            
            col_ah1, col_ah2 = st.columns(2)
            with col_ah1:
                inicio_aud = st.selectbox("Horário Início*", HORARIOS_DISPONIVEIS, index=1, key="a_inicio")
            with col_ah2:
                fim_aud = st.selectbox("Horário Fim*", HORARIOS_DISPONIVEIS, index=3, key="a_fim")

        with col2:
            st.markdown("##### 🛠️ Equipamentos Necessários")
            recurso_visuo = st.radio("Apresentação Visual:", [
                "Nenhum", "Projetor / DataShow", "Lousa Digital / Interativa"
            ], key="a_visuo")
            qtd_mic = st.slider("Quantidade de Microfones sem fio:", min_value=0, max_value=4, value=1, key="a_mic")
            sistema_som = st.selectbox("Sistema de Som:", [
                "Som Geral do Auditório (Mesa + Caixas Fixas)",
                "Caixa de Som Portátil com Bluetooth",
                "Sem necessidade de Som"
            ], key="a_som")

        obs_aud = st.text_area("Descrição do Evento / Observações adicionais para a TI", key="a_obs")
        submit_aud = st.form_submit_button("Confirmar Reserva do Auditório")

    if submit_aud:
        if not prof_aud or not email_aud:
            st.error("Por favor, preencha os campos obrigatórios (Nome e E-mail).")
        else:
            id_reserva_aud = f"AUD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            detalhes_equipamentos = f"[AUDITÓRIO] Visual: {recurso_visuo} | Mics: {qtd_mic} | Som: {sistema_som}"
            obs_final = f"{detalhes_equipamentos} | Obs: {obs_aud}" if obs_aud else detalhes_equipamentos
            
            dados_aud = {
                "id": str(id_reserva_aud),
                "professor": prof_aud,
                "email": email_aud.strip().lower(),
                "unidade": "Auditório GDV",
                "data": str(data_aud),
                "inicio": str(inicio_aud),
                "fim": str(fim_aud),
                "quantidade": 1,
                "obs": obs_final
            }
            if salvar_reserva(dados_aud):
                st.success("Reserva do Auditório confirmada com sucesso!")
                st.rerun()

# =========================================================
# ABA 3: PAINEL DE CONSULTA DE RESERVAS
# =========================================================
with aba_minhas_reservas:
    st.subheader("📋 Reservas Cadastradas no Sistema")
    
    if st.button("🔄 Atualizar Lista de Reservas"):
        st.cache_data.clear()
        st.rerun()
        
    df_reservas = carregar_dados_planilha()
    
    if df_reservas.empty:
        st.info("Nenhuma reserva registrada no momento ou a carregar dados...")
    else:
        colunas_visiveis = ["professor", "unidade", "data", "inicio", "fim", "quantidade", "obs"]
        cols_existentes = [c for c in colunas_visiveis if c in df_reservas.columns]
        
        df_exibicao = df_reservas[cols_existentes].copy()
        if "data" in df_exibicao.columns:
            df_exibicao = df_exibicao.sort_values(by="data", ascending=False)
            
        st.dataframe(
            df_exibicao,
            use_container_width=True,
            hide_index=True,
            height=400
        )

# =========================================================
# ABA 4: CANCELAMENTO DINÂMICO POR E-MAIL
# =========================================================
with aba_cancelar:
    st.subheader("❌ Cancelar Agendamento")
    st.caption("Digite o seu e-mail institucional para visualizar os seus agendamentos ativos e realizar o cancelamento.")

    email_busca = st.text_input("Informe o seu E-mail Institucional*", key="busca_email_cancelar")
    
    if email_busca:
        df_todas = carregar_dados_planilha()
        
        if not df_todas.empty and "email" in df_todas.columns:
            df_todas['email_norm'] = df_todas['email'].astype(str).str.strip().str.lower()
            df_meus = df_todas[df_todas['email_norm'] == email_busca.strip().lower()]
            
            if df_meus.empty:
                st.warning("Nenhum agendamento encontrado para este e-mail.")
