import apiClient from './client';

export async function getAppVersion(): Promise<string> {
  const { data } = await apiClient.get<{ version: string }>('/health');
  return data.version;
}
