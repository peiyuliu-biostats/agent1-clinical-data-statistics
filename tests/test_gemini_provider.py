import json

from clinical_stat_agent.agent import _gemini_answer


class FakeResponse:
    status_code = 200

    def json(self):
        answer = {
            "answer": "Structured Gemini response",
            "project_definition": "",
            "general_definition": "",
            "disease_context": "",
            "statistical_impact": "",
            "data_impact": "",
            "citations": [],
            "uncertainties": [],
            "questions_for_review": [],
            "confidence": "medium",
        }
        return {"candidates": [{"content": {"parts": [{"text": json.dumps(answer)}]}}]}


class FakeClient:
    last_request = None

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, headers, json):
        FakeClient.last_request = {"url": url, "headers": headers, "json": json}
        return FakeResponse()

    def get(self, url, headers=None, params=None):
        return FakeResponse()


def test_gemini_uses_structured_generate_content(monkeypatch):
    monkeypatch.setattr("clinical_stat_agent.agent.httpx.Client", FakeClient)
    monkeypatch.setattr("clinical_stat_agent.agent.settings", type("S", (), {"gemini_api_key": "fake", "gemini_model": "gemini-2.5-flash"})())
    answer = _gemini_answer("test prompt")
    assert answer.answer == "Structured Gemini response"
    request = FakeClient.last_request
    assert ":generateContent" in request["url"]
    assert request["json"]["generationConfig"]["responseMimeType"] == "application/json"
    assert request["json"]["generationConfig"]["responseJsonSchema"]["title"] == "EvidenceAnswer"
