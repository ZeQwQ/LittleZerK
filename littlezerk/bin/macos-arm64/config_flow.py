#!/usr/bin/env python3
"""
配置流程模块 - 交互式配置向导
ver0.5
"""

from config_manager import (
    MODEL_PRESETS, WEATHER_PRESETS,
    STEP_BACK, load_config, save_config
)
from api_detection import detect_provider


# ─────────────────────────────────────────────────────────────
# 配置流程步骤
# ─────────────────────────────────────────────────────────────

def step1_select_input_method() -> str:
    """步骤1: 选择输入方式"""
    print("\n" + "-" * 40)
    print("📍 选择 API 输入方式")
    print(f"   输入 {STEP_BACK} 返回\n")
    print("  1. 输入 API 端点 (Base URL)")
    print("  2. 输入 API Key + Base URL")
    print("  3. 从预设列表选择")

    while True:
        c = input(f"\n选择 (1/2/3) [{STEP_BACK} 返回]: ").strip()
        if c == STEP_BACK:
            return None
        if c in ("1", "2", "3"):
            return c
        print("无效选择，请输入 1、2 或 3")


def step2_input_base_url(state: dict) -> dict:
    """步骤2a: 输入 Base URL"""
    print("\n" + "-" * 40)
    print("📍 输入 API 端点 (Base URL)")
    print(f"   输入 {STEP_BACK} 返回\n")
    print("示例:")
    print("  https://api.minimaxi.com/v1")
    print("  https://api.deepseek.com/v1")
    print("  https://api.openai.com/v1")

    base_url = input(f"\n输入 Base URL [{STEP_BACK} 返回]: ").strip()
    if base_url == STEP_BACK:
        return None

    if not base_url:
        print("URL 不能为空")
        return step2_input_base_url(state)

    # 自动检测提供商
    preset_key, preset = detect_provider(base_url)
    if preset:
        print(f"✅ 检测到提供商: {preset['name']}")
        state["preset"] = preset
        state["preset_key"] = preset_key
    else:
        print("⚠️ 未识别到已知提供商，将使用自定义配置")
        state["preset"] = MODEL_PRESETS["custom"]
        state["preset_key"] = "custom"

    # 修正 URL 格式
    if not base_url.endswith("/v1"):
        base_url = base_url.rstrip("/") + "/v1"

    state["base_url"] = base_url
    return state


def step2_input_api_key(state: dict) -> dict:
    """步骤2b: 输入 API Key 和 Base URL"""
    print("\n" + "-" * 40)
    print("📍 输入 API Key 和 Base URL")
    print(f"   输入 {STEP_BACK} 返回\n")

    api_key = input("输入 API Key: ").strip()
    if api_key == STEP_BACK:
        return None

    if not api_key:
        print("API Key 不能为空")
        return step2_input_api_key(state)

    base_url = input("输入 Base URL: ").strip()
    if base_url == STEP_BACK:
        return None

    if not base_url:
        print("URL 不能为空")
        return step2_input_api_key(state)

    state["api_key"] = api_key
    state["preset"] = MODEL_PRESETS["custom"]
    state["preset_key"] = "custom"

    # 修正 URL 格式
    if not base_url.endswith("/v1"):
        base_url = base_url.rstrip("/") + "/v1"

    state["base_url"] = base_url
    return state


def step2_select_from_preset(state: dict) -> dict:
    """步骤2c: 从预设选择"""
    print("\n" + "-" * 40)
    print("📍 选择 AI 提供商")
    print(f"   输入 {STEP_BACK} 返回\n")

    presets = list(MODEL_PRESETS.items())
    for i, (key, preset) in enumerate(presets, 1):
        print(f"  {i}. {preset['name']}")

    while True:
        c = input(f"\n选择 (1-{len(presets)}) [{STEP_BACK} 返回]: ").strip()
        if c == STEP_BACK:
            return None

        try:
            idx = int(c) - 1
            if 0 <= idx < len(presets):
                key, preset = presets[idx]
                state["preset"] = preset
                state["preset_key"] = key
                print(f"✅ 已选择: {preset['name']}")

                if preset["base_url"]:
                    state["base_url"] = preset["base_url"]
                return state
        except ValueError:
            pass

        print(f"无效选择，请输入 1-{len(presets)}")


