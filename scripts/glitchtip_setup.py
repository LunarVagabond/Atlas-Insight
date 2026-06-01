"""Idempotent GlitchTip provisioning script.

Run inside the glitchtip-web container:
    python /tmp/glitchtip_setup.py <domain>

Behavior:
- Creates/updates Atlas Insight org.
- Creates/updates GitHub OAuth SocialApp and org association when env vars exist.
- Creates/updates one or more projects and project keys.
- Promotes first local user to org owner/superuser if a user exists.
- Prints DSN for primary project as last stdout line.
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
from allauth.socialaccount.models import SocialApp
from apps.organizations_ext.models import (
    Organization,
    OrganizationOwner,
    OrganizationSocialApp,
    OrganizationUser,
)
from apps.projects.models import Project, ProjectKey

User = get_user_model()

org, _ = Organization.objects.get_or_create(name="Atlas Insight", defaults={"slug": "atlas-insight"})

# Optional GitHub social login app wiring for this organization.
github_client_id = os.environ.get("GITHUB_CLIENT_ID", "").strip()
github_secret = os.environ.get("GITHUB_SECRET", "").strip()
if github_client_id and github_secret:
    social_app, _ = SocialApp.objects.get_or_create(
        provider="github",
        provider_id="github",
        defaults={
            "name": "GitHub",
            "client_id": github_client_id,
            "secret": github_secret,
            "key": "",
            "settings": {},
        },
    )
    social_app.name = "GitHub"
    social_app.client_id = github_client_id
    social_app.secret = github_secret
    social_app.key = ""
    social_app.provider = "github"
    social_app.provider_id = "github"
    social_app.save()
    OrganizationSocialApp.objects.get_or_create(organization=org, social_app=social_app)

# Promote first available user when one exists.
u = User.objects.filter(email__isnull=False).order_by("id").first() or User.objects.order_by("id").first()
if u:
    u.is_staff = True
    u.is_superuser = True
    u.save(update_fields=["is_staff", "is_superuser"])
    ou, _ = OrganizationUser.objects.get_or_create(organization=org, user=u, defaults={"role": 3})
    if ou.role != 3:
        ou.role = 3
        ou.save(update_fields=["role"])
    OrganizationOwner.objects.get_or_create(organization=org, organization_user=ou)

projects_raw = os.environ.get(
    "GLITCHTIP_PROJECTS",
    "Backend,Frontend",
)
project_names = [p.strip() for p in projects_raw.split(",") if p.strip()]
primary_project_name = os.environ.get("GLITCHTIP_PRIMARY_PROJECT", "Backend").strip() or "Backend"

def _guess_platform(name: str) -> str:
    if name.startswith("django"):
        return "python-django"
    if name.startswith("celery"):
        return "python"
    if "frontend" in name or "vue" in name:
        return "javascript-vue"
    return "python"

primary_key = None
for name in project_names:
    proj, _ = Project.objects.get_or_create(
        name=name,
        organization=org,
        defaults={"platform": _guess_platform(name)},
    )
    key, _ = ProjectKey.objects.get_or_create(project=proj)
    if name == primary_project_name:
        primary_key = key

if primary_key is None:
    proj, _ = Project.objects.get_or_create(
        name=primary_project_name,
        organization=org,
        defaults={"platform": _guess_platform(primary_project_name)},
    )
    primary_key, _ = ProjectKey.objects.get_or_create(project=proj)

raw_dsn = primary_key.get_dsn()
key_part = raw_dsn.split("//")[-1].split("@")[0]
proj_id = raw_dsn.rstrip("/").split("/")[-1]
scheme = "https" if domain.startswith("https") else "http"
host = domain.split("://")[-1].rstrip("/")
final_dsn = f"{scheme}://{key_part}@{host}/{proj_id}"

if u:
    print(f"INFO: owner user = {u.email or u.username or u.id}")
else:
    print("INFO: no user yet; sign in to GlitchTip when ready")
print(f"INFO: org = {org.slug}")
print(f"INFO: projects = {', '.join(project_names)}")

print(final_dsn)
