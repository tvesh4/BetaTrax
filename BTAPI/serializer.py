from rest_framework import serializers
from .models import *

class TesterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tester
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'displayName', 'description', 'currentVersion', 'isActiveBeta']

class ProductOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductOwner
        fields = ['id', 'fullName', 'email', 'username', 'isActive', 'productId']

class DeveloperSerializer(serializers.ModelSerializer):
    class Meta:
        model = Developer
        fields = ['id', 'productId', 'fullName', 'email', 'username', 'isActive']

class DefectReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefectReport
        fields = '__all__'

class ReportLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefectReport
        fields = ['id', 'title', 'status']