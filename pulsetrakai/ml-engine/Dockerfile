# Minimal ML engine Dockerfile
FROM python:3.11-slim
WORKDIR /ml
COPY . .
RUN pip install --no-cache-dir flask
EXPOSE 9000
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=9000"]

# © PUBLIUS33™ — PulseTrakAI™. All Rights Reserved.
