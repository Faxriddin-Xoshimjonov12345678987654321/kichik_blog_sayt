from django.contrib.auth.password_validation import validate_password
from django.core.validators import FileExtensionValidator
from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import AccountUser, VIA_EMAIL, VIA_PHONE, NEW, CODE_VERIFY, DONE, PHOTO_DONE

from base.utils import email_phone_regrex, send_verify_code


class SignUpSerializer(serializers.ModelSerializer):
    email_or_phone_number = serializers.CharField(write_only=True)

    class Meta:
        model = AccountUser
        fields = ['auth_status', 'auth_type', 'auth_role', 'email_or_phone_number']
        extra_kwargs = {
            'auth_status': {'read_only': True},
            'auth_type': {'read_only': True},
            'auth_role': {'read_only': True},
        }

    def create(self, validated_data):
        user = AccountUser(**validated_data)
        user.save()

        code = user.generate_code(user.auth_type)
        send_verify_code(user, code)

        return user

    def to_representation(self, instance):
        data = super().to_representation(instance)

        return {
            'token': instance.token(),
            'data': data
        }

    def validate(self, attrs):
        user_input = attrs.get('email_or_phone_number').strip()

        user_input_type = email_phone_regrex(user_input)

        if user_input_type == 'email':
            user_input = user_input.lower()

            if AccountUser.objects.filter(email=user_input).exists():
                raise ValidationError('Bu email allaqachon ro\'yxatdan o\'tgan')

            data = {
                'email': user_input,
                'auth_type': VIA_EMAIL
            }

        else:
            if AccountUser.objects.filter(phone_number=user_input).exists():
                raise ValidationError('Bu telefon raqam allaqachon ro\'yxatdan o\'tgan')

            data = {
                'phone_number': user_input,
                'auth_type': VIA_PHONE
            }

        return data


class VerifySerializer(serializers.Serializer):
    code = serializers.CharField(min_length=4, max_length=4)


class ChangeUserInfoSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate_username(self, username):
        if len(username) < 5:
            raise ValidationError('Username kamida 5 ta belgidan iborat bo\'lishi kerak')

        if username.isdigit():
            raise ValidationError('Username faqat raqamlardan iborat bo\'lmasligi kerak')

        user = self.context['request'].user

        if AccountUser.objects.filter(username=username).exclude(pk=user.pk).exists():
            raise ValidationError('Bu username band')

        return username

    def validate(self, attrs):
        user = self.context['request'].user

        if user.auth_status == NEW:
            raise ValidationError('Avval tasdiqlash kodini kiriting')

        if attrs['password'] != attrs['confirm_password']:
            raise ValidationError('Parollar bir xil emas')

        validate_password(attrs['password'], user)

        return attrs

    def update(self, instance, validated_data):
        instance.first_name = validated_data['first_name']
        instance.last_name = validated_data['last_name']
        instance.username = validated_data['username']
        instance.set_password(validated_data['password'])

        if instance.auth_status == CODE_VERIFY:
            instance.auth_status = DONE

        instance.save()

        return instance

    def to_representation(self, instance):
        return {
            'message': 'Ma\'lumotlar saqlandi',
            'auth_status': instance.auth_status,
            'token': instance.token()
        }


class ChangePhotoSerializer(serializers.Serializer):
    photo = serializers.ImageField(
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )

    def validate_photo(self, photo):
        if photo.size > 5 * 1024 * 1024:
            raise ValidationError('Rasm hajmi 5 MB dan oshmasligi kerak')

        return photo

    def validate(self, attrs):
        user = self.context['request'].user

        if user.auth_status not in (DONE, PHOTO_DONE):
            raise ValidationError('Avval shaxsiy ma\'lumotlaringizni to\'ldiring')

        return attrs

    def update(self, instance, validated_data):
        instance.image = validated_data['photo']

        if instance.auth_status == DONE:
            instance.auth_status = PHOTO_DONE

        instance.save()

        return instance

    def to_representation(self, instance):
        request = self.context['request']

        return {
            'message': 'Rasm saqlandi',
            'auth_status': instance.auth_status,
            'image': request.build_absolute_uri(instance.image.url)
        }


class LoginSerializer(serializers.Serializer):
    userinput = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        userinput = attrs['userinput'].strip()

        user = AccountUser.objects.filter(
            Q(username=userinput) | Q(email=userinput.lower()) | Q(phone_number=userinput)
        ).first()

        if user is None or not user.check_password(attrs['password']):
            raise ValidationError('Login yoki parol xato')

        if not user.is_active:
            raise ValidationError('Akkaunt faol emas')

        if not user.is_verified:
            raise ValidationError('Ro\'yxatdan o\'tish yakunlanmagan')

        attrs['user'] = user

        return attrs


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context['request'].user

        if not user.check_password(attrs['old_password']):
            raise ValidationError({'old_password': 'Eski parol xato'})

        if attrs['new_password'] != attrs['confirm_password']:
            raise ValidationError('Yangi parollar bir xil emas')

        validate_password(attrs['new_password'], user)

        return attrs

    def update(self, instance, validated_data):
        instance.set_password(validated_data['new_password'])
        instance.save()

        return instance

    def to_representation(self, instance):
        return {
            'message': 'Parol muvaffaqiyatli o\'zgartirildi',
            'token': instance.token()
        }


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountUser
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email',
            'phone_number', 'image', 'address', 'auth_status', 'date_joined'
        ]
        read_only_fields = ['id', 'email', 'phone_number', 'auth_status', 'date_joined']
        extra_kwargs = {'username': {'min_length': 5}}
