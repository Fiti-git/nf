from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Outlet, Employee

@admin.register(Outlet)
class OutletAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    search_fields = ("code", "name")

# This allows editing Employee data inside the User page
class EmployeeInline(admin.StackedInline):
    model = Employee
    can_delete = False
    verbose_name_plural = 'Employee Profile'
    filter_horizontal = ("outlets",) # Makes selecting many outlets easy

class UserAdmin(BaseUserAdmin):
    inlines = (EmployeeInline,)
    list_display = ("username", "email", "get_role", "is_staff")

    def get_role(self, obj):
        return ", ".join([g.name for g in obj.groups.all()])
    get_role.short_description = 'Role'

# Replace default User admin with our custom one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)