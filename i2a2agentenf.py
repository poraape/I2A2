# Commented out IPython magic to ensure Python compatibility.
# %%writefile app.py
# 
# import streamlit as st
# import pandas as pd
# import os
# import zipfile
# import google.generativeai as genai
# 
# # --- Configuração do Modelo Gemini ---
# # A API Key já foi configurada como variável de ambiente no Colab
# try:
#     GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
#     genai.configure(api_key=GOOGLE_API_KEY)
#     model = genai.GenerativeModel('gemini-1.5-flash')
# except Exception as e:
#     st.error(f"Erro ao configurar a API do Gemini. Verifique se a API Key está correta nos Secrets do Colab. Detalhes: {e}")
#     st.stop()
# 
# 
# # --- Funções "Ferramenta" do nosso Agente ---
# 
# def descompactar_arquivo(caminho_zip, pasta_destino):
#     """Ferramenta 1: Descompacta um arquivo .zip para uma pasta de destino."""
#     if not os.path.exists(pasta_destino):
#         os.makedirs(pasta_destino)
#     try:
#         with zipfile.ZipFile(caminho_zip, 'r') as zip_ref:
#             zip_ref.extractall(pasta_destino)
#         st.info(f"Arquivo descompactado em '{pasta_destino}'")
#         return pasta_destino
#     except Exception as e:
#         st.error(f"Erro ao descompactar o arquivo: {e}")
#         return None
# 
# def encontrar_csv(pasta):
#     """Ferramenta 2: Encontra o primeiro arquivo .csv em uma pasta."""
#     try:
#         for arquivo in os.listdir(pasta):
#             if arquivo.lower().endswith('.csv'):
#                 caminho_completo = os.path.join(pasta, arquivo)
#                 st.info(f"Arquivo CSV encontrado: '{arquivo}'")
#                 return caminho_completo
#     except Exception as e:
#         st.error(f"Erro ao procurar o arquivo CSV: {e}")
#     return None
# 
# def carregar_dados(caminho_csv):
#     """Ferramenta 3: Carrega os dados de um CSV para um DataFrame Pandas."""
#     try:
#         df = pd.read_csv(caminho_csv, encoding='utf-8', on_bad_lines='skip')
#     except UnicodeDecodeError:
#         df = pd.read_csv(caminho_csv, encoding='latin1', on_bad_lines='skip')
#     st.success("Dados carregados com sucesso!")
#     return df
# 
# # --- Interface Gráfica (Streamlit) ---
# 
# st.set_page_config(layout="wide", page_title="Agente CSV-Analyst")
# st.title("🤖 Agente CSV-Analyst")
# st.write("Faça o upload de um arquivo .zip contendo um CSV e faça uma pergunta sobre seus dados.")
# 
# PASTA_UPLOADS = "uploads"
# PASTA_DADOS = "dados_descompactados"
# 
# if not os.path.exists(PASTA_UPLOADS):
#     os.makedirs(PASTA_UPLOADS)
# 
# arquivo_zip_carregado = st.file_uploader(
#     "1. Faça o upload do seu arquivo .zip", type=['zip']
# )
# 
# pergunta_usuario = st.text_input(
#     "2. Faça sua pergunta em linguagem natural sobre os dados do CSV"
# )
# 
# if st.button("Analisar e Responder"):
#     if arquivo_zip_carregado is not None and pergunta_usuario:
#         with st.spinner("O Agente está trabalhando..."):
#             caminho_zip = os.path.join(PASTA_UPLOADS, arquivo_zip_carregado.name)
#             with open(caminho_zip, "wb") as f:
#                 f.write(arquivo_zip_carregado.getbuffer())
# 
#             pasta_descompactada = descompactar_arquivo(caminho_zip, PASTA_DADOS)
# 
#             if pasta_descompactada:
#                 caminho_csv = encontrar_csv(pasta_descompactada)
# 
#                 if caminho_csv:
#                     df = carregar_dados(caminho_csv)
#                     st.write("Amostra dos dados:")
#                     st.dataframe(df.head())
# 
#                     st.info("Agente: Usando Gemini para gerar o código de análise...")
# 
#                     prompt_gerador_codigo = f"""
#                     Você é um especialista em análise de dados com Python e Pandas.
#                     O usuário tem um DataFrame pandas chamado `df`.
#                     As colunas do DataFrame são: {list(df.columns)}
#                     A pergunta do usuário é: "{pergunta_usuario}"
# 
#                     Sua tarefa é gerar APENAS o código Python (usando o DataFrame `df`) que responde a essa pergunta.
#                     O resultado final do seu código deve ser armazenado em uma variável chamada `resultado`.
#                     Não inclua explicações, apenas o código. Não use `print()`. Não inclua os marcadores de código ```python ou ```.
#                     """
# 
#                     resposta_gemini = model.generate_content(prompt_gerador_codigo)
#                     codigo_gerado = resposta_gemini.text.strip()
# 
#                     st.write("Código de análise gerado pelo Gemini:")
#                     st.code(codigo_gerado, language='python')
# 
#                     try:
#                         namespace = {'df': df}
#                         exec(codigo_gerado, namespace)
#                         resultado_bruto = namespace['resultado']
# 
#                         st.success("Código executado com sucesso!")
#                         st.write("Resultado da análise (bruto):")
#                         st.write(resultado_bruto)
# 
#                         st.info("Agente: Usando Gemini para criar uma resposta final clara...")
# 
#                         prompt_sintetizador = f"""
#                         Você é um assistente de IA prestativo.
#                         Com base na pergunta original do usuário e no resultado da análise de dados, forneça uma resposta clara e concisa em português.
# 
#                         Pergunta Original: "{pergunta_usuario}"
#                         Resultado da Análise: "{resultado_bruto}"
# 
#                         Sua Resposta:
#                         """
# 
#                         resposta_final_gemini = model.generate_content(prompt_sintetizador)
#                         resposta_final = resposta_final_gemini.text
# 
#                         st.markdown("---")
#                         st.header("✅ Resposta do Agente:")
#                         st.markdown(f"### {resposta_final}")
# 
#                     except Exception as e:
#                         st.error(f"Ocorreu um erro ao executar o código gerado: {e}")
#                         st.warning("O Agente pode ter gerado um código inválido. Tente reformular sua pergunta.")
# 
#                 else:
#                     st.error("Nenhum arquivo .csv foi encontrado no .zip fornecido.")
#     else:
#         st.warning("Por favor, faça o upload de um arquivo .zip e digite uma pergunta.")

