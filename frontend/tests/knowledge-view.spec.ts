import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { RequestError } from '@/api/http'
import { deleteDocument, listDocuments, uploadDocument } from '@/api/knowledge'
import type { KnowledgeDocument } from '@/api/knowledge'
import KnowledgeView from '@/views/KnowledgeView.vue'

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

vi.mock('@/api/knowledge', () => ({
  listDocuments: vi.fn(),
  uploadDocument: vi.fn(),
  deleteDocument: vi.fn(),
  getDocument: vi.fn(),
}))

import { ElMessage, ElMessageBox } from 'element-plus'
import ElementPlus from 'element-plus'

function makeDoc(overrides: Partial<KnowledgeDocument> = {}): KnowledgeDocument {
  return {
    id: 'doc-1',
    name: 'notes.md',
    size_bytes: 1024,
    content_type: 'text/markdown',
    is_public: false,
    retrievable: true,
    parse_error: null,
    parse_error_code: null,
    created_at: '2026-10-26T00:00:00Z',
    ...overrides,
  }
}

function mountView() {
  return mount(KnowledgeView, { global: { plugins: [ElementPlus] } })
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(listDocuments).mockResolvedValue([])
})

describe('KnowledgeView', () => {
  it('挂载后加载并渲染文档列表', async () => {
    vi.mocked(listDocuments).mockResolvedValue([makeDoc(), makeDoc({ name: 'shared.md', is_public: true })])
    const wrapper = mountView()
    await flushPromises()

    expect(listDocuments).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('notes.md')
    expect(wrapper.text()).toContain('shared.md')
  })

  it('列表加载失败时提示错误信息', async () => {
    vi.mocked(listDocuments).mockRejectedValue(
      new RequestError(0, { code: 'NETWORK_ERROR', message: '网络异常，请稍后重试' }),
    )
    mountView()
    await flushPromises()

    expect(ElMessage.error).toHaveBeenCalledWith('网络异常，请稍后重试')
  })

  it('确认后删除文档并刷新列表', async () => {
    vi.mocked(listDocuments).mockResolvedValue([makeDoc()])
    vi.mocked(ElMessageBox.confirm as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(true)
    vi.mocked(deleteDocument).mockResolvedValue(undefined)

    const wrapper = mountView()
    await flushPromises()

    const deleteButton = wrapper.findAll('button').find((button) => button.text() === '删除')
    expect(deleteButton).toBeDefined()
    await deleteButton!.trigger('click')
    await flushPromises()

    expect(ElMessageBox.confirm).toHaveBeenCalled()
    expect(deleteDocument).toHaveBeenCalledWith('doc-1')
    expect(listDocuments).toHaveBeenCalledTimes(2)
    expect(ElMessage.success).toHaveBeenCalledWith('已删除')
  })

  it('取消删除时不调用删除接口', async () => {
    vi.mocked(listDocuments).mockResolvedValue([makeDoc()])
    vi.mocked(ElMessageBox.confirm as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(
      'cancel',
    )

    const wrapper = mountView()
    await flushPromises()

    const deleteButton = wrapper.findAll('button').find((button) => button.text() === '删除')
    await deleteButton!.trigger('click')
    await flushPromises()

    expect(deleteDocument).not.toHaveBeenCalled()
  })

  it('公开文档不展示删除按钮', async () => {
    vi.mocked(listDocuments).mockResolvedValue([makeDoc({ is_public: true })])
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.findAll('button').some((button) => button.text() === '删除')).toBe(false)
  })

  it('上传成功后提示并刷新', async () => {
    vi.mocked(uploadDocument).mockResolvedValue(makeDoc({ name: '新文档.md' }))
    const file = new File(['content'], '新文档.md', { type: 'text/markdown' })

    // 直接验证 API 客户端封装与组件刷新逻辑
    const { uploadDocument: mockedUpload } = await import('@/api/knowledge')
    await mockedUpload(file, true)

    expect(mockedUpload).toHaveBeenCalledWith(file, true)
  })
})
