#!/usr/bin/env python3
"""
工具实现模块 - 所有工具的具体实现
ver0.5
"""

import os
import sys
import json
import time
import ast
import urllib.request
import urllib.parse
import requests
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────────────────────
# 工具实现
# ─────────────────────────────────────────────────────────────

def calculator(expression: str) -> str:
    """安全的数学表达式计算器"""
    try:
        allowed_chars = set("0123456789.+-*/() **%")
        if not all(c in allowed_chars or c.isspace() for c in expression):
            return "错误: 表达式包含无效字符"

        # 使用 AST 解析验证表达式语法
        tree = ast.parse(expression, mode='eval')

        # 验证只包含数学运算（禁止函数调用、变量引用等）
        allowed_nodes = (
            ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
            ast.USub, ast.UAdd
        )

        for node in ast.walk(tree):
            if not isinstance(node, allowed_nodes):
                return "错误: 表达式包含不支持的操作"

        # 使用受限命名空间安全执行
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"错误: {e}"


def get_weather(city: str, provider: str = None, api_key: str = None) -> str:
    """获取城市天气"""
    if not city:
        return "错误: 城市名称不能为空"

    # 城市名映射（常见城市）
    city_map = {
        "北京": "Beijing", "上海": "Shanghai", "广州": "Guangzhou",
        "深圳": "Shenzhen", "武汉": "Wuhan", "西安": "Xi'an",
        "成都": "Chengdu", "重庆": "Chongqing", "杭州": "Hangzhou",
        "南京": "Nanjing", "天津": "Tianjin", "苏州": "Suzhou",
        "郑州": "Zhengzhou", "长沙": "Changsha", "沈阳": "Shenyang",
        "青岛": "Qingdao", "宁波": "Ningbo", "东莞": "Dongguan",
        "无锡": "Wuxi", "昆明": "Kunming", "哈尔滨": "Harbin",
        "福州": "Fuzhou", "厦门": "Xiamen", "济南": "Jinan",
        "大连": "Dalian", "温州": "Wenzhou", "合肥": "Hefei",
        "南宁": "Nanning", "南昌": "Nanchang", "贵阳": "Guiyang",
        "太原": "Taiyuan", "石家庄": "Shijiazhuang", "长春": "Changchun",
        "兰州": "Lanzhou", "海口": "Haikou", "珠海": "Zhuhai",
        "常州": "Changzhou", "徐州": "Xuzhou", "烟台": "Yantai",
        "唐山": "Tangshan", "洛阳": "Luoyang", "威海": "Weihai",
        "吉林": "Jilin", "九江": "Jiujiang", "大同": "Datong",
    }

    # 如果输入是中文，转换为英文
    city_en = city_map.get(city, city)

    # 根据 provider 调用不同的 API
    if provider == "openweathermap" or (provider is None and api_key):
        return _get_weather_openweathermap(city_en, api_key)
    elif provider == "weatherapi":
        return _get_weather_weatherapi(city_en, api_key)
    elif provider == "qweather":
        return _get_weather_qweather(city_en, api_key)
    else:
        return _get_weather_free(city_en)


def _get_weather_free(city: str) -> str:
    """使用 Open-Meteo 免费 API"""
    try:
        # 先获取城市坐标
        geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1"
        geo_resp = requests.get(geocode_url, timeout=10)
        geo_data = geo_resp.json()

        if not geo_data.get("results"):
            return f"未找到城市: {city}"

        lat = geo_data["results"][0]["latitude"]
        lon = geo_data["results"][0]["longitude"]
        timezone = geo_data["results"][0].get("timezone", "Asia/Shanghai")

        # 获取天气
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code,wind_speed_10m&timezone={urllib.parse.quote(timezone)}"
        resp = requests.get(weather_url, timeout=10)
        data = resp.json()

        current = data["current"]
        temp = current["temperature_2m"]
        weather_code = current["weather_code"]
        wind = current["wind_speed_10m"]

        weather_desc = _weather_code_to_desc(weather_code)

        return f"{city}: {weather_desc}，温度 {temp}°C，风速 {wind}km/h"
    except Exception as e:
        return f"查询失败: {e}"


