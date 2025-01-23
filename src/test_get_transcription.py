from speech_to_text import WhisperLiveTranscription
import time

modeles = [
    "openai/whisper-tiny",
    "openai/whisper-base",
    "openai/whisper-small",
    "openai/whisper-medium",
    "openai/whisper-large",
    "openai/whisper-large-v2",
    "openai/whisper-large-v3",
    "openai/whisper-large-v3-turbo",
]

resu = []
try:
    transcriber = WhisperLiveTranscription(model_id=modeles[2], language="french")
    transcriber.start_recording()
    transcription = transcriber.get_transcription(block=False, timeout=2)
    print("Press Ctrl+C to stop...")

    while True:
        transcription = transcriber.get_transcription(block=False, timeout=2)
        if transcription:
            resu.append(transcription["text"])
            # print(f"{transcription['timestamp']}: {transcription['text']}")
        time.sleep(0.1)

except KeyboardInterrupt:
    try:
        transcriber.stop_recording()
    except Exception as e:
        print(f"Error stopping: {e}")
    finally:
        if hasattr(transcriber, "p"):
            try:
                transcriber.p.terminate()
            except:
                pass


print(resu)
