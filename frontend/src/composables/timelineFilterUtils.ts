import type { FilterSelection } from '../components/analysis/TimelineFilter.vue'

export function monthInFilter(month: string, selection: FilterSelection): boolean {
  if (selection.year !== 'All' && !month.startsWith(selection.year)) return false
  if (selection.months.size > 0 && !selection.months.has(parseInt(month.slice(5, 7)))) return false
  return true
}

export function commitInDayFilter(isoDate: string, selection: FilterSelection): boolean {
  if (!selection.days.size) return true
  const day = parseInt(isoDate.slice(8, 10))
  const minDay = Math.min(...selection.days)
  const maxDay = Math.max(...selection.days)
  return day >= minDay && day <= maxDay
}

export function isFilterActive(selection: FilterSelection): boolean {
  return selection.year !== 'All' || selection.months.size > 0 || selection.days.size > 0
}
