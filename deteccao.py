import cv2
import mediapipe as mp
import requests
import time
import datetime
import winsound
import sqlite3

camera_ativa = False


def obter_localizacao():
    try:
        resposta = requests.get("http://ip-api.com/json/", timeout=5)
        dados = resposta.json()
        return {
            "cidade": dados.get("city", "Desconhecida"),
            "estado": dados.get("regionName", "Desconhecido"),
            "pais": dados.get("country", "Desconhecido")
        }
    except Exception as e:
        print(f"Erro ao obter localização: {e}")
        return {
            "cidade": "Erro",
            "estado": "Erro",
            "pais": "Erro"
        }


def start_camera_detection(usuario_logado):
    conn = sqlite3.connect("usuarios.db", check_same_thread=False)
    cursor = conn.cursor()
    global camera_ativa

    N8N_WEBHOOK_URL_DROWSINESS_ALERT = 'https://driver777.app.n8n.cloud/webhook-test/automation'
    ALERT_SOUND_PATH = 'alert_sound.wav'
    DROWSINESS_THRESHOLD_SECONDS = 2
    EYE_CLOSED_EAR_THRESHOLD = 0.25
    WEBHOOK_SOUND_COOLDOWN_SECONDS = 10

    eyes_closed_start_time = None
    last_alert_trigger_time = 0

    mp_face_mesh = mp.solutions.face_mesh
    mp_drawing = mp.solutions.drawing_utils
    drawing_spec = mp_drawing.DrawingSpec(thickness=1, circle_radius=1)

    LEFT_EYE_LANDMARKS = [362, 387, 385, 263, 380, 374]
    RIGHT_EYE_LANDMARKS = [33, 160, 158, 133, 153, 144]

    def euclidean_distance(p1, p2):
        return ((p1.x - p2.x)**2 + (p1.y - p2.y)**2)**0.5

    def calculate_ear(eye_idx, landmarks):
        p1, p2, p3, p4, p5, p6 = [landmarks[i] for i in eye_idx]
        A = euclidean_distance(p2, p6)
        B = euclidean_distance(p3, p5)
        C = euclidean_distance(p1, p4)
        return (A + B) / (2.0 * C) if C != 0 else 0

    def send_drowsiness_alert_to_n8n(timestamp, duration_closed, message):
        payload = {
            "timestamp": timestamp,
            "durationEyesClosedSeconds": round(duration_closed, 2),
            "alertMessage": message,
            "source": "Sistema de Detecção"
        }

        try:
            response = requests.post(
                N8N_WEBHOOK_URL_DROWSINESS_ALERT, json=payload, timeout=5)
            response.raise_for_status()
            print(f"Alerta de sonolência enviado: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Erro ao enviar alerta: {e}")

        try:
            localizacao = obter_localizacao()
            data_atual = datetime.datetime.now().strftime("%Y-%m-%d")
            hora_atual = datetime.datetime.now().strftime("%H:%M:%S")
            tempo_fechado = f"{round(duration_closed, 2)}s"

            cursor.execute("""
                INSERT INTO ocorrencias (username, data, hora, tempo_olhos_fechados, cidade, estado, pais)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (usuario_logado, data_atual, hora_atual, tempo_fechado,
                  localizacao["cidade"], localizacao["estado"], localizacao["pais"]))
            conn.commit()
            print("Ocorrência salva no banco de dados.")
        except sqlite3.Error as e:
            print(f"Erro ao salvar ocorrência: {e}")

    cap = cv2.VideoCapture(0)

    with mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as face_mesh:

        if not cap.isOpened():
            print("Erro: Não foi possível abrir a webcam.")
            exit()

        print("Sistema de detecção de sonolência ativo.")
        print("Pressione 'q' para sair...")

        while cap.isOpened() and camera_ativa:
            success, image = cap.read()
            if not success:
                print("Frame vazio.")
                continue

            image = cv2.flip(image, 1)
            image.flags.writeable = False
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(image)
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            current_ear = 1.0
            is_eyes_closed = False

            if results.multi_face_landmarks:
                for face_landmarks in results.multi_face_landmarks:
                    mp_drawing.draw_landmarks(
                        image=image,
                        landmark_list=face_landmarks,
                        connections=mp_face_mesh.FACEMESH_TESSELATION,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=mp_drawing.DrawingSpec(
                            color=(0, 255, 0), thickness=1)
                    )
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

                    left_ear = calculate_ear(
                        LEFT_EYE_LANDMARKS, face_landmarks.landmark)
                    right_ear = calculate_ear(
                        RIGHT_EYE_LANDMARKS, face_landmarks.landmark)
                    current_ear = (left_ear + right_ear) / 2.0

                    is_eyes_closed = current_ear < EYE_CLOSED_EAR_THRESHOLD

                    cv2.putText(image, f"EAR: {current_ear:.2f}", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    break

            current_time_epoch = time.time()

            if is_eyes_closed:
                if eyes_closed_start_time is None:
                    eyes_closed_start_time = current_time_epoch

                duration_closed = current_time_epoch - eyes_closed_start_time
                cv2.putText(image, f"Olhos fechados: {duration_closed:.2f}s", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                if duration_closed >= DROWSINESS_THRESHOLD_SECONDS:
                    if (current_time_epoch - last_alert_trigger_time) > WEBHOOK_SOUND_COOLDOWN_SECONDS:
                        print(
                            f"ALERTA: olhos fechados por {duration_closed:.2f} segundos.")
                        send_drowsiness_alert_to_n8n(
                            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            duration_closed=duration_closed,
                            message=f"Driver detectado com sonolência: olhos fechados por {duration_closed:.2f} segundos."
                        )
                        last_alert_trigger_time = current_time_epoch

                        winsound.PlaySound(
                            ALERT_SOUND_PATH, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                eyes_closed_start_time = None

            cv2.imshow('Sistema de Detecção de Sonolência', image)
            if cv2.waitKey(5) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()
