# WakeAPP 🦉🚗💤  

> Monitoramento de sonolência em motoristas – 2º Lugar no **Hackathon UniAnchieta 2025**  

## 📖 Sobre o Projeto  

O **WakeAPP** é um aplicativo de **monitoramento facial em tempo real**, desenvolvido durante o **Hackathon UniAnchieta 2025**.  
Nosso objetivo é **reduzir os acidentes de trânsito causados por sonolência e fadiga**, que juntos representam cerca de **60% dos acidentes**.  

### 🔑 Funcionalidades principais:
- 👁️ **Detecção de sonolência**: o sistema monitora se o motorista mantém os olhos fechados por **mais de 2 segundos**.  
- 🔊 **Alerta sonoro**: dispara um aviso imediato para despertar o condutor.  
- 📩 **Notificações automáticas**: envia mensagem para **WhatsApp** e **e-mail de emergência** cadastrados.  
- 📊 **Histórico de ocorrências**: armazena dados sobre os episódios de sonolência, incluindo:
  - Data  
  - Hora  
  - Local (via geolocalização)  
  - Tempo de olhos fechados  



## 🛠️ Tecnologias utilizadas  

- **Python** 🐍  
- **OpenCV** → para reconhecimento e monitoramento facial  
- **Flet** → interface do aplicativo  
- **Mediapipe** → detecção de rosto e olhos  
- **n8n** → automação de notificações (WhatsApp e e-mail)  
- **Requests** → integração com webhooks  
- **Threading & AsyncIO** → execução paralela de tarefas  


## 🚀 Como executar o projeto  

### 1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/wakeapp.git
cd wakeapp
```
### 2. Crie um ambiente virtual e instale as dependências:
```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

pip install -r requirements.txt
```
### 3. Configure os webhooks do n8n:
```bash
N8N_REGISTER_WEBHOOK_URL = "sua-url-do-webhook-register"
N8N_LOGIN_WEBHOOK_URL = "sua-url-do-webhook-login"
```
### 4. Configure os webhooks do n8n:
```bash
python app.py
```
