import os
import uuid
import io
import wave
from datetime import datetime
from enum import Enum, auto

import numpy as np

#import sounddevice as sd
#from agents.voice import AudioInput
#from agents.voice.input import TextInput

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastrtc import (
    Stream,
    ReplyOnPause,
)
from gradio.utils import get_space

from agents import (
    Agent,
    function_tool,
    Runner,
)
from agents.extensions.handoff_prompt import prompt_with_handoff_instructions
from agents.voice import SingleAgentVoiceWorkflow, VoicePipeline

from dotenv import load_dotenv


# :::::::::::::::::::::::::::::::::::::::::::::: #
#                  Time Helpers                  #
# :::::::::::::::::::::::::::::::::::::::::::::: #

def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# :::::::::::::::::::::::::::::::::::::::::::::: #
#                   Environment                  #
# :::::::::::::::::::::::::::::::::::::::::::::: #

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("OPENAI_API_KEY not set in environment")

SESSION_ID = str(uuid.uuid4())

USE_SERVER_NAME = '0.0.0.0'
USE_SERVER_PORT = 3000

AUDIO_USE_SAMPLE_RATE = 24000

TRANSIENT_DATA_DIR  = os.getenv("TRANSIENT_DATA_DIR")
SESSION_RECORD_FILE_PATH = os.path.join(TRANSIENT_DATA_DIR, f"session_record_{timestamp()}.log")
JSON_DB_FILE = os.getenv("JSON_DB_FILE")
JSON_DB_FILE_PATH = os.path.join(TRANSIENT_DATA_DIR, JSON_DB_FILE)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

from openai import OpenAI, AsyncOpenAI
# sync client
client = OpenAI(api_key=OPENAI_API_KEY)
# async client
aclient = AsyncOpenAI(api_key=OPENAI_API_KEY)

# :::::::::::::::::::::::::::::::::::::::::::::: #
#                 Session Records                #
# :::::::::::::::::::::::::::::::::::::::::::::: #

class SessionRole(str, Enum):
    USER      = "user"
    ASSISTANT = "assistant"
    APP       = "app"

# Ensure parent directory exists
os.makedirs(os.path.dirname(SESSION_RECORD_FILE_PATH), exist_ok=True)
    
def session_record_push(src, msg) -> str:
    entry = f"[{timestamp()}], {src}: {msg}"
    print(entry, flush=True)
    with open(SESSION_RECORD_FILE_PATH, 'a', encoding='utf-8') as f:
            f.write(f"{entry}\n")
            f.flush()
            
session_record_push(SessionRole.APP, "---------------------------")
session_record_push(SessionRole.APP, f"Session: id={SESSION_ID}, filename={SESSION_RECORD_FILE_PATH}")
session_record_push(SessionRole.APP, "---------------------------")
session_record_push(SessionRole.APP, f"TRANSIENT_DATA_DIR={TRANSIENT_DATA_DIR}")
session_record_push(SessionRole.APP, f"JSON_DB_FILE={JSON_DB_FILE}")
session_record_push(SessionRole.APP, f"AUDIO_USE_SAMPLE_RATE={AUDIO_USE_SAMPLE_RATE}")
session_record_push(SessionRole.APP, f"USE_SERVER_NAME={USE_SERVER_NAME}")
session_record_push(SessionRole.APP, f"USE_SERVER_PORT={USE_SERVER_PORT}")
session_record_push(SessionRole.APP, "---------------------------")

# :::::::::::::::::::::::::::::::::::::::::::::: #
#              Agent Tool Functions              #
# :::::::::::::::::::::::::::::::::::::::::::::: #

