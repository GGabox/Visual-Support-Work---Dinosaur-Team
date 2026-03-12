# Audio/haptics.py
import time

def vibrate(pattern="short"):
    if pattern == "short":
        print("📳 Vibración corta")
    elif pattern == "double":
        print("📳📳 Vibración doble")
    elif pattern == "long":
        print("📳📳📳 Vibración larga")