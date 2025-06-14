# Use a slim Python base image for a smaller final image size
FROM python:3.11-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
# Using --no-cache-dir and --upgrade pip for efficiency and best practices
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY app.py .

# Expose the port that Gunicorn will listen on
# This is an internal port within the container; your Nginx proxy will map to this.
EXPOSE 5000

# Command to run the application using Gunicorn
# -b 0.0.0.0:5000: Binds Gunicorn to all network interfaces on port 5000
# -w 2: Runs with 2 worker processes (adjust based on your server's cores/load)
# app:app: Specifies the Flask application instance (app object in app.py)
CMD ["gunicorn", "-b", "0.0.0.0:5000", "-w", "2", "app:app"]