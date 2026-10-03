import io

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image
from rest_framework.test import APITestCase

from .models import AccountUser, NEW, CODE_VERIFY, DONE, PHOTO_DONE

FAST_HASHER = override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])


def make_image(name='test.png'):
    buffer = io.BytesIO()
    Image.new('RGB', (10, 10), 'red').save(buffer, format='PNG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')


def make_verified_user(username='tester01', password='Strong-pass-123', email=None):
    user = AccountUser.objects.create(
        username=username,
        email=email or f'{username}@example.com',
        auth_status=DONE,
        password=password,
    )
    return user


@FAST_HASHER
class AuthFlowTests(APITestCase):
    def sign_up(self, value='ali@example.com'):
        response = self.client.post(reverse('signup'), {'email_or_phone_number': value}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['token']['access']}")
        return AccountUser.objects.get(email=value.lower()) if '@' in value else AccountUser.objects.get(phone_number=value)

    def test_full_registration_flow(self):
        user = self.sign_up()
        self.assertEqual(user.auth_status, NEW)
        self.assertEqual(len(mail.outbox), 1)

        code = user.codes.first().code
        response = self.client.post(reverse('verify'), {'code': code}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['auth_status'], CODE_VERIFY)

        response = self.client.put(reverse('change-user-info'), {
            'first_name': 'Ali', 'last_name': 'Valiyev', 'username': 'alivaliyev',
            'password': 'Strong-pass-123', 'confirm_password': 'Strong-pass-123',
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['auth_status'], DONE)

        response = self.client.put(reverse('change-photo'), {'photo': make_image()}, format='multipart')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['auth_status'], PHOTO_DONE)

        self.client.credentials()
        response = self.client.post(reverse('login'), {'userinput': 'ali@example.com', 'password': 'Strong-pass-123'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn('access', response.data['token'])

        response = self.client.post(reverse('login'), {'userinput': 'alivaliyev', 'password': 'Strong-pass-123'}, format='json')
        self.assertEqual(response.status_code, 200)

    def test_phone_signup(self):
        user = self.sign_up('+998901234567')
        self.assertEqual(user.auth_type, 'via_phone')

    def test_duplicate_and_invalid_signup(self):
        self.sign_up()
        self.client.credentials()
        response = self.client.post(reverse('signup'), {'email_or_phone_number': 'ALI@example.com'}, format='json')
        self.assertEqual(response.status_code, 400)
        response = self.client.post(reverse('signup'), {'email_or_phone_number': 'noto\'g\'ri'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_wrong_code_rejected(self):
        user = self.sign_up()
        real = user.codes.first().code
        wrong = '1111' if real != '1111' else '2222'
        response = self.client.post(reverse('verify'), {'code': wrong}, format='json')
        self.assertEqual(response.status_code, 400)
        user.refresh_from_db()
        self.assertEqual(user.auth_status, NEW)

    def test_resend_code_blocked_while_valid(self):
        self.sign_up()
        response = self.client.get(reverse('resend-code'))
        self.assertEqual(response.status_code, 400)

    def test_info_requires_verification_first(self):
        self.sign_up()
        response = self.client.put(reverse('change-user-info'), {
            'first_name': 'Ali', 'last_name': 'Valiyev', 'username': 'alivaliyev',
            'password': 'Strong-pass-123', 'confirm_password': 'Strong-pass-123',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_unverified_user_cannot_login(self):
        user = self.sign_up()
        user.set_password('Strong-pass-123')
        user.save()
        self.client.credentials()
        response = self.client.post(reverse('login'), {'userinput': user.username, 'password': 'Strong-pass-123'}, format='json')
        self.assertEqual(response.status_code, 400)


@FAST_HASHER
class ProfileAndPasswordTests(APITestCase):
    def setUp(self):
        self.user = make_verified_user()
        response = self.client.post(reverse('login'), {'userinput': 'tester01', 'password': 'Strong-pass-123'}, format='json')
        self.refresh = response.data['token']['refresh']
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['token']['access']}")

    def test_profile_get_and_patch(self):
        response = self.client.get(reverse('me'))
        self.assertEqual(response.data['username'], 'tester01')

        response = self.client.patch(reverse('me'), {'address': 'Toshkent', 'email': 'hack@example.com'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['address'], 'Toshkent')
        self.assertEqual(response.data['email'], 'tester01@example.com')

    def test_change_password(self):
        response = self.client.put(reverse('change-password'), {
            'old_password': 'xato', 'new_password': 'Another-pass-456', 'confirm_password': 'Another-pass-456',
        }, format='json')
        self.assertEqual(response.status_code, 400)

        response = self.client.put(reverse('change-password'), {
            'old_password': 'Strong-pass-123', 'new_password': 'Another-pass-456', 'confirm_password': 'Another-pass-456',
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)

        self.client.credentials()
        response = self.client.post(reverse('login'), {'userinput': 'tester01', 'password': 'Another-pass-456'}, format='json')
        self.assertEqual(response.status_code, 200)

    def test_logout_blacklists_refresh(self):
        response = self.client.post(reverse('logout'), {'refresh': self.refresh}, format='json')
        self.assertEqual(response.status_code, 205)

        response = self.client.post(reverse('token-refresh'), {'refresh': self.refresh}, format='json')
        self.assertEqual(response.status_code, 401)

    def test_profile_requires_auth(self):
        self.client.credentials()
        self.assertEqual(self.client.get(reverse('me')).status_code, 401)
