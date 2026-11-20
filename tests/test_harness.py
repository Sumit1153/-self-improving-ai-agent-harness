from app.harness import AgentHarness
from app.providers import LLMReply
from app.schemas import RunRequest
from app.storage import RunStore
from app.tools import Tools


def test_demo_calculator_and_persistence(harness, settings):
    result = harness.run(RunRequest(task='Calculate (18 + 6) * 3', expected_answer='72', match_type='numeric'))
    assert result.success
    assert result.answer == '72'
    assert result.attempts[0].plan.tool == 'calculator'
    assert result.total_tokens == 0  # Demo is explicitly not an LLM.
    assert RunStore(settings.database_path).get(result.run_id)['answer'] == '72'
    assert len(RunStore(settings.database_path).recent()) == 1


def test_demo_note_search(harness):
    result = harness.run(RunRequest(task='What database stores run history and evaluation attempts?',
                                    expected_answer='SQLite', match_type='contains'))
    assert result.success
    assert 'SQLite' in result.answer


class FlakyProvider:
    def __init__(self):
        self.calls = 0

    def plan(self, task, feedback):
        return LLMReply('{"tool":"calculator","tool_input":"(18+6)*3"}', tokens=11)

    def answer(self, task, tool_name, tool_output, feedback):
        self.calls += 1
        return LLMReply('0' if self.calls == 1 else tool_output, tokens=7)

    def direct(self, task):
        return LLMReply('0', tokens=10)


def test_feedback_driven_retry(settings):
    fake = FlakyProvider()
    harness = AgentHarness(fake, Tools(settings.notes_path), RunStore(settings.database_path),
                           'ollama', 'fake-llm-for-test')
    result = harness.run(RunRequest(task='Calculate (18+6)*3', expected_answer='72', match_type='numeric'))
    assert result.success
    assert len(result.attempts) == 2
    assert not result.attempts[0].passed
    assert result.attempts[1].passed
    assert result.total_tokens == 36


class BadPlanThenGood(FlakyProvider):
    def plan(self, task, feedback):
        self.calls += 1
        if self.calls == 1:
            return LLMReply('{"tool":"shell","tool_input":"rm -rf /"}')
        return LLMReply('{"tool":"calculator","tool_input":"1+1"}')

    def answer(self, task, tool_name, tool_output, feedback):
        return LLMReply(tool_output)


def test_invalid_plan_can_recover(settings):
    harness = AgentHarness(BadPlanThenGood(), Tools(settings.notes_path),
                           RunStore(settings.database_path), 'ollama', 'fake')
    result = harness.run(RunRequest(task='Calculate 1+1', expected_answer='2', match_type='numeric'))
    assert result.success and len(result.attempts) == 2
    assert result.attempts[0].plan is None


def test_no_expected_is_only_structural(harness):
    result = harness.run(RunRequest(task='Calculate 2 + 3'))
    assert result.success
    assert 'NOT verified' in result.attempts[-1].feedback


def test_retry_is_bounded(harness):
    result = harness.run(RunRequest(task='Calculate 2 + 3', expected_answer='999', match_type='numeric', max_attempts=2))
    assert not result.success and len(result.attempts) == 2
