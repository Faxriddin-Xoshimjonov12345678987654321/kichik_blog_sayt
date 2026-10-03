from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import AccountUser, CODE_VERIFY
from accounts.tests import make_verified_user, make_image
from .models import Category, Tag, Post, PostLike, Bookmark, DRAFT, PUBLISHED

FAST_HASHER = override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
CONTENT = 'Bu post uchun yetarlicha uzun matn. ' * 5


def login(client, user):
    token = user.token()['access']
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')


def make_post(author, title='Django haqida post', status=PUBLISHED, **extra):
    return Post.objects.create(author=author, title=title, content=CONTENT, status=status, **extra)


@FAST_HASHER
class PostCrudTests(APITestCase):
    def setUp(self):
        self.author = make_verified_user('author01')
        self.other = make_verified_user('other001')
        self.category = Category.objects.create(name='Dasturlash')
        login(self.client, self.author)

    def test_create_post_with_category_and_tags(self):
        response = self.client.post(reverse('post-list'), {
            'title': 'Birinchi postim', 'content': CONTENT, 'category': self.category.slug,
            'tags': ['Python', 'django', 'python'], 'status': PUBLISHED,
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['author']['username'], 'author01')
        self.assertEqual(sorted(response.data['tags']), ['django', 'python'])
        self.assertEqual(response.data['category'], 'dasturlash')
        self.assertEqual(response.data['likes_count'], 0)
        self.assertIsNotNone(response.data['published_at'])
        self.assertTrue(response.data['slug'].startswith('birinchi-postim-'))

    def test_create_post_with_image_multipart(self):
        response = self.client.post(reverse('post-list'), {
            'title': 'Rasmli post', 'content': CONTENT, 'image': make_image(),
            'tags': ['rasm', 'test'],
        }, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['status'], DRAFT)
        self.assertIsNotNone(response.data['image'])
        self.assertEqual(sorted(response.data['tags']), ['rasm', 'test'])

    def test_create_validation(self):
        response = self.client.post(reverse('post-list'), {'title': 'abc', 'content': 'qisqa'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('title', response.data)
        self.assertIn('content', response.data)

    def test_create_requires_login_and_verification(self):
        payload = {'title': 'Yangi post sarlavhasi', 'content': CONTENT}
        self.client.credentials()
        self.assertEqual(self.client.post(reverse('post-list'), payload, format='json').status_code, 401)

        newbie = AccountUser.objects.create(email='newbie@example.com', auth_status=CODE_VERIFY)
        login(self.client, newbie)
        self.assertEqual(self.client.post(reverse('post-list'), payload, format='json').status_code, 403)

    def test_drafts_hidden_from_public_but_visible_to_author(self):
        draft = make_post(self.author, 'Qoralama post', status=DRAFT)
        make_post(self.author, 'Chop etilgan post')

        self.client.credentials()
        response = self.client.get(reverse('post-list'))
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(self.client.get(reverse('post-detail', args=[draft.slug])).status_code, 404)

        login(self.client, self.other)
        self.assertEqual(self.client.get(reverse('post-detail', args=[draft.slug])).status_code, 404)

        login(self.client, self.author)
        self.assertEqual(self.client.get(reverse('post-detail', args=[draft.slug])).status_code, 200)

    def test_detail_counts_views_except_for_author(self):
        post = make_post(self.author)
        url = reverse('post-detail', args=[post.slug])

        self.assertEqual(self.client.get(url).data['views'], 0)

        login(self.client, self.other)
        self.assertEqual(self.client.get(url).data['views'], 1)
        self.assertEqual(self.client.get(url).data['views'], 2)

        post.refresh_from_db()
        self.assertEqual(post.views, 2)

    def test_only_author_can_update_and_delete(self):
        post = make_post(self.author)
        url = reverse('post-detail', args=[post.slug])

        login(self.client, self.other)
        self.assertEqual(self.client.patch(url, {'title': 'Boshqa sarlavha'}, format='json').status_code, 403)
        self.assertEqual(self.client.delete(url).status_code, 403)

        login(self.client, self.author)
        response = self.client.patch(url, {'title': 'Yangilangan sarlavha', 'tags': ['yangi']}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['title'], 'Yangilangan sarlavha')
        self.assertEqual(response.data['tags'], ['yangi'])
        self.assertEqual(response.data['slug'], post.slug)

        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())

    def test_publishing_draft_sets_published_at(self):
        post = make_post(self.author, status=DRAFT)
        self.assertIsNone(post.published_at)

        response = self.client.patch(reverse('post-detail', args=[post.slug]), {'status': PUBLISHED}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data['published_at'])


@FAST_HASHER
class PostDiscoveryTests(APITestCase):
    def setUp(self):
        self.alice = make_verified_user('alice001')
        self.bob = make_verified_user('bobbob01')
        self.python = Category.objects.create(name='Python')
        self.web = Category.objects.create(name='Veb')
        self.p1 = make_post(self.alice, 'Python asoslari', category=self.python, views=50)
        self.p2 = make_post(self.bob, 'Veb dasturlash', category=self.web, views=10)
        self.p3 = make_post(self.bob, 'Python va Django', category=self.python, views=30)
        self.p1.tags.add(Tag.objects.create(name='python'))
        self.p3.tags.add(Tag.objects.get(name='python'), Tag.objects.create(name='django'))
        PostLike.objects.create(user=self.alice, post=self.p3)
        PostLike.objects.create(user=self.bob, post=self.p3)
        PostLike.objects.create(user=self.bob, post=self.p1)

    def titles(self, response):
        return [item['title'] for item in response.data['results']]

    def test_search(self):
        response = self.client.get(reverse('post-list'), {'search': 'django'})
        self.assertEqual(sorted(self.titles(response)), ['Python va Django'])

    def test_filters(self):
        response = self.client.get(reverse('post-list'), {'category': 'python'})
        self.assertEqual(response.data['count'], 2)

        response = self.client.get(reverse('post-list'), {'tag': 'django'})
        self.assertEqual(self.titles(response), ['Python va Django'])

        response = self.client.get(reverse('post-list'), {'author': 'bobbob01'})
        self.assertEqual(response.data['count'], 2)

        response = self.client.get(reverse('post-list'), {'author': 'bobbob01', 'category': 'python'})
        self.assertEqual(self.titles(response), ['Python va Django'])

    def test_ordering(self):
        response = self.client.get(reverse('post-list'), {'ordering': '-views'})
        self.assertEqual(self.titles(response), ['Python asoslari', 'Python va Django', 'Veb dasturlash'])

        response = self.client.get(reverse('post-list'), {'ordering': '-likes_count'})
        self.assertEqual(self.titles(response)[0], 'Python va Django')
        self.assertEqual(response.data['results'][0]['likes_count'], 2)

    def test_pagination(self):
        response = self.client.get(reverse('post-list'), {'page_size': 2})
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['count'], 3)
        self.assertIsNotNone(response.data['next'])

    def test_likes_counted_without_tag_join_inflation(self):
        response = self.client.get(reverse('post-list'), {'tag': 'python'})
        counts = {item['title']: item['likes_count'] for item in response.data['results']}
        self.assertEqual(counts, {'Python asoslari': 1, 'Python va Django': 2})

    def test_like_toggle_and_flags(self):
        login(self.client, self.alice)
        url = reverse('post-like', args=[self.p2.slug])

        response = self.client.post(url)
        self.assertEqual(response.data, {'liked': True, 'count': 1})
        listing = self.client.get(reverse('post-list'))
        flags = {item['title']: item['is_liked'] for item in listing.data['results']}
        self.assertTrue(flags['Veb dasturlash'])
        self.assertTrue(flags['Python va Django'])
        self.assertFalse(flags['Python asoslari'])

        response = self.client.post(url)
        self.assertEqual(response.data, {'liked': False, 'count': 0})

    def test_like_requires_login(self):
        self.assertEqual(self.client.post(reverse('post-like', args=[self.p1.slug])).status_code, 401)

    def test_bookmarks(self):
        login(self.client, self.alice)

        response = self.client.post(reverse('post-bookmark', args=[self.p2.slug]))
        self.assertEqual(response.data['bookmarked'], True)
        self.client.post(reverse('post-bookmark', args=[self.p3.slug]))

        response = self.client.get(reverse('bookmarks'))
        self.assertEqual(response.data['count'], 2)
        self.assertTrue(all(item['is_bookmarked'] for item in response.data['results']))

        self.client.post(reverse('post-bookmark', args=[self.p3.slug]))
        self.assertEqual(self.client.get(reverse('bookmarks')).data['count'], 1)
        self.assertEqual(Bookmark.objects.filter(user=self.alice).count(), 1)

    def test_my_posts_with_status_filter_and_stats(self):
        make_post(self.bob, 'Bobning qoralamasi', status=DRAFT)
        login(self.client, self.bob)

        self.assertEqual(self.client.get(reverse('my-posts')).data['count'], 3)
        self.assertEqual(self.client.get(reverse('my-posts'), {'status': 'draft'}).data['count'], 1)
        self.assertEqual(self.client.get(reverse('my-posts'), {'status': 'published'}).data['count'], 2)

        stats = self.client.get(reverse('my-stats')).data
        self.assertEqual(stats['total_posts'], 3)
        self.assertEqual(stats['published_posts'], 2)
        self.assertEqual(stats['draft_posts'], 1)
        self.assertEqual(stats['total_views'], 40)
        self.assertEqual(stats['total_likes'], 2)

    def test_my_posts_requires_login(self):
        self.assertEqual(self.client.get(reverse('my-posts')).status_code, 401)

    def test_categories_and_tags(self):
        response = self.client.get(reverse('category-list'))
        counts = {item['slug']: item['posts_count'] for item in response.data}
        self.assertEqual(counts, {'python': 2, 'veb': 1})

        response = self.client.get(reverse('tag-list'))
        self.assertEqual([(t['name'], t['posts_count']) for t in response.data], [('python', 2), ('django', 1)])

    def test_author_profile(self):
        response = self.client.get(reverse('author-profile', args=['bobbob01']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['posts_count'], 2)
        self.assertEqual(response.data['total_views'], 40)
        self.assertEqual(response.data['total_likes'], 2)
        self.assertEqual(self.client.get(reverse('author-profile', args=['yoq-user'])).status_code, 404)


class SlugTests(APITestCase):
    def test_slug_unique_and_unicode(self):
        user = make_verified_user('sluguser')
        first = make_post(user, "O'zbekiston haqida")
        second = make_post(user, "O'zbekiston haqida")
        self.assertNotEqual(first.slug, second.slug)

        cyrillic = make_post(user, 'Ўзбекистон ҳақида')
        self.assertTrue(cyrillic.slug.startswith('ўзбекистон'))

        category = Category.objects.create(name='Fan va texnika')
        self.assertEqual(category.slug, 'fan-va-texnika')
        self.assertEqual(Category.objects.create(name='Fan va  texnika!').slug[:15], 'fan-va-texnika-')

    def test_read_time(self):
        user = make_verified_user('readuser')
        post = Post.objects.create(author=user, title='Uzun post', content='so\'z ' * 450)
        self.assertEqual(post.read_time, 2)
