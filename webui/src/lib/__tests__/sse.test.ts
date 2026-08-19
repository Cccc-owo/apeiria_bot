import { afterEach, describe, expect, it, vi } from "vitest";
import { createSseClient } from "../sse";

function sseResponse(chunks: string[], init: ResponseInit = {}): Response {
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(new TextEncoder().encode(chunk));
      }
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
    ...init,
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("createSseClient", () => {
  it("parses data lines and resolves done for one-shot streams", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(sseResponse(['data: {"a":1}\n\n']));
    vi.stubGlobal("fetch", fetchMock);

    const messages: string[] = [];
    const client = createSseClient(
      "/sse",
      "token",
      (data) => {
        messages.push(data);
      },
      undefined,
      { autoReconnect: false },
    );

    await client.done;

    expect(messages).toEqual(['{"a":1}']);
    expect(fetchMock).toHaveBeenCalledWith(
      "/sse",
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({
          Authorization: "Bearer token",
        }),
      }),
    );
  });

  it("sends POST body and content type when configured", async () => {
    const fetchMock = vi.fn().mockResolvedValue(sseResponse(["data: ok\n\n"]));
    vi.stubGlobal("fetch", fetchMock);

    const client = createSseClient(
      "/api/update",
      "token",
      () => {},
      undefined,
      {
        method: "POST",
        body: { branch: "main", type: "branch" },
        autoReconnect: false,
      },
    );

    await client.done;

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/update",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          "Content-Type": "application/json",
          Authorization: "Bearer token",
        }),
        body: JSON.stringify({ branch: "main", type: "branch" }),
      }),
    );
  });

  it("calls onError and resolves done on failed responses", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(null, { status: 500 }));
    vi.stubGlobal("fetch", fetchMock);

    const errors: Error[] = [];
    const client = createSseClient(
      "/sse",
      "token",
      () => {},
      (err) => {
        errors.push(err);
      },
      { autoReconnect: false },
    );

    await client.done;

    expect(errors).toHaveLength(1);
    expect(errors[0].message).toContain("500");
  });

  it("close resolves done and stops waiting for fetch", async () => {
    let resolveFetch: ((response: Response) => void) | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(
        () =>
          new Promise<Response>((resolve) => {
            resolveFetch = resolve;
          }),
      ),
    );

    const client = createSseClient("/sse", "token", () => {});
    client.close();

    await client.done;
    expect(resolveFetch).toBeDefined();
  });
});
