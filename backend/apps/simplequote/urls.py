from django.urls import path

from apps.simplequote.views import (
    AdminQuoteParamDetailView,
    AdminQuoteParamView,
    AdminQuoteTableDetailView,
    AdminQuoteTableView,
    FefcoCatalogView,
    MemberSimpleQuoteConvertView,
    MemberSimpleQuoteDetailView,
    MemberSimpleQuoteListCreateView,
    DrawingParseView,
    ShippingEstimateView,
    StpParseView,
)

urlpatterns = [
    path("packaging/fefco-catalog", FefcoCatalogView.as_view()),
    path("member/simple-quotes", MemberSimpleQuoteListCreateView.as_view()),
    path("member/simple-quotes/shipping-estimate", ShippingEstimateView.as_view()),
    path("member/simple-quotes/parse-stp", StpParseView.as_view()),
    path("member/simple-quotes/parse-drawing", DrawingParseView.as_view()),
    path("member/simple-quotes/<int:pk>", MemberSimpleQuoteDetailView.as_view()),
    path("member/simple-quotes/<int:pk>/convert", MemberSimpleQuoteConvertView.as_view()),
    path("admin/quote-params", AdminQuoteParamView.as_view()),
    path("admin/quote-params/<int:pk>", AdminQuoteParamDetailView.as_view()),
    path("admin/quote-tables", AdminQuoteTableView.as_view()),
    path("admin/quote-tables/<int:pk>", AdminQuoteTableDetailView.as_view()),
]
