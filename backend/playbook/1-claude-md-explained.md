# CLAUDE.md — Rules for the AI Agent

CLAUDE.md is a project-level instructions file that Claude Code reads automatically. It contains coding conventions, architectural patterns, and constraints — so the AI generates code that follows your preferences instead of generic defaults.

## Hierarchical merging

Claude Code merges CLAUDE.md files hierarchically — when working in `backend/`, it reads both the root and `backend/CLAUDE.md`. This mirrors how `.eslintrc` or `tsconfig.json` work in monorepos: shared rules at the root, workspace-specific rules in subfolders.

- **Root `CLAUDE.md`** — monorepo-wide: git workflow, mise conventions, documentation standards
- **`backend/CLAUDE.md`** — Python/FastAPI-specific: async everywhere, `Mapped[]` annotations, `select()` not `session.query()`, mypy strict, Pydantic v2 `ConfigDict`, testing patterns

When the AI generates code, these rules are applied automatically — you don't have to repeat them in every prompt.

## Living document

The key insight: **CLAUDE.md is a living document**. As you build features during the interview and discover new patterns (pagination conventions, eager loading rules, error handling layers), you add them to `backend/CLAUDE.md` so every subsequent prompt benefits. This is demonstrated in Round 1 Step 6 and Round 5.
