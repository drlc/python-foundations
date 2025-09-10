# Base project
This is the base project for backend projects
## Setup
### Prerequisites

This repo assumes that [Docker](https://www.docker.com/get-started), [pyenv](https://github.com/pyenv/pyenv) and [Poetry](https://python-poetry.org/docs/) are already installed and configured.

### Install

- clone the repo and cd into it
- activate a compatible python version: `pyenv local 3.12.3`
- install the repo with all its dependencies: `make install`
    > NOTE: this also installs pre-commit hooks, and after the first commit it will take some time to setup the environments

### Usage for unix

Navigate to your project folder and run
- `make lint`: lints the entire project
- `make test`: runs all tests
- `make example`: run working example



## Example Application

This repository includes a complete example application (`example_app/`) that demonstrates the project structure and patterns.

### Running the Example App

1. **Start the databases:**
   ```bash
   cd example_app
   docker-compose up -d
   ```

2. **Run database migrations:**
   ```bash
   make migrate-up
   ```

3. **Start the development server:**
   ```bash
   make dev
   ```
   The API will be available at `http://localhost:8080`

4. **Access database management tools:**
   - Mongo Express: `http://localhost:8082` (admin UI for MongoDB)
   - PostgreSQL: Connect directly on `localhost:5432`

### Database Management

- **Migrate up:** `make migrate-up` - Apply all pending migrations
- **Migrate down:** `make migrate-down` - Rollback all migrations
- **Custom migration:** `make migrate MIGRATE_COMM='up 1'` - Apply specific migration commands

### Project Structure

The example app follows a clean architecture pattern:

```
example_app/
├── adapters/          # External interfaces (databases, APIs)
│   ├── gateways/      # HTTP clients and external API calls
│   └── stores/        # Database repositories
├── endpoints/         # Web API endpoints
│   └── api/           # REST API routes
├── usecases/          # Business logic layer
│   └── dto/           # Data transfer objects
├── migrations/        # Database schema migrations
├── settings.py        # Configuration management
└── main.py           # Application entry point
```

### Configuration

Copy `.env.example` to `.env` and adjust settings as needed. The application uses environment variables for configuration with sensible defaults.

### Database Credentials (Development)

- **PostgreSQL:** 
  - User: `local-user`
  - Password: `local-pwd`
  - Database: `local-database`
  - Port: `5432`

- **MongoDB:**
  - User: `local-user`
  - Password: `local-pwd`
  - Port: `27017`