def step3_input_api_key(state: dict) -> dict:
    """步骤3: 输入 API Key"""
    print("\n" + "-" * 40)
    print("📍 输入 API Key")
    print(f"   输入 {STEP_BACK} 返回\n")

    preset = state.get("preset", {})
    name = preset.get("name", "该提供商")

    if not preset.get("default_model"):
        print(f"⚠️ {name} 需要手动输入完整信息")

    api_key = input("输入 API Key: ").strip()
    if api_key == STEP_BACK:
        return None

    if not api_key:
        print("API Key 不能为空")
        return step3_input_api_key(state)

    state["api_key"] = api_key
    state["provider_key"] = state["preset_key"]
    return state


def step4_select_model(state: dict) -> dict:
    """步骤4: 选择模型"""
    print("\n" + "-" * 40)
    print("📍 选择 AI 模型")
    print(f"   输入 {STEP_BACK} 返回\n")

    preset = state.get("preset", {})
    models = preset.get("models", [])
    default = preset.get("default_model", "")

    if models:
        print(f"可用模型 (默认: {default}):\n")
        for i, model in enumerate(models, 1):
            marker = " ← 默认" if model == default else ""
            print(f"  {i}. {model}{marker}")
        print(f"\n  c. 自定义模型名称")

        while True:
            c = input(f"\n选择模型编号或输入模型名 [{STEP_BACK} 返回]: ").strip()
            if c == STEP_BACK:
                return None

            if c.lower() == "c":
                model = input("输入自定义模型名称: ").strip()
                if model == STEP_BACK:
                    continue
                if model:
                    state["model"] = model
                    return state

            try:
                idx = int(c) - 1
                if 0 <= idx < len(models):
                    state["model"] = models[idx]
                    print(f"✅ 已选择: {models[idx]}")
                    return state
            except ValueError:
                pass

            # 直接输入模型名
            if c:
                state["model"] = c
                return state

            print("无效选择")
    else:
        model = input("输入模型名称: ").strip()
        if model == STEP_BACK:
            return None
        state["model"] = model or default
        return state


def step5_select_weather_provider(state: dict) -> dict:
    """步骤5: 选择天气 API"""
    print("\n" + "-" * 40)
    print("📍 选择天气 API（可选）")
    print(f"   输入 {STEP_BACK} 返回\n")

    presets = list(WEATHER_PRESETS.items())
    for i, (key, preset) in enumerate(presets, 1):
        need_key = "需要 Key" if preset["need_key"] else "免费无需 Key"
        print(f"  {i}. {preset['name']} ({need_key})")

    while True:
        c = input(f"\n选择天气 API (1-{len(presets)}) [{STEP_BACK} 返回]: ").strip()
        if c == STEP_BACK:
            return None

        try:
            idx = int(c) - 1
            if 0 <= idx < len(presets):
                key, preset = presets[idx]
                state["weather_provider"] = key
                state["weather_preset"] = preset
                print(f"✅ 已选择: {preset['name']}")
                return state
        except ValueError:
            pass

        print(f"无效选择，请输入 1-{len(presets)}")


def step6_input_weather_key(state: dict) -> dict:
    """步骤6: 输入天气 API Key（如果需要）"""
    weather_provider = state.get("weather_provider", "free")
    weather_preset = state.get("weather_preset", {})

    if not weather_preset.get("need_key"):
        state["weather_api_key"] = ""
        return state

    print("\n" + "-" * 40)
    print("📍 输入天气 API Key")
    print(f"   输入 {STEP_BACK} 返回\n")
    print(f"提供商: {weather_preset.get('name', '')}")
    print(f"获取地址: https://www.qweather.com" if weather_provider == "qweather" else "")

    key_env = weather_preset.get("key_env", "")
    if key_env:
        import os
        env_key = os.environ.get(key_env, "")
        if env_key:
            print(f"\n检测到环境变量 {key_env}，是否使用？")
            use_env = input("使用环境变量 (Y/n): ").strip().lower()
            if use_env != "n":
                state["weather_api_key"] = env_key
                print("✅ 已使用环境变量中的 Key")
                return state

    api_key = input("输入 API Key: ").strip()
    if api_key == STEP_BACK:
        return None

    state["weather_api_key"] = api_key
    return state


