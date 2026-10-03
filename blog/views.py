from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.generics import (
    ListAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView, GenericAPIView
)
from rest_framework.response import Response

from accounts.models import AccountUser, DONE, PHOTO_DONE
from base.permissions import IsVerifiedOrReadOnly, IsAuthorOrReadOnly
from .models import Category, Tag, Post, PostLike, Bookmark, PUBLISHED, DRAFT
from .serializers import (
    CategorySerializer, TagSerializer, PostListSerializer,
    PostDetailSerializer, PostWriteSerializer, AuthorSerializer
)


class PostFilterMixin:
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['title', 'content', 'category__name', 'tags__name', 'author__username']
    ordering_fields = ['created_at', 'published_at', 'views', 'likes_count', 'title']
    ordering = ['-published_at', '-created_at']

    def filter_by_params(self, queryset):
        params = self.request.query_params

        category = params.get('category')
        tag = params.get('tag')
        author = params.get('author')

        if category:
            queryset = queryset.filter(category__slug=category)

        if tag:
            queryset = queryset.filter(tags__slug=tag)

        if author:
            queryset = queryset.filter(author__username=author)

        return queryset


class CategoryListView(ListAPIView):
    serializer_class = CategorySerializer
    pagination_class = None
    queryset = Category.objects.annotate(
        posts_count=Count('posts', filter=Q(posts__status=PUBLISHED))
    )


class TagListView(ListAPIView):
    serializer_class = TagSerializer
    pagination_class = None
    queryset = Tag.objects.annotate(
        posts_count=Count('posts', filter=Q(posts__status=PUBLISHED))
    ).filter(posts_count__gt=0).order_by('-posts_count', 'name')


class PostListCreateView(PostFilterMixin, ListCreateAPIView):
    permission_classes = [IsVerifiedOrReadOnly]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PostWriteSerializer

        return PostListSerializer

    def get_queryset(self):
        queryset = Post.objects.published().with_stats(self.request.user)

        return self.filter_by_params(queryset)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class PostDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsVerifiedOrReadOnly, IsAuthorOrReadOnly]
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return PostWriteSerializer

        return PostDetailSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Post.objects.with_stats(user)

        if user.is_authenticated:
            return queryset.filter(Q(status=PUBLISHED) | Q(author=user))

        return queryset.filter(status=PUBLISHED)

    def retrieve(self, request, *args, **kwargs):
        post = self.get_object()

        if post.author_id != request.user.id:
            Post.objects.filter(pk=post.pk).update(views=post.views + 1)
            post.views += 1

        return Response(self.get_serializer(post).data)


class MyPostListView(PostFilterMixin, ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PostListSerializer
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        queryset = Post.objects.filter(author=user).with_stats(user)

        post_status = self.request.query_params.get('status')

        if post_status in (DRAFT, PUBLISHED):
            queryset = queryset.filter(status=post_status)

        return self.filter_by_params(queryset)


class BookmarkListView(PostFilterMixin, ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PostListSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Post.objects.published().filter(bookmarks__user=user).with_stats(user)

        return self.filter_by_params(queryset)


class ToggleView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Post.objects.published()
    lookup_field = 'slug'
    model = None
    related_name = None
    response_key = None

    def post(self, request, slug):
        post = self.get_object()

        obj, created = self.model.objects.get_or_create(user=request.user, post=post)

        if not created:
            obj.delete()

        return Response({
            self.response_key: created,
            'count': getattr(post, self.related_name).count()
        })


class LikeToggleView(ToggleView):
    model = PostLike
    related_name = 'likes'
    response_key = 'liked'


class BookmarkToggleView(ToggleView):
    model = Bookmark
    related_name = 'bookmarks'
    response_key = 'bookmarked'


class MyStatsView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        posts = Post.objects.filter(author=request.user)

        stats = posts.aggregate(
            total_posts=Count('id'),
            published_posts=Count('id', filter=Q(status=PUBLISHED)),
            draft_posts=Count('id', filter=Q(status=DRAFT)),
            total_views=Sum('views'),
        )

        stats['total_views'] = stats['total_views'] or 0
        stats['total_likes'] = PostLike.objects.filter(post__in=posts).count()
        stats['total_bookmarks'] = Bookmark.objects.filter(post__in=posts).count()

        return Response(stats)


class AuthorProfileView(GenericAPIView):
    serializer_class = AuthorSerializer
    queryset = AccountUser.objects.filter(auth_status__in=[DONE, PHOTO_DONE])
    lookup_field = 'username'

    def get(self, request, username):
        author = self.get_object()
        posts = Post.objects.published().filter(author=author)

        stats = posts.aggregate(posts_count=Count('id'), total_views=Sum('views'))

        return Response({
            'author': self.get_serializer(author).data,
            'posts_count': stats['posts_count'],
            'total_views': stats['total_views'] or 0,
            'total_likes': PostLike.objects.filter(post__in=posts).count(),
            'joined': author.date_joined,
        })
