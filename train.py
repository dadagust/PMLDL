import ollama
from IPython.core.debugger import prompt

conversation_history = []
prompt = "hello who are you"
conversation_history.append({'role': 'user', 'content': prompt})

response = ollama.chat(
    model="innosama",
    messages=conversation_history,
    stream=False
)
print(response)