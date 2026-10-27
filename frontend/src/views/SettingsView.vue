<template>
  <div class="settings-page">
    <el-card shadow="never" class="llm-card">
        <template #header>
          <div class="card-header">
            <span>模型配置</span>
            <el-tag size="small" :type="llmSourceTag">{{ llmSourceLabel }}</el-tag>
          </div>
        </template>
        <el-form label-width="110px" class="llm-form">
          <el-form-item label="API Key">
            <el-input
              v-model="llmForm.api_key"
              type="password"
              show-password
              clearable
              :placeholder="llmPlaceholder"
              autocomplete="new-password"
            />
          </el-form-item>
          <el-form-item label="Base URL">
            <el-input v-model="llmForm.base_url" placeholder="https://api.deepseek.com" />
          </el-form-item>
          <el-form-item label="模型名">
            <el-input v-model="llmForm.model" placeholder="deepseek-chat" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="llmSaving" @click="onSaveLLM">保存</el-button>
            <span class="form-tip">留空表示保持不变；清除 API Key 后将回落到服务端环境变量</span>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never" class="dict-card">
        <template #header>
          <div class="card-header">
            <span>押题选项字典</span>
          </div>
        </template>
        <el-tabs v-model="activeTab">
        <el-tab-pane
          v-for="group in groups"
          :key="group.type"
          :label="group.title"
          :name="group.type"
        >
          <el-form inline class="add-form" @submit.prevent>
            <el-form-item>
              <el-input
                v-model="group.draft"
                :placeholder="group.placeholder"
                maxlength="80"
                clearable
                @keyup.enter="onAdd(group)"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="group.saving" @click="onAdd(group)">
                添加
              </el-button>
            </el-form-item>
          </el-form>

          <el-table
            :data="itemsOf(group.type)"
            v-loading="loading"
            empty-text="暂无选项，添加后将在押题向导中生效"
          >
            <el-table-column prop="label" label="名称" min-width="200" show-overflow-tooltip />
            <el-table-column prop="value" label="存储值" min-width="160" show-overflow-tooltip />
            <el-table-column label="操作" width="90">
              <template #default="{ row }">
                <el-button link type="danger" @click="onDelete(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { RequestError } from '@/api/http'
import {
  createItem,
  deleteItem,
  listAll,
  type DictItem,
  type DictType,
} from '@/api/dictionary'
import { getLLMSettings, updateLLMSettings } from '@/api/settings'

interface Group {
  type: DictType
  title: string
  placeholder: string
  draft: string
  saving: boolean
}

const groups = reactive<Group[]>([
  { type: 'target_role', title: '目标岗位', placeholder: '如：Python 后端工程师', draft: '', saving: false },
  { type: 'programming_language', title: '编程语言', placeholder: '如：Python', draft: '', saving: false },
])

const activeTab = ref<DictType>('target_role')
const items = ref<DictItem[]>([])
const loading = ref(false)

const itemsOf = computed(() => (type: DictType) => items.value.filter((item) => item.type === type))

async function refresh(): Promise<void> {
  loading.value = true
  try {
    items.value = await listAll()
  } catch (error) {
    ElMessage.error(error instanceof RequestError ? error.message : '加载字典失败')
  } finally {
    loading.value = false
  }
}

async function onAdd(group: Group): Promise<void> {
  const label = group.draft.trim()
  if (!label) {
    ElMessage.warning('请输入名称')
    return
  }
  group.saving = true
  try {
    await createItem({ type: group.type, label })
    ElMessage.success(`已添加「${label}」`)
    group.draft = ''
    await refresh()
  } catch (error) {
    ElMessage.error(error instanceof RequestError ? error.message : '添加失败')
  } finally {
    group.saving = false
  }
}

async function onDelete(item: DictItem): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定删除「${item.label}」吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await deleteItem(item.id)
    ElMessage.success('已删除')
    await refresh()
  } catch (error) {
    ElMessage.error(error instanceof RequestError ? error.message : '删除失败')
  }
}

onMounted(() => {
  refresh()
  refreshLLM()
})

// ===== 模型配置 =====
const llmForm = reactive({ api_key: '', base_url: '', model: '' })
const llmMasked = ref<string | null>(null)
const llmSource = ref<'database' | 'environment' | 'none'>('none')
const llmSaving = ref(false)

const llmPlaceholder = computed(() =>
  llmMasked.value ? `已配置（${llmMasked.value}），留空保持不变` : '尚未配置，请输入 API Key',
)

const llmSourceLabel = computed(
  () => ({ database: '数据库配置', environment: '环境变量', none: '未配置' })[llmSource.value],
)

const llmSourceTag = computed(() =>
  llmSource.value === 'none' ? 'danger' : llmSource.value === 'database' ? 'success' : 'info',
)

async function refreshLLM(): Promise<void> {
  try {
    const data = await getLLMSettings()
    llmMasked.value = data.api_key_masked
    llmSource.value = data.source
    llmForm.base_url = data.base_url
    llmForm.model = data.model
    llmForm.api_key = ''
  } catch (error) {
    ElMessage.error(error instanceof RequestError ? error.message : '加载模型配置失败')
  }
}

async function onSaveLLM(): Promise<void> {
  llmSaving.value = true
  try {
    const payload: Record<string, string> = {
      base_url: llmForm.base_url.trim(),
      model: llmForm.model.trim(),
    }
    if (llmForm.api_key.trim()) {
      payload.api_key = llmForm.api_key.trim()
    }
    const result = await updateLLMSettings(payload)
    ElMessage.success(result.message)
    await refreshLLM()
  } catch (error) {
    ElMessage.error(error instanceof RequestError ? error.message : '保存失败')
  } finally {
    llmSaving.value = false
  }
}
</script>

<style scoped>
.settings-page {
  max-width: 860px;
  margin: 0 auto;
}

.llm-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-tip {
  font-size: 12px;
  color: var(--text-secondary);
}

.llm-form {
  max-width: 520px;
}

.form-tip {
  margin-left: 12px;
  font-size: 12px;
  color: var(--text-secondary);
}

.add-form {
  margin-bottom: 8px;
}
</style>
