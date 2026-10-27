<template>
  <div class="interview-page">
    <!-- 发起 / 恢复选择 -->
    <template v-if="mode === 'pick'">
      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>开始面试</span>
            <span class="header-tip">基于押题记录进行一问一答模拟面试</span>
          </div>
        </template>

        <template v-if="ongoingSessions.length > 0">
          <h4 class="section-title">进行中的面试</h4>
          <div class="session-cards">
            <el-card
              v-for="item in ongoingSessions"
              :key="item.id"
              shadow="hover"
              class="mini-card"
              @click="resumeSession(item.id)"
            >
              <div class="mini-card-body">
                <span class="mini-title">{{ item.target_role }}</span>
                <el-progress
                  :percentage="Math.round((item.answered_count / item.total_questions) * 100)"
                  :stroke-width="8"
                  class="mini-progress"
                />
                <span class="mini-meta">{{ item.answered_count }}/{{ item.total_questions }} 题已答 · 点击继续</span>
              </div>
            </el-card>
          </div>
        </template>

        <h4 class="section-title">发起新面试</h4>
        <div v-if="loading" v-loading="true" class="loading-block" />
        <el-empty
          v-else-if="predictions.length === 0"
          description="还没有押题记录，先去完成一次简历押题，再回来开始面试"
        >
          <router-link :to="{ name: 'resume-quiz' }">
            <el-button type="primary">去简历押题</el-button>
          </router-link>
        </el-empty>
        <div v-else class="session-cards">
          <el-card
            v-for="item in predictions"
            :key="item.id"
            shadow="hover"
            class="mini-card"
            @click="onStart(item.id)"
          >
            <div class="mini-card-body">
              <span class="mini-title">{{ item.target_role }} · {{ item.years_of_experience }}</span>
              <span class="mini-meta">
                {{ item.question_count }} 道押题 · 生成于 {{ formatTime(item.generated_at) }}
              </span>
              <span class="mini-cta">开始面试 →</span>
            </div>
          </el-card>
        </div>

        <template v-if="pastSessions.length > 0">
          <h4 class="section-title">历史面试</h4>
          <el-table class="history-table" :data="pastSessions" size="small">
            <el-table-column prop="target_role" label="岗位" min-width="160" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.status === 'completed' ? 'success' : 'info'" size="small">
                  {{ row.status === 'completed' ? '已完成' : '已放弃' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="作答" width="90">
              <template #default="{ row }">{{ row.answered_count }}/{{ row.total_questions }}</template>
            </el-table-column>
            <el-table-column label="操作" width="90">
              <template #default="{ row }">
                <el-button link type="primary" @click="viewHistory(row.id)">查看</el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- 移动端卡片列表 -->
          <div class="history-cards">
            <el-card v-for="row in pastSessions" :key="row.id" shadow="never" class="history-card">
              <div class="history-row">
                <span class="history-role">{{ row.target_role }}</span>
                <el-tag :type="row.status === 'completed' ? 'success' : 'info'" size="small">
                  {{ row.status === 'completed' ? '已完成' : '已放弃' }}
                </el-tag>
              </div>
              <div class="history-meta">
                <span>作答 {{ row.answered_count }}/{{ row.total_questions }}</span>
                <el-button link type="primary" size="small" @click="viewHistory(row.id)">查看</el-button>
              </div>
            </el-card>
          </div>
        </template>
      </el-card>
    </template>

    <!-- 面试进行中 / 详情 -->
    <template v-else>
      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <el-button link @click="backToPick">← 返回</el-button>
            <span class="header-title">{{ active?.target_role }}</span>
            <el-tag size="small" :type="statusTag">{{ statusLabel }}</el-tag>
          </div>
        </template>

        <div class="progress-row">
          <el-progress
            :percentage="progressPercent"
            :stroke-width="10"
            :format="() => `${answeredCount} / ${active?.total_questions ?? 0}`"
          />
          <el-button
            v-if="active?.status === 'ongoing'"
            link
            type="danger"
            @click="onAbandon"
          >
            放弃面试
          </el-button>
        </div>

        <div class="messages" ref="messagesBox">
          <div
            v-for="(message, index) in active?.messages ?? []"
            :key="index"
            class="message-row"
            :class="message.role"
          >
            <div class="bubble">
              <span v-if="message.role === 'interviewer'" class="msg-position">第 {{ message.position }} 题</span>
              <span class="msg-content">{{ message.skipped ? '（已跳过本题）' : message.content }}</span>
            </div>
          </div>
          <div v-if="active?.status === 'completed'" class="finish-banner">
            面试完成！全部问答已记录，评分报告将在后续版本提供。
          </div>
          <div v-else-if="active?.status === 'abandoned'" class="finish-banner muted">
            该面试已放弃。
          </div>
        </div>

        <template v-if="active?.status === 'ongoing'">
          <el-input
            v-model="answerDraft"
            type="textarea"
            :rows="4"
            :maxlength="5000"
            show-word-limit
            placeholder="输入你的回答（可以结合语音输入）"
            class="answer-input"
          />
          <div class="answer-actions">
            <el-button
              v-if="speechSupported"
              :type="listening ? 'danger' : 'default'"
              :loading="listening"
              @click="toggleSpeech"
            >
              {{ listening ? '正在聆听…点击结束' : '语音输入' }}
            </el-button>
            <el-button :disabled="submitting" @click="onSkip">跳过本题</el-button>
            <el-button
              type="primary"
              :loading="submitting"
              :disabled="!answerDraft.trim()"
              @click="onSubmitAnswer"
            >
              提交回答
            </el-button>
          </div>
        </template>
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: 'InterviewView' })

