from rest_framework.decorators import api_view, permission_classes
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .permissions import IsUser, IsDeveloper, IsOwner
from .models import *
from .serializer import *
from django.shortcuts import get_object_or_404
from .utils import *

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_new_report(request): 
    serializer = DefectReportSerializer(data=request.data)
    if serializer.is_valid():
        report = serializer.save(testerId=request.user)
        if request.user.email:
            send_status_update_email(report)
        if report.productId.ownerId and report.productId.ownerId.email:
            send_po_update_email(report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated, IsDeveloper | IsOwner])
def get_assigned_defects(request, id):
    reports = DefectReport.objects.filter(
        status=DefectReport.Status.ASSIGNED,
        assignedToId=id.title()
    )
    data = reports.values('id', 'status', 'title')
    if not data:
        return Response({"message": "No assigned reports for this developer"}, status=200)
    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_full_report(request, id):
    report = get_object_or_404(DefectReport, pk=id.title())
    serializer = DefectReportSerializer(report)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_developer_metric(request, id):
    developer = get_object_or_404(Developer, user__username=id.title())

    fixed_count = developer.fixedCount
    reopened_count = developer.reopenedCount

    report = "Insufficient data"
    if fixed_count >= 20:
        ratio = reopened_count / fixed_count
        match ratio:
            case val if val < (1/32):
                report = "Good"
            case val if val < (1/8):
                report = "Fair"
            case _:
                report = "Poor"

    return Response({"report": report})

@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsUser | IsOwner | IsDeveloper])
def patch_update_report(request, id):  
    
    new_status = request.query_params.get('status')
    new_severity = request.query_params.get('severity')
    new_priority = request.query_params.get('priority')
    new_parent = request.query_params.get('parent')
    # dev_id = request.query_params.get('dev')
    report = get_object_or_404(DefectReport, id=id.title())
    
    user = request.user
    is_owner = user.groups.filter(name='Owner').exists()
    is_developer = user.groups.filter(name='Developer').exists()
    status_changed = False

    if new_status and new_status.title() in DefectReport.Status:
        match report.status:
            case 'New':
                # only if role == "ProductOwner", 'Closed' = Cannot Reproduce, Duplicate, Rejected
                if is_owner and (new_status.title() == 'Open' or new_status.title() in ('Duplicate', 'Rejected')):
                    report.status = new_status.title()
                    status_changed = True
                    if new_status in ('Duplicate', 'Rejected'):
                        if report.parent:
                            if report.parent.testerId.email:
                                send_duplicate_update_email(report.parent, report)
                                send_duplicate_update_email(report, report.parent)
                        if new_parent:
                            new_parent_id = get_object_or_404(DefectReport, id=new_parent)
                            report.parent_id = new_parent_id
                            if new_parent_id.testerId.email:
                                send_duplicate_update_email(new_parent_id, report)
                                send_duplicate_update_email(report, new_parent_id)
            case ('Open' | 'Reopened'):
                # only if role == "Developer"
                if is_developer and new_status.title() == 'Assigned':
                    report.status = new_status.title()
                    status_changed = True
                    report.assignedToId = user
            case 'Assigned':
                # only if role == "Developer", 'Closed' = Cannot Reproduce
                if is_developer:
                    if new_status.title() == 'Fixed':
                        report.status = new_status.title()
                        status_changed = True
                        request.user.developer_profile.fixedCount += 1
                        request.user.developer_profile.save()
                    elif new_status.title() == 'Cannot Reproduce':
                        report.status = new_status.title()
                        status_changed = True
            case 'Fixed':
                # only if role == "ProductOwner"
                if is_owner:
                    if new_status.title() == 'Resolved': 
                        report.status = new_status.title()
                        status_changed = True
                    elif new_status.title() == 'Reopened':
                        report.status = new_status.title()
                        report.assignedToId.developer_profile.reopenedCount += 1
                        report.assignedToId.developer_profile.save()
                        status_changed = True
    if report and report.testerId.email and status_changed:
        send_status_update_email(report)
    if report.children and status_changed:
        for child in report.children.all():
            send_children_update_email(child)
    if report.productId.ownerId and report.productId.ownerId.email and status_changed:
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
@permission_classes([IsAuthenticated])
def post_comment(request, id): 
    report = get_object_or_404(DefectReport, id=id.title())
    serializer = CommentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(defectReportId=report, authorId=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsOwner | IsDeveloper])
def post_new_product(request): 
    data = request.data 
    serializer = ProductSerializer(data=data)
    if serializer.is_valid():
        serializer.save(ownerId=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
