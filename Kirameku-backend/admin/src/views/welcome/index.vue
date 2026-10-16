<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import ReCol from "@/components/ReCol";
import { ReNormalCountTo } from "@/components/ReCountTo";
import { getDashboardStats, type DashboardStats } from "@/api/dashboard";
import { getPosts, type PostItem } from "@/api/post";

defineOptions({
  name: "Welcome"
});

const loading = ref(true);
const loadError = ref("");
const stats = ref<DashboardStats | null>(null);
const posts = ref<PostItem[]>([]);

/** 顶部统计卡片 —— 全部来自后端 /api/dashboard/stats */
const cards = computed(() => {
  const c = stats.value?.counts;
  return [
    { key: "posts", name: "已发布文章", value: c?.posts ?? 0, unit: "篇", color: "#41b6ff", bg: "#effaff" },
    { key: "drafts", name: "草稿", value: c?.drafts ?? 0, unit: "篇", color: "#e85f33", bg: "#fff5f4" },
    { key: "categories", name: "分类", value: c?.categories ?? 0, unit: "个", color: "#26ce83", bg: "#eff8f4" },
    { key: "tags", name: "标签", value: c?.tags ?? 0, unit: "个", color: "#7846e5", bg: "#f6f4fe" },
    { key: "comments", name: "评论", value: c?.comments ?? 0, unit: "条", color: "#f5a524", bg: "#fef9ee" },
    { key: "visitors", name: "累计访客", value: c?.visitors ?? 0, unit: "人次", color: "#0ea5e9", bg: "#eff6ff" }
  ];
});

type TrendItem = { date: string; count: number };

const postTrend = computed<TrendItem[]>(() => stats.value?.post_trend ?? []);
const visitorTrend = computed<TrendItem[]>(() => stats.value?.visitor_trend ?? []);

const maxOf = (list: TrendItem[]) => list.reduce((m, i) => Math.max(m, i.count), 0);
const sumOf = (list: TrendItem[]) => list.reduce((s, i) => s + i.count, 0);

const postMax = computed(() => maxOf(postTrend.value));
const visitorMax = computed(() => maxOf(visitorTrend.value));
const postTotal = computed(() => sumOf(postTrend.value));
const visitorTotal = computed(() => sumOf(visitorTrend.value));

/** 柱高：全 0 时给个最小高度，避免整条看不见 */
function barPct(count: number, max: number) {
  if (!max || count <= 0) return 2;
  return Math.max(4, Math.round((count / max) * 100));
}

type DistItem = { name: string; value: number };

/** 分布 → 百分比进度条 */
function toPercent(list: DistItem[]) {
  const total = list.reduce((s, i) => s + i.value, 0);
  return list.map(i => {
    const p = total ? Math.round((i.value / total) * 100) : 0;
    return {
      name: i.name,
      value: i.value,
      percentage: p,
      color: p >= 50 ? "#26ce83" : p >= 25 ? "#41b6ff" : "#f5a524"
    };
  });
}

const categoryDist = computed(() => toPercent(stats.value?.category_distribution ?? []));
const browserDist = computed(() => toPercent(stats.value?.browser_distribution ?? []));

function fmt(dt?: string | null) {
  if (!dt) return "—";
  return String(dt).replace("T", " ").slice(0, 16);
}

