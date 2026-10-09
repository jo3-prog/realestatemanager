from rest_framework.routers import SimpleRouter

from .views import CategoryViewSet, FavoriteViewSet, PropertyViewSet

router = SimpleRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("properties", PropertyViewSet, basename="property")
router.register("favorites", FavoriteViewSet, basename="favorite")
urlpatterns = router.urls
