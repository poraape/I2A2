import streamlit as st
import pandas as pd
import zipfile
import google.generativeai as genai
import io
import matplotlib.pyplot as plt
import seaborn as sns
import json

# =============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E ESTILO
# =============================================================================

st.set_page_config(
    layout="centered",
    page_title="Data Insights Pro",
    page_icon="🍏"
)

# Estilo CSS para a estética "Apple-like" minimalista
def load_css():
    st.markdown("""
    <style>
        html, body, [class*="st-"] {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
        }
        [data-testid="stChatMessage"] {
            border-radius: 18px; padding: 1em 1.2em; margin-bottom: 1em;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid rgba(0,0,0,0.05);
        }
        .stButton>button { border-radius: 12px; }
        [data-testid="stFileUploader"] {
            border: 2px dashed #e0e0e0; background-color: #fafafa; padding: 2rem; border-radius: 12px;
        }
        .block-container { max-width: 800px; padding-top: 3rem; padding-bottom: 3rem; }
    </style>
    """, unsafe_allow_html=True)

load_css()

# =============================================================================
# 2. CONFIGURAÇÃO DO MODELO DE IA (GEMINI)
# (Esta seção permanece a mesma)
# =============================================================================
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception:
    st.error("Chave da API do Google não configurada.")
    st.stop()

# =============================================================================
# 3. ARQUITETURA MULTI-AGENTE E FUNÇÕES AUXILIARES
# (As funções dos agentes e auxiliares permanecem as mesmas da versão anterior)
# =============================================================================
def agent_onboarding(dataframes_dict):
    summary = "### 🗂️ Catálogo de Dados Carregado\n\n"
    summary += f"Detectei e carreguei com sucesso **{len(dataframes_dict)}** arquivo(s) CSV:\n"
    all_dfs = []
    for name, df in dataframes_dict.items():
        summary += f"- **{name}**: `{len(df)}` linhas, `{len(df.columns)}` colunas.\n"
        all_dfs.append(df)
    combined_df = pd.concat(all_dfs, ignore_index=True)
    summary += f"\n**Visão Agregada:** Ao todo, você tem um conjunto de dados com **{len(combined_df)}** linhas para análise combinada.\n"
    prompt = f"""
    Você é um Analista de Dados Estratégico. Sua missão é fazer o onboarding de um conjunto de múltiplos arquivos de dados.
    Resumo do Catálogo: {summary}
    Amostra Combinada: {combined_df.head().to_markdown()}
    Com base nisso, realize as seguintes tarefas:
    1.  **Resumo Executivo:** Escreva um parágrafo sobre o potencial analítico deste conjunto de dados.
    2.  **Perguntas Estratégicas Sugeridas:** Formule uma lista de 4 perguntas inteligentes (individual, combinada, visualização).
    """
    response = model.generate_content(prompt)
    return summary + "\n" + response.text

def agent_router(query, chat_history):
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
    prompt = f"""
    Você é um agente roteador. Decida a ferramenta (`gerar_codigo_pandas` ou `gerar_codigo_visualizacao`) para a pergunta.
    Histórico: {history_str}
    Pergunta: "{query}"
    Responda APENAS com JSON: {{"ferramenta": "...", "pergunta_refinada": "..."}}
    """
    response = model.generate_content(prompt)
    try:
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(cleaned_response)
    except (json.JSONDecodeError, AttributeError):
        return {"ferramenta": "gerar_codigo_pandas", "pergunta_refinada": query}

def tool_code_generator(query, df_head):
    prompt = f"""
    Especialista Pandas: Gere código Python para a pergunta. DataFrame `df`. Resultado em `resultado`.
    Amostra: {df_head.to_markdown()}
    Pergunta: "{query}"
    """
    response = model.generate_content(prompt)
    raw_code = response.text
    return raw_code.replace("```python", "").replace("```", "").strip()

def tool_visualization_generator(query, df_head):
    prompt = f"""
    Especialista em Visualização (Matplotlib/Seaborn): Gere código Python para a pergunta. DataFrame `df`.
    Amostra: {df_head.to_markdown()}
    Pergunta: "{query}"
    Instruções: Use `fig, ax = plt.subplots()`. Sem `plt.show()`. Resultado em `resultado = fig`.
    """
    response = model.generate_content(prompt)
    raw_code = response.text
    return raw_code.replace("```python", "").replace("```", "").strip()

def agent_results_synthesizer(query, code_result):
    return f"**Análise para a pergunta:** '{query}'\n\n**Resultado:**\n\n```\n{str(code_result)}\n```"

def load_dataframes_from_zip(zip_file):
    dataframes = {}
    try:
        with zipfile.ZipFile(zip_file, 'r') as z:
            for filename in z.namelist():
                if filename.lower().endswith('.csv'):
                    with z.open(filename) as f:
                        dataframes[filename] = pd.read_csv(f, on_bad_lines='skip')
        return dataframes if dataframes else None
    except Exception:
        return None

