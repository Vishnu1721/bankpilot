"""CLI wiring tests use fakes explicitly; live replay runs separately in CI."""
from unittest.mock import Mock

import pytest

import main as cli
from src.capability.results import ReplayResult, ReplayStatus
from src.handoff.manager import HumanHandoffManager, HandoffCancelled
from tests.test_headless_replay import build_parser, verify_result


@pytest.mark.parametrize('member_id', ['10023', '10024', 'reviewer-custom-id'])
def test_discovery_forwards_reviewer_goal_target_and_parameters(monkeypatch, tmp_path, member_id):
    surface = Mock()
    monkeypatch.setattr(cli, 'BrowserSurface', Mock(return_value=Mock(start=Mock(return_value=surface))))
    artifact = tmp_path / 'flow.json'
    agent = Mock()

    def run(**kwargs):
        artifact.write_text('{}')  # Fake artifact: only CLI wiring is under test.
        assert kwargs['goal'] == f'Look up {member_id}'
        assert kwargs['parameters'] == {'member_id': member_id}
        return {'savings_balance': 'test-value'}

    agent.run.side_effect = run
    monkeypatch.setattr(cli, 'DiscoveryAgent', Mock(return_value=agent))
    assert cli.main(['discover', '--target', 'http://localhost:5001/',
                     '--goal', f'Look up {member_id}', '--artifact', str(artifact),
                     '--param', f'member_id={member_id}']) == 0
    surface.navigate.assert_called_once_with('http://localhost:5001/')
    surface.close.assert_called_once()


@pytest.mark.parametrize('status,exit_code', [(ReplayStatus.SUCCESS, 0),
    (ReplayStatus.BUSINESS_OUTCOME, 0), (ReplayStatus.FAILURE, 1)])
def test_replay_cli_exit_status_and_no_discovery(monkeypatch, tmp_path, status, exit_code):
    artifact = tmp_path / 'flow.json'
    artifact.write_text('{}')
    surface = Mock()
    monkeypatch.setattr(cli, 'BrowserSurface', Mock(return_value=Mock(start=Mock(return_value=surface))))
    discovery = Mock(side_effect=AssertionError('Replay must not construct discovery'))
    monkeypatch.setattr(cli, 'DiscoveryAgent', discovery)
    engine = Mock()
    engine.run.return_value = ReplayResult(status=status, outputs={}, message='test')
    monkeypatch.setattr(cli, 'ReplayEngine', Mock(return_value=engine))
    assert cli.main(['replay', '--artifact', str(artifact), '--param', 'member_id=custom']) == exit_code
    assert engine.run.call_args.args[1] == {'member_id': 'custom'}
    discovery.assert_not_called()
    surface.close.assert_called_once()


@pytest.mark.parametrize('field,bad_value', [('status', ReplayStatus.FAILURE),
    ('outputs', {'answer': 'wrong'}), ('code', 'UNEXPECTED')])
def test_reviewer_checker_rejects_wrong_results(field, bad_value):
    args = build_parser().parse_args(['--artifact', 'custom.json', '--param', 'id=42',
        '--expect-status', 'success', '--expect-output', 'answer=expected'])
    data = dict(status=ReplayStatus.SUCCESS, outputs={'answer': 'expected'}, code=None, message='test')
    verify_result(ReplayResult(**data), args)
    data[field] = bad_value
    with pytest.raises(AssertionError):
        verify_result(ReplayResult(**data), args)


def test_operator_can_cancel_without_resuming(monkeypatch):
    surface = Mock()
    surface.page.url = 'http://localhost:5001/'
    manager = HumanHandoffManager(surface)
    monkeypatch.setattr(manager, '_state_fingerprint', lambda: 'unchanged')
    monkeypatch.setattr('builtins.input', lambda _: '/cancel')
    with pytest.raises(HandoffCancelled):
        manager.handoff('Untrusted UI detected')


def test_headless_handoff_rejected_before_browser_start(monkeypatch):
    browser = Mock()
    monkeypatch.setattr(cli, 'BrowserSurface', browser)
    with pytest.raises(SystemExit):
        cli.main(['replay', '--artifact', 'any.json', '--headless', '--enable-handoff'])
    browser.assert_not_called()
