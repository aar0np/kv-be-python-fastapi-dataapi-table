FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir poetry==1.7.1

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Recommendation service
COPY app/main_reco.py /app/app/
COPY app/api/v1/endpoints/recommendations_feed.py /app/app/api/v1/endpoints/
COPY app/api/v1/endpoints/reco_internal.py /app/app/api/v1/endpoints/
COPY app/api/v1/dependencies.py /app/app/api/v1/
COPY app/models/ /app/app/models/
COPY app/services/recommendation_service.py /app/app/services/
COPY app/services/video_service.py /app/app/services/
COPY app/services/comment_service.py /app/app/services/
COPY app/core/ /app/app/core/
COPY app/db/ /app/app/db/

EXPOSE 8000

CMD ["uvicorn", "app.main_reco:service_app", "--host", "0.0.0.0", "--port", "8000"] 