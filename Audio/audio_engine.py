import pyttsx3
import time


class AudioEngine:
    def __init__(self, cooldown=3):
        self.engine = pyttsx3.init()
        self.cooldown = cooldown
        self.last_time = 0

        # 🎙️ Buscar voz en español
        voices = self.engine.getProperty("voices")
        for v in voices:
            if "spanish" in v.name.lower() or "es" in v.id.lower():
                self.engine.setProperty("voice", v.id)
                break

        self.engine.setProperty("rate", 165)   # velocidad natural
        self.engine.setProperty("volume", 1.0)

    def speak(self, text):
        if not text:
            return

        now = time.time()
        if now - self.last_time < self.cooldown:
            return

        self.last_time = now
        self.engine.say(text)
        self.engine.runAndWait()
