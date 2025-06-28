import flet as ft
import threading
import deteccao
import asyncio
import winsound
import requests # Importar a biblioteca requests para fazer requisições HTTP

# URLs dos seus webhooks do n8n. Você DEVE substituir estas URLs pelas suas URLs reais do n8n.
N8N_REGISTER_WEBHOOK_URL = "https://driver777.app.n8n.cloud/webhook-test/register"
N8N_LOGIN_WEBHOOK_URL = "https://driver777.app.n8n.cloud/webhook-test/login"

users_db = {}
ligado = False
usuario_logado = ""

# Funções simuladas para deteccao (seção "deteccao")
# No seu ambiente real, 'deteccao' seria um módulo separado.    
class DeteccaoSimulada:
    def __init__(self):
        self.camera_ativa = False

    def start_camera_detection(self):
        print("Detecção da câmera iniciada (simulado).")
        while self.camera_ativa:
            # Simula algum trabalho da câmera
            asyncio.sleep(1)
        print("Detecção da câmera parada (simulado).")

deteccao = DeteccaoSimulada()

# Função para enviar dados para o webhook de registro do n8n
def send_registration_to_n8n(username, password):
    """
    Envia dados de registro para o webhook de registro do n8n.
    """
    payload = {
        "eventType": "cadastro",
        "username": username,
        "password": password
    }
    
    try:
        response = requests.post(N8N_REGISTER_WEBHOOK_URL, json=payload, timeout=5)
        response.raise_for_status() # Lança um HTTPError para respostas de erro (4xx ou 5xx)
        print(f"Dados de registro enviados para n8n com sucesso: {response.status_code}")
        print(f"Resposta n8n: {response.text}")
    except requests.exceptions.Timeout:
        print("Erro: A requisição de registro para o n8n expirou.")
    except requests.exceptions.ConnectionError:
        print("Erro: Não foi possível conectar ao servidor de registro n8n. Verifique a URL e sua conexão.")
    except requests.exceptions.HTTPError as err:
        print(f"Erro HTTP ao enviar dados de registro para n8n: {err}")
    except Exception as e:
        print(f"Ocorreu um erro inesperado ao enviar dados de registro para n8n: {e}")

# Função para enviar dados para o webhook de login do n8n
def send_login_to_n8n(username):
    """
    Envia dados de login para o webhook de login do n8n.
    """
    payload = {
        "eventType": "login",
        "username": username
    }
    
    try:
        response = requests.post(N8N_LOGIN_WEBHOOK_URL, json=payload, timeout=5)
        response.raise_for_status() # Lança um HTTPError para respostas de erro (4xx ou 5xx)
        print(f"Dados de login enviados para n8n com sucesso: {response.status_code}")
        print(f"Resposta n8n: {response.text}")
    except requests.exceptions.Timeout:
        print("Erro: A requisição de login para o n8n expirou.")
    except requests.exceptions.ConnectionError:
        print("Erro: Não foi possível conectar ao servidor de login n8n. Verifique a URL e sua conexão.")
    except requests.exceptions.HTTPError as err:
        print(f"Erro HTTP ao enviar dados de login para n8n: {err}")
    except Exception as e:
        print(f"Ocorreu um erro inesperado ao enviar dados de login para n8n: {e}")


