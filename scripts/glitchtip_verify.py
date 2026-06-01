import os
import sys

sys.path.insert(0, "/code")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "glitchtip.settings")

import django

django.setup()

from django.db.models import Count
from apps.logs.models import LogEvent
from apps.organizations_ext.models import Organization
from apps.projects.models import Project

org = Organization.objects.get(slug="atlas-insight")
projects = sorted(Project.objects.filter(organization=org).values_list("name", flat=True))
print(f"projects: {projects}")

backend = Project.objects.get(organization=org, name="Backend")
service_counts = (
    LogEvent.objects.filter(organization=org, project=backend)
    .exclude(service="")
    .values("service")
    .annotate(count=Count("id"))
    .order_by("service")
)

print("backend_log_services:")
for row in service_counts:
    print(f"- {row['service']}: {row['count']}")
