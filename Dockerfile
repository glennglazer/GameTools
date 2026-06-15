FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y \
    less \
    vim \
    git \
    && rm -rf /var/lib/apt/lists/*