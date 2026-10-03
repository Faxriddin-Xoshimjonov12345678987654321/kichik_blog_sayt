from django.contrib.auth.models import update_last_login
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, GenericAPIView, UpdateAPIView, RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import NEW, CODE_VERIFY, AccountUser
from .serializers import (
    SignUpSerializer, VerifySerializer, ChangeUserInfoSerializer, ChangePhotoSerializer,
    LoginSerializer, LogoutSerializer, ChangePasswordSerializer, UserSerializer
)

from base.utils import send_verify_code


class SignUpView(CreateAPIView):
    serializer_class = SignUpSerializer
    queryset = AccountUser.objects.all()


class VerifyView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VerifySerializer
    queryset = AccountUser.objects.all()

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user

        verify = user.codes.filter(
            code=serializer.validated_data['code'],
            used=False,
            expire_time__gte=timezone.now()
        ).first()

        if verify is None:
            raise ValidationError({'code': 'Kod xato yoki muddati o\'tgan'})

        verify.used = True
        verify.save()

        if user.auth_status == NEW:
            user.auth_status = CODE_VERIFY
            user.save()

        return Response({
            'message': 'Kod tasdiqlandi',
            'auth_status': user.auth_status,
            'token': user.token()
        })


class ResendCodeView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.auth_status != NEW:
            raise ValidationError('Siz allaqachon tasdiqlangansiz')

        if user.codes.filter(used=False, expire_time__gte=timezone.now()).exists():
            raise ValidationError('Kodingiz hali yaroqli, biroz kuting')

        code = user.generate_code(user.auth_type)
        send_verify_code(user, code)

        return Response({'message': 'Yangi kod yuborildi'})


class ChangeUserInfoView(UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangeUserInfoSerializer
    http_method_names = ['put', 'options']

    def get_object(self):
        return self.request.user


class ChangePhotoView(UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangePhotoSerializer
    http_method_names = ['put', 'options']

    def get_object(self):
        return self.request.user


class LoginView(GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        update_last_login(None, user)

        return Response({
            'auth_status': user.auth_status,
            'token': user.token()
        })


class LogoutView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LogoutSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            RefreshToken(serializer.validated_data['refresh']).blacklist()
        except TokenError:
            raise ValidationError({'refresh': 'Token yaroqsiz yoki muddati o\'tgan'})

        return Response({'message': 'Tizimdan chiqildi'}, status=status.HTTP_205_RESET_CONTENT)


class ChangePasswordView(UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangePasswordSerializer
    http_method_names = ['put', 'options']

    def get_object(self):
        return self.request.user


class ProfileView(RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer
    http_method_names = ['get', 'patch', 'options']

    def get_object(self):
        return self.request.user
