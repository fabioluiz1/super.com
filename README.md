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

##### ESLint

Catches bugs and enforces strict typing rules at the code level.

- `typescript-eslint` strict preset
- `no-explicit-any` enforced as error
- `max-len` warns at 100 characters (URLs and strings excluded)
- `eslint-config-prettier` disables rules that conflict with Prettier

```bash
mise run lint          # check for lint errors
```
