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
            sheet.append_row(headers)
        elif "email_copia" not in headers:
            sheet.update_cell(1, len(headers) + 1, "email_copia")
            headers.append("email_copia")

        linha = [nova.get(h, "") for h in headers]
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
        if not data or len(data) <= 1 or "id" not in data[0]:
            return False
        col_id = data[0].index("id")
        alvo = str(id_reserva).strip()
        for idx, row in enumerate(data[1:], start=2):
            if len(row) > col_id:
                if str(row[col_id]).strip() == alvo:
                    sheet.delete_rows(idx)
                    st.cache_data.clear()
                    return True
        return False
    except Exception as e:
        st.error(f"Erro ao remover reserva: {e}")
        return False

st.title("Portal de Reservas - GDV")
st.caption(
    "Gerenciamento integrado de Chromebooks e Auditório "
    "para professores e colaboradores."
)

aba_chr, aba_aud, aba_painel, aba_canc = st.tabs([
    "💻 Reservar Chromebooks",
    "🎭 Reservar Auditório",
    "📋 Painel de Reservas",
    "❌ Cancelar Reserva"
])

with aba_chr:
    st.subheader("💻 Agendamento de Carrinho de Chromebooks")
    with st.form("form_chromebook", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            prof_c = st.text_area(
                "Nome do Professor / Solicitante*",
                height=68,
                key="c_prof"
            )
            email_c = st.text_area(
                "E-mail principal (@gdv.com.br ou @gdv.pro.br)*",
                height=68,
                key="c_email"
            )
            copia_c = st.text_area(
                "E-mail em copia (Opcional)*",
                height=68,
                key="c_copia"
            )
            unid_c = st.selectbox(
                "Unidade / Bloco*",
                ["Unidade Play", "Bloco 2", "Bloco 3", "Bloco 7"],
                key="c_unid"
            )
        with c2:
            data_c = st.date_input(
                "Data do uso*",
                value=date.today(),
                format="DD/MM/YYYY",
                key="c_data"
            )
            ch1, ch2 = st.columns(2)
            ini_c = ch1.time_input(
                "Horario Inicio*",
                value=time(7, 50),
                step=300,
                key="c_ini"
            )
            fim_c = ch2.time_input(
                "Horario Fim*",
                value=time(8, 40),
                step=300,
                key="c_fim"
            )
            qtd_c = st.number_input(
                "Quantidade de Chromebooks*",
                min_value=1,
                max_value=TOTAL_CHR,
                value=30,
                key="c_qtd"
            )
            obs_c = st.text_area(
                "Observacoes / Solicitacoes especiais",
                height=68,
                key="c_obs"
            )
        sub_c = st.form_submit_button(
            "Confirmar Reserva de Chromebooks"
        )

    if sub_c:
        p_clean = prof_c.strip()
        e_clean = email_c.strip().lower()
        cp_clean = copia_c.strip().lower()
        d_clean = data_c.strftime("%d/%m/%Y")
        i_str = ini_c.strftime("%H:%M")
        f_str = fim_c.strftime("%H:%M")

        if not p_clean or not e_clean:
            st.error("Preencha Nome e E-mail principal.")
        elif not validar_email_gdv(e_clean):
            st.error(
                "E-mail principal deve terminar com "
                "@gdv.com.br ou @gdv.pro.br."
            )
        elif cp_clean and not validar_email_gdv(cp_clean):
            st.error(
                "E-mail em copia deve terminar com "
                "@gdv.com.br ou @gdv.pro.br."
            )
        elif ini_c >= fim_c:
            st.error("Horario fim deve ser maior que inicio.")
        else:
            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            id_res = f"CHR-{ts}"
            obs_txt = (
                f"[CHROMEBOOK] {obs_c}"
                if obs_c else "[CHROMEBOOK]"
            )
            if cp_clean:
                obs_txt = f"{obs_txt} | Copia: {cp_clean}"
            dados = {
                "id": id_res,
                "professor": p_clean,
                "email": e_clean,
                "email_copia": cp_clean,
                "unidade": unid_c,
                "data": d_clean,
                "inicio": i_str,
                "fim": f_str,
                "quantidade": int(qtd_c),
                "obs": obs_txt
            }
            bloq, mot = verificar_conflito(dados, "CHROMEBOOK")
            if bloq:
                st.warning(f"⚠️ Reserva nao realizada: {mot}")
            else:
                with st.spinner("Registrando reserva..."):
                    if salvar_reserva(dados):
                        msg_ok = (
                            f"Reserva de {qtd_c} Chromebooks "
                            f"({id_res}) confirmada para "
                            f"{d_clean}, das {i_str} as {f_str} "
                            f"({unid_c})!"
                        )
                        st.session_state["msg_sucesso"] = msg_ok
                        st.rerun()

with aba_aud:
    st.subheader("🎭 Agendamento do Auditório GDV")
    with st.form("form_auditorio", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            prof_a = st.text_area(
                "Nome do Solicitante / Responsavel*",
                height=68,
                key="a_prof"
            )
            email_a = st.text_area(
                "E-mail principal (@gdv.com.br ou @gdv.pro.br)*",
                height=68,
                key="a_email"
            )
            copia_a = st.text_area(
                "E-mail em copia (Opcional)*",
                height=68,
                key="a_copia"
            )
            st.selectbox(
                "Local*",
                ["Auditório GDV"],
                disabled=True,
                key="a_unid"
            )
            data_a = st.date_input(
                "Data do Evento / Aula*",
                value=date.today(),
                format="DD/MM/YYYY",
                key="a_data"
            )
            ah1, ah2 = st.columns(2)
            ini_a = ah1.time_input(
                "Horario Inicio*",
                value=time(7, 50),
                step=300,
                key="a_ini"
            )
            fim_a = ah2.time_input(
                "Horario Fim*",
                value=time(9, 30),
                step=300,
                key="a_fim"
            )
        with c2:
            st.markdown("##### 🛠️ Equipamentos Necessarios")
            visuo = st.radio(
                "Apresentacao Visual:",
                [
                    "Nenhum",
                    "Projetor / DataShow",
                    "Lousa Digital / Interativa"
                ],
                key="a_visuo"
            )
            mics = st.slider(
                "Quantidade de Microfones sem fio:",
                0, 4, 1,
                key="a_mic"
            )
            som = st.selectbox(
                "Sistema de Som:",
                [
                    "Som Geral do Auditório",
                    "Caixa de Som Portátil com Bluetooth",
                    "Sem necessidade de Som"
                ],
                key="a_som"
            )
            obs_a = st.text_area(
                "Descricao do Evento / Observacoes",
                height=100,
                key="a_obs"
            )
        sub_a = st.form_submit_button(
            "Confirmar Reserva do Auditório"
        )

    if sub_a:
        p_clean = prof_a.strip()
        e_clean = email_a.strip().lower()
        cp_clean = copia_a.strip().lower()
        d_clean = data_a.strftime("%d/%m/%Y")
        i_str = ini_a.strftime("%H:%M")
        f_str = fim_a.strftime("%H:%M")

        if not p_clean or not e_clean:
            st.error("Preencha Nome e E-mail principal.")
        elif not validar_email_gdv(e_clean):
            st.error(
                "E-mail principal deve terminar com "
                "@gdv.com.br ou @gdv.pro.br."
            )
        elif cp_clean and not validar_email_gdv(cp_clean):
            st.error(
                "E-mail em copia deve terminar com "
                "@gdv.com.br ou @gdv.pro.br."
            )
        elif ini_a >= fim_a:
            st.error("Horario fim deve ser maior que inicio.")
        else:
            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            id_aud = f"AUD-{ts}"
            det = (
                f"[AUDITORIO] Visual: {visuo} | "
                f"Mics: {mics} | Som: {som}"
            )
            obs_txt = (
                f"{det} | Obs: {obs_a}" if obs_a else det
            )
            if cp_clean:
                obs_txt = f"{obs_txt} | Copia: {cp_clean}"
            dados_a = {
                "id": id_aud,
                "professor": p_clean,
                "email": e_clean,
                "email_copia": cp_clean,
                "unidade": "Auditório GDV",
                "data": d_clean,
                "inicio": i_str,
                "fim": f_str,
                "quantidade": 1,
                "obs": obs_txt
            }
            bloq, mot = verificar_conflito(dados_a, "AUDITORIO")
            if bloq:
                st.warning(f"⚠️ Reserva nao realizada: {mot}")
            else:
                with st.spinner("Registrando reserva..."):
                    if salvar_reserva(dados_a):
                        msg_ok = (
                            f"Reserva do Auditorio GDV ({id_aud}) "
                            f"confirmada para {d_clean}, "
                            f"das {i_str} as {f_str}!"
                        )
                        st.session_state["msg_sucesso"] = msg_ok
                        st.rerun()

with aba_painel:
    st.subheader("📋 Reservas Cadastradas no Sistema")
    if st.button("🔄 Atualizar Lista de Reservas"):
        st.cache_data.clear()
        st.rerun()
    df_res = carregar_dados_planilha()
    if df_res.empty:
        st.info("Nenhuma reserva registrada no momento.")
    else:
        desejadas = [
            "professor", "unidade", "data",
            "inicio", "fim", "quantidade", "obs"
        ]
        cols = [c for c in desejadas if c in df_res.columns]
        df_ex = df_res[cols].copy()
        if "data" in df_ex.columns:
            df_ex["data"] = df_ex["data"].apply(normalizar_data)
            df_ex["_ord"] = pd.to_datetime(
                df_ex["data"],
                format="%d/%m/%Y",
                errors="coerce"
            )
            df_ex = df_ex.sort_values(
                by="_ord", ascending=False
            ).drop(columns=["_ord"])
        st.dataframe(
            df_ex,
            use_container_width=True,
            hide_index=True,
            height=400
        )

with aba_canc:
    st.subheader("❌ Cancelar Agendamento")
    st.caption(
        "Digite o e-mail principal ou em copia para cancelar."
    )
    busca_raw = st.text_area(
        "Informe o E-mail (Principal ou Copia)*",
        height=68,
        key="busca_canc"
    )
    busca = busca_raw.strip().lower()
    if busca:
        df_t = carregar_dados_planilha()
        if not df_t.empty and "email" in df_t.columns:
            df_t["em"] = (
                df_t["email"].astype(str).str.strip().str.lower()
            )
            if "email_copia" in df_t.columns:
                df_t["cp"] = (
                    df_t["email_copia"]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                )
            else:
                df_t["cp"] = ""
            meus = df_t[
                (df_t["em"] == busca) | (df_t["cp"] == busca)
            ]
            if meus.empty:
                st.warning("Nenhum agendamento encontrado.")
            else:
                st.success(
                    f"Encontrado(s) {len(meus)} agendamento(s):"
                )
                opcoes = {}
                for _, r in meus.iterrows():
                    dt_f = normalizar_data(r.get("data", ""))
                    hi = r.get("inicio", "")
                    hf = r.get("fim", "")
                    un = r.get("unidade", "")
                    pr = r.get("professor", "")
                    rot = f"📅 {dt_f} | ⏰ {hi}-{hf} | 📍 {un} ({pr})"
                    opcoes[rot] = str(r.get("id", ""))
                sel = st.selectbox(
                    "Selecione a reserva para cancelar:",
                    options=list(opcoes.keys())
                )
                btn_c = st.button(
                    "🗑️ Confirmar Cancelamento",
                    type="primary"
                )
                if btn_c:
                    if remover_reserva_por_id(opcoes[sel]):
                        st.session_state["msg_sucesso"] = (
                            "Reserva cancelada com sucesso!"
                        )
                        st.rerun()