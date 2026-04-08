from rest_framework import serializers
from .models import *
from django.contrib.auth.models import User

# class TesterSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Tester
#         fields = '__all__'

class ProductSerializer(serializers.ModelSerializer): #pbi 6 - sprint 2 allows PO to register product by API
    # owner = serializers.ReadOnlyField(source='owner.username')
    class Meta:
        model = Product
        fields = ['id', 'displayName', 'description', 'currentVersion', 'isActiveBeta', 'ownerId']

class ProductOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductOwner
        fields = ['id', 'fullName', 'email', 'username', 'isActive', 'productId']

class DeveloperSerializer(serializers.ModelSerializer):
    class Meta:
        model = Developer
        fields = ['id', 'productId', 'fullName', 'email', 'username', 'isActive']

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'authorId', 'content', 'createdAt']

class DefectReportSerializer(serializers.ModelSerializer):
    # sprint 2 pbi 7 duplicate parent link
    comments = CommentSerializer(many=True, read_only=True)
    children = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    parent = serializers.PrimaryKeyRelatedField(queryset=DefectReport.objects.all(), required=False)
    class Meta:
        model = DefectReport
        fields = '__all__'
        read_only_fields = ['status', 'parent', 'children'] # status to be changed thru custom actions

    def validate(self, data):
        
        # sprint2: ensuring a report cannot be its own parent
        
        if data.get('parent') and self.instance:
            if data['parent'].id == self.instance.id:
                raise serializers.ValidationError("A report cannot be a duplicate of itself.")
        return data

class ReportLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefectReport
        fields = ['id', 'title', 'status']

