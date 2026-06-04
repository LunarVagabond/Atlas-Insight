// =============================================================================
// Supported Languages & Frameworks — single source of truth for Atlas Insight.
//
// ⚠️  When adding support for a new language or framework in the analyzers,
//     update this file too. It drives the UI across the home page, about page,
//     and docs. See: frontend/src/components/ui/LanguageList.vue
//
// To add an entry:
//   1. Choose a tier:
//        'full'         — import graph analysis + dependency scanning
//        'dependencies' — dependency manifest scanning only (no import graph)
//   2. Choose a kind:
//        'language'     — a programming language (Python, Go, etc.)
//        'framework'    — a framework or runtime (Django, React, etc.)
//        'tool'         — infrastructure tooling (Docker, etc.)
//   3. Set iconUrl — any reachable SVG works. devicons is convenient:
//        https://devicon.dev
//        CDN: https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/<slug>/<slug>-original.svg
//        Some entries use -plain.svg when -original doesn't exist — check devicon.dev.
// =============================================================================

export type AnalysisTier = 'full' | 'dependencies'
export type SupportedKind = 'language' | 'framework' | 'tool'

export interface SupportedLanguage {
  name: string
  iconUrl: string
  tier: AnalysisTier
  kind: SupportedKind
}

const DEVICON = (slug: string, variant = 'original') =>
  `https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/${slug}/${slug}-${variant}.svg`

export const SUPPORTED_LANGUAGES: SupportedLanguage[] = [
  // ── Languages — full import-graph + dependency support ───────────────────
  { name: 'Python',     iconUrl: DEVICON('python'),          tier: 'full',         kind: 'language' },
  { name: 'TypeScript', iconUrl: DEVICON('typescript'),      tier: 'full',         kind: 'language' },
  { name: 'JavaScript', iconUrl: DEVICON('javascript'),      tier: 'full',         kind: 'language' },
  { name: 'Go',         iconUrl: DEVICON('go'),              tier: 'full',         kind: 'language' },
  { name: 'Ruby',       iconUrl: DEVICON('ruby'),            tier: 'full',         kind: 'language' },
  { name: 'Rust',       iconUrl: DEVICON('rust'),            tier: 'full',         kind: 'language' },
  { name: 'Java',       iconUrl: DEVICON('java'),            tier: 'full',         kind: 'language' },
  { name: 'Kotlin',     iconUrl: DEVICON('kotlin'),          tier: 'full',         kind: 'language' },
  { name: 'C#',         iconUrl: DEVICON('csharp'),          tier: 'full',         kind: 'language' },
  { name: 'PHP',        iconUrl: DEVICON('php'),             tier: 'full',         kind: 'language' },
  { name: 'Swift',      iconUrl: DEVICON('swift'),           tier: 'full',         kind: 'language' },
  { name: 'Dart',       iconUrl: DEVICON('dart'),            tier: 'full',         kind: 'language' },
  { name: 'Elixir',     iconUrl: DEVICON('elixir'),          tier: 'full',         kind: 'language' },
  { name: 'Scala',      iconUrl: DEVICON('scala'),           tier: 'full',         kind: 'language' },
  { name: 'Lua',        iconUrl: DEVICON('lua'),             tier: 'full',         kind: 'language' },

  // ── Languages — dependency scanning only (no import graph) ───────────────
  { name: 'C',          iconUrl: DEVICON('c'),               tier: 'dependencies', kind: 'language' },
  { name: 'C++',        iconUrl: DEVICON('cplusplus'),       tier: 'dependencies', kind: 'language' },
  { name: 'Haskell',    iconUrl: DEVICON('haskell'),         tier: 'dependencies', kind: 'language' },
  { name: 'Zig',        iconUrl: DEVICON('zig', 'original'), tier: 'dependencies', kind: 'language' },

  // ── Frameworks — detected via dependency manifests ───────────────────────
  { name: 'React',      iconUrl: DEVICON('react'),           tier: 'dependencies', kind: 'framework' },
  { name: 'Vue',        iconUrl: DEVICON('vuejs'),           tier: 'dependencies', kind: 'framework' },
  { name: 'Angular',    iconUrl: DEVICON('angularjs'),       tier: 'dependencies', kind: 'framework' },
  { name: 'Next.js',    iconUrl: DEVICON('nextjs'),          tier: 'dependencies', kind: 'framework' },
  { name: 'Django',     iconUrl: DEVICON('django', 'plain'), tier: 'dependencies', kind: 'framework' },
  { name: 'Rails',      iconUrl: DEVICON('rails', 'plain'),  tier: 'dependencies', kind: 'framework' },
  { name: 'Spring',     iconUrl: DEVICON('spring'),          tier: 'dependencies', kind: 'framework' },
  { name: 'Laravel',    iconUrl: DEVICON('laravel'),         tier: 'dependencies', kind: 'framework' },
  { name: 'Node.js',    iconUrl: DEVICON('nodejs'),          tier: 'dependencies', kind: 'framework' },
  { name: 'Flutter',    iconUrl: DEVICON('flutter'),         tier: 'dependencies', kind: 'framework' },
  { name: 'Phoenix',    iconUrl: DEVICON('phoenix', 'plain'), tier: 'dependencies', kind: 'framework' },

  // ── Tools — infrastructure we inspect ────────────────────────────────────
  { name: 'Docker',     iconUrl: DEVICON('docker'),          tier: 'dependencies', kind: 'tool' },
]
