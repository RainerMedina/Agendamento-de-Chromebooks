import streamlit as st
from datetime import datetime, date
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# =========================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# =========================================================
st.set_page_config(
    page_title="Portal de Reservas - GDV",
    page_icon="🏫",
    layout="wide"
)

# Ocultar o menu superior padrão do Streamlit
ocultar_menu = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(ocultar_menu, unsafe_allow_html=True)

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# =========================================================
# 2. FUNÇÕES PARA MANIPULAR A PLANILHA (SALVAR E CANCELAR)
# =========================================================
def salvar_reserva(nova_reserva):
    try:
        df_atual = conn.read(ttl=0)
        df_novo = pd.DataFrame([nova_reserva])
        df_final = pd.concat([df_atual, df_novo], ignore_index=True)
        conn.update(worksheet="Página1", data=df_final)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar na planilha: {e}")
        return False

def cancelar_reserva_por_data_horario(email_solicitante, data_reserva, inicio_reserva):
    try:
        df_atual = conn.read(ttl=0)
        if df_atual.empty:
            return False, "Nenhuma reserva encontrada no sistema."
        
        # Normalização dos dados para busca
        df_atual['email_norm'] = df_atual['email'].astype(str).str.strip().str.lower()
        df_atual['data_norm'] = df_atual['data'].astype(str).str.strip()
        df_atual['inicio_norm'] = df_atual['inicio'].astype(str).str.strip()

        email_busca = str(email_solicitante).strip().lower()
        data_busca = str(data_reserva).strip()
        inicio_busca = inicio_reserva.strftime("%H:%M").strip()

        # Procura a reserva correspondente ao E-mail, Data e Horário de Início
        filtro = (
            (df_atual['email_norm'] == email_busca) & 
            (df_atual['data_norm'] == data_busca) & 
            (df_atual['inicio_norm'] == inicio_busca)
        )
        
        if not df_atual[filtro].empty:
            # Remove a linha encontrada e limpa as colunas auxiliares antes de atualizar a planilha
            df_atualizado = df_atual[~filtro].drop(columns=['email_norm', 'data_norm', 'inicio_norm'])
            conn.update(worksheet="Página1", data=df_atualizado)
            return True, "Reserva cancelada com sucesso!"
        else:
            return False, "Nenhuma reserva encontrada para os dados informados (E-mail, Data e Horário)."
    except Exception as e:
        return False, f"Erro ao processar o cancelamento: {e}"

# =========================================================
# 3. CABEÇALHO COM LOGO E NAVEGAÇÃO POR ABAS
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
            data_chrome = st.date_input("Data do uso*", min_value=date.today(), key="c_data")
            col_h1, col_h2 = st.columns(2)
            with col_h1:
                inicio_chrome = st.time_input("Horário Início*", key="c_inicio")
            with col_h2:
                fim_chrome = st.time_input("Horário Fim*", key="c_fim")
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
                "email": email_chrome,
                "unidade": unidade_chrome,
                "data": str(data_chrome),
                "inicio": inicio_chrome.strftime("%H:%M"),
                "fim": fim_chrome.strftime("%H:%M"),
                "quantidade": int(qtd_chrome),
                "obs": f"[CHROMEBOOK] {obs_chrome}" if obs_chrome else "[CHROMEBOOK]"
            }
            
            if salvar_reserva(dados):
                st.success("Reserva de Chromebooks realizada com sucesso!")

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
            data_aud = st.date_input("Data do Evento / Aula*", min_value=date.today(), key="a_data")
            
            col_ah1, col_ah2 = st.columns(2)
            with col_ah1:
                inicio_aud = st.time_input("Horário Início*", key="a_inicio")
            with col_ah2:
                fim_aud = st.time_input("Horário Fim*", key="a_fim")

        with col2:
            st.markdown("##### 🛠️ Equipamentos Necessários")
            
            recurso_visuo = st.radio("Apresentação Visual:", [
                "Nenhum",
                "Projetor / DataShow",
                "Lousa Digital / Interativa"
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
                "email": email_aud,
                "unidade": "Auditório GDV",
                "data": str(data_aud),
                "inicio": inicio_aud.strftime("%H:%M"),
                "fim": fim_aud.strftime("%H:%M"),
                "quantidade": 1,
                "obs": obs_final
            }
            
            if salvar_reserva(dados_aud):
                st.success("Reserva do Auditório confirmada com sucesso!")

# =========================================================
# ABA 3: PAINEL DE CONSULTA DE RESERVAS
# =========================================================
with aba_minhas_reservas:
    st.subheader("📋 Reservas Cadastradas no Sistema")
    
    if st.button("🔄 Atualizar Lista de Reservas"):
        st.rerun()
        
    try:
        df_reservas = conn.read(ttl=0)
        
        if df_reservas.empty:
            st.info("Nenhuma reserva registrada no momento.")
        else:
            colunas_visiveis = ["professor", "unidade", "data", "inicio", "fim", "quantidade", "obs"]
            df_exibicao = df_reservas[colunas_visiveis]
            
            st.dataframe(
                df_exibicao.sort_values(by="data", ascending=False),
                use_container_width=True,
                hide_index=True
            )
    except Exception as e:
        st.warning("Aguardando novas reservas ou atualize a página.")

# =========================================================
# ABA 4: CANCELAMENTO DE RESERVA (POR E-MAIL, DIA E HORÁRIO)
# =========================================================
with aba_cancelar:
    st.subheader("❌ Cancelar uma Reserva Existente")
    st.caption("Informe seu e-mail institucional, a data e o horário de início da reserva que deseja cancelar.")

    with st.form("form_cancelamento"):
        email_cancelar = st.text_input("Seu E-mail Institucional*", key="canc_email")
        
        col_canc1, col_canc2 = st.columns(2)
        with col_canc1:
            data_cancelar = st.date_input("Data da Reserva*", key="canc_data")
        with col_canc2:
            inicio_cancelar = st.time_input("Horário de Início*", key="canc_inicio")
            
        btn_cancelar = st.form_submit_button("Confirmar Cancelamento")

    if btn_cancelar:
        if not email_cancelar:
            st.warning("Por favor, preencha seu e-mail institucional.")
        else:
            sucesso, msg = cancelar_reserva_por_data_horario(email_cancelar, data_cancelar, inicio_cancelar)
            if sucesso:
                st.success(msg)
            else:
                st.error(msg)
