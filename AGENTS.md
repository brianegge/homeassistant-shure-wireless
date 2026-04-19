# AGENTS.md - Instructions for AI Coding Agents

## Pre-commit Setup

This repo uses pre-commit hooks for code quality. **Always run these before committing:**

```bash
# Install pre-commit (if not already installed)
pip3 install pre-commit
# or on macOS: brew install pre-commit

# Install hooks for this repo
pre-commit install

# Run all hooks on all files
pre-commit run --all-files
```

### Common Issues

**"Shure" flagged as misspelling:**
- Already fixed - `.codespellrc` ignores "shure"

**Ruff formatting changes files:**
- This is expected - ruff auto-formats code
- After first run, stage changes with `git add -u`
- Run hooks again to verify

**Push permission denied:**
- Fork the repo first if you don't have write access
- Use `gh pr checkout <PR#>` to work on existing PRs

## Development Workflow

1. Checkout PR: `gh pr checkout <PR#>`
2. Install pre-commit: `pre-commit install`
3. Make changes
4. Run hooks: `pre-commit run --all-files`
5. Add changes: `git add -u` (or `git add -A` for new files)
6. Commit: `git commit -m "description"`
7. Push: `git push`

## CI Checks

The repo runs these checks on every PR:
- **Ruff** - Python linting and formatting
- **Codespell** - Spell checking (ignores: hass, shure)
- **YAML/JSON validation**
- **Trailing whitespace**
- **End of file fixer**

All checks must pass before merge.
