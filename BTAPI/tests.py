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
