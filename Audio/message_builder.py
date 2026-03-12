import time

_last_object = None
_last_position = None
_last_time = 0

COOLDOWN = 4  # segundos


def build_message(label, x_center, frame_width):
    global _last_object, _last_position, _last_time

    now = time.time()

    # 📍 Posición humana
    if x_center < frame_width * 0.33:
        position = "a tu izquierda"
    elif x_center > frame_width * 0.66:
        position = "a tu derecha"
    else:
        position = "frente a ti"

    # 🔁 Si es lo mismo muy seguido, no hablar
    if label == _last_object and position == _last_position:
        if now - _last_time < COOLDOWN:
            return None

    # 🗣️ FRASES NATURALES
    if label == "person":
        message = f"Persona {position}. Mantén distancia."
    elif label in ["chair", "table"]:
        message = f"Objeto {position}. Ten cuidado."
    elif label in ["cell phone", "bottle"]:
        message = f"{label.replace('_', ' ')} {position}. Puedes tomarlo."
    else:
        message = f"Objeto {position}."

    _last_object = label
    _last_position = position
    _last_time = now

    return message
