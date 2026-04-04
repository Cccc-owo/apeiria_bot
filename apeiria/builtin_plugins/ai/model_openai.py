import asyncio
import json
from time import perf_counter
from urllib import error, request

from nonebot import logger

from .config import AIModelSettings
from .model_base import AIModelClient


class OpenAICompatibleModelClient(AIModelClient):
    def __init__(self, settings: AIModelSettings) -> None:
        self.settings = settings

    async def generate_text(self, prompt: str) -> str | None:
        if not self.settings.enabled:
            return None
        if not self.settings.base_url.strip() or not self.settings.model.strip():
            logger.warning("AI plugin model skipped because base_url/model is missing")
            return None
        if not self.settings.api_key.strip():
            logger.warning("AI plugin model skipped because api_key is missing")
            return None

        payload = {
            "model": self.settings.model,
            "messages": [
                {"role": "user", "content": prompt},
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        target = self._build_chat_completions_url()
        started_at = perf_counter()
        req = request.Request(
            target,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.api_key}",
            },
            method="POST",
        )
        try:
            data = await asyncio.to_thread(self._perform_request, req)
        except (OSError, error.HTTPError, error.URLError, json.JSONDecodeError) as exc:
            self._log_request_exception(exc, target, perf_counter() - started_at)
            return None

        return self._extract_content(data, target)

    def _perform_request(self, req: request.Request) -> dict[str, object]:
        with request.urlopen(
            req,
            timeout=self.settings.timeout_seconds,
        ) as response:
            return json.loads(response.read().decode("utf-8"))

    def _build_chat_completions_url(self) -> str:
        base_url = self.settings.base_url.strip().rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"
        return f"{base_url}/chat/completions"

    def _extract_content(self, data: dict[str, object], target: str) -> str | None:
        choices = data.get("choices", [])
        if not isinstance(choices, list) or not choices:
            logger.warning(
                "AI plugin response missing choices: url={} model={} payload_keys={}",
                target,
                self.settings.model,
                sorted(data.keys()),
            )
            return None

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            logger.warning(
                "AI plugin response invalid choice: url={} model={} choice_type={}",
                target,
                self.settings.model,
                type(first_choice).__name__,
            )
            return None

        message = first_choice.get("message", {})
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            logger.warning(
                "AI plugin response missing text content: "
                "url={} model={} message_keys={}",
                target,
                self.settings.model,
                sorted(message.keys()) if isinstance(message, dict) else [],
            )
            return None
        return content.strip()

    def _read_error_body(self, exc: error.HTTPError) -> str:
        try:
            body = exc.read().decode("utf-8", errors="replace").strip()
        except OSError:
            return ""
        if not body:
            return ""
        return body[:500]

    def _log_request_exception(
        self,
        exc: OSError | error.HTTPError | error.URLError | json.JSONDecodeError,
        target: str,
        elapsed_seconds: float,
    ) -> None:
        details = (
            f"url={target} model={self.settings.model} "
            f"timeout_seconds={self.settings.timeout_seconds} "
            f"elapsed_seconds={elapsed_seconds:.3f}"
        )
        if isinstance(exc, error.HTTPError):
            logger.warning(
                "AI plugin HTTP request failed: "
                "status={} reason={} {} response_body={}",
                exc.code,
                exc.reason,
                details,
                self._read_error_body(exc),
            )
            return
        logger.warning(
            "AI plugin request failed: error_type={} error={} {}",
            type(exc).__name__,
            exc,
            details,
        )
