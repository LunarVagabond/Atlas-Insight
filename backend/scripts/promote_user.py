import os
import sys
from pathlib import Path

import django

# Ensure backend root (parent of scripts/) is importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    django.setup()

    from django.contrib.auth import get_user_model

    email = os.environ.get("PROMOTE_EMAIL", "").strip()
    username = os.environ.get("PROMOTE_USERNAME", "").strip()

    User = get_user_model()
    user = None
    if email:
        user = User.objects.filter(email=email).first()
    if user is None and username:
        user = User.objects.filter(username=username).first()
    if user is None:
        user = User.objects.order_by("id").first()

    if user is None:
        print("No Django users found. Login via GitHub first, then rerun promote-user.")
        return

    user.is_staff = True
    user.is_superuser = True
    user.save(update_fields=["is_staff", "is_superuser"])
    print(f"Promoted Django user: {user.email or user.username or user.id}")


if __name__ == "__main__":
    main()
