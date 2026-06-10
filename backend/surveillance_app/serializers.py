from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password_confirm', 'first_name', 'last_name')
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': False},
            'last_name': {'required': False},
        }

    def validate(self, attrs):
        """
        Validate that passwords match

        Query Parameters:
        - attrs: Dictionary containing password and password_confirm
        - Returns: Validated attribute dictionary
        """
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def validate_email(self, value):
        """
        Validate that email is unique

        Query Parameters:
        - value: Email string to check
        - Returns: Validated email string
        """
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        """
        Create a new admin user

        Query Parameters:
        - validated_data: Dictionary of validated user data
        - Returns: Created User instance
        """
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        # Create user as staff/admin
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email'),
            password=password,
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            is_staff=True,  # Make them admin/staff
            is_superuser=False  # Make them superuser for full admin access
        )
        return user

class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login - supports both email and username"""
    email = serializers.CharField(required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(style={'input_type': 'password'}, write_only=True)

    def validate(self, attrs):
        """
        Validate user credentials - accepts email or username

        Query Parameters:
        - attrs: Dictionary containing email/username and password
        - Returns: Dictionary with authenticated user object
        """
        email = attrs.get('email', '').strip()
        username = attrs.get('username', '').strip()
        password = attrs.get('password')

        if not password:
            raise serializers.ValidationError('Password is required.')

        # Support both email and username login
        login_field = email if email else username
        if not login_field:
            raise serializers.ValidationError('Email or username is required.')

        # Try to find user by email first, then by username
        try:
            from django.contrib.auth.models import User
            user_obj = None
            if '@' in login_field:
                # Try to find by email
                try:
                    user_obj = User.objects.get(email=login_field)
                except User.DoesNotExist:
                    pass
            
            # If not found by email, try by username
            if not user_obj:
                user_obj = User.objects.get(username=login_field)
            
            # Authenticate with username (Django's authenticate uses username)
            user = authenticate(request=self.context.get('request'), username=user_obj.username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid email/username or password.')
            if not user.is_staff:
                raise serializers.ValidationError('Access denied. Admin access required.')
            attrs['user'] = user
            return attrs
            
        except User.DoesNotExist:
            raise serializers.ValidationError('Invalid email/username or password.')

class UserSerializer(serializers.ModelSerializer):
    """Serializer for user information"""
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser')
        read_only_fields = ('id', 'is_staff', 'is_superuser')


