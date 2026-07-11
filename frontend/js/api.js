const DEFAULT_TIMEOUT = 120000;

function timeoutPromise(ms) {
  return new Promise((_, reject) => {
    setTimeout(() => reject(new Error('Request timed out')), ms);
  });
}

async function request(url, options = {}, timeout = DEFAULT_TIMEOUT) {
  const controller = new AbortController();
  const signal = controller.signal;

  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(url, { ...options, signal });
    clearTimeout(timer);

    const contentType = response.headers.get('Content-Type') || '';
    const isJson = contentType.includes('application/json');
    const body = isJson ? await response.json() : await response.text();

    if (!response.ok) {
      const error = new Error(body?.message || 'Request failed');
      error.status = response.status;
      error.body = body;
      throw error;
    }

    return body;
  } catch (error) {
    clearTimeout(timer);
    if (error.name === 'AbortError') {
      throw new Error('The request timed out. Please try again.');
    }
    throw error;
  }
}

export async function postUpload(formData) {
  return request('/api/upload', {
    method: 'POST',
    body: formData,
  });
}

export async function getReport(reportId) {
  if (!reportId) {
    throw new Error('Missing report ID');
  }
  return request(`/api/report/${encodeURIComponent(reportId)}/status`, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
  });
}

export async function postChatMessage(reportId, message) {
  if (!reportId) {
    throw new Error('Missing report ID');
  }
  if (!message || !message.trim()) {
    throw new Error('Message cannot be empty');
  }
  return request(`/api/report/${encodeURIComponent(reportId)}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({ message: message.trim() }),
  });
}