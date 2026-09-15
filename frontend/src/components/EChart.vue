<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts";
const props = defineProps<{ option: any; height?: string }>();
const el = ref<HTMLDivElement>(); let chart: echarts.ECharts | null = null;
const render = () => { if (!el.value) return; if (!chart) chart = echarts.init(el.value); chart.setOption(props.option, true); };
const resize = () => chart?.resize();
onMounted(() => { render(); window.addEventListener("resize", resize); });
watch(() => props.option, render, { deep: true });
onBeforeUnmount(() => { window.removeEventListener("resize", resize); chart?.dispose(); });
</script>
<template><div ref="el" :style="{ width: '100%', height: height || '320px' }" /></template>
