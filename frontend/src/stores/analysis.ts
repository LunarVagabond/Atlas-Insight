import { defineStore } from 'pinia'
import axios from 'axios'
import { useToast } from '../composables/useToast'
import type {
  AnalysisRun,
  RunResult,
  RunListItem,
  FeaturedRepo,
  SimilarRun,
  DiffData,
  FileHistory,
  PrImpactData,
  ConstellationData,
} from '../types'

export type {
  AnalysisRun,
  RunResult,
  RunListItem,
  FeaturedRepo,
  SimilarRun,
  DiffData,
  FileHistory,
}

export type { SubProject, RepoTypeInfo } from '../types/run'
export type {
  LicenseData, LicenseDepEntry, LicenseIssue,
  ComplexityData, ComplexityHotspot,
  DeadCodeData, DeadCodeEntry,
  TestCoverageData, UntestedDir,
  ContainerData, DockerfileResult, ComposeResult, ContainerIssue,
  CicdData, CicdWorkflow,
  ChangelogData, ChangelogIssue,
} from '../types/run'
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
export type { PrImpactData, PrImpactSubsystem, PrImpactReviewer } from '../types/pr-impact'
export type { ConstellationData, ConstellationRelated } from '../types/constellation'

// Per-repo branch list cache (keyed by "owner/name")
type BranchEntry = { branches: string[]; scanned: string[] }

export const useAnalysisStore = defineStore('analysis', {
  state: () => ({
    url: '' as string,
    currentRunId: null as string | null,
    status: 'idle' as 'idle' | 'submitting' | 'polling' | 'done' | 'error',
    run: null as AnalysisRun | null,
    staleRun: null as AnalysisRun | null,
    error: null as string | null,
    _pollInterval: null as ReturnType<typeof setInterval> | null,
    prImpactCache: {} as Record<number, PrImpactData>,
    prImpactLoading: null as number | null,
    prImpactError: null as number | null,
    constellationData: null as ConstellationData | null,
    constellationLoading: false,
    branches: null as string[] | null,
    scannedBranches: null as string[] | null,
    branchesLoading: false,
    // Branch list cache keyed by "owner/name" — survives branch navigation, cleared on clearRun()
    _branchCache: {} as Record<string, BranchEntry>,
  }),

  actions: {
    async submitUrl(url: string, pat?: string, branch?: string) {
      this.url = url
      this.status = 'submitting'
      this.error = null
      this.run = null
      this.staleRun = null
      try {
        const { data } = await axios.post('/api/v1/repositories/analyze', {
          url,
          pat: pat || undefined,
          branch: branch || undefined,
        })
        this.currentRunId = data.run_id
        this.status = 'polling'
        this._startPolling(data.run_id)
        return data.run_id as string
      } catch (err: unknown) {
        this.status = 'error'
        const axiosErr = err as { response?: { status?: number; data?: { detail?: string } } }
        const msg = axiosErr.response?.data?.detail ?? 'Failed to submit URL'
        this.error = msg
        if (axiosErr.response?.status === 429) {
          useToast().warning(msg, 8000)
        } else {
          useToast().error(msg)
        }
        throw err
      }
    },


    async fetchConstellation(runId: string): Promise<void> {
      if (this.constellationLoading) return
      this.constellationLoading = true
      try {
        const { data } = await axios.get(`/api/v1/repositories/runs/${runId}/constellation`)
        this.constellationData = data as ConstellationData
      } catch {
        this.constellationData = { related: [] }
      } finally {
        this.constellationLoading = false
      }
    },

    async fetchPrImpact(runId: string, prNumber: number): Promise<PrImpactData | null> {
      if (this.prImpactLoading === prNumber) return null
      this.prImpactLoading = prNumber
      this.prImpactError = null
      try {
        const { data } = await axios.get(`/api/v1/repositories/runs/${runId}/pr-impact`, { params: { pr: prNumber } })
        this.prImpactCache = { ...this.prImpactCache, [prNumber]: data as PrImpactData }
        return data as PrImpactData
      } catch {
        this.prImpactError = prNumber
        return null
      } finally {
        this.prImpactLoading = null
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
          useToast().error(this.error)
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
        const axiosErr = err as { response?: { status?: number; data?: { detail?: string } } }
        const status = axiosErr.response?.status
        // 429 = transient rate limit — skip this tick, keep polling
        if (status === 429) {
          useToast().warning('Rate limited — retrying shortly…', 4000)
          return false
        }
        const msg = axiosErr.response?.data?.detail ?? 'Failed to fetch run'
        this.status = 'error'
        this.error = msg
        useToast().error(msg)
        this._stopPolling()
        return false
      }
    },

    async fetchBranches(runId: string): Promise<void> {
      const repoKey = this.run ? `${this.run.repo_owner}/${this.run.repo_name}` : ''
      if (repoKey && this._branchCache[repoKey]) {
        // Populate active state from cache, then refresh scanned list in background
        const c = this._branchCache[repoKey]
        this.branches = c.branches
        this.scannedBranches = c.scanned
        // Refresh scanned (branch scan state changes) but not the full list (rarely changes)
        try {
          const { data } = await axios.get(`/api/v1/repositories/runs/${runId}/branches`)
          const refreshed = { branches: data.branches as string[], scanned: data.scanned as string[] }
          this._branchCache[repoKey] = refreshed
          this.branches = refreshed.branches
          this.scannedBranches = refreshed.scanned
        } catch { /* keep cached data on failure */ }
        return
      }
      if (this.branchesLoading) return
      this.branchesLoading = true
      try {
        const { data } = await axios.get(`/api/v1/repositories/runs/${runId}/branches`)
        this.branches = data.branches as string[]
        this.scannedBranches = data.scanned as string[]
        if (repoKey) this._branchCache[repoKey] = { branches: this.branches, scanned: this.scannedBranches }
      } catch {
        this.branches = []
        this.scannedBranches = []
      } finally {
        this.branchesLoading = false
      }
    },

    async submitBranch(branch: string): Promise<string> {
      if (!this.run) throw new Error('No active run')
      const url = this.run.repo_url
      const pat = this.run.result ? undefined : undefined
      return this.submitUrl(url, pat, branch)
    },

    async retryRun(runId: string): Promise<string> {
      try {
        const { data } = await axios.post(`/api/v1/repositories/runs/${runId}/retry`)
        return data.run_id as string
      } catch (err: unknown) {
        const axiosErr = err as { response?: { status?: number; data?: { detail?: string } } }
        const msg = axiosErr.response?.data?.detail ?? 'Failed to start re-analysis'
        if (axiosErr.response?.status === 429) {
          useToast().warning(msg, 8000)
        } else {
          useToast().error(msg)
        }
        throw err
      }
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
      this.prImpactCache = {}
      this.prImpactLoading = null
      this.prImpactError = null
      this.constellationData = null
      this.constellationLoading = false
      this.branches = null
      this.scannedBranches = null
      this.branchesLoading = false
      this._branchCache = {}
    },
  },
})
