from rest_framework import permissions

from accounts.models import DONE, PHOTO_DONE


def is_verified(user):
    return bool(
        user
        and user.is_authenticated
        and (user.is_staff or user.auth_status in (DONE, PHOTO_DONE))
    )


class IsVerifiedOrReadOnly(permissions.BasePermission):
    message = "Bu amalni bajarish uchun ro'yxatdan o'tishni to'liq yakunlang"

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return is_verified(request.user)


class IsAuthorOrReadOnly(permissions.BasePermission):
    message = "Siz faqat o'zingizning postingizni o'zgartira olasiz"

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return obj.author_id == request.user.id
