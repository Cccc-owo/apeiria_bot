from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from urllib.parse import quote

from nonebot_plugin_localstore import get_data_dir, get_plugin_data_dir

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_LEGACY_HELP_DATA_DIR = get_data_dir("help")


def _get_standard_help_data_dir() -> Path:
    try:
        return get_plugin_data_dir()
    except RuntimeError:
        return get_data_dir("apeiria.plugins.help")


def _help_data_dirs() -> tuple[Path, ...]:
    standard_dir = _get_standard_help_data_dir()
    if standard_dir == _LEGACY_HELP_DATA_DIR:
        return (standard_dir,)
    return (standard_dir, _LEGACY_HELP_DATA_DIR)


def get_help_data_dir() -> Path:
    standard_dir, *legacy_dirs = _help_data_dirs()
    for legacy_dir in legacy_dirs:
        if legacy_dir.exists() and not standard_dir.exists():
            return legacy_dir
    standard_dir.mkdir(parents=True, exist_ok=True)
    return standard_dir


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
        for base_dir in _help_data_dirs():
            custom_dir = base_dir / "custom_templates"
            if (custom_dir / name).is_file():
                return custom_dir
    return _TEMPLATES_DIR


def read_template(name: str, *, use_custom: bool) -> str:
    if use_custom:
        for base_dir in _help_data_dirs():
            custom_path = base_dir / "custom_templates" / name
            if custom_path.is_file():
                return custom_path.read_text(encoding="utf-8")
    return (_TEMPLATES_DIR / name).read_text(encoding="utf-8")


def resolve_data_file(raw_path: str) -> Path | None:
    stripped = raw_path.strip()
    if not stripped:
        return None
    path = Path(stripped)
    if not path.is_absolute():
        for base_dir in _help_data_dirs():
            candidate = (base_dir / path).resolve()
            if candidate.is_relative_to(base_dir.resolve()) and candidate.is_file():
                return candidate
        return None
    resolved = path.resolve()
    if resolved.is_file() and any(
        resolved.is_relative_to(base_dir.resolve()) for base_dir in _help_data_dirs()
    ):
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
    svg = """
<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 96 96">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#78d7ff"/>
      <stop offset="100%" stop-color="#4a86ff"/>
    </linearGradient>
  </defs>
  <rect x="14" y="14" width="68" height="68" rx="18" fill="url(#g)"/>
  <rect x="28" y="28" width="16" height="16" rx="4" fill="#ffffff"/>
  <rect x="52" y="28" width="16" height="16" rx="4" fill="#ffffff" opacity="0.98"/>
  <rect x="28" y="52" width="16" height="16" rx="4" fill="#ffffff" opacity="0.98"/>
  <rect x="52" y="52" width="16" height="16" rx="4" fill="#ffffff" opacity="0.9"/>
  <path d="M44 36h8M36 44v8M60 44v8M44 60h8"
        stroke="#4a86ff"
        stroke-width="2.5"
        stroke-linecap="round"
        opacity="0.22"/>
</svg>
""".strip()
    return "data:image/svg+xml;utf8," + quote(svg)


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
