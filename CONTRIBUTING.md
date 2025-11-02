# Contributing to PayerHub

Thank you for your interest in contributing to PayerHub! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions with the community.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/payerHub.git`
3. Create a virtual environment: `python -m venv venv`
4. Activate it: `source venv/bin/activate` (Unix) or `venv\Scripts\activate` (Windows)
5. Install dependencies: `pip install -r requirements.txt`
6. Install dev dependencies: `pip install -e ".[dev]"`

## Development Workflow

1. Create a new branch: `git checkout -b feature/your-feature-name`
2. Make your changes
3. Run tests: `pytest`
4. Format code: `black src/ tests/`
5. Lint code: `flake8 src/ tests/`
6. Commit changes: `git commit -m "Description of changes"`
7. Push to your fork: `git push origin feature/your-feature-name`
8. Create a Pull Request

## Project Structure

```
payerHub/
├── src/                    # Source code
│   ├── api/               # API layer
│   ├── core/              # Core business logic
│   ├── integrations/      # External integrations
│   ├── infrastructure/    # Infrastructure code
│   └── web/               # Web UI
├── tests/                 # Test files
├── docs/                  # Documentation
├── scripts/               # Utility scripts
└── config/                # Configuration files
```

## Coding Standards

- Follow PEP 8 style guide
- Use type hints for function parameters and return values
- Write docstrings for all public functions and classes
- Keep functions small and focused
- Write tests for new features

## Testing

- Write unit tests for all new code
- Ensure all tests pass before submitting PR
- Aim for >80% code coverage
- Use pytest for testing

## Documentation

- Update README.md if adding new features
- Add docstrings to all public APIs
- Update relevant documentation in docs/

## Pull Request Process

1. Ensure all tests pass
2. Update documentation as needed
3. Add a clear description of changes
4. Reference any related issues
5. Wait for review from maintainers

## Questions?

Feel free to open an issue for any questions or concerns.
