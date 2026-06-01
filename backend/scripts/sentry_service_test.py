import django
import logging
import sentry_sdk


def main() -> None:
    django.setup()

    marker = "SENTRY_SERVICE_TEST"
    bucket_loggers = {
        "django-analysis": "apps.analysis.tasks",
        "django-api": "apps.api.router",
        "django-repositories": "apps.repositories.router",
        "django-users": "apps.users.middleware",
        "django-utils": "apps.utils.flags",
        "django-config": "config.urls",
        "django": "django.request",
        "celery-workers": "celery.worker",
        "celery-flower": "flower.events",
    }

    for bucket, logger_name in bucket_loggers.items():
        level = logging.ERROR if logger_name == "django.request" else logging.INFO
        logging.getLogger(logger_name).log(
            level,
            "%s bucket=%s logger=%s",
            marker,
            bucket,
            logger_name,
            extra={"service": bucket},
        )

    sentry_sdk.flush(timeout=10)
    print(f"Sent service test logs: {len(bucket_loggers)}")
    print(f"Marker: {marker}")


if __name__ == "__main__":
    main()
