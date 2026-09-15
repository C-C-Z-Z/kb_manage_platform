<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ArrowDown, Notebook, DataAnalysis, DataBoard, DocumentAdd, Fold, Message, Operation, Setting, Tickets, User, UserFilled } from "@element-plus/icons-vue";
import { authState, hasPermission, logout } from "../auth";

const route = useRoute(); const router = useRouter(); const collapsed = ref(false);
const menu = [
  { path: "/chat", label: "智能问答", icon: Message, permission: "qa:use" },
  { path: "/sessions", label: "会话历史", icon: Tickets, permission: "qa:session:read" },
  { path: "/knowledge", label: "知识管理", icon: Notebook, permission: "knowledge:read" },
  { path: "/import", label: "文档导入", icon: DocumentAdd, permission: "import:create" },
  { path: "/dashboard", label: "数据洞察", icon: DataBoard, permission: "dashboard:read" },
  { path: "/operations", label: "沉淀运营", icon: Operation, permission: "faq:manage" },
  { path: "/audit", label: "审计日志", icon: DataAnalysis, permission: "audit:read" },
  { path: "/iam/users", label: "组织与账号", icon: UserFilled, permission: "iam:user:manage" },
  { path: "/system", label: "模型与系统", icon: Setting, permission: "model:manage" }
];
const items = computed(() => menu.filter((item) => hasPermission(item.permission)));
const active = computed(() => items.value.find((item) => route.path.startsWith(item.path))?.path || route.path);
const handleLogout = async () => { await logout(); await router.replace("/login"); };
</script>
<template>
  <el-container class="app-shell">
    <el-aside :width="collapsed ? '64px' : '232px'" class="app-sider">
      <div class="brand-block"><div class="brand-mark">KB</div><div v-if="!collapsed" class="brand-copy"><strong>知识库管理平台</strong><span>Knowledge Console</span></div></div>
      <el-menu :default-active="active" :collapse="collapsed" router background-color="#102a4c" text-color="#d7e2f0" active-text-color="#ffffff">
        <el-menu-item v-for="item in items" :key="item.path" :index="item.path"><el-icon><component :is="item.icon" /></el-icon><template #title>{{ item.label }}</template></el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="app-header">
        <el-button text @click="collapsed = !collapsed"><el-icon><Fold /></el-icon></el-button>
        <el-space size="middle"><el-tag type="primary">{{ authState.user?.department_id || "未分配部门" }}</el-tag><el-avatar :icon="User" /><span class="username">{{ authState.user?.username }}</span><el-button text @click="router.push('/change-password')">修改密码</el-button><el-button text @click="handleLogout">退出</el-button></el-space>
      </el-header>
      <el-main class="app-content"><router-view /></el-main>
    </el-container>
  </el-container>
</template>
