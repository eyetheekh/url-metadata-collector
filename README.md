# URL Metadata Collector Service

A FastAPI-based service that collects and serves metadata (headers, cookies, page source) for URLs using an asynchronous background processing model.

---

# Features

* **POST /url_metadata**

  * Collects metadata synchronously
  * Stores in MongoDB

* **GET /url_metadata**

  * Returns metadata if available
  * Triggers background processing if missing (returns `202 Accepted`)

* **Background Worker**

  * Handles metadata collection asynchronously
  * Ensures non-blocking API responses

* **Security**

  * CSP middleware
  * CORS configuration

---

# Architecture

```
Client
   ↓
API (FastAPI)
   ↓
Service Layer
   ↓
Repository Layer
   ↓
MongoDB

Background Worker (async)
```

---

# Project Structure

```
app/
├── api/
│   └── v1/
│       ├── endpoints/
│       └── dependencies/
├── core/
│   ├── config.py
│   ├── logging.py
│   └── middlewares/
├── db/
│   ├── database.py
│   └── indexes.py
├── models/
├── repositories/
├── services/
├── workers/
├── main.py
```

---

# Installation

```
git clone https://github.com/eyetheekh/url-metadata-collector.git
cd url-metadata-collector

# Create and activate a uv-managed virtual environment
uv venv
source .venv/bin/activate

# Install dependencies with uv
uv pip install -r requirements.txt
```

---

# Run with Docker

```bash
docker-compose up --build
```

This will build and start all required services. (e.g., FastAPI app, MongoDB, Mongo Express).

---

# Local Development

## 1. Start MongoDB + Mongo Express with Docker
```bash
docker-compose up -d mongodb mongo-express
```

This spins up only the database and admin UI containers, exposing them locally for development.

## 2. Run the FastAPI app with `uv`
```bash
uv run uvicorn app.main:app --reload
```
---

# Testing

```
pytest
```

Pytest configurations can be adjusted in pyproject.toml under:
``` toml
[tool.pytest.ini_options]
```
---

# API Endpoints

## 1. GET `/v1/url_metadata`

### Query

```
url: AnyHttpUrl
```

### Behavior

| Case      | Response     |
| --------- | ------------ |
| Exists    | 200 OK       |
| Not found | 202 Accepted |

### Example

```
curl "http://localhost:8000/v1/url_metadata?url=https://example.com"
```

---

## 2. POST `/v1/url_metadata`

### Body

```
{
  "url": "https://example.com"
}
```

### Behavior

| Case      | Response     |
| --------- | ------------ |
| New URL   | 201 Created  |
| Duplicate | 409 Conflict |

---

# Background Worker

    * Atomic job claiming
    * Metadata collection
    * Status updates

* Triggered via:

  * GET (on db lookup miss)
  * POST (after creation)

* Utilizes asyncio.create_task() to fire and forget the task to the event loop.
```
asyncio.create_task(worker.process(url))
```

---

# Key Design Decisions

## 1. Api → Service → Repository

* Api: HTTP layer
* Service: Business logic
* Repository: Database interaction

---

## 2. Async-first design

* Async FastAPI endpoints
* Async MongoDB client
* Background processing using asyncio

---

## 3. No external queue

* Constraint: No external services like Celery/Redis
* Solution:

  * MongoDB atomic operations for state management
  * In-process singleton background workers for metadata collection

---

# URL Metdata Schema

```
{
  "url": "string",
  "headers": {},
  "cookies": {},
  "page_source": "string",
  "status_code": 200,
  "process_state": "pending | processing | completed | failed",
  "failure_count": 0,
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

---

## Indexes

* Unique index on `url`
* process_state for process lookups

---

# Security

## CSP Middleware
* Swagger routes excluded from CSP
* Strict headers applied in production

---

# Limitations
* Background worker runs per process in a multi worker deployment and task duplication handled via DB.
* Global shared cache since workers run per process. sync & invalidation becomes buggy.
* No queue for async tasks.
* Retry loop not implemented yet.

---

# Future Improvements

* Retry mechanism for failed jobs
* Rate limiting ( might require redis or workarounds )
* Global cache ( would require redis )

---

# Testing Strategy

* Integration tests using httpx AsyncClient
* Covers:

  * GET miss → 202
  * POST create → 201
  * Duplicate handling → 409

---

# Scalability Notes

* Each worker process:

  * Has its own event loop
  * Executes background tasks independently

* Deduplication ensured via MongoDB atomic operations

---