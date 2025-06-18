# 🍏 Data Insights Pro

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.33-ff4b4b.svg)](https://streamlit.io)
[![Made with Gemini 1.5](https://img.shields.io/badge/Made%20with-Gemini%201.5-8A2BE2.svg)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Um **parceiro de análise de dados autônomo** que transforma seus arquivos CSV em insights estratégicos e visualizações claras. Construído com uma arquitetura multi-agente avançada, este aplicativo não apenas responde perguntas, mas também pensa, analisa e guia você através dos seus dados.

---

### ✨ Features Avançadas

*   **Análise Exploratória Proativa:** Ao carregar um arquivo, um agente especializado realiza uma Análise Exploratória de Dados (EDA), apresentando um resumo estatístico, insights iniciais e sugerindo caminhos de investigação.
*   **Geração de Visualizações:** Peça gráficos em linguagem natural! O agente entende sua intenção e gera visualizações (gráficos de barras, histogramas, etc.) para ilustrar os dados.
*   **Agente Roteador Inteligente:** Um "cérebro" central analisa cada pergunta e decide a melhor ferramenta para a tarefa, seja um cálculo com Pandas ou uma visualização com Matplotlib/Seaborn.
*   **Memória Conversacional:** O agente mantém o contexto da conversa, permitindo perguntas de acompanhamento de forma natural (ex: "E por categoria?").
*   **Interface de Chat Intuitiva:** Uma experiência de usuário limpa e focada, projetada para uma interação fluida e direta.

### 🚀 Demonstração

[SUGESTÃO] Grave um novo GIF que mostre o fluxo aprimorado:
1.  Upload do arquivo.
2.  Aparecimento da análise proativa e das perguntas sugeridas.
3.  Você faz uma pergunta que gera um gráfico.
4.  Você faz uma pergunta de acompanhamento que gera um número.

![Demo do Data Insights Pro](https://i.imgur.com/link_para_seu_novo_gif.gif)

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
```bash
# Crie o ambiente
python3 -m venv .venv

# Ative o ambiente (Linux/Mac)
source .venv/bin/activate

# Ative o ambiente (Windows)
# .venv\Scripts\activate
```

**4. Instale as Dependências:**
**Importante:** O novo `requirements.txt` contém bibliotecas de visualização.
```bash
pip install -r requirements.txt
```

**5. Configure sua Chave da API do Gemini:**
*   Crie um arquivo chamado `.env` na raiz do projeto.
*   Adicione sua chave da API do Google Gemini a este arquivo:
    ```
    GOOGLE_API_KEY="SUA_CHAVE_SECRETA_REAL_VAI_AQUI"
    ```
*   O arquivo `.env` já está no `.gitignore` para proteger sua chave.

**6. Execute o Aplicativo Streamlit:**
```bash
streamlit run app.py
```
Abra seu navegador no endereço `http://localhost:8501`.

### ☁️ Deploy na Streamlit Community Cloud

Este aplicativo está pronto para ser publicado na nuvem gratuitamente.

1.  Envie seu projeto para um repositório público no GitHub (certifique-se de que o `.gitignore` está protegendo seu `.env`).
2.  Cadastre-se na [Streamlit Community Cloud](https://share.streamlit.io/).
3.  Clique em "New app" e selecione seu repositório.
4.  Antes de fazer o deploy, vá em "Advanced settings..." e adicione sua `GOOGLE_API_KEY` na seção "Secrets".

### 💻 Tech Stack

*   **Linguagem:** Python
*   **Framework da Interface:** Streamlit
*   **Manipulação de Dados:** Pandas
*   **Visualização de Dados:** Matplotlib, Seaborn
*   **Modelo de IA:** Google Gemini 1.5 flash latestesro
