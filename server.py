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

    # Find the last occurrence of a sentence-ending character
    last_index = -1
    for i in range(len(text) - 1, -1, -1):
        if text[i] in sentence_endings:
            last_index = i
            break

    # If a sentence-ending character is found, return the text up to that index
    if last_index != -1:
        return text[:last_index + 1]

    # If no sentence-ending character is found, return the original text
    return text


# Function to call Ollama and generate text
def generate_response(history, model_name="innosama", stream=False):
    response = ollama.chat(
        model=model_name,
        messages=history,
        stream=stream
    )
    # print("generated", response)
    resp = ""
    if stream == True:
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
    # print("get response", response)
    if cut == True:
        response = trim_to_full_sentences(response)
    conversation_history.append({'role': 'assistant', 'content': response})
    return response


def split_into_sentences(text):
    return re.split(r'(?<=[.!?])\s+', text)


def continue_gen():
    global conversation_history
    response = generate_response(conversation_history, model_name)
    conversation_history[-1]["content"] += " " + trim_to_full_sentences(response)


def response2audio(response):
    global tts
    response = response.replace("«", "").replace("»", "")
    sentences = split_into_sentences(response)
    audio_files = []
    for i, sentence in enumerate(sentences):
        file_path = f"sentence_{i}.wav"
        tts.tts_to_file(text=sentence, speaker_wav="sam.wav", language="en", file_path=file_path, speed=1.2)
        audio_files.append(file_path)
    final_audio = AudioSegment.silent(duration=0)  # start with empty audio
    silence_between = 0  # 500ms of silence between sentences
    trim_duration = 300

    for audio_file in audio_files:
        sentence_audio = AudioSegment.from_wav(audio_file)

        # Trim the last `trim_duration` ms from the end of the audio
        if trim_duration > 0:
            sentence_audio = sentence_audio[:-trim_duration]

        # Concatenate the trimmed audio with the specified silence
        final_audio += sentence_audio + AudioSegment.silent(duration=silence_between)

    # Export the final concatenated audio
    final_audio.export("final_output.wav", format="wav")


def response2audioV2(response):
    global tts
    response = response.replace("«", "").replace("»", "")
    tts.tts_to_file(
        text=response,
        file_path="final_output.wav",
        speaker_wav="sam.wav",
        language="en")


def get_sudden_response():
    r = random.randint(1, 10)
    if r <= 5:
        conversation_history.append({'role': 'SYSTEM', 'content': "say something random to continue topic"})
    else:
        conversation_history.append({'role': 'SYSTEM', 'content': "say something random to change topic"})
    return get_response(data, model_name)


def monitor_timeout():
    while True:
        if time.time() - last_received_time > 15:
            get_sudden_response()
            time.sleep(15)  # Avoid repeated triggers during the wait
        time.sleep(1)


# Example usage
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
    last_received_time = time.time()
    timeout_thread = threading.Thread(target=monitor_timeout, daemon=True)
    # timeout_thread.start()

    while True:
        try:
            client_socket, addr = server_socket.accept()
            print(f"Connected: {addr}")

            while True:
                try:

                    data = client_socket.recv(1024).decode('utf-8')
                    if len(data) == 0:
                        continue
                    print(f"Receiving data: {data}")
                    if data == "bye":
                        print(f"Client {addr} ended the session.")
                        break

                    response = get_response(data, model_name)
                    last_received_time = time.time()
                    response2audio(response)

                    with open("final_output.wav", "rb") as f:
                        audio_data = f.read()
                        client_socket.sendall(audio_data)

                    print(f"Sent response: {response}")
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
