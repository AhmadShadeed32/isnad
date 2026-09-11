"""The recording identity survives packaging but detects runtime code changes."""
import json
import shutil

from demo.lab import runner


def test_committed_recordings_match_current_runtime():
    """Fail release validation when implementation changes outlive the recordings."""
    bundle = json.loads(
        (runner.REPO_ROOT / 'demo/lab/artifacts/bundle.json').read_text()
    )
    revision, dirty = runner._code_revision()
    policy = runner._policy_digest()
    assert not dirty, 'Runtime source identity is unavailable'
    recordings = [bundle, *(case['run'] for case in bundle['cases'])]
    for recording in recordings:
        assert recording['code_revision'] == revision, (
            'Lab recordings are stale; run scripts/build_lab_artifacts.py'
        )
        assert recording['policy_digest'] == policy
        assert recording['dirty'] is False


def test_container_sources_match_checkout_without_git(monkeypatch, tmp_path):
    original = runner._code_revision()
    assert original[0].startswith('sha256:') and not original[1]
    for folder in ('app', 'demo/lab'):
        shutil.copytree(runner.REPO_ROOT / folder, tmp_path / folder,
                        ignore=shutil.ignore_patterns('__pycache__', 'artifacts'))
    monkeypatch.setattr(runner, 'REPO_ROOT', tmp_path)
    assert runner._code_revision() == original
    # Writing the bundle cannot invalidate its own identity.
    artifacts = tmp_path / 'demo/lab/artifacts'
    artifacts.mkdir()
    (artifacts / 'bundle.json').write_text('{"recorded": true}')
    assert runner._code_revision() == original
    source = tmp_path / 'app/agent/planner.py'
    source.write_text(source.read_text() + '\n# changed implementation\n')
    assert runner._code_revision()[0] != original[0]


def test_missing_runtime_tree_cannot_claim_identity(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, 'REPO_ROOT', tmp_path)
    assert runner._code_revision() == ('unknown', True)
