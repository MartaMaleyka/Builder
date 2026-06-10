const API = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return null;
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) return res.json();
  return res;
}

export async function sendMessage(sessionId, message) {
  return request("/clarify", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, message }),
  });
}

export async function generatePRD(sessionId) {
  return request("/prd/generate", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
  });
}

export async function getPRD(sessionId) {
  return request(`/prd/${sessionId}`);
}

export async function approvePRD(sessionId, prd) {
  await request("/prd/approve", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      approved: true,
      edited_prd: prd,
    }),
  });
}

export async function rejectPRD(sessionId) {
  await request("/prd/approve", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, approved: false }),
  });
}

export async function startCodeGen(sessionId) {
  await request("/code/generate", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
  });
}

export async function getCodeStatus(sessionId) {
  return request(`/code/status/${sessionId}`);
}

export async function downloadZip(sessionId) {
  const res = await fetch(`${API}/code/download/${sessionId}`);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Download failed: ${res.status}`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${sessionId}-project.zip`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
