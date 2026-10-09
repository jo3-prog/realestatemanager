from rest_framework.routers import SimpleRouter

from .views import InquiryViewSet

router = SimpleRouter()
router.register("inquiries", InquiryViewSet, basename="inquiry")
urlpatterns = router.urls
