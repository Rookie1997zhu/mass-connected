from django.urls import path

from apps.blog.views import (
    AdminBlogCategoryDetailView,
    AdminBlogCategoryListCreateView,
    AdminBlogCommentDetailView,
    AdminBlogCommentListView,
    AdminBlogPostDetailView,
    AdminBlogPostListCreateView,
    BlogCommentDeleteView,
    BlogPostCommentCreateView,
    BlogPostLikeView,
    PublicBlogCategoryListView,
    PublicBlogCommentListView,
    PublicBlogPostDetailView,
    PublicBlogPostListView,
    PublicBlogTagListView,
)

urlpatterns = [
    path("public/blog/categories", PublicBlogCategoryListView.as_view()),
    path("public/blog/tags", PublicBlogTagListView.as_view()),
    path("public/blog/posts", PublicBlogPostListView.as_view()),
    path("public/blog/posts/<int:pk>", PublicBlogPostDetailView.as_view()),
    path("public/blog/posts/<int:pk>/comments", PublicBlogCommentListView.as_view()),
    path("blog/posts/<int:pk>/like", BlogPostLikeView.as_view()),
    path("blog/posts/<int:pk>/comments", BlogPostCommentCreateView.as_view()),
    path("blog/comments/<int:pk>", BlogCommentDeleteView.as_view()),
    path("admin/blog/categories", AdminBlogCategoryListCreateView.as_view()),
    path("admin/blog/categories/<int:pk>", AdminBlogCategoryDetailView.as_view()),
    path("admin/blog/posts", AdminBlogPostListCreateView.as_view()),
    path("admin/blog/posts/<int:pk>", AdminBlogPostDetailView.as_view()),
    path("admin/blog/comments", AdminBlogCommentListView.as_view()),
    path("admin/blog/comments/<int:pk>", AdminBlogCommentDetailView.as_view()),
]
