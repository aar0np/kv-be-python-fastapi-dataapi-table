# NOTICE - February 10, 2026

This repository was temporarily offline following the confirmation of unauthorized activity within a limited number of our public DataStax GitHub repositories, listed below. Working with our internal incident response team, we worked to contain, remediate and investigate the activity.

We followed established incident-response processes to review and to revert any unauthorized activity.

Required Actions: Collaborators who interacted with this repository between January 31, 2026, and February 9, 2026, rebase your branch onto the new main / master. *Do not merge main / master into your branch!*

At DataStax, we remain committed to your security and to transparency within the open-source community.

Impacted Repositories:
 - github.com/KillrVideo/killrvideo-react-frontend
 - github.com/KillrVideo/kv-be-python-fastapi-dataapi-table
 - github.com/KillrVideo/kv-dataloader-csharp


# KillrVideo v2 – Python FastAPI Backend
Date: June 2025

A reference backend for the KillrVideo sample application rebuilt for 2025 using **FastAPI**, **Poetry** and **DataStax Astra DB**.

---

## Overview
This repo demonstrates modern API best-practices with:

* FastAPI & Pydantic v2 for typed request/response models
* Role-based JWT auth
* Async Cassandra (Astra DB) driver via `astrapy`
* Ruff + MyPy for quality gates
* Pytest suite (~150 tests)
* Micro-service friendly layout – or run everything as a monolith

---

## Prerequisites
1. **Python 3.10+** (use pyenv or asdf)
2. **Poetry** for dependency management:  
   `pip install "poetry==1.7.1"`
3. A **DataStax Astra DB** serverless database – grab a free account.
4. Docker (optional) if you want to run the individual services in containers.

---

## Setup & Configuration
```bash
# clone
git clone https://github.com/your-org/killrvideo-python-fastapi-backend.git
cd killrvideo-python-fastapi-backend

# install runtime dependencies (prod / Docker)
poetry install

# for local development with tests & tooling uncomment:
# poetry install --with dev

# copy env template & fill in Astra creds and SECRET_KEY
cp .env.example .env
```

Environment variables (all live in `.env`):

| Variable | Description |
|----------|-------------|
| `ASTRA_DB_API_ENDPOINT` | REST endpoint for your Astra DB instance |
| `ASTRA_DB_APPLICATION_TOKEN` | Token created in Astra UI |
| `ASTRA_DB_KEYSPACE` | Keyspace name |
| `SECRET_KEY` | JWT signing secret |
| `VECTOR_SEARCH_ENABLED` | Toggle semantic vector search (true/false) |

---

## Running the Application
### 1. Monolith (combined services)
```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Docs: <http://localhost:8000/docs>

### 2. Individual Micro-services
| Service | Entry-point | Port (example) | Docs URL |
|---------|------------|---------------|----------|
| **user-svc** | `app.main_user:service_app` | 8001 | /docs |
| **video-svc** | `app.main_video:service_app` | 8002 | /docs |
| **comment-svc** | `app.main_comment:service_app` | 8003 | /docs |
| **reco-svc** | `app.main_reco:service_app` | 8004 | /docs |

Run one:
```bash
poetry run uvicorn app.main_video:service_app --reload --port 8002
```

---

## Local HTTPS Development

Front-end development expects HTTPS at `https://localhost:8443`. Follow these steps to generate a trusted certificate and run FastAPI over TLS locally.

```bash
# 1. Install mkcert (one-time)
brew install mkcert             # macOS
# Linux:
#   sudo apt install libnss3-tools && \
#   curl -L https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/mkcert-v1.4.4-linux-amd64 -o /usr/local/bin/mkcert && \
#   chmod +x /usr/local/bin/mkcert

# 2. Generate & trust a local CA (one-time)
mkcert -install

# 3. Create cert/key for localhost and loopback addresses
mkdir -p certs
mkcert -key-file certs/localhost-key.pem \
       -cert-file certs/localhost.pem \
       localhost 127.0.0.1 ::1
```

Start the backend on `https://localhost:8443`:

