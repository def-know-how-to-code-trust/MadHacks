import whisper
import time
from pydub import AudioSegment

def get_audio_duration(file_path):
    audio = AudioSegment.from_file(file_path)
    return len(audio) / 1000.0  # Convert milliseconds to seconds

def transcribe_with_timing(file_path):
    # Load the model
    model = whisper.load_model("base")
    
    # Get audio duration
    audio_duration = get_audio_duration(file_path)
    
    # Measure transcription time
    start_time = time.time()
    result = model.transcribe(file_path)
    end_time = time.time()
    
    transcription_time = end_time - start_time
    
    return result, audio_duration, transcription_time

# Use the function
file_path = "audio.mp3"
result, audio_duration, transcription_time = transcribe_with_timing(file_path)

print(f"Transcription: {result['text'],result['language']}")
print(f"Audio Duration: {audio_duration:.2f} seconds")
print(f"Transcription Time: {transcription_time:.2f} seconds")
print(f"Real-time Factor: {transcription_time / audio_duration:.2f}x")