async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    const [s, p] = await Promise.all([
      getDashboardStats(),
      getPosts({ page: 1, size: 10 })
    ]);
    stats.value = s;
    posts.value = Array.isArray(p) ? p : [];
  } catch (e: any) {
    loadError.value = e?.message ?? String(e);
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div v-loading="loading">
    <el-alert
      v-if="loadError"
      type="error"
      show-icon
      :closable="false"
      class="mb-4"
      :title="`仪表盘数据加载失败：${loadError}`"
    />

    <!-- ① 真实统计卡片 -->
    <el-row :gutter="24" justify="space-around">
      <re-col
        v-for="item in cards"
        :key="item.key"
        class="mb-4.5"
        :value="4"
        :xs="12"
        :sm="8"
        :md="4"
      >
        <el-card class="line-card" shadow="never">
          <div class="flex justify-between items-center">
            <span class="text-md font-medium">{{ item.name }}</span>
            <div
              class="size-8 flex-c rounded-md"
              :style="{ backgroundColor: item.bg }"
            >
              <div
                class="size-2.5 rounded-full"
                :style="{ backgroundColor: item.color }"
              />
            </div>
          </div>
          <div class="flex items-end justify-between mt-3">
            <ReNormalCountTo
              :duration="1200"
              :fontSize="'1.5em'"
              :startVal="0"
              :endVal="item.value"
            />
            <span class="text-xs text-text_color_regular mb-1">{{ item.unit }}</span>
          </div>
        </el-card>
      </re-col>

      <!-- ② 文章发布趋势（近 30 天） -->
      <re-col class="mb-4.5" :value="12" :xs="24">
        <el-card shadow="never">
          <div class="flex justify-between items-center">
            <span class="text-md font-medium">文章发布趋势（近 30 天）</span>
            <span class="text-xs text-text_color_regular">共 {{ postTotal }} 篇</span>
          </div>
          <div class="bar-wrap">
            <div
              v-for="(d, i) in postTrend"
              :key="i"
              class="bar"
              :style="{
                height: barPct(d.count, postMax) + '%',
                backgroundColor: d.count ? '#41b6ff' : 'rgba(148,163,184,0.22)'
              }"
              :title="d.date + ' · ' + d.count + ' 篇'"
            />
          </div>
          <div class="flex justify-between mt-2 text-xs text-text_color_regular">
            <span>{{ postTrend[0] ? postTrend[0].date : "" }}</span>
            <span>{{ postTrend[postTrend.length - 1] ? postTrend[postTrend.length - 1].date : "" }}</span>
          </div>
        </el-card>
      </re-col>

      <!-- ③ 访客趋势（近 30 天） -->
      <re-col class="mb-4.5" :value="12" :xs="24">
        <el-card shadow="never">
          <div class="flex justify-between items-center">
            <span class="text-md font-medium">访客趋势（近 30 天）</span>
            <span class="text-xs text-text_color_regular">共 {{ visitorTotal }} 人次</span>
          </div>
          <div class="bar-wrap">
            <div
              v-for="(d, i) in visitorTrend"
              :key="i"
              class="bar"
              :style="{
                height: barPct(d.count, visitorMax) + '%',
                backgroundColor: d.count ? '#26ce83' : 'rgba(148,163,184,0.22)'
              }"
              :title="d.date + ' · ' + d.count + ' 人次'"
            />
          </div>
          <div class="flex justify-between mt-2 text-xs text-text_color_regular">
            <span>{{ visitorTrend[0] ? visitorTrend[0].date : "" }}</span>
            <span>{{ visitorTrend[visitorTrend.length - 1] ? visitorTrend[visitorTrend.length - 1].date : "" }}</span>
          </div>
        </el-card>
      </re-col>

      <!-- ④ 分类分布 -->
      <re-col class="mb-4.5" :value="12" :xs="24">
        <el-card shadow="never">
          <span class="text-md font-medium">分类分布</span>
          <div v-if="!categoryDist.length" class="empty-tip">暂无数据</div>
          <div
            v-for="(item, i) in categoryDist"
            :key="i"
            class="dist-row"
          >
            <el-progress
              :text-inside="true"
              :percentage="item.percentage"
              :stroke-width="20"
              :color="item.color"
              striped
              striped-flow
              :duration="90"
            />
            <span class="dist-label">{{ item.name }} · {{ item.value }}</span>
          </div>
        </el-card>
      </re-col>

      <!-- ⑤ 浏览器分布 -->
      <re-col class="mb-4.5" :value="12" :xs="24">
        <el-card shadow="never">
          <span class="text-md font-medium">浏览器分布</span>
          <div v-if="!browserDist.length" class="empty-tip">暂无数据</div>
          <div
            v-for="(item, i) in browserDist"
            :key="i"
            class="dist-row"
          >
            <el-progress
              :text-inside="true"
              :percentage="item.percentage"
              :stroke-width="20"
              :color="item.color"
              striped
              striped-flow
              :duration="90"
            />
            <span class="dist-label">{{ item.name }} · {{ item.value }}</span>
          </div>
        </el-card>
      </re-col>

      <!-- ⑥ 最近文章 -->
      <re-col class="mb-4.5" :value="24" :xs="24">
        <el-card shadow="never">
          <div class="flex justify-between items-center mb-3">
            <span class="text-md font-medium">最近文章</span>
            <el-button text type="primary" @click="load">刷新</el-button>
          </div>
          <el-table :data="posts" size="small" stripe>
            <el-table-column prop="id" label="ID" width="64" />
            <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
            <el-table-column prop="category" label="分类" width="120" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag
                  :type="row.status === 'published' ? 'success' : 'info'"
                  size="small"
                >
                  {{ row.status === "published" ? "已发布" : "草稿" }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="发布时间" width="170">
              <template #default="{ row }">{{ fmt(row.published_at) }}</template>
            </el-table-column>
            <el-table-column prop="views" label="浏览" width="80" />
          </el-table>
        </el-card>
      </re-col>
    </el-row>
  </div>
</template>

<style lang="scss" scoped>
:deep(.el-card) {
  --el-card-border-color: none;
}

.bar-wrap {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 140px;
  margin-top: 16px;

  .bar {
    flex: 1;
    border-radius: 3px 3px 0 0;
    transition: all 0.3s;
    cursor: pointer;

    &:hover {
      filter: brightness(1.25);
    }
  }
}

.dist-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 18px;

  :deep(.el-progress--line) {
    width: 70%;
  }
}

.dist-label {
  font-size: 13px;
  white-space: nowrap;
  color: var(--el-text-color-regular);
}

.empty-tip {
  padding: 32px 0;
  font-size: 13px;
  text-align: center;
  color: var(--el-text-color-secondary);
}
</style>
