// 1. CRITICAL: Strip any trailing slashes from the environment variable if present
const rawUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
const API_BASE_URL = rawUrl.endsWith('/') ? rawUrl.slice(0, -1) : rawUrl;

/**
 * Streams a target Git repository into the multi-model indexing pipeline.
 * @param {string} repoUrl - The public GitHub repository clone address
 * @param {string} repoId - A unique tracking identifier string for the workspace
 */
export const ingestRepository = async (repoUrl, repoId) => {
  try {
    // FIXED: Appended missing /api prefix to match main.py router pathing
    const response = await fetch(`${API_BASE_URL}/api/ingest`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        repository_url: repoUrl.trim(),
        repository_id: repoId.trim(),
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Ingestion engine failed.');
    }

    return await response.json();
  } catch (error) {
    console.error('❌ Ingestion Network Error:', error);
    throw error;
  }
};

/**
 * Legacy synchronous codebase search.
 * @param {string} userQuery - The conversational code exploration request string
 * @param {string} repoId - The tracking identifier string for the current active workspace
 */
export const searchCodebase = async (userQuery, repoId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: userQuery.trim(),
        repository_id: repoId.trim(), // FIXED: Scopes vector search to current active repo
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Search routing failed.');
    }

    return await response.json(); // Returns: { answer: "..." }
  } catch (error) {
    console.error('❌ Search Network Error:', error);
    throw error;
  }
};

/**
 * Exposes raw stream connection channel directly to UI layouts for seamless ingestion.
 * @param {string} userQuery - The conversational code exploration request string
 * @param {string} repoId - The tracking identifier string for the current active workspace
 */
export const searchCodebaseStream = async (userQuery, repoId) => {
  // FIXED: Added repoId argument and packed it inside the body payload
  const response = await fetch(`${API_BASE_URL}/api/search/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: userQuery.trim(),
      repository_id: repoId.trim(), // FIXED: Injects active tracking context to avoid backend data leaks
    }),
  });

  if (!response.ok) {
    throw new Error('Streaming connection dropped by agent coordinator.');
  }

  return response;
};

/**
 * Verifies if the FastAPI instance is awake and running.
 */
export const checkBackendHealth = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`);
    return response.ok;
  } catch {
    return false;
  }
};
