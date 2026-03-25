from rest_framework.decorators import api_view
from rest_framework import status
from rest_framework.response import Response
from .models import *
from .serializer import *
from django.shortcuts import get_object_or_404

@api_view(['POST'])
def post_new_report(request): 
    data = request.data 
    serializer = DefectReportSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_new_reports(request):
    reports = DefectReport.objects.filter(status=DefectReport.Status.NEW)
    serializer = ReportLiteSerializer(reports, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_assigned_defects(request, id):
    reports = DefectReport.objects.filter(
        status=DefectReport.Status.ASSIGNED,
        assignedToId=id
    )
    data = reports.values('id', 'status', 'title')
    if not data:
        return Response({"message": "No assigned reports for this developer"}, status=200)
    return Response(data)

@api_view(['GET'])
def get_full_report(request, id):
    report = get_object_or_404(DefectReport, pk=id)
    serializer = DefectReportSerializer(report)
    return Response(serializer.data)

@api_view(['PATCH'])
def patch_update_report(request):


    return Response(status=status.HTTP_400_BAD_REQUEST)


# @api_view(['POST'])
# def post_comment(request): 
#     return Response(status=status.HTTP_400_BAD_REQUEST)

