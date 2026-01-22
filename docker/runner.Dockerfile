# Minimal Python image for running code securely
FROM python:3.10-slim

# Install only pytest (needed to run tests)
RUN pip install --no-cache-dir pytest

# Create non-root user for security
RUN useradd -m -s /bin/bash testrunner

# Switch to non-root user
USER testrunner

# Set working directory
WORKDIR /home/testrunner

# Default command (will be overridden at runtime)
CMD ["python", "--version"]