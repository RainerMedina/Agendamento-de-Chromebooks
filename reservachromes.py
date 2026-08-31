import streamlit as st
import datetime
import pandas as pd
import os

# Arquivo para gravar os agendamentos no servidor
ARQUIVO_RESERVAS = "reservas_chromebooks.csv"

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
# 2. FUNÇÕES DE BANCO DE DADOS (CSV)
# ==========================================
def carregar_reservas():
    if os.path.exists(ARQUIVO_RESERVAS):
        try:
            df = pd.read_csv(ARQUIVO_RESERVAS, dtype=str)
            return df
        except Exception:
            return pd.DataFrame(columns=["id", "professor", "email", "unidade", "data", "inicio", "fim", "quantidade", "obs"])
    else:
        return pd.DataFrame(columns=["id", "professor", "email", "unidade", "data", "inicio", "fim", "quantidade", "obs"])

def salvar_reserva(nova_reserva):
    df = carregar_reservas()
    novo_df = pd.DataFrame([nova_reserva])
    df = pd.concat([df, novo_df], ignore_index=True)
    df.to_csv(ARQUIVO_RESERVAS, index=False)

def cancelar_reserva(id_reserva):
    df = carregar_reservas()
    if not df.empty and "id" in df.columns:
        df = df[df["id"] != str(id_reserva)]
        df.to_csv(ARQUIVO_RESERVAS, index=False)

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
            id_unico = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
            
            nova_reserva = {
                "id": id_unico,
                "professor": nome_professor,
                "email": email_professor.strip().lower(),
                "unidade": unidade,
                "data": str(data_reserva),
                "inicio": horario_inicio.strftime("%H:%M"),
                "fim": horario_fim.strftime("%H:%M"),
                "quantidade": str(quantidade),
                "obs": observacoes if observacoes else ""
            }
            salvar_reserva(nova_reserva)
            st.success("✅ Agendamento realizado com sucesso! Vá para a aba 'Consultar Reservas' para visualizar.")

# ------------------------------------------
# ABA 2: CONSULTAR E CANCELAR RESERVAS
# ------------------------------------------
with tab_consultar:
    st.header("Agendamentos Realizados")
    
    df_reservas = carregar_reservas()
    
    if df_reservas.empty:
        st.info("Nenhum agendamento realizado até o momento.")
    else:
        ver_todas = st.checkbox("Mostrar todas as datas", value=False)
        
        if not ver_todas:
            data_filtro = st.date_input("Filtrar por data", value=datetime.date.today())
            data_filtro_str = str(data_filtro)
            reservas_filtradas = df_reservas[df_reservas["data"] == data_filtro_str]
        else:
            reservas_filtradas = df_reservas

        if reservas_filtradas.empty:
            st.warning("Nenhum agendamento encontrado para a data selecionada.")
        else:
            st.write(f"**Total de agendamentos encontrados:** {len(reservas_filtradas)}")
            
            for idx, r in reservas_filtradas.iterrows():
                data_formatada = r['data']
                try:
                    data_obj = datetime.datetime.strptime(r['data'], "%Y-%m-%d")
                    data_formatada = data_obj.strftime("%d/%m/%Y")
                except Exception:
                    pass

                titulo_card = f"📍 {r['unidade']} | {data_formatada} ({r['inicio']} às {r['fim']}) - Prof. {r['professor']}"
                
                with st.expander(titulo_card):
                    st.write(f"**Professor(a):** {r['professor']}")
                    st.write(f"**Bloco / Local:** {r['unidade']}")
                    st.write(f"**Data:** {data_formatada}")
                    st.write(f"**Horário:** {r['inicio']} às {r['fim']}")
                    st.write(f"**Quantidade de Chromebooks:** {r['quantidade']}")
                    if pd.notna(r['obs']) and str(r['obs']).strip():
                        st.write(f"**Observações:** {r['obs']}")
                    
                    st.divider()
                    st.subheader("🔒 Cancelar Agendamento")
                    
                    reserva_id = r.get("id", str(idx))
                    email_dono = str(r.get("email", "")).strip().lower()
                    
                    # Campo para validação do e-mail do autor
                    email_confirmacao = st.text_input(
                        "Digite seu e-mail cadastrado para autorizar o cancelamento:",
                        key=f"input_email_{reserva_id}"
                    )
                    
                    if st.button("❌ Confirmar Cancelamento", key=f"btn_del_{reserva_id}"):
                        if not email_confirmacao:
                            st.error("Digite o e-mail cadastrado na reserva para poder cancelar.")
                        elif email_confirmacao.strip().lower() != email_dono:
                            st.error("E-mail incorreto! Apenas a pessoa que criou esta reserva pode cancelá-la.")
                        else:
                            cancelar_reserva(reserva_id)
                            st.success("Reserva cancelada com sucesso!")
                            st.rerun()
