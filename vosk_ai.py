import os
import time
import pygame

import pyaudio
import json
from vosk import Model, KaldiRecognizer
import socket
from playsound import playsound
pygame.mixer.init()
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(('10.241.1.26', 12345))

English = True

model_path = "vosk-model-en-us-0.42-gigaspeech" if English else "vosk-model-ru-0.42"

if not os.path.exists(model_path):
    print(f"{model_path} Not founded")
    exit(1)

model = Model(model_path)

RATE = 16000
CHUNK = 1024

p = pyaudio.PyAudio()

stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE, input=True, frames_per_buffer=CHUNK, input_device_index=1)
stream.start_stream()

rec = KaldiRecognizer(model, RATE)


is_waiting_for_response = False

try:
    print("You can speak now")
    input()

    while True:
        if is_waiting_for_response:
            response = client_socket.recv(40000000)
            if not response:
                print("No response from server. Closing connection.")
                break

            with open(f"response.wav", "wb") as file:
                file.write(response)
            print("writed audio")

            pygame.mixer.music.load(f"response.wav")
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                time.sleep(0.1)

            pygame.mixer.music.unload()
            os.remove(f"response.wav")
            is_waiting_for_response = False
            print("You can speak now")
            input()


        else:
            data = stream.read(CHUNK)
            if len(data) == 0:
                break

            if rec.AcceptWaveform(data):
                result = rec.Result()
                text = json.loads(result)["text"]
                client_socket.send(text.encode('utf-8'))
                print(f"Resolved text: {text}")
                is_waiting_for_response = True

            data = None

except KeyboardInterrupt:
    print("Stopped resolving")

finally:
    client_socket.close()
    stream.stop_stream()
    stream.close()
    p.terminate()
