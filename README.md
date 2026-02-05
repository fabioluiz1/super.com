# Super.com Mock Interview

This monorepo uses [mise](https://mise.jdx.dev/) to pin tool versions (Node, etc.) and run tasks across subprojects. One `mise install` replaces manual version management, and `mise run` provides a unified interface to linters, formatters, and build scripts — no need for husky, lint-staged, or per-project npm scripts at the root.

## Quickstart

```bash
mise trust
mise install
mise run install:frontend
```
