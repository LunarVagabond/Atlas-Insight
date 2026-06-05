<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import axios from 'axios'
import AppTabs from '../components/ui/AppTabs.vue'
import AppButton from '../components/ui/AppButton.vue'
import AppCard from '../components/ui/AppCard.vue'
import LanguageList from '../components/ui/LanguageList.vue'

const TABS = ['About', 'Why Atlas Insight', 'Guide', 'Contributors']
const activeTab = ref('About')

const _rawPublicBase = (import.meta.env.VITE_PUBLIC_BASE_URL as string | undefined) || window.location.origin
const publicBase = _rawPublicBase.includes('localhost') ? 'https://atlas.dsyndicate.dev' : _rawPublicBase
const bookmarklet = `javascript:(function(){window.open('${publicBase}/?url='+encodeURIComponent(location.href),'_blank')})()`

const searchQuery = ref('')

interface GuideEntry {
  id: string
  term: string
  range?: string
  section: string
  defHtml: string
  methodLabel: string
  method: string
  searchText: string
}

const GUIDE_ENTRIES: GuideEntry[] = [
  // ── Scores & Risk ────────────────────────────────────────────────────────
  {
    id: 'risk-score',
    term: 'Risk Score',
    range: '0 – 100',
    section: 'Scores & Risk',
    defHtml: `Each heuristic signal produces a 0–100 risk score where <span class="guide-kw">0 = no concern</span> and <span class="guide-kw">100 = maximum risk</span>. The composite "Overall Risk Score" on the Overview tab is the unweighted average across all signals. A score of 30 or below is shown in green, 30–60 in yellow, and above 60 in red.`,
    methodLabel: 'How we compute it',
    method: 'Each signal uses its own formula (see individual entries below). The composite is a simple mean across all signals that were computable for that repo.',
    searchText: 'risk score 0 100 composite overall heuristic signal green yellow red health',
  },
  {
    id: 'oss-score',
    term: 'OSS Score',
    range: '0 – 10',
    section: 'Scores & Risk',
    defHtml: `A single number summarizing how ready a project is for open-source collaboration and long-term sustainability. <span class="guide-kw">10 is best</span>. This is not a code quality score — it measures community scaffolding: docs, CI, licensing, and regular releases.`,
    methodLabel: 'How we compute it',
    method: 'Weighted combination of 16 heuristics: community health (13%), documentation (11%), CI/testing (11%), security hygiene (9%), release cadence (8%), abandonment risk (8%), license risk (7%), test coverage (7%), dependency health (6%), CI/CD maturity (5%), bus factor (5%), complexity debt (4%), container hygiene (3%), monolith growth (2%), commit velocity (1%), burnout (1%). Each is inverted (100 − risk score) so lower risk = higher contribution to the OSS score, then normalized to 0–10. Only signals computable for that repo contribute; weights are renormalized if some are missing.',
    searchText: 'oss score open source sustainability champion thriving growing seedling struggling dormant 10 weighted community docs ci release bus factor security dependency monolith velocity burnout license test coverage cicd container complexity',
  },
  {
    id: 'confidence',
    term: 'Confidence Level',
    section: 'Scores & Risk',
    defHtml: `Each heuristic signal carries a <span class="guide-kw">confidence</span> rating — <em>low</em>, <em>medium</em>, or <em>high</em> — indicating how much data was available to compute it. A young repo with 10 commits will have low confidence on activity signals. Treat low-confidence scores as directional hints, not firm conclusions.`,
    methodLabel: 'How we compute it',
    method: 'Set per-signal based on thresholds: e.g., burnout is high-confidence only if the repo has 6+ months of contributor churn data; monolith growth is high-confidence only if the import graph has 50+ nodes.',
    searchText: 'confidence low medium high data young repo hints directional signal reliability',
  },
  // ── Activity & Momentum ──────────────────────────────────────────────────
  {
    id: 'commit-velocity',
    term: 'Commit Velocity',
    section: 'Activity & Momentum',
    defHtml: `Whether the pace of commits is <span class="guide-kw">speeding up or slowing down</span> over the last 6 months. A declining velocity can signal reduced interest, shifting priorities, or a project approaching completion. Rising velocity is a strong health indicator.`,
    methodLabel: 'How we compute it',
    method: 'We split the last 6 months of commit history into two 3-month windows and compare their averages. The score uses a smooth power curve: score = 75 × (1 − ratio)^0.65. Approximate landmarks: ratio 1.0→0, 0.8→15, 0.7→22, 0.5→48, 0.4→55, 0.0→75. No hard buckets — every change in ratio moves the score. Needs at least 6 months of history to run.',
    searchText: 'commit velocity pace slowing speeding up 6 months trend decline rise momentum activity smooth power curve',
  },
  {
    id: 'activity-decay',
    term: 'Activity Decay Ratio',
    section: 'Activity & Momentum',
    defHtml: `The ratio of <span class="guide-kw">recent commit frequency to historical peak frequency</span>. A ratio of 1.0 means the project is as active as it has ever been. A ratio of 0.3 means recent months produce about 30% of the commits the project did at its busiest.`,
    methodLabel: 'How we compute it',
    method: 'We bucket all commits by week, find the rolling peak 4-week average, and divide the most recent 4-week average by that peak. The result feeds the Burnout Risk heuristic.',
    searchText: 'activity decay ratio peak frequency recent historical burnout 1.0 0.3 weekly',
  },
  {
    id: 'abandonment-risk',
    term: 'Abandonment Risk',
    section: 'Activity & Momentum',
    defHtml: `How likely it is that this repo is <span class="guide-kw">no longer actively maintained</span>, based on the time since the last commit. Unmaintained repos don't get security patches, bug fixes, or compatibility updates with newer tooling.`,
    methodLabel: 'How we compute it',
    method: 'Smooth logarithmic curve based on days since last commit. Under 30d = 0. Beyond 30d: score = min(90, 5 + 22 × log(1 + (days − 30) / 20)). Approximate landmarks: 30d→5, 90d→35, 180d→52, 365d→68, 730d→84, 1095d+→90. No hard cliffs — each additional day of silence adds a continuously increasing penalty.',
    searchText: 'abandonment risk maintained last commit days silent dormant inactive unmaintained deprecated smooth log curve',
  },
  {
    id: 'contributor-churn',
    term: 'Contributor Churn',
    section: 'Activity & Momentum',
    defHtml: `How many unique authors committed code each month, broken into <span class="guide-kw">new</span> (first-ever commit), <span class="guide-kw">active</span> (committed this month), and <span class="guide-kw">lost</span> (active last month, quiet this month). A shrinking active count is one of the strongest burnout signals.`,
    methodLabel: 'How we compute it',
    method: 'Parsed from the full commit log. Each month we track which email addresses committed; "new" is their first appearance, "lost" is their first month of absence after at least one prior active month.',
    searchText: 'contributor churn new active lost monthly authors burnout signal leave leaving email',
  },
  {
    id: 'burnout-risk',
    term: 'Team Burnout Risk',
    section: 'Activity & Momentum',
    defHtml: `A composite signal combining <span class="guide-kw">contributor drop from peak</span> and <span class="guide-kw">activity decay</span>. High scores mean fewer people are doing less work than they historically did — a classic early warning sign of a project running out of steam.`,
    methodLabel: 'How we compute it',
    method: 'Score = (normalized_contributor_drop × 50) + ((1 − activity_decay_ratio) × 50), capped at 100. Contributor drop is normalized by team size: larger teams absorb proportionally more attrition. Dampener = √(2 / peak_contributor_count) — so a 50-person team losing half its contributors is penalized much less than a 2-person team losing one. Solo projects score 0 on this component by design.',
    searchText: 'burnout risk team contributors drop peak activity decay steam momentum warning formula team size normalization',
  },
  // ── Architecture ─────────────────────────────────────────────────────────
  {
    id: 'import-graph',
    term: 'Import Graph',
    section: 'Architecture',
    defHtml: `A <span class="guide-kw">directed graph</span> where each node is a source file and each edge is an import statement. If file A imports from file B, there is an edge A → B. The shape of this graph reveals how tightly coupled different parts of the codebase are.`,
    methodLabel: 'How we compute it',
    method: 'We statically parse import/require/use statements from source files using language-specific parsers. Supported: Python, TypeScript, JavaScript, Go, Ruby, Rust, Java, Kotlin, C#, PHP. We do not execute any code — this is pure text analysis.',
    searchText: 'import graph directed nodes edges files coupling dependency static analysis python typescript javascript go ruby rust java kotlin csharp php',
  },
  {
    id: 'god-module',
    term: 'God Module',
    section: 'Architecture',
    defHtml: `A file that <span class="guide-kw">many other files import from</span> — it has a high "in-degree" in the import graph. God modules are not always bad (a well-designed utility module is fine), but they create architectural risk: changing one affects everything that depends on it, making refactoring expensive and risky.`,
    methodLabel: 'How we compute it',
    method: 'We count how many other files import each file (in-degree). The god module threshold scales with repo size: max(10, int(node_count × 0.05)) — so a 200-node repo uses threshold 10 and a 400-node repo uses 20. This prevents large repos from generating dozens of flags while keeping small repos sensitive. Each god module adds 4 points to the Monolith Growth score.',
    searchText: 'god module in-degree import many files coupling refactor utility shared centralized hub threshold scales size',
  },
  {
    id: 'circular-dependency',
    term: 'Circular Dependency',
    section: 'Architecture',
    defHtml: `When module A imports B which (directly or through a chain) imports A again. Circular dependencies prevent <span class="guide-kw">tree-shaking</span>, complicate testing in isolation, and can cause <span class="guide-kw">initialization-order bugs</span> that are hard to diagnose.`,
    methodLabel: 'How we compute it',
    method: 'We run a depth-first cycle detection algorithm on the import graph. Each detected cycle adds 3 points to the Monolith Growth score. The heuristic drawer shows an example cycle chain so you can find it in the code.',
    searchText: 'circular dependency cycle import chain tree-shaking initialization order bug graph detection dfs',
  },
  {
    id: 'monolith-growth',
    term: 'Monolith Growth Score',
    section: 'Architecture',
    defHtml: `A combined measure of <span class="guide-kw">architectural complexity</span> — how much the codebase has structural patterns that make it harder to work in. It combines god modules and circular dependencies into one number.`,
    methodLabel: 'How we compute it',
    method: 'Score = (god_module_count × 4) + (cycle_count × 3), capped at 100. A repo with 5 god modules and 3 cycles scores (5 × 4) + (3 × 3) = 29. The god module threshold scales with repo size — see the God Module entry for how "unusually high in-degree" is determined.',
    searchText: 'monolith growth score architectural complexity god modules cycles formula calculation',
  },
  {
    id: 'hot-files',
    term: 'Hot Files',
    section: 'Architecture',
    defHtml: `Files with the <span class="guide-kw">most commit touches</span> over the project history. High-churn files are either critical shared utilities, or files that are frequently broken and patched. Worth understanding before making changes.`,
    methodLabel: 'How we compute it',
    method: 'We count how many distinct commits touched each file path across the entire git log, then rank by that count. Files renamed or moved may appear separately.',
    searchText: 'hot files churn commit touches high frequency changed often utility critical',
  },
  {
    id: 'bus-factor',
    term: 'Bus Factor',
    section: 'Architecture',
    defHtml: `The <span class="guide-kw">minimum number of contributors</span> that would need to stop working before 80% or more of the codebase has no active knowledge holder. A bus factor of 1 means one person leaving would leave most of the codebase "orphaned."`,
    methodLabel: 'How we compute it',
    method: 'For each file we identify the contributor who touched it the most. We rank contributors by how many files they "own" and count how many are needed to cover 80% of all files. Risk score = max(0, (5 − bus_factor) × 20), so bus factor 1 = 80 risk, bus factor 5+ = 0 risk.',
    searchText: 'bus factor knowledge holder contributors 80% owner file single point failure orphan institutional',
  },
  {
    id: 'subsystems',
    term: 'Subsystems',
    section: 'Architecture',
    defHtml: `Logical groupings of files by their <span class="guide-kw">path structure</span> — frontend, API, data layer, tests, config, etc. Each subsystem shows which files are most active, who works on them, and what GitHub issues relate to that area.`,
    methodLabel: 'How we compute it',
    method: 'We match file paths against keyword patterns (e.g. paths containing "component", "view", "ui" → frontend subsystem). Files that do not match any pattern go into "other". Subsystems are ranked by commit activity.',
    searchText: 'subsystems frontend api data tests config path groups areas ownership activity',
  },
  {
    id: 'pr-impact',
    term: 'PR Impact Preview',
    section: 'Architecture',
    defHtml: `On-demand complexity estimate for any open pull request. Enter a PR number on the <span class="guide-kw">Ownership</span> tab to see: <span class="guide-kw">complexity score</span> (0–100), which <span class="guide-kw">subsystems</span> the PR touches, whether it modifies a <span class="guide-kw">highly-imported module</span> or a <span class="guide-kw">dependency manifest</span>, and <span class="guide-kw">suggested reviewers</span> ranked by who has recently committed to the exact files in this PR.`,
    methodLabel: 'How we compute it',
    method: 'Complexity score: files changed (0–30 pts) + line delta (0–25 pts) + subsystems crossed (0–25 pts) + touches god module (+10 pts) + dependency manifest changed (+10 pts), capped at 100. Low < 30, Medium 30–59, High 60+. Reviewer suggestions: we fetch the last 10 commits for each of the most-changed files in the PR via GitHub API and rank authors by how many of those files they appear in — the person who has touched the most files in this specific PR comes first. Falls back to subsystem-activity-weighted top contributors if commit history is unavailable.',
    searchText: 'pr impact pull request complexity reviewer suggestion review who subsystem files changed line delta god module dependency manifest score',
  },
  // ── Project Health ───────────────────────────────────────────────────────
  {
    id: 'community-health-files',
    term: 'Community Health Files',
    section: 'Project Health',
    defHtml: `Standard files that signal a project is set up to welcome contributors: <span class="guide-kw">LICENSE</span> (legal terms of use), <span class="guide-kw">CONTRIBUTING</span> (how to make your first PR), <span class="guide-kw">CODE_OF_CONDUCT</span> (community norms), <span class="guide-kw">SECURITY</span> (how to report vulnerabilities), <span class="guide-kw">CHANGELOG</span> (what changed between versions).`,
    methodLabel: 'How we compute it',
    method: 'We scan the file tree for common filenames and locations for each community file (root, docs/, .github/). Score: no license +30, no CONTRIBUTING +20, no SECURITY +15, no CoC +10, no CHANGELOG +10.',
    searchText: 'community health files license contributing code of conduct security changelog readme welcome contributors',
  },
  {
    id: 'documentation-quality',
    term: 'Documentation Quality',
    section: 'Project Health',
    defHtml: `How complete and useful the project documentation is for a newcomer. Scores low when there is no README, when the README is <span class="guide-kw">too short to be useful</span> (under 100 words), or when key sections are missing — how to install it, how to use it, how to contribute.`,
    methodLabel: 'How we compute it',
    method: 'We parse the README and scan for section headings matching installation, usage, contributing, and changelog patterns. Each missing section adds 15 points. A missing README entirely scores 90. A short README (under 100 words) with no code examples adds the full 15 pts; one that is short but has ≥2 code blocks adds only 8 pts. Sections with under 20 words are considered shallow — three or more shallow sections add an additional 15 pts. Score capped at 100.',
    searchText: 'documentation quality readme short word count installation usage contributing changelog sections missing newcomer code blocks shallow sections',
  },
  {
    id: 'ci-health',
    term: 'CI Health',
    section: 'Project Health',
    defHtml: `Whether the project has <span class="guide-kw">automated quality checks</span> wired up: a CI pipeline (GitHub Actions, CircleCI, Travis, etc.), a linting configuration, and a meaningful amount of test files. These catch bugs before they ship.`,
    methodLabel: 'How we compute it',
    method: 'No CI detected = +40 risk. No lint config = +20 risk. Test file ratio below 5% = +30 risk (×0.65 if CI is configured), below 15% = +15 risk (×0.65 if CI), below 25% = +5 risk (×0.65 if CI). The discount when CI exists reflects that integration and end-to-end tests often run in CI pipelines without appearing as test files in the source tree.',
    searchText: 'ci health continuous integration github actions circleci travis pipeline linting automated testing checks file ratio discount',
  },
  {
    id: 'test-ratio',
    term: 'Test Ratio',
    section: 'Project Health',
    defHtml: `The proportion of <span class="guide-kw">test files to source files</span> in the repository. A ratio of 20% means roughly 1 test file for every 5 source files. A structural proxy — a project with 3 comprehensive integration tests and 100 source files will score low even if it has excellent coverage.`,
    methodLabel: 'How we compute it',
    method: 'Files are classified as tests if they live in a test/ or spec/ directory, have "test" or "spec" in their filename, or match common test framework patterns. Count of test files ÷ non-test source files.',
    searchText: 'test ratio files coverage proxy integration unit spec testing percentage',
  },
  {
    id: 'dependency-health',
    term: 'Dependency Health',
    section: 'Project Health',
    defHtml: `Risk from external dependencies — <span class="guide-kw">deprecated Docker base images</span>, missing <span class="guide-kw">lockfiles</span>, and very large dependency trees. Each represents a different class of supply-chain or reproducibility risk.`,
    methodLabel: 'How we compute it',
    method: 'Deprecated Docker base image = +15 per image. Missing lockfile = +20 per package manager. Over 200 total dependencies adds a small scaling penalty (max +20). Unpinned dependencies (no version spec) above 30% of total = up to +15 penalty for reproducibility risk. Score capped at 100.',
    searchText: 'dependency health docker base image deprecated lockfile supply chain reproducibility package count unpinned version spec',
  },
  {
    id: 'lockfile',
    term: 'Lockfile',
    section: 'Project Health',
    defHtml: `A file that <span class="guide-kw">pins exact dependency versions</span> so every build uses the same code. Examples: <code>package-lock.json</code>, <code>yarn.lock</code>, <code>Pipfile.lock</code>, <code>poetry.lock</code>, <code>Cargo.lock</code>. Without one, two developers running the same install command may get different package versions.`,
    methodLabel: 'How we detect it',
    method: 'We scan the file tree for the expected lockfile for each detected package manager. If a package manifest exists (e.g. package.json) but its lockfile does not, we flag it as a missing lockfile warning.',
    searchText: 'lockfile package-lock.json yarn.lock pipfile.lock poetry.lock cargo.lock pin versions reproducible build npm pip cargo',
  },
  {
    id: 'release-cadence',
    term: 'Release Cadence',
    section: 'Project Health',
    defHtml: `How regularly the project <span class="guide-kw">cuts formal releases</span> (git tags / GitHub releases) and how recently the last one was. Regular releases give downstream users a stable update path and signal active maintenance.`,
    methodLabel: 'How we compute it',
    method: 'No releases = 35 risk. Under 90d = 0. Beyond 90d: smooth log curve — score = min(75, 5 + 25 × log(1 + (days − 90) / 100)). Approximate landmarks: 90d→5, 180d→21, 365d→39, 730d→56, 1095d→65, 1460d+→75. No hard cliffs — staleness grows continuously. Projects that ship from main without tagging will score worse than they deserve here.',
    searchText: 'release cadence tags versions github releases stable update maintenance semver changelog last release smooth log curve',
  },
  {
    id: 'security-hygiene',
    term: 'Security Hygiene',
    section: 'Project Health',
    defHtml: `Whether common security mistakes are present: <span class="guide-kw">accidentally committed secrets</span> (API keys, .env files, private keys), a missing <code>.gitignore</code>, or a <code>.gitignore</code> that doesn't exclude patterns it should. A committed secret should be treated as compromised immediately.`,
    methodLabel: 'How we detect it',
    method: 'We scan the tracked file list (not file contents) for filenames matching common secret patterns: .env, *.pem, *.key, credential JSON files, etc. We also parse .gitignore and check it against recommended patterns. We do not read file contents or transmit any detected secrets.',
    searchText: 'security hygiene secrets api keys env pem key gitignore credentials committed compromised patterns',
  },
  // ── Contributing ────────────────────────────────────────────────────────
  {
    id: 'contribution-opportunities',
    term: 'Contribution Opportunities',
    section: 'Contributing & Opportunities',
    defHtml: `Specific, actionable entry points for someone who wants to contribute. These can be <span class="guide-kw">open GitHub issues</span> tagged good-first-issue or help-wanted, structural gaps like missing tests or docs, or infrastructure improvements like adding CI.`,
    methodLabel: 'How we find them',
    method: 'Combination of GitHub issues fetched via the API (filtered for beginner-friendly labels) and synthetic opportunities from structural analysis (e.g. "add a lockfile", "write a CONTRIBUTING guide", "add CI"). Issue opportunities require a GitHub token to fetch.',
    searchText: 'contribution opportunities first issue help wanted open source beginner newcomer entry points issues structural',
  },
  {
    id: 'difficulty-ratings',
    term: 'Difficulty Ratings',
    section: 'Contributing & Opportunities',
    defHtml: `Each opportunity is rated <span class="guide-kw">beginner</span>, <span class="guide-kw">intermediate</span>, or <span class="guide-kw">advanced</span>. Beginner tasks require minimal domain knowledge — adding a file, fixing a typo, writing a small doc. Advanced tasks require deep architectural understanding.`,
    methodLabel: 'How we rate them',
    method: 'For GitHub issues we look at labels (good-first-issue = beginner, help-wanted = intermediate). For synthetic opportunities we assign fixed difficulty by task type: adding a LICENSE is beginner, refactoring a god module is advanced.',
    searchText: 'difficulty beginner intermediate advanced rating labels good first issue help wanted domain knowledge',
  },
  {
    id: 'readiness-score',
    term: 'Readiness Score',
    section: 'Contributing & Opportunities',
    defHtml: `Whether an opportunity is actually <span class="guide-kw">ready to be picked up right now</span>. A "Ready" issue has no open PR already addressing it and is not blocked. A "Claimed" issue has an open PR. "Stale" issues have not been touched in a long time.`,
    methodLabel: 'How we compute it',
    method: 'We cross-reference open issues against open PRs using JIT data fetched from GitHub after analysis completes. A PR mentioning an issue number (via "Fixes #123" or "Closes #123") marks that issue as claimed.',
    searchText: 'readiness ready claimed stale open pr issue cross reference fixes closes blocked available',
  },
  {
    id: 'arch-tours',
    term: 'Architecture Tours',
    section: 'Contributing & Opportunities',
    defHtml: `Guided reading paths through a codebase subsystem — <span class="guide-kw">entry files to start from</span>, the most-changed files to understand, and a suggested reading order. Tours help a newcomer build a mental model without randomly browsing files.`,
    methodLabel: 'How we compute them',
    method: 'We group files by subsystem type (frontend, API, data, tests, config, docs) using path patterns. Within each group we identify entry points (top-level index/router/main files), the most-changed files by commit count, and generate a suggested reading order starting from the entry points outward.',
    searchText: 'architecture tours guided reading path subsystem entry files reading order newcomer mental model frontend api data tests config docs',
  },
  // ── OSS Score Tiers ─────────────────────────────────────────────────────
  {
    id: 'oss-tiers',
    term: 'OSS Score Tiers',
    section: 'Scores & Risk',
    defHtml: `The six labels applied to an OSS Score: <span class="guide-kw">Champion</span> (9.0–10), <span class="guide-kw">Thriving</span> (7.5–8.9), <span class="guide-kw">Growing</span> (6.0–7.4), <span class="guide-kw">Seedling</span> (4.0–5.9), <span class="guide-kw">Struggling</span> (2.0–3.9), <span class="guide-kw">Dormant</span> (0–1.9). These appear on analysis cards, sub-project summaries, and status badges.`,
    methodLabel: 'How tiers are assigned',
    method: 'Purely score-based cutoffs. Champion = 9.0+, Thriving = 7.5+, Growing = 6.0+, Seedling = 4.0+, Struggling = 2.0+, Dormant = below 2.0. The same tier labels appear for both the top-level repo and for individual sub-projects detected inside a monorepo.',
    searchText: 'champion thriving growing seedling struggling dormant oss score tier label badge 9 7.5 6 4 2 monorepo subproject sub-project',
  },
  {
    id: 'sub-projects',
    term: 'Sub-projects',
    section: 'Architecture',
    defHtml: `When Atlas Insight detects a <span class="guide-kw">monorepo</span> — a single repository containing multiple independent projects — it splits the analysis into per-sub-project slices. Each sub-project gets its own stack detection, dependency summary, security scan, and OSS Score. This avoids mixing Python backend deps with JavaScript frontend deps in a single report.`,
    methodLabel: 'How we detect them',
    method: 'We look for monorepo signals: presence of packages/, apps/, services/, or frontend/+backend/ directories; root-level package.json with workspaces; pnpm-workspace.yaml; Cargo.toml workspaces; go.work files. When found, each top-level sub-directory with its own manifest is treated as a sub-project.',
    searchText: 'sub-projects subprojects monorepo packages apps services frontend backend workspaces split analysis per-project independent stack champion oss score',
  },
  // ── License ────────────────────────────────────────────────────────────────
  {
    id: 'license-risk',
    term: 'License Risk',
    section: 'Project Health',
    defHtml: `Whether the project has a <span class="guide-kw">recognized open-source license</span> and whether any dependency licenses are <span class="guide-kw">incompatible</span> with it. A missing license means all rights are reserved by default — contributors and users cannot legally use, modify, or distribute the code. Copyleft licenses (GPL, AGPL) require derivative works to use the same license.`,
    methodLabel: 'How we detect it',
    method: 'We scan the file tree for standard license filenames (LICENSE, LICENSE.md, COPYING, etc.) and match the file content against regex patterns for 14 SPDX identifiers. If no file is found, we fall back to the GitHub API\'s license_spdx field. For the top 100 dependencies we cross-reference a static lookup table of known package licenses across PyPI, npm, crates.io, RubyGems, and Go to flag incompatible combinations. No external API calls for license data — this is a static lookup.',
    searchText: 'license risk spdx mit apache gpl agpl lgpl mpl bsd isc copyleft permissive osi approved derivative compatibility dependency',
  },
  // ── Code Quality ───────────────────────────────────────────────────────────
  {
    id: 'complexity-debt',
    term: 'Complexity Debt',
    section: 'Architecture',
    defHtml: `A measure of how many <span class="guide-kw">large, hard-to-navigate files</span> exist in the codebase. Files over 500 non-blank, non-comment lines are flagged as hotspots. Hotspots without an adjacent test file are weighted more heavily — large untested files are both complex and fragile to change.`,
    methodLabel: 'How we compute it',
    method: 'We count non-blank, non-comment lines in every source file across 12 languages (same set as TODO scanning). Files over 500 LOC are classified as hotspots and checked for an adjacent test file (e.g. test_foo.py next to foo.py, or foo.test.ts next to foo.ts). Score = (over_threshold_ratio × 50) + (untested_hotspot_ratio × 50), capped at 100.',
    searchText: 'complexity debt loc lines of code hotspot large file 500 threshold untested adjacent test fragile hard to change',
  },
  {
    id: 'unreferenced-files',
    term: 'Unreferenced Files',
    section: 'Architecture',
    defHtml: `Source files that are <span class="guide-kw">never imported</span> by any other file in the repository — potential dead code. Known entry points (main.py, index.js, etc.) and files in scripts/, bin/, tests/ directories are excluded automatically. Requires a dense enough import graph to be reliable.`,
    methodLabel: 'How we detect them',
    method: 'We reuse the import graph edges already computed for the Architecture tab and compute the in-degree of every node. Nodes with in-degree 0 that are not entry points, test files, config files, or migration files are flagged. When the graph has fewer than 20 edges, we suppress the result entirely and note that the graph is too sparse for a reliable signal.',
    searchText: 'unreferenced files dead code import graph in-degree entry point sparse never imported orphan module',
  },
  {
    id: 'test-coverage',
    term: 'Test Coverage Proxy',
    section: 'Project Health',
    defHtml: `A structural proxy for test coverage — not a runtime measurement. We map which <span class="guide-kw">directories have at least one test file</span> nearby, which framework is in use, and what the overall test-file ratio is. Useful for spotting large swaths of untested code even without instrumentation.`,
    methodLabel: 'How we compute it',
    method: 'We walk the file tree and classify files as tests if they live in a test/ or spec/ directory, contain "test" or "spec" in the filename, or match common test framework patterns. For each non-test directory with 3+ source files we check whether a sibling test file or tests/ subdirectory exists. The risk score penalizes low test ratios: below 5% → 80 risk, 5–15% → 55, 15–25% → 30, 25–40% → 10, above 40% → 0. Additional penalty for directories with no test coverage.',
    searchText: 'test coverage proxy directory ratio framework pytest jest rspec vitest mocha go test untested source files structural',
  },
  // ── DevOps ─────────────────────────────────────────────────────────────────
  {
    id: 'container-hygiene',
    term: 'Container Hygiene',
    section: 'Project Health',
    defHtml: `Static analysis of <span class="guide-kw">Dockerfile</span> and <span class="guide-kw">docker-compose</span> files for common security and reproducibility issues: running as root, unpinned base images, credentials baked into environment variables, using ADD instead of COPY, and missing apt cache cleanup.`,
    methodLabel: 'How we detect issues',
    method: 'We scan every Dockerfile* file in the repo line by line. High-severity: no USER directive (runs as root by default), USER root explicitly set, ENV variable with a name matching *SECRET*, *KEY*, *TOKEN*, or *PASSWORD*. Medium: FROM *:latest (unpinned base image). Low: ADD for local files (use COPY instead), apt-get install without --no-install-recommends, apt-get install without clearing /var/lib/apt afterwards. Docker Compose files are checked for :latest service images and exposed ports without healthchecks. Score: high issues × 25 + medium issues × 10 + low issues × 3, capped at 100.',
    searchText: 'container hygiene dockerfile docker compose root user latest unpinned base image secret env key token password add copy apt cache',
  },
  {
    id: 'cicd-maturity',
    term: 'CI/CD Maturity',
    section: 'Project Health',
    defHtml: `How complete the <span class="guide-kw">automated pipeline</span> is — not just whether CI exists, but whether it actually runs tests, applies a linter, has a deployment step, and tests across multiple runtime versions (matrix strategy). A basic CI that only builds the project without running tests scores much lower than one with a full quality gate.`,
    methodLabel: 'How we compute it',
    method: 'For GitHub Actions we parse every .yml and .yaml file under .github/workflows/ and scan the run: commands across all jobs. Test presence: keyword match against pytest, jest, vitest, mocha, rspec, cargo test, go test, etc. Lint presence: ruff, eslint, pylint, rubocop, golangci, mypy, tsc, etc. Deploy presence: deploy, publish, helm upgrade, kubectl apply, etc. For other CI systems (Travis, CircleCI, Jenkinsfile, GitLab CI) we fall back to text matching the entire config file. Maturity score: base 40 if any CI exists, +30 for tests, +15 for lint, +10 for deploy, +5 for matrix. Risk score = 100 − maturity score.',
    searchText: 'ci cd maturity pipeline github actions travis circleci jenkins tests lint deploy matrix strategy quality gate automated',
  },
  {
    id: 'changelog-discipline',
    term: 'Changelog Discipline',
    section: 'Project Health',
    defHtml: `Whether the project maintains a structured <span class="guide-kw">CHANGELOG</span> file, what format it uses, and whether it is kept up to date with the actual commit history. A changelog lets downstream users understand what changed between versions without reading raw commits.`,
    methodLabel: 'How we detect it',
    method: 'We check for the changelog file detected by the project structure analyzer (CHANGELOG.md, CHANGELOG, HISTORY.md, etc.) and read the first 20 KB. Format detection: Keep a Changelog format (## [Unreleased] or ## [x.y.z] headings) → "keep-a-changelog"; any ## vX.Y or ## X.Y versioned heading → "versioned"; everything else → "prose". We extract the first ISO date (YYYY-MM-DD) found in the file and compare it to the last commit date. If the changelog has not been updated within 90 days of the last commit and the repo is still active, we flag it as stale.',
    searchText: 'changelog discipline keep a changelog versioned format stale date last updated prose history versions',
  },
]

