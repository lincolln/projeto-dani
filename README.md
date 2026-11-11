# Sistema Kanemberg v2 — Gestão de Loja, Estoque, PDV & App Mobile (PWA)

Sistema comercial completo desenvolvido para a **Kanemberg Multimarcas**, integrando **Painel Desktop Widescreen** (`/sistema`) para o computador do caixa e **Aplicativo Mobile PWA Offline-First** (`/app`) para atendimento rápido, consulta de estoque, leitura de etiquetas QR Code (`KNB...`), PDV e controle de Fiado/Crediário.

---

## Parte 1 — Como Baixar e Instalar no Computador da Loja (Windows)

### 1. Pré-requisitos Rápidos
1. **Python 3.10 ou superior** instalado no Windows ([python.org/downloads](https://www.python.org/downloads/)).
   - **Importante:** Na primeira tela do instalador do Python, marque a caixa **`Add python.exe to PATH`** antes de clicar em *Install Now*.
2. **Git para Windows** instalado ([git-scm.com](https://git-scm.com/download/win)) — *opcional, recomendado para sincronização automática do túnel mobile*.

---

### 2. Como Baixar o Sistema

- **Opção A (Via Git no Terminal — Recomendado):**
  Abra o Prompt de Comando ou PowerShell na Área de Trabalho e execute:
  ```bash
  git clone https://github.com/lincolln/projeto-dani.git
  cd projeto-dani
  ```

- **Opção B (Download Direto em ZIP):**
  1. Acesse **`https://github.com/lincolln/projeto-dani`** no navegador.
  2. Clique no botão verde **`<> Code`** no topo direito da página e selecione **`Download ZIP`**.
  3. Extraia a pasta na **Área de Trabalho** ou em **`C:\Kanemberg`**.

---

### 3. Instalação das Dependências (Apenas na 1ª Vez)
Abra o terminal (Prompt de Comando ou PowerShell) dentro da pasta do projeto e execute:

```bash
pip install -r requirements.txt
```

*(Dica: você também pode dar 2 cliques no arquivo `1_instalar_no_cliente.bat` na primeira vez para instalar os pacotes e criar o atalho na Área de Trabalho automaticamente).*

---

### 4. Como Abrir e Entrar no Sistema do Computador (Dia a Dia)
1. Na pasta do projeto, dê **2 cliques** no arquivo **`Iniciar_Kanemberg.bat`** (recomendamos clicar com o botão direito nele ➔ **Enviar para ➔ Área de trabalho (criar atalho)** para facilitar o uso diário).
2. **Permissão do Firewall (1ª vez):** Se o Windows Defender Firewall exibir uma janela perguntando sobre o Python/`cloudflared`, marque as duas caixas (**Redes privadas** e **Redes públicas**) e clique em **`Permitir acesso`**.
3. O sistema iniciará o servidor em segundo plano e abrirá automaticamente o **Painel Administrativo Kanemberg v2** em janela dedicada de aplicativo:
   - Endereço local do Caixa: **`http://localhost:8000/sistema`**

---

## Parte 2 — Como Baixar e Entrar no Aplicativo do Celular (Android / iOS)

O sistema conta com um **App Mobile PWA (Progressive Web App)** com tecnologia **Offline-First e Reconexão Automática**, permitindo vender pelo celular usando a câmera como leitor de código QR, consultar estoque em tempo real e gerenciar o fiado.

### Passo 1 — No Computador do Caixa
1. Com o sistema aberto no computador, clique no botão **`Conexão & Servidor`** (localizado no canto inferior esquerdo da barra lateral).
2. Verifique se a chave **`Acesso Mobile`** está ligada (**`ON`**).
3. Aguarde alguns segundos até o **QR Code HTTPS (Cloudflare)** aparecer na tela (caso necessário, clique em **`Iniciar / Reiniciar Túnel Cloudflare`**).

---

### Passo 2 — Instalar o Aplicativo no Celular (Feito Apenas na 1ª Vez)
1. Abra a **câmera do celular** e aponte para o **QR Code** exibido na tela do computador.
2. Toque no link **`https://...trycloudflare.com`** que aparecerá na câmera para abri-lo no navegador (**Chrome** no Android ou **Safari** no iPhone/iOS).
3. Instale o aplicativo na tela inicial:
   - **No Android (Chrome):** Toque no banner **`Instalar Aplicativo`** ou abra o menu de **3 pontinhos (⋮)** no canto superior direito e toque em **`Instalar aplicativo`** (ou *Adicionar à tela inicial*).
   - **No iPhone (Safari):** Toque no botão **Compartilhar** (ícone de quadrado com seta para cima na barra inferior) e selecione **`Adicionar à Tela de Início`**.
4. Pronto! O aplicativo **Kanemberg** será instalado na tela inicial do seu celular como um aplicativo nativo em tela cheia (sem barra de endereço do navegador).

---

### Passo 3 — Como Entrar no Aplicativo Mobile (Credenciais de Acesso)
1. Abra o aplicativo **Kanemberg** na tela inicial do celular.
2. Na tela de login, preencha os campos **Operador** e **Código de Acesso** conforme o perfil desejado e toque em **`Acessar Painel`**:

| Perfil de Acesso | Operador (Usuário) | Código de Acesso (Senha) | Permissões no Aplicativo |
| :--- | :--- | :--- | :--- |
| **Administrador / Caixa** | `admin` | `Kanemberg@2026` | Acesso completo (Vendas, Estoque, Cadastro, Fiado e Resumo Financeiro) |
| **Vendedor(a)** | `vendedor` | `Loja@2026` | Acesso operacional de loja (PDV/Vendas, Consulta de Estoque e Fiado) |

> **Nota:** Caso deseje personalizar os usuários ou senhas da loja, basta editar o arquivo `.env` na pasta principal do computador (variáveis `ADMIN_USER`, `ADMIN_PASS`, `VENDEDOR_USER` e `VENDEDOR_PASS`).

---

### Passo 4 — Como Funciona nos Dias Seguintes (Reconexão Automática)
- **Você NÃO precisa instalar o aplicativo novamente nos dias seguintes.**
- Todos os dias, ao ligar o computador da loja e abrir o **`Iniciar_Kanemberg.bat`**, basta tocar no ícone do aplicativo **Kanemberg** já instalado no celular:
  1. O aplicativo abre instantaneamente (mesmo que o link do túnel do dia anterior tenha mudado).
  2. Em segundo plano, ele consulta automaticamente o **Porteiro Inteligente** e a rede Wi-Fi da loja, conectando-se sozinho ao novo endereço do dia sem precisar ler QR Code novamente.
  3. **Sincronização Manual de Emergência:** Se a internet da loja oscilar ou você trocar de roteador, basta tocar no botão **`Sincronizar via QR Code / Wi-Fi`** na tela de login do celular e apontar a câmera para o QR Code do computador.

---

## Estrutura Principal do Projeto

- **`Iniciar_Kanemberg.bat`** — Inicializador diário do sistema no computador do caixa.
- **`api_mobile.py`** — Servidor FastAPI unificado (Desktop + Mobile PWA + Gerenciador de Túnel Cloudflare + Backup SQLite).
- **`loja_daniel_v2.db`** — Banco de dados SQLite local em modo WAL de alta performance.
- **`static_sistema/`** — Interface Desktop Widescreen (`/sistema`) com Estoque, Cadastro Camaleão, PDV, Fiado e Dashboard Executivo.
- **`static/`** — Aplicativo Mobile PWA (`/app`) com Service Worker Offline-First e leitor de QR Code.
- **`docs/`** — Porteiro Inteligente HTTPS (GitHub Pages) para descoberta automática do túnel diário.
