import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { authState, hasPermission } from "../auth";
import AppLayout from "../components/AppLayout.vue";
import LoginView from "../views/LoginView.vue";
import ChatView from "../views/ChatView.vue";
import SessionsView from "../views/SessionsView.vue";
import KnowledgeListView from "../views/KnowledgeListView.vue";
import KnowledgeDetailView from "../views/KnowledgeDetailView.vue";
import ImportView from "../views/ImportView.vue";
import DashboardView from "../views/DashboardView.vue";
import OperationsView from "../views/OperationsView.vue";
import AuditView from "../views/AuditView.vue";
import SystemSettingsView from "../views/SystemSettingsView.vue";
import IamView from "../views/IamView.vue";
import ChangePasswordView from "../views/ChangePasswordView.vue";
import ForbiddenView from "../views/ForbiddenView.vue";
import NotFoundView from "../views/NotFoundView.vue";

const routes: RouteRecordRaw[] = [
  { path: "/login", component: LoginView, meta: { public: true } },
  { path: "/", component: AppLayout, children: [
    { path: "", redirect: "/chat" },
    { path: "chat", component: ChatView, meta: { permission: "qa:use" } },
    { path: "sessions", component: SessionsView, meta: { permission: "qa:session:read" } },
    { path: "knowledge", component: KnowledgeListView, meta: { permission: "knowledge:read" } },
    { path: "knowledge/:knowledgeId", component: KnowledgeDetailView, meta: { permission: "knowledge:read" } },
    { path: "import", component: ImportView, meta: { permission: "import:create" } },
    { path: "dashboard", component: DashboardView, meta: { permission: "dashboard:read" } },
    { path: "operations", component: OperationsView, meta: { permission: "faq:manage" } },
    { path: "audit", component: AuditView, meta: { permission: "audit:read" } },
    { path: "system", component: SystemSettingsView, meta: { permission: "model:manage" } },
    { path: "iam/users", component: IamView, meta: { permission: "iam:user:manage" } },
    { path: "change-password", component: ChangePasswordView },
    { path: "403", component: ForbiddenView }
  ] },
  { path: "/:pathMatch(.*)*", component: NotFoundView }
];

export const router = createRouter({ history: createWebHistory(), routes });
router.beforeEach((to) => {
  if (to.meta.public) return true;
  if (!authState.user) return { path: "/login", query: { redirect: to.fullPath } };
  const permission = to.meta.permission as string | undefined;
  if (permission && !hasPermission(permission)) return "/403";
  return true;
});
