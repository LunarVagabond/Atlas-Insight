import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import URLInputForm from '../components/analysis/URLInputForm.vue'

vi.mock('../stores/auth', () => ({
  useAuthStore: () => ({
    isAuthenticated: false,
    user: null,
    displayName: '',
    connectGithub: vi.fn(),
  }),
}))

vi.mock('axios', () => ({
  default: { get: vi.fn().mockResolvedValue({ data: [] }) },
}))

const stubs = {
  AppButton: {
    template: '<button :disabled="disabled || loading" @click="$emit(\'click\')"><slot /></button>',
    props: ['loading', 'disabled', 'type', 'size'],
  },
}

function makeWrapper(props = {}) {
  return mount(URLInputForm, { props, global: { stubs } })
}

describe('URLInputForm — rendering', () => {
  it('renders URL input and submit button', () => {
    const w = makeWrapper()
    expect(w.find('input[type="url"]').exists()).toBe(true)
    expect(w.find('button').exists()).toBe(true)
    expect(w.find('button').text()).toContain('Analyze')
  })

  it('populates input from initialUrl prop', () => {
    const w = makeWrapper({ initialUrl: 'https://github.com/foo/bar' })
    expect((w.find('input').element as HTMLInputElement).value).toBe('https://github.com/foo/bar')
  })

  it('disables input when loading', () => {
    const w = makeWrapper({ loading: true })
    expect((w.find('input').element as HTMLInputElement).disabled).toBe(true)
  })

  it('shows external error prop', () => {
    const w = makeWrapper({ error: 'Something went wrong' })
    expect(w.find('.url-form__error').text()).toContain('Something went wrong')
  })
})

describe('URLInputForm — validation', () => {
  it('shows error on empty submit', async () => {
    const w = makeWrapper()
    await w.find('form').trigger('submit')
    expect(w.find('.url-form__error').exists()).toBe(true)
    expect(w.find('.url-form__error').text()).toContain('Please enter a GitHub URL')
  })

  it('shows error for non-GitHub URL', async () => {
    const w = makeWrapper()
    await w.find('input').setValue('https://gitlab.com/foo/bar')
    await w.find('form').trigger('submit')
    expect(w.find('.url-form__error').text()).toContain('valid GitHub repository URL')
  })

  it('shows error for bare domain', async () => {
    const w = makeWrapper()
    await w.find('input').setValue('github.com/foo/bar')
    await w.find('form').trigger('submit')
    expect(w.find('.url-form__error').exists()).toBe(true)
  })

  it('emits submitted with URL for valid GitHub URL', async () => {
    const w = makeWrapper()
    await w.find('input').setValue('https://github.com/owner/repo')
    await w.find('form').trigger('submit')
    expect(w.emitted('submitted')).toBeTruthy()
    expect(w.emitted('submitted')![0][0]).toBe('https://github.com/owner/repo')
  })

  it('button is disabled while loading (prevents user submission)', () => {
    const w = makeWrapper({ loading: true })
    expect((w.find('button').element as HTMLButtonElement).disabled).toBe(true)
  })

  it('strips trailing slash from valid URL before emitting', async () => {
    const w = makeWrapper()
    await w.find('input').setValue('https://github.com/owner/repo/')
    await w.find('form').trigger('submit')
    expect(w.emitted('submitted')![0][0]).toBe('https://github.com/owner/repo/')
  })
})

describe('URLInputForm — PAT toggle', () => {
  it('PAT input hidden by default', () => {
    const w = makeWrapper()
    expect(w.find('.url-form__pat-input').exists()).toBe(false)
  })

  it('PAT input shown after clicking PAT button', async () => {
    const w = makeWrapper()
    await w.find('.url-form__opt-btn').trigger('click')
    expect(w.find('.url-form__pat-input').exists()).toBe(true)
  })

  it('PAT input hidden again on second click', async () => {
    const w = makeWrapper()
    const btn = w.find('.url-form__opt-btn')
    await btn.trigger('click')
    await btn.trigger('click')
    expect(w.find('.url-form__pat-input').exists()).toBe(false)
  })
})
