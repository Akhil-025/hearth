import pyttsx3

VOICE_PROFILE = {
    "default": 1,      # Replace with the voice index you liked (e.g., Microsoft Zira)
    "introspect": 1,   # You can assign a different index here for reflective moments
    "alert": 0
}

def speak(text, mode="default"):
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    voice_id = voices[VOICE_PROFILE[mode]].id
    engine.setProperty('voice', voice_id)
    engine.setProperty('rate', 160)
    engine.say(text)
    engine.runAndWait()
