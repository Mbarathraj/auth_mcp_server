from rest_framework import viewsets

from .models import Task
from .serializers import TaskSerializer
from rest_framework.permissions import IsAuthenticated

class TaskViewSet(viewsets.ModelViewSet):
    """
    Full CRUD on tasks, but only ever on the *logged-in user's* tasks.

    Because get_queryset filters by request.user, another user's task is not
    just forbidden: it does not exist as far as this user is concerned (404).
    """
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Task.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        # Owner comes from the verified JWT, never from the request body
        serializer.save(owner=self.request.user)