# =============================================================================
# 5. LÓGICA DA INTERFACE E ESTADO DA SESSÃO (REESTRUTURADA)
# =============================================================================

# Inicialização do estado da sessão
if "messages" not in st.session_state:
    st.session_state.messages = []
if "dataframes" not in st.session_state:
    st.session_state.dataframes = None
if "active_scope" not in st.session_state:
    st.session_state.active_scope = "Nenhum"

# --- TÍTULO PRINCIPAL ---
st.title("🍏 Data Insights Pro")
# <-- MUDANÇA: Nova frase de efeito
st.markdown("##### Um universo de dados em um único lugar. Pergunte, explore, descubra.")
st.markdown("---")

# --- LÓGICA DE LAYOUT CONDICIONAL ---

# Se nenhum arquivo foi carregado, mostra a interface de UPLOAD.
if st.session_state.dataframes is None:
    st.markdown("###### Comece sua jornada de análise.")
    st.info("Para começar, carregue um arquivo `.zip` contendo um ou mais arquivos `.csv`.")
    
    uploaded_file = st.file_uploader(
        "Arraste seu catálogo de dados aqui", 
        type="zip", 
        label_visibility="collapsed"
    )
    
    if uploaded_file:
        with st.spinner("Catalogando e analisando seus arquivos..."):
            dfs = load_dataframes_from_zip(uploaded_file)
            if dfs:
                st.session_state.dataframes = dfs
                st.session_state.messages = []
                welcome_message = agent_onboarding(dfs)
                st.session_state.messages.append({"role": "assistant", "content": welcome_message})
                st.session_state.active_scope = "Analisar Todos em Conjunto" # Define um padrão
                st.rerun()
            else:
                st.error("Nenhum arquivo .csv encontrado no .zip.")

# Se arquivos JÁ foram carregados, mostra a interface de CHAT.
else:
    # <-- MUDANÇA: Seletor de escopo integrado à interface de chat
    scope_options = ["Analisar Todos em Conjunto"] + list(st.session_state.dataframes.keys())
    st.session_state.active_scope = st.selectbox(
        "**Escopo da Análise:**",
        options=scope_options,
        index=scope_options.index(st.session_state.active_scope)
    )
    st.markdown("---")

    # Exibe o histórico de mensagens
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if isinstance(message["content"], str):
                st.markdown(message["content"])
            else:
                st.pyplot(message["content"])

    # Captura a nova pergunta do usuário
    if prompt := st.chat_input(f"Pergunte sobre '{st.session_state.active_scope}'..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Processa a pergunta com os agentes
        with st.chat_message("assistant"):
            with st.spinner("Analisando..."):
                try:
                    # Prepara o DataFrame ativo com base no escopo
                    if st.session_state.active_scope == "Analisar Todos em Conjunto":
                        active_df = pd.concat(st.session_state.dataframes.values(), ignore_index=True)
                    else:
                        active_df = st.session_state.dataframes[st.session_state.active_scope]
                    
                    router_decision = agent_router(prompt, st.session_state.messages)
                    ferramenta = router_decision.get("ferramenta")
                    pergunta_refinada = router_decision.get("pergunta_refinada", prompt)
                    st.write(f"🤖 *Usando a ferramenta `{ferramenta}`...*")
                    
                    codigo_gerado = ""
                    if ferramenta == "gerar_codigo_visualizacao":
                        codigo_gerado = tool_visualization_generator(pergunta_refinada, active_df.head())
                    else:
                        codigo_gerado = tool_code_generator(pergunta_refinada, active_df.head())
                    
                    namespace = {'df': active_df, 'plt': plt, 'sns': sns, 'pd': pd, 'io': io}
                    exec(codigo_gerado, namespace)
                    resultado_bruto = namespace.get('resultado')

                    if isinstance(resultado_bruto, plt.Figure):
                        st.pyplot(resultado_bruto)
                        st.session_state.messages.append({"role": "assistant", "content": resultado_bruto})
                    else:
                        resposta_final = agent_results_synthesizer(pergunta_refinada, resultado_bruto)
                        st.markdown(resposta_final)
                        st.session_state.messages.append({"role": "assistant", "content": resposta_final})

                except Exception as e:
                    error_message = f"Desculpe, encontrei um erro. Tente reformular sua pergunta.\n\n**Detalhe técnico:** `{e}`"
                    st.error(error_message)
                    st.session_state.messages.append({"role": "assistant", "content": error_message})
    
    # Adiciona um botão para permitir que o usuário comece de novo
    if st.button("Analisar Novo Catálogo de Dados"):
        st.session_state.dataframes = None
        st.session_state.messages = []
        st.session_state.active_scope = "Nenhum"
        st.rerun()
