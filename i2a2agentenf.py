import streamlit as st
import pandas as pd
import zipfile
import google.generativeai as genai
import io # <-- MUDANÇA: Necessário para trabalhar com arquivos em memória

# --- Configuração do Modelo Gemini ---
# A maneira correta de acessar secrets na Streamlit Cloud
try:
    # <-- MUDANÇA: Usando st.secrets em vez de os.environ
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    # <-- MUDANÇA: Mensagem de erro mais apropriada para o ambiente
    st.error("Erro ao configurar a API do Gemini. Verifique se você configurou o GOOGLE_API_KEY nos Secrets do seu app no Streamlit Cloud.")
    st.error(f"Detalhes do erro: {e}")
    st.stop()


# --- Funções "Ferramenta" Otimizadas para Memória ---

# <-- MUDANÇA: Função totalmente reescrita para operar em memória
def carregar_csv_de_zip_em_memoria(arquivo_zip_em_memoria):
    """
    Lê um arquivo .zip em memória, encontra o primeiro arquivo .csv dentro dele,
    e o carrega em um DataFrame Pandas.
    """
    try:
        with zipfile.ZipFile(arquivo_zip_em_memoria, 'r') as z:
            # Encontra o primeiro arquivo .csv na lista de arquivos do zip
            nome_csv = next((nome for nome in z.namelist() if nome.lower().endswith('.csv')), None)
            
            if nome_csv:
                st.info(f"Arquivo CSV encontrado no zip: '{nome_csv}'")
                # Lê o arquivo CSV de dentro do zip diretamente para a memória
                with z.open(nome_csv) as f:
                    try:
                        # Tenta ler com a codificação mais comum
                        df = pd.read_csv(f, encoding='utf-8', on_bad_lines='skip')
                    except UnicodeDecodeError:
                        # Se falhar, tenta com outra codificação comum
                        # Precisamos "rebobinar" o leitor de arquivo em memória
                        f.seek(0)
                        df = pd.read_csv(f, encoding='latin1', on_bad_lines='skip')
                    st.success("Dados carregados com sucesso!")
                    return df
            else:
                st.error("Nenhum arquivo .csv foi encontrado dentro do .zip.")
                return None
    except Exception as e:
        st.error(f"Ocorreu um erro ao processar o arquivo zip: {e}")
        return None

# --- Interface Gráfica (Streamlit) ---

st.set_page_config(layout="wide", page_title="Agente CSV-Analyst")
st.title("🤖 Agente CSV-Analyst")
st.write("Faça o upload de um arquivo .zip contendo um CSV e faça uma pergunta sobre seus dados.")

# <-- MUDANÇA: Toda a lógica de criar pastas foi removida.

arquivo_zip_carregado = st.file_uploader(
    "1. Faça o upload do seu arquivo .zip", type=['zip']
)

pergunta_usuario = st.text_input(
    "2. Faça sua pergunta em linguagem natural sobre os dados do CSV"
)

if st.button("Analisar e Responder"):
    if arquivo_zip_carregado is not None and pergunta_usuario:
        with st.spinner("O Agente está trabalhando..."):
            
            # <-- MUDANÇA: Chamamos a nova função que opera em memória
            df = carregar_csv_de_zip_em_memoria(arquivo_zip_carregado)

            # A lógica a seguir só executa se o DataFrame foi carregado com sucesso
            if df is not None:
                st.write("Amostra dos dados:")
                st.dataframe(df.head())

                st.info("Agente: Usando Gemini para gerar o código de análise...")

                prompt_gerador_codigo = f"""
                Você é um especialista em análise de dados com Python e Pandas.
                O usuário tem um DataFrame pandas chamado `df`.
                As colunas do DataFrame são: {list(df.columns)}
                A pergunta do usuário é: "{pergunta_usuario}"

                Sua tarefa é gerar APENAS o código Python (usando o DataFrame `df`) que responde a essa pergunta.
                O resultado final do seu código deve ser armazenado em uma variável chamada `resultado`.
                Não inclua explicações, apenas o código. Não use `print()`. Não inclua os marcadores de código ```python ou ```.
                """
                
                try:
                    resposta_gemini = model.generate_content(prompt_gerador_codigo)
                    codigo_gerado = resposta_gemini.text.strip()

                    st.write("Código de análise gerado pelo Gemini:")
                    st.code(codigo_gerado, language='python')

                    namespace = {'df': df}
                    exec(codigo_gerado, namespace)
                    resultado_bruto = namespace['resultado']

                    st.success("Código executado com sucesso!")
                    st.write("Resultado da análise (bruto):")
                    st.write(resultado_bruto)

                    st.info("Agente: Usando Gemini para criar uma resposta final clara...")

                    prompt_sintetizador = f"""
                    Você é um assistente de IA prestativo.
                    Com base na pergunta original do usuário e no resultado da análise de dados, forneça uma resposta clara e concisa em português.

                    Pergunta Original: "{pergunta_usuario}"
                    Resultado da Análise: "{resultado_bruto}"

                    Sua Resposta:
                    """
                    
                    resposta_final_gemini = model.generate_content(prompt_sintetizador)
                    resposta_final = resposta_final_gemini.text

                    st.markdown("---")
                    st.header("✅ Resposta do Agente:")
                    st.markdown(f"### {resposta_final}")

                except Exception as e:
                    st.error(f"Ocorreu um erro durante a execução da IA: {e}")
                    st.warning("O Agente pode ter gerado um código inválido ou a chamada à API falhou. Tente reformular sua pergunta.")

    else:
        st.warning("Por favor, faça o upload de um arquivo .zip e digite uma pergunta.")
