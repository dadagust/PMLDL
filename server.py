import sys
import ollama
import re
import socket
import torch
from TTS.api import TTS
from pydub import AudioSegment
import random
import time
import threading

"""Server file"""

device = "cuda" if torch.cuda.is_available() else "cpu"

def trim_to_full_sentences(text):
    # Define sentence-ending characters
    sentence_endings = {'.', '?', '!'}
    last_index = -1
    for i in range(len(text) - 1, -1, -1):
        if text[i] in sentence_endings:
            last_index = i
            break
    return text[:last_index + 1] if last_index != -1 else text

def generate_response(history, model_name="innosama", stream=False):
    response = ollama.chat(model=model_name, messages=history, stream=stream)
    resp = ""
    if stream:
        for chunk in response:
            resp += chunk['message']['content']
            print(chunk['message']['content'], end='', flush=True)
        print()
    else:
        return response['message']['content']

def get_response(prompt, model_name="innosama", cut=True, stream=False):
    global conversation_history
    conversation_history.append({'role': 'user', 'content': prompt})
    response = generate_response(conversation_history, model_name)
    if cut:
        response = trim_to_full_sentences(response)
    conversation_history.append({'role': 'assistant', 'content': response})
    return response

def split_into_sentences(text):
    return re.split(r'(?<=[.!?])\s+', text)

def response2audio(response):
    global tts
    response = response.replace("«", "").replace("»", "")
    sentences = split_into_sentences(response)
    audio_files = []
    for i, sentence in enumerate(sentences):
        file_path = f"sentence_{i}.wav"
        tts.tts_to_file(text=sentence, speaker_wav="sam.wav", language="en", file_path=file_path, speed=1.2)
        audio_files.append(file_path)
    final_audio = AudioSegment.silent(duration=0)
    silence_between = 0
    trim_duration = 300

    for audio_file in audio_files:
        sentence_audio = AudioSegment.from_wav(audio_file)
        if trim_duration > 0:
            sentence_audio = sentence_audio[:-trim_duration]
        final_audio += sentence_audio + AudioSegment.silent(duration=silence_between)

    final_audio.export("final_output.wav", format="wav")

def get_sudden_response():
    r = random.randint(1, 10)
    if r <= 5:
        conversation_history.append({'role': 'SYSTEM', 'content': "say something random to continue topic"})
        print("continuing topic")
    else:
        conversation_history.append({'role': 'SYSTEM', 'content': "say something random to change topic"})
        print("changing topic")
    return get_response("", model_name)

def discard_sudden_response():
    global conversation_history
    if len(conversation_history) > 0 and conversation_history[-1]['role'] == "SYSTEM":
        conversation_history = conversation_history[:-1]
    elif len(conversation_history) > 1 and conversation_history[-2]['role'] == "SYSTEM":
        conversation_history = conversation_history[:-2]

if __name__ == "__main__":
    model_name = "innosama"
    HOST = '0.0.0.0'
    PORT = 12345
    conversation_history = []
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)
    print(f"Server Launched on {HOST}:{PORT}, awaiting connections...")

    data = ""

    while True:
        try:
            client_socket, addr = server_socket.accept()
            last_received_time = time.time()
            print(f"Connected: {addr}")

            while True:
                # Check for timeout and trigger sudden response if needed
                if time.time() - last_received_time > 44:
                    print("Timeout detected, generating sudden response...")
                    response = get_sudden_response()
                    last_received_time = time.time()  # Reset the timeout clock
                    response2audio(response)

                    with open("final_output.wav", "rb") as f:
                        audio_data = f.read()
                        client_socket.sendall(audio_data)
                    print(f"Sent response: {response}")
                try:
                    # Use socket timeout for non-blocking checks
                    client_socket.settimeout(1)
                    data = client_socket.recv(1024).decode('utf-8')
                    if len(data) == 0:
                        continue


                    if data == "DISCARD_SUDDEN_RESPONSE":
                        last_received_time = time.time()
                        discard_sudden_response()  # Call the function to handle discard logic
                        continue

                    print(f"Receiving data: {data}")

                    if data == "bye":
                        print(f"Client {addr} ended the session.")
                        break

                    last_received_time = time.time()
                    response = get_response(data, model_name)
                    response2audio(response)

                    with open("final_output.wav", "rb") as f:
                        audio_data = f.read()
                        client_socket.sendall(audio_data)

                    print(f"Sent response: {response}")
                except socket.timeout:
                    # Ignore socket timeout to continue checking for data or timeout
                    pass
                except ConnectionResetError:
                    print(f"Client {addr} forcibly closed the connection.")
                    conversation_history = []
                    break
                except Exception as e:
                    print(f"Error handling client {addr}: {e}")
                    conversation_history = []
                    break

        except Exception as e:
            print(f"Error accepting connection: {e}")
        finally:
            try:
                client_socket.close()
            except NameError:
                pass
