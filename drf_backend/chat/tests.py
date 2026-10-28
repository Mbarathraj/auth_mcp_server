from unittest.mock import patch

from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from users.models import User


@override_settings(GEMINI_API_KEY="test-key")
class ChatEndpointTests(APITestCase):
    def setUp(self):
        cache.clear()  # reset rate-limit counters between tests
        User.objects.create_user("alice", "alice@example.com", "Str0ng-pass-123")
        resp = self.client.post(
            reverse("token_obtain_pair"), {"username": "alice", "password": "Str0ng-pass-123"}
        )
        self.token = resp.data["access"]

    def auth(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_requires_login(self):
        resp = self.client.post("/api/chat/", {"prompt": "hi"})
        self.assertEqual(resp.status_code, 401)

    def test_rejects_empty_prompt(self):
        self.auth()
        self.assertEqual(self.client.post("/api/chat/", {"prompt": ""}).status_code, 400)

    @patch("chat.views.run_chat", return_value=("You have 2 tasks.", ["list_my_tasks"]))
    def test_success_forwards_users_own_token(self, mock_run):
        self.auth()
        resp = self.client.post("/api/chat/", {"prompt": "what are my tasks?"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["answer"], "You have 2 tasks.")
        self.assertEqual(resp.data["tools_used"], ["list_my_tasks"])
        # the user's own JWT (not a user id) is what gets forwarded to MCP
        mock_run.assert_called_once_with("what are my tasks?", self.token)

    @patch("chat.views.run_chat", side_effect=RuntimeError("mcp down"))
    def test_returns_502_when_backend_pipeline_fails(self, _):
        self.auth()
        self.assertEqual(self.client.post("/api/chat/", {"prompt": "hi"}).status_code, 502)

    @override_settings(GEMINI_API_KEY="")
    def test_returns_503_when_not_configured(self):
        self.auth()
        self.assertEqual(self.client.post("/api/chat/", {"prompt": "hi"}).status_code, 503)
