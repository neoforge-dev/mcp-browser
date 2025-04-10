FROM mcr.microsoft.com/playwright:v1.50.0-noble

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Install system dependencies needed for Python, venv, Xvfb, curl, ping
    # Pin pip and setuptools for stability
    PIP_VERSION=24.0 \
    SETUPTOOLS_VERSION=69.5.1 \
    # Install Poetry
    POETRY_HOME="/opt/poetry" \
    POETRY_VERSION=1.8.2 \
    PATH="$POETRY_HOME/bin:$PATH"

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

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - --version $POETRY_VERSION

# Create app directory
WORKDIR /app

# Copy dependency definition files
COPY pyproject.toml poetry.lock* /app/

# Install project dependencies using Poetry
# --no-root: Don't install the project itself as editable, only dependencies
# Using --no-cache-dir might not be necessary with Poetry but doesn't hurt
RUN poetry install --no-interaction --no-ansi --no-root --without dev

# Install Playwright browsers (redundant? Playwright base image should have them, but let's ensure)
# Consider removing if base image guarantees browsers
RUN python3 -m playwright install chromium --with-deps

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
