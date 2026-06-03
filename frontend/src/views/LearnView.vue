<script setup lang="ts">
import { ref } from 'vue'
import AppTabs from '../components/ui/AppTabs.vue'

const TABS = ['Git Basics', 'Reading a Project', 'Your First Contribution', 'Recommendations']
const activeTab = ref('Git Basics')
</script>

<template>
  <div class="learn-view">
    <div class="learn-view__hero">
      <h1 class="learn-view__title">Developer Guide</h1>
      <p class="learn-view__tagline">A practical guide for developers at every level — from your first <code>git init</code> to navigating a large open-source codebase.</p>
    </div>

    <AppTabs :tabs="TABS" v-model="activeTab" />

    <div class="learn-view__body">
      <div class="learn-view__disclaimer">
        <p>This guide reflects widely shared practices across the software community — not universal law. Every project, team, and language ecosystem does things differently. Use this as a starting point and let the codebase you're working in be your final authority.</p>
      </div>
    </div>

    <!-- ── Git Basics ──────────────────────────────────────────────────────── -->
    <div v-if="activeTab === 'Git Basics'" class="learn-view__body">

      <section class="learn-view__section">
        <h2 class="learn-view__section-title">What is Git?</h2>
        <p>Git is a <strong>version control system</strong> — software that tracks every change ever made to your code. Think of it as a detailed save history for an entire project, where you can always go back to any point in time and see exactly what changed, who changed it, and why.</p>
        <p>When you work on a team, Git lets multiple people edit the same codebase simultaneously without overwriting each other's work. It's the tool behind nearly every open-source project in the world.</p>
        <p class="learn-view__atlas-callout">Atlas Insight is built entirely on git data — commit history, authorship, file churn, branching patterns. Every score and signal you see in the app comes from reading the same history you're about to learn to read yourself.</p>
      </section>

      <section class="learn-view__section">
        <h2 class="learn-view__section-title">Core concepts</h2>

        <div class="learn-concept">
          <div class="learn-concept__term">Repository (repo)</div>
          <div class="learn-concept__body">
            <p>A folder that Git is tracking. It contains your project files plus a hidden <code>.git/</code> directory where Git stores the entire history. When you "clone" a repo from GitHub, you get a full copy of that history on your machine.</p>
          </div>
        </div>

        <div class="learn-concept">
          <div class="learn-concept__term">Commit</div>
          <div class="learn-concept__body">
            <p>A snapshot of your project at a specific moment. Each commit has a unique ID (a hash like <code>a3f9c2b</code>), a message describing the change, and a pointer to the previous commit. The chain of commits is the project's history.</p>
            <pre class="learn-view__code">git add README.md
git commit -m "Add installation instructions to README"</pre>
          </div>
        </div>

        <div class="learn-concept">
          <div class="learn-concept__term">Branch</div>
          <div class="learn-concept__body">
            <p>A separate line of development. The default branch is usually called <code>main</code> (or <code>master</code> in older repos). When you want to add a feature without touching the main branch, you create a new branch, make your changes there, and merge it back when ready.</p>
            <pre class="learn-view__code">git checkout -b my-feature   # create + switch to a new branch
git checkout main             # switch back to main</pre>
          </div>
        </div>

        <div class="learn-concept">
          <div class="learn-concept__term">Remote</div>
          <div class="learn-concept__body">
            <p>A copy of the repository hosted on a server — usually GitHub. <code>origin</code> is the conventional name for the remote your local repo was cloned from. You <em>push</em> commits up to the remote and <em>pull</em> other people's commits down from it.</p>
            <pre class="learn-view__code">git push origin my-feature   # upload your branch
git pull origin main          # download latest changes from main</pre>
          </div>
        </div>

        <div class="learn-concept">
          <div class="learn-concept__term">Pull Request (PR)</div>
          <div class="learn-concept__body">
            <p>A request to merge your branch into another branch (usually <code>main</code>). PRs live on GitHub (not in Git itself) and are the standard way to propose changes, get code review, and discuss the work before it's merged.</p>
          </div>
        </div>

        <div class="learn-concept">
          <div class="learn-concept__term">Merge conflict</div>
          <div class="learn-concept__body">
            <p>When two branches edit the same lines of the same file, Git can't automatically decide which version to keep. It marks the conflict in the file and asks you to resolve it manually. This sounds scary but is a normal part of collaborating.</p>
            <pre class="learn-view__code">&lt;&lt;&lt;&lt;&lt;&lt;&lt; HEAD
