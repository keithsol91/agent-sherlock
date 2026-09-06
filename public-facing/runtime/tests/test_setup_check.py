"""Installed-runtime setup verification, including real subprocess failures."""

from contextlib import asynccontextmanager
import json
import logging
from pathlib import Path
import sys
import tempfile
import time
import venv

import pytest

from agent_sherlock import setup_check


async def test_installed_runtime_round_trip_restart_and_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("SHERLOCK_CONFIG", str(tmp_path / "do-not-read-provider-config.json"))
    monkeypatch.setenv("SHERLOCK_DATA_DIR", str(tmp_path / "do-not-touch-data"))
    monkeypatch.setenv("SHERLOCK_PROFILE", "do-not-use-profile")
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "do-not-import"))
    real_stdio = setup_check.stdio_client
    starts = []
    closed = []

    @asynccontextmanager
    async def tracked_stdio(parameters, **kwargs):
        root = Path(parameters.cwd)
        assert not starts or len(closed) == 1, "First subprocess must close before restart"
        assert parameters.command == str(Path(sys.executable).absolute())
        assert parameters.args == [
            "-I", "-m", "agent_sherlock", "--data-dir", str(root / "data"),
            "--profile", "setup-check", "--config", str(root / "empty.json"), "serve",
        ]
        assert json.loads((root / "empty.json").read_text(encoding="utf-8")) == {"connections": {}}
        if starts:
            assert (root / "data/setup-check/cases.sqlite3").is_file()
        starts.append(root)
        async with real_stdio(parameters, **kwargs) as streams:
            yield streams
        assert root.is_dir(), "Temporary files must survive until subprocess exit"
        closed.append(root)

    monkeypatch.setattr(setup_check, "stdio_client", tracked_stdio)
    result = await setup_check.verify_runtime(sys.executable)

    assert result == {"passed": True, "tools_discovered": 25, "case_round_trip": True,
                      "restart_persistence": True, "provider_calls": 0}
    assert len(starts) == len(closed) == 2 and starts[0] == starts[1]
    assert not starts[0].exists()
    assert not (tmp_path / "do-not-touch-data").exists()


@pytest.mark.parametrize("kind", ["missing", "directory", "not-executable"])
async def test_bad_executable_has_safe_stage_error(tmp_path, kind):
    executable = tmp_path / "sensitive-example-path"
    if kind == "directory":
        executable.mkdir()
    elif kind == "not-executable":
        executable.write_text("not an executable", encoding="utf-8")
    expected = "MCP startup" if kind == "not-executable" else "Python executable validation"
    with pytest.raises(ValueError, match=f"^Runtime setup check failed during {expected}\\.$") as error:
        await setup_check.verify_runtime(executable)
    assert "sensitive-example-path" not in str(error.value)
    assert error.value.__suppress_context__ is True


async def test_python_without_installed_runtime_fails_cleanly(tmp_path, capfd):
    environment = tmp_path / "empty python environment"
    venv.EnvBuilder(with_pip=False).create(environment)
    python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")

    with pytest.raises(ValueError, match="^Runtime setup check failed during MCP startup\\.$"):
        await setup_check.verify_runtime(python)

    output = capfd.readouterr()
    assert "No module named" not in output.err
    assert "Traceback" not in output.err
    assert output.out == ""


def use_test_server(tmp_path, monkeypatch, source):
    """Replace only the launch arguments; still exercise the real SDK subprocess."""
    script = tmp_path / "fictional test server.py"
    script.write_text(source, encoding="utf-8")
    real_parameters = setup_check.StdioServerParameters
    created = []

    def parameters(**kwargs):
        kwargs["args"] = ["-I", str(script)]
        created.append(Path(kwargs["cwd"]))
        return real_parameters(**kwargs)

    monkeypatch.setattr(setup_check, "StdioServerParameters", parameters)
    monkeypatch.setattr(setup_check, "_REQUEST_TIMEOUT_SECONDS", 0.25)
    monkeypatch.setattr(setup_check, "_CHECK_TIMEOUT_SECONDS", 2)
    return created


async def test_invalid_server_output_is_suppressed_and_temp_data_removed(tmp_path, monkeypatch, capfd, caplog):
    roots = use_test_server(tmp_path, monkeypatch,
                            "import sys\n"
                            "print('fictional-secret-on-stdout', flush=True)\n"
                            "print('fictional-secret-on-stderr', file=sys.stderr, flush=True)\n")
    caplog.set_level(logging.DEBUG)
    with pytest.raises(ValueError, match="^Runtime setup check failed during MCP startup\\.$") as error:
        await setup_check.verify_runtime(sys.executable)

    output = capfd.readouterr()
    assert "fictional-secret" not in output.out + output.err + caplog.text + str(error.value)
    assert roots and all(not root.exists() for root in roots)
    assert setup_check._CHECK_LOG_CONTEXT.get() is False


async def test_hanging_server_is_bounded_and_terminated_before_cleanup(tmp_path, monkeypatch):
    # Reading stdin keeps this process alive until the client's shutdown closes
    # the pipe. Its final marker proves it exited before verification returned.
    marker = tmp_path / "fictional-server-exited"
    roots = use_test_server(tmp_path, monkeypatch,
                            "import sys\nfrom pathlib import Path\n"
                            "sys.stdin.read()\n"
                            f"Path({str(marker)!r}).write_text('closed', encoding='utf-8')\n")
    started = time.monotonic()
    with pytest.raises(ValueError, match="^Runtime setup check failed during MCP startup\\.$"):
        await setup_check.verify_runtime(sys.executable)

    assert time.monotonic() - started < 10
    assert marker.read_text(encoding="utf-8") == "closed"
    assert roots and all(not root.exists() for root in roots)


async def test_failed_tool_result_reports_only_its_stage(tmp_path, monkeypatch):
    real_call = setup_check._call
    roots = []
    real_temporary_directory = tempfile.TemporaryDirectory

    def temporary_directory(**kwargs):
        directory = real_temporary_directory(dir=tmp_path, **kwargs)
        roots.append(Path(directory.name))
        return directory

    async def failed_call(client, name, **arguments):
        if name == "finding_add":
            raise RuntimeError("fictional-secret-provider-error")
        return await real_call(client, name, **arguments)

    monkeypatch.setattr(setup_check, "TemporaryDirectory", temporary_directory)
    monkeypatch.setattr(setup_check, "_call", failed_call)
    with pytest.raises(ValueError, match="^Runtime setup check failed during fictional finding creation\\.$"):
        await setup_check.verify_runtime(sys.executable)
    assert roots and all(not root.exists() for root in roots)
