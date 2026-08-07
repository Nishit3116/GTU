FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Copy requirement files first for layer caching
COPY pyproject.toml requirements.txt ./

# Install project and dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Copy application source code
COPY gtu_academic_engine ./gtu_academic_engine
COPY gtu_pyq_downloader ./gtu_pyq_downloader
COPY README.md ./

# Set environment variables
ENV PORT=5000
ENV PYTHONUNBUFFERED=1
ENV GTU_LOG_LEVEL=INFO

EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

CMD ["python", "-m", "gtu_academic_engine"]
