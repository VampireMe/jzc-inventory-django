from django.contrib import admin

from .models import Department, Role, UserRole


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    search_fields = ("name", "code")


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "department", "status", "approved_by", "updated_at")
    list_filter = ("role", "department", "status")
    search_fields = ("user__username", "department__name")

