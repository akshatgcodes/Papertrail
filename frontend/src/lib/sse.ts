// Server-sent events over fetch. EventSource can only GET, and a question with its scope
// is sent as a JSON body, so the stream is read and split into frames by hand.

export type SSEvent = { event: string; data: string };

export class SSEParser {
  private buf = "";

  feed(chunk: string): SSEvent[] {
    this.buf += chunk.replace(/\r\n?/g, "\n");
    const out: SSEvent[] = [];
    let end: number;
    while ((end = this.buf.indexOf("\n\n")) !== -1) {
      const frame = this.buf.slice(0, end);
      this.buf = this.buf.slice(end + 2);
      let event = "message";
      const data: string[] = [];
      for (const line of frame.split("\n")) {
        if (!line || line.startsWith(":")) continue; // comment / keep-alive
        const colon = line.indexOf(":");
        const field = colon === -1 ? line : line.slice(0, colon);
        let value = colon === -1 ? "" : line.slice(colon + 1);
        if (value.startsWith(" ")) value = value.slice(1);
        if (field === "event") event = value;
        else if (field === "data") data.push(value);
      }
      if (data.length) out.push({ event, data: data.join("\n") });
    }
    return out;
  }
}

/** POSTs `body` and calls onEvent for each event until the stream ends. */
export async function postStream(
  url: string,
  body: unknown,
  onEvent: (event: string, data: unknown) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
    credentials: "include",
    signal,
  });
  if (!res.ok || !res.body) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(typeof detail.detail === "string" ? detail.detail : `Request failed (${res.status})`);
  }
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  const parser = new SSEParser();
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    for (const e of parser.feed(value)) onEvent(e.event, JSON.parse(e.data));
  }
}
