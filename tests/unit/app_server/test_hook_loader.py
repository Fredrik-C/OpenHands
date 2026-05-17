import json
from pathlib import Path

from openhands.app_server.app_conversation.hook_loader import (
    load_hooks_from_file,
    merge_hook_configs,
)
from openhands.sdk.hooks import HookConfig


def _hook_config(data: dict) -> HookConfig:
    return HookConfig.from_dict(data)


def test_merge_hook_configs_global_precedence_and_dedup():
    global_hooks = _hook_config(
        {
            'stop': [
                {
                    'matcher': '*',
                    'hooks': [
                        {'type': 'command', 'command': 'echo baseline', 'timeout': 10}
                    ],
                }
            ]
        }
    )
    workspace_hooks = _hook_config(
        {
            'stop': [
                {
                    'matcher': '*',
                    'hooks': [
                        {'type': 'command', 'command': 'echo baseline', 'timeout': 10},
                        {'type': 'command', 'command': 'echo workspace', 'timeout': 15},
                    ],
                }
            ]
        }
    )

    merged = merge_hook_configs(global_hooks, workspace_hooks)

    assert merged is not None
    stop_matchers = merged.model_dump(mode='json')['stop']
    assert stop_matchers[0]['matcher'] == '*'
    hooks = stop_matchers[0]['hooks']
    assert hooks == [
        {'type': 'command', 'command': 'echo baseline', 'timeout': 10},
        {'type': 'command', 'command': 'echo workspace', 'timeout': 15},
    ]


def test_load_hooks_from_file_supports_wrapped_payload(tmp_path: Path):
    hook_file = tmp_path / 'workflow-hooks.json'
    hook_file.write_text(
        json.dumps(
            {
                'hook_config': {
                    'stop': [
                        {
                            'matcher': '*',
                            'hooks': [
                                {
                                    'type': 'command',
                                    'command': 'echo stop',
                                    'timeout': 5,
                                }
                            ],
                        }
                    ]
                }
            }
        ),
        encoding='utf-8',
    )

    hook_config = load_hooks_from_file(str(hook_file))

    assert hook_config is not None
    assert hook_config.model_dump(mode='json')['stop'][0]['matcher'] == '*'
