from fastapi.testclient import TestClient

from services.job_api.app.main import app


def test_dashboard_page_loads() -> None:
    client = TestClient(app)
    html_response = client.get('/dashboard')
    assert html_response.status_code == 200
    assert 'CronasFastAPI' in html_response.text
