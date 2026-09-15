import { ref, type Ref } from "vue";
export function useAsync<T>(loader: () => Promise<T>, immediate = true) {
  const data = ref<T | null>(null) as Ref<T | null>; const loading = ref(false); const error = ref<Error | null>(null);
  const execute = async () => { loading.value = true; error.value = null; try { const result = await loader(); data.value = result; return result; } catch (caught) { const normalized = caught instanceof Error ? caught : new Error("请求失败"); error.value = normalized; throw normalized; } finally { loading.value = false; } };
  if (immediate) void execute().catch(() => undefined);
  return { data, loading, error, execute };
}
