"""Bootstrap tenants for the BetaTrax Final Review.

Spec source: BetaTrax_Final_Demo_Setup.pdf.  Two demo tenants in
addition to the public tenant: SE Tenant 1 (schema=se1) and SE
Tenant 2 (schema=se2), each populated with the users, product,
defect report, comments and developer-metric values prescribed by
the spec.

Idempotent: re-running is safe.  On first run after the rename
from acme/globex, drops the obsolete schemas as well.
"""

from datetime import datetime, timezone

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import connection
from django_tenants.utils import tenant_context

from BTAPI.models import Client, Comment, DefectReport, Developer, Domain, Product


OBSOLETE_SCHEMAS = ['acme', 'globex']


SE1_CONFIG = {
    'users': [
        {'username': 'user_1', 'group': 'Owner'},
        {'username': 'user_2', 'group': 'Developer',
         'developer_profile': {'fixedCount': 0, 'reopenedCount': 0}},
        {'username': 'user_3', 'group': 'User'},
        {'username': 'user_4', 'group': 'User'},
        {'username': 'user_5', 'group': 'User'},
        {'username': 'Tester_1', 'group': 'User',
         'email': 'icyreward@gmail.com'},
    ],
    'product': {
        'id': 'prod_1',
        'displayName': 'SE Tenant 1 Product',
        'description': 'Product under beta test for SE Tenant 1.',
        'currentVersion': '0.9.0',
        'isActiveBeta': True,
        'owner': 'user_1',
        'developer': 'user_2',
    },
    'defects': [
        {
            'id': 'Dr1',
            'productVersion': '0.9.0',
            'title': 'Unable to search',
            'description': 'Search button unresponsive after completing an initial search',
            'reproductionSteps': (
                '1. Complete a search\n'
                '2. Modify search criteria\n'
                '3. Click Search button'
            ),
            'tester': 'Tester_1',
            'status': DefectReport.Status.ASSIGNED,
            'severity': DefectReport.Severity.MAJOR,
            'priority': DefectReport.Priority.HIGH,
            'assignedTo': 'user_2',
            'submittedAt': datetime(2026, 3, 25, 10, 53, tzinfo=timezone.utc),
            'comments': [],
        },
    ],
}


SE2_CONFIG = {
    'users': [
        {'username': 'user_6', 'group': 'Owner'},
        {'username': 'user_7', 'group': 'Developer',
         'developer_profile': {'fixedCount': 8, 'reopenedCount': 1}},
        {'username': 'user_8', 'group': 'Developer',
         'developer_profile': {'fixedCount': 0, 'reopenedCount': 0}},
        {'username': 'Tester_1', 'group': 'User',
         'email': 'icyreward@gmail.com'},
    ],
    'product': {
        'id': 'prod_1',
        'displayName': 'SE Tenant 2 Product',
        'description': 'Product under beta test for SE Tenant 2.',
        'currentVersion': '0.9.0',
        'isActiveBeta': True,
        'owner': 'user_6',
        # Product.devId is a single FK — user_8 is a Developer in the
        # tenant but is not the FK-linked dev of prod_1.  Documented
        # limitation in CLAUDE.md (Known Limitations).
        'developer': 'user_7',
    },
    'defects': [
        {
            'id': 'Dr1',
            'productVersion': '0.9.0',
            'title': 'Hit count incorrect',
            'description': (
                'Following a successful search, the hit count is different to the '
                'number of matches displayed.'
            ),
            'reproductionSteps': (
                '1. Enter search criteria that ensure at least one match\n'
                '2. Search\n'
                '3. Compare matches displayed with the number of hits reported.'
            ),
            'tester': 'Tester_1',
            'status': DefectReport.Status.ASSIGNED,
            'severity': DefectReport.Severity.MINOR,
            'priority': DefectReport.Priority.HIGH,
            'assignedTo': 'user_7',
            'submittedAt': datetime(2026, 4, 27, 15, 37, tzinfo=timezone.utc),
            'comments': [
                {
                    'id': 'Cmt1',
                    'author': 'user_7',
                    'content': 'Comment added by developer',
                    'createdAt': datetime(2026, 4, 26, 20, 49, tzinfo=timezone.utc),
                },
                {
                    'id': 'Cmt2',
                    'author': 'user_6',
                    'content': 'Comment added by product owner',
                    'createdAt': datetime(2026, 4, 26, 23, 27, tzinfo=timezone.utc),
                },
            ],
        },
    ],
}


