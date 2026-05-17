"""Utilities for loading hooks for V1 conversations.

This module provides functions to load hooks from the agent-server,
which centralizes all hook loading logic. The app-server acts as a
thin proxy that calls the agent-server's /api/hooks endpoint.

All hook loading is handled by the agent-server.
"""

import json
import logging
from pathlib import Path
from typing import Any

import httpx

from openhands.sdk.hooks import HookConfig

_logger = logging.getLogger(__name__)


def _hook_config_to_dict(hook_config: HookConfig) -> dict[str, Any]:
    return hook_config.model_dump(mode='json', exclude_none=True)


def _hook_identity(hook: dict[str, Any]) -> str:
    hook_type = str(hook.get('type', ''))
    command = str(hook.get('command', ''))
    timeout = str(hook.get('timeout', ''))
    async_flag = str(hook.get('async', ''))
    return f'{hook_type}|{command}|{timeout}|{async_flag}'


def merge_hook_configs(
    global_hook_config: HookConfig | None,
    workspace_hook_config: HookConfig | None,
) -> HookConfig | None:
    """Merge hook configs with deterministic precedence and de-duplication.

    Precedence/order:
    1. Global hooks first.
    2. Workspace hooks appended.
    3. Duplicate hooks (per event + matcher) are removed.
    """
    if global_hook_config is None and workspace_hook_config is None:
        return None
    if global_hook_config is None:
        return workspace_hook_config
    if workspace_hook_config is None:
        return global_hook_config

    global_data = _hook_config_to_dict(global_hook_config)
    workspace_data = _hook_config_to_dict(workspace_hook_config)
    merged: dict[str, list[dict[str, Any]]] = {}
    event_types = sorted(
        {
            *(global_data.keys()),
            *(workspace_data.keys()),
        }
    )

    for event_type in event_types:
        matcher_order: list[str] = []
        matcher_to_hooks: dict[str, list[dict[str, Any]]] = {}
        matcher_seen_hooks: dict[str, set[str]] = {}

        for source in (global_data, workspace_data):
            for matcher in source.get(event_type, []) or []:
                matcher_key = str(matcher.get('matcher', '*'))
                if matcher_key not in matcher_to_hooks:
                    matcher_to_hooks[matcher_key] = []
                    matcher_seen_hooks[matcher_key] = set()
                    matcher_order.append(matcher_key)

                for hook in matcher.get('hooks', []) or []:
                    if not isinstance(hook, dict):
                        continue
                    identity = _hook_identity(hook)
                    if identity in matcher_seen_hooks[matcher_key]:
                        continue
                    matcher_seen_hooks[matcher_key].add(identity)
                    matcher_to_hooks[matcher_key].append(hook)

        merged_matchers: list[dict[str, Any]] = []
        for matcher_key in matcher_order:
            hooks = matcher_to_hooks[matcher_key]
            if not hooks:
                continue
            merged_matchers.append({'matcher': matcher_key, 'hooks': hooks})

        if merged_matchers:
            merged[event_type] = merged_matchers

    if not merged:
        return None

    merged_config = HookConfig.from_dict(merged)
    if merged_config.is_empty():
        return None
    return merged_config


def load_hooks_from_file(path: str) -> HookConfig | None:
    """Load a hook config from a local JSON file.

    Accepts either:
    - a direct HookConfig dict shape, or
    - a wrapper payload with ``{"hook_config": ...}``.
    """
    hook_path = Path(path)
    content = hook_path.read_text(encoding='utf-8')
    data = json.loads(content)

    if not isinstance(data, dict):
        raise ValueError(f'Hook file {path} must contain a JSON object')

    hook_config_data = data.get('hook_config') if 'hook_config' in data else data
    if hook_config_data is None:
        return None
    if not isinstance(hook_config_data, dict):
        raise ValueError(f'Invalid hook_config payload in {path}')

    hook_config = HookConfig.from_dict(hook_config_data)
    if hook_config.is_empty():
        return None
    return hook_config


