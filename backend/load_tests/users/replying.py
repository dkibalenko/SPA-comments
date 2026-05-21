from locust import HttpUser, between, task

from load_tests import pool
from load_tests.helpers import (
    get_captcha,
    random_email,
    random_text,
    random_username
)


class ReplyingUser(HttpUser):
    """Reply poster. Reads a thread then posts a reply to an existing comment.

    Task ratio 4:1 means the user reads the thread four times before
    replying once — more deliberate than a top-level commenter.
    """
    weight = 1
    wait_time = between(8.0, 20.0)

    def on_start(self) -> None:
        pool.seed(self.client)

    @task(4)
    def browse_thread(self) -> None:
        cid = pool.pick()
        if cid is None:
            return
        self.client.get(
            f"/api/comments/{cid}/tree/",
            name="/api/comments/{id}/tree/",
        )

    @task(1)
    def post_reply(self) -> None:
        parent_id = pool.pick()
        if parent_id is None:
            return

        token, answer = get_captcha(self.client)
        if not token or not answer:
            return

        username = random_username()
        resp = self.client.post(
            "/api/comments/",
            data={
                "username": username,
                "email": random_email(username),
                "text": random_text(),
                "captcha_token": token,
                "captcha_answer": answer,
                "parent_id": parent_id,
            },
            name="/api/comments/ [reply]",
        )
        if resp.status_code == 201:
            cid = resp.json().get("id")
            if cid:
                pool.register(cid)
