import apiClient from './client';

const getCurrentUserId = () => {
  try {
    const saved = localStorage.getItem('vault_user');
    if (!saved) return null;
    const user = JSON.parse(saved);
    return user?.id || null;
  } catch (error) {
    return null;
  }
};

const getAuthHeaders = () => {
  const stored = localStorage.getItem('vault_user');
  if (!stored) return {};
  try {
    const user = JSON.parse(stored);
    return user?.token ? { Authorization: `Bearer ${user.token}` } : {};
  } catch {
    return {};
  }
};

const withUserScope = (params = {}) => {
  const userId = getCurrentUserId();
  if (!userId) return params;
  return { ...params, user_id: userId };
};

export const listObjects = () => apiClient.get('/objects', {
  params: withUserScope(),
  headers: getAuthHeaders(),
});

export const getObjectMetadata = (objectName) => apiClient.get(`/objects/${objectName}/metadata`, {
  params: withUserScope(),
  headers: getAuthHeaders(),
});

export const getObjectVersions = (objectName) => apiClient.get(`/objects/${objectName}/versions`, {
  params: withUserScope(),
  headers: getAuthHeaders(),
});

export const verifyObjectIntegrity = (objectName, version) => {
  const params = withUserScope(version ? { version } : {});
  const url = `/objects/${objectName}/verify`;
  return apiClient.get(url, { params, headers: getAuthHeaders() });
};

export const deleteObject = (objectName) => apiClient.delete(`/objects/${objectName}`, {
  params: withUserScope(),
  headers: getAuthHeaders(),
});

export const uploadObject = (objectName, fileOrBuffer, onUploadProgress) => {
  const config = {
    headers: {
      ...getAuthHeaders(),
      'Content-Type': fileOrBuffer.type || 'application/octet-stream',
    },
    onUploadProgress,
    params: withUserScope(),
  };
  return apiClient.put(`/objects/${objectName}`, fileOrBuffer, config);
};

export const downloadObjectUrl = (objectName, version) => {
  const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const userId = getCurrentUserId();
  const params = new URLSearchParams();
  if (userId) params.set('user_id', userId);
  if (version) params.set('version', String(version));
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return `${baseURL}/objects/${objectName}${suffix}`;
};
