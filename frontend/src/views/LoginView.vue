<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { Lock, User } from "@element-plus/icons-vue";
import { authState, login } from "../auth";
const router = useRouter(); const route = useRoute(); const error = ref(""); const form = reactive({ username: "", password: "" });
async function submit() { error.value = ""; try { await login(form.username, form.password); await router.replace(String(route.query.redirect || "/chat")); } catch (e) { error.value = e instanceof Error ? e.message : "登录失败"; } }
</script>
<template><div class="login-page"><div class="login-panel"><div class="login-copy"><div class="brand-mark large">KB</div><h1>知识库管理平台</h1><p>统一维护企业知识，按全局、部门、角色和个人四维权限完成安全检索与智能问答。</p></div><el-card class="login-card"><h2>登录控制台</h2><el-alert v-if="error" :title="error" type="error" show-icon :closable="false" class="form-alert" /><el-form label-position="top" @submit.prevent="submit"><el-form-item label="用户名"><el-input v-model="form.username" size="large" :prefix-icon="User" /></el-form-item><el-form-item label="密码"><el-input v-model="form.password" type="password" show-password size="large" :prefix-icon="Lock" @keyup.enter="submit" /></el-form-item><el-button type="primary" size="large" :loading="authState.loading" native-type="submit" style="width:100%">登录</el-button></el-form></el-card></div></div></template>
