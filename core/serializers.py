from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Employee, Outlet


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

class OutletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Outlet
        fields = ['id', 'code', 'name']

class EmployeeSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    primary_outlet_details = OutletSerializer(source='primary_outlet', read_only=True)

    class Meta:
        model = Employee
        fields = ['primary_outlet', 'primary_outlet_details', 'is_active']

    def get_role(self, obj):
        return obj.user.groups.first().name if obj.user.groups.exists() else None
    

