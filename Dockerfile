Use an official Python runtime as a parent image
FROM python:3.11-slim

Set the working directory in the container
WORKDIR /app

Copy the requirements file into the container at /app
COPY requirements.txt .

Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

Copy the rest of the application's code into the container at /app
COPY . .

Expose the port the app runs on
EXPOSE 8080

Define environment variable for the port
ENV PORT 8080

Run the application using gunicorn, a production-ready web server.
Gunicorn is configured to listen on the port specified by the PORT env var.
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "main:app"]