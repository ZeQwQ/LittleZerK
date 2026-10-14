#!/usr/bin/env python3
"""
API 检测模块 - 自动识别 AI 提供商
ver0.5
"""

from config_manager import MODEL_PRESETS


def detect_provider(base_url: str) -> tuple:
    """
    根据 base_url 自动识别提供商
    返回 (preset_key, preset)
    """
    if not base_url:
        return None, None

    base_url_lower = base_url.lower()

    for key, preset in MODEL_PRESETS.items():
        for regex in preset.get("regex", []):
            import re
            if re.search(regex, base_url_lower):
                return key, preset

    return None, None
