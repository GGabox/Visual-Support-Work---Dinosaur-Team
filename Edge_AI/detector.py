# Hackathon SIC 2025\Edge_AI\detector.py
import cv2
import time
import random
import os
import sys
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

# =====================
# CONFIGURACIÓN TIEMPOS
# =====================
AUDIO_LOCK_UNTIL = 0  
CHAR_SPEED = 0.08     # Ajusta este valor si las frases son muy largas o cortas

EVENT_COOLDOWN = 1.0
STATE_COOLDOWN = 6.0  
TRACK_COOLDOWN = 2.0
OBJECT_ACTION_COOLDOWN = 7.0

# =====================
# DICCIONARIOS RESTAURADOS
# =====================
IMPORTANT_OBJECTS = {
    "person": {"name": "persona", "gender": "f"},
    "cell phone": {"name": "teléfono", "gender": "m"},
    "dog": {"name": "perro", "gender": "m"},
    "cat": {"name": "gato", "gender": "m"},
    "bottle": {"name": "botella", "gender": "f"},
    "chair": {"name": "silla", "gender": "f"}
}

OBJECT_ACTIONS = {
    "chair": ["puedes sentarte", "es un buen lugar para descansar"],
    "cell phone": ["puedes tomarlo", "está al alcance de tu mano"],
    "bottle": ["puedes beber agua", "puedes tomarla"],
    "dog": ["ten cuidado al pasar"],
    "cat": ["hay un gato cerca"]
}

EVENT_PHRASES = {
    "izquierda": ["Algo se mueve por tu izquierda", "Alguien pasó por tu izquierda"],
    "derecha": ["Movimiento por tu derecha", "Alguien pasó por tu derecha"],
    "frente": ["Movimiento frente a ti"]
}

PRESENCE_PHRASES = [
    "Hay {count} {object} {zone}",
    "Tienes {count} {object} {zone}",
    "Se detectan {count} {object} {zone}"
]

# =====================
# UTILIDADES
# =====================
def zone_from_x(x, w):
    if x < w * 0.4: return "izquierda"
    elif x > w * 0.6: return "derecha"
    return "frente"

def article_for(gender, plural=False):
    if plural: return "las" if gender == "f" else "los"
    return "una" if gender == "f" else "un"

def describe_object_action(label, zone):
    obj = IMPORTANT_OBJECTS[label]
    zone_text = f"a tu {zone}" if zone != "frente" else "frente a ti"
    action = random.choice(OBJECT_ACTIONS[label])
    return f"Tienes {article_for(obj['gender'])} {obj['name']} {zone_text}, {action}"

# ==========================================================
# FUNCIÓN DE HABLA CONTROLADA (ANTI-SOLAPAMIENTO)
# ==========================================================
def smart_speak(engine, text, now):
    global AUDIO_LOCK_UNTIL
    # Verificamos tanto el estado del motor como nuestro cronómetro interno
    if engine.is_speaking or now < AUDIO_LOCK_UNTIL:
        return False 

    # Bloqueamos el sistema proporcionalmente al largo del texto
    duration = max(1.8, len(text) * CHAR_SPEED)
    engine.speak(text)
    AUDIO_LOCK_UNTIL = now + duration
    return True

# =====================
# MAIN
# =====================
def main():
    global AUDIO_LOCK_UNTIL
    print("--- VSW Asistente Visual (Frases completas y Anti-solapamiento) ---")

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    model = YOLO("yolov8n.pt")
    audio = EdgeAudioEngine()

    track_zone_memory = {}
    track_state = {}
    last_event_time = {}
    last_state_time = {}
    last_track_time = {}
    last_object_action = {}
    
    paused = False

    while True:
        ret, frame = cap.read()
        if not ret: break

        now = time.time()
        h, w, _ = frame.shape
        
        # Estado de disponibilidad del audio para este frame
        can_speak_now = not audio.is_speaking and now >= AUDIO_LOCK_UNTIL

        key = cv2.waitKey(1) & 0xFF
        if key == ord("p") or key == ord("P"):
            paused = not paused
            audio.stop()
            AUDIO_LOCK_UNTIL = 0
            print("⏸️ PAUSADO")
        elif key == ord("q") or key == ord("Q"):
            break

        if paused:
            cv2.imshow("VSW Assistant", frame)
            continue

        results = model.track(frame, persist=True, conf=0.45, verbose=False)
        seen = []

        if results and results[0].boxes:
            for box in results[0].boxes:
                if box.id is None: continue
                label = model.names[int(box.cls[0])]
                if label not in IMPORTANT_OBJECTS: continue

                tid = int(box.id[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                x_center = (x1 + x2) / 2
                x_norm = x_center / w
                box_size = (y2 - y1) / h
                zone = zone_from_x(x_center, w)
                seen.append((label, zone))

                # 1. Cambio de Zona
                prev_zone = track_zone_memory.get(tid)
                if prev_zone and prev_zone != zone:
                    last = last_event_time.get(tid, 0)
                    if can_speak_now and now - last > EVENT_COOLDOWN:
                        if smart_speak(audio, random.choice(EVENT_PHRASES[zone]), now):
                            vibrate("short")
                            last_event_time[tid] = now
                            can_speak_now = False
                track_zone_memory[tid] = zone

                # 2. Tracking Persona
                if label == "person":
                    prev = track_state.get(tid)
                    if prev:
                        dx = x_norm - prev["x"]
                        ds = box_size - prev["size"]
                        parts = ["La persona"]
                        if abs(dx) > 0.008:
                            parts.append("se mueve a la derecha" if dx > 0 else "se mueve a la izquierda")
                        else: parts.append(f"está {zone}")
                        if abs(ds) > 0.015:
                            parts.append("se acerca" if ds > 0 else "se aleja")
                        
                        msg = " ".join(parts)
                        last_t = last_track_time.get(tid, 0)
                        if can_speak_now and now - last_t > TRACK_COOLDOWN:
                            if smart_speak(audio, msg, now):
                                last_track_time[tid] = now
                                can_speak_now = False
                    track_state[tid] = {"x": x_norm, "size": box_size}

                # 3. Acciones de Objetos
                if label != "person" and label in OBJECT_ACTIONS:
                    key_obj = (label, zone)
                    last = last_object_action.get(key_obj, 0)
                    if can_speak_now and now - last > OBJECT_ACTION_COOLDOWN:
                        if smart_speak(audio, describe_object_action(label, zone), now):
                            vibrate("double")
                            last_object_action[key_obj] = now
                            can_speak_now = False

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # 4. Resumen Global (Contexto)
        if can_speak_now and seen:
            summary = {}
            for l, z in seen: summary[(l, z)] = summary.get((l, z), 0) + 1
            for (l, z), count in summary.items():
                obj = IMPORTANT_OBJECTS[l]
                art = article_for(obj["gender"], count > 1)
                name = obj["name"] + ("s" if count > 1 else "")
                z_txt = f"a tu {z}" if z != "frente" else "frente a ti"
                
                phrase = random.choice(PRESENCE_PHRASES).format(count=count, object=f"{art} {name}", zone=z_txt)
                last = last_state_time.get(phrase, 0)
                if now - last > STATE_COOLDOWN:
                    if smart_speak(audio, phrase, now):
                        last_state_time[phrase] = now
                        can_speak_now = False
                        break

        cv2.imshow("VSW Assistant", frame)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()