TENANTS = [
    {
        'schema_name': 'public',
        'name': 'Public',
        'domain': 'localhost',
        'config': None,
    },
    {
        'schema_name': 'se1',
        'name': 'SE Tenant 1',
        'domain': 'se1.localhost',
        'config': SE1_CONFIG,
    },
    {
        'schema_name': 'se2',
        'name': 'SE Tenant 2',
        'domain': 'se2.localhost',
        'config': SE2_CONFIG,
    },
]


class Command(BaseCommand):
    help = (
        "Bootstrap the public tenant plus the two SE Tenants required "
        "by the Final Review setup spec.  Idempotent."
    )

    def handle(self, *args, **options):
        self._cleanup_obsolete()
        for cfg in TENANTS:
            client = self._get_or_create_tenant(cfg)
            self._get_or_create_domain(cfg, client)
            if cfg['config']:
                self._populate(client, cfg['config'])
        self.stdout.write(self.style.SUCCESS('Bootstrap complete.'))

    def _cleanup_obsolete(self):
        for schema in OBSOLETE_SCHEMAS:
            client = Client.objects.filter(schema_name=schema).first()
            if client is None:
                with connection.cursor() as cur:
                    cur.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
                continue
            Domain.objects.filter(tenant=client).delete()
            client.delete()
            with connection.cursor() as cur:
                cur.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
            self.stdout.write(f"Removed obsolete tenant + schema '{schema}'")

    def _get_or_create_tenant(self, cfg):
        client, created = Client.objects.get_or_create(
            schema_name=cfg['schema_name'],
            defaults={'name': cfg['name']},
        )
        action = 'Creating' if created else 'Skipping (exists)'
        self.stdout.write(
            f"{action} tenant '{cfg['name']}' "
            f"(schema={cfg['schema_name']}, domain={cfg['domain']})"
        )
        return client

    def _get_or_create_domain(self, cfg, client):
        Domain.objects.get_or_create(
            domain=cfg['domain'],
            defaults={'tenant': client, 'is_primary': True},
        )

    def _populate(self, client, config):
        with tenant_context(client):
            groups = self._ensure_groups()
            if DefectReport.objects.exists():
                self.stdout.write(
                    f"  Sample data already exists in {client.schema_name}, skipping"
                )
                return

            users = self._create_users(config['users'], groups)
            product = self._create_product(config['product'], users)
            for defect_cfg in config['defects']:
                self._create_defect(defect_cfg, product, users)

            self.stdout.write(
                f"  Populated {client.schema_name}: "
                f"{len(users)} users, product '{product.id}', "
                f"{len(config['defects'])} defect(s)"
            )

    def _ensure_groups(self):
        return {
            name: Group.objects.get_or_create(name=name)[0]
            for name in ('User', 'Developer', 'Owner')
        }

    def _create_users(self, user_cfgs, groups):
        users = {}
        for cfg in user_cfgs:
            user = User.objects.create_user(
                username=cfg['username'],
                password='pw',
                email=cfg.get('email', ''),
            )
            user.groups.add(groups[cfg['group']])
            if 'developer_profile' in cfg:
                Developer.objects.create(
                    user=user,
                    fixedCount=cfg['developer_profile']['fixedCount'],
                    reopenedCount=cfg['developer_profile']['reopenedCount'],
                )
            users[cfg['username']] = user
        return users

    def _create_product(self, cfg, users):
        return Product.objects.create(
            id=cfg['id'],
            displayName=cfg['displayName'],
            description=cfg['description'],
            currentVersion=cfg['currentVersion'],
            isActiveBeta=cfg['isActiveBeta'],
            ownerId=users[cfg['owner']],
            devId=users[cfg['developer']],
        )

    def _create_defect(self, cfg, product, users):
        defect = DefectReport.objects.create(
            id=cfg['id'],
            productId=product,
            productVersion=cfg['productVersion'],
            title=cfg['title'],
            description=cfg['description'],
            reproductionSteps=cfg['reproductionSteps'],
            testerId=users[cfg['tester']],
            status=cfg['status'],
            severity=cfg['severity'],
            priority=cfg['priority'],
            assignedToId=users[cfg['assignedTo']],
        )
        # auto_now_add ignores explicit values at create() time; backdate
        # via .update() so the spec timestamp is what the API returns.
        DefectReport.objects.filter(pk=defect.pk).update(
            submittedAt=cfg['submittedAt']
        )

        for cmt_cfg in cfg.get('comments', []):
            comment = Comment.objects.create(
                id=cmt_cfg['id'],
                content=cmt_cfg['content'],
                defectReportId=defect,
                authorId=users[cmt_cfg['author']],
            )
            Comment.objects.filter(pk=comment.pk).update(
                createdAt=cmt_cfg['createdAt']
            )
