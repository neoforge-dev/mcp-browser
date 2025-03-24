FROM mcr.microsoft.com/playwright:v1.51.1-noble

# Security setup
RUN apt-get update && \
    apt-get install -y xvfb curl python3 python3-pip && \
    mkdir -p /home/pwuser/Downloads && \
    chown -R pwuser:pwuser /home/pwuser

# Set up the application directory
WORKDIR /app

# Copy pyproject.toml first for dependency installation
COPY pyproject.toml .

# Install dependencies using pip with system package override
RUN python3 -m pip install --break-system-packages -e .

# Install Playwright browsers
RUN python3 -m playwright install chromium

# Copy security configurations
COPY docker/apparmor/mcp-browser.profile /etc/apparmor.d/
RUN apparmor_parser -r /etc/apparmor.d/mcp-browser.profile || echo "AppArmor profile loading failed - skipping"

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
