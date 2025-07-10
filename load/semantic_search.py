"""Locust load-test file exercising the semantic search endpoint.

Run standalone, e.g.:

    locust -f load/semantic_search.py --headless -u 200 -r 20 -t 5m \
           --host https://staging.killrvideo.com

The parameters above spin up 200 concurrent users with a hatch rate of 20
users/second, roughly mapping to ~20 requests per second steady-state given
our simple user scenario.  Adjust figures to match your capacity planning.

The *host* URL is provided at runtime via the ``--host`` flag or the
``STAGING_BASE_URL`` environment variable.
"""

from locust import HttpUser, task, between


class SemanticSearchUser(HttpUser):  # noqa: D401 – Locust user class
    # Short random wait to reach ~20 RPS with 200 users
    wait_time = between(0.1, 0.3)

    @task
    def search(self):  # noqa: D401
        # Static query keeps the test deterministic; real test could randomise.
        self.client.get(
            "/api/v1/search/videos", params={"query": "cats", "mode": "semantic"}
        )
