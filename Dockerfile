FROM python:3.11-slim

WORKDIR /app

# Copy only the files needed for installation
COPY pyproject.toml README.md ./
COPY abm/ abm/

RUN pip install --no-cache-dir .

ENTRYPOINT ["abm"]
