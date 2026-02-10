from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from api.authentication.serializers import RegisterSerializer


class RegisterViewSet(viewsets.ModelViewSet):
    http_method_names = ["post"]
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        # Extract data
        email = request.data.get('email')
        ci_number = request.data.get('ci_number')
        password = request.data.get('password')
        username = request.data.get('username')

        # Check if user exists by CI (Account Claim)
        from api.user.models import User
        existing_user_by_ci = User.objects.filter(ci_number=ci_number).first()

        if existing_user_by_ci:
            # Case A: User Found by CI -> Claim/Update Account
            user = existing_user_by_ci
            user.email = email
            user.username = username or email # Keep username synced with email if provided, or default to email
            user.set_password(password)
            user.save()
            
            return Response(
                {
                    "success": True,
                    "userID": user.id,
                    "msg": "Account verified and updated successfully.",
                },
                status=status.HTTP_200_OK,
            )
        
        # Case B: New User -> Check if email is available
        if User.objects.filter(email=email).exists():
             return Response(
                {
                    "success": False,
                    "msg": "Email already registered.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Proceed with standard creation
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                "success": True,
                "userID": user.id,
                "msg": "The user was successfully registered",
            },
            status=status.HTTP_201_CREATED,
        )
