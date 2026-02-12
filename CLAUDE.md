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
- **Never bypass pre-commit** — `--no-verify` is forbidden. If the hook fails on a `fixup!` commit message, stash any pending changes with `git stash`, fix the issue, then `git stash pop` after the rebase. The hook exists to catch real problems; skipping it means broken code can enter the history.

## Mise

- mise is the single tool for version pinning, task running, and git hooks — replacing nvm, husky, and lint-staged
- All linter/formatter/build commands are defined as mise tasks in `.mise.toml`
- **Always use `mise run <task>` to run commands** — never invoke tools directly (`uv run pytest`, `npx jest`, `npm run lint`, etc.). The mise tasks have the correct working directory, flags, and environment already configured.
- Task names must be specific and unambiguous: `install:frontend` not `install`, `lint:sass` not `lint:css`
- The `pre-commit` task depends on all check tasks and runs them in parallel
- `mise run setup` installs the git pre-commit hook — this is part of the quickstart, not optional

## Monorepo Structure

```
.mise.toml          # tool versions + all tasks
README.md           # quickstart + tool docs (succinct)
docs/               # deep-dive guides (linked from README)
frontend/           # React + Vite + TypeScript
backend/            # FastAPI + SQLAlchemy + PostgreSQL
```

Workspace-specific rules live in their own CLAUDE.md files:

- `frontend/CLAUDE.md` — React, TypeScript, Sass, ESLint, Prettier, Stylelint
- `backend/CLAUDE.md` — Python, FastAPI, SQLAlchemy, Alembic, testing, logging
