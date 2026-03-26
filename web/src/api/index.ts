import client from './client'

export interface WebUIPrincipal {
  user_id: string
  username: string
  role: string
}

export interface SettingsFieldItem {
  key: string
  type: string
  editor: string
  item_type: string | null
  key_type: string | null
  default: unknown
  help: string
  choices: unknown[]
  current_value: unknown
  local_value: unknown
  value_source: string
  global_key: string | null
  has_local_override: boolean
  allows_null: boolean
  editable: boolean
  type_category: string
}

export interface SettingsResponse {
  module_name: string
  section: string
  legacy_flatten: boolean
  config_source: string
  has_config_model: boolean
  fields: SettingsFieldItem[]
}

export interface RawSettingsResponse {
  module_name: string
  section: string
  text: string
}

export interface ModuleConfigItem {
  name: string
  is_loaded: boolean
  is_importable: boolean
}

export interface DirConfigItem {
  path: string
  exists: boolean
  is_loaded: boolean
}

export interface DriverConfigItem {
  name: string
  is_active: boolean
}

export interface DashboardStatus {
  status: string
  uptime: number
  plugins_count: number
  disabled_plugins_count: number
  groups_count: number
  disabled_groups_count: number
  bans_count: number
  adapters: string[]
}

export interface DashboardEventItem {
  timestamp: string
  level: string
  source: string
  message: string
}

export interface LogItem {
  timestamp: string
  level: string
  source: string
  message: string
  raw: string
  extra: Record<string, unknown>
}

export interface LogHistoryResponse {
  items: LogItem[]
  before: number
  next_before: number | null
  has_more: boolean
}

export interface WebUIBuildStatus {
  is_built: boolean
  is_stale: boolean
  can_build: boolean
  build_tool: string | null
  detail: string | null
}

export interface WebUIBuildRunResult extends WebUIBuildStatus {
  logs: string
}

export interface WebUIBuildStreamEvent {
  event: 'chunk' | 'done' | 'error'
  chunk?: string
  detail?: string | null
  status?: WebUIBuildStatus
}

export interface PluginItem {
  module_name: string
  name: string | null
  description: string | null
  source: string
  is_global_enabled: boolean
  is_protected: boolean
  protected_reason: string | null
  plugin_type: string
  admin_level: number
  author: string | null
  version: string | null
  required_plugins: string[]
  dependent_plugins: string[]
}

export const login = (payload: {
  username: string
  password: string
}) =>
  client.post<{ token: string; principal: WebUIPrincipal }>('/auth/login', payload)

export const register = (payload: {
  invite_code: string
  username: string
  password: string
}) =>
  client.post<{ status: string; detail?: string | null }>('/auth/register', payload)

export const getCurrentUser = () =>
  client.get<WebUIPrincipal>('/auth/me')

export const getStatus = () =>
  client.get<DashboardStatus>('/dashboard/status')

export const getDashboardEvents = () =>
  client.get<{ items: DashboardEventItem[] }>('/dashboard/events')

export const getWebUIBuildStatus = () =>
  client.get<WebUIBuildStatus>('/dashboard/webui-build')

export const rebuildWebUI = () =>
  client.post<WebUIBuildRunResult>('/dashboard/webui-build')

export async function streamRebuildWebUI(
  onEvent: (event: WebUIBuildStreamEvent) => void | Promise<void>,
) {
  const token = localStorage.getItem('token')
  const response = await fetch('/api/dashboard/webui-build/stream', {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  })

  if (response.status === 401) {
    localStorage.removeItem('token')
    localStorage.removeItem('apeiria-principal')
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }

  if (!response.ok) {
    const body = await response.text()
    let detail = body
    try {
      const payload = JSON.parse(body) as { detail?: string }
      detail = payload.detail || body
    } catch {
      // Keep plain-text error bodies as-is.
    }
    throw new Error(detail || 'Failed to rebuild WebUI')
  }

  if (!response.body) {
    throw new Error('Build log stream unavailable')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })

    let lineBreakIndex = buffer.indexOf('\n')
    while (lineBreakIndex >= 0) {
      const line = buffer.slice(0, lineBreakIndex).trim()
      buffer = buffer.slice(lineBreakIndex + 1)
      if (line) {
        await onEvent(JSON.parse(line) as WebUIBuildStreamEvent)
      }
      lineBreakIndex = buffer.indexOf('\n')
    }

    if (done) {
      const line = buffer.trim()
      if (line) {
        await onEvent(JSON.parse(line) as WebUIBuildStreamEvent)
      }
      break
    }
  }
}

