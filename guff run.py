import ollama

modelfile='''
FROM ./unsloth.Q8_0.gguf
SYSTEM You are an Anime Vtuber, you can use bad words and be lewd.
'''

ollama.create(model='Inno-sama', modelfile=modelfile)