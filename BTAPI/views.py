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
def patch_update_report(request, id):  
    
    new_status = request.query_params.get('status')
    new_severity = request.query_params.get('severity')
    new_priority = request.query_params.get('priority')
    new_parent = request.query_params.get('parent')
    # dev_id = request.query_params.get('dev')
    report = get_object_or_404(DefectReport, id=id)
    if new_status and new_status in DefectReport.Status:
        match report.status:
            case 'New':
                # only if role == "ProductOwner", 'Closed' = Cannot Reproduce, Duplicate, Rejected
                if new_status == 'Open' or new_status == 'Closed':
                    report.status = new_status
                    if new_status == 'Closed':
                        if new_parent:
                            new_parent_id = get_object_or_404(DefectReport, id=new_parent)
                            report.parent_id = new_parent_id
                            if getattr(new_parent, 'testerEmail', None):
                                send_duplicate_update_email(new_parent, report)
                                send_duplicate_update_email(report, new_parent)
                        if report.parent:
                            if getattr(report.parent, 'testerEmail', None):
                                send_duplicate_update_email(report.parent, report)
                                send_duplicate_update_email(report, report.parent)
            case ('Open', 'Reopened'):
                # only if role == "Developer"
                if new_status == 'Assigned':
                    report.status = new_status
            case 'Assigned':
                # only if role == "Developer", 'Closed' = Cannot Reproduce
                if new_status == 'Fixed' or new_status == 'Closed':
                    report.status = new_status
            case 'Fixed':
                # only if role == "ProductOwner"
                if new_status == 'Resolved':
                    report.status = new_status
                # only if role == "Tester" or role == "ProductOwner"
                elif new_status == 'Reopened':
                    report.status = new_status
    if report and getattr(report, 'testerEmail', None):
        send_status_update_email(report)
    if report.children:
        for child in report.children.all():
            getattr(child, 'testerEmail', None)
            send_children_update_email(child)
    if report.productId.ownerId and getattr(report.productId.ownerId, 'email', None):
        send_po_update_email(report)

    # if dev_id: 
    #     report.assignedToId_id = dev_id
    if new_severity: 
        if new_severity in DefectReport.Severity:
            report.severity = new_severity
    if new_priority: 
        if new_priority in DefectReport.Priority:
            report.priority = new_priority
    report.save()
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

@api_view(['POST'])
def post_new_product(request): 
    data = request.data 
    serializer = ProductSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
