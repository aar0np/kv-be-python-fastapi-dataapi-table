FROM python:3.10-slim

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Copy dependency files first for caching
COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Copy service code
COPY app/main_user.py /app/app/
COPY app/api/v1/endpoints/account_management.py /app/app/api/v1/endpoints/
COPY app/api/v1/dependencies.py /app/app/api/v1/
COPY app/models/ /app/app/models/
COPY app/services/user_service.py /app/app/services/
COPY app/core/ /app/app/core/
COPY app/db/ /app/app/db/

EXPOSE 8000

CMD ["uvicorn", "app.main_user:service_app", "--host", "0.0.0.0", "--port", "8000"] 