def step7_select_session_save_mode(state: dict) -> dict:
    """步骤7: 选择会话保存方式"""
    print("\n" + "-" * 40)
    print("📍 选择会话保存方式")
    print(f"   输入 {STEP_BACK} 返回\n")
    print("  1. 自动覆盖（latest.json） - 节约空间，每次只保存一份")
    print("  2. 时间戳保存（latest_xxx.json） - 详细完整，保留历史记录")

    while True:
        c = input(f"\n选择保存方式 (1/2) [{STEP_BACK} 返回]: ").strip()
        if c == STEP_BACK:
            return None
        if c == "1":
            state["session_save_mode"] = "overwrite"
            return state
        if c == "2":
            state["session_save_mode"] = "timestamp"
            return state
        print("无效选择，请输入 1 或 2")


# ─────────────────────────────────────────────────────────────
# 主配置流程
# ─────────────────────────────────────────────────────────────

def get_config(force_reset: bool = False):
    """获取配置（引导用户完成配置或加载已有配置）"""
    if not force_reset:
        saved = load_config()
        if saved.get("api_key") and saved.get("base_url") and saved.get("model"):
            print("\n" + "=" * 50)
            print("🤖 小小泽 - ver0.5")
            print("=" * 50)
            print(f"\n📌 检测到已保存的配置:")
            print(f"   AI 提供商: {saved.get('provider', '未知')}")
            print(f"   AI 模型: {saved.get('model')}")
            weather_provider = saved.get("weather_provider", "free")
            weather_name = WEATHER_PRESETS.get(weather_provider, {}).get("name", "未知")
            print(f"   天气 API: {weather_name}")
            print(f"\n   输入 'api choose' 可重新选择配置")
            return saved

    state = {}

    input_method = step1_select_input_method()
    if input_method is None:
        return get_config()

    if input_method == "1":
        result = step2_input_base_url(state)
        if result is None:
            return get_config()
    elif input_method == "2":
        result = step2_input_api_key(state)
        if result is None:
            return get_config()
    else:
        result = step2_select_from_preset(state)
        if result is None:
            return get_config()

    result = step3_input_api_key(state)
    if result is None:
        return get_config()

    result = step4_select_model(state)
    if result is None:
        return get_config()

    result = step5_select_weather_provider(state)
    if result is None:
        return get_config()

    result = step6_input_weather_key(state)
    if result is None:
        return get_config()

    result = step7_select_session_save_mode(state)
    if result is None:
        return get_config()

    base_url = state["base_url"]
    if base_url and not base_url.endswith("/v1"):
        base_url = base_url.rstrip("/") + "/v1"

    save_mode_names = {"overwrite": "自动覆盖（latest.json）", "timestamp": "时间戳（latest_xxx.json）"}

    cfg = {
        "base_url": base_url,
        "api_key": state["api_key"],
        "model": state["model"],
        "provider": state["preset"]["name"],
        "provider_key": state["provider_key"],
        "weather_provider": state["weather_provider"],
        "weather_api_key": state.get("weather_api_key", ""),
        "session_save_mode": state.get("session_save_mode", "overwrite"),
    }

    save_config(cfg)

    print("\n" + "=" * 50)
    print("✅ 配置完成并已保存!")
    print(f"   AI 提供商: {state['preset']['name']}")
    print(f"   AI 模型: {state['model']}")
    print(f"   天气 API: {state['weather_preset']['name']}")
    print(f"   会话保存: {save_mode_names.get(state.get('session_save_mode', 'overwrite'))}")
    print("=" * 50)

    return cfg
