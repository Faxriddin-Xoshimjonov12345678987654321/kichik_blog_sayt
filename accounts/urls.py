from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    SignUpView, VerifyView, ResendCodeView, ChangeUserInfoView, ChangePhotoView,
    LoginView, LogoutView, ChangePasswordView, ProfileView
)

urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('verify/', VerifyView.as_view(), name='verify'),
    path('resend-code/', ResendCodeView.as_view(), name='resend-code'),
    path('change-user-info/', ChangeUserInfoView.as_view(), name='change-user-info'),
    path('change-photo/', ChangePhotoView.as_view(), name='change-photo'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('me/', ProfileView.as_view(), name='me'),
]
