"""Whole-file recorded replay over real HTTP/WS with disposable services/state."""
import importlib.util
from pathlib import Path


def test_mac_recorded_metadata_network_integration():
    path = Path(__file__).resolve().parents[1] / 'scripts/mac/recorded_e2e.py'
    spec = importlib.util.spec_from_file_location('sentinel_mac_e2e', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.run()
    assert result['status'] == 'PASS'
    assert result['websocket_frames'] == 254
    assert result['suppressed_holds'] == 43


def test_mac_replay_rejects_modified_metadata_before_launch(tmp_path, monkeypatch):
    import pytest
    path = Path(__file__).resolve().parents[1] / 'scripts/mac/recorded_e2e.py'
    spec = importlib.util.spec_from_file_location('sentinel_mac_hash_gate', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    changed = tmp_path / 'modified.json'
    changed.write_bytes(module.METADATA.read_bytes() + b'\n')
    monkeypatch.setattr(module, 'METADATA', changed)
    with pytest.raises(AssertionError, match='hash mismatch'):
        module.run()
