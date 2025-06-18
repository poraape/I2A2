import streamlit as st
import pandas as pd
import zipfile
import google.generativeai as genai
import io
import matplotlib.pyplot as plt
import seaborn as sns
import json
from duckduckgo_search import DDGS

# =============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E ESTILO
# =============================================================================

st.set_page_config(
    layout="centered",
    page_title="Data Insights Pro", # Título mais curto e elegante para a aba do navegador
    page_icon="🍏"
)

# Estilo CSS aprimorado para a estética "Apple-like"
def load_css():
    st.markdown("""
    <style>
        /* Reset e Fontes */
        html, body, [class*="st-"] {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            font-weight: 400;
        }
        
        /* Títulos */
        h1 {
            font-weight: 600;
            letter-spacing: -0.03em;
        }
        
        /* Container Principal */
        .block-container {
            max-width: 720px; /* Largura ideal para leitura */
            padding-top: 3rem;
            padding-bottom: 3rem;
        }
        
        /* Mensagens de Chat */
        [data-testid="stChatMessage"] {
            border-radius: 20px;
            padding: 1rem 1.25rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            border: none;
        }
        
        /* Botões */
        .stButton>button {
            border-radius: 10px;
            font-weight: 500;
        }
        
        /* Caixa de Upload de Arquivo */
        [data-testid="stFileUploader"] {
            border: 1.5px dashed #d0d0d5;
            background-color: #f8f8fa;
            border-radius: 12px;
            padding: 2rem;
        }
        
        /* Caixa de Informação (st.info) */
        [data-testid="stAlert"] {
            border-radius: 12px;
            border: none;
            background-color: #f0f0f5;
        }
    </style>
    """, unsafe_allow_html=True)

load_css()

# =============================================================================
# 2. CONFIGURAÇÃO DO MODELO DE IA (GEMINI)
# =============================================================================
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
except Exception:
    st.error("Chave da API do Google não configurada.")
    st.stop()

# =============================================================================
# 3. DEFINIÇÃO DAS FERRAMENTAS (TOOLS)
# =============================================================================
# Cada função é uma ferramenta que o agente pode escolher usar.
# As docstrings são CRUCIAIS, pois o LLM as usa para decidir qual ferramenta chamar.

def python_code_interpreter(code: str, scope: str):
    """
    Executa código Python (Pandas, Matplotlib) em um escopo de dados específico.
    Use esta ferramenta para qualquer tipo de cálculo, manipulação ou visualização de dados.
    O código deve usar um DataFrame chamado `df`.
    O resultado da execução deve ser armazenado em uma variável chamada `resultado`.
    Retorna o resultado da execução ou uma mensagem de erro.
    """
    try:
        # Prepara o DataFrame ativo com base no escopo
        if scope == "Analisar Todos em Conjunto":
            active_df = pd.concat(st.session_state.dataframes.values(), ignore_index=True)
        else:
            active_df = st.session_state.dataframes[scope]
        
        namespace = {'df': active_df, 'plt': plt, 'sns': sns, 'pd': pd, 'io': io}
        exec(code, namespace)
        return namespace.get('resultado', "Código executado, mas sem resultado explícito.")
    except Exception as e:
        return f"Erro ao executar o código: {e}"

def web_search(query: str):
    """
    Realiza uma busca na web para encontrar informações atuais ou de conhecimento geral.
    Use para perguntas sobre cotações de moeda, definições, notícias ou qualquer coisa que não esteja nos dados.
    """
    with DDGS() as ddgs:
        results = [r['body'] for r in ddgs.text(query, max_results=3)]
    return "\n".join(results) if results else "Nenhum resultado encontrado."

def list_available_data():
    """
    Lista todos os arquivos de dados (CSVs) que foram carregados e estão disponíveis para análise.
    """
    if not st.session_state.dataframes:
        return "Nenhum arquivo de dados foi carregado ainda."
    return f"Os seguintes arquivos estão disponíveis: {', '.join(st.session_state.dataframes.keys())}"

