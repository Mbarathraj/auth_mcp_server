import logging

from django.conf import settings
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import run_chat

logger = logging.getLogger(__name__)


class ChatRequestSerializer(serializers.Serializer):
    prompt = serializers.CharField(max_length=2000)


class ChatView(APIView):
    """
    POST /api/chat/   {"prompt": "add a task to buy milk"}

    The user must be logged in (JWT). Their own token is forwarded to the MCP
    server, so the tools can only ever touch THIS user's data.
    """

    throttle_scope = "chat"  # rate limit, see REST_FRAMEWORK in settings.py

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not settings.GEMINI_API_KEY:
            return Response(
                {"detail": "The assistant is not configured (missing GEMINI_API_KEY)."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # The raw access token from the "Authorization: Bearer <token>" header
        user_token = request.META["HTTP_AUTHORIZATION"].split(" ", 1)[1]

        try:
            answer, tools_used = run_chat(serializer.validated_data["prompt"], user_token)
        except Exception:
            logger.exception("Chat request failed")
            return Response(
                {"detail": "The assistant is unavailable right now. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({"answer": answer, "tools_used": tools_used})
