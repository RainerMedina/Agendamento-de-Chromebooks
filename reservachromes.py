import streamlit as st
import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==========================================
# 1. CONFIGURAÇÕES DA PÁGINA STREAMLIT
# ==========================================
st.set_page_config(
    page_title="Agendamento de Chromebooks - GDV",
    page_icon="💻",
    layout="centered"
)

st.title("💻 Agendamento de Chromebooks - GDV")
st.markdown("Reserve os blocos de Chromebooks para suas aulas de forma rápida e integrada com a Infraestrutura.")

# ==========================================
# 2. CONEXÃO COM GOOGLE CALENDAR (SECRETS)
# ==========================================
SCOPES = ['https://www.googleapis.com/auth/calendar']

@st.cache_resource
def get_calendar_service():
    """Autentica na Google Calendar API usando as credenciais do Streamlit Secrets."""
    try:
        # Lê o dicionário gcp_service_account configurado no Secrets do Streamlit Cloud
        service_account_info = dict(st.secrets["gcp_service_account"])
        
        # Garante que as quebras de linha da chave privada sejam interpretadas corretamente
        if "private_key" in service_account_info:
            service_account_info["private_key"] = service_account_info["private_key"].replace('\\n', '\n')
            
        creds = Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES
        )
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        st.error(f"Erro ao conectar com a API do Google Calendar: {e}")
        return None

# ID da Agenda do Google (Pode ser o e-mail do calendário compartilhado ou 'primary')
CALENDAR_ID = st.secrets.get("CALENDAR_ID", "primary")

# E-mail da equipe de infraestrutura
EMAIL_INFRA = "grupo_infraestrutura@gdv.com.br"

