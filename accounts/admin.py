from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AccountUser, Verify


@admin.register(AccountUser)
class AccountUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'phone_number', 'auth_status', 'is_staff']
    list_filter = ['auth_status', 'auth_type', 'is_staff']
    search_fields = ['username', 'email', 'phone_number']
    fieldsets = UserAdmin.fieldsets + (
        ('Qo\'shimcha ma\'lumotlar', {
            'fields': ('phone_number', 'auth_status', 'auth_type', 'auth_role', 'image', 'address')
        }),
    )


@admin.register(Verify)
class VerifyAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'verify_type', 'used', 'expire_time']
    list_filter = ['verify_type', 'used']
    search_fields = ['user__username', 'user__email']
