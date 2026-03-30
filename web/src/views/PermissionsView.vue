<template>
  <div class="permission-workbench">
    <div class="permission-workbench__header">
      <div>
        <h1 class="page-title">{{ t('permissions.title') }}</h1>
      </div>
      <v-btn :loading="loading" variant="tonal" @click="loadAll">{{ t('common.refresh') }}</v-btn>
    </div>

    <v-alert v-if="errorMessage" density="comfortable" type="error" variant="tonal">
      {{ errorMessage }}
    </v-alert>

    <div class="permission-perspectives">
      <button
        v-for="item in perspectiveItems"
        :key="item.value"
        class="permission-perspective"
        :class="{ 'permission-perspective--active': perspective === item.value }"
        type="button"
        @click="perspective = item.value"
      >
        <span class="permission-perspective__label">{{ item.title }}</span>
        <span class="permission-perspective__meta">{{ item.meta }}</span>
      </button>
    </div>

    <template v-if="perspective === 'plugins'">
      <div class="permission-layout">
        <section class="permission-sidebar">
          <v-text-field
            v-model="pluginSearch"
            class="permission-sidebar__search"
            clearable
            density="compact"
            hide-details
            :placeholder="t('permissions.searchPlugins')"
            prepend-inner-icon="mdi-magnify"
            single-line
            variant="outlined"
          />

          <div class="permission-sidebar__list">
            <button
              v-for="item in visiblePlugins"
              :key="item.module_name"
              class="permission-sidebar__item"
              :class="{ 'permission-sidebar__item--active': item.module_name === selectedPluginModule }"
              type="button"
              @click="selectedPluginModule = item.module_name"
            >
              <div class="permission-sidebar__item-main">
                <span class="permission-sidebar__item-title">{{ item.name || item.module_name }}</span>
                <span class="permission-sidebar__item-subtitle">{{ item.module_name }}</span>
              </div>
              <div class="permission-sidebar__item-tags">
                <v-chip
                  v-if="!item.is_global_enabled"
                  color="warning"
                  size="x-small"
                  variant="tonal"
                >
                  {{ t('permissions.globalOff') }}
                </v-chip>
                <v-chip
                  v-if="item.is_protected"
                  color="error"
                  size="x-small"
                  variant="tonal"
                >
                  {{ t('permissions.protected') }}
                </v-chip>
                <v-chip
                  v-if="pluginRuleCount(item.module_name) > 0"
                  color="primary"
                  size="x-small"
                  variant="tonal"
                >
                  {{ pluginRuleCount(item.module_name) }}
                </v-chip>
              </div>
            </button>
          </div>
        </section>

        <section v-if="selectedPlugin" class="permission-main">
          <div class="permission-panel permission-panel--hero">
            <div class="permission-panel__hero-main">
              <div class="permission-panel__title">{{ selectedPlugin.name || selectedPlugin.module_name }}</div>
              <div class="permission-panel__subtitle">{{ selectedPlugin.module_name }}</div>
            </div>
            <div class="permission-panel__hero-stats">
              <div class="permission-inline-stat permission-inline-stat--control">
                <span class="permission-inline-stat__label">{{ t('permissions.accessMode') }}</span>
                <v-select
                  class="permission-access-mode"
                  density="compact"
                  hide-details
                  item-title="title"
                  item-value="value"
                  :items="accessModeOptions"
                  :loading="pendingPluginAccessMode"
                  :model-value="selectedPlugin.access_mode"
                  @update:model-value="updateSelectedPluginAccessMode"
                />
              </div>
              <div class="permission-inline-stat">
                <span class="permission-inline-stat__label">{{ t('permissions.explicitRules') }}</span>
                <span class="permission-inline-stat__value">{{ selectedPluginRules.length }}</span>
              </div>
              <div class="permission-inline-stat">
                <span class="permission-inline-stat__label">{{ t('permissions.disabledInGroups') }}</span>
                <span class="permission-inline-stat__value">{{ groupsWithPluginDisabled.length }}</span>
              </div>
              <div class="permission-inline-stat">
                <span class="permission-inline-stat__label">{{ t('permissions.groupsWithBotOff') }}</span>
                <span class="permission-inline-stat__value">{{ groupsWithBotDisabled.length }}</span>
              </div>
            </div>
          </div>

          <div class="permission-grid">
            <v-card class="permission-panel">
              <v-card-title>{{ t('permissions.userRules') }}</v-card-title>
              <v-card-text class="permission-rule-columns">
                <div>
                  <div class="permission-section-title">{{ t('permissions.allow') }}</div>
                  <div v-if="selectedPluginUserAllowRules.length" class="permission-rule-list">
                    <div
                      v-for="rule in selectedPluginUserAllowRules"
                      :key="ruleKey(rule)"
                      class="permission-rule-row"
                    >
                      <div>
                        <div class="font-weight-medium">{{ rule.subject_id }}</div>
                        <div class="text-caption text-medium-emphasis">{{ rule.note || t('permissions.noNote') }}</div>
                      </div>
                      <v-btn icon="mdi-delete" size="small" variant="text" @click="handleDeleteRule(rule)" />
                    </div>
                  </div>
                  <div v-else class="permission-empty">{{ t('permissions.noRules') }}</div>
                </div>
                <div>
                  <div class="permission-section-title">{{ t('permissions.deny') }}</div>
                  <div v-if="selectedPluginUserDenyRules.length" class="permission-rule-list">
                    <div
                      v-for="rule in selectedPluginUserDenyRules"
                      :key="ruleKey(rule)"
                      class="permission-rule-row"
                    >
                      <div>
                        <div class="font-weight-medium">{{ rule.subject_id }}</div>
                        <div class="text-caption text-medium-emphasis">{{ rule.note || t('permissions.noNote') }}</div>
                      </div>
                      <v-btn icon="mdi-delete" size="small" variant="text" @click="handleDeleteRule(rule)" />
                    </div>
                  </div>
                  <div v-else class="permission-empty">{{ t('permissions.noRules') }}</div>
                </div>
              </v-card-text>
            </v-card>

            <v-card class="permission-panel">
              <v-card-title>{{ t('permissions.groupRules') }}</v-card-title>
              <v-card-text class="permission-rule-columns">
                <div>
                  <div class="permission-section-title">{{ t('permissions.allow') }}</div>
                  <div v-if="selectedPluginGroupAllowRules.length" class="permission-rule-list">
                    <div
                      v-for="rule in selectedPluginGroupAllowRules"
                      :key="ruleKey(rule)"
                      class="permission-rule-row"
                    >
                      <div>
                        <div class="font-weight-medium">{{ rule.subject_id }}</div>
                        <div class="text-caption text-medium-emphasis">{{ rule.note || t('permissions.noNote') }}</div>
                      </div>
                      <v-btn icon="mdi-delete" size="small" variant="text" @click="handleDeleteRule(rule)" />
                    </div>
                  </div>
                  <div v-else class="permission-empty">{{ t('permissions.noRules') }}</div>
                </div>
                <div>
                  <div class="permission-section-title">{{ t('permissions.deny') }}</div>
                  <div v-if="selectedPluginGroupDenyRules.length" class="permission-rule-list">
                    <div
                      v-for="rule in selectedPluginGroupDenyRules"
                      :key="ruleKey(rule)"
                      class="permission-rule-row"
                    >
                      <div>
                        <div class="font-weight-medium">{{ rule.subject_id }}</div>
                        <div class="text-caption text-medium-emphasis">{{ rule.note || t('permissions.noNote') }}</div>
                      </div>
                      <v-btn icon="mdi-delete" size="small" variant="text" @click="handleDeleteRule(rule)" />
                    </div>
                  </div>
                  <div v-else class="permission-empty">{{ t('permissions.noRules') }}</div>
                </div>
              </v-card-text>
            </v-card>
          </div>

          <v-card class="permission-panel">
            <v-card-title>{{ t('permissions.createRuleTitle') }}</v-card-title>
            <v-card-text class="permission-form-grid">
              <v-select
                v-model="pluginRuleForm.subject_type"
                density="comfortable"
                hide-details
                :items="subjectTypeOptions"
                :label="t('permissions.subjectType')"
              />
              <v-text-field
                v-model="pluginRuleForm.subject_id"
                density="comfortable"
                hide-details
                :label="t('permissions.subjectId')"
                :placeholder="pluginRuleForm.subject_type === 'group' ? t('permissions.groupIdPlaceholder') : t('permissions.userIdPlaceholder')"
              />
              <v-select
                v-model="pluginRuleForm.effect"
                density="comfortable"
                hide-details
                :items="effectOptions"
                :label="t('permissions.effect')"
              />
              <v-text-field
                v-model="pluginRuleForm.note"
                density="comfortable"
                hide-details
                :label="t('permissions.note')"
              />
              <div class="permission-form-grid__actions">
                <v-btn
                  color="primary"
                  :disabled="!pluginRuleForm.subject_id.trim()"
                  :loading="creatingRule"
                  @click="createRuleForPlugin"
                >
                  {{ t('permissions.createRule') }}
                </v-btn>
              </div>
            </v-card-text>
          </v-card>

          <div v-if="groupsWithPluginDisabled.length || groupsWithBotDisabled.length" class="permission-grid">
            <v-card v-if="groupsWithPluginDisabled.length" class="permission-panel">
              <v-card-title>{{ t('permissions.disabledInGroups') }}</v-card-title>
              <v-card-text>
                <div class="permission-chip-list">
                  <v-chip
                    v-for="group in groupsWithPluginDisabled"
                    :key="group.group_id"
                    color="warning"
                    variant="tonal"
                  >
                    {{ group.group_name || group.group_id }}
                  </v-chip>
                </div>
              </v-card-text>
            </v-card>

            <v-card v-if="groupsWithBotDisabled.length" class="permission-panel">
              <v-card-title>{{ t('permissions.groupsWithBotOff') }}</v-card-title>
              <v-card-text>
                <div class="permission-chip-list">
                  <v-chip
                    v-for="group in groupsWithBotDisabled"
                    :key="group.group_id"
                    color="warning"
                    variant="tonal"
                  >
                    {{ group.group_name || group.group_id }}
                  </v-chip>
                </div>
              </v-card-text>
            </v-card>
          </div>
        </section>
      </div>
    </template>

    <template v-else-if="perspective === 'groups'">
      <div class="permission-layout">
        <section class="permission-sidebar">
          <v-text-field
            v-model="groupSearch"
            class="permission-sidebar__search"
            clearable
            density="compact"
            hide-details
            :placeholder="t('permissions.searchGroups')"
            prepend-inner-icon="mdi-magnify"
            single-line
            variant="outlined"
          />

          <div class="permission-sidebar__list">
            <button
              v-for="item in visibleGroups"
              :key="item.group_id"
              class="permission-sidebar__item"
              :class="{ 'permission-sidebar__item--active': item.group_id === selectedGroupId }"
              type="button"
              @click="selectGroup(item.group_id)"
            >
              <div class="permission-sidebar__item-main">
                <span class="permission-sidebar__item-title">{{ item.group_name || item.group_id }}</span>
                <span class="permission-sidebar__item-subtitle">{{ item.group_id }}</span>
              </div>
              <div class="permission-sidebar__item-tags">
                <v-chip :color="item.bot_status ? 'success' : 'warning'" size="x-small" variant="tonal">
                  {{ item.bot_status ? t('permissions.botOn') : t('permissions.botOff') }}
                </v-chip>
              </div>
            </button>
          </div>
        </section>

        <section v-if="selectedGroup" class="permission-main">
          <div class="permission-panel permission-panel--hero">
            <div>
              <div class="permission-panel__eyebrow">{{ t('permissions.groupView') }}</div>
              <div class="permission-panel__title">{{ selectedGroup.group_name || selectedGroup.group_id }}</div>
              <div class="permission-panel__subtitle">{{ selectedGroup.group_id }}</div>
            </div>
            <v-switch
              color="success"
              hide-details
              inset
              :loading="pendingGroupBot"
              :model-value="selectedGroup.bot_status"
              @update:model-value="updateSelectedGroupBot($event)"
            />
          </div>

          <div class="permission-grid">
            <v-card class="permission-panel">
              <v-card-title>{{ t('permissions.groupPluginSwitches') }}</v-card-title>
              <v-card-text class="permission-stack">
                <v-autocomplete
                  v-model="selectedGroupDisabledPluginsDraft"
                  chips
                  closable-chips
                  density="comfortable"
                  item-title="title"
                  item-value="value"
                  :items="pluginModuleOptions"
                  :label="t('permissions.disabledPlugins')"
                  multiple
                />
                <div class="permission-form-grid__actions">
                  <v-btn
                    color="primary"
                    :disabled="!hasPendingGroupPluginChanges"
                    :loading="pendingGroupPlugins"
                    @click="saveSelectedGroupPlugins"
                  >
                    {{ t('common.save') }}
                  </v-btn>
                </div>
              </v-card-text>
            </v-card>

            <v-card class="permission-panel">
              <v-card-title>{{ t('permissions.createRuleTitle') }}</v-card-title>
              <v-card-text class="permission-form-grid">
                <v-select
                  v-model="groupRuleForm.effect"
                  density="comfortable"
                  hide-details
                  :items="effectOptions"
                  :label="t('permissions.effect')"
                />
                <v-autocomplete
                  v-model="groupRuleForm.plugin_module"
                  clearable
                  density="comfortable"
                  hide-details
                  item-title="title"
                  item-value="value"
                  :items="pluginModuleOptions"
                  :label="t('permissions.pluginModule')"
                />
                <v-text-field
                  v-model="groupRuleForm.note"
                  density="comfortable"
                  hide-details
                  :label="t('permissions.note')"
                />
                <div class="permission-form-grid__actions">
                  <v-btn
                    color="primary"
                    :disabled="!groupRuleForm.plugin_module.trim()"
                    :loading="creatingRule"
                    @click="createRuleForGroup"
                  >
                    {{ t('permissions.createRule') }}
                  </v-btn>
                </div>
              </v-card-text>
            </v-card>
          </div>

          <div class="permission-grid">
            <v-card class="permission-panel">
              <v-card-title>{{ t('permissions.groupRules') }}</v-card-title>
              <v-card-text class="permission-rule-list">
                <div
                  v-for="rule in selectedGroupRules"
                  :key="ruleKey(rule)"
                  class="permission-rule-row"
                >
                  <div>
                    <div class="font-weight-medium">{{ rule.plugin_module }}</div>
                    <div class="text-caption text-medium-emphasis">
                      {{ rule.effect === 'allow' ? t('permissions.allow') : t('permissions.deny') }}
                    </div>
                  </div>
                  <v-btn icon="mdi-delete" size="small" variant="text" @click="handleDeleteRule(rule)" />
                </div>
                <div v-if="!selectedGroupRules.length" class="permission-empty">{{ t('permissions.noRules') }}</div>
              </v-card-text>
            </v-card>

            <v-card class="permission-panel">
              <v-card-title>{{ t('permissions.groupUserLevels') }}</v-card-title>
              <v-card-text class="permission-rule-list">
                <div
                  v-for="entry in selectedGroupUsers"
                  :key="`${entry.user_id}:${entry.group_id}`"
                  class="permission-rule-row"
                >
                  <div class="font-weight-medium">{{ entry.user_id }}</div>
                  <v-select
                    class="permission-level-select"
                    density="compact"
                    hide-details
                    :items="levelOptions"
                    :model-value="entry.level"
                    @update:model-value="updateLevel(entry, $event)"
                  />
                </div>
                <div v-if="!selectedGroupUsers.length" class="permission-empty">{{ t('permissions.noUsers') }}</div>
              </v-card-text>
            </v-card>
          </div>
        </section>
      </div>
    </template>

    <template v-else-if="perspective === 'users'">
      <div class="permission-layout">
        <section class="permission-sidebar">
          <v-text-field
            v-model="userSearch"
            class="permission-sidebar__search"
            clearable
            density="compact"
            hide-details
            :placeholder="t('permissions.searchUsers')"
            prepend-inner-icon="mdi-magnify"
            single-line
            variant="outlined"
          />

          <div class="permission-sidebar__list">
            <button
              v-for="item in visibleUserEntries"
              :key="item.user_id"
              class="permission-sidebar__item"
              :class="{ 'permission-sidebar__item--active': item.user_id === selectedUserId }"
              type="button"
              @click="selectedUserId = item.user_id"
            >
              <div class="permission-sidebar__item-main">
                <span class="permission-sidebar__item-title">{{ item.user_id }}</span>
                <span class="permission-sidebar__item-subtitle">
                  {{ t('permissions.userGroupsMeta', { count: item.groups }) }}
                </span>
              </div>
              <div class="permission-sidebar__item-tags">
                <v-chip v-if="item.rules > 0" color="primary" size="x-small" variant="tonal">
                  {{ item.rules }}
                </v-chip>
              </div>
            </button>
          </div>
        </section>

        <section v-if="selectedUserId" class="permission-main">
          <div class="permission-panel permission-panel--hero">
            <div>
              <div class="permission-panel__eyebrow">{{ t('permissions.userView') }}</div>
              <div class="permission-panel__title">{{ selectedUserId }}</div>
              <div class="permission-panel__subtitle">{{ t('permissions.userRulesAndLevels') }}</div>
            </div>
          </div>

          <div class="permission-grid">
            <v-card class="permission-panel">
              <v-card-title>{{ t('permissions.createRuleTitle') }}</v-card-title>
              <v-card-text class="permission-form-grid">
                <v-select
                  v-model="userRuleForm.effect"
                  density="comfortable"
                  hide-details
                  :items="effectOptions"
                  :label="t('permissions.effect')"
                />
                <v-autocomplete
                  v-model="userRuleForm.plugin_module"
                  clearable
                  density="comfortable"
                  hide-details
                  item-title="title"
                  item-value="value"
                  :items="pluginModuleOptions"
                  :label="t('permissions.pluginModule')"
                />
                <v-text-field
                  v-model="userRuleForm.note"
                  density="comfortable"
                  hide-details
                  :label="t('permissions.note')"
                />
                <div class="permission-form-grid__actions">
                  <v-btn
                    color="primary"
                    :disabled="!userRuleForm.plugin_module.trim()"
                    :loading="creatingRule"
                    @click="createRuleForUser"
                  >
                    {{ t('permissions.createRule') }}
                  </v-btn>
                </div>
              </v-card-text>
            </v-card>

            <v-card class="permission-panel">
              <v-card-title>{{ t('permissions.userRules') }}</v-card-title>
              <v-card-text class="permission-rule-list">
                <div
                  v-for="rule in selectedUserRules"
                  :key="ruleKey(rule)"
                  class="permission-rule-row"
                >
                  <div>
                    <div class="font-weight-medium">{{ rule.plugin_module }}</div>
                    <div class="text-caption text-medium-emphasis">
                      {{ rule.effect === 'allow' ? t('permissions.allow') : t('permissions.deny') }}
                    </div>
                  </div>
                  <v-btn icon="mdi-delete" size="small" variant="text" @click="handleDeleteRule(rule)" />
                </div>
                <div v-if="!selectedUserRules.length" class="permission-empty">{{ t('permissions.noRules') }}</div>
              </v-card-text>
            </v-card>
          </div>

          <v-card class="permission-panel">
            <v-card-title>{{ t('permissions.userLevels') }}</v-card-title>
            <v-card-text class="permission-rule-list">
              <div
                v-for="entry in selectedUserLevels"
                :key="`${entry.user_id}:${entry.group_id}`"
                class="permission-rule-row"
              >
                <div>
                  <div class="font-weight-medium">{{ entry.group_id }}</div>
                  <div class="text-caption text-medium-emphasis">{{ groupNameById(entry.group_id) }}</div>
                </div>
                <v-select
                  class="permission-level-select"
                  density="compact"
                  hide-details
                  :items="levelOptions"
                  :model-value="entry.level"
                  @update:model-value="updateLevel(entry, $event)"
                />
              </div>
              <div v-if="!selectedUserLevels.length" class="permission-empty">{{ t('permissions.noUsers') }}</div>
            </v-card-text>
          </v-card>
        </section>
      </div>
    </template>

    <template v-else>
      <v-card class="permission-panel">
        <v-card-title>{{ t('permissions.rulesView') }}</v-card-title>
        <v-card-text class="permission-stack">
          <div class="permission-filters">
            <v-text-field
              v-model="ruleSearch"
              clearable
              density="comfortable"
              hide-details
              :label="t('permissions.searchRules')"
              prepend-inner-icon="mdi-magnify"
            />
            <v-select
              v-model="ruleEffectFilter"
              density="comfortable"
              hide-details
              :items="ruleEffectOptions"
              :label="t('permissions.effect')"
            />
          </div>

          <v-data-table
            density="comfortable"
            :headers="ruleHeaders"
            :items="filteredRules"
            :loading="loading"
          >
            <template #item.subject_type="{ value }">
              {{ value === 'user' ? t('permissions.user') : t('permissions.group') }}
            </template>
            <template #item.effect="{ value }">
              <v-chip :color="value === 'allow' ? 'success' : 'warning'" size="small" variant="tonal">
                {{ value === 'allow' ? t('permissions.allow') : t('permissions.deny') }}
              </v-chip>
            </template>
            <template #item.actions="{ item }">
              <v-btn icon="mdi-delete" size="small" variant="text" @click="handleDeleteRule(item)" />
            </template>
          </v-data-table>
        </v-card-text>
      </v-card>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { computed, onMounted, reactive, ref, watch } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { useRoute } from 'vue-router'
  import {
    type AccessRuleItem,
    createAccessRule,
    deleteAccessRule,
    getAccessRules,
    getGroups,
    getPlugins,
    getUsers,
    type GroupItem,
    type PluginItem,
    updateGroup,
    updateGroupPlugins,
    updatePluginAccessMode,
    updateUserLevel,
    type UserLevelItem,
  } from '@/api'
  import { getErrorMessage } from '@/api/client'
  import { useNoticeStore } from '@/stores/notice'

  type Perspective = 'plugins' | 'groups' | 'users' | 'rules'

  const route = useRoute()
  const { t } = useI18n()
  const noticeStore = useNoticeStore()

  const perspective = ref<Perspective>('plugins')
  const loading = ref(false)
  const creatingRule = ref(false)
  const pendingGroupBot = ref(false)
  const pendingGroupPlugins = ref(false)
  const pendingPluginAccessMode = ref(false)
  const pendingUserKey = ref('')
  const errorMessage = ref('')

  const plugins = ref<PluginItem[]>([])
  const groups = ref<GroupItem[]>([])
  const rules = ref<AccessRuleItem[]>([])
  const users = ref<UserLevelItem[]>([])

  const pluginSearch = ref('')
  const groupSearch = ref('')
  const userSearch = ref('')
  const ruleSearch = ref('')
  const ruleEffectFilter = ref<'all' | 'allow' | 'deny'>('all')

  const selectedPluginModule = ref('')
  const selectedGroupId = ref('')
  const selectedUserId = ref('')
  const selectedGroupDisabledPluginsDraft = ref<string[]>([])

  const pluginRuleForm = reactive({
    subject_type: 'user',
    subject_id: '',
    effect: 'allow',
    note: '',
  })
  const groupRuleForm = reactive({
    plugin_module: '',
    effect: 'allow',
    note: '',
  })
  const userRuleForm = reactive({
    plugin_module: '',
    effect: 'allow',
    note: '',
  })

  const levelOptions = [0, 1, 2, 3, 4, 5, 6]

  const perspectiveItems = computed<
    Array<{ value: Perspective; title: string; meta: string }>
  >(() => [
    { value: 'plugins', title: t('permissions.pluginsTab'), meta: String(plugins.value.length) },
    { value: 'groups', title: t('permissions.groupsTab'), meta: String(groups.value.length) },
    { value: 'users', title: t('permissions.usersTab'), meta: String(userEntries.value.length) },
    { value: 'rules', title: t('permissions.rulesTab'), meta: String(rules.value.length) },
  ])

  const ruleHeaders = computed(() => [
    { title: t('permissions.subjectType'), key: 'subject_type' },
    { title: t('permissions.subjectId'), key: 'subject_id' },
    { title: t('permissions.pluginModule'), key: 'plugin_module' },
    { title: t('permissions.effect'), key: 'effect' },
    { title: t('permissions.note'), key: 'note' },
    { title: '', key: 'actions', sortable: false },
  ])

  const subjectTypeOptions = computed(() => [
    { title: t('permissions.user'), value: 'user' },
    { title: t('permissions.group'), value: 'group' },
  ])
  const effectOptions = computed(() => [
    { title: t('permissions.allow'), value: 'allow' },
    { title: t('permissions.deny'), value: 'deny' },
  ])
  const accessModeOptions = computed(() => [
    { title: t('permissions.accessModeDefaultAllow'), value: 'default_allow' },
    { title: t('permissions.accessModeDefaultDeny'), value: 'default_deny' },
  ])
  const ruleEffectOptions = computed(() => [
    { title: t('permissions.effectAll'), value: 'all' },
    { title: t('permissions.allow'), value: 'allow' },
    { title: t('permissions.deny'), value: 'deny' },
  ])

  const manageablePlugins = computed(() =>
    plugins.value.filter(item => item.kind !== 'core' && !item.is_protected),
  )

  const pluginModuleOptions = computed(() =>
    manageablePlugins.value.map(item => ({
      title: item.name && item.name !== item.module_name ? `${item.name} (${item.module_name})` : item.module_name,
      value: item.module_name,
    })),
  )

  const visiblePlugins = computed(() => {
    const keyword = pluginSearch.value.trim().toLowerCase()
    return manageablePlugins.value.filter(item => {
      if (!keyword) return true
      return `${item.name || ''} ${item.module_name}`.toLowerCase().includes(keyword)
    })
  })

  const visibleGroups = computed(() => {
    const keyword = groupSearch.value.trim().toLowerCase()
    return groups.value.filter(item => {
      if (!keyword) return true
      return `${item.group_name || ''} ${item.group_id}`.toLowerCase().includes(keyword)
    })
  })

  const filteredRules = computed(() => {
    const keyword = ruleSearch.value.trim().toLowerCase()
    return rules.value.filter(item => {
      const matchKeyword = !keyword || [
        item.subject_type,
        item.subject_id,
        item.plugin_module,
        item.effect,
        item.note || '',
      ].some(value => value.toLowerCase().includes(keyword))
      const matchEffect = ruleEffectFilter.value === 'all' || item.effect === ruleEffectFilter.value
      return matchKeyword && matchEffect
    })
  })

  const selectedPlugin = computed(() =>
    manageablePlugins.value.find(item => item.module_name === selectedPluginModule.value) || null,
  )
  const selectedGroup = computed(() =>
    groups.value.find(item => item.group_id === selectedGroupId.value) || null,
  )

  const selectedPluginRules = computed(() =>
    rules.value.filter(rule => rule.plugin_module === selectedPluginModule.value),
  )
  const selectedPluginUserAllowRules = computed(() =>
    selectedPluginRules.value.filter(rule => rule.subject_type === 'user' && rule.effect === 'allow'),
  )
  const selectedPluginUserDenyRules = computed(() =>
    selectedPluginRules.value.filter(rule => rule.subject_type === 'user' && rule.effect === 'deny'),
  )
  const selectedPluginGroupAllowRules = computed(() =>
    selectedPluginRules.value.filter(rule => rule.subject_type === 'group' && rule.effect === 'allow'),
  )
  const selectedPluginGroupDenyRules = computed(() =>
    selectedPluginRules.value.filter(rule => rule.subject_type === 'group' && rule.effect === 'deny'),
  )

  const groupsWithPluginDisabled = computed(() =>
    groups.value.filter(group => group.disabled_plugins.includes(selectedPluginModule.value)),
  )
  const groupsWithBotDisabled = computed(() =>
    groups.value.filter(group => !group.bot_status),
  )

  const selectedGroupRules = computed(() =>
    rules.value.filter(rule => rule.subject_type === 'group' && rule.subject_id === selectedGroupId.value),
  )
  const selectedGroupUsers = computed(() =>
    users.value.filter(item => item.group_id === selectedGroupId.value),
  )

  const userEntries = computed(() => {
    const fromLevels = users.value.map(item => item.user_id)
    const fromRules = rules.value.filter(item => item.subject_type === 'user').map(item => item.subject_id)
    return [...new Set([...fromLevels, ...fromRules])]
      .filter(Boolean)
      .map(userId => ({
        user_id: userId,
        groups: users.value.filter(item => item.user_id === userId).length,
        rules: rules.value.filter(item => item.subject_type === 'user' && item.subject_id === userId).length,
      }))
  })

  const visibleUserEntries = computed(() => {
    const keyword = userSearch.value.trim().toLowerCase()
    return userEntries.value.filter(item => {
      if (!keyword) return true
      return item.user_id.toLowerCase().includes(keyword)
    })
  })

  const selectedUserRules = computed(() =>
    rules.value.filter(rule => rule.subject_type === 'user' && rule.subject_id === selectedUserId.value),
  )
  const selectedUserLevels = computed(() =>
    users.value.filter(item => item.user_id === selectedUserId.value),
  )

  const hasPendingGroupPluginChanges = computed(() => {
    const current = [...(selectedGroup.value?.disabled_plugins || [])].sort()
    const draft = [...selectedGroupDisabledPluginsDraft.value].sort()
    return JSON.stringify(current) !== JSON.stringify(draft)
  })

  function ruleKey (rule: AccessRuleItem): string {
    return `${rule.subject_type}:${rule.subject_id}:${rule.plugin_module}`
  }

  function pluginRuleCount (moduleName: string): number {
    return rules.value.filter(rule => rule.plugin_module === moduleName).length
  }

  function selectGroup (groupId: string): void {
    selectedGroupId.value = groupId
    selectedGroupDisabledPluginsDraft.value = [
      ...(groups.value.find(item => item.group_id === groupId)?.disabled_plugins || []),
    ]
  }

  function groupNameById (groupId: string): string {
    return groups.value.find(item => item.group_id === groupId)?.group_name || groupId
  }

  function applyRouteState (): void {
    const tabQuery = route.query.tab
    if (tabQuery === 'plugins' || tabQuery === 'groups' || tabQuery === 'users' || tabQuery === 'rules') {
      perspective.value = tabQuery
    }
  }

  function ensureSelections (): void {
    if (!selectedPluginModule.value && manageablePlugins.value.length) {
      selectedPluginModule.value = manageablePlugins.value[0].module_name
    }
    if (
      selectedPluginModule.value
      && !manageablePlugins.value.some(item => item.module_name === selectedPluginModule.value)
    ) {
      selectedPluginModule.value = manageablePlugins.value[0]?.module_name || ''
    }
    if (!selectedGroupId.value && groups.value.length) {
      selectGroup(groups.value[0].group_id)
    }
    if (!selectedUserId.value && userEntries.value.length) {
      selectedUserId.value = userEntries.value[0].user_id
    }
    if (selectedGroup.value) {
      selectedGroupDisabledPluginsDraft.value = [...selectedGroup.value.disabled_plugins]
    }
  }

  async function loadAll (): Promise<void> {
    loading.value = true
    errorMessage.value = ''
    try {
      const [pluginsResponse, groupsResponse, rulesResponse, usersResponse] = await Promise.all([
        getPlugins(),
        getGroups(),
        getAccessRules(),
        getUsers(),
      ])
      plugins.value = pluginsResponse.data
      groups.value = groupsResponse.data
      rules.value = rulesResponse.data
      users.value = usersResponse.data
      ensureSelections()
    } catch (error) {
      errorMessage.value = getErrorMessage(error, t('permissions.loadFailed'))
    } finally {
      loading.value = false
    }
  }

  async function createRule (payload: {
    subject_type: string
    subject_id: string
    plugin_module: string
    effect: string
    note: string | null
  }): Promise<void> {
    creatingRule.value = true
    errorMessage.value = ''
    try {
      const response = await createAccessRule(payload)
      rules.value = [response.data, ...rules.value.filter(item => ruleKey(item) !== ruleKey(response.data))]
      noticeStore.show(t('permissions.ruleCreated'), 'success')
    } catch (error) {
      errorMessage.value = getErrorMessage(error, t('permissions.ruleCreateFailed'))
      noticeStore.show(errorMessage.value, 'error')
    } finally {
      creatingRule.value = false
    }
  }

  async function createRuleForPlugin (): Promise<void> {
    if (!selectedPluginModule.value || !pluginRuleForm.subject_id.trim()) return
    await createRule({
      subject_type: pluginRuleForm.subject_type,
      subject_id: pluginRuleForm.subject_id.trim(),
      plugin_module: selectedPluginModule.value,
      effect: pluginRuleForm.effect,
      note: pluginRuleForm.note.trim() || null,
    })
    pluginRuleForm.subject_id = ''
    pluginRuleForm.note = ''
    pluginRuleForm.effect = 'allow'
  }

  async function updateSelectedPluginAccessMode (
    nextValue: unknown,
  ): Promise<void> {
    if (!selectedPlugin.value) return
    const accessMode = String(nextValue)
    if (!['default_allow', 'default_deny'].includes(accessMode)) return
    if (selectedPlugin.value.access_mode === accessMode) return

    const previous = selectedPlugin.value.access_mode
    selectedPlugin.value.access_mode = accessMode
    pendingPluginAccessMode.value = true
    errorMessage.value = ''
    try {
      await updatePluginAccessMode(selectedPlugin.value.module_name, accessMode)
      noticeStore.show(t('common.save'), 'success')
    } catch (error) {
      selectedPlugin.value.access_mode = previous
      errorMessage.value = getErrorMessage(error, t('permissions.loadFailed'))
      noticeStore.show(errorMessage.value, 'error')
    } finally {
      pendingPluginAccessMode.value = false
    }
  }

  async function createRuleForGroup (): Promise<void> {
    if (!selectedGroupId.value || !groupRuleForm.plugin_module.trim()) return
    await createRule({
      subject_type: 'group',
      subject_id: selectedGroupId.value,
      plugin_module: groupRuleForm.plugin_module.trim(),
      effect: groupRuleForm.effect,
      note: groupRuleForm.note.trim() || null,
    })
    groupRuleForm.plugin_module = ''
    groupRuleForm.note = ''
    groupRuleForm.effect = 'allow'
  }

  async function createRuleForUser (): Promise<void> {
    if (!selectedUserId.value || !userRuleForm.plugin_module.trim()) return
    await createRule({
      subject_type: 'user',
      subject_id: selectedUserId.value,
      plugin_module: userRuleForm.plugin_module.trim(),
      effect: userRuleForm.effect,
      note: userRuleForm.note.trim() || null,
    })
    userRuleForm.plugin_module = ''
    userRuleForm.note = ''
    userRuleForm.effect = 'allow'
  }

  async function handleDeleteRule (rule: AccessRuleItem): Promise<void> {
    errorMessage.value = ''
    try {
      await deleteAccessRule({
        subject_type: rule.subject_type,
        subject_id: rule.subject_id,
        plugin_module: rule.plugin_module,
      })
      rules.value = rules.value.filter(item => ruleKey(item) !== ruleKey(rule))
      noticeStore.show(t('permissions.ruleDeleted'), 'success')
    } catch (error) {
      errorMessage.value = getErrorMessage(error, t('permissions.ruleDeleteFailed'))
      noticeStore.show(errorMessage.value, 'error')
    }
  }

  async function updateSelectedGroupBot (nextValue: unknown): Promise<void> {
    if (!selectedGroup.value) return
    const enabled = Boolean(nextValue)
    if (selectedGroup.value.bot_status === enabled) return

    const previous = selectedGroup.value.bot_status
    selectedGroup.value.bot_status = enabled
    pendingGroupBot.value = true
    errorMessage.value = ''
    try {
      await updateGroup(selectedGroup.value.group_id, enabled)
      noticeStore.show(t('permissions.groupUpdated'), 'success')
    } catch (error) {
      selectedGroup.value.bot_status = previous
      errorMessage.value = getErrorMessage(error, t('permissions.groupUpdateFailed'))
      noticeStore.show(errorMessage.value, 'error')
    } finally {
      pendingGroupBot.value = false
    }
  }

  async function saveSelectedGroupPlugins (): Promise<void> {
    if (!selectedGroup.value) return
    pendingGroupPlugins.value = true
    errorMessage.value = ''
    const nextValue = [...selectedGroupDisabledPluginsDraft.value]
    const previous = [...selectedGroup.value.disabled_plugins]
    try {
      await updateGroupPlugins(selectedGroup.value.group_id, nextValue)
      selectedGroup.value.disabled_plugins = nextValue
      noticeStore.show(t('permissions.groupPluginsUpdated'), 'success')
    } catch (error) {
      selectedGroupDisabledPluginsDraft.value = previous
      errorMessage.value = getErrorMessage(error, t('permissions.groupUpdateFailed'))
      noticeStore.show(errorMessage.value, 'error')
    } finally {
      pendingGroupPlugins.value = false
    }
  }

  async function updateLevel (item: UserLevelItem, nextValue: unknown): Promise<void> {
    const level = Number(nextValue)
    if (Number.isNaN(level) || level === item.level) return
    const previous = item.level
    const key = `${item.user_id}:${item.group_id}`
    item.level = level
    pendingUserKey.value = key
    errorMessage.value = ''
    try {
      await updateUserLevel(item.user_id, item.group_id, level)
      noticeStore.show(t('permissions.levelUpdated', { userId: item.user_id, groupId: item.group_id }), 'success')
    } catch (error) {
      item.level = previous
      errorMessage.value = getErrorMessage(error, t('permissions.levelUpdateFailed'))
      noticeStore.show(errorMessage.value, 'error')
    } finally {
      pendingUserKey.value = ''
    }
  }

  watch(() => route.query, () => {
    applyRouteState()
  })

  onMounted(async () => {
    applyRouteState()
    await loadAll()
  })
