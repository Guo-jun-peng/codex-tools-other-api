import { fetchApi } from './client'
import type { ProxyStatus } from '../types/status'

export const statusApi = {
  getStatus: () =>
    fetchApi<ProxyStatus>('/status'),
}
