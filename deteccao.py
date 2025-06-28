import cv2
import mediapipe as mp
import requests
import time
import datetime
import winsound

camera_ativa = False


def start_camera_detection():
    global camera_ativa
    # --- Configurações do Alerta e Webhook n8n ---
    # URL do seu Webhook n8n. Você precisará criar este webhook no n8n.
    N8N_WEBHOOK_URL_DROWSINESS_ALERT = 'https://driver777.app.n8n.cloud/webhook-test/automation'

    # Caminho para o arquivo de som de alerta
    # Certifique-se de que este arquivo existe na mesma pasta!
    ALERT_SOUND_PATH = 'alert_sound.wav'

    # Limiar de tempo (em segundos) que os olhos podem ficar fechados antes do alerta
    DROWSINESS_THRESHOLD_SECONDS = 2  # Alterado de 5 para 2 segundos

    # Limiar do Eye Aspect Ratio (EAR) para considerar os olhos fechados
    # Este valor pode precisar de ajuste dependendo da câmera e iluminação.
    # Valores comuns variam de 0.2 a 0.3 para olhos fechados, e 0.3 a 0.45 para olhos abertos.
    # Este valor pode precisar de ajuste após verificar os novos valores EAR.
    EYE_CLOSED_EAR_THRESHOLD = 0.25

    # Cooldown para o webhook e o som (evita spam de alertas)
    # Só envia alerta/som novamente após X segundos
    WEBHOOK_SOUND_COOLDOWN_SECONDS = 10

    # --- Variáveis de Estado ---
    eyes_closed_start_time = None  # Marca o início do fechamento dos olhos
    last_alert_trigger_time = 0  # Última vez que o alerta foi disparado

    # --- Configurações do MediaPipe ---
    mp_face_mesh = mp.solutions.face_mesh
    mp_drawing = mp.solutions.drawing_utils
    drawing_spec = mp_drawing.DrawingSpec(thickness=1, circle_radius=1)

    # Índices dos pontos faciais (landmarks) para os olhos esquerdo e direito para o cálculo do EAR.
    # Estes são os 6 pontos específicos usados na fórmula padrão do EAR, na ordem:
    # P1 (canto interno), P2 (pálpebra superior interna), P3 (pálpebra superior externa),
    # P4 (canto externo), P5 (pálpebra inferior externa), P6 (pálpebra inferior interna).
    # As coordenadas (x,y) de cada landmark são acessadas via face_landmarks.landmark[INDEX].
    LEFT_EYE_LANDMARKS = [
        362,  # P1 - Canto interno
        387,  # P2 - Pálpebra superior (meio-interno)
        385,  # P3 - Pálpebra superior (meio-externo)
        263,  # P4 - Canto externo
        380,  # P5 - Pálpebra inferior (meio-externo)
        374   # P6 - Pálpebra inferior (meio-interno)
    ]
    RIGHT_EYE_LANDMARKS = [
        33,   # P1 - Canto interno
        160,  # P2 - Pálpebra superior (meio-interno)
        158,  # P3 - Pálpebra superior (meio-externo)
        133,  # P4 - Canto externo
        153,  # P5 - Pálpebra inferior (meio-externo)
        144   # P6 - Pálpebra inferior (meio-interno)
    ]

    # --- Funções de Cálculo ---

    def euclidean_distance(point1, point2):
        """Calcula a distância euclidiana entre dois pontos 2D."""
        return ((point1.x - point2.x)**2 + (point1.y - point2.y)**2)**0.5

    def calculate_ear(eye_landmarks_indices, landmarks):
        """
        Calcula o Eye Aspect Ratio (EAR) para um olho.
        Baseado nos 6 pontos (P1 a P6) de um olho.
        EAR = (|P2-P6| + |P3-P5|) / (2 * |P1-P4|)
        """
        # Mapeia os índices para os objetos landmark reais
        p1 = landmarks[eye_landmarks_indices[0]]  # Canto interno (horizontal)
        # Pálpebra superior (vertical)
        p2 = landmarks[eye_landmarks_indices[1]]
        # Pálpebra superior (vertical)
        p3 = landmarks[eye_landmarks_indices[2]]
        p4 = landmarks[eye_landmarks_indices[3]]  # Canto externo (horizontal)
        # Pálpebra inferior (vertical)
        p5 = landmarks[eye_landmarks_indices[4]]
        # Pálpebra inferior (vertical)
        p6 = landmarks[eye_landmarks_indices[5]]

        # Distâncias verticais
        A = euclidean_distance(p2, p6)
        B = euclidean_distance(p3, p5)

        # Distância horizontal
        C = euclidean_distance(p1, p4)

        # Evita divisão por zero
        if C == 0:
            return 0

        ear = (A + B) / (2.0 * C)
        return ear

    def send_drowsiness_alert_to_n8n(timestamp, duration_closed, message):
        """
        Envia os dados do alerta de sonolência para o webhook do n8n.
        """
        payload = {
            "timestamp": timestamp,
            "durationEyesClosedSeconds": round(duration_closed, 2),
            "alertMessage": message,
            "source": "Sistema de Detecção "
        }

        try:
            response = requests.post(
                N8N_WEBHOOK_URL_DROWSINESS_ALERT, json=payload, timeout=5)
            response.raise_for_status()  # Lança um erro para status HTTP ruins (4xx ou 5xx)
            print(
                f"Alerta de sonolência enviado para n8n! Status: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Erro ao enviar alerta de sonolência para n8n: {e}")

    # --- Captura de Vídeo (Webcam) ---
    cap = cv2.VideoCapture(0)  # 0 para a webcam padrão

    # Inicializa o MediaPipe Face Mesh
    with mp_face_mesh.FaceMesh(
            max_num_faces=1,  # Foca em apenas um rosto para simplificar
            refine_landmarks=True,  # Melhora a precisão dos landmarks
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5) as face_mesh:

        if not cap.isOpened():
            print("Erro: Não foi possível abrir a webcam.")
            exit()

        print(
            f"Sistema de detecção de sonolência ativo. Limiar de olhos fechados: {DROWSINESS_THRESHOLD_SECONDS} segundos.")
        print("Pressione 'q' para sair...")

        while cap.isOpened() and camera_ativa:
            success, image = cap.read()
            if not success:
                print("Ignorando frame vazio da câmera.")
                continue

            # Espelhar a imagem horizontalmente para uma visualização de selfie (opcional).
            image = cv2.flip(image, 1)

            # Converter a imagem BGR para RGB antes de processar pelo MediaPipe.
            image.flags.writeable = False
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(image)

            # Desenhar as anotações de detecção de rosto e malha.
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            current_ear = 1.0  # Valor padrão para olhos abertos
            is_eyes_closed = False

            if results.multi_face_landmarks:
                for face_landmarks in results.multi_face_landmarks:
                    # Desenhar a malha facial COMPLETA para depuração (temporariamente)
                    mp_drawing.draw_landmarks(
                        image=image,
                        landmark_list=face_landmarks,
                        # Habilitado para visualização completa da malha
                        connections=mp_face_mesh.FACEMESH_TESSELATION,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=1, circle_radius=1))

                    # Desenhar apenas os contornos dos olhos (após desenhar a malha completa)
                    # Estes podem sobrepor a malha completa nos olhos, tornando-os mais visíveis.
                    mp_drawing.draw_landmarks(
                        image=image,
                        landmark_list=face_landmarks,
                        connections=mp_face_mesh.FACEMESH_LEFT_EYE,
                        landmark_drawing_spec=drawing_spec,
                        connection_drawing_spec=drawing_spec)
                    mp_drawing.draw_landmarks(
                        image=image,
                        landmark_list=face_landmarks,
                        connections=mp_face_mesh.FACEMESH_RIGHT_EYE,
                        landmark_drawing_spec=drawing_spec,
                        connection_drawing_spec=drawing_spec)

                    # Obter os landmarks dos olhos para calcular o EAR
                    left_ear = calculate_ear(
                        LEFT_EYE_LANDMARKS, face_landmarks.landmark)
                    right_ear = calculate_ear(
                        RIGHT_EYE_LANDMARKS, face_landmarks.landmark)

                    # Use a média dos dois olhos
                    current_ear = (left_ear + right_ear) / 2.0

                    # Determine se os olhos estão fechados
                    if current_ear < EYE_CLOSED_EAR_THRESHOLD:
                        is_eyes_closed = True
                    else:
                        is_eyes_closed = False

                    # Desenhar o valor do EAR na tela para depuração
                    cv2.putText(image, f"EAR: {current_ear:.2f}", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                    # Processa apenas o primeiro rosto detectado (max_num_faces=1)
                    break

            # --- Lógica de Alerta de Sonolência ---
            current_time_epoch = time.time()

            if is_eyes_closed:
                if eyes_closed_start_time is None:
                    eyes_closed_start_time = current_time_epoch  # Inicia a contagem

                duration_closed = current_time_epoch - eyes_closed_start_time
                cv2.putText(image, f"Olhos fechados: {duration_closed:.2f}s", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                if duration_closed >= DROWSINESS_THRESHOLD_SECONDS:
                    # Se o alerta não foi disparado recentemente
                    if (current_time_epoch - last_alert_trigger_time) > WEBHOOK_SOUND_COOLDOWN_SECONDS:
                        print(
                            f"ALERTA: Olhos fechados por {duration_closed:.2f} segundos!")

                        # Enviar webhook para n8n
                        send_drowsiness_alert_to_n8n(
                            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            duration_closed=duration_closed,
                            message=f"Driver detectado com sonolência: olhos fechados por {duration_closed:.2f} segundos."
                        )
                        last_alert_trigger_time = current_time_epoch  # Atualiza o tempo do último alerta

                        winsound.PlaySound(
                            ALERT_SOUND_PATH, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                eyes_closed_start_time = None  # Reseta a contagem se os olhos abrirem

            # Exibir a imagem.
            cv2.imshow('Sistema de Deteccao de Sonolencia', image)

            # Sair do loop se 'q' for pressionado.
            if cv2.waitKey(5) & 0xFF == ord('q'):
                break

    # Liberar os recursos.
    cap.release()
    cv2.destroyAllWindows()
