from rest_framework.decorators import api_view
from rest_framework import status
from rest_framework.response import Response
from .models import *
from .serializer import *
from django.http import JsonResponse
from django.shortcuts import render

@api_view(['POST'])
def post_new_report(request): 
    tester_data = request.data.get('tester')
    defectReport_data = request.data.get('defectReport')
    
    tester_serializer = TesterSerializer(data=tester_data)
    defectReport_serializer = DefectReportSerializer(data=defectReport_data)

    if tester_serializer.is_valid() and defectReport_serializer.is_valid():
        tester_serializer.save()
        defectReport_serializer.save()

        return Response({
            "tester": tester_serializer.data,
            "defectReport": defectReport_serializer.data
        }, status=status.HTTP_201_CREATED)

    all_errors = {**tester_serializer.errors, **defectReport_serializer.errors}
    return Response(all_errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_new_reports(request):
    queryset = DefectReport.objects.all()
    
    # Grab 'status' from the URL (?status=NE)
    status_filter = request.query_params.get('status')
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
        
    serializer = DefectReportSerializer(queryset, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_assigned_defects(request):
    return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_full_report(request):
    return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH'])
def patch_update_report(request):
    return Response(status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def post_comment(request): 
    return Response(status=status.HTTP_400_BAD_REQUEST)

