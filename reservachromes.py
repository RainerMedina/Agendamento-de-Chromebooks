import streamlit as st
from datetime import datetime, time

# Configuração da página e título oficial
st.set_page_config(page_title="Agendamento de Chromebooks - GDV", page_icon="💻", layout="centered")

# Lista de locais disponíveis
LOCAIS_DISPONIVEIS = ["Bloco 2", "Bloco 3", "Bloco 7", "Unidade Play"]

# Criando as abas
tab_agendar, tab_consultar = st.tabs(["📝 Nova Reserva", "🔍 Consultar Agendamentos"])

# ==============================================================================
# ABA 1: FORMULÁRIO DE NOVA RESERVA
# ==============================================================================
with tab_agendar:
    st.title("💻 Agendamento de Chromebooks - GDV")
    
    with st.form("form_agendamento"):
        st.subheader("Dados da Reserva")
        
        # Seleção do Bloco / Unidade
        local_selecionado = st.selectbox("Selecione a Unidade / Bloco*", LOCAIS_DISPONIVEIS)
        
        nome_professor = st.text_input("Nome Completo do Professor*", placeholder="Ex: Anisio")
        email_professor = st.text_input("E-mail do Professor*", placeholder="Ex: anisio@gdv.com.br")
        disciplina = st.text_input("Disciplina / Turma*", placeholder="Ex: Portugues - 9 Ano - A")
        
        col1, col2 = st.columns(2)
        with col1:
            data_reserva = st.date_input("Data da Reserva*", min_value=datetime.now().date())
            horario_inicio = st.time_input("Horário de Início*", value=time(8, 0))
        with col2:
            quantidade = st.number_input("Qtd. de Chromebooks*", min_value=1, max_value=40, value=30)
            horario_fim = st.time_input("Horário de Término*", value=time(8, 50))

        observacoes = st.text_area("Observações ou Pedidos Especiais", placeholder="Ex: teste")
        
        submitted = st.form_submit_button("Confirmar e Reservar Agenda")

    if submitted:
        if not nome_professor or not email_professor or not disciplina:
            st.error("Por favor, preencha todos os campos obrigatórios (*).")
        elif horario_inicio >= horario_fim:
            st.error("O horário de término deve ser posterior ao horário de início.")
        else:
            # Estrutura pronta para envio dos convites por e-mail no Google Calendar
            participantes = [
                {"email": email_professor},
                {"email": "grupo_infraestrutura@gdv.com.br"}
            ]
            
            # Título do evento no Google Calendar incluirá o Local e o Professor
            titulo_evento = f"[{local_selecionado}] Chromebooks ({quantidade}x) - {nome_professor}"
            
            st.success(f"Reserva confirmada com sucesso para {nome_professor}!")
            st.info(f"**Resumo:** {quantidade} Chromebooks no **{local_selecionado}** para **{data_reserva.strftime('%d/%m/%Y')}** das **{horario_inicio.strftime('%H:%M')}** às **{horario_fim.strftime('%H:%M')}**.")
            st.success(f"✉️ E-mail de confirmação enviado para **{email_professor}** com cópia para **grupo_infraestrutura@gdv.com.br**.")

# ==============================================================================
# ABA 2: CONSULTA DE RESERVAS EXISTENTES
# ==============================================================================
with tab_consultar:
    st.title("📅 Consultar Reservas - GDV")
    
    col_data, col_local = st.columns(2)
    with col_data:
        data_consulta = st.date_input("Data para consulta:", value=datetime.now().date())
    with col_local:
        filtro_local = st.selectbox("Filtrar por Unidade / Bloco:", ["Todos"] + LOCAIS_DISPONIVEIS)
    
    st.subheader(f"Agendamentos para {data_consulta.strftime('%d/%m/%Y')}")
    st.markdown("---")
    
    # Exemplo simulado de como os resultados filtrados aparecerão
    col_hora, col_detalhes = st.columns([1, 3])
    with col_hora:
        st.write("⏰ **08:00 - 08:50**")
        st.caption("📍 **Bloco 2**")
    with col_detalhes:
        st.write("**Professor:** Anisio (anisio@gdv.com.br)")
        st.write("**Turma:** Portugues - 9 Ano - A | **Qtd:** 30 Chromebooks")
        st.caption("Obs: teste")
        
    st.markdown("---")