</script>

<style scoped>
.permission-workbench {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: calc(100vh - (var(--page-gutter) * 2));
  min-height: 0;
  overflow: hidden;
}

.permission-workbench__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex: 0 0 auto;
}

.permission-workbench__subtitle {
  color: rgba(var(--v-theme-on-surface), 0.64);
  font-size: 0.92rem;
}

.permission-perspectives {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  flex: 0 0 auto;
}

.permission-perspective {
  border: 1px solid rgba(var(--v-theme-outline), 0.18);
  border-radius: 18px;
  padding: 12px 16px;
  text-align: left;
  background: rgb(var(--v-theme-surface));
  transition: border-color 0.2s ease, background 0.2s ease, transform 0.2s ease;
}

.permission-perspective--active {
  border-color: rgba(var(--v-theme-primary), 0.4);
  background: rgba(var(--v-theme-primary), 0.08);
  transform: translateY(-1px);
}

.permission-perspective__label {
  display: block;
  font-weight: 700;
}

.permission-perspective__meta {
  display: block;
  margin-top: 2px;
  color: rgba(var(--v-theme-on-surface), 0.64);
}

.permission-layout {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 16px;
  min-height: 0;
  flex: 1 1 auto;
  overflow: hidden;
}

.permission-sidebar,
.permission-panel {
  border: 1px solid rgba(var(--v-theme-outline), 0.14);
  border-radius: 24px;
  background: rgb(var(--v-theme-surface));
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
}

