import { defineStore } from 'pinia'
import axios from 'axios'
import type {
  AnalysisRun,
  RunResult,
  RunListItem,
  FeaturedRepo,
  SimilarRun,
  DiffData,
  FileHistory,
  JitIssue,
  JitPrData,
} from '../types'

export type {
  AnalysisRun,
  RunResult,
  RunListItem,
  FeaturedRepo,
  SimilarRun,
  DiffData,
  FileHistory,
  JitIssue,
  JitPrData,
}

export type { RoadmapMilestone } from '../types/structure'
export type { ContributionOpportunity, ArchTour, ArchTourFile, ArchTourStep } from '../types/contributions'
export type { HeuristicDelta } from '../types/heuristics'
export type { ClassificationDelta } from '../types/classification'
export type { CommitData, MonthlyCommit, FileHistoryCommit } from '../types/commits'
export type { GraphData, DepsData } from '../types/graph'
export type { HeuristicSignal, HeuristicSignalKey } from '../types/heuristics'
export type { OssScore, Classification, ClassificationLevel } from '../types/classification'
export type { ReadmeData, LinkSignal } from '../types/readme'
export type { LanguageInfo, StructureData, CommunityFilesContent } from '../types/structure'
export type { VulnFinding, SecurityData } from '../types/security'
export type { GitHubContributor, GitHubMeta } from '../types/github'
export type { TodoItem, TodoData } from '../types/todos'
export type { OwnershipSubsystem, OwnershipData } from '../types/ownership'

export const useAnalysisStore = defineStore('analysis', {
  state: () => ({
    url: '' as string,
    currentRunId: null as string | null,
    status: 'idle' as 'idle' | 'submitting' | 'polling' | 'done' | 'error',
    run: null as AnalysisRun | null,
    staleRun: null as AnalysisRun | null,
    error: null as string | null,
    _pollInterval: null as ReturnType<typeof setInterval> | null,
    jitIssues: null as JitIssue[] | null,
    jitPrs: null as JitPrData | null,
    jitLoading: false,
    jitError: false,
    diffData: null as DiffData | null,
    diffLoading: false,
    similarRuns: null as SimilarRun[] | null,
    similarLoading: false,
  }),

  actions: {
    async submitUrl(url: string, pat?: string) {
      this.url = url
      this.status = 'submitting'
      this.error = null
      this.run = null
      this.staleRun = null
      try {
        const { data } = await axios.post('/api/v1/repositories/analyze', {
          url,
          pat: pat || undefined,
        })
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

    async fetchJitData(runId: string) {
      if (this.jitLoading) return
      this.jitLoading = true
      this.jitError = false
      try {
        const [issuesRes, prsRes] = await Promise.allSettled([
          axios.get(`/api/v1/repositories/runs/${runId}/issues`),
          axios.get(`/api/v1/repositories/runs/${runId}/prs`),
        ])
        this.jitIssues = issuesRes.status === 'fulfilled' ? issuesRes.value.data : null
        this.jitPrs = prsRes.status === 'fulfilled' ? prsRes.value.data : null
        if (issuesRes.status === 'rejected' && prsRes.status === 'rejected') {
          this.jitError = true
        }
      } finally {
        this.jitLoading = false
      }
    },

    async fetchDiff(runId: string) {
      if (this.diffLoading) return
      this.diffLoading = true
      try {
        const { data } = await axios.get(`/api/v1/repositories/runs/${runId}/diff`)
        this.diffData = data
      } catch {
        this.diffData = { available: false }
      } finally {
        this.diffLoading = false
      }
    },

    async fetchSimilar(runId: string) {
      if (this.similarLoading) return
      this.similarLoading = true
      try {
        const { data } = await axios.get(`/api/v1/repositories/runs/${runId}/similar`)
        this.similarRuns = data
      } catch {
        this.similarRuns = []
      } finally {
        this.similarLoading = false
      }
    },

    async fetchFileHistory(runId: string, path: string): Promise<FileHistory | null> {
      try {
        const { data } = await axios.get(`/api/v1/repositories/runs/${runId}/file-history`, { params: { path } })
        return data as FileHistory
      } catch {
        return null
      }
    },

    async pollRun(runId: string) {
      this.currentRunId = runId
      this.staleRun = null
      this.run = null
      this.error = null
      this.status = 'polling'
      const ok = await this._fetchRun(runId)
      if (!ok) return
      const run = this.run as AnalysisRun | null
      if (!run || (run.status !== 'completed' && run.status !== 'failed')) {
        this._startPolling(runId)
      } else {
        this.status = run.status === 'completed' ? 'done' : 'error'
        if (run.status === 'failed') {
          this.error = run.result?.error ?? 'Analysis failed'
        }
      }
    },

    _startPolling(runId: string) {
      this._stopPolling()
      this._pollInterval = setInterval(async () => {
        await this._fetchRun(runId)
        if (this.run?.status === 'completed') {
          this.status = 'done'
          this.staleRun = null
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

    async _fetchRun(runId: string): Promise<boolean> {
      try {
        const { data } = await axios.get(`/api/v1/repositories/runs/${runId}`)
        this.run = data
        return true
      } catch (err: unknown) {
        this.status = 'error'
        const axiosErr = err as { response?: { data?: { detail?: string } } }
        this.error = axiosErr.response?.data?.detail ?? 'Failed to fetch run'
        this._stopPolling()
        return false
      }
    },

    async retryRun(runId: string): Promise<string> {
      const { data } = await axios.post(`/api/v1/repositories/runs/${runId}/retry`)
      return data.run_id as string
    },

    async deleteRun(runId: string) {
      await axios.delete(`/api/v1/repositories/runs/${runId}`)
    },

    clearRun() {
      this._stopPolling()
      this.url = ''
      this.currentRunId = null
      this.status = 'idle'
      this.run = null
      this.staleRun = null
      this.error = null
      this.diffData = null
      this.jitIssues = null
      this.jitPrs = null
      this.jitError = false
      this.similarRuns = null
    },
  },
})
