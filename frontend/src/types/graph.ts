export interface GraphData {
  node_count: number
  edge_count: number
  cycles: string[][]
  cycle_count: number
  god_modules: { module: string; in_degree: number }[]
  hotspots: { file: string; degree: number }[]
  nodes: { id: string; in_degree: number }[]
  edges: { source: string; target: string }[]
}

export interface DepsData {
  dependencies: { name: string; version_spec: string; source: string; dev?: boolean; version?: string; ecosystem?: string }[]
  dependency_count: number
  docker_issues: { file: string; issue: string }[]
  missing_lockfile_warnings: string[]
}
