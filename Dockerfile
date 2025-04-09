FROM mcr.microsoft.com/playwright:v1.51.1-noble

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    xvfb \
    curl \
    python3 \
    python3-pip \
    python3.12-venv \
    iputils-ping \
    netcat-openbsd \
    apparmor-utils \
    dbus \
    && rm -rf /var/lib/apt/lists/*

# Set up virtual environment
ENV VIRTUAL_ENV=/app/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONPATH=/app
RUN python3 -m venv $VIRTUAL_ENV

# Install Python dependencies
COPY pyproject.toml requirements-test.txt /app/
WORKDIR /app
RUN pip install --no-cache-dir -r requirements-test.txt

# Install Playwright browsers
RUN python3 -m playwright install chromium

# Copy application files
COPY src/ /app/src/
COPY tests/ /app/tests/

# Copy Xvfb init script
COPY docker/xvfb-init.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/xvfb-init.sh

# Set environment variables
ENV DISPLAY=:99
ENV RUN_TESTS=false

# Start Xvfb and run application or tests
CMD ["/usr/local/bin/xvfb-init.sh"]
