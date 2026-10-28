from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Login: POST {username, password} -> {access, refresh}
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    # POST {refresh} -> new {access}
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/users/", include("users.urls")),
    path("api/tasks/", include("tasks.urls")),
    path("api/chat/", include("chat.urls")),
]
