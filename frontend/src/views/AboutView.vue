<script setup lang="ts">
</script>

<template>
  <div class="about-view">
    <div class="about-view__hero">
      <h1 class="about-view__title">Atlas Insight</h1>
      <p class="about-view__tagline">Repository archaeology — no AI, just data.</p>
    </div>

    <div class="about-view__body">
      <section class="about-view__section">
        <h2 class="about-view__section-title">What is this?</h2>
        <p>Atlas Insight analyzes public GitHub repositories and surfaces patterns that are hard to see at a glance — commit velocity trends, contributor burnout signals, architectural complexity, dependency health, and more. Everything is deterministic and computed directly from the git history and source files. No LLMs, no guessing.</p>
      </section>

      <section class="about-view__section">
        <h2 class="about-view__section-title">How to use it</h2>
        <ol class="about-view__steps">
          <li>Paste a GitHub repository URL into the input on the home page.</li>
          <li>Click <strong>Analyze</strong>. Analysis takes 30–90 seconds for most repos.</li>
          <li>Explore the tabs — each one surfaces a different lens on the codebase.</li>
          <li>Share the permalink or export raw JSON for further processing.</li>
        </ol>
        <p class="about-view__note">Private repositories require a GitHub Personal Access Token with <code>repo</code> scope, or OAuth login.</p>
      </section>

      <section class="about-view__section">
        <h2 class="about-view__section-title">What the tabs show</h2>
        <ul class="about-view__feature-list">
          <li><strong>Overview</strong> — high-level stats: stars, language, age, top contributors, tech stack.</li>
          <li><strong>Project</strong> — README content, community files, links, and release history.</li>
          <li><strong>Architecture</strong> — import graph, god modules, circular dependencies, hot files.</li>
          <li><strong>Tours</strong> — guided reading paths through major subsystems.</li>
          <li><strong>Ownership</strong> — file ownership map, bus factor, subsystem breakdown.</li>
          <li><strong>Dependencies</strong> — all declared dependencies, Docker base image warnings, missing lockfiles.</li>
          <li><strong>Security</strong> — hardcoded secrets scan, gitignore gaps, common patterns.</li>
          <li><strong>History</strong> — commit timeline, contributor churn, monthly breakdown, roadmap milestones.</li>
          <li><strong>Heuristics</strong> — scored risk signals: burnout, abandonment, monolith growth, and more.</li>
          <li><strong>Contributing</strong> — actionable contribution opportunities with difficulty ratings.</li>
        </ul>
      </section>

      <section class="about-view__section">
        <h2 class="about-view__section-title">OSS Score</h2>
        <p>Each completed analysis gets an OSS Score from <strong>0–10</strong>. It measures how well-set-up a project is for open-source contribution and long-term sustainability — not code quality. Higher is better.</p>
        <div class="about-view__badge-grid">
          <div class="about-view__badge-row">
            <span class="about-view__badge-emoji">🏆</span>
            <div>
              <strong>Champion (9–10)</strong>
              <span>License, docs, CI, releases, active contributors — the works.</span>
            </div>
          </div>
          <div class="about-view__badge-row">
            <span class="about-view__badge-emoji">⭐</span>
            <div>
              <strong>Thriving (7.5–9)</strong>
              <span>Strong foundation with minor gaps.</span>
            </div>
          </div>
          <div class="about-view__badge-row">
            <span class="about-view__badge-emoji">🌱</span>
            <div>
              <strong>Growing (6–7.5)</strong>
              <span>Good bones, room to improve community scaffolding.</span>
            </div>
          </div>
          <div class="about-view__badge-row">
            <span class="about-view__badge-emoji">🌿</span>
            <div>
              <strong>Seedling (4–6)</strong>
              <span>Active but missing several OSS essentials.</span>
            </div>
          </div>
          <div class="about-view__badge-row">
            <span class="about-view__badge-emoji">😬</span>
            <div>
              <strong>Struggling (2–4)</strong>
              <span>Low docs, CI, or release cadence.</span>
            </div>
          </div>
          <div class="about-view__badge-row">
            <span class="about-view__badge-emoji">💀</span>
            <div>
              <strong>Dormant (0–2)</strong>
              <span>Abandoned or severely under-maintained.</span>
            </div>
          </div>
        </div>
        <p class="about-view__note">Score weights: Community health 25% · Documentation 20% · CI/testing 20% · Release cadence 15% · Activity 10% · Bus factor 10%.</p>
      </section>

      <section class="about-view__section">
        <h2 class="about-view__section-title">Disclaimer</h2>
        <div class="about-view__disclaimer">
          <p>Atlas Insight is a <strong>for-fun tool</strong> built for curiosity and exploration — not auditing or judgment. Scores and signals are heuristic-based and will never capture the full picture of how a team operates. A low OSS score doesn't mean a project is bad; it might just mean the team works differently, ships privately, or simply hasn't gotten around to adding a CONTRIBUTING file. Take everything here with a healthy grain of salt.</p>
          <p>If a score feels wrong for your project, it probably is — every codebase has context that static analysis can't see. Use this as a starting point for conversation, not a verdict.</p>
        </div>
      </section>

      <section class="about-view__section">
        <h2 class="about-view__section-title">Limitations</h2>
        <ul class="about-view__feature-list">
          <li>Analysis runs on a point-in-time clone — results reflect the repo at fetch time.</li>
          <li>Import graph analysis covers Python, TypeScript, JavaScript, Go, Ruby, Rust, Java, Kotlin, C#, and PHP. Other languages show dependency reports only. We're always working to expand language support.</li>
          <li>Very large repositories (&gt;500 MB) may time out.</li>
          <li>GitHub API rate limits apply; some JIT data (issues, PRs) may be unavailable under load.</li>
        </ul>
      </section>
    </div>
  </div>
</template>
