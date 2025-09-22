import { api, apiFetch } from './apiClient'; // added

// Agent chat API helpers (non-stream + streaming)
export const askAgent = async (payload) => {
  const res = await api.post('/api/agent/ask', { ...payload, stream: false });
  if (!res || !res.data) throw new Error('askAgent failed (no data)');
  return res.data;
};

/**
 * Stream agent response (SSE over POST body via fetch + ReadableStream).
 * handlers: { onChunk(text, rawChunk), onComplete(finalText, meta), onError(err) }
 * Returns: () => abort()
 */
export const streamAgent = (payload, handlers = {}) => {
  const controller = new AbortController();
  const { onComplete, onError } = handlers;
  let cumulativeText = '';
  let completeSeen = false;

  const parseAndEmit = (dataLine) => {
    try {
      const chunk = JSON.parse(dataLine);
      const incoming = (chunk.response ?? '').replace(/\r/g, '');
      if (!incoming) return;
      if (incoming === 'Processing your request...' && !chunk.complete) return;

      // Incoming is always treated as cumulative snapshot
      if (incoming !== cumulativeText) {
        cumulativeText = incoming;
        handlers.onChunk && handlers.onChunk(cumulativeText, chunk);
      }

      if (chunk.complete && !completeSeen) {
        completeSeen = true;
        handlers.onComplete && handlers.onComplete(cumulativeText, chunk);
      }
    } catch {
      /* ignore */
    }
  };

  (async () => {
    try {
      const res = await apiFetch('/api/agent/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          'Cache-Control': 'no-cache'
        },
        body: JSON.stringify({ ...payload, stream: true }),
        signal: controller.signal
      });
      if (!res.ok || !res.body) throw new Error(`streamAgent failed (${res.status})`);
      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let idx;
        while ((idx = buffer.indexOf('\n\n')) >= 0) {
          const raw = buffer.slice(0, idx).trim();
          buffer = buffer.slice(idx + 2);
          if (raw.startsWith('data:')) {
            parseAndEmit(raw.replace(/^data:\s*/, ''));
          }
        }
      }
      if (buffer.trim().startsWith('data:')) {
        parseAndEmit(buffer.trim().replace(/^data:\s*/, ''));
      }
      if (!completeSeen) onComplete && onComplete(cumulativeText, { complete: true });
    } catch (err) {
      if (!controller.signal.aborted) onError && onError(err);
    }
  })();

  return () => controller.abort();
};