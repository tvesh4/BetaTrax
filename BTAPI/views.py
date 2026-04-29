from rest_framework.decorators import api_view, permission_classes
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .permissions import IsUser, IsDeveloper, IsOwner
from .models import *
from .serializer import *
from django.shortcuts import get_object_or_404
from .utils import *
from .metrics import classify_developer_effectiveness
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from drf_spectacular.types import OpenApiTypes

@extend_schema(
    tags=['Defect Reports'],
    summary='Submit a new defect report',
    request=DefectReportSerializer,
    responses={201: DefectReportSerializer},
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_new_report(request):
    serializer = DefectReportSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        report = serializer.save(testerId=request.user)
        if report.email:
            send_status_update_email(report)
        if report.productId.ownerId and report.productId.ownerId.email:
            send_po_update_email(report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    tags=['Defect Reports'],
    summary='List defect reports filtered by status',
    responses={200: ReportLiteSerializer(many=True)},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_reports(request, status):
    match status.upper():
        case "NEW":
            reports = DefectReport.objects.filter(status=DefectReport.Status.NEW)
        case "OPEN":
            reports = DefectReport.objects.filter(status=DefectReport.Status.OPEN)
        case "ASSIGNED":
            reports = DefectReport.objects.filter(status=DefectReport.Status.ASSIGNED)
        case "FIXED":
            reports = DefectReport.objects.filter(status=DefectReport.Status.FIXED)
        case "RESOLVED":
            reports = DefectReport.objects.filter(status=DefectReport.Status.RESOLVED)
        case "REOPENED":
            reports = DefectReport.objects.filter(status=DefectReport.Status.REOPENED)
        case "CANNOT_REPRODUCE":
            reports = DefectReport.objects.filter(status=DefectReport.Status.CANNOT_REPRODUCE)
        case "DUPLICATE":
            reports = DefectReport.objects.filter(status=DefectReport.Status.DUPLICATE)
        case "REJECTED":
            reports = DefectReport.objects.filter(status=DefectReport.Status.REJECTED)
        case "CLOSED":
            reports = DefectReport.objects.filter(status__in=[
                DefectReport.Status.CANNOT_REPRODUCE,
                DefectReport.Status.DUPLICATE,
                DefectReport.Status.REJECTED,
            ])
        case "ALL":
            reports = DefectReport.objects.all()
        case _:
            return Response({"error": f"Invalid status '{status}'"}, status=400)
    serializer = ReportLiteSerializer(reports, many=True)
    return Response(serializer.data)

@extend_schema(
    tags=['Defect Reports'],
    summary='List ASSIGNED reports for a developer',
    responses={200: ReportLiteSerializer(many=True)},
)
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

@extend_schema(
    tags=['Defect Reports'],
    summary='Get full detail of a defect report',
    responses={200: DefectReportSerializer},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_full_report(request, id):
    report = get_object_or_404(DefectReport, pk=id.title())
    serializer = DefectReportSerializer(report)
    return Response(serializer.data)

@extend_schema(
    tags=['Metrics'],
    summary='Get developer effectiveness classification',
    responses={
        200: inline_serializer(
            name='DeveloperMetricResponse',
            fields={'report': serializers.CharField()},
        ),
    },
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_developer_metric(request, id):
    developer = get_object_or_404(Developer, user__username=id.title())
    report = ''
    fixed_count = developer.fixedCount
    reopened_count = developer.reopenedCount
    ratio = 0
    if fixed_count < 20:
        report = "Insufficient data"
        return Response({
            "report": report,
            "fixedCount": developer.fixedCount,
            "reopenedCount": developer.reopenedCount,
        })  
    else:
        ratio = reopened_count / fixed_count
        if ratio < 1 / 32:
            report = "Good"
        elif ratio < 1 / 8:
            report = "Fair"
        else:
            report = "Poor"

    return Response({
        "report": report,
        "fixedCount": developer.fixedCount,
        "reopenedCount": developer.reopenedCount,
        "ratio": ratio
    })

@extend_schema(
    tags=['Defect Reports'],
    summary='Update report status, severity, priority, or duplicate parent',
    request=None,
    responses={200: DefectReportSerializer},
    parameters=[
        OpenApiParameter(
            name='status', type=OpenApiTypes.STR, required=False,
            location=OpenApiParameter.QUERY,
            description='New status (e.g. Open, Assigned, Fixed, Resolved, Reopened, Cannot Reproduce, Duplicate, Rejected). Role-enforced.',
        ),
        OpenApiParameter(
            name='severity', type=OpenApiTypes.STR, required=False,
            location=OpenApiParameter.QUERY,
            description='New severity (Low, Minor, Major, Critical). Owner-only; silently ignored if the caller is not in the Owner group.',
        ),
        OpenApiParameter(
            name='priority', type=OpenApiTypes.STR, required=False,
            location=OpenApiParameter.QUERY,
            description='New priority (Low, Medium, High, Critical). Owner-only; silently ignored if the caller is not in the Owner group.',
        ),
        OpenApiParameter(
            name='parent', type=OpenApiTypes.STR, required=False,
            location=OpenApiParameter.QUERY,
            description='Defect ID of the parent report (used when marking this report as a duplicate).',
        ),
        OpenApiParameter(
            name='dev', type=OpenApiTypes.STR, required=False,
            location=OpenApiParameter.QUERY,
            description='User PK of the developer to (re)assign this report to. Owner-only; silently ignored if the caller is not in the Owner group.',
        ),
    ],
)
@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsUser | IsOwner | IsDeveloper])
def patch_update_report(request, id):
    
    new_status = request.query_params.get('status')
    new_severity = request.query_params.get('severity')
    new_priority = request.query_params.get('priority')
    new_parent = request.query_params.get('parent')
    dev_id = request.query_params.get('dev')
    report = get_object_or_404(DefectReport, id=id.title())

    user = request.user
    is_owner = user.groups.filter(name='Owner').exists()
    is_developer = user.groups.filter(name='Developer').exists()
    status_changed = False

    if new_status and new_status.title() in DefectReport.Status:
        new_status = new_status.title()
        match report.status:
            case 'New':
                # only if role == "ProductOwner", 'Closed' = Cannot Reproduce, Duplicate, Rejected
                if is_owner and (new_status == 'Open' or new_status in ('Duplicate', 'Rejected')):
                    if new_status == 'Open':
                        report.status = new_status
                        status_changed = True
                    elif new_status == 'Rejected':
                        report.status = new_status
                        status_changed = True
                    elif new_status == 'Duplicate':
                        if report.parent:
                            report.status = new_status
                            status_changed = True
                            if report.parent.testerId.email:
                                send_duplicate_update_email(report.parent, report)
                                send_duplicate_update_email(report, report.parent)
                        if new_parent:
                            new_parent_id = get_object_or_404(DefectReport, id=new_parent.title())
                            if new_parent_id != report and new_parent_id not in report.children.all():
                                report.parent_id = new_parent_id
                                report.status = new_status
                                status_changed = True
                                if new_parent_id.testerId.email:
                                    send_duplicate_update_email(new_parent_id, report)
                                    send_duplicate_update_email(report, new_parent_id)
            case ('Open' | 'Reopened'):
                # only if role == "Developer"
                if is_developer and new_status == 'Assigned':
                    report.status = new_status
                    status_changed = True
                    report.assignedToId = user
            case 'Assigned':
                # only if role == "Developer", 'Closed' = Cannot Reproduce
                if is_developer:
                    if new_status == 'Fixed':
                        report.status = new_status
                        status_changed = True
                        request.user.developer_profile.fixedCount += 1
                        request.user.developer_profile.save()
                    elif new_status == 'Cannot Reproduce':
                        report.status = new_status
                        status_changed = True
            case 'Fixed':
                # only if role == "ProductOwner"
                if is_owner:
                    if new_status == 'Resolved': 
                        report.status = new_status
                        status_changed = True
                    elif new_status == 'Reopened':
                        report.status = new_status
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

    if dev_id and is_owner:
        report.assignedToId_id = dev_id
    if new_severity and is_owner:
        if new_severity in DefectReport.Severity:
            report.severity = new_severity
    if new_priority and is_owner:
        if new_priority in DefectReport.Priority:
            report.priority = new_priority
    report.save()
    serializer = DefectReportSerializer(report)
    return Response(serializer.data, status=status.HTTP_200_OK)

@extend_schema(
    tags=['Comments'],
    summary='Post a comment on a defect report',
    request=CommentSerializer,
    responses={201: CommentSerializer},
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsDeveloper | IsOwner])
def post_comment(request, id):
    report = get_object_or_404(DefectReport, id=id.title())
    serializer = CommentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(defectReportId=report, authorId=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    tags=['Products'],
    summary='Register a new product',
    request=ProductSerializer,
    responses={201: ProductSerializer},
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsOwner | IsDeveloper])
def post_new_product(request):
    data = request.data
    serializer = ProductSerializer(data=data)
    if serializer.is_valid():
        serializer.save(ownerId=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