export const restartBot = () =>
  client.post<{ status: string; detail?: string | null }>('/dashboard/restart')

export const getLogHistory = (params?: { before?: number; limit?: number }) =>
  client.get<LogHistoryResponse>('/logs/history', { params })

export const getPlugins = () =>
  client.get<PluginItem[]>('/plugins/')

export const getCoreSettings = () =>
  client.get<SettingsResponse>('/plugins/core/settings')

export const getCoreSettingsRaw = () =>
  client.get<RawSettingsResponse>('/plugins/core/settings/raw')

export const updateCoreSettings = (payload: {
  values: Record<string, unknown>
  clear?: string[]
}) =>
  client.patch<SettingsResponse>('/plugins/core/settings', payload)

export const updateCoreSettingsRaw = (payload: { text: string }) =>
  client.patch<RawSettingsResponse>('/plugins/core/settings/raw', payload)

export const getPluginSettings = (moduleName: string) =>
  client.get<SettingsResponse>(`/plugins/${moduleName}/settings`)

export const getPluginSettingsRaw = (moduleName: string) =>
  client.get<RawSettingsResponse>(`/plugins/${moduleName}/settings/raw`)

export const updatePluginSettings = (
  moduleName: string,
  payload: {
    values: Record<string, unknown>
    clear?: string[]
  },
) =>
  client.patch<SettingsResponse>(`/plugins/${moduleName}/settings`, payload)

export const updatePluginSettingsRaw = (
  moduleName: string,
  payload: { text: string },
) =>
  client.patch<RawSettingsResponse>(`/plugins/${moduleName}/settings/raw`, payload)

export const getPluginConfig = () =>
  client.get<{
    modules: ModuleConfigItem[]
    dirs: DirConfigItem[]
  }>('/plugins/config')

export const getAdapterConfig = () =>
  client.get<{ modules: ModuleConfigItem[] }>('/plugins/adapters/config')

export const updateAdapterConfig = (payload: { modules: string[] }) =>
  client.patch<{ modules: ModuleConfigItem[] }>('/plugins/adapters/config', payload)

export const getDriverConfig = () =>
  client.get<{ builtin: DriverConfigItem[] }>('/plugins/drivers/config')

export const updateDriverConfig = (payload: { builtin: string[] }) =>
  client.patch<{ builtin: DriverConfigItem[] }>('/plugins/drivers/config', payload)

export const updatePluginConfig = (payload: {
  modules: string[]
  dirs: string[]
}) =>
  client.patch<{
    modules: ModuleConfigItem[]
    dirs: DirConfigItem[]
  }>('/plugins/config', payload)

export const updatePlugin = (moduleName: string, enabled: boolean) =>
  client.patch(`/plugins/${moduleName}`, null, {
    params: { enabled },
  })

export const getBans = () =>
  client.get<any[]>('/permissions/bans')

export const createBan = (payload: {
  user_id: string
  group_id?: string | null
  duration?: number
  reason?: string | null
}) =>
  client.post('/permissions/bans', payload)

export const deleteBan = (banId: number) =>
  client.delete(`/permissions/bans/${banId}`)

export const getGroups = () =>
  client.get<any[]>('/groups/')

export const updateGroup = (groupId: string, botStatus: boolean) =>
  client.patch(`/groups/${groupId}`, null, {
    params: { bot_status: botStatus },
  })

export const updateGroupPlugins = (groupId: string, disabledPlugins: string[]) =>
  client.patch(`/groups/${groupId}/plugins`, disabledPlugins)

export const getUsers = () =>
  client.get<any[]>('/permissions/users')

export const updateUserLevel = (userId: string, groupId: string, level: number) =>
  client.patch(`/permissions/users/${userId}`, { level }, {
    params: { group_id: groupId },
  })

export const getDataTables = () =>
  client.get<{ name: string; label: string; primary_key: string }[]>('/data/')

export const getDataRecords = (table: string, page = 1, pageSize = 20, search = '') =>
  client.get<{
    table: string
    primary_key: string
    columns: string[]
    total: number
    page: number
    page_size: number
    search: string
    items: Record<string, unknown>[]
  }>(`/data/${table}`, {
    params: {
      page,
      page_size: pageSize,
      search,
    },
  })

export const getDataRecord = (table: string, recordId: string) =>
  client.get<{
    table: string
    primary_key: string
    record: Record<string, unknown>
  }>(`/data/${table}/${recordId}`)
