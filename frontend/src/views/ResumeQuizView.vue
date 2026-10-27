<template>
  <div class="quiz-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>简历押题</span>
          <span class="header-tip">填写目标信息、选择简历，AI 将生成最可能被问到的题目与命中依据</span>
        </div>
      </template>

      <el-steps :active="step" align-center finish-status="success" class="steps">
        <el-step title="面试目标" />
        <el-step title="选择简历" />
        <el-step title="押题结果" />
      </el-steps>

      <!-- 第一步：面试目标信息 -->
      <el-form
        v-if="step === 0"
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="110px"
        class="step-body"
      >
        <el-form-item label="目标岗位" prop="target_role">
          <el-select
            v-model="form.target_role"
            filterable
            allow-create
            default-first-option
            placeholder="选择或输入目标岗位"
            style="width: 100%"
          >
            <el-option v-for="role in roleOptions" :key="role" :label="role" :value="role" />
          </el-select>
        </el-form-item>
        <el-form-item label="工作年限" prop="years_of_experience">
          <el-select v-model="form.years_of_experience" placeholder="选择工作年限" style="width: 100%">
            <el-option v-for="option in yearOptions" :key="option" :label="option" :value="option" />
          </el-select>
        </el-form-item>
        <el-form-item label="岗位描述" prop="job_description">
          <el-input
            v-model="form.job_description"
            type="textarea"
            :rows="8"
            maxlength="2000"
            show-word-limit
            placeholder="粘贴招聘 JD 或岗位要求，AI 将结合简历与其生成押题（必填，≤2000 字）"
          />
        </el-form-item>
        <el-form-item label="编程语言">
          <el-select
            v-model="form.programming_language"
            placeholder="可选"
            clearable
            style="width: 100%"
          >
            <el-option v-for="lang in languageOptions" :key="lang" :label="lang" :value="lang" />
          </el-select>
        </el-form-item>
        <el-form-item class="form-actions">
          <el-button type="primary" @click="goStepTwo">
            下一步
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 第二步：选择或上传简历 -->
      <div v-else-if="step === 1" class="step-body">
        <el-alert
          v-if="hasUnusableResume"
          type="warning"
          :closable="false"
          show-icon
          title="部分简历解析失败，无法用于押题；请删除后重新上传（支持 PDF / DOCX / TXT）"
        />
        <el-radio-group v-model="selectedResumeId" class="resume-list">
          <el-radio
            v-for="resume in resumes"
            :key="resume.id"
            :value="resume.id"
            :disabled="resume.parse_status !== 'succeeded'"
            border
            class="resume-item"
          >
            <span class="resume-name">{{ resume.original_name }}</span>
            <el-tag
              :type="resume.parse_status === 'succeeded' ? 'success' : 'danger'"
              size="small"
            >
              {{ resume.parse_status === 'succeeded' ? '已就绪' : '解析失败' }}
            </el-tag>
            <span class="resume-time">{{ formatTime(resume.created_at) }}</span>
            <el-button
              v-if="resume.parse_status === 'succeeded'"
              link
              type="primary"
              size="small"
              class="preview-button"
              @click.stop="openPreview(resume)"
            >
              预览
            </el-button>
            <el-button
              link
              type="danger"
              size="small"
              class="preview-button"
              @click.stop="onDeleteResume(resume)"
            >
              删除
            </el-button>
          </el-radio>
        </el-radio-group>
        <el-empty v-if="resumes.length === 0 && !loadingResumes" description="还没有简历，先上传一份" />

        <div class="upload-row">
          <el-upload
            :auto-upload="false"
            :show-file-list="false"
            accept=".pdf,.docx,.txt"
            :on-change="onResumeFileChange"
          >
            <el-button :loading="uploading">上传新简历</el-button>
          </el-upload>
        </div>

        <div class="actions">
          <el-button @click="step = 0">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M19 12H5M11 18l-6-6 6-6" />
            </svg>
            上一步
          </el-button>
          <el-button
            type="primary"
            :disabled="!selectedSucceededResume"
            @click="goStepThree"
          >
            下一步
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </el-button>
        </div>
      </div>

      <!-- 第三步：生成与结果 -->
      <div v-else class="step-body">
        <div v-if="!prediction" class="generate-area">
          <el-button type="primary" size="large" :loading="generating" @click="generate">
            {{ generating ? 'AI 分析中，约需数十秒…' : '生成押题' }}
          </el-button>
          <p class="generate-tip">将结合简历、岗位描述与命中的知识库资料生成 {{ QUESTION_HINT }}</p>
          <div class="actions">
            <el-button :disabled="generating" @click="step = 1">上一步</el-button>
          </div>
        </div>

        <template v-else>
          <el-alert
            type="info"
            :closable="false"
            show-icon
            title="以下内容由 AI 生成，仅供参考"
            :description="`模型：${prediction.model_name} · 提示词版本：${prediction.prompt_version} · 生成时间：${formatTime(prediction.generated_at)}`"
          />

          <div class="question-list">
            <el-card
              v-for="question in prediction.questions"
              :key="question.position"
              shadow="never"
              class="question-card"
            >
              <div class="question-head">
                <span class="question-index">Q{{ question.position }}</span>
                <span class="question-text">{{ question.question }}</span>
                <el-tag :type="difficultyTag(question.difficulty)" size="small">
                  {{ difficultyLabel(question.difficulty) }}
                </el-tag>
              </div>
              <div class="evidence-list">
                <div v-for="(item, index) in question.evidence" :key="index" class="evidence-item">
                  <el-tag size="small" :type="sourceTag(item.source)">{{ sourceLabel(item.source) }}</el-tag>
                  <span class="evidence-ref">{{ item.ref }}</span>
                  <span class="evidence-excerpt">「{{ item.excerpt }}」</span>
                </div>
              </div>
              <div
                v-if="question.reference_answer"
                class="answer-toggle"
                @click="toggleAnswer(question.position)"
              >
                <span class="answer-toggle-label">
                  {{ expanded.has(question.position) ? '收起参考答案' : '查看参考答案' }}
                </span>
                <svg
                  viewBox="0 0 24 24"
                  width="14"
                  height="14"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  aria-hidden="true"
                  :class="{ expanded: expanded.has(question.position) }"
                >
                  <path d="M6 9l6 6 6-6" />
                </svg>
              </div>
              <div v-if="expanded.has(question.position)" class="reference-answer">
                {{ question.reference_answer }}
              </div>
            </el-card>
          </div>

          <div class="actions">
            <el-button @click="step = 1">上一步</el-button>
            <el-button @click="restart">再生成一次</el-button>
          </div>
        </template>
      </div>
    </el-card>

    <el-dialog
      v-model="previewVisible"
      :title="previewData?.original_name ?? '简历预览'"
      width="640px"
      top="8vh"
    >
      <div v-if="previewLoading" class="preview-loading" v-loading="true" element-loading-text="加载中…" />
      <pre v-else class="preview-text">{{ previewData?.parsed_text }}</pre>
      <template #footer>
        <el-button @click="previewVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: 'ResumeQuizView' })

