import random

from locust import HttpUser, between, task

from load_tests import pool
from load_tests.helpers import random_ordering


class ReadingUser(HttpUser):
    """Passive reader. Browses the paginated list and opens comment trees.

    Represents the majority of traffic - most visitors only read.
    Task ratio 5:2 means the list is hit ~2.5× more often than trees.
    """
    weight = 7
    wait_time = between(1.0, 5.0)  # user thread sleeps

    def on_start(self) -> None:
        pool.seed(self.client)

    @task(5)
    def browse_list(self) -> None:
        page = random.randint(1, 2)
        self.client.get(
            f"/api/comments/?ordering={random_ordering()}&page={page}",
            name = "/api/comments/ [list]",
        )

    @task(2)
    def view_tree(self) -> None:
        cid = pool.pick()
        if cid is None:
            return
        self.client.get(
            f"/api/comments/{cid}/tree/",
            name = "/api/comments/{id}/tree/",
        )
