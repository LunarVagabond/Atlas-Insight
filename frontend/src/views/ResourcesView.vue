<script setup lang="ts">
interface Resource {
  title: string
  url: string
  desc: string
  free: boolean
  type: 'docs' | 'interactive' | 'book' | 'video' | 'community' | 'tool'
}

interface ResourceSection {
  heading: string
  intro: string
  items: Resource[]
}

const TYPE_LABELS: Record<Resource['type'], string> = {
  docs: 'Docs',
  interactive: 'Interactive',
  book: 'Book',
  video: 'Video',
  community: 'Community',
  tool: 'Tool',
}

const SECTIONS: ResourceSection[] = [
  {
    heading: 'Git & Version Control',
    intro: 'Git is the foundation of modern software development. These resources go from absolute beginner to advanced internals.',
    items: [
      { title: 'Pro Git (book)', url: 'https://git-scm.com/book/en/v2', desc: 'The definitive Git reference book. Free to read online. Covers everything from first commit to rebasing internals.', free: true, type: 'book' },
      { title: 'Learn Git Branching', url: 'https://learngitbranching.js.org', desc: 'Hands-down the best interactive Git visualizer. You run real git commands and watch the commit graph update live.', free: true, type: 'interactive' },
      { title: 'Oh My Git!', url: 'https://ohmygit.org', desc: 'A card game that teaches Git concepts. Surprisingly effective for visual learners and complete beginners.', free: true, type: 'interactive' },
      { title: 'Git – the simple guide', url: 'https://rogerdudler.github.io/git-guide/', desc: 'No-nonsense one-page reference with the core commands explained plainly. Good quick bookmark.', free: true, type: 'docs' },
      { title: 'Atlassian Git Tutorials', url: 'https://www.atlassian.com/git/tutorials', desc: 'Deep tutorials on specific topics: rebasing, merging strategies, git hooks, workflows. Excellent for leveling up after the basics.', free: true, type: 'docs' },
      { title: 'GitHub Skills', url: 'https://skills.github.com', desc: 'Official GitHub interactive courses. You learn by doing — real PRs, real branches, bot feedback in the repo itself.', free: true, type: 'interactive' },
    ],
  },
  {
    heading: 'Open Source Contribution',
    intro: 'Finding your first project, understanding contribution norms, and navigating the community.',
    items: [
      { title: 'First Contributions', url: 'https://firstcontributions.github.io', desc: 'A real open-source repo designed specifically for your first ever pull request. Step-by-step, forking through merged PR.', free: true, type: 'interactive' },
      { title: 'Good First Issue', url: 'https://goodfirstissue.dev', desc: 'Curates beginner-friendly issues from hundreds of popular open-source projects. Filter by language.', free: true, type: 'tool' },
      { title: 'Up For Grabs', url: 'https://up-for-grabs.net', desc: 'Aggregates projects actively looking for contributors. Filters by label and language.', free: true, type: 'tool' },
      { title: 'Open Source Guides (GitHub)', url: 'https://opensource.guide', desc: 'In-depth guides on how open source works: how to contribute, how to maintain a project, how to build community.', free: true, type: 'docs' },
      { title: 'CodeTriage', url: 'https://www.codetriage.com', desc: 'Sends you one open GitHub issue per day from a project you care about. Low-pressure way to stay engaged.', free: true, type: 'tool' },
    ],
  },
  {
    heading: 'Learning to Code',
    intro: 'Structured paths for picking up programming fundamentals and specific languages.',
    items: [
      { title: 'The Odin Project', url: 'https://www.theodinproject.com', desc: 'Free full-stack curriculum covering HTML, CSS, JavaScript, and Ruby. Project-based. One of the most respected free resources available.', free: true, type: 'interactive' },
      { title: 'freeCodeCamp', url: 'https://www.freecodecamp.org', desc: 'Free certifications in web development, data science, and more. Thousands of coding challenges and a large community.', free: true, type: 'interactive' },
      { title: 'exercism.org', url: 'https://exercism.org', desc: 'Practice exercises in 65+ languages with human mentorship. The mentor model makes it stand out — real feedback on real solutions.', free: true, type: 'interactive' },
      { title: 'roadmap.sh', url: 'https://roadmap.sh', desc: 'Opinionated, community-built learning roadmaps for frontend, backend, DevOps, and dozens of specific skills. Great for orientation.', free: true, type: 'docs' },
      { title: 'CS50 (Harvard)', url: 'https://cs50.harvard.edu/x/', desc: "Harvard's intro computer science course, completely free. Sets a strong foundation in how computers actually work — memory, algorithms, data structures.", free: true, type: 'video' },
      { title: 'MDN Web Docs', url: 'https://developer.mozilla.org', desc: 'The authoritative reference for HTML, CSS, and JavaScript. If you build for the web, this is the tab you never close.', free: true, type: 'docs' },
      { title: 'Python.org Tutorial', url: 'https://docs.python.org/3/tutorial/', desc: "The official Python tutorial. Well-written, comprehensive, and authoritative. Best place to start learning Python.", free: true, type: 'docs' },
    ],
  },
  {
    heading: 'Code Quality & Engineering Practices',
    intro: 'Writing code that works is step one. Writing code that others can understand and maintain is where the craft is.',
    items: [
      { title: 'Refactoring Guru', url: 'https://refactoring.guru', desc: 'Explains design patterns and refactoring techniques with clear illustrations and code examples in multiple languages.', free: true, type: 'docs' },
      { title: 'Clean Code (book)', url: 'https://www.oreilly.com/library/view/clean-code-a/9780136083238/', desc: "Robert Martin's influential book on writing readable, maintainable code. Controversial in places but foundational for understanding why naming matters.", free: false, type: 'book' },
      { title: 'The Pragmatic Programmer (book)', url: 'https://pragprog.com/titles/tpp20/the-pragmatic-programmer-20th-anniversary-edition/', desc: 'Career-spanning advice on software craftsmanship. Less about syntax, more about how to think like a professional developer.', free: false, type: 'book' },
      { title: 'Google Engineering Practices', url: 'https://google.github.io/eng-practices/', desc: "Google's public guide to code review — what reviewers look for and how authors should respond. Excellent real-world reference.", free: true, type: 'docs' },
      { title: 'Conventional Commits', url: 'https://www.conventionalcommits.org', desc: 'A widely-adopted specification for writing structured, machine-readable commit messages. Worth adopting early.', free: true, type: 'docs' },
    ],
  },
  {
    heading: 'Tools Every Developer Uses',
    intro: 'Essential tooling you will encounter on almost any project.',
    items: [
      { title: 'GitHub Docs', url: 'https://docs.github.com', desc: 'Official documentation for GitHub: Actions, Issues, PRs, Pages, Projects. Authoritative and thorough.', free: true, type: 'docs' },
      { title: 'Regex101', url: 'https://regex101.com', desc: 'Interactive regex tester and debugger with a full explanation of each part of your pattern. Indispensable.', free: true, type: 'tool' },
      { title: 'explainshell.com', url: 'https://explainshell.com', desc: 'Paste any shell command and it breaks down each flag and argument with documentation. Incredibly useful when reading unfamiliar scripts.', free: true, type: 'tool' },
      { title: 'DevDocs', url: 'https://devdocs.io', desc: 'Unified, searchable offline documentation for hundreds of languages, frameworks, and tools. Fast and distraction-free.', free: true, type: 'docs' },
      { title: 'JSON Crack', url: 'https://jsoncrack.com', desc: 'Visualizes JSON, YAML, CSV, and XML as a graph. Useful for understanding complex API responses.', free: true, type: 'tool' },
    ],
  },
  {
    heading: 'Communities & Staying Current',
    intro: 'Development is a social practice. Good communities accelerate learning faster than any tutorial.',
    items: [
      { title: 'Hacker News', url: 'https://news.ycombinator.com', desc: 'Tech news and discussion. Reading the comments (selectively) exposes you to how experienced engineers think about problems.', free: true, type: 'community' },
      { title: 'dev.to', url: 'https://dev.to', desc: 'Developer blogging platform with a welcoming community. Good for beginner-to-intermediate articles and finding people to follow.', free: true, type: 'community' },
      { title: 'Stack Overflow', url: 'https://stackoverflow.com', desc: "You already know this one. Beyond Q&A: reading highly-upvoted answers on topics you don't yet understand is a surprisingly efficient way to learn.", free: true, type: 'community' },
      { title: 'GitHub Explore', url: 'https://github.com/explore', desc: 'Curated trending repos and topics. Good way to discover active projects in areas you care about.', free: true, type: 'community' },
      { title: 'The Changelog (podcast)', url: 'https://changelog.com/podcast', desc: 'Long-form conversations with open-source maintainers and engineers. Good for commutes. Helps contextualize the ecosystem.', free: true, type: 'community' },
    ],
  },
]
</script>

