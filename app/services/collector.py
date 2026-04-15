import httpx
from ..core import settings


class MetadataCollector:
    async def collect(self, url: str):
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=settings.HTTP_TIMEOUT
        ) as client:
            response = await client.get(url)
            if response is None:
                return None

            return {
                "headers": dict(response.headers),
                "cookies": {k: v for k, v in response.cookies.items()},
                "page_source": response.text,
                "status_code": response.status_code,
            }
