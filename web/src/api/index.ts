import client from './client'

export const login = (password: string) =>
  client.post<{ token: string }>('/auth/login', { password })

export const getStatus = () =>
  client.get<{
    status: string
    uptime: number
    plugins_count: number
    disabled_plugins_count: number
    groups_count: number
    disabled_groups_count: number
    bans_count: number
    adapters: string[]
  }>('/dashboard/status')

export const restartBot = () =>
  client.post<{ status: string; detail?: string | null }>('/dashboard/restart')

export const getPlugins = () =>
  client.get<any[]>('/plugins/')

export const getPluginConfig = () =>
  client.get<{
    modules: Array<{
      name: string
      is_loaded: boolean
      is_importable: boolean
    }>
    dirs: Array<{
      path: string
      exists: boolean
      is_loaded: boolean
    }>
  }>('/plugins/config')

export const getAdapterConfig = () =>
  client.get<{
    modules: Array<{
      name: string
      is_loaded: boolean
      is_importable: boolean
    }>
  }>('/plugins/adapters/config')

export const updateAdapterConfig = (payload: {
  modules: string[]
}) =>
  client.patch<{
    modules: Array<{
      name: string
      is_loaded: boolean
      is_importable: boolean
    }>
  }>('/plugins/adapters/config', payload)

export const getDriverConfig = () =>
  client.get<{
    builtin: Array<{
      name: string
      is_active: boolean
    }>
  }>('/plugins/drivers/config')

export const updateDriverConfig = (payload: {
  builtin: string[]
}) =>
  client.patch<{
    builtin: Array<{
      name: string
      is_active: boolean
    }>
  }>('/plugins/drivers/config', payload)

export const updatePluginConfig = (payload: {
  modules: string[]
  dirs: string[]
}) =>
  client.patch<{
    modules: Array<{
      name: string
      is_loaded: boolean
      is_importable: boolean
    }>
    dirs: Array<{
      path: string
      exists: boolean
      is_loaded: boolean
    }>
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

export const getDataRecords = (table: string, page = 1, pageSize = 20) =>
  client.get<{
    table: string
    primary_key: string
    columns: string[]
    total: number
    page: number
    page_size: number
    items: Record<string, unknown>[]
  }>(`/data/${table}`, {
    params: {
      page,
      page_size: pageSize,
    },
  })

export const getDataRecord = (table: string, recordId: string) =>
  client.get<{
    table: string
    primary_key: string
    record: Record<string, unknown>
  }>(`/data/${table}/${recordId}`)

export const updateDataRecord = (
  table: string,
  recordId: string,
  values: Record<string, unknown>,
) =>
  client.patch<{
    table: string
    primary_key: string
    record: Record<string, unknown>
  }>(`/data/${table}/${recordId}`, { values })