def get_data_schema(filename: str):
    """
    Fornece o esquema (nomes das colunas e tipos de dados) de um arquivo de dados específico.
    """
    if filename not in st.session_state.dataframes:
        return f"Erro: O arquivo '{filename}' não foi encontrado."
    df = st.session_state.dataframes[filename]
    buffer = io.StringIO()
    df.info(buf=buffer)
    return buffer.getvalue()

# Dicionário de ferramentas para fácil acesso
TOOLS = {
    "python_code_interpreter": python_code_interpreter,
    "web_search": web_search,
    "list_available_data": list_available_data,
    "get_data_schema": get_data_schema
}

# =============================================================================
# 4. O AGENTE EXECUTOR (ReAct)
# =============================================================================

def agent_executor(query, chat_history, scope):
    """O cérebro do sistema. Usa o modelo ReAct para pensar e usar ferramentas."""
    
    # RAG: Recuperação de contexto relevante
    context = f"""
    **Contexto Atual da Análise:**
    - Escopo Selecionado: {scope}
    - Arquivos Disponíveis: {list(st.session_state.dataframes.keys())}
    - Histórico da Conversa: {"".join([f'{m["role"]}: {m["content"]}\\n' for m in chat_history])}
    """

    prompt = f"""
    Você é um Analista de Dados Autônomo. Sua missão é responder à pergunta do usuário usando um ciclo de Pensamento-Ação-Observação (ReAct).
    Você tem acesso a um conjunto de ferramentas e deve decidir qual usar para cada passo.

    {context}

    **Ferramentas Disponíveis:**
    - `python_code_interpreter(code: str, scope: str)`: Executa código Python para análise de dados.
    - `web_search(query: str)`: Busca informações na web.
    - `list_available_data()`: Lista os arquivos de dados carregados.
    - `get_data_schema(filename: str)`: Obtém as colunas de um arquivo específico.

    **Ciclo de Trabalho:**
    1.  **Thought:** Descreva seu plano passo a passo. O que você precisa saber? Qual ferramenta o ajudará a obter essa informação?
    2.  **Action:** Escolha UMA ferramenta e formule a entrada para ela em um formato JSON.
        Exemplo de Ação:
        ```json
        {{"tool": "web_search", "tool_input": "cotação atual BRL para USD"}}
        ```
    3.  O sistema executará a ferramenta e você receberá uma **Observation**.
    4.  Repita o ciclo Pensamento-Ação até ter informações suficientes para responder à pergunta original.
    5.  Quando tiver a resposta final, seu último pensamento deve ser "Eu tenho a resposta final." e a Ação deve ser um JSON com a ferramenta "final_answer" e a resposta completa.
        ```json
        {{"tool": "final_answer", "tool_input": "A resposta final é..."}}
        ```

    **Inicie o processo.**

    **Pergunta do Usuário:** "{query}"
    """
    
    response = model.generate_content(prompt)
    try:
        # Extrai o JSON da resposta do LLM
        json_part = response.text.split("```json").split("```")[0]
        action_json = json.loads(json_part)
        return action_json, response.text # Retorna a ação e o pensamento completo
    except (IndexError, json.JSONDecodeError):
        # Fallback se o LLM não seguir o formato
        return {"tool": "final_answer", "tool_input": f"Desculpe, tive um problema ao formular um plano de ação. A resposta do modelo foi: {response.text}"}, response.text

# =============================================================================
# 5. LÓGICA DA INTERFACE E ESTADO DA SESSÃO
# =============================================================================

# Inicialização do estado da sessão para garantir que as variáveis existam
if "messages" not in st.session_state:
    st.session_state.messages = []
if "dataframes" not in st.session_state:
    st.session_state.dataframes = None
if "active_scope" not in st.session_state:
    st.session_state.active_scope = "Nenhum"

# --- LÓGICA DE LAYOUT CONDICIONAL ---

