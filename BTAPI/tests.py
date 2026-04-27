from django.contrib.auth.models import Group, User
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from BTAPI.metrics import classify_developer_effectiveness
from BTAPI.models import Comment, DefectReport, Developer, Product


class ClassifierTests(SimpleTestCase):
    """Cover Sprint 3 §22-24: classify_developer_effectiveness.

    Six cases give full statement coverage and full branch coverage
    of BTAPI/metrics.py.  Boundary cases 4 and 6 pin the strict-`<`
    semantics of the thresholds and are the cases most likely to
    catch a future `<=` regression.
    """

    def test_zero_data_returns_insufficient(self):
        # fixed_count < 20 branch true (case 1)
        self.assertEqual(
            classify_developer_effectiveness(0, 0),
            "Insufficient data",
        )

    def test_just_below_threshold_returns_insufficient(self):
        # fixed_count < 20 branch true (case 2: 19 fixes is still not enough)
        self.assertEqual(
            classify_developer_effectiveness(19, 0),
            "Insufficient data",
        )

    def test_at_threshold_zero_reopened_returns_good(self):
        # fixed_count < 20 false; ratio 0 < 1/32 true (case 3)
        self.assertEqual(
            classify_developer_effectiveness(20, 0),
            "Good",
        )

    def test_ratio_exactly_one_thirty_second_returns_fair(self):
        # ratio == 1/32 -> ratio < 1/32 false; ratio < 1/8 true (case 4)
        self.assertEqual(
            classify_developer_effectiveness(32, 1),
            "Fair",
        )

    def test_ratio_between_thresholds_returns_fair(self):
        # ratio == 3/32 (0.09375) -> Fair (case 5)
        self.assertEqual(
            classify_developer_effectiveness(32, 3),
            "Fair",
        )

    def test_ratio_exactly_one_eighth_returns_poor(self):
        # ratio == 1/8 -> ratio < 1/8 false -> Poor (case 6)
        self.assertEqual(
            classify_developer_effectiveness(32, 4),
            "Poor",
        )


class EndpointSmokeTests(APITestCase):
    """Sprint 3 §38: one representative happy-path test per endpoint
    method.

    Fixture identifiers are TitleCase ('Tester', 'Dev', 'Po', 'Def001',
    'Prod001') so that endpoint-side `.title()` lookups are no-ops
    -- this sidesteps a known case-fragility bug without changing
    the views.  Tests added in subsequent tasks.
    """

    @classmethod
    def setUpTestData(cls):
        user_group = Group.objects.create(name='User')
        dev_group = Group.objects.create(name='Developer')
        owner_group = Group.objects.create(name='Owner')

        cls.tester = User.objects.create_user(
            username='Tester', password='pw', email='tester@example.com')
        cls.tester.groups.add(user_group)

        cls.dev = User.objects.create_user(
            username='Dev', password='pw', email='dev@example.com')
        cls.dev.groups.add(dev_group)

        cls.po = User.objects.create_user(
            username='Po', password='pw', email='po@example.com')
        cls.po.groups.add(owner_group)

        cls.dev_profile = Developer.objects.create(
            user=cls.dev, fixedCount=0, reopenedCount=0)

        cls.product = Product.objects.create(
            id='Prod001',
            displayName='Test Product',
            description='desc',
            currentVersion='1.0',
            isActiveBeta=True,
            ownerId=cls.po,
            devId=cls.dev,
        )

        cls.defect = DefectReport.objects.create(
            id='Def001',
            productId=cls.product,
            productVersion='1.0',
            title='Seed defect',
            description='desc',
            reproductionSteps='steps',
            testerId=cls.tester,
            status=DefectReport.Status.NEW,
            assignedToId=cls.dev,
        )

    def test_post_token_returns_access_and_refresh(self):
        """#1: POST /api/token/ — JWT obtain."""
        response = self.client.post(
            '/api/token/',
            {'username': 'Tester', 'password': 'pw'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_post_token_refresh_returns_new_access(self):
        """#2: POST /api/token/refresh/ — JWT refresh."""
        obtain = self.client.post(
            '/api/token/',
            {'username': 'Tester', 'password': 'pw'},
            format='json',
        )
        refresh_token = obtain.data['refresh']

        response = self.client.post(
            '/api/token/refresh/',
            {'refresh': refresh_token},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)

    def test_get_reports_by_status_returns_list(self):
        """#4: GET /api/reports/<status>/ — list reports filtered by status."""
        self.client.force_authenticate(user=self.tester)
        response = self.client.get('/api/reports/NEW/')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        ids = [item['id'] for item in response.data]
        self.assertIn('Def001', ids)

    def test_get_assigned_defects_returns_ok(self):
        """#5: GET /api/reports/assigned/<dev.pk>/ — developer's ASSIGNED tasks.

        The seed defect is in 'New' state (not 'Assigned'), so the endpoint
        returns the 'No assigned reports' message.  We pass dev.pk as the
        URL parameter to sidestep the known bug at views.py:55 that does
        `assignedToId=id.title()` against an FK column.
        """
        self.client.force_authenticate(user=self.dev)
        response = self.client.get(f'/api/reports/assigned/{self.dev.pk}/')
        self.assertEqual(response.status_code, 200)

    def test_get_full_report_returns_defect(self):
        """#6: GET /api/defect/<id>/ — full defect detail.

        Lowercase URL parameter ('def001') deliberately exercises the
        existing `.title()` lookup convention.
        """
        self.client.force_authenticate(user=self.tester)
        response = self.client.get('/api/defect/def001/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], 'Def001')

    def test_get_developer_metric_returns_classification(self):
        """#10: GET /api/metric/<id>/ — developer effectiveness classification.

        URL parameter is the developer's username verbatim.  fixedCount
        is 0 so the classifier returns 'Insufficient data'.
        """
        self.client.force_authenticate(user=self.dev)
        response = self.client.get('/api/metric/Dev/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['report'], 'Insufficient data')

    def test_post_new_report_creates_defect(self):
        """#3: POST /api/defect/ — submit a new defect report."""
        self.client.force_authenticate(user=self.tester)
        response = self.client.post(
            '/api/defect/',
            {
                'id': 'Def002',
                'productId': 'Prod001',
                'productVersion': '1.0',
                'title': 'Crashes on startup',
                'description': 'App quits immediately.',
                'reproductionSteps': '1. Open app',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'New')

    def test_patch_update_report_new_to_open(self):
        """#7: PATCH /api/update/<id>/?status=Open — owner moves New -> Open.

        Simplest workflow transition; avoids the duplicate-link branches
        and the raw-vs-titled comparison bug at views.py:101.
        """
        self.client.force_authenticate(user=self.po)
        response = self.client.patch('/api/update/def001/?status=Open')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'Open')

    def test_post_comment_creates_comment(self):
        """#8: POST /api/comment/<id>/ — post a comment on a defect.

        Comment.id is a manually-assigned CharField, so the body must
        include a unique 'id' value.
        """
        self.client.force_authenticate(user=self.tester)
        response = self.client.post(
            '/api/comment/def001/',
            {'id': 'Com001', 'content': 'I see this too.'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['content'], 'I see this too.')

    def test_post_new_product_creates_product(self):
        """#9: POST /api/product/ — register a new product."""
        self.client.force_authenticate(user=self.po)
        response = self.client.post(
            '/api/product/',
            {
                'id': 'Prod002',
                'displayName': 'BetaTrax Mobile',
                'description': 'Mobile companion app.',
                'currentVersion': '0.1',
                'isActiveBeta': True,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['id'], 'Prod002')
