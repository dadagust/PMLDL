# Inno-sama
A voice to voice artificial conversation system.

---

## Key Components and Workflow

### 1. **Server side**
- **Purpose**: Runs the LLM and TTS voice model

  - Gets the text data from the client and then, returns the .wav file with the voice to it.
  
### 2. **Client side**
- **Purpose**: Runs the vosk model to generate text, from the audio of a client
  - Connects to the server and send the text data to the server, then voices .wav, that the server returned 
  
### 3. **Ollama**
- **Purpose**: Creates and serves a model from the .guff file
- **Steps**:
  - *ollama serve* to create an ollama server for the model.
  - *ollama create innosama -f ModelFile* to create an instance of an LLM model
  - The rest of the work is done by the server code