import { computed, onActivated, onMounted, reactive, ref } from 'vue'

const expanded = reactive(new Set<number>())

function toggleAnswer(position: number): void {
  if (expanded.has(position)) {
    expanded.delete(position)
  } else {
    expanded.add(position)
  }
}
import { ElMessage, ElMessageBox, type FormInstance, type FormRules, type UploadFile } from 'element-plus'

import { RequestError } from '@/api/http'
import {
  deleteResume,
  listResumes,
  previewResume,
  uploadResume,
  type Resume,
  type ResumePreview,
} from '@/api/resume'
import { createPrediction, type Prediction } from '@/api/prediction'
import { listByType, type DictType } from '@/api/dictionary'

const QUESTION_HINT = '最可能被问到的题目'

// 字典为空或加载失败时的兜底选项；可在「设置」页维护
const FALLBACK_ROLE_OPTIONS = [
  '前端工程师',
  '后端工程师',
  '全栈工程师',
  '算法工程师',
  '测试工程师',
  '数据分析师',
  '产品经理',
]
const FALLBACK_LANGUAGE_OPTIONS = [
  'Python',
  'Java',
  'JavaScript/TypeScript',
  'Go',
  'C++',
  'C#',
  '其他',
]
const yearOptions = ['在校/应届', '1年以内', '1-3年', '3-5年', '5-10年', '10年以上']

