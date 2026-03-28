# Render Plugin

Chinese version: [README_zh-CN.md](./README_zh-CN.md)

## Usage

Recommended convenience APIs:

- `html_to_pic(...)`
- `template_to_pic(...)`
- `url_to_pic(...)`
- `markdown_to_pic(...)`

Lower-level APIs:

- `RenderOptions`
- `render_html(...)`
- `render_template(...)`
- `render_url(...)`
- `get_render_service()`
- `get_render_status()`

## Example

```python
from pathlib import Path

from apeiria.plugins.render import html_to_pic, markdown_to_pic, template_to_pic

template_dir = Path(__file__).parent / "templates"


async def render_html_card() -> bytes:
    return await html_to_pic(
        "<div id='card'>hello</div>",
        width=480,
        selector="#card",
        inline_style=(
            "body{margin:0;padding:24px;background:#111827;}"
            "#card{padding:20px;border-radius:16px;background:#2563eb;color:#fff;}"
        ),
    )


async def render_template_card(data: dict[str, object]) -> bytes:
    return await template_to_pic(
        "card.html",
        template_dir=template_dir,
        context=data,
        width=720,
        selector="body",
    )


async def render_markdown_card() -> bytes:
    return await markdown_to_pic(
        "# Title\n\n- item 1\n- item 2\n\n`code`",
        width=720,
    )
```

## Notes

- Browser warmup starts asynchronously during startup by default.
- Relative asset paths can be resolved with `base_url=...`.
- Wait for short animations with `settle_time_ms=...`.
