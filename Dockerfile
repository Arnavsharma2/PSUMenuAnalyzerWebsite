FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create cache directory
RUN mkdir -p cache

EXPOSE 8080

ENV PORT 8080

# Use gunicorn for production
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT --timeout 120 --workers 1 --threads 4 main:app"]