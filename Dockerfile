# This image bundles the optional Terra/AnVIL support (the [terra] extra),
# which pulls in fs.anvilfs -> getm -> bgzip. bgzip 0.3.5 has a C extension
# that includes `longintrepr.h`, a CPython header relocated out of the public
# include path in Python 3.11, so it only compiles on Python 3.10 and earlier.
# Plain `pip install gxabm` (no extra) has no such constraint.
FROM python:3.10-slim-bookworm

WORKDIR /app

# Copy only the files needed for installation
COPY pyproject.toml README.md ./
COPY abm/ abm/

# Install Python 3, pip, build tools, and other required packages
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    gcc \
    libz-dev \
    libbz2-dev \
    liblzma-dev \
    curl \
    jq \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install kubectl directly from binary to avoid GPG signature issues
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/

# Install the Python package with Terra support (python:3.10-slim already
# provides python/pip in an isolated environment, so no venv or symlinks are
# needed).
RUN pip install --no-cache-dir .[terra]

CMD ["abm"]
