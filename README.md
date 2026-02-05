# Super.com Mock Interview

This monorepo uses [mise](https://mise.jdx.dev/) to pin tool versions (Node, etc.) and run tasks across subprojects. One `mise install` replaces manual version management, and `mise run` provides a unified interface to linters, formatters, and build scripts — no need for husky, lint-staged, or per-project npm scripts at the root.

## Quickstart

```bash
mise trust
mise install
mise run install:frontend
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
