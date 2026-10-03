from django.core.mail import send_mail
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError

import re
import uuid


email_regrex = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
phone_regrex = re.compile(r'^\+998(90|91|93|94|95|98|99|33|97|71)\d{7}$')


def email_phone_regrex(user_input):
    if re.fullmatch(email_regrex, user_input):
        return 'email'

    elif re.fullmatch(phone_regrex, user_input):
        return 'phone'

    else:
        raise ValidationError('Siz xato email yoki telefon raqam kiritdingiz')


def send_verify_code(user, code):
    if user.email:
        send_mail(
            subject='Tasdiqlash kodi',
            message=f'Sizning tasdiqlash kodingiz: {code}',
            from_email=None,
            recipient_list=[user.email],
        )
        print(f"EMAIL CODE: {code}")

    elif user.phone_number:
        print(f"PHONE NUMBER CODE: {code}")


def unique_slug(model, value, max_length=120, with_suffix=False):
    base_slug = slugify(value, allow_unicode=True)[:max_length - 9].strip('-') or 'item'
    slug = f"{base_slug}-{uuid.uuid4().hex[:8]}" if with_suffix else base_slug

    while model.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{uuid.uuid4().hex[:8]}"

    return slug
