import sys
import ollama
import re
import socket
import torch
from TTS.api import TTS
from pydub import AudioSegment

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
def generate_response(history, model_name,stream = False):
    response = ollama.chat(
        model=model_name,
        messages=history,
        stream=stream
    )
    resp = ""
    if stream == True:
        for chunk in response:
            resp += chunk['message']['content']
            print(chunk['message']['content'], end='', flush=True)
        print()
    else:
        return response['message']['content']




def get_response(prompt,model_name,cut = True,stream = False):
    global conversation_history
    conversation_history.append({'role': 'user', 'content': prompt})
    response = generate_response(conversation_history,model_name)
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
        tts.tts_to_file(text=sentence, speaker_wav="sent_000.wav", language="en", file_path=file_path, speed=1.2)
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


# Example usage
if __name__ == "__main__":
    model_name = "example"

    conversation_history = []
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 12345))  # Замените на IP адрес и порт сервера
    server_socket.listen(1)

    print("Сервер запущен, ожидаю подключения...")
    client_socket, addr = server_socket.accept()
    print(f"Подключен: {addr}")

    data = ""
    while data != "bye":
        data = client_socket.recv(1024).decode('utf-8')
        print(f"Полученные данные: {data}")
        response = get_response(data,model_name)

        response2audio(response)

        with open("final_output.wav", "rb") as f:
            audio_data = f.read()
            client_socket.sendall(audio_data)

        print(f"Отправленные данные: {response}")
    client_socket.close()
    server_socket.close()
