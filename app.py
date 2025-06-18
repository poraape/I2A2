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
st.set_page_config(layout="centered", page_title="Data Insights", page_icon="🍏")

def load_css():
    st.markdown("""
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
        .block-container { max-width: 800px; padding-top: 3rem; padding-bottom: 3rem; }
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
# 3. ARQUITETURA MULTI-AGENTE 2.0
# =============================================================================

def agent_onboarding(df):
    """Analisa o dataframe (info e describe) e gera insights proativos."""
    info_buffer = io.StringIO()
    df.info(buf=info_buffer)
    df_info = info_buffer.getvalue()
    df_describe = df.describe().to_markdown()

    prompt = f"""
    Você é um Analista de Dados Estratégico. Sua missão é realizar uma análise exploratória inicial (EDA) em um novo conjunto de dados e apresentar suas descobertas de forma proativa.

    **Estrutura dos Dados (df.info()):**
    ---
    {df_info}
    ---
    **Resumo Estatístico (df.describe()):**
    ---
    {df_describe}
    ---
    **Amostra dos Dados (df.head()):**
    ---
    {df.head().to_markdown()}
    ---

    Com base em TODAS as informações acima, realize as seguintes tarefas:
    1.  **Resumo Executivo:** Escreva um parágrafo conciso sobre a natureza e o propósito provável deste conjunto de dados.
    2.  **Insights Iniciais:** Identifique 2-3 observações interessantes diretamente das estatísticas. Aponte para possíveis anomalias, distribuições notáveis ou correlações implícitas (ex: "A média da 'idade' é 35, mas o valor máximo é 99, o que pode indicar outliers. A receita tem um grande desvio padrão, sugerindo vendas muito desiguais.").
    3.  **Perguntas Estratégicas:** Formule uma lista de 3 perguntas inteligentes e acionáveis que um líder de negócios faria. Essas perguntas devem ir além do óbvio e sugerir análises mais profundas, incluindo visualizações (ex: "Qual é a correlação entre 'investimento_marketing' e 'receita'?", "Como as vendas se distribuem por categoria de produto em um gráfico de barras?").
    """
    response = model.generate_content(prompt)
    return response.text

def agent_router(query, chat_history):
    """O cérebro do sistema. Decide qual ferramenta usar."""
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
    
    prompt = f"""
    Você é um agente roteador de IA. Sua função é analisar a pergunta do usuário e o histórico da conversa para decidir qual ferramenta é a mais apropriada para a tarefa.

    **Ferramentas Disponíveis:**
    1. `gerar_codigo_pandas`: Use para perguntas que podem ser respondidas com um cálculo, uma tabela, um número ou texto. Exemplos: "qual a média de idade?", "liste os 5 produtos mais vendidos", "qual o total de vendas?".
    2. `gerar_codigo_visualizacao`: Use para perguntas que pedem explicitamente por um gráfico ou implicam uma análise visual. Exemplos: "mostre-me um gráfico de barras", "qual a distribuição da idade?", "plote a série temporal de vendas", "crie um histograma".

    **Histórico da Conversa:**
    {history_str}

    **Pergunta Atual do Usuário:**
    "{query}"

    Com base na pergunta atual e no contexto do histórico, qual ferramenta você deve usar?
    Responda APENAS com um objeto JSON contendo duas chaves: "ferramenta" e "pergunta_refinada".
    A "pergunta_refinada" deve ser a pergunta do usuário, possivelmente enriquecida com o contexto do histórico.

    Exemplo de Resposta 1:
    {{"ferramenta": "gerar_codigo_pandas", "pergunta_refinada": "Qual é a média de idade dos clientes no Brasil?"}}

    Exemplo de Resposta 2:
    {{"ferramenta": "gerar_codigo_visualizacao", "pergunta_refinada": "Gerar um gráfico de barras mostrando o total de vendas por categoria de produto"}}
    """
    response = model.generate_content(prompt)
    try:
        # Limpa a resposta para garantir que seja um JSON válido
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(cleaned_response)
    except (json.JSONDecodeError, AttributeError):
        # Fallback se o LLM não retornar um JSON válido
        return {"ferramenta": "gerar_codigo_pandas", "pergunta_refinada": query}


def tool_code_generator(query, df_head):
    """Ferramenta que gera código Pandas."""
    prompt = f"""
    Você é um especialista em Python e Pandas. Gere código para responder à pergunta.
    DataFrame: `df`.
    Amostra:
    {df_head.to_markdown()}
    Pergunta: "{query}"
    Gere APENAS o código Python. O resultado final DEVE ser armazenado na variável `resultado`.
    """
    response = model.generate_content(prompt)
    # <-- MUDANÇA: Lógica de sanitização para remover texto extra e Markdown
    raw_code = response.text
    cleaned_code = raw_code.replace("```python", "").replace("```", "").strip()
    return cleaned_code

def tool_visualization_generator(query, df_head):
    """Ferramenta que gera código de visualização."""
    # <-- MUDANÇA: Removida a formatação Markdown (**) do prompt
    prompt = f"""
    Você é um especialista em visualização de dados com Python, Matplotlib e Seaborn.
    Gere código para criar uma visualização que responda à pergunta do usuário.
    Use o DataFrame `df`.
    Amostra:
    {df_head.to_markdown()}
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
    # Lógica de sanitização para remover texto extra e Markdown
    raw_code = response.text
    cleaned_code = raw_code.replace("```python", "").replace("```", "").strip()
    return cleaned_code

def agent_results_synthesizer(query, code_result):
    """Sintetiza resultados textuais."""
    # Implementação simplificada para manter o foco na lógica principal
    return f"**Análise para a pergunta:** '{query}'\n\n**Resultado:**\n\n```\n{str(code_result)}\n```"

# =============================================================================
# 4. FUNÇÕES AUXILIARES
# =============================================================================
def load_csv_from_zip(zip_file):
    try:
        with zipfile.ZipFile(zip_file, 'r') as z:
            csv_filename = next((name for name in z.namelist() if name.lower().endswith('.csv')), None)
            if csv_filename:
                with z.open(csv_filename) as f:
                    return pd.read_csv(f, on_bad_lines='skip')
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

st.title("🍏 Data Insights Pro")
st.markdown("Seu parceiro de análise estratégica, com a tecnologia Gemini 1.5.")
st.markdown("---")

if st.session_state.df is None:
    st.info("Para começar, carregue um arquivo `.zip` contendo um `.csv`.")
    uploaded_file = st.file_uploader("Arraste seu arquivo aqui", type="zip", label_visibility="collapsed")
    if uploaded_file:
        with st.spinner("Realizando análise exploratória inicial..."):
            df = load_csv_from_zip(uploaded_file)
            if df is not None:
                st.session_state.df = df
                st.session_state.messages = []
                welcome_message = agent_onboarding(df)
                st.session_state.messages.append({"role": "assistant", "content": welcome_message})
                st.rerun()
            else:
                st.error("Nenhum arquivo .csv encontrado no .zip.")
else:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if isinstance(message["content"], str):
                st.markdown(message["content"])
            else: # Se for um gráfico
                st.pyplot(message["content"])

    if prompt := st.chat_input("Faça uma pergunta ou peça um gráfico..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analisando e decidindo a melhor abordagem..."):
                try:
                    # Roteador decide qual ferramenta usar
                    router_decision = agent_router(prompt, st.session_state.messages)
                    ferramenta = router_decision.get("ferramenta")
                    pergunta_refinada = router_decision.get("pergunta_refinada", prompt)

                    st.write(f"🤖 *Decisão do Agente: Usando a ferramenta `{ferramenta}`...*")
                    
                    codigo_gerado = ""
                    if ferramenta == "gerar_codigo_visualizacao":
                        codigo_gerado = tool_visualization_generator(pergunta_refinada, st.session_state.df.head())
                    else: # Fallback para pandas
                        codigo_gerado = tool_code_generator(pergunta_refinada, st.session_state.df.head())
                    
                    # Executa o código gerado
                    namespace = {
                        'df': st.session_state.df,
                        'plt': plt,
                        'sns': sns,
                        'pd': pd,
                        'io': io
                    }
                    exec(codigo_gerado, namespace)
                    resultado_bruto = namespace.get('resultado')

                    # Exibe o resultado apropriado
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
    
    st.markdown("---")
    if st.button("Analisar Novo Arquivo"):
        st.session_state.df = None
        st.session_state.messages = []
        st.rerun()