```bash
poetry run uvicorn app.main:app \
  --reload --host 0.0.0.0 --port 8443 \
  --ssl-certfile certs/localhost.pem \
  --ssl-keyfile  certs/localhost-key.pem
```

Your React/Next.js dev server can now proxy or fetch against `https://localhost:8443` without the *ECONNREFUSED* error.

_Tip_: For convenience create `scripts/run_dev_https.py` and a Poetry entry-point so you can simply run `poetry run serve-https`. See the script in the repo for details.

---

## Linting & Type Checking
```bash
poetry run ruff check .        # lint
poetry run ruff format .       # auto-format
poetry run mypy .              # static types
```

---

## Running Tests
```bash
poetry run pytest              # run all tests
poetry run pytest -v           # verbose
poetry run pytest --cov=app    # with coverage (needs pytest-cov)
```

### End-to-End Smoke Test (staging)
Provide the base URL of a running deployment via the `STAGING_BASE_URL` env var and run the *e2e* marked tests:

```bash
STAGING_BASE_URL=https://staging.killrvideo.com \
poetry run pytest tests/e2e -m e2e -q
```

The test performs a single semantic search request and validates the JSON schema.

### On-Demand Load Testing
A lightweight Locust scenario ships with the repo. Use the `run-load-test` helper (registered as a Poetry script) to drive a burst of semantic searches against any environment:

```bash
# 200 users, ramping at 20/s for 5 minutes
poetry run run-load-test https://staging.killrvideo.com \
  --users 200 --spawn-rate 20 --duration 5m
```

Flags:
* `URL` (positional) – base URL to test
* `--users` – concurrent users (default 200)
* `--spawn-rate` – users spawned per second (default 20)
* `--duration` – test length (Locust time string, default `5m`)

Behind the scenes this wraps:
```bash
locust -f load/semantic_search.py --headless -u <users> -r <spawn> -t <duration> --host <URL>
```

---

## Project Structure
```
app/
  api/v1/endpoints/   # FastAPI routers per feature
  models/             # Pydantic domain models
  services/           # Business-logic layer
  db/                 # Astra client helpers
  core/               # config, security, utils
  main.py             # monolith entrypoint
  main_*.py           # per-service entrypoints
services_dockerfiles/ # Dockerfiles per service
```

---

## Building & Running with Docker
```bash
# user service
docker build -t killrvideo/user-svc -f services_dockerfiles/user.Dockerfile .
docker run -p 8001:8000 --env-file .env killrvideo/user-svc

# video service
docker build -t killrvideo/video-svc -f services_dockerfiles/video.Dockerfile .
docker run -p 8002:8000 --env-file .env killrvideo/video-svc
```

(Repeat for **comment-svc** & **reco-svc**.)

---

## API Specification
The OpenAPI schema is autogenerated by FastAPI and served at `/openapi.json` for each service (or `/api/v1/<svc>/openapi.json` when running monolith). 

### Refreshing the YAML snapshot

For convenience the repo keeps a pre-generated copy under `docs/killrvideo_openapi.yaml` so documentation sites and static tooling don't need a live server.  Whenever you change endpoints, regenerate the file via:

```bash
# install/update dev deps (PyYAML is required)
poetry install  # one-time

# generate/update the spec
poetry run gen-openapi

# commit the change if you want it in version control
git add docs/killrvideo_openapi.yaml
git commit -m "Refresh OpenAPI spec"
```

`gen-openapi` is a Poetry script defined in `pyproject.toml` and implemented in `scripts/generate_openapi.py`.  It imports the FastAPI app, calls `app.openapi()`, and writes the YAML with keys preserved in the original order.

You can also run it ad-hoc without Poetry's script shim:

```bash
poetry run python scripts/generate_openapi.py
``` 

## Observability
See docs/observability.md for full guide.  Import-ready Grafana dashboards:

| Dashboard | File | UID |
|-----------|------|-----|
| API latency by route | `docs/grafana/api_latency_by_route.json` | `kv-api-latency` |
| Backend hot-path latency | `docs/grafana/backend_hot_path.json` | `kv-hotpath` |
| Astra DB operations | `docs/grafana/astra_db_calls.json` | `kv-astra-db` |

Upload the JSON → select Prometheus datasource → done. 