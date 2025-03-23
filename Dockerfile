FROM mcr.microsoft.com/playwright:v1.51.1-noble

# Security setup
RUN apt-get update && \
    apt-get install -y xvfb curl && \
    groupadd -r pwuser && \
    useradd -r -g pwuser -G audio,video pwuser && \
    mkdir -p /home/pwuser/Downloads && \
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

# Copy security configurations
COPY docker/apparmor/mcp-browser.profile /etc/apparmor.d/
RUN apparmor_parser -r /etc/apparmor.d/mcp-browser.profile

# Copy application files
COPY src/ /app/src/
COPY docker/xvfb-init.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/xvfb-init.sh

# Change ownership of the application to the non-root user
RUN chown -R pwuser:pwuser /app

# Switch to non-root user
USER pwuser
EXPOSE 7665

CMD ["/usr/local/bin/xvfb-init.sh"]
