import whisper
import time
from pydub import AudioSegment
import os
import argparse
import oci
from prettytable import PrettyTable
from oci.config import from_file
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
# from TTS.api import TTS
import subprocess
import base64 
import shutil
from pathlib import Path
# from TTS.tts.models.xtts import Xtts
# from TTS.tts.configs.xtts_config import XttsConfig
# file_path = "supportLang.txt"
app = Flask(__name__)
CORS(app)
config = from_file(file_location="config")
app.config['PERMANENT_SESSION_LIFETIME'] = 300  # seconds
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 300  # seconds
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB limit
trans_client = oci.ai_language.AIServiceLanguageClient(config)

FISH = config.get("compartmenter")
TEMP_DIR = "temp_files"  # Define temp directory name

# Create temp directory if it doesn't exist
Path(TEMP_DIR).mkdir(parents=True, exist_ok=True)

# modelWHISPER = whisper.load_model("turbo")

print('Initing TTS...')
print("Loading model...")
# config = XttsConfig()
# config.load_json("/path/to/xtts/config.json")
# tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
# model.load_checkpoint(config, use_deepspeed=True)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ensure_mp3_format(input_path, output_path):
    """Convert any audio file to MP3 format with proper timestamp handling"""
    try:
        command = [
            'ffmpeg',
            '-y',  # Overwrite output files
            '-i', input_path,  # Input file
            '-codec:a', 'libmp3lame',  # Use MP3 codec
            '-qscale:a', '2',  # Quality setting (2 is high quality)
            '-ar', '44100',  # Sample rate
            '-ac', '2',  # Number of audio channels (stereo)
            '-filter:a', 'asetpts=PTS-STARTPTS',  # Reset timestamps
            '-max_muxing_queue_size', '9999',  # Increase buffer size
            output_path
        ]

        # Run the command and capture output
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        # Verify the output file exists and has size > 0
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"Conversion to MP3 successful: {output_path}")
            return True
        else:
            logger.error("Output file is empty or was not created")
            return False

    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr.decode()}")
        return False
    except Exception as e:
        logger.error(f"An error occurred during MP3 conversion: {str(e)}")
        return False

def ensure_wav_format(input_path, output_path):
    """Convert any audio file to WAV format with specific parameters"""
    try:
        # Set up FFmpeg command with specific parameters for consistent output
        command = [
            'ffmpeg',
            '-i', input_path,  # Input file
            '-acodec', 'pcm_s16le',  # Use PCM 16-bit encoding
            '-ar', '44100',  # Set sample rate to 44.1kHz
            '-ac', '2',  # Set to stereo (2 channels)
            '-y',  # Overwrite output file if it exists
            output_path
        ]
        
        # Run the FFmpeg command and capture output
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        
        # Check if output file was created and has size > 0
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"Conversion to WAV successful: {output_path}")
            return True
        else:
            logger.error("Output file is empty or was not created")
            return False
            
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr.decode()}")
        logger.error(f"An error occurred during WAV conversion: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during conversion: {str(e)}")
        return False

def verify_audio_file(file_path):
    """Verify that an audio file is valid and get its properties"""
    try:
        command = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'a:0',
            '-show_entries', 'stream=codec_name,channels,sample_rate',
            '-of', 'json',
            file_path
        ]
        
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            return True
        return False
    except Exception as e:
        logger.error(f"Error verifying audio file: {str(e)}")
        return False

def cleanup_user_directory(user_id, preserve_source=False):
    """Clean up temporary directory for a specific user"""
    user_dir = os.path.join(TEMP_DIR, f'temp_audio_{user_id}')
    try:
        if os.path.exists(user_dir):
            if preserve_source:
                # Keep SOURCE files, remove everything else
                for file in os.listdir(user_dir):
                    file_path = os.path.join(user_dir, file)
                    if not 'SOURCE' in file and os.path.isfile(file_path):
                        os.remove(file_path)
            else:
                # Remove everything including the directory
                shutil.rmtree(user_dir)
            logger.info(f"Cleaned up directory: {user_dir} (preserve_source={preserve_source})")
    except Exception as e:
        logger.error(f"Error cleaning up user directory: {e}")

def getSourceFiles(user_id):
    """Get list of source files for a specific user"""
    user_dir = os.path.join(TEMP_DIR, f'temp_audio_{user_id}')
    source_files = [f for f in os.listdir(user_dir) if 'SOURCE' in f]
    return source_files


# def generate_speech(text, speaker_wav_path, output_path, language, user_id):
#     """
#     Generate speech using TTS with voice cloning and customizable parameters
    
#     Args:
#         text (str): Text to convert to speech
#         speaker_wav_path (str): Path to speaker WAV file for voice cloning
#         output_path (str): Path to save the generated speech
#         language (str): Target language code
#         user_id (str): User ID for cleanup in case of failure
#     """
#     try:
#         if language == 'zh-CN':
#             language = 'zh-cn'
#         # Generate speech with optimized parameters
#         tts.tts_to_file(
#             text=text,
#             file_path=output_path,
#             speaker_wav=speaker_wav_path,
#             language=language,
#             temperature=0.65,           # Balanced between variety and stability
#             num_beams=1,       # Default length penalty
#             repetition_penalty=2.2,    # Slightly increased to reduce repetition
#             top_k=55,                 # Default diversity parameter
#             top_p=0.85,               # Slightly increased for more natural speech
#             speed=1.0,                # Default speed
#             enable_text_splitting=True # Enable text splitting for better handling
#         )
        
