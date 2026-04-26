from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django_tenants.utils import tenant_context

from BTAPI.models import Client, DefectReport, Developer, Domain, Product


TENANTS = [
    {
        'schema_name': 'public',
        'name': 'Public',
        'domain': 'localhost',
        'sample_data': False,
    },
    {
        'schema_name': 'acme',
        'name': 'ACME Corp',
        'domain': 'acme.localhost',
        'sample_data': True,
        'prefix': 'Acme',
    },
    {
        'schema_name': 'globex',
        'name': 'Globex',
        'domain': 'globex.localhost',
        'sample_data': True,
        'prefix': 'Globex',
    },
]


class Command(BaseCommand):
    help = (
        "Bootstrap the public tenant plus two demo tenants (ACME, Globex) "
        "with isolated sample data.  Idempotent: safe to re-run."
    )

    def handle(self, *args, **options):
        for cfg in TENANTS:
            client = self._get_or_create_tenant(cfg)
            self._get_or_create_domain(cfg, client)
            if cfg['sample_data']:
                self._populate_sample_data(client, cfg['prefix'])
        self.stdout.write(self.style.SUCCESS('Bootstrap complete.'))

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

    def _populate_sample_data(self, client, prefix):
        with tenant_context(client):
            user_group, _ = Group.objects.get_or_create(name='User')
            dev_group, _ = Group.objects.get_or_create(name='Developer')
            owner_group, _ = Group.objects.get_or_create(name='Owner')

            if DefectReport.objects.exists():
                self.stdout.write(
                    f"  Sample data already exists in {prefix}, skipping"
                )
                return

            po = User.objects.create_user(
                username=f'{prefix}Po', password='pw',
                email=f'po@{prefix.lower()}.example.com',
            )
            po.groups.add(owner_group)

            dev = User.objects.create_user(
                username=f'{prefix}Dev', password='pw',
                email=f'dev@{prefix.lower()}.example.com',
            )
            dev.groups.add(dev_group)

            tester = User.objects.create_user(
                username=f'{prefix}Tester', password='pw',
                email=f'tester@{prefix.lower()}.example.com',
            )
            tester.groups.add(user_group)

            Developer.objects.create(
                user=dev, fixedCount=0, reopenedCount=0,
            )

            product = Product.objects.create(
                id=f'{prefix}Prod1',
                displayName=f'{prefix} Demo Product',
                description=f'{prefix} demo description',
                currentVersion='1.0',
                isActiveBeta=True,
                ownerId=po,
                devId=dev,
            )

            DefectReport.objects.create(
                id=f'{prefix}Def1',
                productId=product,
                productVersion='1.0',
                title=f'{prefix} sample defect',
                description='Sample defect for demo.',
                reproductionSteps='1. Open app  2. See bug',
                testerId=tester,
                status=DefectReport.Status.NEW,
                assignedToId=dev,
            )

            self.stdout.write(
                f"  Created users: {prefix}Po, {prefix}Dev, {prefix}Tester"
            )
            self.stdout.write(
                f"  Created product '{prefix}Prod1' and defect '{prefix}Def1'"
            )
