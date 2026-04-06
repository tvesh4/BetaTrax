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
    match status.upper():
        case "NEW":
            reports = DefectReport.objects.filter(status=DefectReport.Status.NEW)
        case "FIXED":
            reports = DefectReport.objects.filter(status=DefectReport.Status.FIXED)
        case "OPEN":
            reports = DefectReport.objects.filter(status=DefectReport.Status.OPEN)
        case "ASSIGNED":
            reports = DefectReport.objects.filter(status=DefectReport.Status.ASSIGNED)
        case "ALL":
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
def patch_update_report(request, id, new_status, dev_id=None, new_severity=None, new_priority=None):
    report = get_object_or_404(DefectReport, id=id)
    if new_status in DefectReport.Status:
        match report.status:
            case 'New':
                if new_status == 'Open':
                    report.status = new_status
            case 'Open':
                if new_status == 'Assigned':
                    report.status = new_status
            case 'Assigned':
                if new_status == 'Fixed':
                    report.status = new_status
            case 'Fixed':
                if new_status == 'Resolved':
                    report.status = new_status
    if dev_id: 
        report.assignedToId_id = dev_id
    if new_severity and new_severity in DefectReport.Severity:
        report.severity = new_severity
    if new_priority and new_priority in DefectReport.Priority:
        report.priority = new_priority
    report.save()
    if report and getattr(report, 'testerEmail', None):
        send_status_update_email(report)
    serializer = DefectReportSerializer(report)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['POST'])
def post_comment(request, id): 
    report = get_object_or_404(DefectReport, id=id)
    serializer = CommentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(defectReportId=report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

