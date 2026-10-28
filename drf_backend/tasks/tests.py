from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User


class TaskIsolationTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", "alice@example.com", "Str0ng-pass-123")
        self.bob = User.objects.create_user("bob", "bob@example.com", "Str0ng-pass-456")

    def login(self, username, password):
        resp = self.client.post(
            reverse("token_obtain_pair"), {"username": username, "password": password}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")

    def test_register_then_login_then_me(self):
        resp = self.client.post(
            reverse("register"),
            {"username": "carol", "email": "carol@example.com", "password": "Str0ng-pass-789"},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", resp.data)

        self.login("carol", "Str0ng-pass-789")
        me = self.client.get(reverse("me"))
        self.assertEqual(me.data["username"], "carol")

    def test_unauthenticated_requests_are_rejected(self):
        self.assertEqual(self.client.get("/api/tasks/").status_code, 401)
        self.assertEqual(self.client.get(reverse("me")).status_code, 401)

    def test_user_only_sees_own_tasks(self):
        self.login("alice", "Str0ng-pass-123")
        self.client.post("/api/tasks/", {"title": "Alice secret task"})
        self.assertEqual(len(self.client.get("/api/tasks/").data), 1)

        self.login("bob", "Str0ng-pass-456")
        self.assertEqual(self.client.get("/api/tasks/").data, [])

    def test_user_cannot_touch_another_users_task(self):
        self.login("alice", "Str0ng-pass-123")
        task_id = self.client.post("/api/tasks/", {"title": "Alice task"}).data["id"]

        self.login("bob", "Str0ng-pass-456")
        url = f"/api/tasks/{task_id}/"
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.patch(url, {"title": "hacked"}).status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)

        # still intact for Alice
        self.login("alice", "Str0ng-pass-123")
        self.assertEqual(self.client.get(url).data["title"], "Alice task")

    def test_client_cannot_assign_task_to_someone_else(self):
        self.login("alice", "Str0ng-pass-123")
        self.client.post("/api/tasks/", {"title": "mine", "owner": self.bob.id})

        self.login("bob", "Str0ng-pass-456")
        self.assertEqual(self.client.get("/api/tasks/").data, [])
