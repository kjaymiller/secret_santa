# AGENTS.md

## Commands (via `just`)
- `just test <path>`: Run specific test (e.g., `just test tests/test_file.py`)
- `just test`: Run all tests (uses `pytest --nomigrations --reuse-db`)
- `just lint`: Run pre-commit hooks (ruff, blacken-docs, etc.)
- `just manage <cmd>`: Run Django commands (e.g., `makemigrations`, `migrate`)
- `just run <cmd>`: Run arbitrary commands in utility container

## Code Style & Standards
- **Stack:** Python 3.13+, Django 5.x.
- **Formatting:** Line length 120 chars. Use `ruff` for linting/formatting.
- **Imports:** Standard lib -> Third-party -> Local.
- **Models:** Use `uuid.uuid4()` for PKs. Define `related_name` and `Meta.ordering`.
- **Testing:** Use `pytest`. Fixtures in `conftest.py` override settings.
- **Conventions:** Follow existing patterns (e.g., `djade` for templates).
- **Environment:** All commands run in Docker. Do not run `pip`/`python` directly.

<!-- bv-agent-instructions-v1 -->

---

## Beads Workflow Integration

This project uses [beads_viewer](https://github.com/Dicklesworthstone/beads_viewer) for issue tracking. Issues are stored in `.beads/` and tracked in git.

### Essential Commands

```bash
# View issues (launches TUI - avoid in automated sessions)
bv

# CLI commands for agents (use these instead)
bd ready              # Show issues ready to work (no blockers)
bd list --status=open # All open issues
bd show <id>          # Full issue details with dependencies
bd create --title="..." --type=task --priority=2
bd update <id> --status=in_progress
bd close <id> --reason="Completed"
bd close <id1> <id2>  # Close multiple issues at once
bd sync               # Commit and push changes
```

### Workflow Pattern

1. **Start**: Run `bd ready` to find actionable work
2. **Claim**: Use `bd update <id> --status=in_progress`
3. **Branch**: Create a new branch or worktree for the issue
4. **Work**: Implement the task
5. **Complete**: Use `bd close <id>`
6. **Sync**: Always run `bd sync` at session end

### Key Concepts

- **Dependencies**: Issues can block other issues. `bd ready` shows only unblocked work.
- **Priority**: P0=critical, P1=high, P2=medium, P3=low, P4=backlog (use numbers, not words)
- **Types**: task, bug, feature, epic, question, docs
- **Blocking**: `bd dep add <issue> <depends-on>` to add dependencies

### Session Protocol

**Before ending any session, run this checklist:**

```bash
git status              # Check what changed
git add <files>         # Stage code changes
bd sync                 # Commit beads changes
git commit -m "..."     # Commit code
bd sync                 # Commit any new beads changes
git push                # Push to remote
```

### Best Practices

- Check `bd ready` at session start to find available work
- Update status as you work (in_progress → closed)
- Create a new branch or worktree when working on a new issue
- Create new issues with `bd create` when you discover tasks
- Use descriptive titles and set appropriate priority/type
- Always `bd sync` before ending session

<!-- end-bv-agent-instructions -->
