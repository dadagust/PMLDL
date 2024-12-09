import os
import time
import pygame
import pyaudio
import json
import socket
import threading
from vosk import Model, KaldiRecognizer

"""Client file"""

"""Specify the server ip and port"""
HOST = '10.241.1.26'
PORT = 12345

pygame.mixer.init()

English = True
model_path = "vosk-model-en-us-0.42-gigaspeech" if English else "vosk-model-ru-0.42"

if not os.path.exists(model_path):
    print(f"{model_path} Not founded")
    exit(1)

model = Model(model_path)

RATE = 16000
CHUNK = 1024

p = pyaudio.PyAudio()
stream = p.open(
    format=pyaudio.paInt16, channels=1,
    rate=RATE, input=True,
    frames_per_buffer=CHUNK,
    input_device_index=1
)
stream.start_stream()
rec = KaldiRecognizer(model, RATE)
is_waiting_for_response = False  # Flag for managing response state

# Function to handle sudden responses from the server
def listen_for_responses(client_socket):
    while True:
        try:
            global is_waiting_for_response
            is_waiting_for_response = False
            response = client_socket.recv(40000000)
            if not response:
                print("Server closed connection.")
                break

            # Save and play the sudden response
            with open("response.wav", "wb") as file:
                file.write(response)

            print("Received sudden response, playing audio...")
            pygame.mixer.music.load("response.wav")
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                time.sleep(0.1)

            pygame.mixer.music.unload()
            os.remove("response.wav")
            print("You can speak now")
        except Exception as e:
            print(f"Error in sudden response listener: {e}")
            break

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((HOST, PORT))

# Start the thread for listening to sudden responses
response_thread = threading.Thread(target=listen_for_responses, args=(client_socket,), daemon=True)
response_thread.start()

"""
When the system tells "You can speak now," press any button and start speaking.
"""
try:
    print("You can speak now")
    input()

    while True:
        if is_waiting_for_response:
            # Handle server response after user input
            is_waiting_for_response = False
            print(f"is waiting response: {is_waiting_for_response}")
            input("")
            client_socket.send(b"DISCARD_SUDDEN_RESPONSE")
        else:
            # Notify the server to discard sudden responses

            #print("Notified server to discard sudden responses.")

            # Process voice input
            data = stream.read(CHUNK)
            if len(data) == 0:
                break

            if rec.AcceptWaveform(data):
                result = rec.Result()
                text = json.loads(result)["text"]

                # Send text to server
                client_socket.send(text.encode('utf-8'))
                print(f"Resolved text: {text}")
                is_waiting_for_response = True

            data = None

except KeyboardInterrupt:
    print("Stopped resolving.")

finally:
    client_socket.close()
    stream.stop_stream()
    stream.close()
    p.terminate()
