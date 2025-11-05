FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py .
COPY config.py .
COPY logger.py .
COPY database.py .
COPY clients.py .
COPY auth.py .
COPY utils.py .
COPY forwarder.py .
COPY task_manager.py .
COPY message_formatter.py .
COPY command_handlers.py .
COPY button_handlers.py .

# Create logs directory
RUN mkdir -p /app/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the bot
CMD ["python", "main.py"]
