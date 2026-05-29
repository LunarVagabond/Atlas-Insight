import { ref, computed, type Ref } from 'vue'

export type SortOrder = 'asc' | 'desc'

export function useTableFilter<T extends Record<string, unknown>>(
  source: Ref<T[]>,
  searchKeys: (keyof T)[],
  defaultSortKey: keyof T,
  defaultOrder: SortOrder = 'desc',
) {
  const query = ref('')
  const sortKey = ref(defaultSortKey) as Ref<keyof T>
  const sortOrder = ref<SortOrder>(defaultOrder)

  const filtered = computed(() => {
    let rows = source.value
    const q = query.value.trim().toLowerCase()
    if (q) {
      rows = rows.filter(row =>
        searchKeys.some(k => String(row[k] ?? '').toLowerCase().includes(q))
      )
    }
    const key = sortKey.value
    const asc = sortOrder.value === 'asc' ? 1 : -1
    return [...rows].sort((a, b) => {
      const av = a[key]
      const bv = b[key]
      if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * asc
      return String(av ?? '').localeCompare(String(bv ?? '')) * asc
    })
  })

  function setSort(key: keyof T) {
    if (sortKey.value === key) {
      sortOrder.value = sortOrder.value === 'desc' ? 'asc' : 'desc'
    } else {
      sortKey.value = key
      sortOrder.value = 'desc'
    }
  }

  function sortIcon(key: keyof T): string {
    if (sortKey.value !== key) return '↕'
    return sortOrder.value === 'desc' ? '↓' : '↑'
  }

  return { query, sortKey, sortOrder, filtered, setSort, sortIcon }
}
