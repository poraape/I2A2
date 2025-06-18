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
st.set_page_config(layout="centered", page_title="Data Insights Pro", page_icon="🍏")
def load_css():
    st.markdown("""<style>... (CSS permanece o mesmo) ...</style>""", unsafe_allow_html=True) # Ocultado para brevidade
load_css()

# =============================================================================
# 2. CONFIGURAÇÃO DO MODELO DE IA (GEMINI)
# =============================================================================
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-pro-latest') # Usando o modelo Pro para máxima capacidade
except Exception:
    st.error("Chave da API do Google não configurada.")
    st.stop()

# =============================================================================
# 3. ARQUITETURA DE AGENTE ÚNICO E ROBUSTO
# =============================================================================

def agent_command_control(query, df_columns, df_head, chat_history):
    """Agente central que refina a pergunta e gera um plano de execução estruturado."""
    columns_str = ", ".join(df_columns)
    history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])

    prompt = f"""
    Você é um Analista de Dados Sênior e um programador Python especialista. Sua missão é converter uma pergunta de um usuário em um plano de ação executável.

    **Contexto Disponível:**
    - **DataFrame `df`:** Contém os dados para análise.
    - **Colunas Disponíveis:** [{columns_str}]
    - **Histórico da Conversa:**
    {history_str}
    - **Pergunta Atual do Usuário:** "{query}"

    **Sua Tarefa:**
    Analise a pergunta do usuário no contexto fornecido. Sua resposta DEVE ser um único objeto JSON com as seguintes três chaves:
    1.  `"pergunta_refinada"`: Reformule a pergunta do usuário para ser clara, específica e sem ambiguidades.
    2.  `"codigo"`: Gere o código Python/Pandas/Matplotlib para responder à `pergunta_refinada`. O resultado deve ser armazenado em uma variável `resultado`. Se a pergunta não puder ser respondida com código (ex: é uma saudação ou uma pergunta meta-analítica), o valor DEVE ser `null`.
    3.  `"explicacao"`: Descreva em uma frase o que o código faz. Se o código for `null`, explique por que você não pôde gerar o código (ex: a pergunta é ambígua, faltam informações, etc.).

    **Exemplo 1: Pergunta Clara**
    - Pergunta do Usuário: "qual a média de idade?"
    - Sua Resposta JSON:
      {{"pergunta_refinada": "Qual é a média da coluna 'idade'?", "codigo": "resultado = df['idade'].mean()", "explicacao": "Calculando a média da coluna 'idade'."}}

    **Exemplo 2: Pergunta Ambígua**
    - Pergunta do Usuário: "e sobre as vendas?"
    - Sua Resposta JSON:
      {{"pergunta_refinada": "Análise sobre as vendas", "codigo": null, "explicacao": "A pergunta sobre 'vendas' é muito ampla. Você gostaria de ver o total de vendas, a média, a distribuição ao longo do tempo ou as vendas por categoria?"}}
      
    **Exemplo 3: Pergunta Visual**
    - Pergunta do Usuário: "mostre um gráfico das categorias"
    - Sua Resposta JSON:
      {{"pergunta_refinada": "Gerar um gráfico de contagem para cada categoria na coluna 'categoria'", "codigo": "import matplotlib.pyplot as plt\\nfig, ax = plt.subplots()\\ndf['categoria'].value_counts().plot(kind='bar', ax=ax)\\nax.set_title('Contagem por Categoria')\\nax.set_ylabel('Contagem')\\nresultado = fig", "explicacao": "Gerando um gráfico de barras para visualizar a contagem de cada categoria."}}
    """
    response = model.generate_content(prompt)
    try:
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(cleaned_response)
    except (json.JSONDecodeError, AttributeError):
        # Fallback se o JSON falhar
        return {"pergunta_refinada": query, "codigo": None, "explicacao": "Desculpe, tive um problema ao processar sua solicitação. Poderia tentar reformular a pergunta?"}

# As funções de onboarding e load_csv permanecem as mesmas
# ... (Cole aqui as funções agent_onboarding e load_dataframes_from_zip da versão anterior) ...
def agent_onboarding(dataframes_dict):
    #... (código idêntico ao anterior)
    pass
def load_dataframes_from_zip(zip_file):
    #... (código idêntico ao anterior)
    pass

# =============================================================================
# 5. LÓGICA DA INTERFACE E ESTADO DA SESSÃO (ATUALIZADA)
# =============================================================================
# ... (A parte inicial da interface permanece a mesma) ...
# (Para manter a resposta concisa, estou omitindo as partes que não mudam, mas você deve mantê-las no seu código)
if "messages" not in st.session_state:
    st.session_state.messages = []
if "dataframes" not in st.session_state:
    st.session_state.dataframes = None
if "active_scope" not in st.session_state:
    st.session_state.active_scope = "Nenhum"

st.title("🍏 Data Insights Pro")
st.markdown("##### Um universo de dados em um único lugar. Pergunte, explore, descubra.")
st.markdown("---")

if st.session_state.dataframes is None:
    # ... (código de upload idêntico ao anterior)
    pass
else:
    # ... (código do seletor de escopo idêntico ao anterior)
    pass

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

        # --- NOVA LÓGICA DE EXECUÇÃO ROBUSTA ---
        with st.chat_message("assistant"):
            with st.spinner("Analisando..."):
                try:
                    # Prepara o DataFrame ativo com base no escopo
                    if st.session_state.active_scope == "Analisar Todos em Conjunto":
                        active_df = pd.concat(st.session_state.dataframes.values(), ignore_index=True)
                    else:
                        active_df = st.session_state.dataframes[st.session_state.active_scope]

                    # Chama o agente de comando central
                    response_json = agent_command_control(prompt, list(active_df.columns), active_df.head(), st.session_state.messages)
                    
                    pergunta_refinada = response_json.get("pergunta_refinada")
                    codigo_gerado = response_json.get("codigo")
                    explicacao = response_json.get("explicacao")

                    st.info(f"**Plano de Ação do Agente:** {explicacao}")

                    # Se o código for nulo, apenas mostre a explicação e pare
                    if codigo_gerado is None:
                        st.warning(explicacao)
                        st.session_state.messages.append({"role": "assistant", "content": explicacao})
                    else:
                        # Se houver código, tente executá-lo
                        namespace = {'df': active_df, 'plt': plt, 'sns': sns, 'pd': pd, 'io': io}
                        exec(codigo_gerado, namespace)
                        resultado_bruto = namespace.get('resultado')

                        # Exibe o resultado
                        if isinstance(resultado_bruto, plt.Figure):
                            st.pyplot(resultado_bruto)
                            st.session_state.messages.append({"role": "assistant", "content": resultado_bruto})
                        else:
                            # Formata o resultado para exibição
                            resposta_formatada = f"**Análise para:** '{pergunta_refinada}'\n\n**Resultado:**\n\n```\n{str(resultado_bruto)}\n```"
                            st.markdown(resposta_formatada)
                            st.session_state.messages.append({"role": "assistant", "content": resposta_formatada})

                except Exception as e:
                    error_message = f"Desculpe, encontrei um erro crítico durante a execução. Isso pode ser um problema no código gerado.\n\n**Detalhe técnico:** `{e}`"
                    st.error(error_message)
                    st.session_state.messages.append({"role": "assistant", "content": error_message})

    if st.button("Analisar Novo Catálogo de Dados"):
        # ... (código do botão idêntico ao anterior)
        pass
