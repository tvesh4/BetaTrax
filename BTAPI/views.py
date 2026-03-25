from rest_framework.decorators import api_view
from rest_framework import status
from rest_framework.response import Response
from .models import *
from .serializer import *
from django.http import JsonResponse
from django.shortcuts import render

@api_view(['POST'])
def post_new_report(request): 



@api_view(['GET'])
def get_new_reports(request):
    users = User.objects.all()
    serializer = UserSerializer(users, many=True)
    return JsonResponse(serializer.data, safe=False)

@api_view(['GET'])
def get_assigned_defects(request):


@api_view(['GET'])
def get_full_report(request):


@api_view(['PATCH'])
def patch_update_report(request):


@api_view(['POST'])
def post_comment(request): 

