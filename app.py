import streamlit as st
import pandas as pd
import zipfile
import google.generativeai as genai
import io

# =============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E ESTILO
# =============================================================================

st.set_page_config(
    # <-- MUDANÇA: Layout "wide" funciona melhor com colunas
    layout="wide", 
    page_title="Data Insights",
    page_icon="🍏"
    # <-- MUDANÇA: initial_sidebar_state não é mais necessário
)

# Estilo CSS para a estética "Apple-like" minimalista
def load_css():
    css = """
    <style>
        html, body, [class*="st-"] {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
        }
        [data-testid="stChatMessage"] {
            border-radius: 18px;
            padding: 1em 1.2em;
            margin-bottom: 1em;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            border: 1px solid rgba(0,0,0,0.05);
        }
        .stButton>button {
            border-radius: 12px;
            border: 1px solid rgba(0, 0, 0, 0.05);
            box-shadow: 0 2px 6px rgba(0,0,0,0.04);
            width: 100%; /* Faz o botão ocupar a largura da coluna */
        }
        .stTextInput, .stTextArea, [data-testid="stFileUploader"] {
            border-radius: 12px;
        }
        /* Remove o padding extra da página principal */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            padding-left: 3rem;
            padding-right: 3rem;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

load_css()

# =============================================================================
# 2. CONFIGURAÇÃO DO MODELO DE IA (GEMINI)
# (Esta seção permanece a mesma)
# =============================================================================
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
except Exception:
    st.error("Chave da API do Google não configurada.")
    st.stop()

# =============================================================================
# 3. ARQUITETURA MULTI-AGENTE E FUNÇÕES AUXILIARES
# (Estas seções permanecem as mesmas)
# =============================================================================
def agent_onboarding(df):
    buffer = io.StringIO()
    df.info(buf=buffer)
    df_info = buffer.getvalue()
    prompt = f"""
    Você é um Analista de Dados Sênior. Sua tarefa é fazer o onboarding de um novo conjunto de dados.
    Com base na seguinte estrutura de dados (resultado de df.info()):
    ---
    {df_info}
    ---
    E nas primeiras 5 linhas:
    ---
    {df.head().to_markdown()}
    ---
    1.  Escreva um resumo conciso e perspicaz sobre o que este conjunto de dados parece representar.
    2.  Gere uma lista de 3 a 4 perguntas estratégicas e inteligentes que um executivo faria sobre esses dados para descobrir insights valiosos. Formate como uma lista de marcadores.
    """
    response = model.generate_content(prompt)
    return response.text

def agent_code_generator(query, df_head):
    prompt = f"""
    Você é um especialista em Python e Pandas. Sua tarefa é gerar código para responder a uma pergunta do usuário sobre um DataFrame.
    As primeiras 5 linhas do DataFrame `df` são:
    {df_head.to_markdown()}
    A pergunta do usuário é: "{query}"
    Gere APENAS o código Python necessário. O resultado final DEVE ser armazenado em uma variável chamada `resultado`.
    Não use print(). Não inclua explicações ou marcadores de código.
    """
    response = model.generate_content(prompt)
    return response.text.strip()

def agent_results_synthesizer(query, code_result):
    prompt = f"""
    Você é um assistente de IA especialista em comunicação de dados.
    A pergunta original do usuário foi: "{query}"
    O resultado da análise de dados foi:
    ---
    {code_result}
    ---
    Sintetize este resultado em uma resposta clara, concisa e amigável para o usuário.
    """
    response = model.generate_content(prompt)
    return response.text

def load_csv_from_zip(zip_file):
    try:
        with zipfile.ZipFile(zip_file, 'r') as z:
            csv_filename = next((name for name in z.namelist() if name.lower().endswith('.csv')), None)
            if csv_filename:
                with z.open(csv_filename) as f:
                    return pd.read_csv(f)
            return None
    except Exception:
        return None

# =============================================================================
# 5. LÓGICA DA INTERFACE E ESTADO DA SESSÃO
# =============================================================================

if "messages" not in st.session_state:
    st.session_state.messages = []
if "df" not in st.session_state:
    st.session_state.df = None

# <-- MUDANÇA: Definindo as colunas fixas do layout
# A coluna da esquerda terá 1/3 da largura e a da direita 2/3.
left_column, right_column = st.columns([1, 2], gap="large")

# --- PAINEL ESQUERDO FIXO ---
with left_column:
    st.title("📂 Arquivos")
    st.markdown("Carregue um arquivo `.zip` contendo um `.csv` para iniciar a análise.")
    
    uploaded_file = st.file_uploader(
        "Carregar arquivo de dados", 
        type="zip", 
        label_visibility="collapsed"
    )
    
    if uploaded_file and st.session_state.df is None:
        with st.spinner("Processando..."):
            df = load_csv_from_zip(uploaded_file)
            if df is not None:
                st.session_state.df = df
                st.session_state.messages = []
                welcome_message = agent_onboarding(df)
                st.session_state.messages.append({"role": "assistant", "content": welcome_message})
                st.success("Arquivo processado!")
                st.rerun() # Força o recarregamento para atualizar a interface do chat
            else:
                st.error("Nenhum CSV encontrado.")
    
    if st.session_state.df is not None:
        st.markdown("---")
        st.markdown("**Arquivo Carregado:**")
        st.dataframe(st.session_state.df.head(3)) # Mostra uma prévia dos dados
        if st.button("Analisar Novo Arquivo"):
            st.session_state.df = None
            st.session_state.messages = []
            st.rerun()

# --- ÁREA PRINCIPAL DO CHAT (DIREITA) ---
with right_column:
    st.title("🍏 Data Insights")
    st.markdown("Seu parceiro de análise de dados, com a tecnologia Gemini.")
    st.markdown("---")

    # Se nenhum arquivo foi carregado, mostra uma mensagem de boas-vindas
    if st.session_state.df is None:
        st.info("Aguardando o carregamento de um arquivo no painel à esquerda.")
    
    # Exibe o histórico de chat
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Lógica de interação do chat
    if st.session_state.df is not None:
        if prompt := st.chat_input("Faça uma pergunta sobre seus dados..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Analisando..."):
                    try:
                        codigo_gerado = agent_code_generator(prompt, st.session_state.df.head())
                        namespace = {'df': st.session_state.df}
                        exec(codigo_gerado, namespace)
                        resultado_bruto = namespace['resultado']
                        resposta_final = agent_results_synthesizer(prompt, resultado_bruto)
                        st.markdown(resposta_final)
                        st.session_state.messages.append({"role": "assistant", "content": resposta_final})
                    except Exception as e:
                        error_message = f"Desculpe, encontrei um erro. Tente reformular sua pergunta.\n\n**Detalhe técnico:** `{e}`"
                        st.error(error_message)
                        st.session_state.messages.append({"role": "assistant", "content": error_message})
