# Super.com Mock Interview

This monorepo uses [mise](https://mise.jdx.dev/) as a single tool to replace three:

- **`mise install`** pins and installs the exact Node version from `.mise.toml` — replaces **nvm**
- **`mise run <task>`** runs linters and formatters defined in `.mise.toml` — replaces **per-project npm scripts at the root**
- **`mise run setup`** generates a git pre-commit hook that runs all checks before every commit — replaces:
  - **husky** — installs git hooks (e.g., pre-commit) so scripts run automatically on `git commit`
  - **lint-staged** — filters `git diff --staged` to only lint/format files you're about to commit, not the entire codebase

## Quickstart

```bash
mise trust
mise install
mise run install:frontend
mise run setup          # install git pre-commit hook
```

### Frontend

#### Stylelint

Lints Sass files with `postcss-sass` for indented syntax support.

```bash
mise run lint:sass     # check for style errors
```

#### Code Quality

**ESLint** handles correctness — it finds bugs and enforces code rules (unused variables, implicit `any`, unsafe patterns). **Prettier** handles formatting — whitespace, line breaks, quotes, semicolons. `eslint-config-prettier` disables ESLint's formatting rules so only Prettier handles style.

##### ESLint

- `typescript-eslint` strict preset
- `no-explicit-any` enforced as error
- `max-len` warns at 100 characters (URLs and strings excluded)

```bash
mise run lint          # check for lint errors
```

##### Prettier

- `printWidth` 100 characters
- `singleQuote` enabled
- `semi` disabled (no semicolons)
- `trailingComma` all

```bash
mise run format        # auto-format all source files
mise run format:check  # check formatting without writing
```
