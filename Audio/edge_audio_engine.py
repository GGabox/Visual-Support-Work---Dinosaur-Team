import subprocess
import tempfile
import edge_tts
import asyncio
import threading
import time
from Audio.message_queue import MessageQueue


class EdgeAudioEngine:
    def __init__(self, voice="es-ES-AlvaroNeural"):
        self.voice = voice
        self.is_speaking = False
        self.lock = threading.Lock()

        # 🧠 Cola inteligente
        self.queue = MessageQueue()

        print("🔊 Edge TTS inicializado correctamente")

        # 🔁 Hilo dedicado al audio
        threading.Thread(
            target=self._audio_loop,
            daemon=True
        ).start()

    # =====================
    # API PÚBLICA
    # =====================
    def speak(self, text, priority=50, ttl=2.0):
        """
        priority: 0–100 (más alto = más importante)
        ttl: segundos antes de expirar
        """
        self.queue.enqueue(text, priority, ttl)

    def stop(self):
        """
        Edge no permite cortar audio en curso,
        pero limpiamos la cola.
        """
        self.queue.clear()

    # =====================
    # LOOP DE AUDIO
    # =====================
    def _audio_loop(self):
        while True:
            if not self.is_speaking:
                msg = self.queue.get_next()
                if msg:
                    self._play(msg)
            time.sleep(0.05)

    # =====================
    # REPRODUCCIÓN
    # =====================
    def _play(self, text):
        with self.lock:
            if self.is_speaking:
                return
            self.is_speaking = True

        try:
            self._play_tts(text)
        except Exception as e:
            print(f"⚠️ Error en Edge TTS: {e}")
        finally:
            self.is_speaking = False

    def _play_tts(self, text):
        # Archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            audio_path = f.name

        async def generate():
            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(audio_path)

        asyncio.run(generate())

        # 🔊 Reproducción estable en Windows
        subprocess.Popen(
            ["cmd", "/c", "start", "/min", audio_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )