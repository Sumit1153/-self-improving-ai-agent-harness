FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY data/benchmark.json data/notes.json ./data/
COPY static ./static
RUN useradd -u 10001 -m appuser && mkdir -p /app/state && chown -R appuser:appuser /app/state
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
