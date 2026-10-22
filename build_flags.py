#!/usr/bin/env python3
"""
生成 Nuitka --include-package 参数列表

不同环境下第三方依赖的包名可能不同（例如 httpx / httpx2），
所以运行时探测实际已安装的包，动态生成编译参数，
避免 CI 因硬编码包名不存在而直接失败。

用法：
    python build_flags.py            # 打印参数
    python build_flags.py --env      # 写入 $GITHUB_ENV（CI 用）
"""

import importlib.util
import os
import sys

# 候选依赖包：命中哪个就包含哪个
CANDIDATES = [
    "openai",          # 必须：SDK 使用惰性导入，必须整包包含
    "httpx2", "httpx",
    "httpcore2", "httpcore",
    "pydantic", "pydantic_core",
    "anyio",
    "requests",
    "bs4", "soupsieve",
    "pypdf",
    "markdown",
    "primp",
    "jiter",
    "sniffio",
    "certifi",
    "idna",
    "lxml",
    "distro",
    "tqdm",
    "typing_extensions",
]


def collect_flags():
    """探测已安装的包，返回 Nuitka 参数列表"""
    found = []
    for pkg in CANDIDATES:
        try:
            if importlib.util.find_spec(pkg) is not None:
                found.append(pkg)
        except (ImportError, ValueError):
            # find_spec 对命名空间包等情况可能抛异常，忽略即可
            continue
    return [f"--include-package={pkg}" for pkg in found]


def main():
    flags = collect_flags()
    joined = " ".join(flags)

    if "--env" in sys.argv:
        github_env = os.environ.get("GITHUB_ENV")
        if not github_env:
            print("错误: 未检测到 GITHUB_ENV 环境变量", file=sys.stderr)
            sys.exit(1)
        with open(github_env, "a", encoding="utf-8") as f:
            f.write(f"NUITKA_INCLUDES={joined}\n")
    else:
        print(joined)

    print(f"[build_flags] 共包含 {len(flags)} 个包", file=sys.stderr)


if __name__ == "__main__":
    main()
