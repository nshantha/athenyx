# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Set work directory
WORKDIR /app

# Install system dependencies required for some Python packages and tree-sitter
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Copy only dependency definition files first to leverage Docker cache
COPY pyproject.toml poetry.lock* ./

# Install project dependencies
# This command will also build tree-sitter language grammars if needed
RUN poetry install --no-root --no-dev && \
    # Pre-build Python grammar (optional but good practice)
    python -c "from tree_sitter_languages import get_parser; get_parser('python')"

# Copy the rest of the application code
COPY . .

# Install the application itself
RUN poetry install --no-dev

# Expose port (FastAPI default)
EXPOSE 8000

# Command to run the application using Uvicorn
# Use --host 0.0.0.0 to allow connections from outside the container
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]