"""安全的 .env 文件读写模块。"""

import os
import re
import tempfile
from pathlib import Path

_ENV_LINE_RE = re.compile(r"^([A-Z_][A-Z0-9_]*)=(.*)$")


def read_env(path: str = ".env") -> dict[str, str]:
    """解析 .env 为 {KEY: VALUE} 字典。"""
    result: dict[str, str] = {}
    p = Path(path)
    if not p.exists():
        return result
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _ENV_LINE_RE.match(line)
        if m:
            result[m.group(1)] = m.group(2)
    return result


def write_env(updates: dict[str, str], path: str = ".env") -> None:
    """原子更新 .env 中指定键，保留注释和顺序。"""
    p = Path(path)
    lines = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
    updated_keys: set[str] = set()
    new_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        m = _ENV_LINE_RE.match(stripped)
        if m and m.group(1) in updates:
            key = m.group(1)
            new_lines.append(f"{key}={updates[key]}")
            updated_keys.add(key)
        else:
            new_lines.append(line)

    # 追加文件中不存在的新键
    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}")

    # 原子写入
    tmp_fd, tmp_path = tempfile.mkstemp(dir=str(p.parent), suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines) + "\n")
        os.replace(tmp_path, path)
    except Exception:
        os.unlink(tmp_path)
        raise


def reload_settings():
    """重置配置单例并重新加载 .env。"""
    from dotenv import load_dotenv
    import sequoia_x.core.config as cfg_module

    cfg_module._settings = None
    load_dotenv(override=True)
    return cfg_module.get_settings()
