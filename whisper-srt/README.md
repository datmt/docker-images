# High-Performance Whisper Transcription API

This project provides a robust, high-performance API for generating subtitles (`.srt` files) from audio files using an optimized version of OpenAI's Whisper model. It is built with Flask and packaged in a Docker container for easy deployment and scaling.

The API leverages `insanely-fast-whisper` to deliver significantly faster transcription speeds compared to the original implementation, making it suitable for production workloads.

## Features

-   **Three Versatile Endpoints:**
    1.  **Synchronous:** Upload an audio file and get the SRT content back immediately.
    2.  **Asynchronous:** Submit a transcription job and receive a task ID.
    3.  **Status Check:** Use the task ID to retrieve the SRT file once transcription is complete.
-   **Multi-language Support:** Specify the audio language for accurate transcription. Defaults to English (`en`).
-   **High Performance:** Built with `insanely-fast-whisper` for optimized CPU and GPU performance.
-   **Containerized:** Packaged with Docker for portability and straightforward deployment on any platform that supports containers.

## Prerequisites

Before you begin, ensure you have the following installed on your system:

-   [Docker](https://docs.docker.com/get-docker/)

## Project Structure

```
.
├── Dockerfile          # Defines the Docker container environment.
├── main.py             # The Flask application with all API logic.
└── requirements.txt    # Python dependencies.
```

## Setup and Installation

Follow these steps to build the Docker image for the application.

1.  **Clone/Download the Project:**
    Ensure you have the `main.py`, `Dockerfile`, and `requirements.txt` files in the same directory.

2.  **Build the Docker Image:**
    Open a terminal in the project's root directory and run the following command. This will build the image and tag it as `whisper-api`.

    ```bash
    docker build -t whisper-api .
    ```

    *Note: This process may take some time as it downloads the base Python image, installs system dependencies like `ffmpeg`, and installs all Python packages including the large `torch` library and the Whisper model files.*

## Running the Application

Once the image is successfully built, you can run it as a container:

```bash
docker run -p 5000:5000 whisper-api
```

This command starts the container and maps port `5000` of the container to port `5000` on your host machine. You should see output from Flask and the model loading process, ending with a line indicating the server is running. The API is now accessible at `http://localhost:5000`.

## API Endpoints Guide

You can interact with the API using any HTTP client, such as `curl` or Postman.

---

### 1. Direct Transcription (Synchronous)

This endpoint is for quick, blocking transcription requests. You send an audio file and receive the SRT text in the response body.

-   **URL:** `/transcribe`
-   **Method:** `POST`
-   **Request Body:** `multipart/form-data`
    -   `audio`: The audio file to transcribe (e.g., `.mp3`, `.wav`, `.m4a`). (Required)
    -   `language`: The two-letter language code (e.g., `es`, `fr`, `de`). Defaults to `en`. (Optional)

**Example (English):**
```bash
curl -X POST -F "audio=@/path/to/your/audio.mp3" http://localhost:5000/transcribe
```

**Example (Spanish):**
```bash
curl -X POST \
  -F "audio=@/path/to/your/audio.mp3" \
  -F "language=es" \
  http://localhost:5000/transcribe
```

**Success Response:**
-   **Code:** `200 OK`
-   **Body:** The raw SRT content as plain text.

---

### 2. Submit Transcription Task (Asynchronous)

This endpoint is ideal for long audio files. It accepts the file, starts a background transcription process, and immediately returns a unique `task_id`.

-   **URL:** `/tasks`
-   **Method:** `POST`
-   **Request Body:** `multipart/form-data`
    -   `audio`: The audio file to transcribe. (Required)
    -   `language`: The two-letter language code. Defaults to `en`. (Optional)

**Example:**
```bash
curl -X POST \
  -F "audio=@/path/to/a/long_podcast.mp3" \
  -F "language=en" \
  http://localhost:5000/tasks
```

**Success Response:**
-   **Code:** `200 OK`
-   **Body:** A JSON object with the task ID.
    ```json
    {
      "task_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
    }
    ```

---

### 3. Retrieve Task Result

Use this endpoint to check the status of an asynchronous job and get the result when it's ready.

-   **URL:** `/tasks/<task_id>`
-   **Method:** `GET`

**Example:**
```bash
# Use the task_id from the previous step
curl http://localhost:5000/tasks/a1b2c3d4-e5f6-7890-1234-567890abcdef
```

**Responses:**

-   **If Processing:**
    -   **Code:** `200 OK`
    -   **Body:**
        ```json
        {
          "status": "processing"
        }
        ```
-   **If Completed:**
    -   **Code:** `200 OK`
    -   **Body:** The response will trigger a file download of `<task_id>.srt` containing the subtitle data.
-   **If Failed:**
    -   **Code:** `500 Internal Server Error`
    -   **Body:**
        ```json
        {
          "status": "failed",
          "message": "Transcription failed."
        }
        ```
-   **If Not Found:**
    -   **Code:** `404 Not Found`
    -   **Body:**
        ```json
        {
          "error": "Task not found"
        }
        ```

## Notes on Deployment

-   **Statelessness:** This application uses an in-memory dictionary to track asynchronous tasks. This is suitable for single-container deployments. If you scale to multiple containers, a shared task queue and result store (like Redis or RabbitMQ) would be necessary.
-   **Cloud Deployment:** For production, it is highly recommended to deploy this container to a service like **AWS Fargate** or **Amazon EC2** rather than a serverless platform like AWS Lambda, due to long cold-start times and the stateful nature of the async task handler.

