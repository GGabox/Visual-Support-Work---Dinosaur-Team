# Audio/natural_language.py

def describe_presence(label, zone):
    if label == "person":
        return f"Hay una persona {zone}."
    else:
        return f"{label} {zone}."


def describe_movement(label, direction):
    if label == "person":
        return f"La persona se mueve hacia tu {direction}."
    else:
        return f"El objeto se mueve hacia tu {direction}."