#         logger.info(f"Speech generated successfully: {output_path}")
#         return True, None
        
#     except Exception as e:
#         error_msg = f"An error occurred during speech generation: {str(e)}"
#         logger.exception(error_msg)
#         cleanup_user_directory(user_id, preserve_source=True)
#         return False, error_msg

def get_audio_duration(file_path):
    try:
        audio = AudioSegment.from_file(file_path)
        return len(audio) / 1000.0  # Convert milliseconds to seconds
    except Exception as e:
        logger.error(f"Error getting audio duration: {str(e)}")
        raise

# def transcribe_with_timing(file_path):
#     try:
#         audio_duration = get_audio_duration(file_path)
#         start_time = time.time()
#         result = modelWHISPER.transcribe(file_path)
#         end_time = time.time()
#         transcription_time = end_time - start_time
#         return result, audio_duration, transcription_time
#     except Exception as e:
#         logger.error(f"Error during transcription: {str(e)}")
#         raise

# def translator(input_text, in_lang, out_lang):
#     try:
#         uuid = uuid_gen(input_text)
#         batch_language_translation_response = trans_client.batch_language_translation(
#             batch_language_translation_details=oci.ai_language.models.BatchLanguageTranslationDetails(
#                 documents=[
#                     oci.ai_language.models.TextDocument(
#                         key=uuid,
#                         text=input_text,
#                         language_code=in_lang)],
#                 compartment_id=FISH,
#                 target_language_code=out_lang),
#             opc_request_id="UEFNLQEL0PID3M4DYU5T"+uuid)
        
#         response_dict = json.loads(str(batch_language_translation_response.data))
        
#         if response_dict['documents']:
#             return response_dict['documents'][0]['translated_text']
#         else:
#             logger.error("Translation failed: No documents in response")
#             return "Translation failed"
#     except Exception as e:
#         logger.error(f"Error during translation: {str(e)}")
#         raise

def uuid_gen(input):
    t = str(time.time())
    t = input + t
    t = hash(t)
    t = str(t)
    t = t[-20:]
    return t

# def batch_translate_segments(segments, source_lang, target_lang):
#     translations = []
#     for segment in segments:
#         logger.info(f"Translating segment: {segment['start']:.2f}s - {segment['end']:.2f}s")
#         translated_text = translator(segment['text'], source_lang, target_lang)
#         translations.append(translated_text)
#     return translations

