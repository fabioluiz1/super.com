# Claude Code Instructions

## Documentation Standards

All documentation must be **didactic, specific, and developer-friendly** — written as if explaining to a junior developer.

- Explain what each tool does and why it exists before listing configuration
- When two tools overlap (e.g., ESLint vs Prettier), explain the boundary between them
- One bullet per rule/setting — no prose lists like "no any types allowed, max line length 100"
- Keep descriptions concise but never vague — "replaces husky" is vague, "installs git hooks so scripts run automatically on `git commit`" is specific
- DX (Developer Experience) must be excellent: quickstart should get a dev running in copy-paste commands

## README Structure

- Root README covers monorepo-wide setup and all tool documentation
- Subproject READMEs (frontend/, backend/) contain only interview instructions and project-specific setup
- Don't duplicate information across READMEs — pick one location (DRY)
- Quickstart block: only setup commands, no lint/format commands (those go in tool sections)
- Tool sections show `mise run` commands (the monorepo interface), not `npm run` (the subproject interface)
- Build documentation incrementally — each commit adds only the docs for what that commit introduces

## Git Workflow

- Use `git rebase --autosquash` with `git commit --fixup=<sha>` to edit previous commits
- Never use `git reset --soft` — it changes the log story
- Each commit should be atomic: one logical change with its corresponding documentation, mise tasks, and README updates

## Mise

- mise is the single tool for version pinning, task running, and git hooks — replacing nvm, husky, and lint-staged
- All linter/formatter/build commands are defined as mise tasks in `.mise.toml`
- Task names must be specific and unambiguous: `install:frontend` not `install`, `lint:sass` not `lint:css`
- The `pre-commit` task depends on all check tasks and runs them in parallel
- `mise run setup` installs the git pre-commit hook — this is part of the quickstart, not optional

## Monorepo Structure

```
.mise.toml          # tool versions + all tasks
README.md           # quickstart + tool docs
frontend/           # React + Vite + TypeScript
backend/            # API server (built during interview)
```

## Code Quality

- Stylelint for Sass (indented syntax via postcss-sass)
- ESLint with typescript-eslint strict preset (no `any`, max-len 100)
- Prettier for formatting (100 chars, single quotes, no semicolons)
- eslint-config-prettier disables ESLint rules that conflict with Prettier
- All checks run on every commit via the pre-commit hook
