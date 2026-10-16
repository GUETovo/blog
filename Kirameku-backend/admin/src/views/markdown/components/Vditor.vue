<script setup lang="ts">
import "vditor/dist/index.css";
import Vditor from "vditor";
import { getToken } from "@/utils/auth";
import { useDark } from "@pureadmin/utils";
import { useIntervalFn } from "@vueuse/core";
import { onMounted, ref, watch, toRaw, onUnmounted } from "vue";

const emit = defineEmits([
  "update:modelValue",
  "after",
  "focus",
  "blur",
  "esc",
  "ctrlEnter",
  "select"
]);

const props = defineProps({
  options: {
    type: Object,
    default() {
      return {};
    }
  },
  modelValue: {
    type: String,
    default: ""
  }
});

const { isDark } = useDark();
const editor = ref<Vditor | null>(null);
const markdownRef = ref<HTMLElement | null>(null);
const editorReady = ref(false);
let pendingValue: string | null = null;

onMounted(() => {
  editor.value = new Vditor(markdownRef.value as HTMLElement, {
    // 正文插图默认上传到后端（→ 腾讯云 COS），避免 Vditor 默认把图片转成 base64 塞进正文
    upload: {
      url: "/api/upload/image",
      fieldName: "file",
      max: 10 * 1024 * 1024,
      accept: "image/*",
      headers: (() => {
        const t = getToken()?.accessToken;
        return t ? { Authorization: `Bearer ${t}` } : {};
      })(),
      format(files: File[], responseText: string) {
        let url = "";
        try {
          const res = JSON.parse(responseText);
          url = res?.url || res?.data?.url || "";
        } catch {
          /* 响应不是 JSON，按失败处理 */
        }
        const name = files?.[0]?.name || "image";
        const succMap: Record<string, string> = {};
        if (url) succMap[name] = url;
        return JSON.stringify({
          msg: url ? "" : "上传失败",
          code: url ? 0 : 1,
          data: { errFiles: url ? [] : [name], succMap }
        });
      }
    },

    ...props.options,
    value: props.modelValue,
    cache: {
      enable: false
    },
    fullscreen: {
      index: 10000
    },
    after() {
      editorReady.value = true;
      if (pendingValue !== null) {
        editor.value?.setValue(pendingValue);
        pendingValue = null;
      }
      emit("after", toRaw(editor.value));
    },
    input(value: string) {
      emit("update:modelValue", value);
    },
    focus(value: string) {
      emit("focus", value);
    },
    blur(value: string) {
      emit("blur", value);
    },
    esc(value: string) {
      emit("esc", value);
    },
    ctrlEnter(value: string) {
      emit("ctrlEnter", value);
    },
    select(value: string) {
      emit("select", value);
    }
  });
});

watch(
  () => props.modelValue,
  newVal => {
    if (!editorReady.value) {
      pendingValue = newVal;
      return;
    }
    if (newVal !== editor.value?.getValue()) {
      editor.value?.setValue(newVal);
    }
  }
);

watch(
  () => isDark.value,
  newVal => {
    const { pause } = useIntervalFn(() => {
      if (editor.value.vditor) {
        newVal
          ? editor.value.setTheme("dark", "dark", "rose-pine")
          : editor.value.setTheme("classic", "light", "github");
        pause();
      }
    }, 20);
  }
);

onUnmounted(() => {
  const editorInstance = editor.value;
  if (!editorInstance) return;
  try {
    editorInstance?.destroy?.();
  } catch (error) {
    console.log(error);
  }
});
</script>

<template>
  <div ref="markdownRef" />
</template>
