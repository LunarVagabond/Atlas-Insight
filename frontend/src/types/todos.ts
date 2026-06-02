export interface TodoItem {
  file: string
  line: number
  type: string
  text: string
}

export interface TodoData {
  total: number
  by_type: Record<string, number>
  items: TodoItem[]
}
