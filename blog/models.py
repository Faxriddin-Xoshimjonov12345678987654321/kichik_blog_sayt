from django.conf import settings
from django.db import models
from django.db.models import Count, Exists, OuterRef, Value, BooleanField
from django.utils import timezone

from base.models import BaseModel
from base.utils import unique_slug

DRAFT, PUBLISHED = ('draft', 'published')


class Category(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True, allow_unicode=True)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(Category, self.name)
        super().save(*args, **kwargs)


class Tag(BaseModel):
    name = models.CharField(max_length=30, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True, allow_unicode=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(Tag, self.name, max_length=50)
        super().save(*args, **kwargs)


class PostQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=PUBLISHED)

    def with_stats(self, user=None):
        queryset = self.select_related('author', 'category').prefetch_related('tags').annotate(
            likes_count=Count('likes', distinct=True)
        )

        if user is not None and user.is_authenticated:
            return queryset.annotate(
                is_liked=Exists(PostLike.objects.filter(post=OuterRef('pk'), user=user)),
                is_bookmarked=Exists(Bookmark.objects.filter(post=OuterRef('pk'), user=user)),
            )

        return queryset.annotate(
            is_liked=Value(False, output_field=BooleanField()),
            is_bookmarked=Value(False, output_field=BooleanField()),
        )


class Post(BaseModel):
    STATUS = (
        (DRAFT, DRAFT),
        (PUBLISHED, PUBLISHED),
    )

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts')
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=255, unique=True, blank=True, allow_unicode=True)
    content = models.TextField()
    image = models.ImageField(upload_to='posts/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS, default=DRAFT)
    views = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)

    objects = PostQuerySet.as_manager()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-published_at']),
        ]

    def __str__(self):
        return self.title

    @property
    def read_time(self):
        return max(1, len(self.content.split()) // 200)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(Post, self.title, max_length=255, with_suffix=True)

        if self.status == PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)


class PostLike(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='post_likes')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'post'], name='unique_post_like'),
        ]

    def __str__(self):
        return f"{self.user.username} -> {self.post.title}"


class Bookmark(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookmarks')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='bookmarks')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'post'], name='unique_post_bookmark'),
        ]

    def __str__(self):
        return f"{self.user.username} -> {self.post.title}"
