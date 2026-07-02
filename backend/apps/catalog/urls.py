from django.urls import path

from apps.catalog.views import (
    AdminCategoryDetailView,
    AdminCategoryListCreateView,
    AdminProductDetailView,
    AdminProductImageUploadView,
    AdminProductListCreateView,
    PublicCategoryListView,
    PublicProductDetailView,
    PublicProductListView,
)

urlpatterns = [
    path("public/categories", PublicCategoryListView.as_view()),
    path("public/products", PublicProductListView.as_view()),
    path("public/products/<int:pk>", PublicProductDetailView.as_view()),
    path("admin/categories", AdminCategoryListCreateView.as_view()),
    path("admin/categories/<int:pk>", AdminCategoryDetailView.as_view()),
    path("admin/products", AdminProductListCreateView.as_view()),
    path("admin/products/<int:pk>", AdminProductDetailView.as_view()),
    path("admin/products/<int:pk>/images", AdminProductImageUploadView.as_view()),
]