const roleOptions = ref<string[]>([...FALLBACK_ROLE_OPTIONS])
const languageOptions = ref<string[]>([...FALLBACK_LANGUAGE_OPTIONS])

async function loadDictOptions(type: DictType, fallback: string[], target: typeof roleOptions) {
  try {
    const items = await listByType(type)
    if (items.length > 0) {
      target.value = items.map((item) => item.label)
    }
  } catch {
    // 字典不可用时静默回退到内置选项
    target.value = [...fallback]
  }
}

const step = ref(0)
const formRef = ref<FormInstance>()
const form = reactive({
  target_role: '',
  years_of_experience: '',
  job_description: '',
  programming_language: '',
})

const rules: FormRules = {
  target_role: [{ required: true, message: '请选择或输入目标岗位', trigger: 'change' }],
  years_of_experience: [{ required: true, message: '请选择工作年限', trigger: 'change' }],
  job_description: [
    { required: true, message: '请填写岗位描述', trigger: 'blur' },
    { max: 2000, message: '岗位描述不能超过 2000 字', trigger: 'blur' },
  ],
}

const resumes = ref<Resume[]>([])
const selectedResumeId = ref('')
const loadingResumes = ref(false)
const uploading = ref(false)
const generating = ref(false)
const prediction = ref<Prediction | null>(null)

const selectedSucceededResume = computed(() => {
  return resumes.value.some(
    (item) => item.id === selectedResumeId.value && item.parse_status === 'succeeded',
  )
})

const hasUnusableResume = computed(() =>
  resumes.value.some((item) => item.parse_status !== 'succeeded'),
)

async function refreshResumes(): Promise<void> {
  loadingResumes.value = true
  try {
    resumes.value = await listResumes()
  } catch (error) {
    ElMessage.error(error instanceof RequestError ? error.message : '加载简历列表失败')
  } finally {
    loadingResumes.value = false
  }
}

async function goStepTwo(): Promise<void> {
  const valid = await formRef.value?.validate().then(
    () => true,
    () => false,
  )
  if (!valid) return
  if (resumes.value.length === 0) {
    await refreshResumes()
  }
  step.value = 1
}

async function onResumeFileChange(file: UploadFile): Promise<void> {
  if (!file.raw) return
  uploading.value = true
  try {
    const created = await uploadResume(file.raw)
    await refreshResumes()
    if (created.parse_status === 'succeeded') {
      selectedResumeId.value = created.id
      ElMessage.success(`《${created.original_name}》上传成功，已就绪`)
    } else {
      ElMessage.warning(`《${created.original_name}》上传成功，但解析失败：${created.parse_error ?? ''}`)
    }
  } catch (error) {
    ElMessage.error(error instanceof RequestError ? error.message : '上传失败，请稍后重试')
  } finally {
    uploading.value = false
  }
}

function goStepThree(): void {
  // 换简历/换配置后进入第三步时，丢弃旧结果以强制重新生成
  prediction.value = null
  step.value = 2
}

const previewVisible = ref(false)
const previewLoading = ref(false)
const previewData = ref<ResumePreview | null>(null)

async function onDeleteResume(resume: Resume): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确定删除《${resume.original_name}》吗？删除后不可恢复，且不能用于押题。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await deleteResume(resume.id)
    if (selectedResumeId.value === resume.id) {
      selectedResumeId.value = ''
    }
    ElMessage.success('已删除')
    await refreshResumes()
  } catch (error) {
    ElMessage.error(error instanceof RequestError ? error.message : '删除失败')
  }
}

async function openPreview(resume: Resume): Promise<void> {
  previewVisible.value = true
  previewLoading.value = true
  previewData.value = null
  try {
    previewData.value = await previewResume(resume.id)
  } catch (error) {
    previewVisible.value = false
    ElMessage.error(error instanceof RequestError ? error.message : '预览加载失败')
  } finally {
    previewLoading.value = false
  }
}

async function generate(): Promise<void> {
  generating.value = true
  try {
    prediction.value = await createPrediction({
      resume_id: selectedResumeId.value,
      target_role: form.target_role,
      years_of_experience: form.years_of_experience,
      job_description: form.job_description,
      programming_language: form.programming_language || undefined,
    })
  } catch (error) {
    ElMessage.error(error instanceof RequestError ? error.message : '押题生成失败，请稍后重试')
  } finally {
    generating.value = false
  }
}

