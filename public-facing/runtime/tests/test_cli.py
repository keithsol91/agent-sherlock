import json
import os
import subprocess
import sys


def run_cli(tmp_path, *args, env=None):
    return subprocess.run([sys.executable, "-m", "agent_sherlock", "--data-dir", str(tmp_path), *args],
                          capture_output=True, text=True, env=env, timeout=30)


def test_cold_demo_ignores_inherited_provider_configuration(tmp_path):
    env = dict(os.environ, SHERLOCK_CONFIG=str(tmp_path / "absent-private-config.json"))
    first = run_cli(tmp_path, "demo", env=env)
    assert first.returncode == 0, first.stderr
    result = json.loads(first.stdout)
    assert result["fictional"] is True and result["network_calls"] == 0
    assert result["profile"] == "demo"
    assert result["fictional_crm_record"]["account_id"] == "fictional-account"
    second = run_cli(tmp_path, "demo", env=env)
    assert second.returncode == 0, second.stderr
    assert json.loads(second.stdout)["medical_clients"] == result["medical_clients"]
    assert not (tmp_path / "default/cases.sqlite3").exists()


def test_module_exit_status_reports_failure(tmp_path):
    failed = run_cli(tmp_path, "--profile", "../escape", "doctor")
    assert failed.returncode == 2
    assert not failed.stdout

