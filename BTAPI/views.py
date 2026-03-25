from rest_framework.decorators import api_view
from rest_framework import status
from rest_framework.response import Response
from .models import *
from .serializer import *
from django.shortcuts import get_object_or_404
from django.shortcuts import render

@api_view(['POST'])
def post_new_report(request): 
    tester_data = request.data.get('tester')
    defectReport_data = request.data.get('defectReport')
    
    tester_serializer = TesterSerializer(data=tester_data)
    defectReport_serializer = DefectReportSerializer(data=defectReport_data)

    if tester_serializer.is_valid() and defectReport_serializer.is_valid():
        # 1. Save the tester first to get an ID
        tester_instance = tester_serializer.save()
        
        # 2. Save the report and link it to that specific tester
        defectReport_serializer.save(tester=tester_instance)

        return Response({
            "tester": tester_serializer.data,
            "defectReport": defectReport_serializer.data
        }, status=status.HTTP_201_CREATED)

    # Combine errors from both serializers
    all_errors = {**tester_serializer.errors, **defectReport_serializer.errors}
    return Response(all_errors, status=status.HTTP_400_BAD_REQUEST)

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

