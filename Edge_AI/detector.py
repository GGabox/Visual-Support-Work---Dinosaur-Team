import cv2
import time
import random
import os
import sys
from ultralytics import YOLO

# Configuración de rutas
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

try:
    from Audio.edge_audio_engine import EdgeAudioEngine
    from Audio.haptics import vibrate
except ImportError:
    print("⚠️ Error cargando módulos de Audio/Haptics")

# ==========================================================
# DICCIONARIO ROBUSTO (Categorías COCO)
# ==========================================================
IMPORTANT_OBJECTS = {
    # Personas y Gestos
    "person": {"name": "persona", "gender": "f", "plural": "personas"},
    # Vehículos y Calle
    "bicycle": {"name": "bicicleta", "gender": "f"}, "car": {"name": "carro", "gender": "m"},
    "motorcycle": {"name": "moto", "gender": "f"}, "bus": {"name": "autobús", "gender": "m"},
    "truck": {"name": "camión", "gender": "m"}, "traffic light": {"name": "semáforo", "gender": "m"},
    "stop sign": {"name": "señal de pare", "gender": "f"}, "bench": {"name": "banca", "gender": "f"},
    # Animales
    "cat": {"name": "gato", "gender": "m"}, "dog": {"name": "perro", "gender": "m"},
    "horse": {"name": "caballo", "gender": "m"}, "sheep": {"name": "oveja", "gender": "f"},
    "cow": {"name": "vaca", "gender": "f"}, "elephant": {"name": "elefante", "gender": "m"},
    "bear": {"name": "oso", "gender": "m"}, "zebra": {"name": "cebra", "gender": "f"},
    "giraffe": {"name": "jirafa", "gender": "f"},
    # Objetos de Interior / Casa
    "backpack": {"name": "mochila", "gender": "f"}, "umbrella": {"name": "paraguas", "gender": "m"},
    "handbag": {"name": "bolso", "gender": "m"}, "tie": {"name": "corbata", "gender": "f"},
    "suitcase": {"name": "maleta", "gender": "f"}, "bottle": {"name": "botella", "gender": "f"},
    "cup": {"name": "taza", "gender": "f"}, "fork": {"name": "tenedor", "gender": "m"},
    "knife": {"name": "cuchillo", "gender": "m"}, "spoon": {"name": "cuchara", "gender": "f"},
    "bowl": {"name": "tazón", "gender": "m"}, "chair": {"name": "silla", "gender": "f"},
    "couch": {"name": "sofá", "gender": "m"}, "potted plant": {"name": "maceta", "gender": "f"},
    "bed": {"name": "cama", "gender": "f"}, "dining table": {"name": "mesa", "gender": "f"},
    "toilet": {"name": "inodoro", "gender": "m"}, "tv": {"name": "pantalla", "gender": "f"},
    "laptop": {"name": "computadora", "gender": "f"}, "mouse": {"name": "ratón", "gender": "m"},
    "keyboard": {"name": "teclado", "gender": "m"}, "cell phone": {"name": "teléfono", "gender": "m"},
    "microwave": {"name": "microondas", "gender": "m"}, "oven": {"name": "horno", "gender": "m"},
    "refrigerator": {"name": "refrigerador", "gender": "m"}, "book": {"name": "libro", "gender": "m"},
    "clock": {"name": "reloj", "gender": "m"}, "vase": {"name": "florero", "gender": "m"},
    "scissors": {"name": "tijeras", "gender": "f"}, "teddy bear": {"name": "oso de peluche", "gender": "m"},
}

OBJECT_ACTIONS = {
    "chair": ["puedes sentarte", "asiento disponible"],
    "bottle": ["puedes beber agua"],
    "traffic light": ["atención al cruzar"],
    "stop sign": ["detente, señal de alto"],
    "laptop": ["computadora detectada frente a ti"],
    "person": ["alguien está cerca"]
}

class VSWDetector:
    def __init__(self):
        self.model = YOLO("yolov8n.pt")
        self.audio = EdgeAudioEngine()
        self.last_spoken = {}
        self.audio_lock_until = 0

    def get_zone(self, x, w):
        # Zona frontal más estricta para precisión (40% al 60%)
        if x < w * 0.40: return "a tu izquierda"
        elif x > w * 0.60: return "a tu derecha"
        return "frente a ti"

    def process_frame(self, frame):
        now = time.time()
        h, w, _ = frame.shape
        results = self.model.track(frame, persist=True, verbose=False, conf=0.45)
        detections_log = []

        if results and results[0].boxes:
            for box in results[0].boxes:
                if box.id is None: continue
                label = self.model.names[int(box.cls[0])]
                if label not in IMPORTANT_OBJECTS: continue

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                zone = self.get_zone(cx, w)
                
                # --- DETECCIÓN DE SALUDO ---
                aspect_ratio = (x2 - x1) / (y2 - y1)
                if label == "person" and aspect_ratio > 0.75:
                    if now - self.last_spoken.get("wave", 0) > 8:
                        msg = "Una persona te está saludando"
                        self.audio.speak(msg)
                        self.last_spoken["wave"] = now
                        detections_log.append(f"👋 {msg}")

                # --- ANUNCIO DE OBJETOS ---
                key = f"{label}_{zone}"
                cooldown = 5.0 if zone == "frente a ti" else 10.0
                
                if now - self.last_spoken.get(key, 0) > cooldown:
                    obj = IMPORTANT_OBJECTS[label]
                    phrase = f"Hay {'una' if obj['gender']=='f' else 'un'} {obj['name']} {zone}"
                    
                    if zone == "frente a ti":
                        vibrate("double") # Feedback físico
                        phrase += f". {random.choice(OBJECT_ACTIONS.get(label, ['está en tu camino']))}"
                    
                    self.audio.speak(phrase)
                    self.last_spoken[key] = now
                    detections_log.append(f"👁️ {phrase}")

                color = (0, 0, 255) if zone == "frente a ti" else (0, 255, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        
        return frame, detections_log