from rest_framework import serializers

from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ("id", "title", "description", "is_done", "created_at")
        # "owner" is deliberately NOT a field: a client can never choose or change it
        read_only_fields = ("id", "created_at")
