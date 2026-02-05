# Contributing to Jarvis Assistant

Thank you for your interest in contributing to Jarvis Assistant! This document provides guidelines and instructions for contributing.

## Getting Started

1. **Fork the repository**
2. **Clone your fork**
   ```bash
   git clone https://github.com/YOUR_USERNAME/jarvis-assistant.git
   cd jarvis-assistant
   ```

3. **Set up the development environment**
   
   **Python Backend:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # source .venv/bin/activate  # Linux/Mac
   pip install -r requirements.txt
   ```

   **React Frontend:**
   ```bash
   npm install
   ```

4. **Create a new branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

### Python Code Style
- Follow PEP 8 guidelines
- Use type hints where appropriate
- Add docstrings to classes and functions
- Keep functions focused and modular

### TypeScript/React Code Style
- Use TypeScript for all new components
- Follow React best practices
- Use functional components with hooks
- Keep components small and reusable

### Commit Messages
Use conventional commit format:
```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
- `feat(voice): add new wake word engine`
- `fix(ui): resolve hologram transparency issue`
- `docs(readme): update installation instructions`

## Testing

Before submitting a PR:
1. Test your changes thoroughly
2. Ensure Python code works: `python main.py`
3. Ensure frontend builds: `npm run build`
4. Check for linting errors

## Pull Request Process

1. Update the README.md if you've added features
2. Update documentation for any API changes
3. Ensure your code follows the style guidelines
4. Create a pull request with a clear description of changes
5. Link any related issues

## Code Review

- Be respectful and constructive
- Respond to feedback promptly
- Be open to suggestions and improvements

## Questions?

Feel free to open an issue for questions or discussions!
