from django.urls import path

from .views import (
    CategoryListView, TagListView, PostListCreateView, PostDetailView, MyPostListView,
    BookmarkListView, LikeToggleView, BookmarkToggleView, MyStatsView, AuthorProfileView
)

urlpatterns = [
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('tags/', TagListView.as_view(), name='tag-list'),
    path('posts/', PostListCreateView.as_view(), name='post-list'),
    path('posts/my/', MyPostListView.as_view(), name='my-posts'),
    path('posts/bookmarks/', BookmarkListView.as_view(), name='bookmarks'),
    path('posts/<str:slug>/', PostDetailView.as_view(), name='post-detail'),
    path('posts/<str:slug>/like/', LikeToggleView.as_view(), name='post-like'),
    path('posts/<str:slug>/bookmark/', BookmarkToggleView.as_view(), name='post-bookmark'),
    path('my-stats/', MyStatsView.as_view(), name='my-stats'),
    path('authors/<str:username>/', AuthorProfileView.as_view(), name='author-profile'),
]
