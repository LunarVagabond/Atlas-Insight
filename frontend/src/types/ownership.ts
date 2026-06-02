export interface OwnershipSubsystem {
  id: string
  name: string
  subsystem_type: string
  file_count: number
  activity_score: number
  hot_files: { file: string; commit_count: number }[]
  god_modules: { module: string; in_degree: number }[]
  primary_language: string
}

export interface OwnershipData {
  subsystems: OwnershipSubsystem[]
  top_contributors: { author: string; email?: string; files_touched: number }[]
  bus_factor: number
}
