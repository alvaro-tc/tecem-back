from api.user.models import User
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    date = serializers.DateTimeField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "date", "first_name", "paternal_surname", "maternal_surname", "ci_number", "phone", "role", "active_course"]
        read_only_field = ["id"]


class ManageUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'role', 'is_active', 'date',
                  'first_name', 'paternal_surname', 'maternal_surname', 'ci_number', 'phone']
        read_only_fields = ['id', 'date']

    def validate_email(self, value):
        if not value:
            return None
        return value

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class ProfileUpdateSerializer(serializers.Serializer):
    # Fields that can be updated
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    paternal_surname = serializers.CharField(max_length=255, required=False, allow_blank=True)
    maternal_surname = serializers.CharField(max_length=255, required=False, allow_blank=True)
    ci_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    active_course = serializers.CharField(required=False, allow_null=True)
    
    # Password change fields
    old_password = serializers.CharField(write_only=True, required=False)
    new_password = serializers.CharField(write_only=True, required=False)
    confirm_password = serializers.CharField(write_only=True, required=False)

    def validate(self, data):
        user = self.context['request'].user
        
        # Password change validation
        if 'new_password' in data or 'old_password' in data:
            if not data.get('old_password'):
                raise serializers.ValidationError({"old_password": "Se requiere la contraseña actual"})
            if not data.get('new_password'):
                raise serializers.ValidationError({"new_password": "Se requiere la nueva contraseña"})
            if not data.get('confirm_password'):
                raise serializers.ValidationError({"confirm_password": "Debe confirmar la nueva contraseña"})
            
            # Verify old password
            if not user.check_password(data['old_password']):
                raise serializers.ValidationError({"old_password": "Contraseña actual incorrecta"})
            
            # Verify password match
            if data['new_password'] != data['confirm_password']:
                raise serializers.ValidationError({"confirm_password": "Las contraseñas no coinciden"})
        
        # Role-based field validation
        if user.role != 'ADMIN':
            # Non-admin users can only edit email, phone, and password
            restricted_fields = ['first_name', 'paternal_surname', 'maternal_surname', 'ci_number']
            for field in restricted_fields:
                if field in data:
                    raise serializers.ValidationError({field: "No tiene permisos para editar este campo"})
        
        return data


class UserCredentialsUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(error_messages={
        'required': 'Este campo es obligatorio.',
        'invalid': 'Introduzca una dirección de correo electrónico válida.'
    })
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        min_length=8,
        error_messages={
            'required': 'Este campo es obligatorio.',
            'min_length': 'La contraseña debe tener al menos 8 caracteres.'
        }
    )

    def validate_email(self, value):
        user = self.context['request'].user
        if User.objects.filter(email=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("Este correo electrónico ya está en uso por otro usuario.")
        return value

    def validate_password(self, value):
        user = self.context['request'].user
        
        # Check against user attributes
        if value.lower() == user.email.lower() if user.email else False:
             raise serializers.ValidationError("La contraseña no puede ser igual a tu correo electrónico.")
        
        # Basic complexity check
        if value.isdigit():
             raise serializers.ValidationError("La contraseña no puede contener solo números.")
        
        return value

    def update(self, instance, validated_data):
        instance.email = validated_data['email']
        instance.set_password(validated_data['password'])
        instance.save()
        return instance