const PORT = 3000
=======
const PORT = 8080
&gt;&gt;&gt;&gt;&gt;&gt;&gt; feature/change-port</pre>
            <p class="learn-view__note">Edit the file to keep the version you want, remove the conflict markers, then <code>git add</code> and <code>git commit</code>.</p>
          </div>
        </div>
      </section>

      <section class="learn-view__section">
        <h2 class="learn-view__section-title">Essential commands</h2>
        <div class="learn-cmd-grid">
          <div class="learn-cmd">
            <code class="learn-cmd__cmd">git clone &lt;url&gt;</code>
            <span class="learn-cmd__desc">Download a repo to your machine</span>
          </div>
          <div class="learn-cmd">
            <code class="learn-cmd__cmd">git status</code>
            <span class="learn-cmd__desc">Show what files have changed</span>
          </div>
          <div class="learn-cmd">
            <code class="learn-cmd__cmd">git diff</code>
            <span class="learn-cmd__desc">Show exact line-by-line changes</span>
          </div>
          <div class="learn-cmd">
            <code class="learn-cmd__cmd">git add &lt;file&gt;</code>
            <span class="learn-cmd__desc">Stage a file for the next commit</span>
          </div>
          <div class="learn-cmd">
            <code class="learn-cmd__cmd">git commit -m "message"</code>
            <span class="learn-cmd__desc">Save a snapshot with a description</span>
          </div>
          <div class="learn-cmd">
            <code class="learn-cmd__cmd">git log --oneline</code>
            <span class="learn-cmd__desc">See commit history, one line each</span>
          </div>
          <div class="learn-cmd">
            <code class="learn-cmd__cmd">git branch</code>
            <span class="learn-cmd__desc">List branches; * marks the current one</span>
          </div>
          <div class="learn-cmd">
            <code class="learn-cmd__cmd">git checkout -b &lt;name&gt;</code>
            <span class="learn-cmd__desc">Create and switch to a new branch</span>
          </div>
          <div class="learn-cmd">
            <code class="learn-cmd__cmd">git pull</code>
            <span class="learn-cmd__desc">Fetch + merge remote changes</span>
          </div>
          <div class="learn-cmd">
            <code class="learn-cmd__cmd">git push</code>
            <span class="learn-cmd__desc">Upload your commits to the remote</span>
          </div>
          <div class="learn-cmd">
            <code class="learn-cmd__cmd">git stash</code>
            <span class="learn-cmd__desc">Temporarily shelve uncommitted changes</span>
          </div>
          <div class="learn-cmd">
            <code class="learn-cmd__cmd">git stash pop</code>
            <span class="learn-cmd__desc">Restore the most recent stash</span>
          </div>
        </div>
      </section>

      <section class="learn-view__section">
        <h2 class="learn-view__section-title">A typical day-to-day workflow</h2>
        <p>Workflows vary by team — some use trunk-based development, others long-lived feature branches, others something in between. This is a common baseline that works for most open-source contribution:</p>
        <ol class="learn-view__steps">
          <li>Pull the latest changes: <code>git pull origin main</code></li>
          <li>Create a branch for your work: <code>git checkout -b fix/typo-in-readme</code></li>
          <li>Make your changes in the files.</li>
          <li>Check what changed: <code>git status</code> and <code>git diff</code></li>
          <li>Stage your changes: <code>git add README.md</code></li>
          <li>Commit with a clear message: <code>git commit -m "Fix typo in README install section"</code></li>
          <li>Push to GitHub: <code>git push origin fix/typo-in-readme</code></li>
          <li>Open a Pull Request on GitHub and describe what you changed and why.</li>
        </ol>
        <p class="learn-view__atlas-callout">In Atlas Insight, the History tab shows commit frequency over time and contributor patterns. Repos where commits are small and consistent tend to show healthier activity signals than repos with long gaps punctuated by massive dump commits.</p>
      </section>

    </div>

    <!-- ── Reading a Project ────────────────────────────────────────────────── -->
    <div v-if="activeTab === 'Reading a Project'" class="learn-view__body">

      <section class="learn-view__section">
        <h2 class="learn-view__section-title">Where to start</h2>
        <p>Opening a new codebase for the first time can feel like entering a room full of strangers. What follows is a general approach — not a checklist that works identically for every project. Every language ecosystem, every framework, and every team has its own conventions. The goal is to orient yourself, not to follow a formula.</p>
      </section>

      <section class="learn-view__section">
        <h2 class="learn-view__section-title">Step 1 — Read the README first</h2>
        <p>The README is the project's front door. A good one tells you what the project does, how to set it up, and how to contribute. Even a short README gives you crucial orientation before you touch any code.</p>
        <p>Look for: what problem does this solve? What's the tech stack? Is there a setup guide? Are there links to deeper documentation?</p>
        <p class="learn-view__atlas-callout">Atlas Insight's <strong>Documentation Quality</strong> signal scores the README for length and key sections (installation, usage, contributing). Repos with thin or missing READMEs show higher risk scores — not because a good README guarantees good code, but because it signals how much the team has invested in helping newcomers.</p>
      </section>

      <section class="learn-view__section">
        <h2 class="learn-view__section-title">Step 2 — Understand the folder structure</h2>
        <p>Before reading any code, scan the top-level directories. Try to understand the intent behind the layout — where does source code live, where do tests live, where is configuration stored? This varies significantly by language and framework.</p>
        <div class="learn-concept">
          <div class="learn-concept__term">Some names you may encounter</div>
          <div class="learn-concept__body">
            <p class="learn-view__note" style="margin-bottom: 0.75rem">Directory names are not standardized. These are common patterns across many projects — your project may use completely different names, nest things differently, or follow conventions specific to its framework. Take these as illustrative examples, not rules.</p>
            <div class="learn-dir-grid">
              <div class="learn-dir-row"><span class="learn-dir-row__path"><code>src/</code> or <code>lib/</code></span><span class="learn-dir-row__desc">Often (not always) the main source code</span></div>
              <div class="learn-dir-row"><span class="learn-dir-row__path"><code>tests/</code>, <code>test/</code>, <code>spec/</code></span><span class="learn-dir-row__desc">Test files — naming varies by language and framework</span></div>
              <div class="learn-dir-row"><span class="learn-dir-row__path"><code>docs/</code></span><span class="learn-dir-row__desc">Extended documentation, API references, guides</span></div>
              <div class="learn-dir-row"><span class="learn-dir-row__path"><code>.github/</code></span><span class="learn-dir-row__desc">GitHub-specific: CI workflows, issue/PR templates</span></div>
              <div class="learn-dir-row"><span class="learn-dir-row__path"><code>scripts/</code></span><span class="learn-dir-row__desc">Build, migration, or utility scripts</span></div>
              <div class="learn-dir-row"><span class="learn-dir-row__path"><code>config/</code></span><span class="learn-dir-row__desc">Configuration — though many projects store this at the root</span></div>
            </div>
          </div>
        </div>
        <p class="learn-view__atlas-callout">The <strong>Architecture tab</strong> in Atlas Insight shows the actual import graph for supported languages — which files depend on which. This is often more useful than folder structure alone, since a file buried three levels deep might be imported by half the codebase.</p>
      </section>

      <section class="learn-view__section">
        <h2 class="learn-view__section-title">Step 3 — Find the entry point</h2>
        <p>Most programs have a starting point — the file or function that runs first. Finding it gives you a thread to follow. <strong>How obvious this is depends entirely on the language and framework.</strong> Frameworks often abstract away a traditional entry point — a Rails app, a Next.js app, and a Django app each have their own conventions that override the "obvious" starting file. When in doubt, check the README or the project's framework documentation first.</p>
        <p>Some common patterns (not universal):</p>
        <ul class="learn-view__list">
          <li>Check the <strong>manifest file</strong> for your ecosystem (e.g. <code>package.json</code> scripts, a <code>Makefile</code>, a <code>Taskfile</code>) — the <code>start</code> or <code>run</code> command usually points you to the entry</li>
          <li>For CLI tools and scripts, look for a file named <code>main</code>, <code>index</code>, <code>cli</code>, or <code>app</code> — but names vary widely</li>
          <li>For framework-based web apps, read the framework's own documentation on project structure — the conventions are very framework-specific</li>
          <li>When lost, look at how CI runs the project (the <code>.github/workflows/</code> or equivalent) — that tells you exactly what command starts things up</li>
        </ul>
      </section>

      <section class="learn-view__section">
        <h2 class="learn-view__section-title">Step 4 — Read the tests</h2>
        <p>Tests are often the most honest documentation in a codebase. They show you what a function is supposed to do with real inputs and expected outputs — no ambiguity, no outdated comments. If a function is confusing, find its tests and read those first. Not all projects have good test coverage (Atlas Insight flags this), but when tests exist they're invaluable for orientation.</p>
        <p>The concept is language-agnostic even if the syntax varies:</p>
        <pre class="learn-view__code"># Python (pytest style)
