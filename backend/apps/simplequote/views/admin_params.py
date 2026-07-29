from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView

from apps.simplequote.models import QuoteParam, QuoteTable
from apps.simplequote.serializers import QuoteParamSerializer, QuoteTableSerializer
from core.permissions import IsAdminRole
from core.responses import success_response


class AdminQuoteParamView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = QuoteParam.objects.all()
        quote_type = request.query_params.get("quote_type")
        if quote_type:
            qs = qs.filter(quote_type=quote_type)
        return success_response({"items": QuoteParamSerializer(qs, many=True).data}, request=request)

    def post(self, request):
        serializer = QuoteParamSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, status=status.HTTP_201_CREATED, request=request)


class AdminQuoteParamDetailView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, pk):
        param = get_object_or_404(QuoteParam, pk=pk)
        serializer = QuoteParamSerializer(param, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, request=request)


class AdminQuoteTableView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        qs = QuoteTable.objects.all()
        quote_type = request.query_params.get("quote_type")
        if quote_type:
            qs = qs.filter(quote_type=quote_type)
        return success_response({"items": QuoteTableSerializer(qs, many=True).data}, request=request)

    def post(self, request):
        serializer = QuoteTableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, status=status.HTTP_201_CREATED, request=request)


class AdminQuoteTableDetailView(APIView):
    permission_classes = [IsAdminRole]

    def patch(self, request, pk):
        table = get_object_or_404(QuoteTable, pk=pk)
        serializer = QuoteTableSerializer(table, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, request=request)