function restart(): void {
  prediction.value = null
}

function difficultyTag(difficulty: string): 'success' | 'warning' | 'danger' | 'info' {
  if (difficulty === 'easy') return 'success'
  if (difficulty === 'hard') return 'danger'
  if (difficulty === 'medium') return 'warning'
  return 'info'
}

function difficultyLabel(difficulty: string): string {
  return { easy: '简单', medium: '中等', hard: '困难' }[difficulty] ?? difficulty
}

function sourceTag(source: string): 'primary' | 'success' | 'warning' {
  if (source === 'resume') return 'primary'
  if (source === 'knowledge') return 'warning'
  return 'success'
}

function sourceLabel(source: string): string {
  return (
    { resume: '简历', job_description: '岗位描述', knowledge: '知识库' }[source] ?? source
  )
}

function formatTime(value: string): string {
  return new Date(value).toLocaleString('zh-CN')
}

onMounted(() => {
  refreshResumes()
  loadDictOptions('target_role', FALLBACK_ROLE_OPTIONS, roleOptions)
  loadDictOptions('programming_language', FALLBACK_LANGUAGE_OPTIONS, languageOptions)
})

// KeepAlive 恢复时静默刷新简历列表，保留用户已填写的状态
onActivated(() => {
  refreshResumes()
})

// 供单元测试驱动向导流程
defineExpose({ step, form, selectedResumeId, resumes, goStepTwo, generate })
</script>

<style scoped>
.quiz-page {
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

.steps {
  margin-bottom: 24px;
}

/* 三种状态图标统一尺寸，保证与主线对齐 */
.steps :deep(.el-step__icon) {
  width: 28px;
  height: 28px;
}

/* 当前步：实心渐变圆 + 对称光环，与已完成步形成明确对比 */
.steps :deep(.el-step__head.is-process .el-step__icon) {
  background: var(--brand-gradient);
  border-color: transparent;
  color: #fff;
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.15);
}

.steps :deep(.el-step__title.is-process) {
  color: var(--brand-blue);
  font-weight: 700;
}

.step-body {
  max-width: 720px;
  margin: 0 auto;
}

.resume-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}

.resume-item {
  width: 100%;
  height: auto;
  padding: 12px;
  margin-right: 0;
}

.resume-name {
  margin-right: 12px;
  font-weight: 600;
}

.resume-time {
  margin-left: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.preview-button {
  margin-left: 12px;
}

.preview-loading {
  height: 320px;
}

.preview-text {
  margin: 0;
  max-height: 56vh;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 13.5px;
  line-height: 1.75;
  color: var(--text-primary);
}

.upload-row {
  margin-top: 16px;
}

.form-actions :deep(.el-form-item__content) {
  display: flex;
  justify-content: flex-end;
  width: 100%;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}

.generate-area {
  padding: 48px 0;
  text-align: center;
}

.generate-tip {
  margin-top: 16px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.question-list {
  max-height: calc(100dvh - 340px);
  min-height: 320px;
  overflow-y: auto;
  padding: 4px 6px;
}

.question-card {
  margin-top: 16px;
}

.answer-toggle {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  margin-top: 12px;
  font-size: 13px;
  color: var(--brand-cyan);
  cursor: pointer;
  user-select: none;
  width: fit-content;
  margin-left: auto;
}

.answer-toggle:hover .answer-toggle-label {
  text-decoration: underline;
}

.answer-toggle svg {
  transition: transform var(--transition-ui);
}

.answer-toggle svg.expanded {
  transform: rotate(180deg);
}

.reference-answer {
  margin-top: 10px;
  padding: 12px 14px;
  border-radius: 10px;
  background: rgba(6, 182, 212, 0.06);
  border: 1px solid rgba(6, 182, 212, 0.18);
  font-size: 13.5px;
  line-height: 1.75;
  color: var(--text-primary);
  white-space: pre-wrap;
}

.question-head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.question-index {
  font-weight: 700;
  color: var(--el-color-primary);
}

.question-text {
  flex: 1;
  font-weight: 600;
}

.evidence-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}

.evidence-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.evidence-ref {
  color: var(--el-text-color-secondary);
}

.evidence-excerpt {
  color: var(--el-text-color-regular);
}
</style>
