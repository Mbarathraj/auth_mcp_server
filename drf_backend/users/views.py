from rest_framework import generics, permissions

from .serializers import RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    """Anyone can sign up (no token needed)."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveAPIView):
    """Returns the logged-in user, identified purely by the JWT."""

    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
