
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

ocultar_menu = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(ocultar_menu, unsafe_allow_html=True)

# =========================================================
# 2. CONEXÃO COM GOOGLE SHEETS
# =========================================================

@st.cache_resource
def conectar_planilha():
    return st.connection("gsheets", type=GSheetsConnection)

conn = conectar_planilha()

COLUNAS = [
    "id", "professor", "email", "unidade",
    "data", "inicio", "fim", "quantidade", "obs"
]

def ler_reservas():
    df = conn.read(worksheet="Página1", ttl=0)

    if df.empty:
        return pd.DataFrame(columns=COLUNAS)

    for coluna in COLUNAS:
        if coluna not in df.columns:
            df[coluna] = ""

    return df[COLUNAS].copy()


# =========================================================
# 3. FUNÇÕES DE MANIPULAÇÃO DA PLANILHA
# =========================================================

def salvar_reserva(nova_reserva):
    try:
        df_atual = ler_reservas()
        df_novo = pd.DataFrame([nova_reserva])
        df_final = pd.concat(
            [df_atual, df_novo],
            ignore_index=True
        )

        conn.update(
            worksheet="Página1",
            data=df_final
        )

        return True

    except Exception as e:
        st.error(f"Erro ao salvar na planilha: {e}")
        return False


def buscar_reservas_por_email(email_busca):
    try:
        df = ler_reservas()

        if df.empty:
            return pd.DataFrame(columns=COLUNAS)

        email_limpo = str(email_busca).strip().lower()

        df["email_norm"] = (
            df["email"].astype(str).str.strip().str.lower()
        )

        resultado = df[
            df["email_norm"] == email_limpo
        ].copy()

        return resultado.drop(columns=["email_norm"])

    except Exception as e:
        st.error(f"Erro ao buscar reservas: {e}")
        return pd.DataFrame(columns=COLUNAS)


def remover_reserva_por_id(id_reserva):
    try:
        df = ler_reservas()

        if df.empty:
            st.warning("Não existem reservas para cancelar.")
            return False

        df["id"] = df["id"].astype(str)

        df_atualizado = df[
            df["id"] != str(id_reserva)
        ].copy()

        if len(df_atualizado) == len(df):
            st.warning("Reserva não encontrada.")
            return False

        conn.update(
            worksheet="Página1",
            data=df_atualizado
        )

        return True

    except Exception as e:
        st.error(f"Erro ao remover reserva: {e}")
        return False


# =========================================================
# 4. VALIDAÇÃO DE HORÁRIOS
# =========================================================

def horarios_validos(inicio, fim):
    return fim > inicio


# =========================================================
# 5. CABEÇALHO
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
        "Gerenciamento integrado de Chromebooks "
        "e Auditório para professores e colaboradores."
    )


# =========================================================
# 6. ABAS
# =========================================================

aba_chromebook, aba_auditorio, aba_minhas_reservas, aba_cancelar = st.tabs([
    "💻 Reservar Chromebooks",
    "🎭 Reservar Auditório",
    "📋 Painel de Reservas",
    "❌ Cancelar Reserva"
])


# =========================================================
# ABA 1 - CHROMEBOOKS
# =========================================================

