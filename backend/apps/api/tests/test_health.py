import pytest
from django.test import Client


@pytest.mark.django_db
class TestHealthEndpoint:
    def test_returns_200(self):
        client = Client()
        response = client.get('/api/v1/health')
        assert response.status_code == 200

    def test_returns_ok_status(self):
        client = Client()
        response = client.get('/api/v1/health')
        data = response.json()
        assert data['status'] == 'ok'

    def test_returns_service_name(self):
        client = Client()
        response = client.get('/api/v1/health')
        data = response.json()
        assert 'service' in data
        assert 'Atlas Insight' in data['service']