def test_parse_date_returns_none_for_invalid():
    assert parse_date("not a date") is None

// JavaScript (Jest style)
test('returns null for invalid input', () => {
  expect(parseDate('not a date')).toBeNull()
})</pre>
        <p class="learn-view__atlas-callout">Atlas Insight's <strong>CI Health</strong> signal measures the ratio of test files to source files. A repo with a low test ratio isn't necessarily undertested (integration tests cover a lot), but it's worth checking before you start making changes — you want to know what safety net exists.</p>
      </section>

      <section class="learn-view__section">
        <h2 class="learn-view__section-title">Don't skip the inline comments</h2>
        <p>Not all documentation lives in a README or a wiki. Many developers write comments directly in the code — for other contributors, or for their future self. A comment like <em>// must run before the cache is populated or you'll get stale data</em> explains something that would never appear in any external doc. When you're confused about why something works the way it does, read more carefully before searching elsewhere. The answer is often one line above the thing that's confusing you.</p>
      </section>

      <section class="learn-view__section">
        <h2 class="learn-view__section-title">Step 5 — Check the git log</h2>
        <p>The commit history tells the story of how the project evolved. Recent commits show what the team is focused on right now. Older commits give context on key decisions. Commit messages that explain <em>why</em> something changed are more valuable than ones that only say <em>what</em> changed.</p>
        <pre class="learn-view__code">git log --oneline -20       # last 20 commits, one line each
