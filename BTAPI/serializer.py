from rest_framework import serializers
from .models import *
from django.contrib.auth.models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

# class TesterSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Tester
#         fields = '__all__'

class UserTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token['username'] = user.username
        token['is_owner'] = user.groups.filter(name='Owner').exists()
        token['is_developer'] = user.groups.filter(name='Developer').exists()

        return token

class ProductSerializer(serializers.ModelSerializer): #pbi 6 - sprint 2 allows PO to register product by API
    ownerId = serializers.ReadOnlyField(source='ownerId.username')
    class Meta:
        model = Product
        fields = ['id', 'displayName', 'description', 'currentVersion', 'isActiveBeta', 'ownerId']
        # extra_kwargs = {
        #     'ownerId': {'read_only': True}
        # }

# class ProductOwnerSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ProductOwner
#         fields = ['id', 'fullName', 'email', 'username', 'isActive', 'productId']

# class DeveloperSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Developer
#         fields = '__all__'

class CommentSerializer(serializers.ModelSerializer):
    authorUsername = serializers.ReadOnlyField(source='authorId.username')
    class Meta:
        model = Comment
        fields = ['id', 'authorUsername', 'content', 'createdAt']
        extra_kwargs = {
            'authorId': {'read_only': True}
        }

class DefectReportSerializer(serializers.ModelSerializer):
    testerUsername = serializers.ReadOnlyField(source='testerId.username')
    # sprint 2 pbi 7 duplicate parent link
    comments = CommentSerializer(many=True, read_only=True)
    children = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    parent = serializers.PrimaryKeyRelatedField(queryset=DefectReport.objects.all(), required=False)
    class Meta:
        model = DefectReport
        fields = '__all__'
        read_only_fields = ['status', 'parent', 'children'] # status to be changed thru custom actions
        extra_kwargs = {
            'testerId': {'read_only': True},
        }

    def validate(self, data):
        
        # sprint2: ensuring a report cannot be its own parent
        
        if data.get('parent') and self.instance:
            if data['parent'].id == self.instance.id:
                raise serializers.ValidationError("A report cannot be a duplicate of itself.")
        
        request = self.context.get('request')
        
        if request and request.user and request.user.is_authenticated:
            user_email = request.user.email
            extra_emails = data.get('email', '')
            if extra_emails and user_email:
                data['email'] = f"{user_email}, {extra_emails}"
            else:
                if extra_emails:
                    data['email'] = extra_emails
                if user_email:
                    data['email'] = user_email
        
        return data

class ReportLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefectReport
        fields = ['id', 'title', 'status']

