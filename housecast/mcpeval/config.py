"""Where the model and the subject live. Configuration, never code.

`base_url`, `api_key`, `model`. That is the customer's surface too, and nothing
below branches on which gateway or vendor answers. This deployment's own
gateway is a default value here and a value anyone can override, which is the
whole reason no gateway name appears in `models.py`.
"""

from __future__ import annotations

import os
import subprocess

# AGENTS.md routes model transport through Agent Proxy. The routing decision
# lives here so nothing in the loop's code knows about it.
DEFAULT_MODEL_BASE_URL = "http://ser8:8080/v1"
DEFAULT_MODEL = "evaluation/deepseek-v4-flash"
DEFAULT_SUBJECT_URL = "http://127.0.0.1:8931/mcp"

# Measured 2026-09-16, both facts and the timings behind this default:
# evaluations/mcp-tool-loop-2026-09-16/README.md.
KNOWN_NO_TOOL_CHOICE = (
    "evaluation/deepseek-v4-pro",
    "evaluation/deepseek-v4-flash",
    "evaluation/deepseek-v4-flash-vision-exp",
)
KNOWN_NO_STRUCTURED_CALLS = ("evaluation/ministral-3-14b",)


def model_base_url() -> str:
    return os.environ.get("MCPEVAL_MODEL_BASE_URL") or DEFAULT_MODEL_BASE_URL


def model_name() -> str:
    return os.environ.get("MCPEVAL_MODEL") or DEFAULT_MODEL


def subject_url() -> str:
    return os.environ.get("MCPEVAL_SUBJECT_URL") or DEFAULT_SUBJECT_URL


def api_key() -> str:
    """The key, from the environment or from this deployment's parameter store.

    Read at call time rather than imported, so a key never sits in a module
    global where a traceback or a repr can print it.
    """
    direct = os.environ.get("MCPEVAL_API_KEY")
    if direct:
        return direct
    path = os.environ.get("MCPEVAL_API_KEY_SSM")
    if not path:
        return ""
    try:
        out = subprocess.run(
            [
                "aosguard",
                "ops",
                "aws",
                "ssm",
                "get-parameter",
                "--name",
                path,
                "--with-decryption",
                "--query",
                "Parameter.Value",
                "--output",
                "text",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout.strip()
