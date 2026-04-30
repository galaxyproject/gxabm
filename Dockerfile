FROM ubuntu:24.04

WORKDIR /app

# Copy only the files needed for installation
COPY pyproject.toml README.md ./
COPY abm/ abm/

# Install Python 3, pip, and other required packages
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    jq \
    apt-transport-https \
    ca-certificates \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Create symlinks for python and pip to work without the '3' suffix
RUN ln -sf /usr/bin/python3 /usr/bin/python \
    && ln -sf /usr/bin/pip3 /usr/bin/pip

# Install kubectl directly from binary to avoid GPG signature issues
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/

# Create a virtual environment and install the Python package
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir .

CMD ["abm"]
