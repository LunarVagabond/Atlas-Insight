import { defineStore } from 'pinia'
import axios from 'axios'

export interface AnalysisRun {
  id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  triggered_at: string
  completed_at: string | null
  result: RunResult | null
}

export interface RunResult {
  commits: CommitData
  graph: GraphData
  dependencies: DepsData
  heuristics: HeuristicSignal[]
  error?: string
}

export interface CommitData {
  total_commits: number
  total_contributors: number
  last_commit_date: string | null
  days_since_last_commit: number | null
  abandoned: boolean
  activity_decay_ratio: number
  weekly_frequency: { week: string; count: number }[]
  monthly_frequency: { month: string; count: number }[]
  contributor_churn: { month: string; active: number; new: number; lost: number }[]
}

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
  dependencies: { name: string; version_spec: string; source: string; dev?: boolean }[]
  dependency_count: number
  docker_issues: { file: string; issue: string }[]
  missing_lockfile_warnings: string[]
}

export interface HeuristicSignal {
  signal: string
  label: string
  score: number
  confidence: 'low' | 'medium' | 'high'
  description: string
}

export interface RunListItem {
  id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  triggered_at: string
  completed_at: string | null
  repo_url: string
  repo_owner: string
  repo_name: string
}

export const useAnalysisStore = defineStore('analysis', {
  state: () => ({
    url: '' as string,
    currentRunId: null as string | null,
    status: 'idle' as 'idle' | 'submitting' | 'polling' | 'done' | 'error',
    run: null as AnalysisRun | null,
    error: null as string | null,
    _pollInterval: null as ReturnType<typeof setInterval> | null,
  }),

  actions: {
    async submitUrl(url: string) {
      this.url = url
      this.status = 'submitting'
      this.error = null
      this.run = null
      try {
        const { data } = await axios.post('/api/v1/repositories/analyze', { url })
        this.currentRunId = data.run_id
        this.status = 'polling'
        this._startPolling(data.run_id)
        return data.run_id as string
      } catch (err: unknown) {
        this.status = 'error'
        const axiosErr = err as { response?: { data?: { detail?: string } } }
        this.error = axiosErr.response?.data?.detail ?? 'Failed to submit URL'
        throw err
      }
    },

    async pollRun(runId: string) {
      this.currentRunId = runId
      this.status = 'polling'
      await this._fetchRun(runId)
      if (this.run?.status !== 'completed' && this.run?.status !== 'failed') {
        this._startPolling(runId)
      } else {
        this.status = this.run.status === 'completed' ? 'done' : 'error'
        if (this.run.status === 'failed') {
          this.error = this.run.result?.error ?? 'Analysis failed'
        }
      }
    },

    _startPolling(runId: string) {
      this._stopPolling()
      this._pollInterval = setInterval(async () => {
        await this._fetchRun(runId)
        if (this.run?.status === 'completed') {
          this.status = 'done'
          this._stopPolling()
        } else if (this.run?.status === 'failed') {
          this.status = 'error'
          this.error = this.run.result?.error ?? 'Analysis failed'
          this._stopPolling()
        }
      }, 3000)
    },

    _stopPolling() {
      if (this._pollInterval) {
        clearInterval(this._pollInterval)
        this._pollInterval = null
      }
    },

    async _fetchRun(runId: string) {
      try {
        const { data } = await axios.get(`/api/v1/repositories/runs/${runId}`)
        this.run = data
      } catch (err: unknown) {
        this.status = 'error'
        const axiosErr = err as { response?: { data?: { detail?: string } } }
        this.error = axiosErr.response?.data?.detail ?? 'Failed to fetch run'
        this._stopPolling()
      }
    },

    clearRun() {
      this._stopPolling()
      this.url = ''
      this.currentRunId = null
      this.status = 'idle'
      this.run = null
      this.error = null
    },
  },
})
