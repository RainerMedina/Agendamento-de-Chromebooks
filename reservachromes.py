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
            'background-color: transparent !important;'
            'padding-top: 7.5rem;'
            'max-width: 1100px;'
            '}'
            '[data-testid="stForm"] {'
            'background-color: rgba(255, 255, 255, 0.25);'
            'backdrop-filter: blur(6px);'
            'border: 1px solid rgba(255, 255, 255, 0.5);'
            'border-radius: 14px;'
            'padding: 1.5rem;'
            '}'
            '[data-testid="stDataFrame"] {'
            'background-color: rgba(255, 255, 255, 0.90);'
            'border-radius: 12px;'
            'padding: 0.5rem;'
            '}'
            'label, p, h1, h2, h3, .stMarkdown {'
            'text-shadow: 0px 1px 3px rgba(255, 255, 255, 0.9);'
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