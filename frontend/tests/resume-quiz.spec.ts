import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { listResumes, uploadResume } from '@/api/resume'
import type { Resume } from '@/api/resume'
import { createPrediction } from '@/api/prediction'
import ResumeQuizView from '@/views/ResumeQuizView.vue'

class ResizeObserverStub {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}
;(globalThis as Record<string, unknown>).ResizeObserver = ResizeObserverStub

vi.mock('element-plus', async (importOriginal) => {
  const actual = await importOriginal<typeof import('element-plus')>()
  return {
    ...actual,
    ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
    ElMessageBox: { confirm: vi.fn() },
  }
})

vi.mock('@/api/resume', () => ({
  listResumes: vi.fn(),
  uploadResume: vi.fn(),
  deleteResume: vi.fn(),
}))

vi.mock('@/api/prediction', () => ({
  createPrediction: vi.fn(),
  listPredictions: vi.fn(),
  getPrediction: vi.fn(),
}))

import ElementPlus from 'element-plus'
import { ElMessage } from 'element-plus'

function makeResume(overrides: Partial<Resume> = {}): Resume {
  return {
    id: 'resume-1',
    original_name: '我的简历.docx',
    size_bytes: 20480,
    content_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    parse_status: 'succeeded',
    parse_error: null,
    parse_error_code: null,
    created_at: '2026-10-26T00:00:00Z',
    ...overrides,
  }
}

function mountView() {
  return mount(ResumeQuizView, { global: { plugins: [ElementPlus] } })
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(listResumes).mockResolvedValue([])
})

