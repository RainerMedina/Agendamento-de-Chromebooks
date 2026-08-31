import streamlit as st
import datetime

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Agendamento de Chromebooks - GDV",
    page_icon="💻",
    layout="centered"
)

st.title("💻 Agendamento de Chromebooks - GDV")
st.markdown("Reserve os blocos de Chromebooks para suas aulas e consulte as reservas realizadas.")

# ==========================================
# 2. BANCO DE DADOS EM MEMÓRIA (COMPARTILHADO)
# ==========================================
# Inicializa a lista de reservas no estado global do Streamlit
if "reservas" not in st.session_state:
    st.session_state.reservas = []

# ==========================================
# 3. INTERFACE EM ABAS
# ==========================================
tab_nova, tab_consultar = st.tabs(["➕ Nova Reserva", "📅 Consultar Reservas"])

# ------------------------------------------
# ABA 1: NOVA RESERVA
# ------------------------------------------
with tab_nova:
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
            # Salva o agendamento no sistema
            nova_reserva = {
                "professor": nome_professor,
                "email": email_professor,
                "unidade": unidade,
                "data": data_reserva,
                "inicio": horario_inicio.strftime("%H:%M"),
                "fim": horario_fim.strftime("%H:%M"),
                "quantidade": quantidade,
                "obs": observacoes
            }
            
            st.session_state.reservas.append(nova_reserva)
            st.success("✅ Agendamento realizado com sucesso! Todos já podem visualizar na aba 'Consultar Reservas'.")

# ------------------------------------------
# ABA 2: CONSULTAR RESERVAS (VISÍVEL PARA TODOS)
# ------------------------------------------
with tab_consultar:
    st.header("Agendamentos Realizados")
    
    if not st.session_state.reservas:
        st.info("Nenhum agendamento realizado até o momento.")
    else:
        # Filtro de data
        data_filtro = st.date_input("Filtrar por data", value=datetime.date.today())
        
        # Encontra agendamentos na data selecionada
        reservas_encontradas = [r for r in st.session_state.reservas if r["data"] == data_filtro]
        
        if not reservas_encontradas:
            st.warning(f"Nenhum agendamento encontrado para a data {data_filtro.strftime('%d/%m/%Y')}.")
        else:
            st.write(f"### Reservas para {data_filtro.strftime('%d/%m/%Y')}:")
            for idx, r in enumerate(reservas_encontradas, start=1):
                with st.expander(f"📍 {r['unidade']} | {r['inicio']} às {r['fim']} - Prof. {r['professor']}"):
                    st.write(f"**Professor(a):** {r['professor']} ({r['email']})")
                    st.write(f"**Bloco / Local:** {r['unidade']}")
                    st.write(f"**Horário:** {r['inicio']} às {r['fim']}")
                    st.write(f"**Quantidade de Chromebooks:** {r['quantidade']}")
                    if r['obs']:
                        st.write(f"**Observações:** {r['obs']}")
