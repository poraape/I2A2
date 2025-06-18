import streamlit as st
import pandas as pd
import zipfile
import google.generativeai as genai
import io

# =============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E ESTILO
# =============================================================================

st.set_page_config(
    layout="centered",
    page_title="Data Insights Agent",
    page_icon="🍏"
)

# Estilo CSS para a estética "Apple-like" minimalista
# Injetamos CSS customizado para estilizar os componentes do Streamlit
def load_css():
    css = """
    <style>
        /* Fontes e fundo principal */
        html, body, [class*="st-"] {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
        }
        /* Estilo dos containers de chat */
        [data-testid="stChatMessage"] {
            border-radius: 18px;
            padding: 1em 1.2em;
            margin-bottom: 1em;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            border: 1px solid rgba(0,0,0,0.05);
        }
        /* Botões */
        .stButton>button {
            border-radius: 12px;
            border: 1px solid rgba(0, 0, 0, 0.05);
            box-shadow: 0 2px 6px rgba(0,0,0,0.04);
        }
        /* Input de texto */
        .stTextInput, .stTextArea {
            border-radius: 12px;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

load_css()

# =============================================================================
# 2. CONFIGURAÇÃO DO MODELO DE IA (GEMINI)
# =============================================================================

# Configuração da API Key de forma segura
import os
from dotenv import load_dotenv

# Lógica para carregar a API Key de forma adaptável
api_key = None

# Tenta carregar do Streamlit Secrets (para produção na nuvem)
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    st.toast("Chave da API carregada do Streamlit Secrets.")
# Se não encontrar, tenta carregar do arquivo .env (para desenvolvimento local/Codespaces)
except:
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        st.toast("Chave da API carregada do arquivo .env local.")

# Se nenhuma chave foi encontrada, exibe o erro e para
if not api_key:
    st.error("Chave da API do Google não encontrada. Configure-a nos Secrets do Streamlit Cloud ou em um arquivo .env local.")
    st.stop()

# Configura o modelo Gemini com a chave encontrada
try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception as e:
    st.error(f"Ocorreu um erro ao configurar o modelo Gemini: {e}")
    st.stop()

# =============================================================================
# 3. ARQUITETURA MULTI-AGENTE
# =============================================================================

# --- AGENTE 1: Onboarding e Análise Inicial ---
def agent_onboarding(df):
    """Analisa o dataframe e gera um resumo e perguntas estratégicas."""
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

# --- AGENTE 2: Gerador de Código Pandas ---
def agent_code_generator(query, df_head):
    """Gera código Pandas para responder a uma pergunta específica."""
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

# --- AGENTE 3: Sintetizador de Resposta ---
def agent_results_synthesizer(query, code_result):
    """Transforma um resultado bruto em uma resposta em linguagem natural."""
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

# =============================================================================
# 4. FUNÇÕES AUXILIARES
# =============================================================================

def load_csv_from_zip(zip_file):
    """Carrega o primeiro CSV encontrado em um arquivo zip em memória."""
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

# Inicialização do estado da sessão para reter dados entre interações
if "messages" not in st.session_state:
    st.session_state.messages = []
if "df" not in st.session_state:
    st.session_state.df = None

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.image("https://i.imgur.com/nJp2Vj2.png", width=80) # Logo genérico minimalista
    st.header("Data Insights Agent")
    st.markdown("Faça o upload do seu arquivo `.zip` contendo um `.csv` para começar a análise.")
    
    uploaded_file = st.file_uploader("Seu arquivo de dados", type="zip", label_visibility="collapsed")
    
    # Processamento do arquivo carregado
    if uploaded_file and st.session_state.df is None:
        with st.spinner("Processando seu arquivo..."):
            df = load_csv_from_zip(uploaded_file)
            if df is not None:
                st.session_state.df = df
                st.session_state.messages = [] # Limpa o chat anterior
                welcome_message = agent_onboarding(df)
                st.session_state.messages.append({"role": "assistant", "content": welcome_message})
                st.success("Arquivo processado! Pronto para suas perguntas.")
            else:
                st.error("Não foi possível encontrar um CSV no arquivo zip.")
    
    if st.session_state.df is not None:
        if st.button("Limpar e Carregar Novo Arquivo"):
            st.session_state.df = None
            st.session_state.messages = []
            st.rerun()

# --- ÁREA PRINCIPAL DO CHAT ---
st.title("🍏 Data Insights")
st.markdown("Seu parceiro de análise de dados, com a tecnologia Gemini.")

# Exibe mensagens do histórico
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Lógica principal de interação
if st.session_state.df is not None:
    # Captura a pergunta do usuário através do input de chat
    if prompt := st.chat_input("Faça uma pergunta sobre seus dados..."):
        # Adiciona a pergunta do usuário ao histórico e exibe
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Resposta do assistente
        with st.chat_message("assistant"):
            with st.spinner("🧠 Pensando..."):
                try:
                    # Passo 1: Gerar código
                    codigo_gerado = agent_code_generator(prompt, st.session_state.df.head())
                    
                    # Passo 2: Executar código de forma segura
                    namespace = {'df': st.session_state.df}
                    exec(codigo_gerado, namespace)
                    resultado_bruto = namespace['resultado']
                    
                    # Passo 3: Sintetizar a resposta final
                    resposta_final = agent_results_synthesizer(prompt, resultado_bruto)

                    # Exibe a resposta final e a adiciona ao histórico
                    st.markdown(resposta_final)
                    st.session_state.messages.append({"role": "assistant", "content": resposta_final})

                except Exception as e:
                    error_message = f"Desculpe, encontrei um erro ao processar seu pedido. O agente pode ter gerado um código inválido.\n\n**Detalhes Técnicos:**\n`{e}`"
                    st.error(error_message)
                    st.session_state.messages.append({"role": "assistant", "content": error_message})
else:
    st.info("Por favor, carregue um arquivo .zip na barra lateral para começar a análise.")