.permission-sidebar {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.permission-sidebar__search {
  flex: 0 0 auto;
}

.permission-sidebar__search :deep(.v-field) {
  border-radius: 12px;
}

.permission-sidebar__search :deep(.v-field__input) {
  min-height: 36px;
  padding-top: 0;
  padding-bottom: 0;
}

.permission-sidebar__list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 4px;
}

.permission-sidebar__item {
  border: 1px solid rgba(var(--v-theme-outline), 0.14);
  border-radius: 16px;
  padding: 10px 12px;
  text-align: left;
  background: rgb(var(--v-theme-surface));
}

.permission-sidebar__item--active {
  border-color: rgba(var(--v-theme-primary), 0.4);
  background: rgba(var(--v-theme-primary), 0.08);
}

.permission-sidebar__item-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.permission-sidebar__item-title {
  font-weight: 700;
}

.permission-sidebar__item-subtitle {
  color: rgba(var(--v-theme-on-surface), 0.64);
  font-size: 0.8rem;
}

.permission-sidebar__item-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.permission-main {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 4px;
}

.permission-panel--hero {
  padding: 16px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.permission-panel__title {
  font-size: 1.2rem;
  font-weight: 800;
}

.permission-panel__subtitle {
  color: rgba(var(--v-theme-on-surface), 0.64);
}

.permission-panel__hero-stats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: flex-end;
}

