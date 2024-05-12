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
