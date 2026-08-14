<script setup lang="ts">
import { reactive, ref } from "vue";
import { useI18n } from "vue-i18n";
import { toast } from "vue-sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const { t } = useI18n();
const form = reactive({ newPassword: "", confirm: "" });
const submitting = ref(false);

async function onSubmit() {
  if (!form.newPassword) return;
  if (form.newPassword !== form.confirm) {
    toast.error(t("account.passwordMismatch"));
    return;
  }
  submitting.value = true;
  try {
    await api.auth.changePasswordForce({ new_password: form.newPassword });
    auth.clearMustChangePassword();
    toast.success(t("account.success"));
    form.newPassword = "";
    form.confirm = "";
  } catch (e) {
    toast.error((e as Error).message || t("account.changeFailed"));
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <Dialog
    :open="auth.mustChangePassword"
    @update:open="() => {}"
  >
    <DialogContent
      :show-close-button="false"
      class="sm:max-w-md"
      @escape-key-down.prevent
      @interact-outside.prevent
    >
      <DialogHeader>
        <DialogTitle>{{ $t("account.mustChangeTitle") }}</DialogTitle>
        <DialogDescription>{{ $t("account.mustChangeDesc") }}</DialogDescription>
      </DialogHeader>
      <form class="space-y-4" @submit.prevent="onSubmit">
        <div class="space-y-2">
          <Label for="force-new">{{ $t("account.newPassword") }}</Label>
          <Input
            id="force-new"
            v-model="form.newPassword"
            type="password"
            autocomplete="new-password"
            required
          />
        </div>
        <div class="space-y-2">
          <Label for="force-confirm">{{ $t("account.confirmPassword") }}</Label>
          <Input
            id="force-confirm"
            v-model="form.confirm"
            type="password"
            autocomplete="new-password"
            required
          />
        </div>
        <Button type="submit" class="w-full" :disabled="submitting">
          {{ submitting ? $t("common.loading") : $t("common.confirm") }}
        </Button>
      </form>
    </DialogContent>
  </Dialog>
</template>
