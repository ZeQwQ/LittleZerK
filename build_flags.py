#!/usr/bin/env python3
"""
生成 Nuitka 依赖包含参数

不同环境下第三方依赖的包名可能不同（例如 httpx / httpx2），
所以运行时探测实际已安装的模块，再动态生成编译参数，
避免 CI 因硬编码包名不存在而直接失败。

同时区分「包」与「单文件模块」：
- 包（目录形式）用 --include-package
- 单文件模块（typing_extensions.py、idna.py 等）用 --include-module
  传错会触发 Nuitka 的 "failed to locate package" 致命错误。

用法：
    python build_flags.py            # 打印参数
    python build_flags.py --env      # 写入 $GITHUB_ENV（CI 用）
"""

import importlib.util
import os
import sys

# 候选依赖：命中哪个就包含哪个
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


def _locate(name):
    """返回 (是否安装, 是否为包)"""
    try:
        spec = importlib.util.find_spec(name)
    except (ImportError, ValueError, AttributeError):
        # find_spec 对命名空间包、已删除模块等情况可能抛异常
        return (False, False)

    if spec is None:
        return (False, False)

    # submodule_search_locations 非空说明是包（目录），否则是单文件模块
    is_package = spec.submodule_search_locations is not None
    return (True, is_package)


def collect_flags():
    """探测已安装的模块，返回 Nuitka 参数列表"""
    flags = []
    for name in CANDIDATES:
        installed, is_package = _locate(name)
        if not installed:
            continue
        kind = "package" if is_package else "module"
        flags.append(f"--include-{kind}={name}")
    return flags


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

    print(f"[build_flags] 共包含 {len(flags)} 个模块", file=sys.stderr)


if __name__ == "__main__":
    main()
