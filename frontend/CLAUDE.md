# Frontend — Claude Code Instructions

## Code Quality

- Stylelint for Sass (indented syntax via postcss-sass)
- ESLint with typescript-eslint strict preset (no `any`, max-len 100)
- Prettier for formatting (100 chars, single quotes, no semicolons)
- eslint-config-prettier disables ESLint rules that conflict with Prettier
- All checks run on every commit via the pre-commit hook
