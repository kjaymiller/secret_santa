# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Secret Santa web application built with Django 5.2 and Python 3.13. The project manages Secret Santa events where participants are randomly assigned gift recipients while maintaining anonymity.

## Development Environment

This project uses Docker Compose with `just` command runner for task automation. All Django commands run inside Docker containers via the `utility` service.

### Key Technologies
- **Django 5.2** with Python 3.13
- **uv** for dependency management
- **PostgreSQL** via pgautoupgrade container
- **Docker Compose** for containerization
- **just** for command automation
- **pytest** for testing

## Common Commands

### Initial Setup
```bash
just bootstrap    # Initialize project (copies .env-dist to .env, locks deps, builds containers)
```

### Docker Operations
```bash
just build        # Build Docker containers
just up           # Start containers (web accessible at http://localhost:8000)
just start        # Start in detached mode
just down         # Stop and remove containers
just restart      # Restart containers
just console      # Open bash shell in utility container
```

### Django Management
```bash
just manage <command>              # Run any Django management command
just manage migrate                # Run migrations
just manage createsuperuser        # Create superuser
just manage makemigrations <app>   # Create migrations
```

### Testing and Linting
```bash
just test                    # Run pytest with default flags
just test <path/to/test>     # Run specific test
just lint                    # Run pre-commit hooks (ruff, pyupgrade, django-upgrade, djhtml, etc.)
just lint-autoupdate         # Update pre-commit hooks
```

### Database Operations
```bash
just pg_dump                 # Dump database to db.dump
just pg_restore              # Restore from db.dump
```

### Dependency Management
```bash
just lock          # Lock dependencies with uv
just upgrade       # Upgrade and lock dependencies
```

### Logs
```bash
just logs          # Show container logs
just tail          # Follow container logs
```

## Project Structure

```
secret_santa/
├── config/              # Django settings and root URL configuration
│   ├── settings.py      # Main settings (uses environs for env vars)
│   └── urls.py          # Root URL configuration
├── events/              # Main app for Secret Santa functionality
│   ├── models.py        # Event, Participant, Assignment, NotificationSchedule models
│   ├── admin.py         # Django admin configuration
│   └── migrations/      # Database migrations
├── frontend/            # Static assets (favicon, etc.)
├── static/              # Collected static files
├── conftest.py          # Pytest configuration and fixtures
├── justfile             # Command automation recipes
├── compose.yml          # Docker Compose configuration
├── Dockerfile           # Multi-stage Docker build
├── pyproject.toml       # Project dependencies and tool configuration
└── MERISE_PLAN.md       # Complete project specification (data models, use cases, business rules)
```

## Architecture Notes

### Django Apps

**events** - Core Secret Santa functionality:
- **Event**: Secret Santa events with auto-generated invite codes
- **Participant**: Event participants (can be linked to User accounts or anonymous)
- **Assignment**: Gift-giving assignments (enforces no self-assignment, unique giver per event)
- **NotificationSchedule**: Scheduled notifications (email/SMS) for events

All models use UUID primary keys. Key constraints:
- Events auto-generate unique 8-character invite codes
- Participants must have unique emails per event
- Assignments enforce circular chain structure with exclusion rules
- No self-assignments allowed (database constraint)

### Settings Configuration
- Settings use `environs[django]` for environment variable management
- `.env` file for local configuration (copied from `.env-dist` during bootstrap)
- Database URL: `env.dj_db_url("DATABASE_URL")` with default `postgres:///secret_santa`
- Email configured via `env.dj_email_url("EMAIL_URL")`
- Cache configured via `env.dj_cache_url("CACHE_URL")`

### Docker Services
- **db**: PostgreSQL 17 with auto-upgrade support
- **utility**: Service for running Django commands and tests
- **web**: Django development server on port 8000

### Testing Setup (conftest.py)
- `use_test_settings` fixture automatically applied to all tests
- DEBUG disabled in tests
- WhiteNoise middleware removed for tests
- Fast MD5 password hasher for test performance
- pytest-django with `--nomigrations --reuse-db` by default

### Pre-commit Hooks
All hooks target Python 3.13+ and Django 5.0+:
- **ruff**: Linting and formatting (120 char line length)
- **pyupgrade**: Upgrade syntax to Python 3.13+
- **django-upgrade**: Upgrade to Django 5.0+ patterns
- **djhtml**: Format Django templates (4-space tabs)
- **djade**: Django 5.2 template compatibility
- **blacken-docs**: Format code in documentation

## Project Specification

See `MERISE_PLAN.md` for complete project specification including:
- Data models (EVENT, USER, PARTICIPANT, ASSIGNMENT, NOTIFICATION_SCHEDULE)
- Business rules and constraints
- Assignment algorithm (circular chain with exclusions)
- API endpoint structure
- Development phases (MVP → Enhanced → Advanced → Scale)
- Security considerations

### Key Business Rules
- Events require minimum 3 confirmed participants for assignments
- Assignments form a circular chain (each person gives to one, receives from one)
- No self-assignments allowed
- Exclusion rules must be respected and are reciprocal
- Participants join via invite code or email invitation
- Organizers cannot view specific assignments (privacy requirement)

## Adding New Django Apps

When creating new apps, add them to `INSTALLED_APPS` in `config/settings.py` under the "Our apps" section (currently empty).

## Running Commands in Container

All development commands run inside Docker containers. Use:
- `just manage <cmd>` for Django management commands
- `just run <cmd>` for arbitrary commands in utility container
- `just console` for interactive shell access
