FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir poetry==1.7.1

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Video service code
COPY app/main_video.py /app/app/
COPY app/api/v1/endpoints/video_catalog.py /app/app/api/v1/endpoints/
COPY app/api/v1/endpoints/flags.py /app/app/api/v1/endpoints/
COPY app/api/v1/dependencies.py /app/app/api/v1/
COPY app/models/ /app/app/models/
COPY app/services/ /app/app/services/
COPY app/core/ /app/app/core/
COPY app/db/ /app/app/db/

EXPOSE 8000

CMD ["uvicorn", "app.main_video:service_app", "--host", "0.0.0.0", "--port", "8000"] 