async def main(page: ft.Page):
    global usuario_logado

    menu_aberto = False
    menu_container = None
    main_view = None

    status_btn = ft.ElevatedButton(text="LIGAR", bgcolor="red", color="white")
    status_label = ft.Text("Desligado", size=20)

    def navegar_para(tela):
        nonlocal main_view
        main_view = tela
        page.views.clear()
        page.views.append(tela)
        page.update()

    async def mostrar_splash():
        splash_view = ft.View(
            "/splash",
            controls=[
                ft.Image(src="logo_inicio.png", width=600, height=600)
            ],
            vertical_alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        navegar_para(splash_view)
        await asyncio.sleep(3)
        navegar_para(login_view)

    def toggle_ligado(e):
        global ligado
        ligado = not ligado
        status_btn.text = "DESLIGAR" if ligado else "LIGAR"
        status_btn.bgcolor = "green" if ligado else "red"
        status_label.value = "Ligado" if ligado else "Desligado"
        page.update()

        if ligado:
            deteccao.camera_ativa = True
            threading.Thread(
                target=deteccao.start_camera_detection, daemon=True).start()
        else:
            deteccao.camera_ativa = False
            winsound.PlaySound(None, winsound.SND_PURGE)

    def logout(e):
        nonlocal menu_aberto, menu_container, main_view
        global usuario_logado
        usuario_logado = ""
        menu_aberto = False
        if menu_container and menu_container in main_view.controls[0].controls:
            main_view.controls[0].controls.remove(menu_container)
            menu_container = None
        navegar_para(login_view)

    def toggle_menu(e):
        nonlocal menu_aberto, menu_container, main_view
        menu_aberto = not menu_aberto
        stack = main_view.controls[0]

        if menu_aberto:
            menu_container = ft.Container(
                content=ft.Column(
                    [
                        ft.Text(f"Olá, {usuario_logado}",
                                weight=ft.FontWeight.BOLD),
                        ft.TextButton("Logoff", on_click=logout),
                    ],
                    tight=True,
                    alignment=ft.MainAxisAlignment.START,
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                ),
                bgcolor="white",
                border=ft.border.all(1, "black"),
                padding=10,
                width=150,
                left=0,
                top=40,
                alignment=ft.alignment.top_left,
            )
            stack.controls.append(menu_container)
        else:
            if menu_container and menu_container in stack.controls:
                stack.controls.remove(menu_container)
                menu_container = None
        page.update()

    def criar_main_view():
        nonlocal menu_aberto, menu_container
        menu_aberto = False
        menu_container = None

        status_btn.on_click = toggle_ligado

        return ft.View(
            "/main",
            [
                ft.Stack(
                    [
                        # Conteúdo central realmente centralizado
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text("Bem-vindo!", size=30,
                                            weight=ft.FontWeight.BOLD),
                                    status_label,
                                    status_btn,
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                tight=True,
                            ),
                            alignment=ft.alignment.center,
                            expand=True,  # Preenche o Stack
                        ),
                        # Topo com botão menu e nome do app
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.TextButton(
                                        "☰",
                                        tooltip="Menu",
                                        on_click=toggle_menu
                                    ),
                                    ft.Text("WakeApp", size=20,
                                            weight=ft.FontWeight.BOLD),
                                ],
                                alignment=ft.MainAxisAlignment.START,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            left=0,
                            top=0,
                            alignment=ft.alignment.top_left,
                        )
                    ],
                    expand=True  # ESSENCIAL: o Stack agora ocupa toda a tela
                )
            ]
        )

    # ========== LOGIN ==========
    login_usuario = ft.TextField(label="Usuário")
    login_senha = ft.TextField(
        label="Senha", password=True, can_reveal_password=True)
    login_mensagem = ft.Text("")

    def tentar_login(e):
        global usuario_logado
        usuario = login_usuario.value
        senha = login_senha.value
        if usuario in users_db and users_db[usuario] == senha:
            usuario_logado = usuario
            navegar_para(criar_main_view())
            # Enviar dados de login para o n8n
            send_login_to_n8n(usuario)
        else:
            login_mensagem.value = "Usuário ou senha incorretos."
            page.update()

    def ir_para_cadastro(e):
        navegar_para(cadastro_view)

    login_view = ft.View(
        "/login",
        [
            ft.Column(
                [
                    ft.Image(src="logo_login.png", width=250, height=250),
                    ft.Text("Login", size=30, weight=ft.FontWeight.BOLD),
                    login_usuario,
                    login_senha,
                    ft.ElevatedButton("Entrar", on_click=tentar_login),
                    ft.TextButton("Cadastrar", on_click=ir_para_cadastro),
                    login_mensagem,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            )
        ],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # ========== CADASTRO ==========
    cadastro_usuario = ft.TextField(label="Novo Usuário")
    cadastro_senha = ft.TextField(
        label="Nova Senha", password=True, can_reveal_password=True)
    cadastro_mensagem = ft.Text("")

    def cadastrar_usuario(e):
        usuario = cadastro_usuario.value
        senha = cadastro_senha.value
        if usuario and senha:
            if usuario in users_db:
                cadastro_mensagem.value = "Usuário já existe!"
            else:
                users_db[usuario] = senha
                cadastro_mensagem.value = "Cadastro realizado com sucesso!"
                # Enviar dados de cadastro para o n8n
                send_registration_to_n8n(usuario, senha)
        else:
            cadastro_mensagem.value = "Preencha todos os campos!"
        page.update()

    def voltar_login(e):
        navegar_para(login_view)

    cadastro_view = ft.View(
        "/cadastro",
        [
            ft.Column(
                [
                    ft.Image(src="logo_login.png", width=150, height=150),
                    ft.Text("Cadastro", size=30, weight=ft.FontWeight.BOLD),
                    cadastro_usuario,
                    cadastro_senha,
                    ft.ElevatedButton("Cadastrar", on_click=cadastrar_usuario),
                    ft.TextButton("Voltar", on_click=voltar_login),
                    cadastro_mensagem,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            )
        ],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Configurações da janela
    page.window_width = 375
    page.window_height = 667
    page.window_min_width = 375
    page.window_min_height = 667
    page.window_max_width = 375
    page.window_max_height = 667
    page.window_resizable = False
    page.title = "WakeApp"

    await mostrar_splash()

if __name__ == "__main__":
    # Certifique-se de que a biblioteca 'requests' está instalada: pip install requests
    asyncio.run(ft.app_async(target=main))
