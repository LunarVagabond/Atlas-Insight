<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import AppCard from '../ui/AppCard.vue'
import AppBadge from '../ui/AppBadge.vue'
import SubProjectSelector from './SubProjectSelector.vue'
import type { GraphData, StructureData, FileHistory, SubProject } from '../../stores/analysis'
import { useAnalysisStore } from '../../stores/analysis'
import { useTableFilter } from '../../composables/useTableFilter'

const props = defineProps<{
  graph: GraphData
  hotFiles?: { file: string; commit_count: number }[]
  structure?: StructureData
  runId?: string
  repoUrl?: string
  subProjects?: SubProject[]
  selectedSubProject?: string | null
}>()

const emit = defineEmits<{ 'update:selectedSubProject': [name: string | null] }>()

const activeGraph = computed<GraphData>(() => {
  if (!props.selectedSubProject || !props.subProjects?.length) return props.graph
  return props.subProjects.find(sp => sp.name === props.selectedSubProject)?.graph ?? props.graph
})

const hotFilesSource = computed(() => (props.hotFiles ?? []) as Record<string, unknown>[])
const hotFilesFilter = useTableFilter(hotFilesSource, ['file'], 'commit_count', 'desc')

const godModuleSource = computed(() => activeGraph.value.god_modules)
const hotspotSource = computed(() => activeGraph.value.hotspots)

const godFilter = useTableFilter(godModuleSource, ['module'], 'in_degree' as keyof (typeof activeGraph.value.god_modules)[0])
const hotFilter = useTableFilter(hotspotSource, ['file'], 'degree' as keyof (typeof activeGraph.value.hotspots)[0])

// ── File explorer + drawer ────────────────────────────────────────────────────

const edgeIndex = computed(() => {
  const imports: Record<string, string[]> = {}
  const importedBy: Record<string, string[]> = {}
  for (const e of activeGraph.value.edges) {
    if (!imports[e.source]) imports[e.source] = []
    imports[e.source].push(e.target)
    if (!importedBy[e.target]) importedBy[e.target] = []
    importedBy[e.target].push(e.source)
  }
  return { imports, importedBy }
})

interface FileInfo {
  id: string
  label: string
  imports: string[]
  importedBy: string[]
  isGod: boolean
  isHotspot: boolean
  degree: number
}

const godIds = computed(() => new Set(activeGraph.value.god_modules.map(g => g.module)))
const hotspotDegrees = computed(() => {
  const m: Record<string, number> = {}
  for (const h of activeGraph.value.hotspots) m[h.file] = h.degree
  return m
})

function buildFileInfo(id: string): FileInfo {
  const idx = edgeIndex.value
  return {
    id,
    label: id.split('/').pop() ?? id,
    imports: (idx.imports[id] ?? []).sort(),
    importedBy: (idx.importedBy[id] ?? []).sort(),
    isGod: godIds.value.has(id),
    isHotspot: id in hotspotDegrees.value,
    degree: hotspotDegrees.value[id] ?? 0,
  }
}

const drawerFile = ref<FileInfo | null>(null)
const store = useAnalysisStore()
const drawerHistory = ref<FileHistory | null>(null)
const drawerHistoryLoading = ref(false)

function openDrawer(id: string) {
  drawerFile.value = buildFileInfo(id)
}

function closeDrawer() {
  drawerFile.value = null
  drawerHistory.value = null
}

