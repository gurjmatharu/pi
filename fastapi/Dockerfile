# Use official Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.in .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir pip-tools \
    && pip-compile requirements.in \
    && pip install --no-cache-dir -r requirements.txt

# Copy the app source code
COPY . .

# Expose the port
EXPOSE 8001

# Run FastAPI app
CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8001"]
