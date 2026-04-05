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
        method = "POST"
        req = request.Request(
            target,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.api_key}",
            },
            method=method,
        )
        try:
            data = await asyncio.to_thread(self._perform_request, req)
        except Exception as exc:  # noqa: BLE001
            self._log_request_exception(
                exc=exc,
                method=method,
                target=target,
                elapsed_seconds=perf_counter() - started_at,
            )
            return None

        logger.info(
            "AI plugin HTTP response success: method={} url={} provider={} model={} "
            "elapsed_seconds={:.3f}",
            method,
            target,
            self.settings.provider,
            self.settings.model,
            perf_counter() - started_at,
        )
        return self._extract_content(data, method=method, target=target)

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

    def _extract_content(
        self,
        data: dict[str, object],
        *,
        method: str,
        target: str,
    ) -> str | None:
        choices = data.get("choices", [])
        if not isinstance(choices, list) or not choices:
            logger.warning(
                "AI plugin HTTP response invalid: method={} url={} provider={} "
                "model={} reason=missing_choices payload_keys={}",
                method,
                target,
                self.settings.provider,
                self.settings.model,
                sorted(data.keys()),
            )
            return None

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            logger.warning(
                "AI plugin HTTP response invalid: method={} url={} provider={} "
                "model={} reason=invalid_choice choice_type={}",
                method,
                target,
                self.settings.provider,
                self.settings.model,
                type(first_choice).__name__,
            )
            return None

        message = first_choice.get("message", {})
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            logger.warning(
                "AI plugin HTTP response invalid: method={} url={} provider={} "
                "model={} reason=missing_text_content message_keys={}",
                method,
                target,
                self.settings.provider,
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
        exc: Exception,
        method: str,
        target: str,
        elapsed_seconds: float,
    ) -> None:
        if isinstance(exc, error.HTTPError):
            logger.warning(
                "AI plugin HTTP request failed: method={} url={} provider={} "
                "model={} status={} reason={} timeout_seconds={} "
                "elapsed_seconds={:.3f} response_body={}",
                method,
                target,
                self.settings.provider,
                self.settings.model,
                exc.code,
                exc.reason,
                self.settings.timeout_seconds,
                elapsed_seconds,
                self._read_error_body(exc),
            )
            return

        reason = exc.reason if isinstance(exc, error.URLError) else str(exc)

        logger.warning(
            "AI plugin URL request failed: method={} url={} provider={} "
            "model={} reason={} error_type={} timeout_seconds={} "
            "elapsed_seconds={:.3f}",
            method,
            target,
            self.settings.provider,
            self.settings.model,
            reason,
            type(exc).__name__,
            self.settings.timeout_seconds,
            elapsed_seconds,
        )