git log --stat              # which files each commit touched
git log -p -- path/to/file  # full change history for one file</pre>
        <p>A message like <em>"Rewrite auth middleware — token expiry was off by one"</em> tells you something went wrong once and was fixed. That context is invaluable before you touch that code.</p>
        <p class="learn-view__atlas-callout">The <strong>History tab</strong> in Atlas Insight visualizes this same data — commit frequency, contributor churn over time, and which months were most active. The <strong>Hot Files</strong> list (Architecture tab) shows which files have the most commit touches historically — those are often the most important or most volatile parts of the codebase.</p>
      </section>

      <section class="learn-view__section">
        <h2 class="learn-view__section-title">Step 6 — Run Atlas Insight</h2>
        <p>Paste the repo URL into Atlas Insight to get a structural summary in seconds. Rather than replacing reading the code, it gives you an orientation layer before you dive in:</p>
        <ul class="learn-view__list">
          <li><strong>Overview</strong> — language, age, top contributors, tech stack at a glance</li>
          <li><strong>Architecture</strong> — import graph, which files are most central, circular dependencies</li>
          <li><strong>Ownership</strong> — who knows what parts of the codebase (useful before asking questions)</li>
          <li><strong>Heuristics</strong> — health signals: is this actively maintained? is there burnout risk? how complex is the structure?</li>
          <li><strong>Contributing</strong> — what's actually available to work on right now, rated by difficulty</li>
        </ul>
        <p>These signals reflect what Atlas Insight's static analysis currently checks for — they're a starting point, not a complete picture. If something looks wrong or missing, it could simply be that our analyzers don't look for that pattern yet. A low OSS score doesn't mean a project is unwelcoming; it might just mean the team works differently, or that we're not measuring something we should be.</p>
        <p>Atlas Insight is still growing, and there are gaps — some languages, patterns, and signals we haven't built yet. If you spot something missing or broken, that might just be your first open-source contribution. <a href="https://github.com/LunarVagabond/Atlas-Insight/issues" target="_blank" rel="noopener noreferrer" class="learn-view__link">The project is open</a> and genuinely welcomes it.</p>
      </section>

      <section class="learn-view__section">
        <h2 class="learn-view__section-title">Community files worth looking for</h2>
        <p>These files appear in many well-maintained projects. They're not required — plenty of excellent projects don't have all of them — but when they exist they're usually worth reading:</p>
        <div class="learn-cmd-grid">
          <div class="learn-cmd">
            <code class="learn-cmd__cmd">README</code>
            <span class="learn-cmd__desc">Project overview, setup, and usage — start here</span>
          </div>
          <div class="learn-cmd">
            <code class="learn-cmd__cmd">CONTRIBUTING</code>
            <span class="learn-cmd__desc">How this team specifically wants changes submitted</span>
          </div>
          <div class="learn-cmd">
            <code class="learn-cmd__cmd">CHANGELOG</code>
            <span class="learn-cmd__desc">What changed between versions — useful historical context</span>
          </div>
          <div class="learn-cmd">
            <code class="learn-cmd__cmd">Manifest file</code>
            <span class="learn-cmd__desc">package.json, pyproject.toml, go.mod, Gemfile, Cargo.toml — whatever your ecosystem uses for dependencies</span>
          </div>
          <div class="learn-cmd">
            <code class="learn-cmd__cmd">CI config</code>
            <span class="learn-cmd__desc">.github/workflows/, .circleci/, etc. — shows exactly how the project is built and tested</span>
          </div>
          <div class="learn-cmd">
            <code class="learn-cmd__cmd">Environment example</code>
            <span class="learn-cmd__desc">.env.example or equivalent — lists required config values for local setup</span>
          </div>
        </div>
        <p class="learn-view__atlas-callout">Atlas Insight's <strong>Project tab</strong> scans for all of these and shows which are present or missing. The <strong>Community Health</strong> heuristic scores how well a repo is set up to welcome contributors based on these files.</p>
      </section>

    </div>

    <!-- ── Your First Contribution ──────────────────────────────────────────── -->
    <div v-if="activeTab === 'Your First Contribution'" class="learn-view__body">

      <section class="learn-view__section">
        <h2 class="learn-view__section-title">Why contribute to open source?</h2>
        <p>Contributing to open-source projects is one of the fastest ways to grow as a developer. You work with real codebases, get feedback from experienced engineers, build a public portfolio, and often directly improve tools you already use. It also builds habits — writing clear commit messages, thinking about code review, communicating in writing — that make you a better collaborator in any context.</p>
      </section>

      <section class="learn-view__section">
        <h2 class="learn-view__section-title">Finding a good first project</h2>
        <p>The best first project is one you actually use. If you rely on a library, tool, or app daily, you already understand the user perspective and have a natural motivation to improve it. Some signals worth checking before investing time:</p>
        <ul class="learn-view__list">
          <li><strong>Active maintenance</strong> — recent commits are a good sign. A project with no activity in a year may not review PRs promptly.</li>
          <li><strong>Beginner-friendly issues</strong> — GitHub issues tagged <code>good first issue</code> or <code>help wanted</code> are explicitly earmarked for newcomers. Not every project uses these labels, but when they do it's a useful signal.</li>
          <li><strong>A CONTRIBUTING guide</strong> — means the team has thought about onboarding. Read it carefully before submitting anything.</li>
          <li><strong>Responsive maintainers</strong> — look at recent PRs to see if they get feedback within a reasonable time.</li>
        </ul>
        <p class="learn-view__atlas-callout">Run the repo through Atlas Insight before committing time to it. The <strong>Contributing tab</strong> surfaces beginner-friendly issues pre-filtered and rated by difficulty. The <strong>Heuristics tab</strong> shows abandonment risk and burnout signals — a repo with a high abandonment score is less likely to actively review your PR. The <strong>OSS Score</strong> summarizes how contributor-ready the project is overall.</p>
      </section>

      <section class="learn-view__section">
        <h2 class="learn-view__section-title">The contribution workflow</h2>
        <ol class="learn-view__steps">
          <li><strong>Fork the repo</strong> — create your own copy on GitHub. This is where your changes will live until they're merged.</li>
          <li><strong>Clone your fork</strong> — <code>git clone https://github.com/YOUR-USERNAME/repo-name</code></li>
          <li><strong>Add the upstream remote</strong> — <code>git remote add upstream https://github.com/ORIGINAL-OWNER/repo-name</code>. This lets you pull in future changes from the original.</li>
          <li><strong>Create a branch</strong> — <code>git checkout -b fix/describe-your-change</code>. Never work directly on <code>main</code>.</li>
          <li><strong>Make your change.</strong> Keep it small and focused — one logical thing per PR.</li>
          <li><strong>Run the tests</strong> — make sure nothing is broken before you submit.</li>
          <li><strong>Commit clearly</strong> — <code>git commit -m "Fix: handle empty string in parse_date"</code>. The message should say what changed and optionally why.</li>
          <li><strong>Push to your fork</strong> — <code>git push origin fix/describe-your-change</code></li>
          <li><strong>Open a Pull Request</strong> — on GitHub, click "Compare &amp; pull request". Write a clear description: what you changed, why, and how you tested it.</li>
          <li><strong>Respond to review</strong> — maintainers may ask for changes. This is normal and expected. Revise and push to the same branch.</li>
        </ol>
      </section>

      <section class="learn-view__section">
        <h2 class="learn-view__section-title">Types of contributions (not just code)</h2>
        <div class="learn-concept-grid">
          <div class="learn-concept learn-concept--card">
            <div class="learn-concept__term">Documentation</div>
            <div class="learn-concept__body"><p>Fix typos, improve explanations, add missing examples, translate docs. Often the highest-impact contribution — and one of the best ways to start because you can do it before you fully understand the codebase.</p></div>
          </div>
          <div class="learn-concept learn-concept--card">
            <div class="learn-concept__term">Bug reports</div>
            <div class="learn-concept__body"><p>A well-written bug report with a minimal reproduction case is genuinely valuable. Include: what you expected, what happened, steps to reproduce, your environment (OS, version).</p></div>
          </div>
          <div class="learn-concept learn-concept--card">
            <div class="learn-concept__term">Tests</div>
            <div class="learn-concept__body"><p>Adding tests for untested edge cases or porting existing tests to a new test framework is a great way to contribute technical work while learning the codebase structure.</p></div>
          </div>
          <div class="learn-concept learn-concept--card">
            <div class="learn-concept__term">Community health files</div>
            <div class="learn-concept__body"><p>Adding a CONTRIBUTING guide, a CODE_OF_CONDUCT, or a CHANGELOG to a project that's missing them is a real, mergeable contribution that helps everyone who comes after you. Atlas Insight's <strong>Community Health</strong> heuristic measures exactly these gaps — projects that score high on that signal are good targets for this kind of contribution.</p></div>
          </div>
        </div>
      </section>

      <section class="learn-view__section">
        <h2 class="learn-view__section-title">What makes a good PR description</h2>
        <pre class="learn-view__code">## What does this do?