import { computed, nextTick, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { RequestError } from '@/api/http'
import {
  abandonInterview,
  getInterview,
  listInterviews,
  skipQuestion,
  startInterview,
  submitAnswer,
  type InterviewSession,
  type InterviewSummary,
  type QuestionItem,
} from '@/api/interview'
import { listPredictions, type PredictionSummary } from '@/api/prediction'

const mode = ref<'pick' | 'session'>('pick')
const loading = ref(false)
const submitting = ref(false)

const predictions = ref<PredictionSummary[]>([])
const sessions = ref<InterviewSummary[]>([])
const active = ref<InterviewSession | null>(null)
const activeQuestions = ref<QuestionItem[]>([])
const answerDraft = ref('')
const messagesBox = ref<HTMLElement>()

const ongoingSessions = computed(() => sessions.value.filter((s) => s.status === 'ongoing'))
const pastSessions = computed(() => sessions.value.filter((s) => s.status !== 'ongoing'))

const answeredCount = computed(() => {
  if (!active.value) return 0
  const skipped = active.value.messages.filter((m) => m.role === 'answerer' && m.skipped).length
  return active.value.messages.filter((m) => m.role === 'answerer').length - skipped + skipped
})

const progressPercent = computed(() => {
  if (!active.value || active.value.total_questions === 0) return 0
  if (active.value.status === 'completed') return 100
  const done = active.value.current_position - 1
  return Math.round((done / active.value.total_questions) * 100)
})

const statusLabel = computed(() =>
  ({ ongoing: '进行中', completed: '已完成', abandoned: '已放弃' })[active.value?.status ?? 'ongoing'],
)
const statusTag = computed(() =>
  active.value?.status === 'completed' ? 'success' : active.value?.status === 'ongoing' ? 'primary' : 'info',
)

async function refresh(): Promise<void> {
  loading.value = true
  try {
    const [sessionList, predictionList] = await Promise.all([listInterviews(), listPredictions()])
    sessions.value = sessionList
    predictions.value = predictionList
  } catch (error) {
    ElMessage.error(error instanceof RequestError ? error.message : '加载数据失败')
  } finally {
    loading.value = false
  }
}

async function onStart(predictionId: string): Promise<void> {
  try {
    const result = await startInterview(predictionId)
    active.value = result.interview
    activeQuestions.value = result.questions
    mode.value = 'session'
    await refresh()
    scrollToBottom()
  } catch (error) {
    if (error instanceof RequestError) {
      ElMessage.warning(error.message)
      if (error.code === 'INTERVIEW_ALREADY_ONGOING') {
        await refresh()
      }
    } else {
      ElMessage.error('发起面试失败')
    }
  }
}

async function resumeSession(id: string): Promise<void> {
  try {
    const session = await getInterview(id)
    active.value = session
    // 从面试官消息重建题目列表（历史消息即题目文本）
    activeQuestions.value = session.messages
      .filter((m) => m.role === 'interviewer')
      .map((m) => ({
        position: m.position,
        question: m.content ?? '',
        difficulty: 'medium',
        reference_answer: null,
      }))
    mode.value = 'session'
    scrollToBottom()
  } catch (error) {
    ElMessage.error(error instanceof RequestError ? error.message : '恢复会话失败')
  }
}

async function viewHistory(id: string): Promise<void> {
  await resumeSession(id)
}

function backToPick(): void {
  mode.value = 'pick'
  active.value = null
  answerDraft.value = ''
  refresh()
}

async function onSubmitAnswer(): Promise<void> {
  if (!active.value) return
  const content = answerDraft.value.trim()
  if (!content) return
  submitting.value = true
  try {
    const result = await submitAnswer(active.value.id, content)
    active.value = result.interview
    activeQuestions.value = result.questions
    answerDraft.value = ''
    scrollToBottom()
  } catch (error) {
    ElMessage.error(error instanceof RequestError ? error.message : '提交失败，请重试')
  } finally {
    submitting.value = false
  }
}

async function onSkip(): Promise<void> {
  if (!active.value) return
  try {
    await ElMessageBox.confirm('确定跳过本题吗？跳过后不可回补回答。', '跳过确认', {
      type: 'warning',
      confirmButtonText: '跳过',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  submitting.value = true
  try {
    const result = await skipQuestion(active.value.id)
    active.value = result.interview
    activeQuestions.value = result.questions
    answerDraft.value = ''
    scrollToBottom()
  } catch (error) {
    ElMessage.error(error instanceof RequestError ? error.message : '操作失败')
  } finally {
    submitting.value = false
  }
}

async function onAbandon(): Promise<void> {
  if (!active.value) return
  try {
    await ElMessageBox.confirm('确定放弃本次面试吗？放弃后不可继续作答。', '放弃确认', {
      type: 'warning',
      confirmButtonText: '放弃',
      cancelButtonText: '继续面试',
    })
  } catch {
    return
  }
  try {
    await abandonInterview(active.value.id)
    ElMessage.success('已放弃')
    backToPick()
  } catch (error) {
    ElMessage.error(error instanceof RequestError ? error.message : '操作失败')
  }
}

function scrollToBottom(): void {
  nextTick(() => {
    messagesBox.value?.scrollTo({ top: messagesBox.value.scrollHeight, behavior: 'smooth' })
  })
}

function formatTime(value: string): string {
  return new Date(value).toLocaleString('zh-CN')
}

// ===== 语音输入：浏览器 Web Speech API，转写填入输入框，由用户手动提交 =====
interface SpeechRecognitionLike {
  lang: string
  continuous: boolean
  interimResults: boolean
  onresult: ((event: unknown) => void) | null
  onerror: (() => void) | null
  onend: (() => void) | null
  start(): void
  stop(): void
}

const listening = ref(false)
let recognition: SpeechRecognitionLike | null = null

const speechSupported = computed(() => {
  const w = globalThis as unknown as Record<string, unknown>
  return Boolean(w.SpeechRecognition ?? w.webkitSpeechRecognition)
})

function toggleSpeech(): void {
  if (listening.value) {
    recognition?.stop()
    return
  }
  const w = globalThis as unknown as Record<string, unknown>
  const Ctor = (w.SpeechRecognition ?? w.webkitSpeechRecognition) as
    | (new () => SpeechRecognitionLike)
    | undefined
  if (!Ctor) {
    ElMessage.warning('当前浏览器不支持语音识别，请直接打字作答')
    return
  }
  recognition = new Ctor()
  recognition.lang = 'zh-CN'
  recognition.continuous = false
  recognition.interimResults = false
  recognition.onresult = (event: unknown) => {
    const results = (event as { results: ArrayLike<ArrayLike<{ transcript: string }>> }).results
    let transcript = ''
    for (let i = 0; i < results.length; i += 1) {
      transcript += results[i][0].transcript
    }
    answerDraft.value = answerDraft.value
      ? `${answerDraft.value}${transcript}`
      : transcript
  }
  recognition.onerror = () => {
    listening.value = false
    recognition = null
    ElMessage.warning('语音识别失败，请改用打字作答')
  }
  recognition.onend = () => {
    listening.value = false
  }
  listening.value = true
  recognition.start()
}

onMounted(refresh)
</script>

<style scoped>
.interview-page {
  max-width: 860px;
  margin: 0 auto;
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

.header-title {
  font-weight: 700;
  color: var(--text-primary);
}

.section-title {
  margin: 20px 0 12px;
  font-size: 14px;
  color: var(--text-secondary);
}

.session-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 14px;
}

.mini-card {
  cursor: pointer;
  transition:
    transform var(--transition-ui),
    border-color var(--transition-ui);
}

.mini-card:hover {
  transform: translateY(-2px);
  border-color: var(--surface-border-hover);
}

.mini-card-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mini-title {
  font-weight: 600;
  color: var(--text-primary);
}

.mini-meta {
  font-size: 12px;
  color: var(--text-secondary);
}

.mini-cta {
  font-size: 13px;
  font-weight: 600;
  color: var(--brand-cyan);
}

.loading-block {
  height: 120px;
}

.progress-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.progress-row .el-progress {
  flex: 1;
}

.messages {
  max-height: calc(100dvh - 420px);
  min-height: 220px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 4px;
}

.message-row {
  display: flex;
}

.message-row.answerer {
  justify-content: flex-end;
}

.bubble {
  max-width: 78%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.7;
  background: var(--surface-glass);
  border: 1px solid var(--surface-border);
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-word;
}

.message-row.interviewer .bubble {
  border-left: 3px solid var(--brand-blue);
}

.message-row.answerer .bubble {
  background: var(--brand-gradient-soft);
  border-color: rgba(37, 99, 235, 0.3);
}

.msg-position {
  display: block;
  margin-bottom: 4px;
  font-size: 11px;
  letter-spacing: 1px;
  color: var(--brand-cyan);
}

.finish-banner {
  padding: 14px;
  border-radius: 10px;
  text-align: center;
  background: var(--brand-gradient-soft);
  border: 1px solid rgba(37, 99, 235, 0.3);
  color: var(--brand-blue);
  font-weight: 600;
}

.finish-banner.muted {
  color: var(--text-secondary);
}

.answer-input {
  margin-top: 16px;
}

.answer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 12px;
}

/* 移动端：历史表格 → 卡片列表 */
.history-cards {
  display: none;
}

@media (max-width: 768px) {
  .history-table {
    display: none;
  }

  .history-cards {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .history-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .history-role {
    font-weight: 600;
    color: var(--text-primary);
  }

  .history-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 6px;
    font-size: 12px;
    color: var(--text-secondary);
  }
}
</style>
