# I2A2
# 🍏 Data Insights Agent

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.33-ff4b4b.svg)](https://streamlit.io)
[![Made with Gemini](https://img.shields.io/badge/Made%20with-Gemini%20AI-8A2BE2.svg)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Um assistente de IA conversacional que transforma seus arquivos CSV em insights estratégicos. Construído com uma arquitetura multi-agente e uma interface minimalista, este não é apenas um leitor de dados, é seu parceiro de análise.

---

### ✨ Features Principais

*   **Análise Inteligente de Onboarding:** Ao carregar um arquivo, um agente especializado analisa seus dados e sugere perguntas estratégicas para iniciar a conversa.
*   **Interface de Chat Conversacional:** Faça perguntas em linguagem natural e receba respostas claras e contextualizadas.
*   **Arquitetura Multi-Agente:** Uma equipe de agentes de IA colabora nos bastidores para entender sua pergunta, gerar o código de análise, executar e sintetizar a resposta.
*   **Design Minimalista e Responsivo:** Uma interface limpa e elegante, inspirada na filosofia de design da Apple, que funciona perfeitamente em desktop e mobile.
*   **Seguro e Adaptável:** O código é projetado para rodar tanto em um ambiente de desenvolvimento local (usando arquivos `.env`) quanto em produção na nuvem (usando `st.secrets`).

### 🚀 Demonstração

[SUGESTÃO] Grave um GIF curto mostrando o fluxo: carregar um arquivo, ver as perguntas sugeridas, fazer uma nova pergunta e receber a resposta. Use ferramentas como [LiceCAP](https://www.cockos.com/licecap/) ou [Giphy Capture](https://giphy.com/apps/giphycapture). Depois, substitua a linha abaixo pelo seu GIF.

![Demo do Data Insights Agent](https://i.imgur.com/link_para_seu_gif_aqui.gif)

### 🛠️ Como Rodar Localmente (Para Desenvolvedores)

Siga estes passos para rodar o projeto em seu próprio ambiente.

**1. Pré-requisitos:**
*   [Python 3.10](https://www.python.org/downloads/) ou superior
*   [Git](https://git-scm.com/)

**2. Clone o Repositório:**
```bash
git clone https://github.com/seu-usuario/seu-repositorio.git
cd seu-repositorio
```

**3. Crie e Ative um Ambiente Virtual:**
É uma forte recomendação usar um ambiente virtual para isolar as dependências do projeto.
```bash
# Crie o ambiente
python3 -m venv .venv

# Ative o ambiente (Linux/Mac)
source .venv/bin/activate

# Ative o ambiente (Windows)
# .venv\Scripts\activate
```

**4. Instale as Dependências:**
```bash
pip install -r requirements.txt
```

**5. Configure sua Chave da API do Gemini:**
*   Crie um arquivo chamado `.env` na raiz do projeto.
*   Adicione sua chave da API do Google Gemini a este arquivo no seguinte formato:
    ```
    GOOGLE_API_KEY="SUA_CHAVE_SECRETA_REAL_VAI_AQUI"
    ```
*   **Importante:** O arquivo `.env` já está listado no `.gitignore` para garantir que sua chave secreta nunca seja enviada para o GitHub.

**6. Execute o Aplicativo Streamlit:**
```bash
streamlit run app.py
```
Abra seu navegador no endereço `http://localhost:8501`.

### ☁️ Deploy na Streamlit Community Cloud

Este aplicativo está pronto para ser publicado na nuvem gratuitamente.

1.  Envie seu projeto para um repositório público no GitHub.
2.  Cadastre-se na [Streamlit Community Cloud](https://share.streamlit.io/) com sua conta do GitHub.
3.  Clique em "New app" e selecione seu repositório.
4.  Antes de fazer o deploy, vá em "Advanced settings..." e adicione sua `GOOGLE_API_KEY` na seção "Secrets", no mesmo formato que o arquivo `.env`.

### 💻 Tech Stack

*   **Linguagem:** Python
*   **Framework da Interface:** Streamlit
*   **Manipulação de Dados:** Pandas
*   **Modelo de IA:** Google Gemini Pro