function formatDate(iso: string): string {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

watch(drawerFile, async (f) => {
  drawerHistory.value = null
  if (!f || !props.runId) return
  drawerHistoryLoading.value = true
  const result = await store.fetchFileHistory(props.runId, f.id)
  drawerHistory.value = result ?? null
  drawerHistoryLoading.value = false
})

// ── File type descriptions ────────────────────────────────────────────────────

const FILE_DESCRIPTIONS: Record<string, { description: string; docs?: string }> = {
  'Makefile': {
    description: 'A Makefile is generally used to automate build tasks — running commands like compiling code, running tests, or cleaning build output, all from a single `make` command.',
    docs: 'https://www.gnu.org/software/make/manual/make.html',
  },
  'Dockerfile': {
    description: 'A Dockerfile is generally used to define how a Docker container image is built — specifying the base OS, copying source files, installing dependencies, and setting the command that runs the app.',
    docs: 'https://docs.docker.com/reference/dockerfile/',
  },
  'docker-compose.yml': {
    description: 'A docker-compose.yml is generally used to define and run multiple Docker containers together — describing services, their ports, environment variables, and shared volumes in one place.',
    docs: 'https://docs.docker.com/compose/',
  },
  'docker-compose.yaml': {
    description: 'A docker-compose.yaml is generally used to define and run multiple Docker containers together — describing services, their ports, environment variables, and shared volumes in one place.',
    docs: 'https://docs.docker.com/compose/',
  },
  'package.json': {
    description: 'A package.json is generally used as the Node.js project manifest — listing the project\'s dependencies, defining scripts you can run (like `npm start` or `npm test`), and storing metadata like name and version.',
    docs: 'https://docs.npmjs.com/cli/v10/configuring-npm/package-json',
  },
  'package-lock.json': {
    description: 'A package-lock.json is generally used to lock the exact version of every installed dependency so that anyone who clones the project and runs `npm install` gets identical packages.',
    docs: 'https://docs.npmjs.com/cli/v10/configuring-npm/package-lock-json',
  },
  'yarn.lock': {
    description: 'A yarn.lock is generally used to record the exact resolved version of every dependency when using the Yarn package manager, ensuring reproducible installs across machines.',
    docs: 'https://yarnpkg.com/configuration/yarnrc',
  },
  'pnpm-lock.yaml': {
    description: 'A pnpm-lock.yaml is generally used to lock dependency versions when using the pnpm package manager, guaranteeing that everyone on the team installs the same packages.',
    docs: 'https://pnpm.io/lockfile-configuration',
  },
  'requirements.txt': {
    description: 'A requirements.txt is generally used to list the Python packages a project depends on, typically installed all at once with `pip install -r requirements.txt`.',
    docs: 'https://pip.pypa.io/en/stable/reference/requirements-file-format/',
  },
  'Pipfile': {
    description: 'A Pipfile is generally used with Pipenv to declare a Python project\'s dependencies and their version constraints, replacing the older requirements.txt workflow.',
    docs: 'https://pipenv.pypa.io/en/latest/pipfile/',
  },
  'pyproject.toml': {
    description: 'A pyproject.toml is generally used as the modern Python project configuration file — specifying build tools, dependencies, and settings for linters, formatters, and test runners in one place.',
    docs: 'https://packaging.python.org/en/latest/guides/writing-pyproject-toml/',
  },
  'setup.py': {
    description: 'A setup.py is generally used as the legacy Python packaging script that defines how a Python package is installed and distributed.',
    docs: 'https://setuptools.pypa.io/en/latest/userguide/quickstart.html',
  },
  'setup.cfg': {
    description: 'A setup.cfg is generally used as a declarative alternative to setup.py for specifying Python package metadata and configuration for setuptools.',
    docs: 'https://setuptools.pypa.io/en/latest/userguide/declarative_config.html',
  },
  'Cargo.toml': {
    description: 'A Cargo.toml is generally used as the Rust project manifest — declaring the package name, version, and crate (library) dependencies that Cargo will download and compile.',
    docs: 'https://doc.rust-lang.org/cargo/reference/manifest.html',
  },
  'Cargo.lock': {
    description: 'A Cargo.lock is generally used to record the exact versions of every Rust crate dependency so builds are reproducible. It is auto-generated by Cargo.',
    docs: 'https://doc.rust-lang.org/cargo/guide/cargo-toml-vs-cargo-lock.html',
  },
  'go.mod': {
    description: 'A go.mod is generally used to define a Go module — declaring the module\'s import path and the minimum required versions of its dependencies.',
    docs: 'https://go.dev/ref/mod#go-mod-file',
  },
  'go.sum': {
    description: 'A go.sum is generally used to store cryptographic checksums of each Go dependency version, ensuring that downloaded modules have not been tampered with.',
    docs: 'https://go.dev/ref/mod#go-sum-files',
  },
  'CMakeLists.txt': {
    description: 'A CMakeLists.txt is generally used to describe how a C or C++ project should be compiled and linked, using CMake to generate platform-specific build files.',
    docs: 'https://cmake.org/cmake/help/latest/manual/cmake-language.7.html',
  },
  '.gitignore': {
    description: 'A .gitignore is generally used to tell Git which files and folders should never be tracked — things like build output, secrets, log files, and editor configuration.',
    docs: 'https://git-scm.com/docs/gitignore',
  },
  '.gitattributes': {
    description: 'A .gitattributes is generally used to set per-file or per-path rules for Git — controlling line endings, diff formatting, and merge behavior for specific file types.',
    docs: 'https://git-scm.com/docs/gitattributes',
  },
  '.editorconfig': {
    description: 'An .editorconfig is generally used to enforce consistent coding style (indentation size, line endings, charset) across different editors and IDEs on the same project.',
    docs: 'https://editorconfig.org/',
  },
  'tsconfig.json': {
    description: 'A tsconfig.json is generally used to configure the TypeScript compiler — controlling strictness, module resolution, which files to include, and where to output compiled JavaScript.',
    docs: 'https://www.typescriptlang.org/tsconfig',
  },
  'jsconfig.json': {
    description: 'A jsconfig.json is generally used in JavaScript projects to give editors like VS Code richer IntelliSense, path aliases, and type information without fully switching to TypeScript.',
    docs: 'https://code.visualstudio.com/docs/languages/jsconfig',
  },
  'vite.config.ts': {
    description: 'A vite.config.ts is generally used to configure Vite — setting up plugins, path aliases, the development server, and build output options for a frontend project.',
    docs: 'https://vite.dev/config/',
  },
  'vite.config.js': {
    description: 'A vite.config.js is generally used to configure Vite — setting up plugins, path aliases, the development server, and build output options for a frontend project.',
    docs: 'https://vite.dev/config/',
  },
  'webpack.config.js': {
    description: 'A webpack.config.js is generally used to configure Webpack — controlling how JavaScript modules, CSS, images, and other assets are bundled into files the browser can load.',
    docs: 'https://webpack.js.org/configuration/',
  },
  'rollup.config.js': {
    description: 'A rollup.config.js is generally used to configure Rollup, a module bundler commonly used to package JavaScript libraries into ESM and CommonJS formats for distribution.',
    docs: 'https://rollupjs.org/configuration-options/',
  },
  '.eslintrc.js': {
    description: 'An .eslintrc.js is generally used to configure ESLint — defining the linting rules, plugins, and parser settings that enforce code quality and style across the project.',
    docs: 'https://eslint.org/docs/latest/use/configure/',
  },
  '.eslintrc.json': {
    description: 'An .eslintrc.json is generally used to configure ESLint — defining the linting rules, plugins, and parser settings that enforce code quality and style across the project.',
    docs: 'https://eslint.org/docs/latest/use/configure/',
  },
  '.eslintrc.yaml': {
    description: 'An .eslintrc.yaml is generally used to configure ESLint — defining the linting rules, plugins, and parser settings that enforce code quality and style across the project.',
    docs: 'https://eslint.org/docs/latest/use/configure/',
  },
  '.prettierrc': {
    description: 'A .prettierrc is generally used to configure Prettier, an opinionated code formatter — setting preferences for indentation, quote style, trailing commas, and line width.',
    docs: 'https://prettier.io/docs/configuration',
  },
  '.babelrc': {
    description: 'A .babelrc is generally used to configure Babel, a JavaScript transpiler that converts modern JS syntax into code that older browsers can understand.',
    docs: 'https://babeljs.io/docs/configuration',
  },
  'jest.config.js': {
    description: 'A jest.config.js is generally used to configure Jest — setting up the test environment, coverage thresholds, module name mapping, and transform rules.',
    docs: 'https://jestjs.io/docs/configuration',
  },
  'vitest.config.ts': {
    description: 'A vitest.config.ts is generally used to configure Vitest, the Vite-native unit testing framework — setting up the test environment, globals, and coverage options.',
    docs: 'https://vitest.dev/config/',
  },
  'CHANGELOG.md': {
    description: 'A CHANGELOG.md is generally used to keep a human-readable history of notable changes, new features, and bug fixes grouped by release version.',
  },
  'CONTRIBUTING.md': {
    description: 'A CONTRIBUTING.md is generally used to explain how others can contribute to the project — covering how to report bugs, submit pull requests, and follow the project\'s code standards.',
  },
  'CODE_OF_CONDUCT.md': {
    description: 'A CODE_OF_CONDUCT.md is generally used to set community expectations — describing how contributors should treat each other and what happens when those standards are not met.',
  },
  'SECURITY.md': {
    description: 'A SECURITY.md is generally used to tell security researchers and users how to responsibly report a vulnerability without disclosing it publicly before a fix is ready.',
  },
  'LICENSE': {
    description: 'A LICENSE file is generally used to state the legal terms under which others may use, copy, modify, and distribute the project\'s source code.',
    docs: 'https://choosealicense.com/',
  },
  'README.md': {
    description: 'A README.md is generally used as the front page of a project — explaining what it does, how to install it, how to use it, and where to find more information.',
  },
}

const EXT_DESCRIPTIONS: Record<string, { description: string; docs?: string }> = {
  '.rs': { description: 'A .rs file is generally used to write Rust source code — a systems programming language focused on memory safety and performance.' },
  '.go': { description: 'A .go file is generally used to write Go source code — a compiled language known for simplicity, fast builds, and built-in concurrency.' },
  '.py': { description: 'A .py file is generally used to write Python source code — a popular, readable language widely used for scripting, data science, and web development.' },
  '.ts': { description: 'A .ts file is generally used to write TypeScript — a superset of JavaScript that adds static types to catch errors before the code runs.' },
  '.tsx': { description: 'A .tsx file is generally used to write TypeScript with JSX syntax, typically in React projects to build typed UI components.' },
  '.js': { description: 'A .js file is generally used to write JavaScript — the language that runs in web browsers and on servers via Node.js.' },
  '.jsx': { description: 'A .jsx file is generally used to write JavaScript with JSX syntax, typically in React projects to describe what UI components should look like.' },
  '.vue': { description: 'A .vue file is generally used as a Vue single-file component — bundling the HTML template, JavaScript logic, and CSS styles for one UI component into a single file.' },
  '.toml': { description: 'A .toml file is generally used as a configuration file in a human-readable format, commonly used by Rust (Cargo.toml), Python, and other ecosystems.' },
  '.yaml': { description: 'A .yaml file is generally used for configuration — its indentation-based structure makes it readable and is widely used for CI pipelines, Docker, and Kubernetes.' },
  '.yml': { description: 'A .yml file is generally used for configuration — its indentation-based structure makes it readable and is widely used for CI pipelines, Docker, and Kubernetes.' },
  '.json': { description: 'A .json file is generally used to store structured data or configuration in a widely-supported, language-neutral text format.' },
  '.md': { description: 'A .md (Markdown) file is generally used to write formatted documentation using plain text — headings, lists, and code blocks render nicely on GitHub and most editors.' },
  '.sh': { description: 'A .sh file is generally used as a shell script — a sequence of commands that run automatically in a Unix/Linux terminal, often used for setup or automation tasks.' },
  '.sql': { description: 'A .sql file is generally used to store database queries or migrations — instructions that create tables, insert data, or change the database schema.' },
}

function getFileDescription(id: string): { description: string; docs?: string } | null {
  const basename = id.split('/').pop() ?? id
  if (FILE_DESCRIPTIONS[basename]) return FILE_DESCRIPTIONS[basename]
  const ext = basename.includes('.') ? '.' + basename.split('.').pop()! : ''
  return EXT_DESCRIPTIONS[ext] ?? null
}

// File explorer search across ALL graph nodes + all_files (deduped)
const explorerQuery = ref('')
const explorerResults = computed(() => {
  const q = explorerQuery.value.trim().toLowerCase()
  if (!q) return []

  // Build unified search set: graph node IDs + all_files paths (deduped)
  const graphIds = new Set(activeGraph.value.nodes.map(n => n.id))
  const allPaths: string[] = [
    ...activeGraph.value.nodes.map(n => n.id),
    ...(props.structure?.all_files ?? []).filter(f => !graphIds.has(f)),
  ]

  return allPaths
    .filter(id => id.toLowerCase().includes(q))
    .slice(0, 40)
    .map(id => ({ id }))
})
</script>

<template>
  <div class="arch-panel">
    <h2 class="panel__title">Architecture</h2>

    <SubProjectSelector
      v-if="subProjects?.length"
      :sub-projects="subProjects"
      :model-value="selectedSubProject ?? null"
      style="margin-bottom: 1rem"
      @update:model-value="emit('update:selectedSubProject', $event)"
    />

    <!-- Stats + File Explorer top row -->
    <div class="arch-top-row">
      <div class="arch-top-row__stats">
        <div class="panel__grid arch-stats-grid">
          <AppCard>
            <div class="stat">
              <div class="stat__value">{{ activeGraph.node_count }}</div>
              <div class="stat__label">Modules Analyzed</div>
            </div>
          </AppCard>
          <AppCard>
            <div class="stat">
              <div class="stat__value">{{ activeGraph.cycle_count }}</div>
              <div class="stat__label">Circular Deps</div>
            </div>
          </AppCard>
          <AppCard>
            <div class="stat">
              <div class="stat__value">{{ activeGraph.god_modules.length }}</div>
              <div class="stat__label">Core Files</div>
            </div>
          </AppCard>
        </div>
      </div>

      <div class="arch-top-row__explorer">
        <h3 class="panel__title">File Explorer</h3>
        <div class="arch-explorer">
          <input
            v-model="explorerQuery"
            class="table-search"
            placeholder="Search any file or module…"
            @keydown.escape="explorerQuery = ''"
          />
          <div v-if="explorerQuery && explorerResults.length" class="arch-explorer__results">
            <button
              v-for="n in explorerResults"
              :key="n.id"
              class="arch-explorer__item"
              :class="{ 'arch-explorer__item--god': godIds.has(n.id), 'arch-explorer__item--hotspot': n.id in hotspotDegrees }"
              @click="openDrawer(n.id)"
            >
              <span class="arch-explorer__item-label" :title="n.id">{{ n.id.split('/').pop() }}</span>
              <span class="arch-explorer__item-path">{{ n.id }}</span>
              <span v-if="godIds.has(n.id)" class="arch-explorer__badge arch-explorer__badge--god" title="Imported by many other files">core file</span>
              <span v-else-if="n.id in hotspotDegrees" class="arch-explorer__badge arch-explorer__badge--hot" title="Heavily connected to other files">well-connected</span>
            </button>
          </div>
          <p v-else-if="explorerQuery" class="arch-explorer__empty">No modules match "{{ explorerQuery }}"</p>
        </div>
      </div>
    </div>

    <!-- Two-column analysis split — sections placed directly so rows align -->
    <div class="arch-split">

      <!-- Row 1 left: Most-Connected Files -->
      <div v-if="activeGraph.hotspots.length" class="arch-section arch-section--col1">
        <h3 class="panel__title">
          Most-Connected Files
          <span class="panel__title-note">click to inspect</span>
        </h3>
        <p class="panel__subtitle">Files with the most import connections — both imports and importers. High numbers mean this file is central to the project.</p>
        <input v-model="hotFilter.query.value" class="table-search" placeholder="Search files…" />
        <div class="arch-section__scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th class="runs-table__sortable" @click="hotFilter.setSort('file')">File {{ hotFilter.sortIcon('file') }}</th>
                <th class="runs-table__sortable" @click="hotFilter.setSort('degree')">Connections {{ hotFilter.sortIcon('degree') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="h in hotFilter.filtered.value"
                :key="h.file"
                class="arch-panel__clickable-row"
                @click="openDrawer(h.file)"
              >
                <td>{{ h.file }}</td>
                <td>{{ h.degree }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Row 1 right: Most-Changed Files -->
      <div v-if="hotFiles?.length" class="arch-section arch-section--col2">
        <h3 class="panel__title">
          Most-Changed Files
          <span class="panel__title-note">click to inspect</span>
        </h3>
        <p class="panel__subtitle">Files edited most often in history — worth reading early to understand what's actively developed or frequently fixed.</p>
        <input v-model="hotFilesFilter.query.value" class="table-search" placeholder="Search files…" />
        <div class="arch-section__scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th class="runs-table__sortable" @click="hotFilesFilter.setSort('file')">File {{ hotFilesFilter.sortIcon('file') }}</th>
                <th class="runs-table__sortable" @click="hotFilesFilter.setSort('commit_count')">Changes {{ hotFilesFilter.sortIcon('commit_count') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(hf, idx) in (hotFilesFilter.filtered.value as any[])"
                :key="hf.file"
                class="arch-panel__clickable-row"
                @click="openDrawer(hf.file)"
              >
                <td>{{ idx + 1 }}</td>
                <td>{{ hf.file }}</td>
                <td>{{ hf.commit_count.toLocaleString() }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Row 2 left: Core Files -->
      <div v-if="activeGraph.god_modules.length" class="arch-section arch-section--col1">
        <h3 class="panel__title">
          Core Files
          <span class="panel__title-note">imported by many others — click to inspect</span>
        </h3>
        <p class="panel__subtitle">Files that many other files depend on. Changing them ripples wide — read these early to understand the project's foundation.</p>
        <input v-model="godFilter.query.value" class="table-search" placeholder="Search files…" />
        <div class="arch-section__scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th class="runs-table__sortable" @click="godFilter.setSort('module')">File {{ godFilter.sortIcon('module') }}</th>
                <th class="runs-table__sortable" @click="godFilter.setSort('in_degree')">Used by {{ godFilter.sortIcon('in_degree') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="m in godFilter.filtered.value"
                :key="m.module"
                class="arch-panel__clickable-row"
                @click="openDrawer(m.module)"
              >
                <td>{{ m.module }}</td>
                <td><AppBadge variant="warning">{{ m.in_degree }}</AppBadge></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Row 2 right: Circular Dependencies -->
      <div v-if="activeGraph.cycles.length" class="arch-section arch-section--col2">
        <h3 class="panel__title">Circular Dependencies</h3>
        <p class="panel__subtitle">Files that depend on each other — like two people waiting for each other to go first. Worth cleaning up over time.</p>
        <div v-for="(cycle, i) in activeGraph.cycles.slice(0, 5)" :key="i" class="cycle-item">
          <code>{{ cycle.join(' → ') }}</code>
        </div>
      </div>

    </div>

    <!-- File drawer — teleported to body so it can be fixed on the right -->
    <Teleport to="body">
      <Transition name="arch-drawer">
        <div v-if="drawerFile" class="arch-file-drawer" @keydown.escape="closeDrawer">
          <div class="arch-file-drawer__backdrop" @click="closeDrawer" />
          <div class="arch-file-drawer__panel">
            <div class="arch-file-drawer__header">
              <div class="arch-file-drawer__title-group">
                <div class="arch-file-drawer__badges">
                  <span v-if="drawerFile.isGod" class="arch-file-drawer__badge arch-file-drawer__badge--god">God module</span>
                  <span v-if="drawerFile.isHotspot" class="arch-file-drawer__badge arch-file-drawer__badge--hot">Hotspot · {{ drawerFile.degree }} connections</span>
                </div>
                <h3 class="arch-file-drawer__filename" :title="drawerFile.id">{{ drawerFile.label }}</h3>
                <p class="arch-file-drawer__path">{{ drawerFile.id }}</p>
                <div v-if="getFileDescription(drawerFile.id)" class="arch-file-drawer__file-info">
                  <span class="arch-file-drawer__file-label">File Type Summary</span>
                  <p class="arch-file-drawer__file-desc">{{ getFileDescription(drawerFile.id)!.description }}</p>
                  <a
                    v-if="getFileDescription(drawerFile.id)!.docs"
                    :href="getFileDescription(drawerFile.id)!.docs"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="arch-file-drawer__file-docs"
                  >
                    Learn more ↗
                  </a>
                </div>
              </div>
              <button class="arch-file-drawer__close" @click="closeDrawer" title="Close (Esc)">✕</button>
            </div>

            <div class="arch-file-drawer__body">
              <div class="arch-file-drawer__section">
                <h4 class="arch-file-drawer__section-title">
                  Imports
                  <span class="arch-file-drawer__count">{{ drawerFile.imports.length }}</span>
                </h4>
                <div v-if="drawerFile.imports.length" class="arch-file-drawer__list">
                  <button
                    v-for="m in drawerFile.imports"
                    :key="m"
                    class="arch-file-drawer__entry arch-file-drawer__entry--out"
                    :title="m"
                    @click="openDrawer(m)"
                  >
                    <span class="arch-file-drawer__arrow">→</span>
                    <span class="arch-file-drawer__entry-name">{{ m.split('/').pop() }}</span>
                    <span class="arch-file-drawer__entry-path">{{ m }}</span>
                  </button>
                </div>
                <p v-else class="arch-file-drawer__empty">No outgoing imports</p>
              </div>

              <div class="arch-file-drawer__section">
                <h4 class="arch-file-drawer__section-title">
                  Imported by
                  <span class="arch-file-drawer__count">{{ drawerFile.importedBy.length }}</span>
                </h4>
                <div v-if="drawerFile.importedBy.length" class="arch-file-drawer__list">
                  <button
                    v-for="m in drawerFile.importedBy"
                    :key="m"
                    class="arch-file-drawer__entry arch-file-drawer__entry--in"
                    :title="m"
                    @click="openDrawer(m)"
                  >
                    <span class="arch-file-drawer__arrow">←</span>
                    <span class="arch-file-drawer__entry-name">{{ m.split('/').pop() }}</span>
                    <span class="arch-file-drawer__entry-path">{{ m }}</span>
                  </button>
                </div>
                <p v-else class="arch-file-drawer__empty">Nothing imports this module</p>
              </div>

              <div v-if="runId" class="arch-file-drawer__section">
                <h4 class="arch-file-drawer__section-title">
                  Commit History
                  <span v-if="drawerHistory" class="arch-file-drawer__count">{{ drawerHistory.commits.length }}</span>
                </h4>
                <div v-if="drawerHistoryLoading" class="file-history__loading">
                  <span class="spinner" />
                  <span>Loading…</span>
                </div>
                <template v-else-if="drawerHistory">
                  <div class="file-history__actions">
                    <a
                      v-if="repoUrl && drawerFile"
                      :href="`${repoUrl}/blob/HEAD/${drawerFile.id}`"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="btn btn--secondary btn--sm"
                    >View on GitHub ↗</a>
                  </div>
                  <p v-if="!drawerHistory.commits.length" class="file-history__empty">No commit history found.</p>
                  <div v-else class="file-history__timeline">
                    <div v-for="commit in drawerHistory.commits" :key="commit.full_sha" class="fh-commit">
                      <div class="fh-commit__header">
                        <a :href="commit.url" target="_blank" rel="noopener noreferrer" class="fh-commit__sha">{{ commit.sha }}</a>
                        <span class="fh-commit__date">{{ formatDate(commit.date) }}</span>
                        <span class="fh-commit__author">{{ commit.author }}</span>
                      </div>
                      <p class="fh-commit__message">{{ commit.message }}</p>
                      <div v-if="commit.issue_refs.length" class="fh-commit__refs">
                        <span class="fh-commit__refs-label">References:</span>
                        <a
                          v-for="ref in commit.issue_refs"
                          :key="ref"
                          :href="repoUrl ? `${repoUrl}/issues/${ref}` : '#'"
                          target="_blank"
                          rel="noopener noreferrer"
                          class="fh-commit__ref-link"
                        >#{{ ref }}</a>
                      </div>
                    </div>
                  </div>
                  <p class="contrib-drawer__disclaimer">Showing most recent {{ drawerHistory.commits.length }} commits.</p>
                </template>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>
