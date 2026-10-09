from rest_framework.routers import SimpleRouter

from .views import AdminUserViewSet

router = SimpleRouter()
router.register("users", AdminUserViewSet, basename="admin-user")
urlpatterns = router.urls
