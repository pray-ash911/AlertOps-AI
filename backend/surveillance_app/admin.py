# admin.py - SIMPLE VERSION
from django.contrib import admin
from .models import *

# Register all models at once
admin.site.register(EventType)
admin.site.register(SurveillanceArea)
admin.site.register(EventLog)
admin.site.register(EventEvidence)

# Register new lift models
admin.site.register(Lift)
admin.site.register(LiftUsage)
admin.site.register(LiftDetection)