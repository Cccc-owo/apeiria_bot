"""Asset helpers for WebChat."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


@dataclass
class ChatAsset:
    asset_id: str
    content_type: str
    file_name: str | None = None
    local_path: Path | None = None
    remote_url: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class AssetManager:
    def __init__(self) -> None:
        self._assets: dict[str, ChatAsset] = {}
        self._asset_dir = Path("data/webui_chat/assets")
        self._asset_dir.mkdir(parents=True, exist_ok=True)

    def get(self, asset_id: str) -> ChatAsset | None:
        return self._assets.get(asset_id)

    def register_path(
        self,
        path: str | Path,
        *,
        content_type: str = "image/png",
        file_name: str | None = None,
    ) -> ChatAsset:
        asset_id = uuid4().hex
        asset = ChatAsset(
            asset_id=asset_id,
            content_type=content_type,
            file_name=file_name,
            local_path=Path(path),
        )
        self._assets[asset_id] = asset
        return asset

    def register_bytes(
        self,
        data: bytes,
        *,
        content_type: str = "image/png",
        suffix: str = ".png",
    ) -> ChatAsset:
        asset_id = uuid4().hex
        file_path = self._asset_dir / f"{asset_id}{suffix}"
        file_path.write_bytes(data)
        asset = ChatAsset(
            asset_id=asset_id,
            content_type=content_type,
            file_name=file_path.name,
            local_path=file_path,
        )
        self._assets[asset_id] = asset
        return asset
