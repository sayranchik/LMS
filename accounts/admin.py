from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class LMSUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("LMS", {"fields": ("role", "bio")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("LMS", {"fields": ("role",)}),)
    list_display = ("username", "email", "first_name", "last_name", "role", "is_staff")
    list_filter = UserAdmin.list_filter + ("role",)
