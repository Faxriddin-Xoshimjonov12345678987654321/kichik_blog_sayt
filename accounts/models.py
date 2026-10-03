from django.db import models 
from django.utils import timezone
from django.contrib.auth.hashers import identify_hasher
from django.contrib.auth.models import AbstractUser
from rest_framework_simplejwt.tokens import RefreshToken

from conf.settings import EMAIL_EXPIRE_TIME, PHONE_EXPIRE_TIME
from base.models import BaseModel

import uuid
import random
from datetime import timedelta

NEW, CODE_VERIFY, DONE, PHOTO_DONE = ('new', 'code_verify', 'done', 'photo_done')
VIA_PHONE, VIA_EMAIL = ('via_phone', 'via_email')
USER = ('user')


class AccountUser(AbstractUser):
    AUTH_STATUS = (
        (NEW, NEW),
        (CODE_VERIFY, CODE_VERIFY),
        (DONE, DONE),
        (PHOTO_DONE, PHOTO_DONE)
    )

    AUTH_TYPE = (
        (VIA_EMAIL, VIA_EMAIL),
        (VIA_PHONE, VIA_PHONE),
    )

    AUTH_ROLE = (
        (USER, USER),
    )

    phone_number = models.CharField(max_length=13, unique=True, null=True, blank=True)
    email = models.EmailField(max_length=30, unique=True, blank=True, null=True)
    auth_status = models.CharField(max_length=20, choices=AUTH_STATUS, default=NEW)
    auth_type = models.CharField(max_length=100, choices=AUTH_TYPE, default=VIA_EMAIL)
    auth_role = models.CharField(max_length=30, choices=AUTH_ROLE, default=USER)
    image = models.ImageField(upload_to='users/', blank=True, null=True)
    address = models.CharField(max_length=250, blank=True, null=True)

    def __str__(self):
        return self.username

    @property
    def is_verified(self):
        return self.is_staff or self.auth_status in (DONE, PHOTO_DONE)

    def check_username(self):
        if not self.username:
            ud = str(uuid.uuid4())
            temp_username = f"username{ud[ud.rfind('-')+1:]}"
            

            while AccountUser.objects.filter(username=temp_username).exists():
                temp_username +=str(random.randint(10, 99))

            self.username = temp_username

    def check_pass(self):
        if not self.password:
            ud = str(uuid.uuid4())
            temp_password = f"password{ud[ud.rfind('-')+1:]}"
            self.password = temp_password

    def hashing_pass(self):
        try:
            identify_hasher(self.password)
        except ValueError:
            self.set_password(self.password)

    def email_normalize(self):
        if self.email:
            temp_email = self.email.lower()
            self.email = temp_email

    def token(self):
        refresh = RefreshToken.for_user(self)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        }

    def generate_code(self, verify_type):
        code = random.randint(1000, 9999)

        Verify.objects.create(
            code=code,
            user=self, 
            verify_type=verify_type
        )

        return code

    def save(self, *args, **kwargs):
        self.check_username()
        self.check_pass()
        self.hashing_pass()
        self.email_normalize()
        return super().save(*args, **kwargs)


class Verify(BaseModel):
    VERIFY_TYPE = (
        (VIA_EMAIL, VIA_EMAIL),
        (VIA_PHONE, VIA_PHONE),
    )

    verify_type = models.CharField(max_length=20, choices=VERIFY_TYPE)
    used = models.BooleanField(default=False)
    expire_time = models.DateTimeField()
    code = models.CharField(max_length=4)
    user = models.ForeignKey(AccountUser, on_delete=models.CASCADE, related_name='codes')

    def __str__(self):
        return f"{self.user.username}----{self.code}"

    def save(self, *args, **kwargs):
        if self._state.adding:
            if self.verify_type == VIA_EMAIL:
                self.expire_time = timezone.now() + timedelta(minutes=EMAIL_EXPIRE_TIME)

            else:
                self.expire_time = timezone.now() + timedelta(minutes=PHONE_EXPIRE_TIME)
        super().save(*args, **kwargs)