@function_tool
def load_appointments(json_str: str) -> str:
    session_record_push(SessionRole.ASSISTANT, f"loading appointments from: dir={TRANSIENT_DATA_DIR} file={JSON_DB_FILE}")
    content = ""
    if os.path.exists(JSON_DB_FILE_PATH):
        with open(JSON_DB_FILE_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
    return  content

@function_tool
def save_appointments(json_str: str) -> str:
    session_record_push(SessionRole.ASSISTANT, f"saving appointments to: dir={TRANSIENT_DATA_DIR} file={JSON_DB_FILE}")
    with open(JSON_DB_FILE_PATH, 'w', encoding='utf-8') as f:
            f.write(json_str)
            f.flush()
            
@function_tool
def get_open_slots() -> str:
    session_record_push(SessionRole.ASSISTANT, f"get open slots")
    return {
        "Hammaslääkäriaika": ["2025-08-19 09:00", "2025-08-21 11:00",  "2025-08-27 9:00"],
        "Suuhygienistiaika": ["2025-08-21 10:00", "2025-08-22 12:00", "2025-08-22 13:00", "2025-08-25 17:00"],
        "Työterveysaika": ["2025-08-17 10:00", "2025-08-22 19:00", "2025-08-23 20:00"]
    }

# :::::::::::::::::::::::::::::::::::::::::::::: #
#                     Agents                     #
# :::::::::::::::::::::::::::::::::::::::::::::: #

assistant_agent = Agent(
    name="Aino Agentti",
    instructions="""
    Sinä olet suomenkielinen ääniavustaja, joka auttaa varaamaan terveyspalveluaikoja.
    Tallennettavien varausten (JSON) tietomalli on (type, time, name).
    Noudata tarkasti tätä vuorovaikutusmallia järjestyksessä:
    1. Tervehdi käyttäjää.
    2. Kysy varauksen tyyppi (vaihtoehdot: Hammaslääkäriaika, Suuhygienistiaika, Työterveysaika).
    3. Kysy toivottu päivämäärä ja kellonaika (ei pakollinen), jos käyttäjällä ei ole toivetta päivämäärästä tai kellonajasta, siirry seuraavaan kohtaan.
    4. Soita get_open_slots()-funktiolle, suodata valitun tyypin vapaat ajat ja ehdota 2-3 vaihtoehtoa käyttäjälle, sitten kysy käyttäjältä minkä ajoista käyttäjä haluaa varata, ja ehdota "voin myös valita ajankohdan puolestasi". Siirry kohtaan 6.
    6. Kysy käyttäjän nimi varauksen nimeksi.
    7. Luo uusi varaus ja soita save_appointments(json_str)-funktiolle tallentaaksesi varauksen JSON muodossa tiedostoon.
    8. Jos uusi aika varattiin käyttäjälle, sano käyttäjälle että aika on nyt varattu.
    9. Sano "Kiitos asioinnista ja hyvää päivän jatkoa! Voit nyt sulkea puhelun".
    Puhu aina suomeksi ja käytä ystävällistä, selkeää sävyä.  
    """.strip(),
    model="gpt-4o-mini",
    tools=[load_appointments, save_appointments, get_open_slots],
)

session_record_push(SessionRole.APP, f"Session Agent: name=\"{assistant_agent.name}\", model=\"{assistant_agent.model}\"")
session_record_push(SessionRole.APP, "---------------------------\n")

# :::::::::::::::::::::::::::::::::::::::::::::: #
#              RTC Handlers/Helpers              #
# :::::::::::::::::::::::::::::::::::::::::::::: #

def pcm_to_wav_bytes(pcm_bytes: bytes, sample_rate: int) -> io.BytesIO:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)            # mono
        wf.setsampwidth(2)            # 2 bytes per sample (int16)
        wf.setframerate(sample_rate)  # e.g., 24000
        wf.writeframes(pcm_bytes)
    buf.seek(0)
    return buf

# NOTE: For this prototype we actually support just one session
# Buffers:
audio_buffers: dict[str, bytearray] = {}
conversation_histories: dict[str, list[dict]] = {}
conversation_histories.setdefault(SESSION_ID, [])

async def on_pause_handler(audio: tuple[int, np.ndarray]):
    """
    Called once the user pauses speaking.
    (sample_rate, np.ndarray of int16 PCM).
    """
    
    sample_rate, samples = audio
    # If for some reason we get float32, convert to int16:
    if samples.dtype == np.float32:
        samples = (samples * 32767).astype(np.int16)
    pcm = samples.tobytes()

    # Accumulate into session buffer
    buf = audio_buffers.setdefault(SESSION_ID, bytearray())
    buf.extend(pcm)

    # Check if the session PCM buffer actually contains anything:
    if not buf:
        return

    print(f"AudioInput: buffer_size={len(buf)}", flush=True)
    
    # --- STT ---
    # User transcripts with Whisper model
    with pcm_to_wav_bytes(buf, sample_rate) as wav_buf:
        wav_buf.name = "audio.wav"
        resp = client.audio.transcriptions.create(
            file=wav_buf,
            model="whisper-1",
            response_format="text",
            language="fi"  # <<< Finnish bias
        )
    transcript = resp
    
    # Append to conversation history
    conversation_history = conversation_histories[SESSION_ID]
    conversation_history.append({"role": SessionRole.USER, "content": transcript})
    session_record_push(SessionRole.USER, transcript)
    
    # !!! Clear buffer for next utterance !!!
    audio_buffers[SESSION_ID].clear()
    
    print("Invoke Agent with the conversation history, await the pipeline results", flush=True)
    
    # Directly run the assistant agent
    result = Runner.run_streamed(
        starting_agent=assistant_agent,
        input=conversation_history
    )

    print("Stream back agent text reply", flush=True)

    reply_text = ""
    async for event in result.stream_events():
        # raw_response_event + text delta events carry the text
        if getattr(event, "data", None) and hasattr(event.data, "delta"):
            reply_text += event.data.delta
  
    session_record_push(SessionRole.ASSISTANT, reply_text)
    conversation_history.append({"role": SessionRole.ASSISTANT, "content": reply_text})
    
    # --- TTS ---
    print("Begin response TTS, stream to PCM buffer", flush=True)
    
    tts = aclient.audio.speech.with_streaming_response.create(
        model="tts-1",
        voice="coral",
        input=reply_text, 
        response_format="pcm",
    )
    
    # Enter the context to get the actual response with iter_bytes()
    async with tts as response:
        async for pcm_bytes in response.iter_bytes(chunk_size=4096):
            arr = np.frombuffer(pcm_bytes, dtype=np.int16).reshape(1, -1)
            yield (AUDIO_USE_SAMPLE_RATE, arr)
            
# Stream Object
stream = Stream(
    handler=ReplyOnPause(
        on_pause_handler,
        can_interrupt=True,
    ),
    modality="audio",
    mode="send-receive",
)

# :::::::::::::::::::::::::::::::::::::::::::::: #
#                 Start Listening                #
# :::::::::::::::::::::::::::::::::::::::::::::: #

app = FastAPI()
stream.mount(app)

# Gradio UI
stream.ui.launch(server_name=USE_SERVER_NAME, server_port=USE_SERVER_PORT)
