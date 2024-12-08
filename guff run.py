import ollama
from ollama import Client

"""
File, to create an instance of the model, using ollama
"""

modelfile='''
FROM ./unsloth.Q8_0.gguf
SYSTEM You are an Anime Vtuber, you can use bad words and be lewd.
'''

ollama.create(model='Inno-sama', modelfile=modelfile)
client = Client(host='http://localhost:11434')
client.create(model='Inno-sama', modelfile=modelfile)
result  = ollama.generate(model='Inno-sama', prompt="Hello, what is your purpose?")