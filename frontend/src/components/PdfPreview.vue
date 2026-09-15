<script setup lang="ts">
import { ref, watch } from "vue"; import * as pdfjsLib from "pdfjs-dist"; import workerSrc from "pdfjs-dist/build/pdf.worker.min.mjs?url";
pdfjsLib.GlobalWorkerOptions.workerSrc=workerSrc; const props=defineProps<{blob:Blob|null}>(); const canvas=ref<HTMLCanvasElement>(); const page=ref(1); const pages=ref(0); let pdf:any=null;
async function render(){if(!props.blob||!canvas.value)return; pdf=await pdfjsLib.getDocument({data:new Uint8Array(await props.blob.arrayBuffer())}).promise;pages.value=pdf.numPages;await renderPage()}
async function renderPage(){if(!pdf||!canvas.value)return;const p=await pdf.getPage(page.value);const viewport=p.getViewport({scale:1.4});canvas.value.width=viewport.width;canvas.value.height=viewport.height;const ctx=canvas.value.getContext("2d");if(ctx)await p.render({canvasContext:ctx,viewport,canvas:canvas.value} as any).promise}
watch(()=>props.blob,()=>{page.value=1;void render()},{immediate:true});watch(page,()=>void renderPage());
</script><template><div class="pdf-preview"><div class="pdf-toolbar"><el-button :disabled="page<=1" @click="page--">上一页</el-button><span>{{page}} / {{pages}}</span><el-button :disabled="page>=pages" @click="page++">下一页</el-button></div><canvas ref="canvas"/></div></template>
