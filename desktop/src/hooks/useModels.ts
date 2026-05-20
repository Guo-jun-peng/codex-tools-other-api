import { useEffect, useState, useCallback } from 'react'
import { modelsApi } from '../api/models'
import type { ModelEntry, ModelForm, AdapterDefaults, TestResult } from '../types/model'

const emptyForm: ModelForm = { alias: '', target_model: '', provider: '', adapter: '', base_url: '', api_key: '', api_key_env: '', enabled: true }

export function useModels() {
  const [models, setModels] = useState<ModelEntry[]>([])
  const [adapters, setAdapters] = useState<string[]>([])
  const [adapterDefaults, setAdapterDefaults] = useState<Record<string, AdapterDefaults>>({})
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<ModelForm>({ ...emptyForm })
  const [editingAlias, setEditingAlias] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState<string | null>(null)
  const [toggling, setToggling] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<Record<string, TestResult>>({})
  const [loadError, setLoadError] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)

  const loadModels = useCallback(async () => {
    setLoadError(false)
    const r = await modelsApi.getModels()
    if (r._error) { setLoadError(true); setModels([]); return }
    const ml = r?.models || []
    setModels(ml)
    if (ml.length === 0) setLoadError(true)
    if (ml.length > 0 && ml[0]?.available_adapters) {
      setAdapters(ml[0].available_adapters)
    }
  }, [])

  useEffect(() => {
    loadModels()
    modelsApi.getAdapters().then(r => {
      if (!r._error && r.adapters) {
        const defaults: Record<string, AdapterDefaults> = {}
        r.adapters.forEach((a: any) => { defaults[a.name] = { base_url: a.base_url, api_key_env: a.api_key_env } })
        setAdapterDefaults(defaults)
      }
    })
  }, [loadModels])

  const resetForm = useCallback(() => { setForm({ ...emptyForm }); setEditingAlias(null); setShowForm(false) }, [])

  const editModel = useCallback((m: ModelEntry) => {
    setForm({
      alias: m.alias,
      target_model: m.target_model,
      provider: m.provider,
      adapter: m.adapter,
      base_url: m.base_url,
      api_key: m.api_key_hint || '',
      api_key_env: m.api_key_env,
      enabled: m.enabled,
    })
    setEditingAlias(m.alias)
    setShowForm(true)
  }, [])

  const handleAdapterChange = useCallback((adapterName: string) => {
    if (!adapterName) {
      setForm(f => ({ ...f, adapter: '', provider: '', base_url: '', api_key_env: '' }))
      return
    }
    const defaults = adapterDefaults[adapterName]
    if (defaults) {
      setForm(f => ({ ...f, adapter: adapterName, provider: adapterName, base_url: defaults.base_url, api_key_env: defaults.api_key_env }))
    } else {
      setForm(f => ({ ...f, adapter: adapterName, provider: adapterName }))
    }
  }, [adapterDefaults])

  const saveModel = useCallback(async (): Promise<string | null> => {
    if (!form.alias || !form.target_model) return '别名和目标模型为必填项'
    setSaving(true)
    const data: any = { ...form }
    if (editingAlias && data.api_key && /\*{3}/.test(data.api_key)) {
      delete data.api_key
    }
    if (!data.api_key) delete data.api_key
    const r = editingAlias ? await modelsApi.updateModel(editingAlias, data) : await modelsApi.addModel(data)
    setSaving(false)
    if (r._error) return r._error
    resetForm()
    loadModels()
    return null
  }, [form, editingAlias, resetForm, loadModels])

  const confirmDelete = useCallback(async () => {
    if (!deleteTarget) return
    const r = await modelsApi.deleteModel(deleteTarget)
    setDeleteTarget(null)
    if (r._error) return r._error
    loadModels()
    return null
  }, [deleteTarget, loadModels])

  const toggleModel = useCallback(async (alias: string) => {
    setToggling(alias)
    const r = await modelsApi.toggleModel(alias)
    setToggling(null)
    if (r._error) return r._error
    setModels(prev => prev.map(m => m.alias === alias ? { ...m, enabled: r.enabled as boolean } : m))
    return null
  }, [])

  const testModel = useCallback(async (alias: string) => {
    setTesting(alias)
    setTestResult(prev => ({ ...prev, [alias]: { status: 'testing', message: '测试中...' } }))
    const r = await modelsApi.testModel(alias)
    setTesting(null)
    if (r._error) { setTestResult(prev => ({ ...prev, [alias]: { status: 'error', message: r._error as string } })); return }
    setTestResult(prev => ({ ...prev, [alias]: r as TestResult }))
  }, [])

  const isApiKeyMasked = useCallback((value: string) => /\*{3}/.test(value), [])

  return {
    models, adapters, adapterDefaults, showForm, form, editingAlias,
    saving, testing, toggling, testResult, loadError, deleteTarget,
    setShowForm, setForm, setDeleteTarget,
    loadModels, resetForm, editModel, handleAdapterChange, saveModel,
    confirmDelete, toggleModel, testModel, isApiKeyMasked,
  }
}
