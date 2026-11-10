import { afterEach, expect, test, vi } from 'vitest';
import { getDocument } from './api.js';
afterEach(() => vi.restoreAllMocks());
test('defaults to same-origin routing and sends workspace token', async () => {
  const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ document_id: 'saved' })));
  expect(await getDocument('saved', 'secret')).toEqual({ document_id: 'saved' });
  expect(fetch).toHaveBeenCalledWith('/api/v1/documents/saved', expect.objectContaining({ headers: { 'X-Document-Token': 'secret' }, signal: expect.any(AbortSignal) }));
});
test('slow workspace request is aborted and returns a useful timeout error', async () => {
  const timeout = vi.spyOn(AbortSignal, 'timeout');
  // Use an immediate timeout rather than waiting eight seconds in the test.
  timeout.mockImplementation(() => {
    const controller = new AbortController();
    setTimeout(() => controller.abort(new DOMException('Timed out', 'TimeoutError')), 5);
    return controller.signal;
  });
  vi.spyOn(globalThis, 'fetch').mockImplementation((_url, { signal }) => new Promise((_resolve, reject) => {
    signal.addEventListener('abort', () => reject(signal.reason), { once: true });
  }));
  await expect(getDocument('saved', 'secret')).rejects.toMatchObject({ code: 'REQUEST_TIMEOUT' });
  expect(timeout).toHaveBeenCalledWith(8000);
});
test('preserves HTTP status so expired workspaces can be distinguished', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ error: { message: 'Expired' } }), { status: 410 }));
  await expect(getDocument('saved', 'secret')).rejects.toMatchObject({ status: 410, message: 'Expired' });
});