const SECTION_ORDER = ['Scores & Risk', 'Activity & Momentum', 'Architecture', 'Project Health', 'Contributing & Opportunities']

const filteredEntries = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return GUIDE_ENTRIES
  return GUIDE_ENTRIES.filter(e =>
    e.term.toLowerCase().includes(q) ||
    e.searchText.toLowerCase().includes(q) ||
    e.method.toLowerCase().includes(q)
  )
})

const visibleSections = computed(() =>
  SECTION_ORDER.filter(s => filteredEntries.value.some(e => e.section === s))
)

function entriesForSection(section: string) {
  return filteredEntries.value.filter(e => e.section === section)
}

function clearSearch() {
  searchQuery.value = ''
}

// ── Contributors tab ─────────────────────────────────────────────────────────
interface Contributor {
  username: string
  bio_md: string
  lines_added: number
  lines_removed: number
  commit_count: number
}

const contribs = ref<Contributor[]>([])
const contribTotal = ref(0)
const contribPage = ref(1)
const contribPerPage = 20
const contribQ = ref('')
const contribLoading = ref(false)

async function fetchContribs() {
  contribLoading.value = true
  try {
    const { data } = await axios.get('/api/v1/contributors/', {
      params: { page: contribPage.value, per_page: contribPerPage, q: contribQ.value },
    })
    contribs.value = data.items
    contribTotal.value = data.total
  } catch {
    contribs.value = []
  } finally {
    contribLoading.value = false
  }
}

