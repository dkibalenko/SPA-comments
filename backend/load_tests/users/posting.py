from locust import HttpUser, between, task

from load_tests import pool
from load_tests.helpers import get_captcha, random_email, random_text, random_username


class PostingUser(HttpUser):
    """Active commenter. Posts top-level comments.

    Task ratio 3:1 means the user reads three times before writing once -
    realistic behaviour for someone composing a comment.
    """
    weight = 2
    wait_time = between(5.0, 15.0)  # user thread sleeps

    def on_start(self) -> None:
        pool.seed(self.client)

    @task(3)
    def browse_before_posting(self) -> None:
        """Locust calls browse 75% of the time"""
        self.client.get(
            "/api/comments/?ordering=-date&page=1",
            name = "/api/comments/ [list]",
        )

    @task(1)
    def post_comment(self) -> None:
        """Locust calls post 25% of the time."""
        token, answer = get_captcha(self.client)
        if not token or not answer:
            return

        username = random_username()
        resp = self.client.post(
            "/api/comments/",
            data = {
                "username": username,
                "email": random_email(username),
                "text": random_text(),
                "captcha_token": token,
                "captcha_answer": answer,
            },
            name = "/api/comments/ [create]",
        )
        if resp.status_code == 201:
            cid = resp.json().get("id")
            if cid:
                pool.register(cid)
