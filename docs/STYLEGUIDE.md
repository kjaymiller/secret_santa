# Secret Santa Style Guide 🎅

This document outlines the coding standards, conventions, and documentation styles for the Secret Santa project.

## 📝 Code Style

We adhere to strict coding standards enforced by pre-commit hooks.

### Python
- **Formatter**: `ruff`
- **Line Length**: 120 characters
- **Target Version**: Python 3.13+
- **Imports**: Standard lib -> Third-party -> Local (sorted by ruff)

### Django
- **Version**: 5.2 (Future-proof patterns)
- **Templates**: Formatted with `djhtml` (4-space tabs), modernized with `djade`

### Documentation
- **Format**: Markdown
- **Linting**: `blacken-docs` ensures code blocks in docs are formatted

## 🧪 Testing

- **Runner**: `pytest`
- **Conventions**:
  - Use `conftest.py` fixtures
  - No DB migrations during tests (`--nomigrations`)
  - Fast password hasher for speed

## 📊 Visuals & Diagrams

We use [Kroki](https://kroki.kjaymiller.dev) to render diagrams dynamically from text. This allows diagrams to be version-controlled as text while being viewable as images.

### Example Workflow

Here is an example of our development workflow rendered via Kroki:

![Development Workflow](https://kroki.kjaymiller.dev/mermaid/svg/eNpLL0osyFAIceFSAALH6NDi1KJYBV1du5rwosyS1GIF5_yU1BoFJw3n_NzczBJNsDInsIKQosz09NSi4hoF52qfzLySzLz0WrC0M1g6ILEYKOUS7ZtalJ4aiyThlpiZU6PgGu2WWQERdgUJKzgBAEpMKAs=)

### How to Add Diagrams
1. Create your diagram using Mermaid, PlantUML, etc.
2. Convert the code to a compressed base64 URL (using the project's helper scripts or online tools).
3. Embed using standard Markdown image syntax: `![Alt](URL)`

## 🛠️ Tools

- **CLI**: `just` for all common tasks
- **Dependency Management**: `uv`
- **Containerization**: Docker Compose

Run `just --list` to see all available commands.
