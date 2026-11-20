from app.providers import OllamaProvider


def test_ollama_request_format(monkeypatch, settings):
    recorded = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {'message': {'content': '{"tool":"none","tool_input":""}'},
                    'prompt_eval_count': 15, 'eval_count': 5}

    def fake_post(url, json, timeout):
        recorded.update({'url': url, 'payload': json, 'timeout': timeout})
        return FakeResponse()

    monkeypatch.setattr('app.providers.httpx.post', fake_post)
    client = OllamaProvider(settings)
    reply = client.plan('Say hello', '')
    assert reply.tokens == 20
    assert recorded['url'] == 'http://localhost:11434/api/chat'
    assert recorded['payload']['format'] == 'json'
    assert recorded['payload']['stream'] is False
