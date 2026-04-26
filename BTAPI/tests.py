from django.test import TestCase

# Create your tests here.

#adding test case to test
from .models import ProductOwner, Developer, Product, DefectReport

class DefectReportTestCase(TestCase):
    def setUp(self):
        # Create required related objects for the test
        self.product_owner = ProductOwner.objects.create(
            id='PO001',
            fullName='John Doe',
            email='john@example.com',
            username='johndoe',
            isActive=True
        )
        self.developer = Developer.objects.create(
            id='DEV001',
            fullName='Jane Smith',
            email='jane@example.com',
            username='janesmith',
            isActive=True
        )
        self.product = Product.objects.create(
            id='PROD001',
            displayName='Test Product',
            description='A test product',
            currentVersion='1.0.0',
            isActiveBeta=True,
            ownerId=self.product_owner,
            devId=self.developer
        )

    def test_defect_report_creation(self):
        # Create a DefectReport instance
        defect = DefectReport.objects.create(
            id='DEF001',
            productId=self.product,
            productVersion='1.0.0',
            title='Test Defect',
            description='This is a test defect report',
            reproductionSteps='Step 1: Do something\nStep 2: See error',
            testerId='TESTER001',
            testerEmail='tester@example.com',
            status=DefectReport.Status.NEW,
            severity=DefectReport.Severity.MAJOR,
            priority=DefectReport.Priority.HIGH,
            assignedToId=self.developer
        )
        
        # Assertions to verify the object was created correctly
        self.assertEqual(defect.title, 'Test Defect')
        self.assertEqual(defect.status, DefectReport.Status.NEW)
        self.assertEqual(defect.productId, self.product)
        self.assertEqual(defect.assignedToId, self.developer)
        self.assertIsNotNone(defect.submittedAt)  # Auto-generated timestamp
        self.assertEqual(str(defect), 'DEF001')  # __str__ method