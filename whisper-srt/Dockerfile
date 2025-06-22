# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required by whisper and ffmpeg
# Update package lists and install ffmpeg which is crucial for audio processing.
# Also install build-essential for any C extensions that might be compiled during pip install.
RUN apt-get update && apt-get install -y ffmpeg build-essential

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# Using --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable
ENV FLASK_APP=main.py

# Run main.py when the container launches
# Use gunicorn for a production-ready server, but flask's dev server is fine for this example.
# We'll stick to the dev server for simplicity here.
CMD ["flask", "run", "--host=0.0.0.0"]

