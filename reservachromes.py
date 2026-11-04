# =========================================================
# ABA 3: PAINEL DE CONSULTA DE RESERVAS
# =========================================================
with aba_minhas_reservas:
    st.subheader("📋 Reservas Cadastradas no Sistema")
    
    if st.button("🔄 Atualizar Lista de Reservas"):
        # Limpa o cache para carregar dados novos instantaneamente ao clicar
        st.cache_data.clear()
        st.rerun()
        
    try:
        # Usa ttl=5 segundos de cache para não travar a conexão ao abrir a página
        df_reservas = conn.read(ttl=5)
        
        if df_reservas.empty:
            st.info("Nenhuma reserva registrada no momento.")
        else:
            colunas_visiveis = ["professor", "unidade", "data", "inicio", "fim", "quantidade", "obs"]
            
            # Filtra apenas as colunas que existem na planilha
            cols_existentes = [c for c in colunas_visiveis if c in df_reservas.columns]
            df_exibicao = df_reservas[cols_existentes].copy()
            
            # Ordena da data mais recente para a mais antiga
            if "data" in df_exibicao.columns:
                df_exibicao = df_exibicao.sort_values(by="data", ascending=False)
            
            st.dataframe(
                df_exibicao,
                use_container_width=True,
                hide_index=True,
                height=400 # Limita a altura da tabela para o navegador carregar rápido
            )
    except Exception as e:
        st.warning("Carregando agendamentos... Se demorar, clique em 'Atualizar Lista'.")
