import flet as ft
import cv2
import base64
import time
import random
import os
import sys
import threading
from ultralytics import YOLO

# ==========================================================
# CONFIGURACIÓN DE RUTAS
# ==========================================================
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

try:
    from Audio.edge_audio_engine import EdgeAudioEngine
    from Audio.haptics import vibrate
    print("✅ Módulos de Audio y Haptics cargados")
except ImportError as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    except Exception as e:
        print(f"⚠️ No se pudo cargar el logo: {e}")
        return None

LOGO_PATH = os.path.join(os.path.dirname(__file__), "Visual Support Work LOGO.jpg")

# =====================
# CONFIGURACIÓN TIEMPOS
# =====================
AUDIO_LOCK_UNTIL = 0  
CHAR_SPEED = 0.08      
STATE_COOLDOWN = 7.0  
EVENT_COOLDOWN = 1.5
TRACK_COOLDOWN = 2.5
OBJECT_ACTION_COOLDOWN = 8.0

# =====================
# DICCIONARIO ROBUSTO (80 OBJETOS)
# =====================
IMPORTANT_OBJECTS = {
    "person": {"name": "persona", "gender": "f", "plural": "personas"},
    "bicycle": {"name": "bicicleta", "gender": "f", "plural": "bicicletas"},
    "car": {"name": "carro", "gender": "m", "plural": "carros"},
    "motorcycle": {"name": "motocicleta", "gender": "f", "plural": "motocicletas"},
    "bus": {"name": "autobús", "gender": "m", "plural": "autobuses"},
    "truck": {"name": "camión", "gender": "m", "plural": "camiones"},
    "traffic light": {"name": "semáforo", "gender": "m", "plural": "semáforos"},
    "fire hydrant": {"name": "hidrante", "gender": "m", "plural": "hidrantes"},
    "stop sign": {"name": "señal de pare", "gender": "f", "plural": "señales de pare"},
    "bench": {"name": "banca", "gender": "f", "plural": "bancas"},
    "cat": {"name": "gato", "gender": "m", "plural": "gatos"},
    "dog": {"name": "perro", "gender": "m", "plural": "perros"},
    "backpack": {"name": "mochila", "gender": "f", "plural": "mochilas"},
    "umbrella": {"name": "paraguas", "gender": "m", "plural": "paraguas"},
    "handbag": {"name": "bolso", "gender": "m", "plural": "bolsos"},
    "suitcase": {"name": "maleta", "gender": "f", "plural": "maletas"},
    "bottle": {"name": "botella", "gender": "f", "plural": "botellas"},
    "cup": {"name": "taza", "gender": "f", "plural": "tazas"},
    "fork": {"name": "tenedor", "gender": "m", "plural": "tenedores"},
    "knife": {"name": "cuchillo", "gender": "m", "plural": "cuchillos"},
    "spoon": {"name": "cuchara", "gender": "f", "plural": "cucharas"},
    "bowl": {"name": "tazón", "gender": "m", "plural": "tazones"},
    "chair": {"name": "silla", "gender": "f", "plural": "sillas"},
    "couch": {"name": "sofá", "gender": "m", "plural": "sofás"},
    "potted plant": {"name": "maceta", "gender": "f", "plural": "macetas"},
    "bed": {"name": "cama", "gender": "f", "plural": "camas"},
    "dining table": {"name": "mesa", "gender": "f", "plural": "mesas"},
    "tv": {"name": "pantalla", "gender": "f", "plural": "pantallas"},
    "laptop": {"name": "computadora", "gender": "f", "plural": "computadoras"},
    "mouse": {"name": "ratón", "gender": "m", "plural": "ratones"},
    "keyboard": {"name": "teclado", "gender": "m", "plural": "teclados"},
    "cell phone": {"name": "teléfono", "gender": "m", "plural": "teléfonos"},
    "microwave": {"name": "microondas", "gender": "m", "plural": "microondas"},
    "oven": {"name": "horno", "gender": "m", "plural": "hornos"},
    "refrigerator": {"name": "refrigerador", "gender": "m", "plural": "refrigeradores"},
    "book": {"name": "libro", "gender": "m", "plural": "libros"},
    "clock": {"name": "reloj", "gender": "m", "plural": "relojes"}
}

OBJECT_ACTIONS = {
    "chair": ["puedes sentarte", "hay un asiento"],
    "cell phone": ["está a tu alcance"],
    "bottle": ["puedes tomar agua"],
    "traffic light": ["atención al semáforo"],
    "stop sign": ["señal de alto"],
    "laptop": ["computadora detectada"]
}

PRESENCE_PHRASES = ["Hay {count} {object} {zone}", "Tienes {count} {object} {zone}"]

def zone_from_x(x, w):
    if x < w * 0.35: return "a tu izquierda"
    elif x > w * 0.65: return "a tu derecha"
    return "frente a ti"

def article_for(gender, plural=False):
    if plural: return "unas" if gender == "f" else "unos"
    return "una" if gender == "f" else "un"

def describe_object_action(label, zone):
    obj = IMPORTANT_OBJECTS[label]
    action = random.choice(OBJECT_ACTIONS.get(label, ["en tu camino"]))
    return f"Tienes {article_for(obj['gender'])} {obj['name']} {zone}. {action}"

def smart_speak(engine, text, now):
    global AUDIO_LOCK_UNTIL
    if engine.is_speaking or now < AUDIO_LOCK_UNTIL:
        return False 
    duration = max(2.2, len(text) * CHAR_SPEED)
    engine.speak(text)
    AUDIO_LOCK_UNTIL = now + duration
    return True

