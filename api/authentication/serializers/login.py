import jwt
from rest_framework import serializers, exceptions
from django.contrib.auth import authenticate
from datetime import datetime, timedelta
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from api.authentication.models import ActiveSession



def _generate_jwt_token(user):
    token = jwt.encode(
        {"id": user.pk, "exp": datetime.utcnow() + timedelta(days=settings.JWT_TOKEN_LIFETIME_DAYS)},
        settings.SECRET_KEY,
        algorithm="HS256"
    )
    if isinstance(token, bytes):
        token = token.decode('utf-8')

    return token


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=255)
    username = serializers.CharField(max_length=255, read_only=True)
    password = serializers.CharField(max_length=128, write_only=True)

    def validate(self, data):
        login_input = data.get("email", None)
        password = data.get("password", None)

        if login_input is None:
            raise exceptions.ValidationError(
                {"success": False, "msg": "Email or CI is required to login"}
            )
        if password is None:
            raise exceptions.ValidationError(
                {"success": False, "msg": "Password is required to log in."}
            )

        # Try to find user by email OR ci_number
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = None
        # Try email
        user = User.objects.filter(email=login_input).first()
        
        # If not found, try CI
        if not user:
            user = User.objects.filter(ci_number=login_input).first()
            
        # Verify password
        if user is None or not user.check_password(password):
             # Check for special student login (CI as password)
             is_special_login = False
             if user and user.role == 'STUDENT' and user.ci_number == password:
                 # Check if email is empty or needs update (logic can be refined)
                 # Here we assume if they use CI as password, they might need update
                 # Ideally, we check if they ALREADY have a valid email set, but user said "created without email"
                 if not user.email or user.email == '':
                     is_special_login = True
            
             if not is_special_login:
                raise exceptions.AuthenticationFailed({"success": False, "msg": "Wrong credentials"})

        if not user.is_active:
            raise exceptions.ValidationError(
                {"success": False, "msg": "User is not active"}
            )

        try:
            # Use filter().first() to avoid MultipleObjectsReturned crash
            session = ActiveSession.objects.filter(user=user).first()
            if not session:
                raise ObjectDoesNotExist

            if not session.token:
                raise ValueError

            jwt.decode(session.token, settings.SECRET_KEY, algorithms=["HS256"])

        except (ObjectDoesNotExist, ValueError, jwt.ExpiredSignatureError, jwt.InvalidTokenError, jwt.DecodeError):
            # If session exists (but invalid), delete it to avoid duplicates if we were using create
            if session:
                session.delete()
            
            session = ActiveSession.objects.create(
                user=user, token=_generate_jwt_token(user)
            )

        return {
            "success": True,
            "token": session.token,
            "requires_account_update": (user.role == 'STUDENT' and user.ci_number == password),
            "user": {
                "_id": user.pk, 
                "email": user.email, 
                "first_name": user.first_name,
                "paternal_surname": user.paternal_surname,
                "maternal_surname": user.maternal_surname,
                "ci_number": user.ci_number,
                "role": user.role,
                "active_course": user.active_course.id if user.active_course else None
            },
        }
