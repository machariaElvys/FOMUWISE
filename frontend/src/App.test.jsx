// @vitest-environment jsdom
import React from 'react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import App from './App.jsx';
import { getDocument } from './services/api.js';
vi.mock('./services/api.js', () => ({ getDocument: vi.fn(), uploadDocument: vi.fn(), askQuestion: vi.fn(), deleteDocument: vi.fn() }));
// The existing app uses the classic JSX runtime.
globalThis.React = React;
beforeEach(() => {
  sessionStorage.clear();
  vi.resetAllMocks();
});
afterEach(cleanup);
function saveWorkspace() {
  sessionStorage.setItem('fomuwise.activeDocumentId', 'saved');
  sessionStorage.setItem('fomuwise.documentToken.saved', 'secret');
}
test('homepage renders without an API request for a new visitor', () => {
  render(<App />);
  expect(screen.getByText('Start with the notice')).toBeTruthy();
  expect(getDocument).not.toHaveBeenCalled();
});
test('homepage stays available during a slow restore and cancels on unmount', () => {
  saveWorkspace();
  getDocument.mockReturnValue(new Promise(() => {}));
  const view = render(<App />);
  expect(screen.getByText('Start with the notice')).toBeTruthy();
  expect(screen.getByRole('status')).toBeTruthy();
  const signal = getDocument.mock.calls[0][2].signal;
  view.unmount();
  expect(signal.aborted).toBe(true);
});
test('temporary failure preserves credentials and offers retry', async () => {
  saveWorkspace();
  getDocument.mockRejectedValue(new Error('Request timed out'));
  render(<App />);
  fireEvent.click(await screen.findByText('Retry opening workspace'));
  await waitFor(() => expect(getDocument).toHaveBeenCalledTimes(2));
  expect(sessionStorage.getItem('fomuwise.documentToken.saved')).toBe('secret');
});
test.each([401, 403, 404, 410])('invalid workspace (%s) clears saved credentials', async (status) => {
  saveWorkspace();
  getDocument.mockRejectedValue(Object.assign(new Error('Expired'), { status }));
  render(<App />);
  await waitFor(() => expect(sessionStorage.getItem('fomuwise.activeDocumentId')).toBeNull());
  expect(sessionStorage.getItem('fomuwise.documentToken.saved')).toBeNull();
});
