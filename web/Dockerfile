FROM python:3.13-slim

WORKDIR /app

COPY web/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

EXPOSE 5000
