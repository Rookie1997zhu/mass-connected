from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.accounts.models import FactoryProfile
from apps.accounts.serializers import PublicPartnerSerializer
from apps.accounts.views._helpers import get_lang
from core.responses import success_response


class PublicPartnerListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = (
            FactoryProfile.objects.filter(status="approved", is_public=True)
            .prefetch_related("processes")
            .order_by("-created_at")
        )
        category_id = request.query_params.get("service_category_id")
        if category_id:
            qs = qs.filter(processes__id=category_id).distinct()
        return success_response(
            {"items": PublicPartnerSerializer(qs, many=True, context={"lang": get_lang(request)}).data},
            request=request,
        )
