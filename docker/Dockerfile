FROM mcr.microsoft.com/playwright:v1.51.1-noble

# Setup directories
RUN mkdir -p /home/pwuser/Downloads && \
    chown -R pwuser:pwuser /home/pwuser

# Install uv
RUN curl -fsSL https://astral.sh/uv/install.sh | bash && \
    echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> /home/pwuser/.bashrc

# Set up the application directory
WORKDIR /app

# Copy pyproject.toml first for dependency installation
COPY pyproject.toml .

# Install dependencies using uv
RUN /root/.cargo/bin/uv pip install -e .

# Install Playwright browsers
RUN python -m playwright install chromium

# Create output directory
RUN mkdir -p /app/output && chown -R pwuser:pwuser /app/output

# Copy application files
COPY src/ /app/src/
COPY mcp-browser/ /app/mcp-browser/

# Change ownership of the application to the non-root user
RUN chown -R pwuser:pwuser /app

# Set necessary environment variables
ENV PYTHONUNBUFFERED=1
ENV SERVER_PORT=7665
ENV OUTPUT_DIR=/app/output

# Switch to non-root user
USER pwuser
EXPOSE 7665

# Command to run the application
CMD ["python", "-m", "uv", "run", "src/main.py"] 