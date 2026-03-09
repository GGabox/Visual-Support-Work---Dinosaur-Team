import time
from collections import deque

# =====================
# CONFIGURACIÓN
# =====================
HISTORY_SIZE = 5          # frames para suavizar
MOVE_THRESHOLD = 60       # píxeles reales para considerar movimiento
COOLDOWN = 1.5            # segundos entre mensajes
CENTER_MARGIN = 0.08      # 8% del ancho = zona muerta

# =====================
# ESTADO
# =====================
_x_history = deque(maxlen=HISTORY_SIZE)
_last_spoken_time = 0
_last_direction = None


def label_humano(label):
    return "Persona" if label == "person" else "Objeto"


def get_stable_position(x_center, frame_width):
    center_left = frame_width * (0.5 - CENTER_MARGIN)
    center_right = frame_width * (0.5 + CENTER_MARGIN)

    if x_center < center_left:
        return "izquierda"
    elif x_center > center_right:
        return "derecha"
    else:
        return "frente"


def build_guidance(label, x_center, box_ratio, frame_width):
    global _last_spoken_time, _last_direction

    now = time.time()

    # =====================
    # PELIGRO INMEDIATO
    # =====================
    if box_ratio > 0.45:
        _x_history.clear()
        _last_spoken_time = now
        return f"Detente. {label_humano(label)} muy cerca frente a ti."

    # =====================
    # SUAVIZADO DE MOVIMIENTO
    # =====================
    _x_history.append(x_center)

    if len(_x_history) < HISTORY_SIZE:
        return None

    avg_x = sum(_x_history) / len(_x_history)
    direction = get_stable_position(avg_x, frame_width)

    # =====================
    # EVITAR REPETICIONES
    # =====================
    if direction == _last_direction:
        return None

    if now - _last_spoken_time < COOLDOWN:
        return None

    # =====================
    # MENSAJES
    # =====================
    if direction == "frente":
        message = f"{label_humano(label)} frente a ti."
    else:
        message = f"{label_humano(label)} a tu {direction}."

    _last_direction = direction
    _last_spoken_time = now

    return message
