from rest_framework.decorators import api_view
from rest_framework import status
from rest_framework.response import Response
from .models import *
from .serializer import *
from django.shortcuts import get_object_or_404
from .utils import *

@api_view(['POST'])
def post_new_report(request): 
    data = request.data 
    serializer = DefectReportSerializer(data=data)
    if serializer.is_valid():
        report = serializer.save()
        if report and getattr(report, 'testerEmail', None):
            send_status_update_email(report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_reports(request, status):
    if status.casefold() == "NEW".casefold():
        reports = DefectReport.objects.filter(status=DefectReport.Status.NEW)
    elif status.casefold() == "FIXED".casefold():
        reports = DefectReport.objects.filter(status=DefectReport.Status.FIXED)
    elif status.casefold() == "OPEN".casefold():
        reports = DefectReport.objects.filter(status=DefectReport.Status.OPEN)
    elif status.casefold() == "ALL".casefold():
        reports = DefectReport.objects.all()
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
def patch_update_report(request, id, dev_id, new_status, new_severity=None, new_priority=None):
    report = get_object_or_404(DefectReport, id=id)
    report.status = new_status
    report.assignedToId_id = dev_id
    if new_severity:
        report.severity = new_severity
    if new_priority:
        report.priority = new_priority
    report.save()
    if report and getattr(report, 'testerEmail', None):
        send_status_update_email(report)
    serializer = DefectReportSerializer(report)
    return Response(serializer.data, status=status.HTTP_200_OK)

# @api_view(['POST'])
# def post_comment(request): 
#     return Response(status=status.HTTP_400_BAD_REQUEST)