Fixes a crash that happened when `parse_date()` received an empty string.
The function now returns `None` instead of raising a ValueError.

## Why?
Reported in issue #42. The user was passing form input directly to
parse_date without validation, which is a reasonable use case.

## How was it tested?
Added a test in tests/test_utils.py: `test_parse_date_handles_empty_string`.
All existing tests still pass (ran `pytest`).</pre>
      </section>

    </div>

    <!-- ── Recommendations ────────────────────────────────────────────────── -->
    <div v-if="activeTab === 'Recommendations'" class="learn-view__body">

      <section class="learn-view__section">
        <h2 class="learn-view__section-title">Patterns worth building — not rules to follow</h2>
        <p>These are habits that tend to produce better outcomes — in code quality, in collaboration, and in personal growth. They're widely shared across the software community, and they show up clearly in the data when you analyze enough codebases. That said, context always wins. Your project, your team, and your constraints come first. Treat these as starting points for thinking, not mandates.</p>
      </section>

      <div class="learn-rec-list">

        <div class="learn-rec">
          <div class="learn-rec__number">01</div>
          <div class="learn-rec__content">
            <h3 class="learn-rec__title">Commit small and often</h3>
            <p>A commit that touches 3 files and has a clear message is infinitely more useful than one that touches 47 files and says "various fixes." Small commits are easier to review, easier to revert, and tell a clearer story in the log. If your commit message needs "and" to describe what changed, it's probably two commits.</p>
            <p class="learn-view__atlas-callout">In Atlas Insight, the History tab shows commit frequency patterns. Repos with consistent small commits tend to have more readable commit timelines and fewer "big bang" changes that are hard to trace back in history.</p>
          </div>
        </div>

        <div class="learn-rec">
          <div class="learn-rec__number">02</div>
          <div class="learn-rec__content">
            <h3 class="learn-rec__title">Read code more than you write it</h3>
            <p>The fastest way to become a better writer is to read a lot. Same with code. Every time you use an open-source library, spend 10 minutes reading the source. You'll pick up patterns, idioms, and naming conventions that are hard to learn any other way.</p>
            <p class="learn-view__atlas-callout">Atlas Insight is a good tool for orientation — run any public repo through it and use the Architecture and Ownership tabs to understand structure before reading individual files. The import graph shows which parts of the code are most central before you've read a single line.</p>
          </div>
        </div>

        <div class="learn-rec">
          <div class="learn-rec__number">03</div>
          <div class="learn-rec__content">
            <h3 class="learn-rec__title">Write the commit message before writing the code</h3>
            <p>If you can't write a clear one-sentence description of what you're about to do, you probably don't have a clear enough picture of the task yet. The message forces clarity. "Add input validation to the login form" is a task. "Stuff" is not.</p>
          </div>
        </div>

        <div class="learn-rec">
          <div class="learn-rec__number">04</div>
          <div class="learn-rec__content">
            <h3 class="learn-rec__title">Understand the problem before touching code</h3>
            <p>Re-read the bug report or feature request twice. Reproduce the bug locally before trying to fix it. Jumping straight to code is often slower than thinking first — especially in an unfamiliar codebase.</p>
          </div>
        </div>

        <div class="learn-rec">
          <div class="learn-rec__number">05</div>
          <div class="learn-rec__content">
            <h3 class="learn-rec__title">Don't fear the terminal</h3>
            <p>GUI tools for Git are fine, but understanding the underlying commands gives you a much clearer mental model of what's actually happening. When something goes wrong (and it will), knowing what <code>git reflog</code> does can save an hour of panic.</p>
          </div>
        </div>

        <div class="learn-rec">
          <div class="learn-rec__number">06</div>
          <div class="learn-rec__content">
            <h3 class="learn-rec__title">Tests are part of the feature</h3>
            <p>A feature without tests isn't finished — it's just untested. Get in the habit of writing at least a basic test for any non-trivial function you write. You don't need 100% coverage. You need confidence that the important paths work. How you test varies a lot by language and framework — follow the conventions already in the project you're working in.</p>
            <p class="learn-view__atlas-callout">Atlas Insight's <strong>CI Health</strong> signal measures test file ratio and whether a CI pipeline exists. Repos that score well on CI Health tend to catch regressions earlier and are generally safer to contribute to — you can run the test suite and know whether you broke something.</p>
          </div>
        </div>

        <div class="learn-rec">
          <div class="learn-rec__number">07</div>
          <div class="learn-rec__content">
            <h3 class="learn-rec__title">Ask questions publicly</h3>
            <p>When you're stuck on an open-source issue, comment on the issue itself instead of emailing the maintainer privately. Your question and the answer are now indexed, searchable, and useful to the next person who hits the same wall. This is how communities build institutional knowledge.</p>
          </div>
        </div>

        <div class="learn-rec">
          <div class="learn-rec__number">08</div>
          <div class="learn-rec__content">
            <h3 class="learn-rec__title">Slow down on naming</h3>
            <p>Names are the most-read documentation in a codebase. <code>processData()</code> tells you nothing. <code>normalizePhoneNumber()</code> tells you everything. Spend a few extra seconds naming things clearly — future you (and everyone else) will appreciate it. If you can't name something clearly, you might not fully understand it yet.</p>
          </div>
        </div>

        <div class="learn-rec">
          <div class="learn-rec__number">09</div>
          <div class="learn-rec__content">
            <h3 class="learn-rec__title">Embrace code review</h3>
            <p>Getting code reviewed feels vulnerable at first. Reframe it: every piece of feedback is a free lesson from someone who knows the codebase better than you do right now. The goal isn't to be right — it's to ship something good together. The best engineers actively seek review on work they're not sure about.</p>
          </div>
        </div>

        <div class="learn-rec">
          <div class="learn-rec__number">10</div>
          <div class="learn-rec__content">
            <h3 class="learn-rec__title">Build things you'll actually use</h3>
            <p>Tutorial projects rarely stick. The most effective learning happens when you're trying to solve a real problem — something you personally find annoying or interesting. The motivation to work through the hard parts is completely different when you care about the outcome.</p>
          </div>
        </div>

      </div>

      <section class="learn-view__section" style="margin-top: 2rem">
        <h2 class="learn-view__section-title">Where to go next</h2>
        <p>The <a href="/resources" class="learn-view__link">Resources page</a> has a curated list of the best learning material for each of these topics — documentation, books, interactive tools, and communities worth joining.</p>
      </section>

    </div>
  </div>
</template>
