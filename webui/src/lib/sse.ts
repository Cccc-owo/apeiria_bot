export interface SseClientOptions {
  method?: "GET" | "POST";
  body?: unknown;
  headers?: Record<string, string>;
  autoReconnect?: boolean;
}

export interface SseClient {
  close: () => void;
  done: Promise<void>;
}

export function createSseClient(
  url: string,
  token: string,
  onMessage: (data: string) => void,
  onError?: (err: Error) => void,
  options: SseClientOptions = {},
): SseClient {
  const { method = "GET", body, headers, autoReconnect = true } = options;
  const controller = new AbortController();
  let stopped = false;
  let resolveDone!: () => void;
  let settled = false;

  const done = new Promise<void>((resolve) => {
    resolveDone = resolve;
  });

  function finish() {
    if (!settled) {
      settled = true;
      resolveDone();
    }
  }

  async function connect() {
    do {
      try {
        const response = await fetch(url, {
          method,
          headers: {
            Authorization: `Bearer ${token}`,
            ...(body !== undefined
              ? { "Content-Type": "application/json" }
              : {}),
            ...headers,
          },
          body: body === undefined ? undefined : JSON.stringify(body),
          signal: controller.signal,
        });

        if (!response.ok || !response.body) {
          throw new Error(`SSE connection failed: ${response.status}`);
        }

        const reader = response.body
          .pipeThrough(new TextDecoderStream())
          .getReader();

        let buffer = "";
        while (true) {
          const { done: readerDone, value } = await reader.read();
          if (readerDone) break;

          buffer += value;
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              onMessage(line.slice(6));
            }
          }
        }
      } catch (err: unknown) {
        if ((err as Error).name === "AbortError" || stopped) {
          finish();
          break;
        }
        onError?.(err as Error);
        if (!autoReconnect) {
          finish();
          break;
        }
      }

      if (!stopped && autoReconnect) {
        await new Promise((resolve) => setTimeout(resolve, 3000));
      } else {
        finish();
      }
    } while (!stopped && autoReconnect);
  }

  connect();

  return {
    close: () => {
      stopped = true;
      controller.abort();
      finish();
    },
    done,
  };
}
