# Developer Notes

## Service Overview

- `app/main.py` creates the FastAPI application and includes the `/v1` API router.
- The app uses lifecycle startup/shutdown with `db_lifespan` to initialize MongoDB, create indexes, and bind the global worker.
- Endpoints are defined under `app/api/v1/endpoints/metadata.py`.

## Key Endpoints

- `GET /v1/url_metadata?url=...`
  - Returns `200 OK` when metadata is completed and available.
  - Returns `202 Accepted` when metadata is pending, processing, or newly scheduled.
  - Returns `503 Service Unavailable` when metadata collection has failed.
- `POST /v1/url_metadata`
  - Accepts JSON payload `{ "url": "https://..." }`.
  - Returns `201 Created` for accepted URLs.
  - Returns `409 Conflict` when URL already exists.

## Background Processing

- The service uses `asyncio.create_task()` to enqueue metadata collection without blocking the request.
- `MetadataWorker.process()` is the entrypoint for async background scraping and state updates.
- MongoDB document state is used to coordinate duplicate requests, retries, and job ownership.

## Config and Environment

- Settings live in `app/core/config.py` and load environment variables from `.env`.
- Default route prefix is `/v1` and MongoDB defaults are configured for local development.
- CSP middleware and CORS middleware are applied in `app/main.py`.

## Testing and Local Development

- API behavior is covered in `tests/test_metadata_endpoints.py`.
- Use `pytest` to run the test suite.
- The Docker stack can be started with `docker-compose up --build`.
- Mongo Express is available as part of the compose configuration for DB inspection.

## Deployment Caveats

- Internal caching will be inconsistent in a multi-worker deployment because each worker process maintains its own cache after forking.
- Single-worker deployments handle concurrent requests fairly well, but can still be improved by adding an internal task queue to prevent too many open socket errors under load.
- Stale job retry logic can be improved to better recover from hung or abandoned processing states.
- Shutdown handling and graceful database state updates should be strengthened to avoid leaving jobs in inconsistent states.
