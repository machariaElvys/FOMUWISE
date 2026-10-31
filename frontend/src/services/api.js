const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api/v1")
  .replace(/\/+$/, "");

async function request(path, options) {
  let response;
  try {
    response = await fetch(API_BASE + path, options);
  } catch {
    throw new Error("FomuWise could not reach the backend. Check that the Flask API is running.");
  }

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = body?.error?.message || "The request could not be completed.";
    const error = new Error(message);
    error.code = body?.error?.code;
    error.status = response.status;
    throw error;
  }
  return body;
}

export function uploadDocument(file) {
  const form = new FormData();
  form.append("file", file);
  return request("/documents", { method: "POST", body: form });
}

export function getDocument(documentId, token) {
  return request("/documents/" + encodeURIComponent(documentId), {
    headers: { "X-Document-Token": token },
  });
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
