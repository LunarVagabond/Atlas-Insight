from django.conf import settings
from django.shortcuts import redirect, render


def frontend_home_redirect(_request):
    return redirect(settings.FRONTEND_URL)


def handler403(request, exception):
    return render(request, 'status/403.html', status=403)


def handler404(request, exception):
    return render(request, 'status/404.html', status=404)


def handler500(request):
    return render(request, 'status/500.html', status=500)