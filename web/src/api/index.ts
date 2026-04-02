import client from './client'

export interface WebUIPrincipal {
  user_id: string
  username: string
  role: string
  capabilities: string[]
}

export interface WebUIAccountItem {
  user_id: string
  username: string
  role: string
  is_disabled: boolean
  last_login_at: string | null
  password_changed_at: string | null
}

export interface SecurityAuditEventItem {
  event_type: string
  occurred_at: string
  actor_username: string | null
  target_username: string | null
  detail: string | null
}

export interface SettingsFieldItem {
  key: string
  label: string
  type: string
  editor: string
  item_type: string | null
  key_type: string | null
  schema: SettingsFieldSchemaItem | null
  default: unknown
  help: string
  choices: SettingsChoiceItem[]
  base_value: unknown
  current_value: unknown
  local_value: unknown
  value_source: string
  global_key: string | null
  has_local_override: boolean
  allows_null: boolean
  editable: boolean
  type_category: string
  order: number
  secret: boolean
}

export interface SettingsFieldSchemaFieldItem {
  key: string
  label: string
  help: string
  default: unknown
  schema: SettingsFieldSchemaItem
}

export interface SettingsChoiceItem {
  title: string
  value: unknown
}

export interface SettingsFieldSchemaItem {
  type: string
  item_type: string | null
  key_type: string | null
  choices: SettingsChoiceItem[]
  allows_null: boolean
  fields: SettingsFieldSchemaFieldItem[]
  item_schema: SettingsFieldSchemaFieldItem | null
  key_schema: SettingsFieldSchemaFieldItem | null
  value_schema: SettingsFieldSchemaFieldItem | null
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

export interface RawSettingsValidationResponse {
  valid: boolean
  message: string | null
  line: number | null
  column: number | null
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
  access_rules_count: number
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
  total: number
  before: number
  next_before: number | null
  has_more: boolean
}

export interface LogSourcesResponse {
  items: string[]
}

export interface LogHistoryQuery {
  before?: number
  limit?: number
  level?: string
  source?: string
  search?: string
  start?: string
  end?: string
  include_access?: boolean
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
  kind: string
  access_mode: string
  name: string | null
  description: string | null
  homepage: string | null
  source: string
  is_global_enabled: boolean
  is_protected: boolean
  protected_reason: string | null
  plugin_type: string
  admin_level: number
  author: string | null
  version: string | null
  is_loaded: boolean
  is_explicit: boolean
  is_dependency: boolean
  is_pending_uninstall: boolean
  can_edit_config: boolean
  can_view_readme: boolean
  can_enable_disable: boolean
  can_uninstall: boolean
  can_package_update: boolean
  child_plugins: string[]
  required_plugins: string[]
  dependent_plugins: string[]
  installed_package: string | null
  installed_module_names: string[]
}

export interface PluginUpdateCheckItem {
  module_name: string
  package_name: string
  current_version: string | null
  latest_version: string | null
  has_update: boolean
  checked: boolean
  error: string | null
}

export interface PluginTogglePreview {
  module_name: string
  enabled: boolean
  allowed: boolean
  summary: string
  blocked_reason: string | null
  requires_enable: string[]
  requires_disable: string[]
  protected_dependents: string[]
  missing_dependencies: string[]
}

export interface PluginToggleResult {
  module_name: string
  enabled: boolean
  affected_modules: string[]
}

export interface PluginReadmeResponse {
  module_name: string
  filename: string
  content: string
}

export interface OrphanPluginConfigItem {
  section: string
  module_name: string | null
  has_section: boolean
  reason: string
}

export interface OrphanPluginConfigResponse {
  items: OrphanPluginConfigItem[]
}

export interface PluginStoreSource {
  source_id: string
  name: string
  kind: string
  enabled: boolean
  is_builtin: boolean
  is_official: boolean
  base_url: string | null
  last_synced_at: string | null
  last_error: string | null
}

export interface PluginStoreItem {
  source_id: string
  source_name: string
  plugin_id: string
  name: string
  module_name: string
  package_name: string
  description: string | null
  project_link: string | null
  homepage: string | null
  author: string | null
  author_link: string | null
  version: string | null
  tags: string[]
  is_official: boolean
  publish_time: string | null
  extra: Record<string, unknown>
  is_installed: boolean
  is_registered: boolean
  installed_package: string | null
  installed_module_names: string[]
  can_update: boolean
}

export interface PluginStoreCategoryItem {
  value: string
  count: number
}

export interface PluginStoreItemsResponse {
  items: PluginStoreItem[]
  categories: PluginStoreCategoryItem[]
  total: number
  page: number
  per_page: number
}

export interface PluginStoreTask {
  task_id: string
  title: string
  status: string
  logs: string
  error: string | null
  result: Record<string, unknown>
  created_at: string | null
  started_at: string | null
  finished_at: string | null
}

export interface AccessRuleItem {
  subject_type: string
  subject_id: string
  plugin_module: string
  effect: string
  note: string | null
}

export interface UserLevelItem {
  user_id: string
  group_id: string
  level: number
}

export function login (payload: {
  username: string
  password: string
}) {
  return client.post<{ token: string, principal: WebUIPrincipal }>('/auth/login', payload)
}

export function register (payload: {
  registration_code: string
  username: string
  password: string
}) {
  return client.post<{ status: string, detail?: string | null }>('/auth/register', payload)
}

export function getCurrentUser () {
  return client.get<WebUIPrincipal>('/auth/me')
}

export function getCurrentAccount () {
  return client.get<WebUIAccountItem>('/auth/me/account')
}

export function changePassword (payload: {
  current_password: string
  new_password: string
}) {
  return client.post<{ status: string, detail?: string | null, token: string, principal: WebUIPrincipal }>('/auth/password', payload)
}

export function getSecurityAuditEvents () {
  return client.get<SecurityAuditEventItem[]>('/auth/audit-events')
}

export function revokeOtherSessions () {
  return client.post<{ status: string, detail?: string | null, token: string, principal: WebUIPrincipal }>('/auth/sessions/revoke-others')
}

export function getStatus () {
  return client.get<DashboardStatus>('/dashboard/status')
}

export function getDashboardEvents () {
  return client.get<{ items: DashboardEventItem[] }>('/dashboard/events')
}

export function getWebUIBuildStatus () {
  return client.get<WebUIBuildStatus>('/dashboard/webui-build')
}

export function rebuildWebUI () {
  return client.post<WebUIBuildRunResult>('/dashboard/webui-build')
}

function clearSessionAndRedirect () {
  localStorage.removeItem('token')
  localStorage.removeItem('apeiria-principal')
  window.location.href = '/login'
}

export async function streamRebuildWebUI (
  onEvent: (event: WebUIBuildStreamEvent) => void | Promise<void>,
) {
  const token = localStorage.getItem('token')
  const response = await fetch('/api/dashboard/webui-build/stream', {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  })

  if (response.status === 401 || response.status === 403) {
    clearSessionAndRedirect()
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

export function restartBot () {
  return client.post<{ status: string, detail?: string | null }>('/dashboard/restart')
}

export function getLogHistory (params?: LogHistoryQuery,
  signal?: AbortSignal) {
  return client.get<LogHistoryResponse>('/logs/history', { params, signal })
}

export function getLogSources (signal?: AbortSignal) {
  return client.get<LogSourcesResponse>('/logs/sources', { signal })
}

export function getPlugins () {
  return client.get<PluginItem[]>('/plugins/')
}

export function checkPluginUpdates (payload?: { force_refresh?: boolean }) {
  return client.post<PluginUpdateCheckItem[]>('/plugins/update-checks', payload || {})
}

export function getOrphanPluginConfigs () {
  return client.get<OrphanPluginConfigResponse>('/plugins/orphan-configs')
}

export function cleanupOrphanPluginConfigs () {
  return client.post<OrphanPluginConfigResponse>('/plugins/orphan-configs/cleanup')
}

export function installManualPlugin (payload: {
  requirement: string
  module_name?: string
}) {
  return client.post<PluginStoreTask>('/plugins/install/manual', payload)
}

export function getPluginInstallTask (taskId: string) {
  return client.get<PluginStoreTask>(`/plugins/install/tasks/${taskId}`)
}

export function updateInstalledPlugin (moduleName: string,
  payload: { package_name: string }) {
  return client.post<PluginStoreTask>(`/plugins/${moduleName}/update`, payload)
}

export function getPluginStoreSources () {
  return client.get<PluginStoreSource[]>('/plugins/store/sources')
}

export function getPluginStoreItems (params?: {
  source?: string
  search?: string
  category?: string
  sort?: string
  installed_only?: boolean
  uninstalled_only?: boolean
  page?: number
  per_page?: number
}) {
  return client.get<PluginStoreItemsResponse>('/plugins/store/items', { params })
}

export function getPluginStoreItem (sourceId: string, pluginId: string) {
  return client.get<PluginStoreItem>(`/plugins/store/items/${encodeURIComponent(sourceId)}/${encodeURIComponent(pluginId)}`)
}

export function refreshPluginStoreSources (payload?: {
  source_id?: string
}) {
  return client.post<PluginStoreSource[]>('/plugins/store/refresh', payload || {})
}

export function installPluginStoreItem (payload: {
  source_id: string
  plugin_id: string
  package_name: string
  module_name: string
}) {
  return client.post<PluginStoreTask>('/plugins/store/install', payload)
}

export function updatePluginStoreItem (payload: {
  source_id: string
  plugin_id: string
  package_name: string
  module_name: string
}) {
  return client.post<PluginStoreTask>('/plugins/store/update', payload)
}

export function getPluginStoreTask (taskId: string) {
  return client.get<PluginStoreTask>(`/plugins/store/tasks/${taskId}`)
}

export function revertPluginStoreInstall (payload: {
  package_name: string
  module_name: string
}) {
  return client.post<{ status: string }>('/plugins/store/revert-install', payload)
}

export function getCoreSettings () {
  return client.get<SettingsResponse>('/plugins/core/settings')
}

export function getCoreSettingsRaw () {
  return client.get<RawSettingsResponse>('/plugins/core/settings/raw')
}

export function updateCoreSettings (payload: {
  values: Record<string, unknown>
  clear?: string[]
}) {
  return client.patch<SettingsResponse>('/plugins/core/settings', payload)
}

export function updateCoreSettingsRaw (payload: { text: string }) {
  return client.patch<RawSettingsResponse>('/plugins/core/settings/raw', payload)
}

export function validateCoreSettingsRaw (payload: { text: string }) {
  return client.post<RawSettingsValidationResponse>('/plugins/core/settings/raw/validate', payload)
}

export function getPluginSettings (moduleName: string) {
  return client.get<SettingsResponse>(`/plugins/${moduleName}/settings`)
}

export function getPluginSettingsRaw (moduleName: string) {
  return client.get<RawSettingsResponse>(`/plugins/${moduleName}/settings/raw`)
}

export function getPluginReadme (moduleName: string) {
  return client.get<PluginReadmeResponse>(`/plugins/${moduleName}/readme`)
}

export function updatePluginSettings (moduleName: string,
  payload: {
    values: Record<string, unknown>
    clear?: string[]
  }) {
  return client.patch<SettingsResponse>(`/plugins/${moduleName}/settings`, payload)
}

export function updatePluginSettingsRaw (moduleName: string,
  payload: { text: string }) {
  return client.patch<RawSettingsResponse>(`/plugins/${moduleName}/settings/raw`, payload)
}

export function validatePluginSettingsRaw (moduleName: string,
  payload: { text: string }) {
  return client.post<RawSettingsValidationResponse>(`/plugins/${moduleName}/settings/raw/validate`, payload)
}

export function getPluginConfig () {
  return client.get<{
    modules: ModuleConfigItem[]
    dirs: DirConfigItem[]
  }>('/plugins/config')
}

export function getAdapterConfig () {
  return client.get<{ modules: ModuleConfigItem[] }>('/plugins/adapters/config')
}

export function updateAdapterConfig (payload: { modules: string[] }) {
  return client.patch<{ modules: ModuleConfigItem[] }>('/plugins/adapters/config', payload)
}

export function getDriverConfig () {
  return client.get<{ builtin: DriverConfigItem[] }>('/plugins/drivers/config')
}

export function updateDriverConfig (payload: { builtin: string[] }) {
  return client.patch<{ builtin: DriverConfigItem[] }>('/plugins/drivers/config', payload)
}

export function updatePluginConfig (payload: {
  modules: string[]
  dirs: string[]
}) {
  return client.patch<{
    modules: ModuleConfigItem[]
    dirs: DirConfigItem[]
  }>('/plugins/config', payload)
}

export function updatePlugin (moduleName: string,
  enabled: boolean,
  cascade = false) {
  return client.patch<PluginToggleResult>(`/plugins/${moduleName}`, null, {
    params: { enabled, cascade },
  })
}

export function getPluginTogglePreview (moduleName: string, enabled: boolean) {
  return client.get<PluginTogglePreview>(`/plugins/${moduleName}/toggle-preview`, {
    params: { enabled },
  })
}

export function uninstallPlugin (moduleName: string,
  payload?: { remove_config?: boolean }) {
  return client.post<{ status: string, detail?: string | null }>(
    `/plugins/${encodeURIComponent(moduleName)}/uninstall`,
    payload || {},
  )
}

export function getAccessRules () {
  return client.get<AccessRuleItem[]>('/permissions/rules')
}

export function createAccessRule (payload: {
  subject_type: string
  subject_id: string
  plugin_module: string
  effect: string
  note?: string | null
}) {
  return client.post<AccessRuleItem>('/permissions/rules', payload)
}

export function deleteAccessRule (payload: {
  subject_type: string
  subject_id: string
  plugin_module: string
}) {
  return client.post('/permissions/rules/delete', payload)
}

export function updatePluginAccessMode (moduleName: string,
  accessMode: string) {
  return client.patch('/permissions/plugins/' + encodeURIComponent(moduleName) + '/access-mode', {
    access_mode: accessMode,
  })
}

export function getUsers () {
  return client.get<UserLevelItem[]>('/permissions/users')
}

export function updateUserLevel (userId: string, groupId: string, level: number) {
  return client.patch(`/permissions/users/${userId}`, { level }, {
    params: { group_id: groupId },
  })
}
