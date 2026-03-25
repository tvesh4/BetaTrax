from rest_framework import serializers
from .models import *

class TesterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tester
        fields = '__all__'
