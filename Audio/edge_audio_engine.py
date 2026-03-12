import os
import pygame
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

        # Inicializar el mezclador de audio de pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        # 🧠 Cola inteligente
        self.queue = MessageQueue()

        print("🔊 Edge TTS inicializado correctamente (Modo Silencioso)")

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
        Limpia la cola de mensajes pendientes.
        """
        self.queue.clear()
        pygame.mixer.music.stop()

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
            # Doble check para evitar solapamientos
            if self.is_speaking:
                return
            self.is_speaking = True

        audio_path = None
        try:
            # 1. Crear archivo temporal de forma segura
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                audio_path = f.name

            # 2. Generar el audio (Async)
            async def generate():
                communicate = edge_tts.Communicate(text, self.voice)
                await communicate.save(audio_path)

            asyncio.run(generate())

            # 3. Reproducción interna con Pygame (Sin ventanas)
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()

            # Esperar a que el audio termine de sonar antes de liberar el estado
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            
            # Descargar el archivo para poder borrarlo
            pygame.mixer.music.unload()

        except Exception as e:
            print(f"⚠️ Error en Edge TTS: {e}")
        finally:
            # 4. Limpieza del archivo temporal
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except Exception as e:
                    print(f"No se pudo eliminar el temporal: {e}")
            
            self.is_speaking = False