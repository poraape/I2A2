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
st.set_page_config(layout="wide", page_title="Data Insights Hub", page_icon="🗂️")

def load_css():
    st.markdown("""
    <style>
        html, body, [class*="st-"] {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
        }
        .block-container { padding: 2rem 3rem; }
    </style>
    """, unsafe_allow_html=True)

load_css()

# =============================================================================
# 2. CONFIGURAÇÃO DO MODELO DE IA (GEMINI)
# =============================================================================
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception:
    st.error("Chave da API do Google não configurada.")
    st.stop()

# =============================================================================
# 3. ARQUITETURA MULTI-AGENTE (ADAPTADA PARA MÚLTIPLOS ARQUIVOS)
# =============================================================================
def agent_onboarding(dataframes_dict):
    """Analisa um dicionário de dataframes e gera um resumo e perguntas estratégicas."""
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

    **Resumo do Catálogo de Dados:**
    ---
    {summary}
    ---
    **Amostra do Conjunto de Dados Combinado:**
    ---
    {combined_df.head().to_markdown()}
    ---

    Com base nas informações acima, realize as seguintes tarefas:
    1.  **Resumo Executivo:** Escreva um parágrafo sobre o potencial analítico deste conjunto de dados, considerando tanto as análises individuais por arquivo quanto a análise agregada.
    2.  **Perguntas Estratégicas Sugeridas:** Formule uma lista de 4 perguntas inteligentes que explorem os dados. Inclua pelo menos uma pergunta sobre um arquivo específico, uma pergunta sobre a análise combinada e uma que sugira uma visualização.
        - Exemplo (Individual): "Qual a receita total no arquivo `vendas_2023.csv`?"
        - Exemplo (Combinada): "Qual foi a média de vendas mensal em todos os anos?"
        - Exemplo (Visualização): "Poderia gerar um gráfico de linhas mostrando a tendência de vendas ao longo do tempo para o conjunto de dados combinado?"
    """
    response = model.generate_content(prompt)
    return summary + "\n" + response.text

# As outras funções de agente (router, generators, synthesizer) permanecem as mesmas,
# pois elas operam no DataFrame que lhes é passado, sem se importar com a origem.
# ... (Cole aqui as funções agent_router, tool_code_generator, etc. da versão anterior) ...
# (Para manter a resposta concisa, estou omitindo as funções que não mudam, mas você deve mantê-las no seu código)
def agent_router(query, chat_history):
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
    prompt = f"""
    Você é um agente roteador de IA. Sua função é analisar a pergunta do usuário e o histórico da conversa para decidir qual ferramenta é a mais apropriada para a tarefa.
    Ferramentas Disponíveis: `gerar_codigo_pandas` (para cálculos, tabelas), `gerar_codigo_visualizacao` (para gráficos).
    Histórico da Conversa: {history_str}
    Pergunta Atual do Usuário: "{query}"
    Responda APENAS com um objeto JSON contendo "ferramenta" e "pergunta_refinada".
    """
    response = model.generate_content(prompt)
    try:
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(cleaned_response)
    except (json.JSONDecodeError, AttributeError):
        return {"ferramenta": "gerar_codigo_pandas", "pergunta_refinada": query}

def tool_code_generator(query, df_head):
    prompt = f"""
    Você é um especialista em Python e Pandas. Gere código para responder à pergunta.
    DataFrame: `df`. Amostra: {df_head.to_markdown()}
    Pergunta: "{query}"
    Gere APENAS o código Python. O resultado DEVE ser armazenado na variável `resultado`.
    """
    response = model.generate_content(prompt)
    raw_code = response.text
    return raw_code.replace("```python", "").replace("```", "").strip()

def tool_visualization_generator(query, df_head):
    prompt = f"""
    Você é um especialista em visualização de dados com Python, Matplotlib e Seaborn.
    Gere código para criar uma visualização que responda à pergunta do usuário.
    Use o DataFrame `df`. Amostra: {df_head.to_markdown()}
    Pergunta: "{query}"
    Instruções Cruciais:
    1. Importe `matplotlib.pyplot as plt` e `seaborn as sns`.
    2. Crie a figura e os eixos (ex: `fig, ax = plt.subplots()`).
    3. Gere o gráfico usando `ax`. Adicione títulos e rótulos claros.
    4. NÃO use `plt.show()`.
    5. O seu código DEVE retornar a figura gerada na variável `resultado` (ex: `resultado = fig`).
    Gere APENAS o código Python.
    """
    response = model.generate_content(prompt)
    raw_code = response.text
    return raw_code.replace("```python", "").replace("```", "").strip()

def agent_results_synthesizer(query, code_result):
    return f"**Análise para a pergunta:** '{query}'\n\n**Resultado:**\n\n```\n{str(code_result)}\n```"

# =============================================================================
# 4. FUNÇÕES AUXILIARES (ATUALIZADAS)
# =============================================================================
def load_dataframes_from_zip(zip_file):
    """Carrega TODOS os CSVs de um arquivo zip em um dicionário de DataFrames."""
    dataframes = {}
    try:
        with zipfile.ZipFile(zip_file, 'r') as z:
            for filename in z.namelist():
                if filename.lower().endswith('.csv'):
                    with z.open(filename) as f:
                        # Usa o nome do arquivo como chave
                        dataframes[filename] = pd.read_csv(f, on_bad_lines='skip')
        return dataframes if dataframes else None
    except Exception:
        return None

# =============================================================================
# 5. LÓGICA DA INTERFACE E ESTADO DA SESSÃO (REESTRUTURADA)
# =============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "dataframes" not in st.session_state:
    st.session_state.dataframes = None
if "active_scope" not in st.session_state:
    st.session_state.active_scope = "Nenhum"

# --- Layout Principal ---
left_column, right_column = st.columns([1, 2.5], gap="large")

# --- PAINEL ESQUERDO: CONTROLES ---
with left_column:
    st.title("🗂️ Data Hub")
    
    if st.session_state.dataframes is None:
        st.info("Carregue um arquivo `.zip` para catalogar seus dados.")
        uploaded_file = st.file_uploader("Carregar arquivo", type="zip", label_visibility="collapsed")
        if uploaded_file:
            with st.spinner("Catalogando arquivos..."):
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
    else:
        st.success("Catálogo de dados pronto!")
        st.markdown("---")
        
        # Menu de seleção de escopo
        scope_options = ["Analisar Todos em Conjunto"] + list(st.session_state.dataframes.keys())
        st.session_state.active_scope = st.selectbox(
            "**Selecione o escopo da análise:**",
            options=scope_options,
            index=scope_options.index(st.session_state.active_scope) # Mantém a seleção
        )
        
        st.markdown("---")
        if st.button("Analisar Novo Catálogo"):
            st.session_state.dataframes = None
            st.session_state.messages = []
            st.session_state.active_scope = "Nenhum"
            st.rerun()

# --- PAINEL DIREITO: CHAT ---
with right_column:
    st.title("🍏 Insights")
    
    if st.session_state.dataframes is None:
        st.info("Aguardando o carregamento de um catálogo de dados no painel à esquerda.")
    else:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if isinstance(message["content"], str):
                    st.markdown(message["content"])
                else:
                    st.pyplot(message["content"])

        if prompt := st.chat_input(f"Pergunte sobre '{st.session_state.active_scope}'..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Analisando..."):
                    try:
                        # Prepara o DataFrame ativo com base no escopo
                        if st.session_state.active_scope == "Analisar Todos em Conjunto":
                            active_df = pd.concat(st.session_state.dataframes.values(), ignore_index=True)
                        else:
                            active_df = st.session_state.dataframes[st.session_state.active_scope]
                        
                        # Roteador decide qual ferramenta usar
                        router_decision = agent_router(prompt, st.session_state.messages)
                        ferramenta = router_decision.get("ferramenta")
                        pergunta_refinada = router_decision.get("pergunta_refinada", prompt)
                        st.write(f"🤖 *Escopo: `{st.session_state.active_scope}`. Ferramenta: `{ferramenta}`...*")
                        
                        # Gera e executa o código
                        codigo_gerado = ""
                        if ferramenta == "gerar_codigo_visualizacao":
                            codigo_gerado = tool_visualization_generator(pergunta_refinada, active_df.head())
                        else:
                            codigo_gerado = tool_code_generator(pergunta_refinada, active_df.head())
                        
                        namespace = {'df': active_df, 'plt': plt, 'sns': sns, 'pd': pd, 'io': io}
                        exec(codigo_gerado, namespace)
                        resultado_bruto = namespace.get('resultado')

                        # Exibe o resultado
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