<template>
  <div class="resources-view">
    <div class="resources-view__hero">
      <h1 class="resources-view__title">Developer Resources</h1>
      <p class="resources-view__tagline">A curated collection of the best free (and a few paid) resources for learning and growing as a developer — from git basics to engineering practices.</p>
    </div>

    <div class="resources-view__body">
      <div
        v-for="section in SECTIONS"
        :key="section.heading"
        class="resources-section"
      >
        <h2 class="resources-section__heading">{{ section.heading }}</h2>
        <p class="resources-section__intro">{{ section.intro }}</p>
        <div class="resources-grid">
          <a
            v-for="item in section.items"
            :key="item.title"
            :href="item.url"
            target="_blank"
            rel="noopener noreferrer"
            class="resource-card"
          >
            <div class="resource-card__header">
              <span class="resource-card__title">{{ item.title }}</span>
              <div class="resource-card__badges">
                <span class="resource-card__type">{{ TYPE_LABELS[item.type] }}</span>
                <span v-if="item.free" class="resource-card__free">Free</span>
              </div>
            </div>
            <p class="resource-card__desc">{{ item.desc }}</p>
          </a>
        </div>
      </div>

      <div class="resources-view__footer-note">
        <p>Know a resource worth adding? <a href="https://github.com/LunarVagabond/Atlas-Insight/issues" target="_blank" rel="noopener noreferrer">Open an issue on GitHub</a> with a link and a sentence on why it belongs here.</p>
      </div>
    </div>
  </div>
</template>