with aba_chromebook:

    st.subheader("💻 Agendamento de Carrinho de Chromebooks")

    with st.form("form_chromebook"):

        col1, col2 = st.columns(2)

        with col1:
            prof_chrome = st.text_input(
                "Nome do Professor / Solicitante*",
                key="c_prof"
            )

            email_chrome = st.text_input(
                "E-mail institucional*",
                key="c_email"
            )

            unidade_chrome = st.selectbox(
                "Unidade / Bloco*",
                [
                    "Unidade Play",
                    "Bloco 2",
                    "Bloco 3",
                    "Bloco 7"
                ],
                key="c_unidade"
            )

        with col2:
            data_chrome = st.date_input(
                "Data do uso*",
                min_value=date.today(),
                key="c_data"
            )

            col_h1, col_h2 = st.columns(2)

            with col_h1:
                inicio_chrome = st.time_input(
                    "Horário Início*",
                    key="c_inicio"
                )

            with col_h2:
                fim_chrome = st.time_input(
                    "Horário Fim*",
                    key="c_fim"
                )

            qtd_chrome = st.number_input(
                "Quantidade de Chromebooks*",
                min_value=1,
                max_value=50,
                value=30,
                key="c_qtd"
            )

        obs_chrome = st.text_area(
            "Observações / Solicitações especiais",
            key="c_obs"
        )

        submit_chrome = st.form_submit_button(
            "Confirmar Reserva de Chromebooks"
        )

    if submit_chrome:

        if not prof_chrome.strip() or not email_chrome.strip():
            st.error("Preencha o nome e o e-mail.")

        elif "@" not in email_chrome:
            st.error("Informe um e-mail válido.")

        elif not horarios_validos(inicio_chrome, fim_chrome):
            st.error("O horário final deve ser posterior ao inicial.")

        else:

            id_reserva = (
                f"CHR-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            )

            dados = {
                "id": id_reserva,
                "professor": prof_chrome.strip(),
                "email": email_chrome.strip(),
                "unidade": unidade_chrome,
                "data": str(data_chrome),
                "inicio": inicio_chrome.strftime("%H:%M"),
                "fim": fim_chrome.strftime("%H:%M"),
                "quantidade": int(qtd_chrome),
                "obs": (
                    f"[CHROMEBOOK] {obs_chrome}"
                    if obs_chrome else "[CHROMEBOOK]"
                )
            }

            if salvar_reserva(dados):
                st.success(
                    "Reserva de Chromebooks realizada com sucesso!"
                )


# =========================================================
# ABA 2 - AUDITÓRIO
# =========================================================

with aba_auditorio:

    st.subheader("🎭 Agendamento do Auditório GDV")

    with st.form("form_auditorio"):

        col1, col2 = st.columns(2)

        with col1:

            prof_aud = st.text_input(
                "Nome do Solicitante / Responsável*",
                key="a_prof"
            )

            email_aud = st.text_input(
                "E-mail institucional*",
                key="a_email"
            )

            st.text_input(
                "Local*",
                value="Auditório GDV",
                disabled=True
            )

            data_aud = st.date_input(
                "Data do Evento / Aula*",
                min_value=date.today(),
                key="a_data"
            )

            col_ah1, col_ah2 = st.columns(2)

            with col_ah1:
                inicio_aud = st.time_input(
                    "Horário Início*",
                    key="a_inicio"
                )

            with col_ah2:
                fim_aud = st.time_input(
                    "Horário Fim*",
                    key="a_fim"
                )

        with col2:

            st.markdown("##### 🛠️ Equipamentos Necessários")

            recurso_visuo = st.radio(
                "Apresentação Visual:",
                [
                    "Nenhum",
                    "Projetor / DataShow",
                    "Lousa Digital / Interativa"
                ],
                key="a_visuo"
            )

            qtd_mic = st.slider(
                "Quantidade de Microfones sem fio:",
                min_value=0,
                max_value=4,
                value=1,
                key="a_mic"
            )

            sistema_som = st.selectbox(
                "Sistema de Som:",
                [
                    "Som Geral do Auditório (Mesa + Caixas Fixas)",
                    "Caixa de Som Portátil com Bluetooth",
                    "Sem necessidade de Som"
                ],
                key="a_som"
            )

        obs_aud = st.text_area(
            "Descrição do Evento / Observações adicionais para a TI",
            key="a_obs"
        )

        submit_aud = st.form_submit_button(
            "Confirmar Reserva do Auditório"
        )

    if submit_aud:

        if not prof_aud.strip() or not email_aud.strip():
            st.error("Preencha o nome e o e-mail.")

        elif "@" not in email_aud:
            st.error("Informe um e-mail válido.")

        elif not horarios_validos(inicio_aud, fim_aud):
            st.error("O horário final deve ser posterior ao inicial.")

        else:

            id_reserva_aud = (
                f"AUD-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            )

            detalhes = (
                f"[AUDITÓRIO] Visual: {recurso_visuo} | "
                f"Mics: {qtd_mic} | Som: {sistema_som}"
            )

            obs_final = (
                f"{detalhes} | Obs: {obs_aud}"
                if obs_aud else detalhes
            )

            dados_aud = {
                "id": id_reserva_aud,
                "professor": prof_aud.strip(),
                "email": email_aud.strip(),
                "unidade": "Auditório GDV",
                "data": str(data_aud),
                "inicio": inicio_aud.strftime("%H:%M"),
                "fim": fim_aud.strftime("%H:%M"),
                "quantidade": 1,
                "obs": obs_final
            }

            if salvar_reserva(dados_aud):
                st.success(
                    "Reserva do Auditório confirmada com sucesso!"
                )


# =========================================================
# ABA 3 - PAINEL DE CONSULTA
# =========================================================

with aba_minhas_reservas:

    st.subheader("📋 Reservas Cadastradas no Sistema")

    if st.button("🔄 Atualizar Lista de Reservas"):

        st.cache_data.clear()
        st.rerun()

    try:

        df_reservas = ler_reservas()

        if df_reservas.empty:

            st.info("Nenhuma reserva registrada no momento.")

        else:

            colunas_visiveis = [
                "professor",
                "unidade",
                "data",
                "inicio",
                "fim",
                "quantidade",
                "obs"
            ]

            df_exibicao = df_reservas[
                colunas_visiveis
            ].copy()

            df_exibicao = df_exibicao.sort_values(
                by="data",
                ascending=False
            )

            # Tabela simples: evita o componente DataFrame
            st.table(df_exibicao)

    except Exception as e:

        st.error(
            f"Erro ao consultar reservas: {e}"
        )


# =========================================================
# ABA 4 - CANCELAMENTO DE RESERVAS
# =========================================================

with aba_cancelar:

    st.subheader("❌ Cancelar Agendamento")

    st.caption(
        "Digite seu e-mail institucional para listar "
        "seus agendamentos ativos."
    )

    email_busca = st.text_input(
        "Informe seu E-mail Institucional*",
        key="busca_email_cancelar"
    )

    if email_busca:

        df_meus = buscar_reservas_por_email(email_busca)

        if df_meus.empty:

            st.warning(
                "Nenhum agendamento encontrado para este e-mail."
            )

        else:

            st.success(
                f"Encontrado(s) {len(df_meus)} agendamento(s)."
            )

            opcoes_reserva = {}

            for _, row in df_meus.iterrows():

                rotulo = (
                    f"📅 {row['data']} | "
                    f"⏰ {row['inicio']} às {row['fim']} | "
                    f"📍 {row['unidade']} | "
                    f"{str(row['obs'])[:30]}"
                )

                opcoes_reserva[rotulo] = str(row["id"])

            reserva_selecionada = st.selectbox(
                "Selecione o agendamento que deseja cancelar:",
                options=list(opcoes_reserva.keys())
            )

            if st.button(
                "🗑️ Confirmar Cancelamento da Reserva Selecionada",
                type="primary"
            ):

                id_para_remover = opcoes_reserva[
                    reserva_selecionada
                ]

                if remover_reserva_por_id(id_para_remover):

                    st.success(
                        "Reserva cancelada com sucesso!"
                    )

                    st.rerun()