def _get_weather_openweathermap(city: str, api_key: str = None) -> str:
    """使用 OpenWeatherMap API"""
    if not api_key:
        return "错误: 需要 API Key"

    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={urllib.parse.quote(city)}&appid={api_key}&units=metric"
        resp = requests.get(url, timeout=10)
        data = resp.json()

        if data.get("cod") != 200:
            return f"查询失败: {data.get('message', '未知错误')}"

        temp = data["main"]["temp"]
        weather = data["weather"][0]["description"]
        wind = data["wind"]["speed"]

        return f"{city}: {weather}，温度 {temp}°C，风速 {wind}m/s"
    except Exception as e:
        return f"查询失败: {e}"


def _get_weather_weatherapi(city: str, api_key: str = None) -> str:
    """使用 WeatherAPI.com"""
    if not api_key:
        return "错误: 需要 API Key"

    try:
        url = f"https://api.weatherapi.com/v1/current.json?key={api_key}&q={urllib.parse.quote(city)}&aqi=no"
        resp = requests.get(url, timeout=10)
        data = resp.json()

        if data.get("error"):
            return f"查询失败: {data['error'].get('message', '未知错误')}"

        temp = data["current"]["temp_c"]
        weather = data["current"]["condition"]["text"]
        wind = data["current"]["wind_kph"]

        return f"{city}: {weather}，温度 {temp}°C，风速 {wind}km/h"
    except Exception as e:
        return f"查询失败: {e}"


def _get_weather_qweather(city: str, api_key: str = None) -> str:
    """使用和风天气 API"""
    if not api_key:
        return "错误: 需要 API Key"

    try:
        url = f"https://devapi.qweather.com/v7/weather/now?location={urllib.parse.quote(city)}&key={api_key}"
        resp = requests.get(url, timeout=10)
        data = resp.json()

        if data.get("code") != "200":
            return f"查询失败: {data.get('message', '未知错误')}"

        now = data["now"]
        temp = now["temp"]
        weather = now["text"]
        wind = now["windSpeed"]

        return f"{city}: {weather}，温度 {temp}°C，风速 {wind}km/h"
    except Exception as e:
        return f"查询失败: {e}"


def _weather_code_to_desc(code: int) -> str:
    """将天气码转换为描述"""
    codes = {
        0: "☀️ 晴朗", 1: "🌤️ 大部晴朗", 2: "⛅ 多云", 3: "☁️ 阴天",
        45: "🌫️ 雾", 48: "🌫️ 冻雾",
        51: "🌧️ 小雨", 53: "🌧️ 中雨", 55: "🌧️ 大雨",
        61: "🌧️ 小雨", 63: "🌧️ 中雨", 65: "🌧️ 大雨",
        71: "🌨️ 小雪", 73: "🌨️ 中雪", 75: "🌨️ 大雪",
        80: "🌧️ 阵雨", 81: "🌧️ 中阵雨", 82: "⛈️ 强阵雨",
        95: "⛈️ 雷暴", 96: "⛈️ 雷暴冰雹", 99: "⛈️ 强雷暴冰雹",
    }
    return codes.get(code, "❓ 未知天气")


def change_weather_api(provider: str, reason: str = "") -> str:
    """更换天气 API 提供商"""
    from config_manager import save_config, load_config, WEATHER_PRESETS

    try:
        cfg = load_config()
        old_provider = cfg.get("weather_provider", "free")

        if old_provider == provider:
            return f"当前已经是 {WEATHER_PRESETS[provider]['name']}，无需更换"

        cfg["weather_provider"] = provider
        save_config(cfg)

        new_name = WEATHER_PRESETS[provider]["name"]
        return f"✅ 已更换天气 API：{new_name}\n原因: {reason}"
    except Exception as e:
        return f"更换失败: {e}"


def save_session_state(msgs: list = None) -> str:
    """保存当前会话状态"""
    from config_manager import load_config, CONFIG_FILE

    try:
        cfg = load_config()
        session_save_mode = cfg.get("session_save_mode", "overwrite")

        # 构建会话数据
        session_data = {
            "session_id": f"session_{int(time.time())}",
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "config": {
                "provider": cfg.get("provider", ""),
                "model": cfg.get("model", ""),
                "weather_provider": cfg.get("weather_provider", "free"),
            }
        }

        if msgs:
            # 保存最近的消息摘要
            recent = msgs[-20:] if len(msgs) > 20 else msgs
            session_data["dialogue_summary"] = [
                {"role": m.get("role"), "content": m.get("content", "")[:200]}
                for m in recent if isinstance(m, dict)
            ]

        # 根据保存模式选择文件名
        if session_save_mode == "timestamp":
            filename = f"latest_{time.strftime('%Y-%m-%d_%H-%M-%S')}.json"
        else:
            filename = "latest.json"

        save_path = os.path.join(os.path.dirname(CONFIG_FILE), filename)

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)

        return f"✅ 会话已保存: {filename}"
    except Exception as e:
        return f"保存失败: {e}"


