# NOTICE - February 10, 2026

This repository was temporarily offline following the confirmation of unauthorized activity within a limited number of our public DataStax GitHub repositories, listed below. Working with our internal incident response team, we worked to contain, remediate and investigate the activity.

We followed established incident-response processes to review and to revert any unauthorized activity.

Required Actions: Collaborators who interacted with this repository between January 31, 2026, and February 9, 2026, rebase your branch onto the new main / master. **Do not merge main / master into your branch!**

At DataStax, we remain committed to your security and to transparency within the open-source community.

Impacted Repositories:
 - github.com/KillrVideo/killrvideo-react-frontend
 - github.com/KillrVideo/kv-be-python-fastapi-dataapi-table
 - github.com/KillrVideo/kv-dataloader-csharp

---

# KillrVideo v2 Workshop

## Python FastAPI Backend

Date: January 2026

A reference backend for the KillrVideo sample application rebuilt for 2026 using **FastAPI**, **Poetry** and **DataStax Astra DB**.

Prerequisites:
- Python 3.10 or 3.11
- Poetry (Python dependency management - step #4)
- An Astra DB account (step #1)
- NPM (for the frontend - step #7)

_Note: You may also want to consider additional tools for managing multiple Python versions or environments, such as PyEnv or venv._

## Workshop Contents
1. [Create your Database](#1-create-your-astra-db-database)
2. [Create schema](#2-create-schema)
3. [Generate Embeddings and Load Data](#3-generate-embeddings-and-load-data)
4. [Connect to Astra DB](#4-connect-to-astra-db)
5. [Query videos from Astra DB](#5-query-videos-from-astra-db)
6. [Get Related Videos](#6-get-related-videos)
7. [Add KillrVideo frontend](#7-add-killrvideo-frontend)

## 1. Create your Astra DB Database

You can skip to step 1b if you already have an Astra DB database.

### 1a. Create Astra DB account

If you do not have an account yet, register and sign in to Astra DB at [astra.datastax.com](https://astra.datastax.com). This is FREE and NO CREDIT CARD is required. You can use your `GitHub` or `Google` accounts, or you can register with an email.

Follow this [guide](https://docs.datastax.com/en/astra-db-serverless/databases/create-database.html) or the steps below to create a free, **Serverless (Vector) database**.

 - Click on the "Create database" button.
 - Select "Serverless (vector)".
 - Enter a name for the database.
 - Pick a cloud provider.
 - Select a "free" region close to where you are located.
 - Click "Create Database."

### 1b. Obtain your Astra DB credentials

 - At the next screen, be sure to click the **"Generate Token"** button, copy your new token, and paste it somewhere safe (for now).
 - Once the database is created, you will also need to copy the `API_ENDPOINT` value from the very top of the screen.
 - From the "three dots" menu on the right side of the screen (by "Region"), select "Download SCB" and save the file locally.
 
### 1c. Create your Astra DB keyspace

From the Data Explorer tab:
  - Click on the "Keyspace" menu.
  - Select "Create keyspace" and name it `killrvideo`.

## 2. Create your schema

From the database overview, click on the "CQL console" button (top, upper-right). This will open a new tab in your browser.

Copy the following CQL statement into the CQL console:

```SQL
 CREATE TABLE killrvideo.videos (​
   videoid uuid PRIMARY KEY,​
   added_date timestamp,​
   description text,​
   location text,​
   location_type int,​
   name text,​
   preview_image_location text,​
   tags set<text>,​
   content_features vector<float, 384>,​
   userid uuid,​
   content_rating text,​
   category text,​
   language text,​
   views int,​
   youtube_id text);
```

Next, create a Storage Attached Index (SAI) to enable a cosine-based vector search:

```SQL
CREATE CUSTOM INDEX ON killrvideo.videos(content_features)
USING 'StorageAttachedIndex'
WITH OPTIONS = { 'similarity_function': 'cosine' };
```

## 3. Generage Embeddings and Load Data

To load data into Astra DB, we will need to clone a different repository. Make sure this gets cloned into a separate director (from the `kv-be-python-fastapi-dataapi-table` directory):

```bash
git clone git@github.com:KillrVideo/killrvideo-data.git
cd killrvideo-data
```

Set your Astra DB token and the path to your (downloaded) SCB as environment variables:

| Variable | Description |
|----------|-------------|
| `ASTRA_SCB_PATH` | Path to your Astra DB Secure Connect Bundle. |
| `ASTRA_DB_APPLICATION_TOKEN` | Token created in the Astra UI. |

```bash
 export ASTRA_DB_APPLICATION_TOKEN=AstraCS:NOTREALuApjRa:0a5f10DefinitelyNotReal04ec​
 export ASTRA_SCB_PATH=~/Downloads/secure-connect-aaronsdb.zip
```

Next, install the dependencies:

```bash
pip install -r loaders/requirements.txt
```

Run the loader for the `videos` table:

```bash
python loaders/astra-tables/load_data_cql.py videos
```

If that succeeds, you should see something similar to the following:

```bash
2026-01-15 11:12:49,136 - INFO - ✓ Connected to Astra DB​
2026-01-15 11:12:49,136 - INFO - csv_file: /Users/aaron.ploetz/Documents/workspace/killrvideo-data/loaders/../data/csv/videos.csv​
2026-01-15 11:12:49,137 - INFO - Loading videos.csv...​
2026-01-15 11:12:56,664 - INFO - Loaded 100 videos...​
2026-01-15 11:13:04,164 - INFO - Loaded 200 videos...​
2026-01-15 11:13:11,745 - INFO - Loaded 300 videos...​
2026-01-15 11:13:18,825 - INFO - Loaded 400 videos...​
2026-01-15 11:13:26,163 - INFO - Loaded 500 videos...​
2026-01-15 11:13:26,163 - INFO - ✓ Loaded 500 videos (0 errors)​
============================================================​
2026-01-15 11:13:26,163 - INFO - ✓ COMPLETE: Loaded 500 total records​
============================================================
```

## 4. Connect to Astra DB

For these next exercise steps, be sure to `cd` back into this project's (`kv-be-python-fastapi-dataapi-table`) directiory.

If you haven't already done so, install `astrapy` and `poetry`:

```bash
pip install astrapy
pip install poetry
```

And then run `poetry install` to install the project dependencies:
```bash
poetry install
```

Be sure to copy the `.env.example` file to `.env` and update the values in the `.env` file with your Astra DB instance.

```bash
cp .env.example .env
```

| Variable | Description |
|----------|-------------|
| `ASTRA_DB_API_ENDPOINT` | API endpoint for your Astra DB instance. This is the URL you use to access your Astra DB instance. |
| `ASTRA_DB_APPLICATION_TOKEN` | Token created in the Astra UI. |
| `ASTRA_DB_KEYSPACE` | `killrvideo` |

### 4a. astra_client.py - class _AstraDBV2Wrapper - init

 - In your IDE, open `app/db/astra_client.py`.
 - Look for this line in the _AstraDBV2Wrapper class' `__init__` method:

```python
# WORKSHOP EXERCISE #4a
```

After that, add the following code to initialize the Astra DB client to the `_db` variable:

```python
    client = DataAPIClient(token=token)
    self._db = client.get_async_database(
        api_endpoint,
        keyspace=namespace,
    )
```

### 4b. astra_client.py - init_astra_db

 - Look for this line in the `init_astra_db` method:

```python
# WORKSHOP EXERCISE #4b
```

After that line, add the following code to define`db_instance` and create a session with Astra DB:

```python
    db_instance = AstraDB(
        api_endpoint=settings.ASTRA_DB_API_ENDPOINT,
        token=settings.ASTRA_DB_APPLICATION_TOKEN,
        namespace=settings.ASTRA_DB_KEYSPACE,
    )
```

### 4c. astra_client.py - get_astra_db

 - Look for this line in the `init_astra_db` method:

```python
# WORKSHOP EXERCISE #4c
```

Start by checking to see if `db_instance` is defined. If not, call `init_astra_db` to initialize the Astra DB instance. Outside of the `if`-check, return `db_instance`.

```python
    if db_instance is None:
        await init_astra_db()

    return db_instance
```

### Testing for 4a, 4b, and 4c

To test, run the application:

```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

If it successfully connects to Astra DB, you should see something similar to this:

```bash
INFO:     Will watch for changes in these directories: ['/Users/aaron.ploetz/Documents/workspace/kv-be-python-fastapi-dataapi-table']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [96413] using WatchFiles
INFO:app.services.video_service:video_service logger level = 20  (root = 20)
INFO:app.utils.observability:Prometheus instrumentation initialised in 0.10 ms
INFO:app.utils.observability:OpenTelemetry tracing initialised (802.20 ms)
INFO:app.utils.observability:File logging handler attached (logs/app.log)
INFO:     Started server process [96425]
INFO:     Waiting for application startup.
INFO:app.db.astra_client:Initializing AstraDB client for keyspace: killrvideo at https://d32f1a9d-7395-4344-94e...
INFO:app.db.astra_client:AstraDB client initialized successfully.
INFO:     Application startup complete.
```

Press [CTRL+C] to stop the application.

## 5. Query videos from Astra DB

### 5a. video_service.py - get_video_by_id

 - In your IDE, open `app/services/video_service.py`.
 - Look for this line:

```python
# WORKSHOP EXERCISE 5a
```

For this method, we will need to:
 - Convert the `video_id` variable to a UUID.
 - Call `find_one` with a filter on the `videoid` column.
 - Set `doc` to the result of the `find_one` call.

```python
    doc = await db_table.find_one(filter={"videoid": str(video_id)})
```

### 5b. video_service.py - list_videos_with_query

This method is used by several of our video GET endpoints.

 - Look for this line:

```python
# WORKSHOP EXERCISE 5b
```

Here, we will need to:
 - Call `find` while passing named parameters for `filter`, `skip`, `limit`, and `sort`.
 - Set `cursor` to the result of the `find` call.

```python
    cursor = db_table.find(
        filter=query_filter, skip=skip, limit=page_size, sort=sort_options
    )
```

### Testing for 5a and 5b

To test 5a and 5b, run the application:

```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

In another terminal window, run a `curl` command to get a video by ID:

```bash
curl -k -X GET "http://127.0.0.1:8000/api/v1/videos/id/c435ba71-1dad-437a-a0be-28afe6b842e9" -H "accept: application/json"
```

You should see data returned for a single video.

To test 5b, run a `curl` command to get a list of the "latest" videos:

```bash
curl -k -X GET "http://127.0.0.1:8000/api/v1/videos/latest" -H "accept: application/json"
```

This should return a result similar to this:

```bash
{"data":[{"videoId":"86e1763b-6482-4014-9f7f-5028415d8e95","title":"Build AI-Powered Apps Faster with Langflow","thumbnailUrl":"https://i.ytimg.com/vi/L7V_woT8mbQ/maxresdefault.jpg","userId":"4a626541-39ca-4407-802e-08a82fa27f5f","submittedAt":"2025-08-28T05:04:35Z","content_rating":"G","category":"Education","views":0,"averageRating":null},{"videoId":"b2f64758-46dd-4976-8099-3d51ed6c82fc","title":"MCP for Developers: Visual AI with MCP, Langflow & IBM Tools","thumbnailUrl":"https://i.ytimg.com/vi/x76QZRuC__8/maxresdefault.jpg","userId":"ffd032c3-4d2b-4385-92e4-5bb6b3bfb5da","submittedAt":"2025-08-21T05:01:57Z","content_rating":"G","category":"Education","views":0,"averageRating":null},{"videoId":"8926e6d1-c09d-4f96-92a7-415b5a887233","title":"Build Real-Time GenAI Product Recs that Boost Cart Size","thumbnailUrl":"https://i.ytimg.com/vi/jwGAeqeORnM/maxresdefault.jpg","userId":"dd919cc2-cb00-4df2-8a23-4aee419acea7","submittedAt":"2025-07-23T04:52:22Z","content_rating":"G","category":"Education","views":0,"averageRating":null}],"pagination":{"currentPage":1,"pageSize":10,"totalItems":3,"totalPages":1}}
```

## 6. Get Related Videos

 - In your IDE, open the file `app/services/recommendation_service.py`.
 - Look for this line in the `get_related_videos` method:

 ```python
# WORKSHOP EXERCISE 6
```

Here we will need to:
 - Use the `video_service` to get a single video by it's `videoid` (using the `get_video_by_id` method), and set `target_video` to the result.
 - If `target_video` is `None`, then return an empty list.
 - Use `target_video`'s `content_features` (vector embedding) column to query other additional, similar videos, and set `recommended_videos` to the result.

```python
    target_video = await video_service.get_video_by_id(video_id)
    if target_video is None:
        return []

    recommended_videos, _total = await video_service.list_videos_with_query(
        {},
        page=1,
        page_size=limit,
        sort_options={"content_features": target_video.content_features}
    )
```

### Testing for 6

To test 6, run the application:

```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

In another terminal window, run a `curl` command to get a video by ID:

```bash
curl -k -X GET "http://127.0.0.1:8000/api/v1/videos/id/c435ba71-1dad-437a-a0be-28afe6b842e9/related?limit=5" -H "accept: application/json"
```

You should see a response like this:

```bash
[{"videoId":"6a7aec3d-453b-4044-a565-cc6d4aaf44a8","title":"Learn how to build an e-Commerce App!","thumbnailUrl":"https://i.ytimg.com/vi/8KmSN3KEspE/maxresdefault.jpg","score":0.58},{"videoId":"5a2735b5-4f67-44b0-a404-aa208a91f5ac","title":"Build an eCommerce Website with Spring Boot and a NoSQL DB","thumbnailUrl":"https://i.ytimg.com/vi/P_km9yKgiqA/maxresdefault.jpg","score":0.7},{"videoId":"86c2c337-31f2-4621-84cf-55fabccb17df","title":"Build an eCommerce Website with Spring Boot and a NoSQL DB","thumbnailUrl":"https://i.ytimg.com/vi/nzQzLtIJINk/maxresdefault.jpg","score":0.95},{"videoId":"19eebc24-6bbe-49f7-a08d-93697974e1d2","title":"Learn how to build an e-Commerce App!","thumbnailUrl":"https://i.ytimg.com/vi/sGBFNDvk0pA/maxresdefault.jpg","score":0.59}]
```

## 7. Add KillrVideo frontend

 - Clone the web frontend repository:

```bash
git clone git@github.com:KillrVideo/killrvideo-react-frontend.git
```

 - Edit the `vite.config.ts` file, ensuring that the proxy target is http://localhost:8000:

 ```json
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
 ```

 - Build and run the project using NPM:

 ```bash
 npm i
 npm run dev
 ```

 - Navigate to http://localhost:8080, and you should see the KillrVideo application running. The latest (Featured) videos should be visible.


## The workshop STOPS here!

--- 

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