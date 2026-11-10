const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api/v1")
  .replace(/\/+$/, "");

async function request(path, options = {}, timeoutMs = 120000) {
  const signal = options.signal
    ? AbortSignal.any([options.signal, AbortSignal.timeout(timeoutMs)])
    : AbortSignal.timeout(timeoutMs);
  try {
    const response = await fetch(API_BASE + path, { ...options, signal });
    const body = await response.json().catch((error) => {
      if (signal.aborted) throw error;
      return {};
    });
    if (!response.ok) {
      const error = new Error(body?.error?.message || "The request could not be completed.");
      error.code = body?.error?.code;
      error.status = response.status;
      throw error;
    }
    return body;
  } catch (error) {
    if (signal.aborted) {
      if (options.signal?.aborted) throw error;
      const timeoutError = new Error("The server took too long to respond. Please try again.");
      timeoutError.code = "REQUEST_TIMEOUT";
      throw timeoutError;
    }
    if (error.status) throw error;
    throw new Error("FomuWise could not reach the backend. Please check your connection and try again.");
  }
}

export function uploadDocument(file) {
  const form = new FormData();
  form.append("file", file);
  return request("/documents", { method: "POST", body: form });
}

export function getDocument(documentId, token, { signal } = {}) {
  return request("/documents/" + encodeURIComponent(documentId), {
    headers: { "X-Document-Token": token },
    signal,
  }, 8000);
}

export function askQuestion(documentId, token, question) {
  return request("/documents/" + encodeURIComponent(documentId) + "/questions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Document-Token": token,
    },
    body: JSON.stringify({ question }),
  });
}

export function deleteDocument(documentId, token) {
  return request("/documents/" + encodeURIComponent(documentId), {
    method: "DELETE",
    headers: { "X-Document-Token": token },
  });
}
