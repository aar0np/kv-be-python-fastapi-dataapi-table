FROM python:3.10-slim

# Set workdir
WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Copy dependency definitions first for caching
COPY pyproject.toml poetry.lock ./

# Install runtime dependencies only
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Copy application code required by the Video Catalog service
COPY app/main_video_catalog.py /app/app/
COPY app/api/v1/endpoints/video_catalog.py /app/app/api/v1/endpoints/
COPY app/api/v1/endpoints/flags.py /app/app/api/v1/endpoints/
COPY app/api/v1/dependencies.py /app/app/api/v1/
COPY app/models/ /app/app/models/
COPY app/services/video_service.py /app/app/services/
COPY app/services/flag_service.py /app/app/services/
COPY app/services/recommendation_service.py /app/app/services/
COPY app/services/comment_service.py /app/app/services/
COPY app/core/ /app/app/core/
COPY app/db/ /app/app/db/

# Expose HTTP port
EXPOSE 8000

CMD ["uvicorn", "app.main_video_catalog:service_app", "--host", "0.0.0.0", "--port", "8000"] 