FROM mcr.microsoft.com/playwright:v1.50.0-noble

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Install system dependencies needed for Python, venv, Xvfb, curl, ping
    PIP_VERSION=24.0 \
    SETUPTOOLS_VERSION=69.5.1

# Install system packages
RUN apt-get update && apt-get install -y \
    xvfb \
    curl \
    python3 \
    python3-pip \
    python3.12-venv \
    iputils-ping \
    # Clean up apt cache
    && rm -rf /var/lib/apt/lists/*

# Set up virtual environment
ENV VIRTUAL_ENV=/app/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN python3 -m venv $VIRTUAL_ENV

# Upgrade pip and setuptools in venv
RUN $VIRTUAL_ENV/bin/pip install --no-cache-dir --upgrade pip==$PIP_VERSION setuptools==$SETUPTOOLS_VERSION

# Create app directory
WORKDIR /app

# Copy dependency definition files and readme
COPY pyproject.toml requirements-test.txt README.md /app/

# Install test dependencies first
RUN $VIRTUAL_ENV/bin/pip install --no-cache-dir -r requirements-test.txt

# Install application dependencies and the application itself
# This reads dependencies from [project].dependencies in pyproject.toml
RUN $VIRTUAL_ENV/bin/pip install --no-cache-dir .

# Install Playwright browsers (redundant? Playwright base image should have them, but let's ensure)
RUN $VIRTUAL_ENV/bin/playwright install chromium --with-deps

# Copy application source code and tests
COPY src/ /app/src/
COPY tests/ /app/tests/

# Copy and set permissions for the entrypoint script
COPY docker/xvfb-init.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/xvfb-init.sh

# Set the entrypoint
ENTRYPOINT ["/usr/local/bin/xvfb-init.sh"]

# Default command (can be overridden)
CMD ["python3", "src/main.py"]
