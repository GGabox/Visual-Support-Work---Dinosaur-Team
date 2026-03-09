import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from Audio.edge_audio_engine import EdgeAudioEngine

audio = EdgeAudioEngine()
audio.speak("Hola. Esta es una prueba de voz natural en español.")