@app.route('/process', methods=['POST'])
def process_audio():
    try:
        # Validate request and extract parameters
        if 'file' not in request.files:
            logger.error("No file part in the request")
            return jsonify({'error': 'No file part in the request'}), 400
        
        file = request.files['file']
        targetLang = request.form.get('targetLang')
        userID = request.form.get('userID')
        sourceName = request.form.get('sourceName')
        
        logger.info(request.form)

        # Validate parameters
        if file.filename == '':
            logger.error("No selected file")
            return jsonify({'error': 'No selected file'}), 400
        if not targetLang or targetLang == '':
            logger.error("No target language specified")
            return jsonify({'error': 'No target language specified'}), 400
        if not userID or userID == '':
            logger.error("No user ID specified")
            return jsonify({'error': 'No user ID specified'}), 400
        
        # Set up user directory
        user_dir = os.path.join(TEMP_DIR, f'temp_audio_{userID}')
        Path(user_dir).mkdir(parents=True, exist_ok=True)
        
        # Handle source files
        source_files = [f for f in os.listdir(user_dir) if 'SOURCE' in f]
        voice_file = None
        
        if sourceName:
            voice_file = os.path.join(user_dir, f'input_{sourceName}_SOURCE.wav')
            if not os.path.exists(voice_file):
                logger.warning(f"Specified source file {sourceName} not found")
                voice_file = None
        
        if not voice_file and source_files:
            voice_file = os.path.join(user_dir, source_files[0])
            logger.info(f"Using default source file: {voice_file}")
        
        # Save and convert input file to MP3 for transcription
        input_temp_path = os.path.join(user_dir, 'input_temp')
        file.save(input_temp_path)
        input_mp3_path = os.path.join(user_dir, 'input.mp3')
        if not ensure_mp3_format(input_temp_path, input_mp3_path):
            cleanup_user_directory(userID, preserve_source=True)
            return jsonify({'error': 'Failed to convert input to MP3'}), 500
        
        # Convert input to WAV for TTS
        input_wav_path = os.path.join(user_dir, 'input.wav')
        if not ensure_wav_format(input_temp_path, input_wav_path):
            cleanup_user_directory(userID, preserve_source=True)
            return jsonify({'error': 'Failed to convert input to WAV'}), 500
        
        os.remove(input_temp_path)
        
        # Process audio
        logger.info(f"Processing file: {input_mp3_path}")
        logger.info(f"Using voice file: {voice_file if voice_file else 'No source file'}")
        
        # Transcribe and translate
        # result, audio_duration, transcription_time = transcribe_with_timing(input_mp3_path)
        # segments = result['segments']
        # batched_translations = batch_translate_segments(segments, result['language'], targetLang)
        # translated = ' '.join(batched_translations)

        # Generate speech
        # wav_output = os.path.join(user_dir, 'output.wav')
        speaker_wav = voice_file if voice_file else input_wav_path
        # print("used speaker wav files",speaker_wav)
        # success, error = generate_speech(
        #     text=translated,
        #     speaker_wav_path=speaker_wav,
        #     output_path=wav_output,
        #     language=targetLang,
        #     user_id=userID
        # )
        
        # if not success:
        #     return jsonify({'error': error}), 500

        # Convert output to MP3
        output_mp3_path = os.path.join(user_dir, 'output.mp3')
        if not ensure_mp3_format(speaker_wav, output_mp3_path):
            cleanup_user_directory(userID, preserve_source=True)
            return jsonify({'error': 'Failed to convert output to MP3'}), 500
        
        # Create response
        with open(output_mp3_path, 'rb') as f:
            audio_data = f.read()
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
        json_response= {
            "audio_duration": 5,
            "transcription_time": 5,
            "time_ratio_trans": 5,
            "result": "Sample Transcription result",
            "transalated": "Sample Translation result",
            "source_lang": "en",
            "target_lang": "en",
            "audio_data": audio_base64,
            "audio_filename": f"processed_audio_{userID}.mp3",
            "content_type": "audio/mpeg",
            'using_source_voice': voice_file is not None,
            'source_file_used': os.path.basename(voice_file) if voice_file else None,
            'available_sources': source_files}
        cleanup_user_directory(userID, preserve_source=True)
        return jsonify(json_response)
        
    except Exception as e:
        logger.exception(f"An error occurred during audio processing: {str(e)}")
        if 'userID' in locals():
            cleanup_user_directory(userID, preserve_source=True)
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            logger.error("No file part in the request")
            return jsonify({'error': 'No file part in the request'}), 400
        
        userID = request.form.get('userID')
        files = request.files.getlist('file')
        
        if len(files) == 0:
            logger.error("No selected file")
            return jsonify({'error': 'No selected file'}), 400
        if not userID or userID == '' or userID is None:
            logger.error("No user ID specified")
            return jsonify({'error': "No user ID specified"}), 400
        
        # Create user-specific directory
        user_dir = os.path.join(TEMP_DIR, f'temp_audio_{userID}')
        Path(user_dir).mkdir(parents=True, exist_ok=True)
        
        successfully_processed = 0
        failed_files = []
        processed_files = []

        for i, file in enumerate(files):
            try:
                # Save original file
                original_path = os.path.join(user_dir, f'temp_upload_original_{i}')
                file.save(original_path)
                
                # Verify the uploaded file is a valid audio file
                if not verify_audio_file(original_path):
                    logger.error(f"File {file.filename} is not a valid audio file")
                    failed_files.append({
                        'filename': file.filename,
                        'error': 'Invalid audio file'
                    })
                    continue

                # Generate unique output filename
                counter = 1
                base_name = "input_SOURCE.wav"
                output_path = os.path.join(user_dir, base_name)
                while os.path.exists(output_path):
                    base_name = f"input_SOURCE_{counter}.wav"
                    output_path = os.path.join(user_dir, base_name)
                    counter += 1

                # Convert file to WAV
                if ensure_wav_format(original_path, output_path):
                    successfully_processed += 1
                    processed_files.append({
                        'original_name': file.filename,
                        'converted_name': base_name
                    })
                    logger.info(f"Successfully processed {file.filename} to {base_name}")
                else:
                    failed_files.append({
                        'filename': file.filename,
                        'error': 'Conversion failed'
                    })

            except Exception as e:
                logger.error(f"Error processing file {file.filename}: {str(e)}")
                failed_files.append({
                    'filename': file.filename,
                    'error': str(e)
                })
                
            finally:
                # Clean up temporary file
                if os.path.exists(original_path):
                    os.remove(original_path)

        # Prepare response
        source_files = [f for f in os.listdir(user_dir) if 'SOURCE' in f]
        
        response_data = {
            'message': f'Processed {successfully_processed} of {len(files)} files successfully',
            'files_processed': successfully_processed,
            'total_files': len(files),
            'source_files': source_files,
            'processed_files': processed_files
        }
        
        if failed_files:
            response_data['failed_files'] = failed_files
            
        if successfully_processed == 0:
            response_data['error'] = 'All file conversions failed'
            return jsonify(response_data), 400

        return jsonify(response_data)
        
    except Exception as e:
        logger.exception("An error occurred during file upload")
        if 'userID' in locals():
            cleanup_user_directory(userID, preserve_source=True)
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500


if __name__ == "__main__":
    # Ensure temp directory exists when starting the application
    Path(TEMP_DIR).mkdir(parents=True, exist_ok=True)
    app.run(host='127.0.0.1', port=8000, debug=True)