def get_project_dir_for_hooks(
    working_dir: str,
    selected_repository: str | None = None,
) -> str:
    """Get the project directory path for loading hooks.

    When a repository is selected, hooks are loaded from
    {working_dir}/{repo_name}/.openhands/hooks.json.
    Otherwise, hooks are loaded from {working_dir}/.openhands/hooks.json.

    Args:
        working_dir: Base working directory path in the sandbox
        selected_repository: Repository name (e.g., 'OpenHands/software-agent-sdk')
            If provided, the repo name is appended to working_dir.

    Returns:
        The project directory path where hooks.json should be located.
    """
    if selected_repository:
        repo_name = selected_repository.split('/')[-1]
        return f'{working_dir}/{repo_name}'
    return working_dir


async def fetch_hooks_from_agent_server(
    agent_server_url: str,
    session_api_key: str | None,
    project_dir: str,
    httpx_client: httpx.AsyncClient,
) -> HookConfig | None:
    """Fetch hooks from the agent-server, raising on HTTP/connection errors.

    This is the low-level function that makes a single API call to the
    agent-server's /api/hooks endpoint. It raises on HTTP and connection
    errors so callers can decide how to handle failures.

    Args:
        agent_server_url: URL of the agent server (e.g., 'http://localhost:8000')
        session_api_key: Session API key for authentication (optional)
        project_dir: Workspace directory path for project hooks
        httpx_client: Shared HTTP client for making the request

    Returns:
        HookConfig if hooks.json exists and is valid, None if no hooks found.

    Raises:
        httpx.HTTPStatusError: If the agent-server returns a non-2xx status.
        httpx.RequestError: If the agent-server is unreachable.
    """
    _logger.debug(
        f'fetch_hooks_from_agent_server called: '
        f'agent_server_url={agent_server_url}, project_dir={project_dir}'
    )
    payload = {'project_dir': project_dir}

    headers = {'Content-Type': 'application/json'}
    if session_api_key:
        headers['X-Session-API-Key'] = session_api_key

    response = await httpx_client.post(
        f'{agent_server_url}/api/hooks',
        json=payload,
        headers=headers,
        timeout=30.0,
    )
    response.raise_for_status()

    data = response.json()

    hook_config_data = data.get('hook_config')
    if hook_config_data is None:
        _logger.debug('No hooks found in workspace')
        return None

    hook_config = HookConfig.from_dict(hook_config_data)

    if hook_config.is_empty():
        _logger.debug('Hooks config is empty')
        return None

    _logger.debug(f'Loaded hooks from agent-server for {project_dir}')
    return hook_config


async def load_hooks_from_agent_server(
    agent_server_url: str,
    session_api_key: str | None,
    project_dir: str,
    httpx_client: httpx.AsyncClient,
) -> HookConfig | None:
    """Load hooks from the agent-server, swallowing errors gracefully.

    Wrapper around fetch_hooks_from_agent_server that catches all errors
    and returns None. Use this for the conversation-start path where hooks
    are optional and failures should not block startup.

    For the hooks viewer endpoint, use fetch_hooks_from_agent_server directly
    so errors can be surfaced to the user.

    Args:
        agent_server_url: URL of the agent server (e.g., 'http://localhost:8000')
        session_api_key: Session API key for authentication (optional)
        project_dir: Workspace directory path for project hooks
        httpx_client: Shared HTTP client for making the request

    Returns:
        HookConfig if hooks.json exists and is valid, None otherwise.
    """
    try:
        return await fetch_hooks_from_agent_server(
            agent_server_url, session_api_key, project_dir, httpx_client
        )
    except httpx.HTTPStatusError as e:
        _logger.warning(
            f'Agent-server at {agent_server_url} returned error status {e.response.status_code} '
            f'when loading hooks from {project_dir}: {e.response.text}'
        )
        return None
    except httpx.RequestError as e:
        _logger.warning(
            f'Failed to connect to agent-server at {agent_server_url} '
            f'when loading hooks from {project_dir}: {e}'
        )
        return None
    except Exception as e:
        _logger.warning(
            f'Failed to load hooks from agent-server at {agent_server_url} '
            f'for project {project_dir}: {e}'
        )
        return None
