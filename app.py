# data_insights_app.py - Refatorado com melhorias estruturais

import streamlit as st
import pandas as pd
import zipfile
import io
import json
import logging
import matplotlib.pyplot as plt
import seaborn as sns
from duckduckgo_search import DDGS
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

# =============================================================================
# CONFIGURAÇÃO E CSS
# =============================================================================
st.set_page_config(layout="centered", page_title="Data Insights Pro", page_icon="🍏")
logging.basicConfig(level=logging.INFO)

def load_css():
    st.markdown("""
    <style>
    html, body, [class*="st-"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    }
    .block-container { max-width: 720px; padding-top: 3rem; padding-bottom: 3rem; }
    [data-testid="stFileUploader"] { background-color: #f8f8fa; border: 1.5px dashed #d0d0d5; border-radius: 12px; padding: 2rem; }
    </style>
    """, unsafe_allow_html=True)

load_css()

# =============================================================================
# FUNÇÕES UTILITÁRIAS
# =============================================================================
def load_dataframes_from_zip(uploaded_file):
    dfs = {}
    with zipfile.ZipFile(uploaded_file) as archive:
        for name in archive.namelist():
            if name.endswith('.csv'):
                with archive.open(name) as f:
                    dfs[name] = pd.read_csv(f)
    return dfs

def get_active_df(scope: str) -> pd.DataFrame:
    if scope == "Analisar Todos em Conjunto":
        return pd.concat(st.session_state.dataframes.values(), ignore_index=True)
    return st.session_state.dataframes[scope]

def agent_onboarding(dfs: dict) -> str:
    return f"{len(dfs)} arquivos carregados com sucesso. Podemos começar a análise!"

# =============================================================================
# CONFIGURANDO O MODELO GEMINI
# =============================================================================
try:
    GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        raise ValueError("Chave não encontrada.")
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception:
    st.error("Chave da API do Google não configurada corretamente.")
    st.stop()

# =============================================================================
# TOOLS
# =============================================================================
def python_code_interpreter(code: str, scope: str):
    try:
        df = get_active_df(scope)
        namespace = {'df': df, 'plt': plt, 'sns': sns, 'pd': pd, 'io': io}
        exec(code, namespace)
        return namespace.get('resultado', "Código executado, mas sem resultado explícito.")
    except Exception as e:
        return f"Erro ao executar o código: {e}"

def web_search(query: str):
    with DDGS() as ddgs:
        results = [r['body'] for r in ddgs.text(query, max_results=3)]
    return "\n".join(results) if results else "Nenhum resultado encontrado."

def list_available_data():
    if not st.session_state.dataframes:
        return "Nenhum arquivo de dados foi carregado ainda."
    return f"Arquivos disponíveis: {', '.join(st.session_state.dataframes.keys())}"

def get_data_schema(filename: str):
    if filename not in st.session_state.dataframes:
        return f"Erro: O arquivo '{filename}' não foi encontrado."
    buffer = io.StringIO()
    st.session_state.dataframes[filename].info(buf=buffer)
    return buffer.getvalue()

TOOLS = {
    "python_code_interpreter": python_code_interpreter,
    "web_search": web_search,
    "list_available_data": list_available_data,
    "get_data_schema": get_data_schema
}

# =============================================================================
# AGENTE EXECUTOR SIMPLES (1 ciclo ReAct)
# =============================================================================
def agent_executor(query, chat_history, scope):
    recent_history = chat_history[-5:]  # limitar histórico para evitar excesso de tokens
    history_str = "".join([f"{m['role']}: {m['content']}\n" for m in recent_history])
    context = f"""
    **Contexto da Análise:**
    - Escopo: {scope}
    - Arquivos: {list(st.session_state.dataframes.keys())}
    - Histórico: {history_str}
    """
    prompt = f"""
    Você é um analista de dados. Siga o ciclo Thought → Action → Observation para resolver:
    {context}
    Pergunta: "{query}"
    Ferramentas: {list(TOOLS.keys())}
    Ao concluir, envie: {{"tool": "final_answer", "tool_input": "..."}}
    """
    try:
        response = model.generate_content(prompt)
    except ResourceExhausted:
        return {"tool": "final_answer", "tool_input": "Limite de uso da API excedido. Tente novamente mais tarde."}, ""

    try:
        json_str = next(part for part in response.text.split("```") if '{' in part)
        return json.loads(json_str), response.text
    except Exception:
        return {"tool": "final_answer", "tool_input": response.text}, response.text

# =============================================================================
# INTERFACE STREAMLIT
# =============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "dataframes" not in st.session_state:
    st.session_state.dataframes = None
if "active_scope" not in st.session_state:
    st.session_state.active_scope = "Nenhum"

if st.session_state.dataframes is None:
    st.title("🍏 Insights")
    st.markdown("##### Transforme dados brutos em diálogos inteligentes.")
    uploaded_file = st.file_uploader("Arraste seu .zip com CSVs", type="zip")
    if uploaded_file:
        with st.spinner("Processando arquivos..."):
            dfs = load_dataframes_from_zip(uploaded_file)
            if dfs:
                st.session_state.dataframes = dfs
                st.session_state.messages = []
                st.session_state.active_scope = "Analisar Todos em Conjunto"
                welcome = agent_onboarding(dfs)
                st.session_state.messages.append({"role": "assistant", "content": welcome})
                st.rerun()
            else:
                st.error("Nenhum CSV encontrado no ZIP.")
else:
    st.title("🍏 Conversando com seus Dados")
    col1, col2 = st.columns([3,1])
    with col1:
        options = ["Analisar Todos em Conjunto"] + list(st.session_state.dataframes.keys())
        st.session_state.active_scope = st.selectbox("Escopo:", options, index=options.index(st.session_state.active_scope))
    with col2:
        if st.button("Novo Catálogo"):
            st.session_state.dataframes = None
            st.rerun()

    st.markdown("---")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input(f"Pergunte sobre '{st.session_state.active_scope}'"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Analisando..."):
                tool_action, pensamento = agent_executor(prompt, st.session_state.messages, st.session_state.active_scope)
                st.write(pensamento)
                if tool_action["tool"] == "final_answer":
                    st.markdown(tool_action["tool_input"])
                    st.session_state.messages.append({"role": "assistant", "content": tool_action["tool_input"]})
                else:
                    tool_fn = TOOLS.get(tool_action["tool"])
                    output = tool_fn(tool_action["tool_input"], st.session_state.active_scope) if 'scope' in tool_fn.__code__.co_varnames else tool_fn(tool_action["tool_input"])
                    st.markdown(f"**Resultado da ferramenta:**\n\n{output}")
                    st.session_state.messages.append({"role": "assistant", "content": output})
