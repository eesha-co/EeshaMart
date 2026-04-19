FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn httpx transformers torch accelerate

COPY app.py .

EXPOSE 7860

CMD ["python", "app.py"]
