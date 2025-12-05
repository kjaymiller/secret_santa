<h1 align="center">Secret Santa 🎅</h1>

<p>
  <a href="https://github.com/jefftriplett/django-startproject/actions" target="_blank">
    <img alt="CI" src="https://github.com/jefftriplett/django-startproject/workflows/CI/badge.svg" />
  </a>
</p>

> A Django web application for organizing Secret Santa gift exchanges with privacy and ease

## Overview

Secret Santa is a web application that helps groups organize gift exchanges where participants are randomly assigned a gift recipient while maintaining complete anonymity. The application handles participant management, random assignments with exclusion rules, and scheduled notifications.

## Core Features

- **Event Management**: Create and manage Secret Santa events with unique invite codes
- **Participant Privacy**: Anonymous participation with secure assignment viewing
- **Smart Assignment**: Circular chain algorithm with exclusion rules (no self-assignments)
- **Flexible Participation**: Link to user accounts or participate anonymously
- **Notifications**: Scheduled email/SMS reminders for participants
- **Minimum Threshold**: Requires 3+ confirmed participants before generating assignments

## Technology Stack

- **Django 5.2** with Python 3.13
- **PostgreSQL 17** with auto-upgrade support
- **Docker Compose** for containerization
- **uv** for fast dependency management
- **just** command runner for task automation
- **pytest** for testing with django-test-plus and model-bakery

## Quick Start

### Prerequisites

- Docker (OrbStack recommended)
- just command runner

### Installation

```shell
# Clone the repository
$ git clone <repository-url>
$ cd secret_santa

# Bootstrap the project (copies .env, locks dependencies, builds containers)
$ just bootstrap

# Run migrations
$ just manage migrate

# Create a superuser
$ just manage createsuperuser

# Start the development server
$ just up
```

The application will be available at http://localhost:8000/

## Usage

### Development Commands

```shell
# Start containers (foreground)
$ just up

# Start containers (background)
$ just start

# Stop containers
$ just down

# Restart containers
$ just restart

# View logs
$ just logs

# Follow logs
$ just tail

# Open bash console in container
$ just console
```

### Django Management

```shell
# Run any Django management command
$ just manage <command>

# Create migrations
$ just manage makemigrations events

# Run migrations
$ just manage migrate

# Create superuser
$ just manage createsuperuser
```

### Testing and Code Quality

```shell
# Run all tests
$ just test

# Run specific test
$ just test events/tests/test_models.py

# Run linters and formatters
$ just lint

# Update pre-commit hooks
$ just lint-autoupdate
```

### Database Operations

```shell
# Dump database to file
$ just pg_dump

# Restore database from dump
$ just pg_restore
```

### Dependency Management

```shell
# Lock dependencies
$ just lock

# Upgrade and lock dependencies
$ just upgrade
```

## Project Structure

```
secret_santa/
├── config/              # Django settings and root URL configuration
│   ├── settings.py      # Main settings with environment variable support
│   └── urls.py          # Root URL configuration
├── events/              # Core Secret Santa functionality
│   ├── models.py        # Event, Participant, Assignment, NotificationSchedule
│   ├── admin.py         # Django admin configuration
│   ├── views.py         # View handlers
│   └── migrations/      # Database migrations
├── frontend/            # Static assets (favicon, etc.)
├── static/              # Collected static files
├── templates/           # Django templates
├── conftest.py          # Pytest configuration and fixtures
├── justfile             # Command automation recipes
├── compose.yml          # Docker Compose configuration
├── Dockerfile           # Multi-stage Docker build
├── pyproject.toml       # Project dependencies and configuration
├── CLAUDE.md            # Development guidance for Claude Code
└── MERISE_PLAN.md       # Complete project specification
```

## Data Models

### Event
- Auto-generated 8-character invite codes
- Organizer relationship (User model)
- Event details (name, description, budget, dates)
- Privacy controls

### Participant
- Linked to User account or anonymous
- Unique email per event
- Confirmation status tracking
- Gift preferences and exclusions

### Assignment
- One-to-one gift-giving relationships
- Circular chain structure
- No self-assignment constraint
- Reveal status tracking

### NotificationSchedule
- Email and SMS notification support
- Scheduled delivery times
- Delivery status tracking

## Key Business Rules

1. **Minimum Participants**: Events require at least 3 confirmed participants before assignments can be generated
2. **Circular Assignment**: Each participant gives to one person and receives from one person
3. **No Self-Assignments**: Database-level constraint prevents self-assignment
4. **Exclusion Rules**: Reciprocal exclusions are respected during assignment
5. **Organizer Privacy**: Organizers cannot view specific assignments to maintain anonymity
6. **Unique Participants**: Each email can only participate once per event

## Configuration

The project uses environment variables for configuration. Copy `.env-dist` to `.env` and customize:

```shell
# Database
DATABASE_URL=postgres://user:pass@db:5432/secret_santa

# Email
EMAIL_URL=smtp://user:pass@smtp.example.com:587

# Cache
CACHE_URL=redis://redis:6379/0

# Django
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1
```

## Testing

Tests are configured with pytest-django and include:

- Automatic test settings via `use_test_settings` fixture
- Fast MD5 password hasher for performance
- `--nomigrations --reuse-db` flags by default
- Model factories via model-bakery
- Enhanced assertions via django-test-plus

```shell
# Run all tests
$ just test

# Run with coverage
$ just test --cov=events

# Run specific test file
$ just test events/tests/test_models.py::TestEvent
```

## Code Quality

Pre-commit hooks enforce code quality standards:

- **ruff**: Linting and formatting (120 char line length)
- **pyupgrade**: Python 3.13+ syntax
- **django-upgrade**: Django 5.0+ patterns
- **djhtml**: Django template formatting (4-space tabs)
- **djade**: Django 5.2 template compatibility
- **blacken-docs**: Format code in documentation

```shell
# Run all hooks
$ just lint

# Update hooks to latest versions
$ just lint-autoupdate
```

## Available Just Commands

```shell
$ just --list
Available recipes:
    bootstrap *ARGS           # Initialize project with dependencies and environment
    build *ARGS               # Build Docker containers with optional args
    console                   # Open interactive bash console in utility container
    down *ARGS                # Stop and remove containers, networks
    lint *ARGS                # Run pre-commit hooks on all files
    lint-autoupdate *ARGS     # Update pre-commit hooks to latest versions
    lock *ARGS                # Lock dependencies with uv
    logs *ARGS                # Show logs from containers
    manage *ARGS              # Run Django management commands
    pg_dump file='db.dump'    # Dump database to file
    pg_restore file='db.dump' # Restore database dump from file
    restart *ARGS             # Restart containers
    run *ARGS                 # Run command in utility container
    start *ARGS="--detach"    # Start services in detached mode by default
    stop *ARGS                # Stop services (alias for down)
    tail                      # Show and follow logs
    test *ARGS                # Run pytest with arguments
    up *ARGS                  # Start containers
    upgrade                   # Upgrade dependencies and lock
```

## Documentation

- **CLAUDE.md**: Development guidance and project overview for Claude Code
- **MERISE_PLAN.md**: Complete project specification with data models, business rules, API structure, and development phases

## Contributing

Contributions are welcome! Please ensure:

1. All tests pass: `just test`
2. Code passes linting: `just lint`
3. New features include tests
4. Documentation is updated as needed

## License

See LICENSE file for details.

## Built With

This project was bootstrapped with [django-startproject](https://github.com/jefftriplett/django-startproject) by Jeff Triplett.