# Se nenhum arquivo foi carregado, mostra a interface de UPLOAD.
if st.session_state.dataframes is None:
    
    # Título e Slogan
    st.title("🍏 Data Insights Pro")
    st.markdown("##### Um universo de dados em um único lugar. Pergunte, explore, descubra.")
    st.markdown("---")
    
    # Área de Upload Centralizada
    st.info("Para começar, carregue um arquivo `.zip` contendo um ou mais arquivos `.csv`.")
    uploaded_file = st.file_uploader(
        "Arraste seu catálogo de dados aqui ou clique para procurar", 
        type="zip", 
        label_visibility="collapsed"
    )
    
    if uploaded_file:
        with st.spinner("Catalogando e analisando seus arquivos..."):
            # Use a função de carregar múltiplos dataframes
            dfs = load_dataframes_from_zip(uploaded_file) 
            if dfs:
                st.session_state.dataframes = dfs
                st.session_state.messages = []
                # Use a função de onboarding que lida com múltiplos arquivos
                welcome_message = agent_onboarding(dfs) 
                st.session_state.messages.append({"role": "assistant", "content": welcome_message})
                st.session_state.active_scope = "Analisar Todos em Conjunto"
                st.rerun()
            else:
                st.error("Nenhum arquivo .csv encontrado no .zip.")

# Se arquivos JÁ foram carregados, mostra a interface de CHAT.
else:
    # Cabeçalho do Chat
    st.title("🍏 Conversando com seus Dados")

    # Seletor de escopo e botão de reset em colunas para organização
    col1, col2 = st.columns([3, 1])
    with col1:
        scope_options = ["Analisar Todos em Conjunto"] + list(st.session_state.dataframes.keys())
        st.session_state.active_scope = st.selectbox(
            "Escopo da Análise:",
            options=scope_options,
            index=scope_options.index(st.session_state.active_scope),
            label_visibility="collapsed"
        )
    with col2:
        if st.button("Analisar Outro", use_container_width=True):
            st.session_state.dataframes = None
            st.session_state.messages = []
            st.session_state.active_scope = "Nenhum"
            st.rerun()
    
    st.markdown("---")

    # Exibe o histórico de mensagens
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if isinstance(message["content"], str):
                st.markdown(message["content"])
            elif "thought" in message["content"]: # Para exibir o raciocínio do agente
                 with st.expander("Ver o Raciocínio do Agente"):
                    st.markdown(message["content"]["thought"])
            else: # Para exibir gráficos
                st.pyplot(message["content"])

    # Captura a nova pergunta do usuário
    if prompt := st.chat_input(f"Pergunte sobre '{st.session_state.active_scope}'..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Processa a pergunta com os agentes
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                try:
                    # Lógica de execução do agente (ReAct)
                    action_json, thought_process = agent_executor(prompt, st.session_state.messages, st.session_state.active_scope)
                    
                    st.session_state.messages.append({"role": "assistant", "content": {"thought": thought_process}})
                    with st.expander("Ver o Raciocínio do Agente"):
                        st.markdown(thought_process)

                    tool_name = action_json.get("tool")
                    tool_input = action_json.get("tool_input")
                    
                    if tool_name == "final_answer":
                        final_response = tool_input
                    elif tool_name in TOOLS:
                        tool_output = TOOLS[tool_name](tool_input, scope=st.session_state.active_scope) if tool_name == "python_code_interpreter" else TOOLS[tool_name](tool_input)
                        
                        final_response = f"**Resultado da Ferramenta `{tool_name}`:**\n\n"
                        if isinstance(tool_output, plt.Figure):
                            st.pyplot(tool_output)
                            st.session_state.messages.append({"role": "assistant", "content": tool_output})
                            final_response = None
                        else:
                            final_response += str(tool_output)
                    else:
                        final_response = "Desculpe, o agente escolheu uma ferramenta desconhecida."

                    if final_response:
                        st.markdown(final_response)
                        st.session_state.messages.append({"role": "assistant", "content": final_response})

                except Exception as e:
                    error_message = f"Ocorreu um erro crítico no ciclo do agente.\n\n**Detalhe técnico:** `{e}`"
                    st.error(error_message)
                    st.session_state.messages.append({"role": "assistant", "content": error_message})

    if st.button("Analisar Novo Catálogo de Dados"):
        # ... (código do botão idêntico ao anterior)
        pass
