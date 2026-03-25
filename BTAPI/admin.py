from django.contrib import admin
from django.apps import apps

# Register your models here.

app_config = apps.get_app_config('BTAPI')
models = app_config.get_models()

for model in models:
    try:
        admin.site.register(model)
    except admin.sites.AlreadyRegistered:
        pass