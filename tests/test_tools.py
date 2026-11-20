import json
import pytest
from app.tools import calculate, Tools, ToolError


@pytest.mark.parametrize(('expression', 'result'), [
    ('(18 + 6) * 3', '72'),
    ('25 * 4 + 12', '112'),
    ('(7 + 5) / 4', '3'),
    ('-8 / 2', '-4'),
    ('1.5 + 2.5', '4'),
])
def test_arithmetic(expression, result):
    assert calculate(expression) == result


@pytest.mark.parametrize('expression', [
    "__import__('os').system('whoami')", '2 ** 10000', '5 / 0',
    '[1,2]', '1e999', '', '1 << 9',
])
def test_calculator_rejects_unsafe_or_invalid_input(expression):
    with pytest.raises(ToolError):
        calculate(expression)


def test_note_lookup(settings):
    tools = Tools(settings.notes_path)
    result = json.loads(tools.execute('note_search', 'which database stores run history?'))
    assert result['matches'][0]['id'] == 'database'
    assert json.loads(tools.execute('note_search', 'flibbertigibbet quokka')) == {'matches': []}


def test_unknown_tool(settings):
    with pytest.raises(ToolError):
        Tools(settings.notes_path).execute('shell', 'ls')
