from django.urls import path

from apps.simplequote.views import (
    AdminQuoteParamDetailView,
    AdminQuoteParamView,
    MemberSimpleQuoteConvertView,
    MemberSimpleQuoteDetailView,
    MemberSimpleQuoteListCreateView,
)

urlpatterns = [
    path("member/simple-quotes", MemberSimpleQuoteListCreateView.as_view()),
    path("member/simple-quotes/<int:pk>", MemberSimpleQuoteDetailView.as_view()),
    path("member/simple-quotes/<int:pk>/convert", MemberSimpleQuoteConvertView.as_view()),
    path("admin/quote-params", AdminQuoteParamView.as_view()),
    path("admin/quote-params/<int:pk>", AdminQuoteParamDetailView.as_view()),
]
