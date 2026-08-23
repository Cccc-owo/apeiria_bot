<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";
import {
  ChevronsUpDown,
  KeyRound,
  LogOut,
  Monitor,
  Moon,
  Sun,
} from "@lucide/vue";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarRail,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import NavGroup from "@/layouts/sidebar/NavGroup.vue";
import { routeTitleMap, sidebarNav } from "@/layouts/sidebar/sidebarNav";
import { useAuthStore } from "@/stores/auth";
import { type Theme, useUiStore } from "@/stores/ui";

const route = useRoute();
const router = useRouter();
const ui = useUiStore();
const auth = useAuthStore();
const { t } = useI18n();

const currentLabel = computed(() => {
  const key =
    typeof route.name === "string" ? routeTitleMap[route.name] : undefined;
  return key ? t(key) : "";
});

const breadcrumbs = computed(() => {
  const name = typeof route.name === "string" ? route.name : "";
  if (name === "settings-nonebot" || name === "settings-apeiria") {
    return [
      { label: t("nav.settings"), to: { name: "settings-nonebot" } },
      { label: currentLabel.value },
    ];
  }
  return [{ label: currentLabel.value }];
});

const initial = computed(() =>
  (auth.username ?? "A").slice(0, 1).toUpperCase(),
);

function setTheme(value: unknown) {
  ui.setTheme(value as Theme);
}

function logout() {
  auth.clearSession();
  void router.push({ name: "login" });
}
</script>

<template>
  <SidebarProvider class="h-svh">
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton as-child size="lg">
              <RouterLink :to="{ name: 'dashboard' }">
                <div
                  class="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary font-bold text-primary-foreground"
                >
                  A
                </div>
                <div class="grid flex-1 text-left leading-tight">
                  <span class="truncate text-base font-semibold">Apeiria</span>
                </div>
              </RouterLink>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <NavGroup
          v-for="(group, i) in sidebarNav"
          :key="group.label ?? i"
          :group="group"
        />
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger as-child>
                <SidebarMenuButton size="lg">
                  <Avatar class="size-8 rounded-lg">
                    <AvatarFallback
                      class="rounded-lg bg-primary/10 text-primary"
                    >
                      {{ initial }}
                    </AvatarFallback>
                  </Avatar>
                  <div class="grid flex-1 text-left text-sm leading-tight">
                    <span class="truncate font-medium">{{
                      auth.username ?? $t("account.admin")
                    }}</span>
                  </div>
                  <ChevronsUpDown class="ml-auto size-4" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent side="top" align="start" class="w-56">
                <DropdownMenuLabel>{{
                  auth.username ?? $t("account.admin")
                }}</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem @click="router.push({ name: 'account' })">
                  <KeyRound />
                  {{ $t("account.changePassword") }}
                </DropdownMenuItem>
                <DropdownMenuItem @click="logout">
                  <LogOut />
                  {{ $t("account.logout") }}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>

      <SidebarRail />
    </Sidebar>

    <SidebarInset>
      <header
        class="flex h-16 shrink-0 items-center gap-2 border-b bg-background px-4"
      >
        <SidebarTrigger class="-ml-1" />
        <div class="h-4 w-px bg-border" />
        <Breadcrumb v-if="breadcrumbs.length > 1">
          <BreadcrumbList>
            <template v-for="(b, i) in breadcrumbs" :key="i">
              <BreadcrumbItem v-if="i < breadcrumbs.length - 1">
                <BreadcrumbLink as-child>
                  <RouterLink :to="b.to!">{{ b.label }}</RouterLink>
                </BreadcrumbLink>
                <BreadcrumbSeparator />
              </BreadcrumbItem>
              <BreadcrumbPage v-else class="text-sm font-medium">{{
                b.label
              }}</BreadcrumbPage>
            </template>
          </BreadcrumbList>
        </Breadcrumb>
        <h1 v-else class="text-sm font-medium">{{ currentLabel }}</h1>
        <div class="ml-auto flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <Button
                variant="ghost"
                size="icon"
                :aria-label="$t('theme.label')"
              >
                <Sun v-if="ui.theme === 'light'" />
                <Moon v-else-if="ui.theme === 'dark'" />
                <Monitor v-else />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuRadioGroup
                :model-value="ui.theme"
                @update:model-value="setTheme"
              >
                <DropdownMenuRadioItem value="light">
                  <Sun />
                  {{ $t("theme.light") }}
                </DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="dark">
                  <Moon />
                  {{ $t("theme.dark") }}
                </DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="system">
                  <Monitor />
                  {{ $t("theme.system") }}
                </DropdownMenuRadioItem>
              </DropdownMenuRadioGroup>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>
      <main class="min-h-0 flex-1 overflow-auto">
        <RouterView />
      </main>
    </SidebarInset>
  </SidebarProvider>
</template>