# ==========================================
# 3. FUNÇÃO DE ENVIO DE E-MAIL
# ==========================================
def enviar_email_confirmacao(email_professor, nome_professor, unidade, data, horario_inicio, horario_fim, quantidade):
    """Envia e-mail de notificação para a Infraestrutura e para o Professor."""
    try:
        # Verifica se as configurações de SMTP estão nos Secrets
        if "smtp" not in st.secrets:
            return False, "Configurações de e-mail (SMTP) não encontradas nos Secrets."

        smtp_server = st.secrets["smtp"]["server"]
        smtp_port = st.secrets["smtp"]["port"]
        smtp_user = st.secrets["smtp"]["user"]
        smtp_password = st.secrets["smtp"]["password"]

        assunto = f"[Reserva Chromebook] {unidade} - {data.strftime('%d/%m/%Y')} ({horario_inicio} às {horario_fim})"
        
        corpo = f"""
        Olá,

        Uma nova reserva de Chromebooks foi realizada!

        📌 Detalhes da Reserva:
        ------------------------------------------
        • Professor(a): {nome_professor} ({email_professor})
        • Local / Bloco: {unidade}
        • Data: {data.strftime('%d/%m/%Y')}
        • Horário: {horario_inicio} às {horario_fim}
        • Quantidade de Unidades: {quantidade}
        ------------------------------------------

        Este é um e-mail automático enviado pelo Sistema de Agendamento GDV.
        """

        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = f"{email_professor}, {EMAIL_INFRA}"
        msg['Subject'] = assunto
        msg.attach(MIMEText(corpo, 'plain'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, [email_professor, EMAIL_INFRA], msg.as_string())
        server.quit()
        return True, "E-mail de confirmação enviado com sucesso!"
    except Exception as e:
        return False, f"Falha ao enviar e-mail: {str(e)}"

# ==========================================
# 4. INTERFACE COM ABAS (STREAMLIT)
# ==========================================
tab_nova_reserva, tab_consultar = st.tabs(["➕ Nova Reserva", "📅 Consultar Reservas"])

# ------------------------------------------
# ABA 1: NOVA RESERVA
# ------------------------------------------
with tab_nova_reserva:
    st.header("Formulário de Reserva")
    
    with st.form("form_reserva", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nome_professor = st.text_input("Nome do Professor(a)*")
        with col2:
            email_professor = st.text_input("E-mail do Professor(a)*")

        unidade = st.selectbox(
            "Selecione a Unidade / Bloco*",
            ["Bloco 2", "Bloco 3", "Bloco 7", "Unidade Play"]
        )

        col3, col4, col5 = st.columns(3)
        with col3:
            data_reserva = st.date_input("Data da Reserva*", min_value=datetime.date.today())
        with col4:
            horario_inicio = st.time_input("Horário de Início*", value=datetime.time(8, 0))
        with col5:
            horario_fim = st.time_input("Horário de Término*", value=datetime.time(8, 50))

        quantidade = st.number_input("Quantidade de Chromebooks*", min_value=1, max_value=50, value=30)
        observacoes = st.text_area("Observações (Opcional)")

        btn_reservar = st.form_submit_button("Confirmar Agendamento", use_container_width=True)

    if btn_reservar:
        if not nome_professor or not email_professor:
            st.error("Por favor, preencha o Nome e o E-mail.")
        elif horario_fim <= horario_inicio:
            st.error("O horário de término deve ser posterior ao horário de início.")
        else:
            service = get_calendar_service()
            if service:
                # Monta as datas e horários no formato ISO (RFC3339) para o Google Calendar
                start_datetime = f"{data_reserva.isoformat()}T{horario_inicio.isoformat()}-03:00"
                end_datetime = f"{data_reserva.isoformat()}T{horario_fim.isoformat()}-03:00"

                event = {
                    'summary': f"Chromebooks: {unidade} - {nome_professor}",
                    'location': unidade,
                    'description': f"Professor: {nome_professor}\nE-mail: {email_professor}\nQuantidade: {quantidade}\nObs: {observacoes}",
                    'start': {'dateTime': start_datetime, 'timeZone': 'America/Sao_Paulo'},
                    'end': {'dateTime': end_datetime, 'timeZone': 'America/Sao_Paulo'},
                    'attendees': [
                        {'email': email_professor},
                        {'email': EMAIL_INFRA}
                    ],
                }

                try:
                    # Inserção do evento na agenda do Google
                    created_event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
                    st.success(f"✅ Reserva realizada com sucesso no Google Calendar!")
                    st.info(f"📍 **Evento:** {created_event.get('htmlLink')}")

                    # Tentativa de envio do e-mail de notificação
                    email_ok, email_msg = enviar_email_confirmacao(
                        email_professor, nome_professor, unidade, data_reserva, horario_inicio, horario_fim, quantidade
                    )
                    if email_ok:
                        st.success("✉️ Notificação enviada por e-mail para você e para a equipe de infraestrutura!")
                    else:
                        st.warning(f"⚠️ Evento criado na agenda, mas o e-mail não pôde ser enviado. ({email_msg})")

                except Exception as e:
                    st.error(f"Erro ao criar agendamento no Google Calendar: {e}")

# ------------------------------------------
# ABA 2: CONSULTAR RESERVAS
# ------------------------------------------
with tab_consultar:
    st.header("Agendamentos Confirmados")
    data_consulta = st.date_input("Filtrar por data", value=datetime.date.today())

    if st.button("Buscar Agendamentos"):
        service = get_calendar_service()
        if service:
            time_min = f"{data_consulta.isoformat()}T00:00:00Z"
            time_max = f"{data_consulta.isoformat()}T23:59:59Z"

            try:
                events_result = service.events().list(
                    calendarId=CALENDAR_ID,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()

                events = events_result.get('items', [])

                if not events:
                    st.info("Nenhuma reserva encontrada para esta data.")
                else:
                    for event in events:
                        start = event['start'].get('dateTime', event['start'].get('date'))
                        horario = start.split('T')[1][:5] if 'T' in start else "Dia todo"
                        
                        st.write(f"📌 **{event.get('summary')}**")
                        st.write(f"⏱️ Horário: {horario} | 📍 Local: {event.get('location', 'Não informado')}")
                        st.divider()
            except Exception as e:
                st.error(f"Erro ao buscar agendamentos: {e}")
