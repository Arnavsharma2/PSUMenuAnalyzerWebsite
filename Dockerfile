FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

ENV PORT 8080

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT --timeout 90 main:app"]