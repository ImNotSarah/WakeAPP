import deteccao
import flet as ft
import threading
import asyncio
import winsound
import requests
import sqlite3

# Conectar (ou criar) o banco de dados
conn = sqlite3.connect("usuarios.db", check_same_thread=False)
cursor = conn.cursor()

# Criar tabela de usuários
cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
""")

# Criar tabela de contatos de emergência
cursor.execute("""
    CREATE TABLE IF NOT EXISTS contatos_emergencia (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL,
        whatsapp TEXT NOT NULL,
        FOREIGN KEY (username) REFERENCES usuarios(username)
    )
""")
# Criar tabela de ocorrências
cursor.execute("""
    CREATE TABLE IF NOT EXISTS ocorrencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        data TEXT NOT NULL,
        hora TEXT NOT NULL,
        tempo_olhos_fechados TEXT NOT NULL,
        FOREIGN KEY (username) REFERENCES usuarios(username)
    )
""")


conn.commit()

# URLs dos seus webhooks do n8n
N8N_REGISTER_WEBHOOK_URL = "https://driver777.app.n8n.cloud/webhook-test/register"
N8N_LOGIN_WEBHOOK_URL = "https://driver777.app.n8n.cloud/webhook-test/001e479f-3e5f-421b-981f-c97fcabc0466"

ligado = False
usuario_logado = ""


def send_registration_to_n8n(username, password):
    payload = {
        "eventType": "cadastro",
        "username": username,
        "password": password
    }
    try:
        response = requests.post(
            N8N_REGISTER_WEBHOOK_URL, json=payload, timeout=5)
        response.raise_for_status()
        print(f"Dados de registro enviados: {response.status_code}")
    except Exception as e:
        print(f"Erro no envio de registro: {e}")


def send_login_to_n8n(username):
    payload = {
        "eventType": "login",
        "username": username
    }
    try:
        response = requests.post(
            N8N_LOGIN_WEBHOOK_URL, json=payload, timeout=5)
        response.raise_for_status()
        print(f"Dados de login enviados: {response.status_code}")
    except Exception as e:
        print(f"Erro no envio de login: {e}")


async def main(page: ft.Page):
    global usuario_logado
    main_view = None

    page.theme_mode = ft.ThemeMode.LIGHT

    # Botão circular grande ligar/desligar
    status_btn = ft.Container(
        content=ft.Text("LIGAR", size=24,
                        weight=ft.FontWeight.BOLD, color="white"),
        width=150,
        height=150,
        alignment=ft.alignment.center,
        bgcolor="red",
        shape=ft.BoxShape.CIRCLE,
        on_click=lambda e: toggle_ligado(e),
        tooltip="Ligar / Desligar"
    )

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
            controls=[ft.Image(src="logo_inicio.png", width=600, height=600)],
            vertical_alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        navegar_para(splash_view)
        await asyncio.sleep(3)
        navegar_para(login_view)

    def toggle_ligado(e):
        global ligado
        ligado = not ligado
        if ligado:
            status_btn.content.value = "DESLIGAR"
            status_btn.bgcolor = "green"
            status_label.value = "Ligado"
            deteccao.camera_ativa = True
            threading.Thread(target=deteccao.start_camera_detection,
                             args=(usuario_logado,)).start()

        else:
            status_btn.content.value = "LIGAR"
            status_btn.bgcolor = "red"
            status_label.value = "Desligado"
            deteccao.camera_ativa = False
            winsound.PlaySound(None, winsound.SND_PURGE)
        status_btn.update()
        status_label.update()

    def logout(e):
        global usuario_logado
        usuario_logado = ""
        navegar_para(login_view)

    def abrir_contato_emergencia(e):
        mensagem = ft.Text("")
        email_field = ft.TextField(label="Novo e-mail", visible=False)
        whatsapp_field = ft.TextField(label="Novo WhatsApp", visible=False)
        salvar_email_btn = ft.ElevatedButton("Salvar E-mail", visible=False)
        salvar_whatsapp_btn = ft.ElevatedButton(
            "Salvar WhatsApp", visible=False)

        def atualizar_email(ev):
            novo_email = email_field.value
            if novo_email:
                cursor.execute(
                    "UPDATE contatos_emergencia SET email=? WHERE username=?", (novo_email, usuario_logado))
                conn.commit()
                mensagem.value = "E-mail atualizado com sucesso!"
                navegar_para(criar_main_view())
            else:
                mensagem.value = "Preencha o novo e-mail."
                email_field.visible = False
                salvar_email_btn.visible = False
                page.update()

        def atualizar_whatsapp(ev):
            novo_whatsapp = whatsapp_field.value
            if novo_whatsapp:
                cursor.execute(
                    "UPDATE contatos_emergencia SET whatsapp=? WHERE username=?", (novo_whatsapp, usuario_logado))
                conn.commit()
                mensagem.value = "WhatsApp atualizado com sucesso!"
                navegar_para(criar_main_view())
            else:
                mensagem.value = "Preencha o novo WhatsApp."
                whatsapp_field.visible = False
                salvar_whatsapp_btn.visible = False
                page.update()

        def editar_email(e):
            email_field.visible = True
            salvar_email_btn.visible = True
            page.update()

        def editar_whatsapp(e):
            whatsapp_field.visible = True
            salvar_whatsapp_btn.visible = True
            page.update()

        cursor.execute(
            "SELECT email, whatsapp FROM contatos_emergencia WHERE username=?", (usuario_logado,))
        contato = cursor.fetchone()

        contato_controls = []

        if contato:
            # Já existe contato
            email_row = ft.Row(
                [
                    ft.Text(f"E-mail: {contato[0]}", size=16),
                    ft.IconButton(icon=ft.Icons.EDIT,
                                  tooltip="Editar E-mail", on_click=editar_email)
                ],
                alignment=ft.MainAxisAlignment.CENTER
            )

            whatsapp_row = ft.Row(
                [
                    ft.Text(f"WhatsApp: {contato[1]}", size=16),
                    ft.IconButton(
                        icon=ft.Icons.EDIT, tooltip="Editar WhatsApp", on_click=editar_whatsapp)
                ],
                alignment=ft.MainAxisAlignment.CENTER
            )
            contato_controls.extend([email_row, whatsapp_row])

            # Define ações de atualização
            salvar_email_btn.on_click = atualizar_email
            salvar_whatsapp_btn.on_click = atualizar_whatsapp

        else:
            # Primeira vez: salvar novo contato
            email_field.visible = True
            whatsapp_field.visible = True
            salvar_email_btn.text = "Salvar Contato"
            salvar_email_btn.visible = True

            def salvar_primeiro_contato(e):
                email = email_field.value
                whatsapp = whatsapp_field.value
                if email and whatsapp:
                    cursor.execute("INSERT INTO contatos_emergencia (username, email, whatsapp) VALUES (?, ?, ?)",
                                   (usuario_logado, email, whatsapp))
                    conn.commit()
                    mensagem.value = "Contato salvo com sucesso!"
                    abrir_contato_emergencia(None)
                else:
                    mensagem.value = "Preencha todos os campos!"
                page.update()

            salvar_email_btn.on_click = salvar_primeiro_contato

        contato_view = ft.View(
            "/contato_emergencia",
            appbar=ft.AppBar(
                leading=ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    tooltip="Voltar",
                    on_click=lambda _: navegar_para(criar_main_view())
                ),
                title=ft.Text("Contato de Emergência"),
            ),
            controls=[
                ft.Column(
                    [
                        *contato_controls,
                        email_field,
                        whatsapp_field,
                        salvar_email_btn,
                        salvar_whatsapp_btn,
                        mensagem,
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True,
                )
            ],
            vertical_alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )

        navegar_para(contato_view)

        contato_view = ft.View(
            "/contato_emergencia",
            appbar=ft.AppBar(
                leading=ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    tooltip="Voltar",
                    on_click=lambda _: navegar_para(criar_main_view())
                ),
                title=ft.Text("Contato de Emergência"),
            ),
            controls=[
                ft.Column(
                    [
                        *contato_controls,
                        email_field,
                        whatsapp_field,
                        salvar_email_btn,
                        salvar_whatsapp_btn,
                        mensagem,
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True,
                )
            ],
            vertical_alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )

        navegar_para(contato_view)

    def criar_main_view():
        status_btn.on_click = toggle_ligado

        def mudar_tema(e):
            if page.theme_mode == ft.ThemeMode.LIGHT:
                page.theme_mode = ft.ThemeMode.DARK
            else:
                page.theme_mode = ft.ThemeMode.LIGHT
            page.update()

        def abrir_historico_ocorrencia(e):
            cursor.execute(
                "SELECT data, hora, tempo_olhos_fechados, cidade, estado, pais FROM ocorrencias WHERE username=? ORDER BY id DESC",
                (usuario_logado,)
            )
            registros = cursor.fetchall()

            colunas = [
                ft.DataColumn(label=ft.Text("Data")),
                ft.DataColumn(label=ft.Text("Hora")),
                ft.DataColumn(label=ft.Text("Tempo")),
                ft.DataColumn(label=ft.Text("Cidade")),
                ft.DataColumn(label=ft.Text("Estado")),
                ft.DataColumn(label=ft.Text("País")),
            ]

            linhas = [
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(reg[0])),
                    ft.DataCell(ft.Text(reg[1])),
                    ft.DataCell(ft.Text(reg[2])),
                    ft.DataCell(ft.Text(reg[3])),
                    ft.DataCell(ft.Text(reg[4])),
                    ft.DataCell(ft.Text(reg[5])),
                ]) for reg in registros
            ]

            historico_view = ft.View(
                "/historico",
                appbar=ft.AppBar(
                    leading=ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        tooltip="Voltar",
                        on_click=lambda _: navegar_para(criar_main_view())
                    ),
                    title=ft.Text("Histórico de Ocorrência"),
                ),
                controls=[
                    ft.DataTable(columns=colunas, rows=linhas),
                ],
                scroll=ft.ScrollMode.ALWAYS,
            )
            navegar_para(historico_view)

        menu_itens = [
            ft.PopupMenuItem(text="Contato de Emergência",
                             on_click=abrir_contato_emergencia),
            ft.PopupMenuItem(text="Histórico de Ocorrência",
                             on_click=abrir_historico_ocorrencia),
            ft.PopupMenuItem(text="Logoff", on_click=logout),
        ]

        return ft.View(
            "/main",
            controls=[
                ft.AppBar(
                    title=ft.Text(f"Olá, {usuario_logado}"),
                    leading=ft.PopupMenuButton(
                        icon=ft.Icons.MENU,
                        tooltip="Menu",
                        items=menu_itens,
                    ),
                    actions=[
                        ft.IconButton(
                            icon=ft.Icons.BRIGHTNESS_6,
                            tooltip="Alternar Tema",
                            on_click=mudar_tema
                        ),
                    ]
                ),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Monitore a sua sonolencia", size=30,
                                    weight=ft.FontWeight.BOLD),
                            status_label,
                            status_btn,
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        tight=True,
                    ),
                    alignment=ft.alignment.center,
                    expand=True,
                )
            ]
        )

    # LOGIN
    login_usuario = ft.TextField(label="Usuário")
    login_senha = ft.TextField(
        label="Senha", password=True, can_reveal_password=True)
    login_mensagem = ft.Text("")

    def tentar_login(e):
        global usuario_logado
        usuario = login_usuario.value
        senha = login_senha.value

        cursor.execute(
            "SELECT * FROM usuarios WHERE username=? AND password=?", (usuario, senha))
        resultado = cursor.fetchone()

        if resultado:
            usuario_logado = usuario
            navegar_para(criar_main_view())
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
                    ft.ElevatedButton(
                        "Entrar", on_click=tentar_login),
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

    # CADASTRO
    cadastro_usuario = ft.TextField(label="Novo Usuário")
    cadastro_senha = ft.TextField(
        label="Nova Senha", password=True, can_reveal_password=True)
    cadastro_mensagem = ft.Text("")

    def cadastrar_usuario(e):
        usuario = cadastro_usuario.value
        senha = cadastro_senha.value
        if usuario and senha:
            try:
                cursor.execute(
                    "INSERT INTO usuarios (username, password) VALUES (?, ?)", (usuario, senha))
                conn.commit()
                cadastro_mensagem.value = "Cadastro realizado com sucesso!"
                send_registration_to_n8n(usuario, senha)
            except sqlite3.IntegrityError:
                cadastro_mensagem.value = "Usuário já existe!"
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
    asyncio.run(ft.app_async(target=main))