watch(activeTab, tab => { if (tab === 'Contributors') fetchContribs() })
watch([contribQ], () => { contribPage.value = 1; fetchContribs() })
watch(contribPage, fetchContribs)

const contribTotalPages = computed(() => Math.ceil(contribTotal.value / contribPerPage))

function renderMd(text: string): string {
  return DOMPurify.sanitize(marked.parse(text, { async: false }) as string)
}
</script>

<template>
  <div class="about-view">
    <div class="about-view__hero">
      <h1 class="about-view__title">Atlas Insight</h1>
      <p class="about-view__tagline">Repository archaeology — no AI, just data.</p>
    </div>

    <AppTabs :tabs="TABS" v-model="activeTab" />

    <!-- ── About tab ──────────────────────────────────────────────────────── -->
    <div v-if="activeTab === 'About'" class="about-view__body" style="margin-top: 2rem">
      <section class="about-view__section">
        <h2 class="about-view__section-title">What is this?</h2>
        <p>Atlas Insight analyzes public GitHub repositories and surfaces patterns that are hard to see at a glance — commit velocity trends, contributor burnout signals, architectural complexity, dependency health, and more. Everything is deterministic and computed directly from the git history and source files. No LLMs, no guessing.</p>
      </section>

      <section class="about-view__section">
        <h2 class="about-view__section-title">How to use it</h2>
        <ol class="about-view__steps">
          <li>Paste a GitHub repository URL into the input on the home page.</li>
          <li>Click <strong>Analyze</strong>. Analysis takes 30–90 seconds for most repos.</li>
          <li>To analyze a non-default branch, use the branch selector next to the URL bar — pick any branch and re-analyze. Each branch gets its own cached result.</li>
          <li>Explore the tabs — each one surfaces a different lens on the codebase.</li>
          <li>Share the permalink or export raw JSON for further processing.</li>
        </ol>
        <p class="about-view__note">Private repositories require a GitHub Personal Access Token with <code>repo</code> scope, or OAuth login.</p>
      </section>

      <section class="about-view__section">
        <h2 class="about-view__section-title">What the tabs show</h2>
        <ul class="about-view__feature-list">
          <li><strong>Overview</strong> — high-level stats: stars, language, age, top contributors, tech stack.</li>
          <li><strong>Heuristics</strong> — 16 scored risk signals: burnout, abandonment, license risk, complexity debt, and more.</li>
          <li><strong>Security</strong> — hardcoded secrets scan, gitignore gaps, known CVEs in dependencies.</li>
          <li><strong>Licenses</strong> — SPDX license detection, OSI approval status, dependency license compatibility check.</li>
          <li><strong>Dependencies</strong> — all declared dependencies, Docker base image warnings, missing lockfiles.</li>
          <li><strong>Architecture</strong> — import graph, god modules, circular dependencies, hot files.</li>
          <li><strong>Code Quality</strong> — file complexity hotspots (LOC distribution), unreferenced files, per-directory test coverage mapping.</li>
          <li><strong>Project</strong> — README content, community files, links, and release history.</li>
          <li><strong>History</strong> — commit timeline, contributor churn, monthly breakdown, roadmap milestones.</li>
          <li><strong>Ownership</strong> — file ownership map, bus factor, subsystem breakdown, and <strong>PR Impact Preview</strong>.</li>
          <li><strong>Contributing</strong> — actionable contribution opportunities with difficulty ratings.</li>
          <li><strong>DevOps</strong> — CI/CD pipeline depth, Dockerfile hygiene, changelog discipline.</li>
          <li><strong>Tours</strong> — guided reading paths through major subsystems.</li>
        </ul>
      </section>

      <section class="about-view__section">
        <h2 class="about-view__section-title">OSS Score</h2>
        <p>Each completed analysis gets an OSS Score from <strong>0–10</strong>. It measures how well-set-up a project is for open-source contribution and long-term sustainability — not code quality. Higher is better.</p>
        <div class="about-view__badge-grid">
          <div class="about-view__badge-row">
            <span class="about-view__badge-emoji">🏆</span>
            <div><strong>Champion (9–10)</strong><span>License, docs, CI, releases, active contributors — the works.</span></div>
          </div>
          <div class="about-view__badge-row">
            <span class="about-view__badge-emoji">⭐</span>
            <div><strong>Thriving (7.5–9)</strong><span>Strong foundation with minor gaps.</span></div>
          </div>
          <div class="about-view__badge-row">
            <span class="about-view__badge-emoji">🌱</span>
            <div><strong>Growing (6–7.5)</strong><span>Good bones, room to improve community scaffolding.</span></div>
          </div>
          <div class="about-view__badge-row">
            <span class="about-view__badge-emoji">🌿</span>
            <div><strong>Seedling (4–6)</strong><span>Active but missing several OSS essentials.</span></div>
          </div>
          <div class="about-view__badge-row">
            <span class="about-view__badge-emoji">😬</span>
            <div><strong>Struggling (2–4)</strong><span>Low docs, CI, or release cadence.</span></div>
          </div>
          <div class="about-view__badge-row">
            <span class="about-view__badge-emoji">💀</span>
            <div><strong>Dormant (0–2)</strong><span>Abandoned or severely under-maintained.</span></div>
          </div>
        </div>
        <p class="about-view__note">Score weights (16 signals): Community health 13% · Documentation 11% · CI/testing 11% · Security hygiene 9% · Release cadence 8% · Abandonment risk 8% · License risk 7% · Test coverage 7% · Dependency health 6% · CI/CD maturity 5% · Bus factor 5% · Complexity debt 4% · Container hygiene 3% · Monolith growth 2% · Commit velocity 1% · Burnout 1%.</p>
      </section>

      <section class="about-view__section">
        <h2 class="about-view__section-title">Quick access</h2>
        <p><strong>Direct link:</strong> append <code>?url=</code> to the home page URL to pre-fill and auto-analyze any repo:</p>
        <pre class="about-view__code">{{ `${publicBase}/?url=https://github.com/owner/repo` }}</pre>
        <p style="margin-top: 1.25rem"><strong>Bookmarklet:</strong> drag this to your bookmarks bar. Click it on any GitHub repo page to open an instant analysis.</p>
        <a
          :href="bookmarklet"
          class="about-view__bookmarklet"
          @click.prevent
          draggable="true"
        >⚡ Analyze on Atlas</a>
        <p class="about-view__note">Drag the button above to your bookmarks bar. Clicking it on a <code>github.com</code> page opens Atlas Insight with that repo pre-loaded.</p>
      </section>

      <section class="about-view__section about-view__section--support">
        <p class="about-view__support-text">
          Atlas Insight is free and always will be.
        </p>
      </section>

      <section class="about-view__section">
        <h2 class="about-view__section-title">Disclaimer</h2>
        <div class="about-view__disclaimer">
          <p>Atlas Insight is a <strong>for-fun tool</strong> built for curiosity and exploration — not auditing or judgment. Scores and signals are heuristic-based and will never capture the full picture of how a team operates. A low OSS score doesn't mean a project is bad; it might just mean the team works differently, ships privately, or simply hasn't gotten around to adding a CONTRIBUTING file.</p>
          <p>If a score feels wrong for your project, it probably is — every codebase has context that static analysis can't see. Use this as a starting point for conversation, not a verdict.</p>
        </div>
      </section>

      <section class="about-view__section">
        <h2 class="about-view__section-title">Supported languages</h2>
        <p>Full import-graph analysis — circular dependencies, god modules, hot files — is available for the following languages. All other languages still get dependency scanning if a supported manifest file is present.</p>
        <LanguageList mode="list" tier="full" style="margin-top: 0.5rem" />
        <p class="about-view__note">Language support is community-driven. If your language is missing, <a href="https://github.com/LunarVagabond/Atlas-Insight/issues" target="_blank" rel="noopener noreferrer">open an issue</a> — adding a parser is a great first contribution.</p>
      </section>

      <section class="about-view__section">
        <h2 class="about-view__section-title">Limitations</h2>
        <ul class="about-view__feature-list">
          <li>Analysis runs on a point-in-time clone — results reflect the repo at fetch time.</li>
          <li>Very large repositories (&gt;500 MB) may time out.</li>
          <li>GitHub API rate limits apply; some JIT data (issues, PRs) may be unavailable under load.</li>
        </ul>
      </section>

      <section class="about-view__section">
        <h2 class="about-view__section-title">New to open source?</h2>
        <p>Atlas Insight surfaces contribution opportunities, but if you're new to git or unfamiliar with how to navigate a codebase, check the resources below:</p>
        <div class="about-view__badge-grid" style="margin-top: 0.5rem">
          <RouterLink to="/learn" class="about-view__quicklink">
            <strong>Developer Guide</strong>
            <span>Git basics, reading a project, making your first PR, and 10 habits worth building.</span>
          </RouterLink>
          <RouterLink to="/resources" class="about-view__quicklink">
            <strong>Resources</strong>
            <span>Curated learning material — interactive tools, books, docs, and communities.</span>
          </RouterLink>
        </div>
      </section>
    </div>

    <!-- ── Why tab ───────────────────────────────────────────────────────── -->
    <div v-if="activeTab === 'Why Atlas Insight'" class="about-view__body" style="margin-top: 2rem">
      <section class="about-view__section">
        <p>Honestly, it started as a hobby project — something fun to tinker on. It turned out to be genuinely enjoyable to build, and somewhere along the way it became something worth sharing.</p>
        <p>The problem it's trying to solve is real though. Open source is one of the best ways to grow as a developer — real codebases, real feedback, something concrete for a portfolio. But walking into an unfamiliar repo can be genuinely overwhelming. Where do you even start? Is the project still active? Is there anything a newcomer can actually pick up, or is every issue already claimed or hopelessly complex?</p>
        <p>Atlas Insight is meant to make that first step easier. Instead of spending an afternoon digging through commit history and scanning issues trying to figure out if a project is a good fit, you can get a clear picture in seconds — how healthy the codebase is, whether it actually welcomes contributors, where the complexity lives, and what's available to work on right now.</p>
        <p>Whether you're looking to land your first OSS contribution, build out a portfolio, find a project that matches skills you want to grow, or just explore — the goal is to lower the barrier between "I want to contribute" and "here's where to begin."</p>
      </section>

      <section class="about-view__section">
        <h2 class="about-view__section-title">Feedback welcome</h2>
        <p>Git history is a surprisingly rich data source. Commit timestamps, authorship patterns, file churn, message conventions, branch topology — there's a huge amount of signal sitting in plain text that most tools never look at. Atlas Insight is just scratching the surface. Dependency graphs, contributor network analysis, cross-repo comparisons, language trend detection — the surface area is enormous. Also, charts are cool. 🤓</p>
        <p>Because there's so much left to explore, feedback genuinely matters. This is a side project built by one person — if a score feels off, a metric is confusing, a repo breaks the analysis, or you have an idea for something useful, I'd love to hear it.</p>
        <p>Find the project on <a href="https://github.com/LunarVagabond/Atlas-Insight" target="_blank" rel="noopener noreferrer">GitHub</a> or reach out directly — feedback is the best way to help.</p>
      </section>
    </div>

    <!-- ── Guide tab ───────────────────────────────────────────────────────── -->
    <div v-if="activeTab === 'Guide'" class="about-view__body guide" style="margin-top: 2rem">

      <p class="guide__intro">Plain-English reference for every number, score, and term in Atlas Insight. Each entry explains what the metric means and exactly how we compute it from the raw repository data.</p>

      <!-- Search bar -->
      <div class="guide-search">
        <div class="guide-search__input-wrap">
          <span class="guide-search__icon">⌕</span>
          <input
            v-model="searchQuery"
            type="search"
            class="guide-search__input"
            placeholder="Search terms — e.g. bus factor, lockfile, CI health…"
            autocomplete="off"
            spellcheck="false"
          />
          <button v-if="searchQuery" class="guide-search__clear" @click="clearSearch" aria-label="Clear search">✕</button>
        </div>
        <span v-if="searchQuery" class="guide-search__count">
          {{ filteredEntries.length }} result{{ filteredEntries.length !== 1 ? 's' : '' }}
        </span>
      </div>

      <!-- No results -->
      <div v-if="filteredEntries.length === 0" class="guide-empty">
        No terms match <strong>{{ searchQuery }}</strong>. Try a different keyword.
      </div>

      <!-- Sections -->
      <template v-for="section in visibleSections" :key="section">
        <section class="about-view__section">
          <h2 class="about-view__section-title">{{ section }}</h2>
          <div class="guide-entry" v-for="entry in entriesForSection(section)" :key="entry.id">
            <div class="guide-entry__term">
              {{ entry.term }}
              <span v-if="entry.range" class="guide-entry__range">{{ entry.range }}</span>
            </div>
            <p class="guide-entry__def" v-html="entry.defHtml" />
            <div class="guide-entry__method">
              <span class="guide-entry__method-label">{{ entry.methodLabel }}</span>
              {{ entry.method }}
            </div>
          </div>
        </section>
      </template>

      <!-- Heuristics drawer reading guide (always shown, not searchable) -->
      <section v-if="!searchQuery" class="about-view__section">
        <h2 class="about-view__section-title">Reading the Heuristics tab</h2>
        <p style="color: var(--color-text-secondary); line-height: 1.65; margin: 0">The Heuristics tab shows every signal as a card with a 0–100 score. Click any card to open a detail drawer. The drawer has three parts:</p>
        <ol class="about-view__steps" style="margin-top: 0.5rem">
          <li><strong>In this repo</strong> — actual numbers and filenames from this specific analysis. Repo-specific context.</li>
          <li><strong>Overview</strong> — what this metric measures in general terms.</li>
          <li><strong>What raises this score / What to look for</strong> — the scoring factors and where to find them in the repo.</li>
        </ol>
        <p class="about-view__note">All scores reset on each re-analysis. Push changes and re-analyze to see updated scores.</p>
      </section>

    </div>

    <!-- ── Contributors tab ─────────────────────────────────────────────── -->
    <div v-if="activeTab === 'Contributors'" class="about-view__body" style="margin-top: 2rem">
      <div class="contrib-tab__controls">
        <input
          v-model="contribQ"
          class="url-form__input"
          placeholder="Search contributors…"
          style="max-width: 280px"
        />
        <span class="contrib-tab__count">{{ contribTotal }} contributor{{ contribTotal !== 1 ? 's' : '' }}</span>
      </div>

      <div v-if="contribLoading" style="padding: 2rem 0; color: var(--color-text-muted)">Loading…</div>

      <div v-else-if="!contribs.length" style="padding: 2rem 0; color: var(--color-text-muted)">
        {{ contribQ ? `No contributors matching "${contribQ}".` : 'No contributors found.' }}
      </div>

      <div v-else class="contrib-tab__list">
        <AppCard v-for="c in contribs" :key="c.username" class="contrib-tab__card">
          <div class="contrib-tab__avatar-col">
            <img
              :src="`https://github.com/${c.username}.png?size=80`"
              :alt="c.username"
              class="contrib-tab__avatar"
              width="80"
              height="80"
            />
          </div>
          <div class="contrib-tab__content-col">
            <div class="contrib-tab__bio" v-html="renderMd(c.bio_md)"></div>
            <div class="contrib-tab__meta">
              <span class="contrib-tab__stat">{{ c.commit_count }} commits</span>
              <span class="contrib-tab__stat contrib-tab__stat--add">+{{ c.lines_added.toLocaleString() }}</span>
              <span class="contrib-tab__stat contrib-tab__stat--del">-{{ c.lines_removed.toLocaleString() }}</span>
            </div>
          </div>
        </AppCard>
      </div>

      <div v-if="contribTotalPages > 1" class="runs-pagination" style="margin-top: 1.5rem">
        <AppButton variant="secondary" :disabled="contribPage <= 1" @click="contribPage--">← Prev</AppButton>
        <span class="runs-pagination__info">Page {{ contribPage }} of {{ contribTotalPages }}</span>
        <AppButton variant="secondary" :disabled="contribPage >= contribTotalPages" @click="contribPage++">Next →</AppButton>
      </div>
    </div>
  </div>
</template>
