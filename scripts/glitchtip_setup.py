"""
Idempotent GlitchTip provisioning script.
Run inside the glitchtip-web container: python /tmp/glitchtip_setup.py <domain>

Outputs the final DSN as the last line of stdout (https://key@host/id).
Exits 0 on success, 1 if no user exists yet.
"""
import os
import sys

sys.path.insert(0, "/code")

domain = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GLITCHTIP_DOMAIN", "http://localhost:4505")
domain = domain.rstrip("/")

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "glitchtip.settings")
django.setup()

from django.contrib.auth import get_user_model
from apps.organizations_ext.models import Organization, OrganizationUser, OrganizationOwner
from apps.projects.models import Project, ProjectKey

User = get_user_model()

u = User.objects.filter(email__isnull=False).order_by("id").first()
if not u:
    print("ERROR: No GlitchTip user found. Sign in at the GlitchTip UI first.", file=sys.stderr)
    sys.exit(1)

org, _ = Organization.objects.get_or_create(name="Atlas Insight", defaults={"slug": "atlas-insight"})
ou, _ = OrganizationUser.objects.get_or_create(organization=org, user=u, defaults={"role": 3})
OrganizationOwner.objects.get_or_create(organization=org, organization_user=ou)

proj, _ = Project.objects.get_or_create(
    name="atlas-insight",
    organization=org,
    defaults={"platform": "python-django"},
)
key, _ = ProjectKey.objects.get_or_create(project=proj)

raw_dsn = key.get_dsn()
key_part = raw_dsn.split("//")[-1].split("@")[0]
proj_id = raw_dsn.rstrip("/").split("/")[-1]
scheme = "https" if domain.startswith("https") else "http"
host = domain.split("://")[-1].rstrip("/")
final_dsn = f"{scheme}://{key_part}@{host}/{proj_id}"

print(final_dsn)
