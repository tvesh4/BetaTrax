from .settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
DATABASE_ROUTERS = ()
INSTALLED_APPS = [a for a in INSTALLED_APPS if a != 'django_tenants']
MIDDLEWARE = [m for m in MIDDLEWARE if 'django_tenants' not in m]
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
