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
//        'tool'         — infrastructure tooling (Docker, Terraform, etc.)
//   3. Choose a maturity:
//        'experimental' — just added, expect gaps
//        'early'        — working but limited coverage
//        'good'         — solid support, few known gaps
//        'mature'       — comprehensive, well-tested
//   4. Set iconUrl — any reachable SVG works. devicons is convenient:
//        https://devicon.dev
//        CDN: https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/<slug>/<slug>-original.svg
//        Some entries use -plain.svg when -original doesn't exist — check devicon.dev.
// =============================================================================

export type AnalysisTier = 'full' | 'dependencies'
export type SupportedKind = 'language' | 'framework' | 'tool'
export type SupportMaturity = 'experimental' | 'early' | 'good' | 'mature'

export interface SupportedLanguage {
  name: string
  iconUrl: string
  tier: AnalysisTier
  kind: SupportedKind
  maturity?: SupportMaturity
}

const DEVICON = (slug: string, variant = 'original') =>
  `https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/${slug}/${slug}-${variant}.svg`

export const SUPPORTED_LANGUAGES: SupportedLanguage[] = [
  // ── Languages — full import-graph + dependency support ───────────────────
  { name: 'Python',     iconUrl: DEVICON('python'),           tier: 'full',         kind: 'language', maturity: 'mature' },
  { name: 'TypeScript', iconUrl: DEVICON('typescript'),       tier: 'full',         kind: 'language', maturity: 'mature' },
  { name: 'JavaScript', iconUrl: DEVICON('javascript'),       tier: 'full',         kind: 'language', maturity: 'mature' },
  { name: 'Go',         iconUrl: DEVICON('go'),               tier: 'full',         kind: 'language', maturity: 'mature' },
  { name: 'Ruby',       iconUrl: DEVICON('ruby'),             tier: 'full',         kind: 'language', maturity: 'good'   },
  { name: 'Rust',       iconUrl: DEVICON('rust'),             tier: 'full',         kind: 'language', maturity: 'good'   },
  { name: 'Java',       iconUrl: DEVICON('java'),             tier: 'full',         kind: 'language', maturity: 'good'   },
  { name: 'Kotlin',     iconUrl: DEVICON('kotlin'),           tier: 'full',         kind: 'language', maturity: 'good'   },
  { name: 'C#',         iconUrl: DEVICON('csharp'),           tier: 'full',         kind: 'language', maturity: 'good'   },
  { name: 'PHP',        iconUrl: DEVICON('php'),              tier: 'full',         kind: 'language', maturity: 'good'   },
  { name: 'Swift',      iconUrl: DEVICON('swift'),            tier: 'full',         kind: 'language', maturity: 'early'  },
  { name: 'Dart',       iconUrl: DEVICON('dart'),             tier: 'full',         kind: 'language', maturity: 'early'  },
  { name: 'Elixir',     iconUrl: DEVICON('elixir'),           tier: 'full',         kind: 'language', maturity: 'early'  },
  { name: 'Scala',      iconUrl: DEVICON('scala'),            tier: 'full',         kind: 'language', maturity: 'early'  },
  { name: 'Lua',        iconUrl: DEVICON('lua'),              tier: 'full',         kind: 'language', maturity: 'early'  },

  // ── Languages — dependency scanning only (no import graph) ───────────────
  { name: 'C',          iconUrl: DEVICON('c'),                tier: 'dependencies', kind: 'language', maturity: 'early'  },
  { name: 'C++',        iconUrl: DEVICON('cplusplus'),        tier: 'dependencies', kind: 'language', maturity: 'early'  },
  { name: 'Haskell',    iconUrl: DEVICON('haskell'),          tier: 'dependencies', kind: 'language', maturity: 'early'  },
  { name: 'Zig',        iconUrl: DEVICON('zig', 'original'),  tier: 'dependencies', kind: 'language', maturity: 'early'  },

  // ── Frameworks — detected via dependency manifests ───────────────────────
  { name: 'React',      iconUrl: DEVICON('react'),            tier: 'dependencies', kind: 'framework', maturity: 'good'  },
  { name: 'Vue',        iconUrl: DEVICON('vuejs'),            tier: 'dependencies', kind: 'framework', maturity: 'good'  },
  { name: 'Angular',    iconUrl: DEVICON('angularjs'),        tier: 'dependencies', kind: 'framework', maturity: 'good'  },
  { name: 'Next.js',    iconUrl: DEVICON('nextjs'),           tier: 'dependencies', kind: 'framework', maturity: 'good'  },
  { name: 'Django',     iconUrl: DEVICON('django', 'plain'),  tier: 'dependencies', kind: 'framework', maturity: 'good'  },
  { name: 'Rails',      iconUrl: DEVICON('rails', 'plain'),   tier: 'dependencies', kind: 'framework', maturity: 'good'  },
  { name: 'Spring',     iconUrl: DEVICON('spring'),           tier: 'dependencies', kind: 'framework', maturity: 'good'  },
  { name: 'Laravel',    iconUrl: DEVICON('laravel'),          tier: 'dependencies', kind: 'framework', maturity: 'good'  },
  { name: 'Node.js',    iconUrl: DEVICON('nodejs'),           tier: 'dependencies', kind: 'framework', maturity: 'good'  },
  { name: 'Flutter',    iconUrl: DEVICON('flutter'),          tier: 'dependencies', kind: 'framework', maturity: 'early' },
  { name: 'Phoenix',    iconUrl: DEVICON('phoenixframework', 'plain'), tier: 'dependencies', kind: 'framework', maturity: 'early' },

  // ── Tools — infrastructure we inspect ────────────────────────────────────
  { name: 'Docker',     iconUrl: DEVICON('docker'),           tier: 'full',         kind: 'tool', maturity: 'mature'       },
  { name: 'Terraform',  iconUrl: DEVICON('terraform'),        tier: 'full',         kind: 'tool', maturity: 'early'        },
]
