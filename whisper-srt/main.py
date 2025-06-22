from flask import Flask, request, jsonify, send_file
import whisper
import os
from datetime import timedelta
import uuid
from threading import Thread
import io

# --- Flask App Initialization ---
app = Flask(__name__)
# Create a directory to store uploaded audio files
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# In-memory dictionary to track task status and results
tasks = {}

# --- Whisper Model Loading ---
# Load the Whisper model once when the application starts
try:
    model = whisper.load_model("base")
    print("Whisper model loaded successfully.")
except Exception as e:
    print(f"Error loading Whisper model: {e}")
    # Exit if the model fails to load, as the app is not functional
    exit()

# --- Core Transcription Function ---
def generate_srt(path, file_name):
    """
    Transcribes the audio file and generates an SRT formatted string.
    """
    try:
        transcribe_result = model.transcribe(audio=path)
        segments = transcribe_result['segments']
        srt_content = ""
        for segment in segments:
            startTime = str(0) + str(timedelta(seconds=int(segment['start']))) + ',000'
            endTime = str(0) + str(timedelta(seconds=int(segment['end']))) + ',000'
            text = segment['text']
            segmentId = segment['id'] + 1
            # Ensure text is clean and doesn't start with a space
            clean_text = text.strip()
            srt_content += f"{segmentId}\n{startTime} --> {endTime}\n{clean_text}\n\n"
        return srt_content
    except Exception as e:
        print(f"Error during transcription: {e}")
        return None

# --- Background Task Function ---
def process_audio_task(task_id, audio_path, file_name):
    """
    Function to run the transcription in a background thread.
    Updates the global 'tasks' dictionary with the result.
    """
    print(f"Starting transcription for task: {task_id}")
    srt_result = generate_srt(audio_path, file_name)
    if srt_result:
        tasks[task_id]['status'] = 'completed'
        tasks[task_id]['result'] = srt_result
        print(f"Transcription completed for task: {task_id}")
    else:
        tasks[task_id]['status'] = 'failed'
        print(f"Transcription failed for task: {task_id}")
    # Clean up the uploaded file after processing
    os.remove(audio_path)

# --- API Endpoints ---

@app.route('/tasks', methods=['POST'])
def submit_task():
    """
    Endpoint to submit an audio file for transcription.
    Starts a background task and returns a task ID.
    """
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Generate a unique task ID
    task_id = str(uuid.uuid4())
    
    # Save the uploaded file temporarily
    file_extension = os.path.splitext(audio_file.filename)[1]
    saved_filename = f"{task_id}{file_extension}"
    audio_path = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
    audio_file.save(audio_path)

    # Initialize task status
    tasks[task_id] = {'status': 'processing'}

    # Start the transcription in a background thread
    thread = Thread(target=process_audio_task, args=(task_id, audio_path, audio_file.filename))
    thread.start()

    return jsonify({"task_id": task_id})

@app.route('/tasks/<task_id>', methods=['GET'])
def get_task_result(task_id):
    """
    Endpoint to check the status of a task and get the SRT result.
    """
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    if task['status'] == 'completed':
        # Create an in-memory file for the SRT content
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
    """
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    # Save the file to a temporary path
    temp_filename = str(uuid.uuid4())
    audio_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
    audio_file.save(audio_path)

    # Perform transcription
    srt_result = generate_srt(audio_path, audio_file.filename)
    
    # Clean up the temporary file
    os.remove(audio_path)

    if srt_result:
        return srt_result, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    else:
        return jsonify({"error": "Failed to transcribe audio"}), 500

# --- Main Execution ---
if __name__ == '__main__':
    # Running on 0.0.0.0 makes it accessible from outside the container
    app.run(host='0.0.0.0', port=5000)

