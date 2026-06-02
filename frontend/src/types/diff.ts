import type { HeuristicDelta } from './heuristics'
import type { ClassificationDelta } from './classification'

export type { HeuristicDelta, ClassificationDelta }

export interface DiffData {
  available: boolean
  previous_run_id?: string
  previous_triggered_at?: string
  heuristics?: HeuristicDelta[]
  dependencies?: { added: string[]; removed: string[]; added_count: number; removed_count: number }
  contributors?: { before: number; after: number; delta: number }
  graph?: { nodes_before: number; nodes_after: number; nodes_delta: number; god_modules_before: number; god_modules_after: number; god_modules_delta: number }
  structure?: { files_before: number; files_after: number; files_delta: number; test_ratio_before: number; test_ratio_after: number }
  classification?: { project_health?: ClassificationDelta | null; contribution_difficulty?: ClassificationDelta | null; documentation_grade?: ClassificationDelta | null; code_complexity?: ClassificationDelta | null }
}
