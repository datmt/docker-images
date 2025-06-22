from flask import Flask, request, jsonify, send_file
import os
from datetime import timedelta
import uuid
from threading import Thread
import io
import torch
from transformers import pipeline

# --- Flask App Initialization ---
app = Flask(__name__)
# Create a directory to store uploaded audio files
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# In-memory dictionary to track task status and results
tasks = {}

# --- Whisper Model Loading (using insanely-fast-whisper) ---
# This uses the Hugging Face pipeline, which insanely-fast-whisper optimizes.
try:
    pipe = pipeline(
        "automatic-speech-recognition",
        model="openai/whisper-base",
    )
    print("Insanely-Fast-Whisper pipeline loaded successfully.")
except Exception as e:
    print(f"Error loading Insanely-Fast-Whisper pipeline: {e}")
    # Exit if the model fails to load, as the app is not functional
    exit()

# --- Core Transcription Function ---
def generate_srt(path, file_name, language='en'):
    """
    Transcribes the audio file using insanely-fast-whisper in a specified language
    and generates an SRT formatted string.
    """
    try:
        # Pass the language to the pipeline using generate_kwargs
        print(f"Starting transcription for {file_name} in language: {language}")
        output = pipe(path, return_timestamps=True, generate_kwargs={"language": language})
        print(f"Transcription successful for {file_name}")

        srt_content = ""
        segment_id = 1
        # The output contains a 'chunks' key with the transcribed segments
        for chunk in output['chunks']:
            start_seconds, end_seconds = chunk['timestamp']
            
            # Create timedelta objects, handling potential None values
            start_time_td = timedelta(seconds=start_seconds or 0)
            end_time_td = timedelta(seconds=end_seconds or 0)

            # Format to hh:mm:ss,ms
            startTime = f"{int(start_time_td.total_seconds()) // 3600:02d}:{int(start_time_td.total_seconds() // 60) % 60:02d}:{int(start_time_td.total_seconds() % 60):02d},{start_time_td.microseconds // 1000:03d}"
            endTime = f"{int(end_time_td.total_seconds()) // 3600:02d}:{int(end_time_td.total_seconds() // 60) % 60:02d}:{int(end_time_td.total_seconds() % 60):02d},{end_time_td.microseconds // 1000:03d}"
            
            text = chunk['text'].strip()
            srt_content += f"{segment_id}\n{startTime} --> {endTime}\n{text}\n\n"
            segment_id += 1
            
        return srt_content
    except Exception as e:
        print(f"Error during transcription: {e}")
        return None

# --- Background Task Function ---
def process_audio_task(task_id, audio_path, file_name, language='en'):
    """
    Function to run the transcription in a background thread.
    Updates the global 'tasks' dictionary with the result.
    """
    print(f"Starting background transcription task: {task_id}")
    srt_result = generate_srt(audio_path, file_name, language=language)
    if srt_result is not None:
        tasks[task_id]['status'] = 'completed'
        tasks[task_id]['result'] = srt_result
        print(f"Transcription completed for task: {task_id}")
    else:
        tasks[task_id]['status'] = 'failed'
        print(f"Transcription failed for task: {task_id}")
    # Clean up the uploaded file after processing
    try:
        os.remove(audio_path)
    except OSError as e:
        print(f"Error removing file {audio_path}: {e}")

# --- API Endpoints ---

@app.route('/tasks', methods=['POST'])
def submit_task():
    """
    Endpoint to submit an audio file for transcription.
    Accepts a 'language' parameter in the form data.
    Starts a background task and returns a task ID.
    """
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    # Get language from form data, default to 'en' (English)
    language = request.form.get('language', 'en')

    task_id = str(uuid.uuid4())
    file_extension = os.path.splitext(audio_file.filename)[1]
    saved_filename = f"{task_id}{file_extension}"
    audio_path = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
    audio_file.save(audio_path)

    tasks[task_id] = {'status': 'processing'}

    # Pass the language to the background thread
    thread = Thread(target=process_audio_task, args=(task_id, audio_path, audio_file.filename, language))
    thread.start()

    return jsonify({"task_id": task_id})

@app.route('/tasks/<task_id>', methods=['GET'])
def get_task_result(task_id):
    """
    Endpoint to check the status of a task and get the SRT result.
    (This endpoint doesn't need changes as the result is self-contained)
    """
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    if task['status'] == 'completed':
        srt_buffer = io.BytesIO(task['result'].encode('utf-8'))
        srt_buffer.seek(0)
        return send_file(
            srt_buffer,
            as_attachment=True,
            download_name=f'{task_id}.srt',
            mimetype='text/plain'
        )
    elif task['status'] == 'failed':
         return jsonify({"status": "failed", "message": "Transcription failed."}), 500
    else:
        return jsonify({"status": task['status']})

@app.route('/transcribe', methods=['POST'])
def transcribe_directly():
    """
    Endpoint to submit an audio file and get the SRT content directly.
    Accepts a 'language' parameter in the form data.
    """
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    # Get language from form data, default to 'en' (English)
    language = request.form.get('language', 'en')
    
    temp_filename = str(uuid.uuid4())
    audio_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
    audio_file.save(audio_path)

    # Pass the language to the transcription function
    srt_result = generate_srt(audio_path, audio_file.filename, language=language)
    
    os.remove(audio_path)

    if srt_result is not None:
        return srt_result, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    else:
        return jsonify({"error": "Failed to transcribe audio"}), 500

# --- Main Execution ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

