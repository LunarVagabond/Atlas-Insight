import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AppButton from '../components/ui/AppButton.vue'

function make(props = {}, slot = 'Click me') {
  return mount(AppButton, { props, slots: { default: slot } })
}

describe('AppButton — rendering', () => {
  it('renders slot content', () => {
    const w = make({}, 'Save')
    expect(w.text()).toContain('Save')
  })

  it('defaults to primary variant class', () => {
    const w = make()
    expect(w.find('button').classes()).toContain('btn--primary')
  })

  it('applies secondary variant class', () => {
    const w = make({ variant: 'secondary' })
    expect(w.find('button').classes()).toContain('btn--secondary')
  })

  it('applies lg size class', () => {
    const w = make({ size: 'lg' })
    expect(w.find('button').classes()).toContain('btn--lg')
  })

  it('applies sm size class', () => {
    const w = make({ size: 'sm' })
    expect(w.find('button').classes()).toContain('btn--sm')
  })

  it('defaults type to button', () => {
    const w = make()
    expect((w.find('button').element as HTMLButtonElement).type).toBe('button')
  })

  it('respects type=submit', () => {
    const w = make({ type: 'submit' })
    expect((w.find('button').element as HTMLButtonElement).type).toBe('submit')
  })
})

describe('AppButton — disabled state', () => {
  it('disabled prop disables button', () => {
    const w = make({ disabled: true })
    expect((w.find('button').element as HTMLButtonElement).disabled).toBe(true)
  })

  it('loading prop disables button', () => {
    const w = make({ loading: true })
    expect((w.find('button').element as HTMLButtonElement).disabled).toBe(true)
  })

  it('not disabled by default', () => {
    const w = make()
    expect((w.find('button').element as HTMLButtonElement).disabled).toBe(false)
  })
})

describe('AppButton — loading spinner', () => {
  it('shows spinner when loading', () => {
    const w = make({ loading: true })
    expect(w.find('.spinner').exists()).toBe(true)
  })

  it('hides spinner when not loading', () => {
    const w = make({ loading: false })
    expect(w.find('.spinner').exists()).toBe(false)
  })
})
