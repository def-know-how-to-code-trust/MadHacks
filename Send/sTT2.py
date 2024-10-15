import whisper
import time
from pydub import AudioSegment
import os
import argparse
import oci
from prettytable import PrettyTable
from oci.config import from_file
import json

file_path = "supportLang.txt"

config = from_file(file_location="config")
trans_client = oci.ai_language.AIServiceLanguageClient(config)

FISH = config.get("compartmenter")

model = whisper.load_model("turbo")

def get_audio_duration(file_path):
    audio = AudioSegment.from_file(file_path)
    return len(audio) / 1000.0  # Convert milliseconds to seconds

def transcribe_with_timing(file_path):
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

    while True:
        if args.file:
            file_path = os.path.join(current_dir, args.file)
            if os.path.exists(file_path):
                preferred_lang = prefLang()
                process_file(file_path, preferred_lang)
            else:
                print(f"File not found: {file_path}")
            args.file = None  # Reset the file argument after processing
        else:
            audio_files = list_audio_files(current_dir)
            if not audio_files:
                print("No audio files found in the current directory.")
                break

            print("\nAvailable audio files:")
            for i, file in enumerate(audio_files, 1):
                print(f"{i}. {file}")
            print("q. Quit the program")

            choice = input("Enter the number of the file to transcribe (or 'q' to quit): ")
            if choice.lower() == 'q':
                break
            try:
                file_index = int(choice) - 1
                if 0 <= file_index < len(audio_files):
                    file_path = os.path.join(current_dir, audio_files[file_index])
                    preferred_lang = prefLang()
                    process_file(file_path, preferred_lang)
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number or 'q' to quit.")

        print("\nWould you like to process another file?")
        continue_choice = input("Enter 'y' to continue or any other key to quit: ")
        if continue_choice.lower() != 'y':
            break

    print("Thank you for using the audio transcription and translation tool. Goodbye!")

def translator(input_text, in_lang, out_lang):
    uuid = uuid_gen(input_text)
    batch_language_translation_response = trans_client.batch_language_translation(
        batch_language_translation_details=oci.ai_language.models.BatchLanguageTranslationDetails(
            documents=[
                oci.ai_language.models.TextDocument(
                    key=uuid,
                    text=input_text,
                    language_code=in_lang)],
            compartment_id=FISH,
            target_language_code=out_lang),
        opc_request_id="UEFNLQEL0PID3M4DYU5T"+uuid)
    
    # Parse the JSON response
    response_dict = json.loads(str(batch_language_translation_response.data))
    
    # Extract the translated text from the response
    if response_dict['documents']:
        return response_dict['documents'][0]['translated_text']
    else:
        return "Translation failed"

def uuid_gen(input):
    t = str(time.time())
    t = input + t
    t = hash(t)
    t = str(t)
    t = t[-20:]
    return t

def prefLang():
    table = printTableLang()
    print("Enter the language code for the output language:")
    print(table)
    outLang = input("Enter the language code for the output language: ")
    return outLang

def printTableLang():
    content = ""
    with open(file_path, 'r') as file:
        content = [line.strip().split(',') for line in file if line.strip()]
    table = PrettyTable()
    table.field_names = ["Language", "Language Code"]
    
    for language, code in content:
        table.add_row([language, code])
    
    table.align["Language"] = "l"  # Left align the Language column
    table.align["Language Code"] = "c"  # Center align the Language Code column
    
    return table

def batch_translate_segments(segments, source_lang, target_lang):
    translations = []
    for segment in segments:
        print(f"Translating segment: {segment['start']:.2f}s - {segment['end']:.2f}s")
        translated_text = translator(segment['text'], source_lang, target_lang)
        translations.append(translated_text)
    return translations

def process_file(file_path, preferred_lang):
    print(f"Processing file: {file_path}")
    result, audio_duration, transcription_time = transcribe_with_timing(file_path)
    
    print(f"\nDetected Language: {result['language']}")
    print(f"Audio Duration: {audio_duration:.2f} seconds")
    print(f"Transcription Time: {transcription_time:.2f} seconds")
    print(f"Real-time Factor: {audio_duration / transcription_time:.2f}x")

    # Process segments
    segments = result['segments']
    batched_translations = batch_translate_segments(segments, result['language'], preferred_lang)

    # Print results
    print("\nTranscription and Translation:")
    for segment, translation in zip(segments, batched_translations):
        print(f"\nTimestamp: {segment['start']:.2f}s - {segment['end']:.2f}s")
        print(f"Transcription: {segment['text']}")
        print(f"Translation: {translation}")

if __name__ == "__main__":
    main()