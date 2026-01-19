from django.db import models
from django.contrib.auth.models import User

class Outlet(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="employee_profile")
    primary_outlet = models.ForeignKey(
        Outlet, 
        on_delete=models.PROTECT, 
        related_name="primary_staff"
    )
    outlets = models.ManyToManyField(
        Outlet, 
        related_name="assigned_staff",
        blank=True
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.user.username