import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SubProjectSelector from '../components/analysis/SubProjectSelector.vue'

const BASE_SP = { path: '', tech_stack: [], dependencies: {} as never, graph: {} as never, security: {} as never, heuristics: [], oss_score: undefined }

const subProjects = [
  { ...BASE_SP, name: 'frontend', languages: ['TypeScript'] },
  { ...BASE_SP, name: 'backend', languages: ['Python'] },
  { ...BASE_SP, name: 'infra', languages: [] },
]

describe('SubProjectSelector', () => {
  it('renders All button and one button per sub-project', () => {
    const wrapper = mount(SubProjectSelector, {
      props: { subProjects, modelValue: null },
    })
    const buttons = wrapper.findAll('button')
    expect(buttons).toHaveLength(4) // All + 3 sub-projects
    expect(buttons[0].text()).toBe('All')
    expect(buttons[1].text()).toContain('frontend')
    expect(buttons[2].text()).toContain('backend')
    expect(buttons[3].text()).toContain('infra')
  })

  it('All button is active when modelValue is null', () => {
    const wrapper = mount(SubProjectSelector, {
      props: { subProjects, modelValue: null },
    })
    const buttons = wrapper.findAll('button')
    expect(buttons[0].classes()).toContain('subproject-selector__btn--active')
    expect(buttons[1].classes()).not.toContain('subproject-selector__btn--active')
  })

  it('sub-project button is active when modelValue matches', () => {
    const wrapper = mount(SubProjectSelector, {
      props: { subProjects, modelValue: 'backend' },
    })
    const buttons = wrapper.findAll('button')
    expect(buttons[0].classes()).not.toContain('subproject-selector__btn--active')
    expect(buttons[2].classes()).toContain('subproject-selector__btn--active')
  })

  it('clicking All emits update:modelValue with null', async () => {
    const wrapper = mount(SubProjectSelector, {
      props: { subProjects, modelValue: 'backend' },
    })
    await wrapper.findAll('button')[0].trigger('click')
    expect(wrapper.emitted('update:modelValue')).toEqual([[null]])
  })

  it('clicking sub-project emits update:modelValue with name', async () => {
    const wrapper = mount(SubProjectSelector, {
      props: { subProjects, modelValue: null },
    })
    await wrapper.findAll('button')[1].trigger('click')
    expect(wrapper.emitted('update:modelValue')).toEqual([['frontend']])
  })

  it('shows language abbreviation badge', () => {
    const wrapper = mount(SubProjectSelector, {
      props: { subProjects, modelValue: null },
    })
    // frontend → TypeScript → TS
    expect(wrapper.findAll('button')[1].text()).toContain('TS')
    // backend → Python → Py
    expect(wrapper.findAll('button')[2].text()).toContain('Py')
    // infra → no languages → no badge
    expect(wrapper.findAll('button')[3].find('.subproject-selector__lang').exists()).toBe(false)
  })
})
