import { fetchApi } from './client'
import type { ModelEntry, AdapterInfo, TestResult } from '../types/model'

export const modelsApi = {
  getModels: () =>
    fetchApi<{ models: ModelEntry[] }>('/models'),

  getAdapters: () =>
    fetchApi<{ adapters: AdapterInfo[] }>('/adapters'),

  addModel: (data: Record<string, unknown>) =>
    fetchApi<{ status: string; alias: string }>('/models', {
      method: 'POST', body: JSON.stringify(data),
    }),

  updateModel: (alias: string, data: Record<string, unknown>) =>
    fetchApi<{ status: string; alias: string }>(
      `/models/${encodeURIComponent(alias)}`,
      { method: 'PUT', body: JSON.stringify(data) },
    ),

  deleteModel: (alias: string) =>
    fetchApi<{ status: string }>(
      `/models/${encodeURIComponent(alias)}`,
      { method: 'DELETE' },
    ),

  toggleModel: (alias: string) =>
    fetchApi<{ status: string; alias: string; enabled: boolean }>(
      `/models/${encodeURIComponent(alias)}/toggle`,
      { method: 'PUT' },
    ),

  testModel: (alias: string, data?: Record<string, unknown>) =>
    fetchApi<TestResult>(
      `/models/${encodeURIComponent(alias)}/test`,
      { method: 'POST', body: JSON.stringify(data || {}) },
    ),
}
