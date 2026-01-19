from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .serializers import LoginSerializer

@api_view(['POST'])
@permission_classes([AllowAny])
def login_api(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password']
        )
        
        if not user:
            return Response({"error": "Invalid Credentials"}, status=400)
        
        token, _ = Token.objects.get_or_create(user=user)
        
        # Get role and employee data
        role = user.groups.first().name if user.groups.exists() else "No Role"
        
        return Response({
            "token": token.key,
            "username": user.username,
            "role": role,
            "primary_outlet": user.employee_profile.primary_outlet.name if hasattr(user, 'employee_profile') else None
        })
    return Response(serializer.errors, status=400)