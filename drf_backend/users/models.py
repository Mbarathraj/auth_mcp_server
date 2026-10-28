from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model: same as Django's, but email is required and unique."""

    email = models.EmailField(unique=True)

    def __str__(self):
        return self.username
