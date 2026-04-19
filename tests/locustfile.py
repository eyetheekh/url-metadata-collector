from locust import HttpUser, task, between
import random
import urllib.parse


class URLMetadataUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """
        Seed with some URLs to simulate realistic behavior.
        """
        self.base_urls = [
            "https://example.com",
            "https://github.com",
            "https://openai.com",
            "https://google.com",
        ]

    def _random_url(self):
        """
        Add slight randomness to avoid constant 409 unless intended.
        """
        base = random.choice(self.base_urls)
        return f"{base}?q={random.randint(1, 100000)}"

    # 1. GET metadata fetch/schedule
    @task(3)
    def get_url_metadata(self):
        url = random.choice(self.base_urls)
        encoded_url = urllib.parse.quote(url, safe="")

        with self.client.get(
            f"/v1/url_metadata?url={encoded_url}",
            headers={"accept": "application/json"},
            catch_response=True,
            name="GET /v1/url_metadata",
        ) as response:
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    # 2. POST create metadata job
    @task(2)
    def create_url_metadata(self):
        url = self._random_url()

        payload = {"url": url}

        with self.client.post(
            "/v1/url_metadata",
            json=payload,
            headers={
                "accept": "application/json",
                "Content-Type": "application/json",
            },
            catch_response=True,
            name="POST /v1/url_metadata (create)",
        ) as response:
            if response.status_code == 201:
                response.success()
            elif response.status_code == 409:
                # acceptable depending on race / duplicates
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    # 3. POST duplicate force 409
    @task(1)
    def create_duplicate_url(self):
        url = "https://example.com"

        payload = {"url": url}

        with self.client.post(
            "/v1/url_metadata",
            json=payload,
            headers={
                "accept": "application/json",
                "Content-Type": "application/json",
            },
            catch_response=True,
            name="POST /v1/url_metadata (duplicate)",
        ) as response:
            if response.status_code == 409:
                response.success()
            elif response.status_code == 201:
                # first insert might succeed depending on timing
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
