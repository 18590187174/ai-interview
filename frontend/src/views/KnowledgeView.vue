<template>
  <div class="knowledge-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>知识库</span>
          <span class="header-tip">上传的资料将作为 AI 押题分析的参考资料，结果中会标注被引用的文档</span>
        </div>
      </template>

      <el-form inline>
        <el-form-item>
          <el-upload
            :auto-upload="false"
            :limit="1"
            :on-change="onFileChange"
            :show-file-list="false"
            accept=".pdf,.docx,.txt,.md"
          >
            <el-button type="primary" :loading="uploading">上传文档</el-button>
          </el-upload>
        </el-form-item>
        <el-form-item label="设为公开">
          <el-switch v-model="isPublic" />
        </el-form-item>
        <el-form-item>
          <span class="form-tip">支持 PDF / DOCX / TXT / MD，单个文件不超过 10MB</span>
        </el-form-item>
      </el-form>

      <el-table :data="documents" v-loading="loading" empty-text="暂无文档，先上传一份吧">
        <el-table-column prop="name" label="文档名称" min-width="220" show-overflow-tooltip />
        <el-table-column label="大小" width="100">
          <template #default="{ row }">{{ formatSize(row.size_bytes) }}</template>
        </el-table-column>
        <el-table-column label="可见性" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_public ? 'success' : 'info'" size="small">
              {{ row.is_public ? '公开' : '私有' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="可检索" width="140">
          <template #default="{ row }">
            <el-tag v-if="row.retrievable" type="success" size="small">已就绪</el-tag>
            <el-tooltip v-else :content="row.parse_error || '无法检索'" placement="top">
              <el-tag type="danger" size="small">不可检索</el-tag>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="上传时间" width="180">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="90">
          <template #default="{ row }">
            <el-button
              v-if="!row.is_public"
              link
              type="danger"
              @click="onDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadFile } from 'element-plus'

import {
  deleteDocument,
  listDocuments,
  uploadDocument,
  type KnowledgeDocument,
} from '@/api/knowledge'
import { RequestError } from '@/api/http'

const documents = ref<KnowledgeDocument[]>([])
const loading = ref(false)
const uploading = ref(false)
const isPublic = ref(false)

async function refresh(): Promise<void> {
  loading.value = true
  try {
    documents.value = await listDocuments()
  } catch (error) {
    ElMessage.error(error instanceof RequestError ? error.message : '加载文档列表失败')
  } finally {
    loading.value = false
  }
}

async function onFileChange(file: UploadFile): Promise<void> {
  if (!file.raw) return
  uploading.value = true
  try {
    const created = await uploadDocument(file.raw, isPublic.value)
    ElMessage.success(
      created.retrievable ? `《${created.name}》上传成功，已可被押题引用` : `《${created.name}》已上传，但无法提取文本：${created.parse_error ?? ''}`,
    )
    await refresh()
  } catch (error) {
    ElMessage.error(error instanceof RequestError ? error.message : '上传失败，请稍后重试')
  } finally {
    uploading.value = false
  }
}

async function onDelete(doc: KnowledgeDocument): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定删除《${doc.name}》吗？删除后不再被押题引用。`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await deleteDocument(doc.id)
    ElMessage.success('已删除')
    await refresh()
  } catch (error) {
    ElMessage.error(error instanceof RequestError ? error.message : '删除失败')
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function formatTime(value: string): string {
  return new Date(value).toLocaleString('zh-CN')
}

onMounted(refresh)
</script>

<style scoped>
.knowledge-page {
  max-width: 960px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.form-tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
