# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.13.3-slim

EXPOSE 8000

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install Poetry
RUN pip install poetry

# Configure Poetry: Don't create virtual environment, install dependencies globally
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=0 \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    POETRY_REQUESTS_TIMEOUT=120

# Set work directory
WORKDIR /app

# Copy Poetry files from app directory
COPY app/pyproject.toml app/poetry.lock ./

# Install dependencies (including dev dependencies for non-prod)
# Retry to tolerate transient network timeouts from package indexes.
RUN poetry config virtualenvs.create false && \
    for i in 1 2 3; do poetry install && break || (echo "poetry install failed, retry $i/3" && sleep 10); done && \
    rm -rf $POETRY_CACHE_DIR

# Copy application code from app directory
COPY app/ /app/

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["gunicorn", "-c", "gunicorn.conf.py", "main:app"]