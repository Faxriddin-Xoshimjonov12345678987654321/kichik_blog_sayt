from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from accounts.models import AccountUser
from .models import Category, Tag, Post


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountUser
        fields = ['username', 'first_name', 'last_name', 'image']


class CategorySerializer(serializers.ModelSerializer):
    posts_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'posts_count']


class TagSerializer(serializers.ModelSerializer):
    posts_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'posts_count']


class PostListSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    category = serializers.SlugRelatedField(slug_field='slug', read_only=True)
    tags = serializers.SlugRelatedField(slug_field='name', many=True, read_only=True)
    excerpt = serializers.SerializerMethodField()
    likes_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.BooleanField(read_only=True)
    is_bookmarked = serializers.BooleanField(read_only=True)
    read_time = serializers.IntegerField(read_only=True)

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'excerpt', 'image', 'author', 'category', 'tags',
            'status', 'views', 'likes_count', 'is_liked', 'is_bookmarked',
            'read_time', 'published_at', 'created_at'
        ]

    def get_excerpt(self, obj):
        text = obj.content.strip()

        if len(text) <= 200:
            return text

        return text[:200].rsplit(' ', 1)[0] + '...'


class PostDetailSerializer(PostListSerializer):
    class Meta(PostListSerializer.Meta):
        fields = PostListSerializer.Meta.fields + ['content', 'updated_at']


class PostWriteSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(
        slug_field='slug', queryset=Category.objects.all(), required=False, allow_null=True
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=30), required=False, max_length=10
    )

    class Meta:
        model = Post
        fields = ['title', 'content', 'image', 'category', 'tags', 'status']

    def validate_title(self, title):
        title = title.strip()

        if len(title) < 5:
            raise ValidationError('Sarlavha kamida 5 ta belgidan iborat bo\'lishi kerak')

        return title

    def validate_content(self, content):
        if len(content.strip()) < 20:
            raise ValidationError('Matn kamida 20 ta belgidan iborat bo\'lishi kerak')

        return content

    def validate_tags(self, tags):
        cleaned = []

        for name in tags:
            name = name.strip().lower()

            if name and name not in cleaned:
                cleaned.append(name)

        return cleaned

    def save_tags(self, post, tags):
        post.tags.set([Tag.objects.get_or_create(name=name)[0] for name in tags])

    def create(self, validated_data):
        tags = validated_data.pop('tags', [])
        post = super().create(validated_data)
        self.save_tags(post, tags)

        return post

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        post = super().update(instance, validated_data)

        if tags is not None:
            self.save_tags(post, tags)

        return post

    def to_representation(self, instance):
        request = self.context['request']
        post = Post.objects.with_stats(request.user).get(pk=instance.pk)

        return PostDetailSerializer(post, context=self.context).data