# =====================
# INTERFAZ FLET
# =====================
def main(page: ft.Page):
    page.title = "VSW Mobile Assistant"
    page.window_width, page.window_height = 420, 850
    page.window_resizable = False
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 15
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    logo_b64 = get_base64_image(LOGO_PATH)
    logo_image = ft.Image(src_base64=logo_b64, height=120, fit=ft.ImageFit.CONTAIN, visible=True if logo_b64 else False)

    camera_view = ft.Image(src_base64="", width=400, height=350, fit=ft.ImageFit.CONTAIN)
    status_text = ft.Text("SISTEMA ACTIVO", color=ft.Colors.GREEN, weight="bold")
    log_list = ft.ListView(expand=1, spacing=5, auto_scroll=True)
    
    state = {"paused": False, "running": True}

    def on_pause_click(e):
        state["paused"] = not state["paused"]
        pause_btn.icon = ft.Icons.PLAY_ARROW if state["paused"] else ft.Icons.PAUSE
        pause_btn.text = "Reanudar" if state["paused"] else "Pausar"
        status_text.value = "PAUSADO" if state["paused"] else "SISTEMA ACTIVO"
        status_text.color = ft.Colors.RED if state["paused"] else ft.Colors.GREEN
        page.update()

    pause_btn = ft.ElevatedButton("Pausar Asistente", icon=ft.Icons.PAUSE, on_click=on_pause_click, width=250)

    page.add(
        ft.Text("Dinosaur Team", size=20, weight="bold"),
        logo_image,
        ft.Container(camera_view, bgcolor=ft.Colors.BLACK, border_radius=15),
        ft.Row([status_text], alignment=ft.MainAxisAlignment.CENTER),
        ft.Row([pause_btn], alignment=ft.MainAxisAlignment.CENTER),
        ft.Divider(),
        ft.Text("Detección de Entorno:", size=14, color=ft.Colors.BLUE_GREY_200),
        ft.Container(log_list, height=200, bgcolor=ft.Colors.BLACK12, border_radius=10, padding=10, expand=True)
    )

    def video_processing():
        global AUDIO_LOCK_UNTIL
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        model = YOLO("yolov8n.pt")
        audio = EdgeAudioEngine()
        track_state, last_state_time, last_track_time, last_object_action = {}, {}, {}, {}
        
        while state["running"]:
            if state["paused"]:
                time.sleep(0.1); continue

            ret, frame = cap.read()
            if not ret: break

            now = time.time()
            h, w, _ = frame.shape
            can_speak_now = not audio.is_speaking and now >= AUDIO_LOCK_UNTIL

            results = model.track(frame, persist=True, conf=0.45, verbose=False)
            seen = []

            if results and results[0].boxes:
                for box in results[0].boxes:
                    if box.id is None: continue
                    label = model.names[int(box.cls[0])]
                    if label not in IMPORTANT_OBJECTS: continue

                    tid = int(box.id[0])
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cx = (x1 + x2) / 2
                    x_norm, box_size = cx / w, (y2 - y1) / h
                    zone = zone_from_x(cx, w)
                    seen.append((label, zone))

                    # Seguimiento Persona
                    if label == "person":
                        prev = track_state.get(tid)
                        if prev and can_speak_now and now - last_track_time.get(tid, 0) > TRACK_COOLDOWN:
                            dx, ds = x_norm - prev["x"], box_size - prev["size"]
                            if abs(dx) > 0.02 or abs(ds) > 0.03:
                                msg = f"La persona {zone} se mueve"
                                if smart_speak(audio, msg, now):
                                    log_list.controls.append(ft.Text(f"🚶 {msg}", size=12))
                                    last_track_time[tid] = now
                                    can_speak_now = False
                        track_state[tid] = {"x": x_norm, "size": box_size}

                    # Acciones Objetos
                    if label in OBJECT_ACTIONS:
                        if can_speak_now and now - last_object_action.get((label, zone), 0) > OBJECT_ACTION_COOLDOWN:
                            msg = describe_object_action(label, zone)
                            if smart_speak(audio, msg, now):
                                if zone == "frente a ti": vibrate("double")
                                log_list.controls.append(ft.Text(f"💡 {msg}", size=12, weight="bold"))
                                last_object_action[(label, zone)] = now
                                can_speak_now = False

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Resumen Global
            if can_speak_now and seen:
                summary = {}
                for l, z in seen: summary[(l, z)] = summary.get((l, z), 0) + 1
                for (label, zone), count in summary.items():
                    if now - last_state_time.get((label, zone), 0) > STATE_COOLDOWN:
                        obj = IMPORTANT_OBJECTS[label]
                        phrase = random.choice(PRESENCE_PHRASES).format(
                            count=count if count > 1 else article_for(obj["gender"]),
                            object=obj["plural"] if count > 1 else obj["name"],
                            zone=zone
                        )
                        if smart_speak(audio, phrase, now):
                            log_list.controls.append(ft.Text(f"👁️ {phrase}", size=12, color=ft.Colors.BLUE_200))
                            last_state_time[(label, zone)] = now
                            can_speak_now = False; break

            _, buffer = cv2.imencode(".jpg", frame)
            camera_view.src_base64 = base64.b64encode(buffer).decode("utf-8")
            page.update()

        cap.release()

    threading.Thread(target=video_processing, daemon=True).start()

ft.app(target=main)