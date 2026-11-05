"""UI-independent preparation of noninteractive service answers."""
from __future__ import annotations

from typing import Any, TypedDict

from rdt.presets.catalog import ServicePreset
from rdt.smart_mapping import get_candidate_parents, apply_smart_mapping
from rdt.strategies.base import NETWORK_NAME
from rdt.strategies.web_server import (
    DEFAULT_CONFIG_DIR, DEFAULT_HTML_DIR, _HTML_MODES,
    DEFAULT_APACHE_CONFIG_DIR, DEFAULT_APACHE_HTML_DIR, DEFAULT_APACHE_SRC_DIR,
)
from rdt.strategies.traefik import (
    DEFAULT_TRAEFIK_CONFIG_DIR, DEFAULT_DASHBOARD_PORT, DEFAULT_HTTPS_PORT,
)


class PreparedAnswers(TypedDict, total=False):
    """Common fields; individual presets may add further answer keys."""

    port: int
    container_name: str
    use_default_creds: bool
    volume_source: str
    network_type: str
    network_name: str
    expose_ports: bool
    healthcheck_params: dict[str, Any]
    depends_on: list[str]
    parent_service: str
    smart_env: dict[str, str]


def build_script_answers(
    preset: ServicePreset,
    port: int | None,
    volume: str | None,
    depends_on: list[str],
    hardcore: bool,
    existing_services: list[str],
    container_name: str | None = None,
    no_ports: bool = False,
    network: str | None = None,
    hc_interval: str | None = None,
    hc_timeout: str | None = None,
    hc_retries: int | None = None,
    hc_start_period: str | None = None,
) -> PreparedAnswers:
    """
    Build an answers dictionary from CLI flags without the interactive wizard.
    Used when running rdt add <service> --yes [--port X] [--volume Y] ...
    """
    answers: dict[str, Any] = {}

    # Port.
    answers["port"] = port if port is not None else preset.default_port

    # Container name
    answers["container_name"] = container_name if container_name else preset.name

    # Credentials
    answers["use_default_creds"] = not hardcore

    # Volume (only for services with volumes).
    if preset.volumes:
        answers["volume_source"] = volume if volume is not None else f"{preset.name}_data"

    # Network.
    if network is None or network == "bridge":
        answers["network_type"] = "bridge"
        answers["network_name"] = NETWORK_NAME
    elif network == "host":
        answers["network_type"] = "host"
        answers["network_name"] = ""
    elif network == "none":
        answers["network_type"] = "none"
        answers["network_name"] = ""
    else:
        # External network name.
        answers["network_type"] = "external"
        answers["network_name"] = network

    # Port publishing.
    answers["expose_ports"] = not no_ports

    # Healthcheck parameters.
    hc_params: dict[str, Any] = {}
    if hc_interval:
        hc_params["interval"] = hc_interval
    if hc_timeout:
        hc_params["timeout"] = hc_timeout
    if hc_retries is not None:
        hc_params["retries"] = hc_retries
    if hc_start_period:
        hc_params["start_period"] = hc_start_period
    answers["healthcheck_params"] = hc_params

    # Dependencies.
    answers["depends_on"] = list(depends_on)

    # Auto Smart Mapping: automatically apply the first found candidate.
    candidates = get_candidate_parents(preset.name, existing_services)
    if candidates:
        answers["parent_service"] = candidates[0]
        answers = apply_smart_mapping(preset.name, existing_services, answers)

    # Service-specific defaults for script mode.
    _apply_service_script_defaults(preset, answers)

    return answers  # Preset-specific extension keys remain supported.


def _apply_service_script_defaults(preset: ServicePreset, answers: dict[str, Any]) -> None:
    """
    Set service-specific defaults for script mode.
    Called from build_script_answers after all common parameters.
    """
    if preset.name == "nginx-proxy":
        answers.setdefault("nginx_upstream", "app:8000")
        answers.setdefault("nginx_server_name", "localhost")
        answers.setdefault("nginx_config_dir", DEFAULT_CONFIG_DIR)

    elif preset.name in _HTML_MODES:
        answers.setdefault("nginx_server_name", "localhost")
        answers.setdefault("nginx_config_dir", DEFAULT_CONFIG_DIR)
        answers.setdefault("nginx_html_dir", DEFAULT_HTML_DIR)

    elif preset.name == "apache-static":
        answers.setdefault("apache_server_name", "localhost")
        answers.setdefault("apache_config_dir", DEFAULT_APACHE_CONFIG_DIR)
        answers.setdefault("apache_html_dir", DEFAULT_APACHE_HTML_DIR)

    elif preset.name == "apache-php":
        answers.setdefault("apache_server_name", "localhost")
        answers.setdefault("apache_config_dir", DEFAULT_APACHE_CONFIG_DIR)
        answers.setdefault("apache_src_dir", DEFAULT_APACHE_SRC_DIR)

    elif preset.name == "logstash":
        # Pipeline mode: beats-es when smart mapping found ES, otherwise beats-stdout.
        pipeline = answers.get("logstash_pipeline", "beats-stdout")
        answers["logstash_pipeline"] = pipeline
        answers["logstash_pipeline_stdout"] = (pipeline == "beats-stdout")
        answers["logstash_pipeline_es"] = (pipeline == "beats-es")
        if pipeline == "beats-es":
            answers.setdefault(
                "logstash_es_host",
                (answers.get("smart_env") or {}).get("LOGSTASH_ES_HOST", "elasticsearch:9200"),
            )

    elif preset.name == "filebeat":
        # Output mode: logstash when found, otherwise elasticsearch when ES is found, otherwise stdout.
        output = answers.get("filebeat_output", "stdout")
        answers["filebeat_output"] = output
        answers["filebeat_output_logstash"] = (output == "logstash")
        answers["filebeat_output_es"] = (output == "elasticsearch")
        answers["filebeat_output_stdout"] = (output == "stdout")
        answers.setdefault("filebeat_log_path", "/var/log/*.log")
        answers.setdefault("filebeat_kibana_host",
                           (answers.get("smart_env") or {}).get("FILEBEAT_KIBANA_HOST", ""))
        if output == "logstash":
            answers.setdefault(
                "filebeat_logstash_host",
                (answers.get("smart_env") or {}).get("FILEBEAT_LOGSTASH_HOST", "logstash:5044"),
            )
        elif output == "elasticsearch":
            answers.setdefault(
                "filebeat_es_host",
                (answers.get("smart_env") or {}).get("FILEBEAT_ES_HOST", "elasticsearch:9200"),
            )

    elif preset.name == "traefik":
        answers.setdefault("traefik_dashboard", True)
        answers.setdefault("dashboard_port", DEFAULT_DASHBOARD_PORT)
        answers.setdefault("traefik_dashboard_insecure", True)
        answers.setdefault("traefik_https", False)
        answers.setdefault("https_port", DEFAULT_HTTPS_PORT)
        answers.setdefault("traefik_http_redirect", False)
        answers.setdefault("traefik_acme_email", "admin@example.com")
        answers.setdefault("traefik_config_dir", DEFAULT_TRAEFIK_CONFIG_DIR)