.permission-inline-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 88px;
}

.permission-inline-stat--control {
  min-width: 156px;
}

.permission-inline-stat__label {
  color: rgba(var(--v-theme-on-surface), 0.64);
  font-size: 0.75rem;
  font-weight: 700;
}

.permission-inline-stat__value {
  font-size: 1.05rem;
  font-weight: 800;
}

.permission-access-mode {
  max-width: 156px;
}

.permission-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.permission-panel :deep(.v-card-title) {
  font-size: 0.96rem;
  font-weight: 700;
  padding-bottom: 8px;
}

.permission-panel :deep(.v-card-text) {
  padding-top: 8px;
}

.permission-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.permission-stat {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(var(--v-theme-outline), 0.12);
}

.permission-stat:last-child {
  border-bottom: 0;
}

.permission-stat__label {
  color: rgba(var(--v-theme-on-surface), 0.64);
}

.permission-stat__value {
  font-weight: 800;
}

.permission-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.permission-form-grid__actions {
  display: flex;
  align-items: center;
}

.permission-rule-columns {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.permission-section-title {
  margin-bottom: 8px;
  font-weight: 700;
}

.permission-rule-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.permission-rule-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid rgba(var(--v-theme-outline), 0.12);
}

.permission-rule-row:last-child {
  border-bottom: 0;
}

.permission-chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.permission-empty {
  color: rgba(var(--v-theme-on-surface), 0.64);
  padding: 4px 0;
}

.permission-level-select {
  max-width: 120px;
}

.permission-filters {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

@media (max-width: 1100px) {
  .permission-perspectives {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .permission-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .permission-grid,
  .permission-rule-columns,
  .permission-form-grid {
    grid-template-columns: 1fr;
  }

  .permission-workbench__header,
  .permission-panel--hero {
    flex-direction: column;
    align-items: stretch;
  }

  .permission-workbench {
    height: auto;
    overflow: visible;
  }

  .permission-layout,
  .permission-main {
    overflow: visible;
  }
}
</style>
