import whisper
import time
from pydub import AudioSegment
import os
import argparse
import oci
from prettytable import PrettyTable

file_path = "supportLang.txt"
config = oci.config.from_file()
trans_client = oci.ai_language.AIServiceLanguageClient(config)

FISH = config.get("compartmenter")
def get_audio_duration(file_path):
    audio = AudioSegment.from_file(file_path)
    return len(audio) / 1000.0  # Convert milliseconds to seconds

def transcribe_with_timing(file_path):
    # Load the model
    model = whisper.load_model("large-v3")
    
    # Get audio duration
    audio_duration = get_audio_duration(file_path)
    
    # Measure transcription time
    start_time = time.time()
    result = model.transcribe(file_path)
    end_time = time.time()
    
    transcription_time = end_time - start_time
    
    return result, audio_duration, transcription_time

def list_audio_files(directory):
    audio_extensions = ('.mp3', '.wav', '.ogg', '.flac', '.m4a', '.wma', '.aac', '.aiff', '.au', '.raw')
    return [f for f in os.listdir(directory) if f.lower().endswith(audio_extensions)]

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio files using Whisper")
    parser.add_argument("--file", help="Specific audio file to transcribe")
    args = parser.parse_args()

    current_dir = os.getcwd()

    if args.file:
        file_path = os.path.join(current_dir, args.file)
        if os.path.exists(file_path):
            process_file(file_path)
        else:
            print(f"File not found: {file_path}")
    else:
        audio_files = list_audio_files(current_dir)
        if not audio_files:
            print("No audio files found in the current directory.")
            return

        print("Available audio files:")
        for i, file in enumerate(audio_files, 1):
            print(f"{i}. {file}")

        while True:
            choice = input("Enter the number of the file to transcribe (or 'q' to quit): ")
            if choice.lower() == 'q':
                return
            try:
                file_index = int(choice) - 1
                if 0 <= file_index < len(audio_files):
                    file_path = os.path.join(current_dir, audio_files[file_index])
                    prefred = prefLang()
                    process_file(file_path, prefred)
                    break
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number or 'q' to quit.")

def process_file(file_path, prefred):
    print(f"Processing file: {file_path}")
    result, audio_duration, transcription_time = transcribe_with_timing(file_path)
    print("\nTranslating file...")
    transated = translator(result['text'],result['language'],prefred)
    print(f"\nTranscription: {result['text']}")
    print(f"\nTranslation: {transated[0].translations[0].translated_text}")
    print(f"Detected Language: {result['language']}")
    print(f"Audio Duration: {audio_duration:.2f} seconds")
    print(f"Transcription Time: {transcription_time:.2f} seconds")
    print(f"Real-time Factor: {audio_duration / transcription_time:.2f}x")

if __name__ == "__main__":
    main()

def translator(input,inLang,outLang):
    uuid = uuid_gen(input)
    batch_language_translation_response =  trans_client.batch_language_translation(
        batch_language_translation_details=oci.ai_language.models.BatchLanguageTranslationDetails(
            documents=[
                oci.ai_language.models.TextDocument(
                    key=uuid,
                    text=input,
                    language_code=inLang)],
            compartment_id=FISH,
            target_language_code=outLang),
        opc_request_id="UEFNLQEL0PID3M4DYU5T"+uuid)
    
    return batch_language_translation_response.data

def uuid_gen(input):
    #get the time with date and time
    t = time.time()
    #convert the time into string
    t = str(t)
    #join with input
    t = input + t
    #hash the string into a unique id of 20 characters
    t = hash(t)
    t = str(t)
    t = t[-20:]
    return t

def prefLang():
    table = printTableLang()
    print("Enter the language code for the output language:")
    print(table)
    outLang = input("Enter the language code for the output language:")
    return outLang

def printTableLang():
    content=""
    with open(file_path, 'r') as file:
        content = [line.strip().split(',') for line in file if line.strip()]
    table = PrettyTable()
    table.field_names = ["Language", "Language Code"]
    
    for language, code in content:
        table.add_row([language, code])
    
    table.align["Language"] = "l"  # Left align the Language column
    table.align["Language Code"] = "c"  # Center align the Language Code column
    
    return table
