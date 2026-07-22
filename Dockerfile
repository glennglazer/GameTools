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

ARG USER_ID=1000
ARG GROUP_ID=1000

RUN groupadd -g ${GROUP_ID} myuser && \
    useradd -u ${USER_ID} -g myuser -m -s /bin/bash myuser

USER myuser