FROM python:3.10-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn httpx transformers torch accelerate

# Copy application files
COPY app.py .
COPY static/ ./static/

# Expose port for Hugging Face Spaces
EXPOSE 7860

CMD ["python", "app.py"]
