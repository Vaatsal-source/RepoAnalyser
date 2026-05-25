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
    const response = await fetch(`${API_BASE_URL}/ingest`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        repository_url: repoUrl,
        repository_id: repoId,
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
 * Fires a natural language prompt to query the codebase vector layout and synthesize a response.
 * @param {string} userQuery - The conversational code exploration request string
 */
export const searchCodebase = async (userQuery) => {
  try {
    const response = await fetch(`${API_BASE_URL}/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: userQuery,
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
 * OPTIONAL ADDITION: Verifies if the Render instance is awake or spinning up
 */
export const checkBackendHealth = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/`); // Hits your FastAPI root endpoint
    return response.ok;
  } catch {
    return false;
  }
};