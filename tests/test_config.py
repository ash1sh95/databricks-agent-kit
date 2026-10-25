import json

from agent_kit import get_secret, load_config, parse_yaml_lite


def test_yaml_lite_nested_and_typed():
    data = parse_yaml_lite(
        "agent_kit:\n  model_endpoint: mock\n  max_steps: 4\n  temperature: 0.5\n  debug: true\n"
    )
    assert data["agent_kit"]["model_endpoint"] == "mock"
    assert data["agent_kit"]["max_steps"] == 4
    assert data["agent_kit"]["temperature"] == 0.5
    assert data["agent_kit"]["debug"] is True


def test_load_json_config(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"catalog": "dev", "schema": "agents", "custom": 1}))
    cfg = load_config(path)
    assert cfg.catalog == "dev" and cfg.schema == "agents"
    assert cfg.extra == {"custom": 1}


def test_load_yaml_lite_config_with_group_key(tmp_path):
    path = tmp_path / "config.yml"
    path.write_text("agent_kit:\n  catalog: sandbox\n")
    assert load_config(path).catalog == "sandbox"


def test_env_overrides_file(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"catalog": "from-file"}))
    monkeypatch.setenv("AGENT_KIT_CATALOG", "from-env")
    assert load_config(path).catalog == "from-env"


def test_get_secret_reads_env_only(monkeypatch):
    monkeypatch.setenv("MY_TEST_SECRET", "s3cr3t-value")
    assert get_secret("MY_TEST_SECRET") == "s3cr3t-value"
    assert get_secret("DEFINITELY_MISSING", "fallback") == "fallback"
