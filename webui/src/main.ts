import { createApp } from "vue";

import "vue-sonner/style.css";

import { createPinia } from "pinia";
import piniaPersist from "pinia-plugin-persistedstate";

import { queryClient, VueQueryPlugin } from "@/lib/queryClient";
import i18n from "@/i18n";
import router from "@/router";
import App from "./App.vue";

import "./style.css";

const app = createApp(App);

const pinia = createPinia();
pinia.use(piniaPersist);

app.use(pinia);
app.use(router);
app.use(VueQueryPlugin, { queryClient });
app.use(i18n);

app.mount("#app");
