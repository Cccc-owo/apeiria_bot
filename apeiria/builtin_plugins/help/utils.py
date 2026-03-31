from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from urllib.parse import quote

from nonebot_plugin_localstore import get_plugin_data_dir

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_DEFAULT_NONEBOT_LOGO_URL = "https://nonebot.dev/logo.png"


def get_help_data_dir() -> Path:
    data_dir = get_plugin_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_cache_dir() -> Path:
    cache_dir = get_help_data_dir() / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_custom_template_dir() -> Path:
    custom_template_dir = get_help_data_dir() / "custom_templates"
    custom_template_dir.mkdir(parents=True, exist_ok=True)
    return custom_template_dir


def get_template_dir(name: str, *, use_custom: bool) -> Path:
    if use_custom:
        custom_dir = get_custom_template_dir()
        if (custom_dir / name).is_file():
            return custom_dir
    return _TEMPLATES_DIR


def read_template(name: str, *, use_custom: bool) -> str:
    if use_custom:
        custom_path = get_custom_template_dir() / name
        if custom_path.is_file():
            return custom_path.read_text(encoding="utf-8")
    return (_TEMPLATES_DIR / name).read_text(encoding="utf-8")


def resolve_data_file(raw_path: str) -> Path | None:
    stripped = raw_path.strip()
    if not stripped:
        return None
    path = Path(stripped)
    base_dir = get_help_data_dir().resolve()
    if not path.is_absolute():
        candidate = (base_dir / path).resolve()
        if candidate.is_relative_to(base_dir) and candidate.is_file():
            return candidate
        return None
    resolved = path.resolve()
    if resolved.is_file() and resolved.is_relative_to(base_dir):
        return resolved
    return None


def read_image_as_data_uri(path: Path | None) -> str:
    if path is None or not path.is_file():
        return ""
    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "image/png"
    data = path.read_bytes()
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def build_default_icon_data_uri(seed: str) -> str:
    _ = seed
    return _DEFAULT_NONEBOT_LOGO_URL


def build_default_logo_data_uri() -> str:
    svg = """
<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 96 96">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#6fd0ff"/>
      <stop offset="100%" stop-color="#4a86ff"/>
    </linearGradient>
  </defs>
  <rect x="18" y="16" width="60" height="60" rx="20" fill="url(#g)"/>
  <rect x="30" y="31" width="36" height="8" rx="4" fill="#ffffff"/>
  <rect x="30" y="44" width="36" height="8" rx="4" fill="#ffffff" opacity="0.95"/>
  <rect x="30" y="57" width="24" height="8" rx="4" fill="#ffffff" opacity="0.9"/>
</svg>
""".strip()
    return "data:image/svg+xml;utf8," + quote(svg)


def find_plugin_icon(module_file: str | None, *, seed: str) -> str:
    if module_file:
        module_path = Path(module_file).resolve()
        candidates = [
            module_path.parent / "logo.png",
            module_path.parent / "logo.webp",
            module_path.parent / "logo.jpg",
            module_path.parent / "logo.jpeg",
            module_path.parent / "logo.svg",
        ]
        for candidate in candidates:
            data_uri = read_image_as_data_uri(candidate)
            if data_uri:
                return data_uri
    return build_default_icon_data_uri(seed)