def get_current_time() -> str:
    """获取当前日期和时间"""
    now = time.localtime()
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday = weekdays[now.tm_wday]
    return time.strftime(f"%Y年%m月%d日 %H:%M:%S {weekday}", now)


def search_flight(departure: str, destination: str, date: str) -> str:
    """搜索机票信息"""
    try:
        query = f"{departure} 到 {destination} 机票 {date}"
        return search_web(query)
    except Exception as e:
        return f"搜索失败: {e}"


def search_train(departure: str, destination: str) -> str:
    """搜索火车票信息"""
    try:
        query = f"{departure} 到 {destination} 火车票"
        return search_web(query)
    except Exception as e:
        return f"搜索失败: {e}"


def search_web(query: str) -> str:
    """通用网页搜索 - 使用 Bing"""
    try:
        url = f"https://www.bing.com/search?q={requests.utils.quote(query)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')

        results = []
        for item in soup.select('li.b_algo')[:6]:
            try:
                title_elem = item.select_one('h2 a')
                if not title_elem:
                    continue
                title = title_elem.get_text()
                link = title_elem.get('href', '')

                snippet = item.select_one('div.p')
                snippet_text = snippet.get_text() if snippet else ""

                results.append(f"📌 {title}\n   {snippet_text[:100]}...\n   🔗 {link[:80]}\n")
            except Exception:
                continue

        if not results:
            return "未找到相关结果"

        return "🌐 搜索结果：\n\n" + "\n".join(results)
    except Exception as e:
        return f"搜索失败: {e}"


def read_file(file_path: str) -> str:
    """读取本地文件（PDF 或 Markdown），提取主要内容"""
    # 安全检查：防止路径遍历
    file_path = os.path.abspath(file_path)

    if not os.path.exists(file_path):
        return f"❌ 文件不存在：{file_path}"

    # 检查文件大小（限制 10MB）
    file_size = os.path.getsize(file_path)
    if file_size > 10 * 1024 * 1024:
        return f"❌ 文件太大（{file_size / 1024 / 1024:.1f}MB），请选择 10MB 以内的文件"

    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            text_parts = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    text_parts.append(f"[第{i+1}页]\n{text}")
            if not text_parts:
                return "⚠️ PDF 中未提取到文字，可能是因为扫描版 PDF"
            content = "\n\n".join(text_parts)
            return f"📄 PDF 文件：{os.path.basename(file_path)}\n共 {len(reader.pages)} 页\n\n{content[:8000]}"
        elif ext == ".md":
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return f"📝 Markdown 文件：{os.path.basename(file_path)}\n\n{content[:10000]}"
        elif ext in (".txt", ".text"):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return f"📄 文本文件：{os.path.basename(file_path)}\n\n{content[:10000]}"
        else:
            return f"❌ 不支持的文件格式：{ext}，仅支持 .pdf、.md、.txt"
    except Exception as e:
        return f"❌ 读取文件失败：{e}"


def get_tool_impls(weather_provider: str = None, memory=None, todo_list=None):
    """获取工具实现字典"""
    impls = {
        "calculator": calculator,
        "search_memory": lambda query="": memory.retrieve(query) if memory else "记忆系统未初始化",
        "change_weather_api": change_weather_api,
        "create_todo_list": lambda tasks: todo_list.create(tasks) if todo_list else "ToDoList 未初始化",
        "complete_task": lambda result="": todo_list.complete_task(result) if todo_list else "ToDoList 未初始化",
        "save_session_state": save_session_state,
        "get_current_time": get_current_time,
        "search_flight": search_flight,
        "search_train": search_train,
        "search_web": search_web,
        "read_file": read_file,
        "add_longterm_memory": lambda content, category="用户偏好": memory.add_longterm_memory(content, category) if memory else "记忆系统未初始化",
        "get_longterm_memories": lambda category=None: memory.get_longterm_memories(category) if memory else "记忆系统未初始化",
        "remove_longterm_memory": lambda memory_id=None, content=None: memory.remove_longterm_memory(memory_id, content) if memory else "记忆系统未初始化",
    }
    if weather_provider:
        impls["get_weather"] = lambda city, p=weather_provider: get_weather(city, p)
    return impls
