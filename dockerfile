# Use Alpine 3.18 with Python 3.10
FROM alpine:3.18

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/app/venv \
    PATH="/app/venv/bin:$PATH"

# Install Python 3.10 and necessary dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    python3-dev \
    build-base \
    libffi-dev \
    openssl-dev \
    gcc \
    musl-dev \
    linux-headers \
    librdkafka \
    librdkafka-dev \
    cyrus-sasl-dev  # Required for SASL

# Set Python 3.10 as default
RUN ln -sf /usr/bin/python3 /usr/bin/python

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Create a virtual environment
RUN python -m venv $VIRTUAL_ENV

# Install dependencies (Force source build for confluent-kafka)
RUN pip install --no-cache-dir --no-binary confluent-kafka -r requirements.txt

# Command to run the application
CMD ["python", "main.py"]
