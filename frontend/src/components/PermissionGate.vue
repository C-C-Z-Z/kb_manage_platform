<script setup lang="ts">
import { computed } from "vue";
import { hasPermission } from "../auth";
const props = defineProps<{ permission: string }>();
const allowed = computed(() => hasPermission(props.permission));
</script>
<template><slot v-if="allowed" /><slot v-else name="fallback" /></template>
