FROM python:3.10-slim

# Set workdir
WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Copy dependency definitions first for better layer caching
COPY pyproject.toml poetry.lock ./

# Install dependencies (no dev, no root install)
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Copy application code required by the Account service
COPY app/main_account.py /app/app/
COPY app/api/v1/endpoints/account_management.py /app/app/api/v1/endpoints/
COPY app/api/v1/dependencies.py /app/app/api/v1/
COPY app/models/ /app/app/models/
COPY app/services/user_service.py /app/app/services/
COPY app/core/ /app/app/core/
COPY app/db/ /app/app/db/

# Expose service port
EXPOSE 8000

# Launch
CMD ["uvicorn", "app.main_account:service_app", "--host", "0.0.0.0", "--port", "8000"] 