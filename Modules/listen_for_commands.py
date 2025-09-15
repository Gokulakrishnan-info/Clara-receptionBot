import speech_recognition as sr
from livekit.agents import function_tool, RunContext

from . import config
from .state import is_awake as _is_awake


@function_tool()
async def listen_for_commands(context: RunContext) -> str:
    """Wake & Sleep Word Detection."""
    global _is_awake
    r = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        r.adjust_for_ambient_noise(source)
        audio = r.listen(source, phrase_time_limit=5)

    try:
        text = r.recognize_google(audio).lower()

        if not _is_awake:
            if config.WAKE_WORD in text:
                _is_awake = True
                return "Wake word detected: Clara is now active."
            else:
                return "Clara is sleeping. (Silent mode active)"

        if config.SLEEP_PHRASE in text:
            _is_awake = False
            return "Sleep command detected: Clara will now stay silent until you say 'dhivya'."
        elif config.WAKE_WORD in text:
            return "Clara is already active."
        else:
            return f"Clara is active. Heard: {text}"

    except sr.UnknownValueError:
        return "No recognizable speech detected."
    except Exception as e:
        return f"Error in wake/sleep detection: {e}"


