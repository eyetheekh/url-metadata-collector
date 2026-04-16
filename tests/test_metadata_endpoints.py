import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock

from app.main import create_application
from app.api.v1.endpoints.metadata import get_metadata_service, get_worker
from app.models import MetadataState


@pytest.fixture
def app():
    return create_application()


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def mock_service():
    service = Mock()

    # sync method
    service.remove_trailing_slash_to_url.side_effect = lambda x: x.rstrip("/")

    # async methods
    service.create_metadata = AsyncMock()
    service.get_metadata = AsyncMock()

    return service


@pytest.fixture
def mock_worker():
    worker = AsyncMock()
    return worker


@pytest.fixture(autouse=True)
def override_dependencies(app, mock_service, mock_worker):
    app.dependency_overrides[get_metadata_service] = lambda: mock_service
    app.dependency_overrides[get_worker] = lambda: mock_worker
    yield
    app.dependency_overrides.clear()


######################################################## GET /url_metadata


def test_get_metadata_found(client, mock_service):
    mock_service.get_metadata.return_value = (
        MetadataState.FOUND,
        {
            "headers": {"content-type": "text/html", "server": "nginx"},
            "cookies": {"sessionid": "abc123xyz"},
            "page_source": "<html><body>Hello World</body></html>",
        },
    )

    response = client.get("/api/v1/url_metadata", params={"url": "https://test.com"})

    assert response.status_code == 200
    assert response.json()["headers"] == {
        "content-type": "text/html",
        "server": "nginx",
    }
    assert response.json()["cookies"] == {"sessionid": "abc123xyz"}
    assert response.json()["page_source"] == "<html><body>Hello World</body></html>"


def test_get_metadata_accepted(client, mock_service, mock_worker):
    mock_service.get_metadata.return_value = (MetadataState.ACCEPTED, None)
    mock_service.create_metadata.return_value = (MetadataState.ACCEPTED, True)

    response = client.get("/api/v1/url_metadata", params={"url": "https://test.com"})

    assert response.status_code == 202
    assert response.json()["message"] == "URL scheduled for metadata collection."


def test_get_metadata_exception(client, mock_service):
    mock_service.get_metadata.side_effect = Exception("fail")

    response = client.get("/api/v1/url_metadata", params={"url": "https://test.com"})

    assert response.status_code == 500


######################################################## POST /url_metadata


def test_create_metadata_success(client, mock_service):
    mock_service.create_metadata.return_value = (
        MetadataState.ACCEPTED,
        True,
    )

    response = client.post(
        "/api/v1/url_metadata",
        json={"url": "https://test.com"},
    )

    assert response.status_code == 201
    assert response.json()["url"] == "https://test.com"
    assert response.json()["message"] == "URL scheduled for metadata collection."


def test_create_metadata_duplicate(client, mock_service):
    mock_service.create_metadata.return_value = (
        MetadataState.DUPLICATE,
        None,
    )

    response = client.post(
        "/api/v1/url_metadata",
        json={"url": "https://test.com"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["url"] == "https://test.com"
    assert response.json()["detail"]["message"] == "URL already exists."


def test_create_metadata_exception(client, mock_service):
    mock_service.create_metadata.side_effect = Exception("fail")

    response = client.post(
        "/api/v1/url_metadata",
        json={"url": "https://test.com"},
    )

    assert response.status_code == 500