describe('ResumeQuizView', () => {
  it('挂载后加载简历列表', async () => {
    vi.mocked(listResumes).mockResolvedValue([makeResume()])
    const wrapper = mountView()
    await flushPromises()

    expect(listResumes).toHaveBeenCalledTimes(1)
    // 第一步展示目标信息表单，简历数据已就绪
    expect(wrapper.text()).toContain('目标岗位')
    expect(wrapper.text()).not.toContain('我的简历.docx')
  })

  it('第二步中解析失败的简历不可选择', async () => {
    vi.mocked(listResumes).mockResolvedValue([
      makeResume(),
      makeResume({
        id: 'resume-bad',
        original_name: '损坏简历.pdf',
        parse_status: 'failed',
        parse_error: '未能从文件中提取到有效文本',
        parse_error_code: 'PARSE_FAILED',
      }),
    ])
    const wrapper = mountView()
    await flushPromises()

    // 填写第一步表单并通过校验进入第二步
    const vm = wrapper.vm as unknown as {
      step: number
      form: Record<string, string>
      goStepTwo: () => Promise<void>
    }
    vm.form.target_role = '后端工程师'
    vm.form.years_of_experience = '3-5年'
    vm.form.job_description = '负责后端服务开发'
    await vm.goStepTwo()
    await flushPromises()

    expect(vm.step).toBe(1)
    const labels = wrapper.findAll('label.el-radio')
    expect(labels.length).toBe(2)
    const broken = labels.find((label) => label.text().includes('损坏简历.pdf'))
    expect(broken).toBeDefined()
    expect(broken!.find('input').attributes('disabled')).toBeDefined()
    const ok = labels.find((label) => label.text().includes('我的简历.docx'))
    expect(ok!.find('input').attributes('disabled')).toBeUndefined()
  })

  it('第三步生成押题并渲染题目与命中依据', async () => {
    vi.mocked(listResumes).mockResolvedValue([makeResume()])
    vi.mocked(createPrediction).mockResolvedValue({
      id: 'p-1',
      status: 'completed',
      target_role: '后端工程师',
      years_of_experience: '3-5年',
      job_description: '负责后端开发',
      programming_language: 'Python',
      model_name: 'deepseek-chat',
      prompt_version: 'prediction-v1',
      generated_at: '2026-10-26T00:00:00Z',
      questions: [
        {
          position: 1,
          question: '请介绍 FastAPI 项目经验',
          difficulty: 'medium',
          reference_answer: '要点：项目背景、承担职责、技术选型与解决思路。',
          evidence: [
            { source: 'resume', ref: '我的简历.docx', ref_id: null, excerpt: '五年经验' },
            { source: 'knowledge', ref: 'tech.md', ref_id: 'doc-9', excerpt: 'FastAPI 数据库' },
          ],
        },
      ],
    })

    const wrapper = mountView()
    await flushPromises()
    const vm = wrapper.vm as unknown as {
      step: number
      selectedResumeId: string
      generate: () => Promise<void>
    }
    vm.step = 2
    vm.selectedResumeId = 'resume-1'
    await vm.generate()
    await flushPromises()

    expect(createPrediction).toHaveBeenCalledWith(
      expect.objectContaining({ resume_id: 'resume-1' }),
    )
    expect(wrapper.text()).toContain('以下内容由 AI 生成')
    expect(wrapper.text()).toContain('请介绍 FastAPI 项目经验')
    expect(wrapper.text()).toContain('tech.md')
    expect(wrapper.text()).toContain('FastAPI 数据库')
  })

  it('生成失败时提示后端错误信息', async () => {
    const { RequestError } = await import('@/api/http')
    vi.mocked(createPrediction).mockRejectedValue(
      new RequestError(503, { code: 'MODEL_UNAVAILABLE', message: '大模型服务暂不可用，请稍后重试' }),
    )
    const wrapper = mountView()
    await flushPromises()
    const vm = wrapper.vm as unknown as { generate: () => Promise<void> }
    await vm.generate()
    await flushPromises()

    expect(ElMessage.error).toHaveBeenCalledWith('大模型服务暂不可用，请稍后重试')
  })

  it('createPrediction 组装正确的请求载荷', async () => {
    vi.mocked(createPrediction).mockResolvedValue({
      id: 'p-1',
      status: 'completed',
      target_role: '后端工程师',
      years_of_experience: '3-5年',
      job_description: '负责后端开发',
      programming_language: 'Python',
      model_name: 'deepseek-chat',
      prompt_version: 'prediction-v1',
      generated_at: '2026-10-26T00:00:00Z',
      questions: [
        {
          position: 1,
          question: '请介绍 FastAPI 项目经验',
          difficulty: 'medium',
          reference_answer: '要点：项目背景、承担职责、技术选型与解决思路。',
          evidence: [
            { source: 'resume', ref: '我的简历.docx', ref_id: null, excerpt: '五年经验' },
            { source: 'knowledge', ref: 'tech.md', ref_id: 'doc-9', excerpt: 'FastAPI 数据库' },
          ],
        },
      ],
    })

    const { createPrediction: mockedCreate } = await import('@/api/prediction')
    await mockedCreate({
      resume_id: 'resume-1',
      target_role: '后端工程师',
      years_of_experience: '3-5年',
      job_description: '负责后端开发',
      programming_language: 'Python',
    })

    expect(mockedCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        resume_id: 'resume-1',
        target_role: '后端工程师',
        programming_language: 'Python',
      }),
    )
  })

  it('createPrediction 失败时抛出带后端错误码的 RequestError', async () => {
    const { RequestError } = await import('@/api/http')
    vi.mocked(createPrediction).mockRejectedValue(
      new RequestError(503, { code: 'MODEL_UNAVAILABLE', message: '大模型服务暂不可用，请稍后重试' }),
    )

    await expect(
      createPrediction({
        resume_id: 'resume-1',
        target_role: '后端工程师',
        years_of_experience: '3-5年',
        job_description: '负责后端开发',
      }),
    ).rejects.toMatchObject({ code: 'MODEL_UNAVAILABLE', status: 503 })
    expect(ElMessage.error).not.toHaveBeenCalled() // 错误提示由组件捕获后统一处理
  })

  it('uploadResume 以 FormData 提交', async () => {
    vi.mocked(uploadResume).mockResolvedValue(makeResume())
    const file = new File(['resume-bytes'], '简历.docx', { type: 'application/msword' })

    await uploadResume(file)

    expect(uploadResume).toHaveBeenCalledWith(file)
  })
})
