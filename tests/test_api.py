from fastapi.testclient import TestClient
from app.main import create_app


def test_health_and_home(settings):
    with TestClient(create_app(settings)) as client:
        assert client.get('/health').json()['provider'] == 'demo'
        assert 'AgentLab' in client.get('/').text
        assert client.get('/static/app.js').status_code == 200


def test_run_and_history(settings):
    with TestClient(create_app(settings)) as client:
        response = client.post('/agent/run', json={
            'task': 'Calculate 25 * 4 + 12', 'expected_answer': '112', 'match_type': 'numeric'
        })
        assert response.status_code == 200
        run = response.json()
        assert run['success']
        assert run['answer'] == '112'
        assert client.get('/runs/' + run['run_id']).json()['answer'] == '112'
        assert len(client.get('/runs').json()) == 1
        assert client.get('/runs/nonexistent').status_code == 404


def test_invalid_payload(settings):
    with TestClient(create_app(settings)) as client:
        assert client.post('/agent/run', json={'task': 'Hi'}).status_code == 422
        assert client.post('/agent/run', json={'task': 'Calculate 2 + 2', 'max_attempts': 100}).status_code == 422


def test_benchmark(settings):
    with TestClient(create_app(settings)) as client:
        response = client.post('/benchmark/run', json={'limit': 6, 'max_attempts': 2})
        assert response.status_code == 200, response.text
        report = response.json()
        assert report['count'] == 6
        assert report['harness_success_rate'] == 100.0
        assert report['baseline_success_rate'] == 0.0
        assert len(client.get('/runs').json()) == 6
