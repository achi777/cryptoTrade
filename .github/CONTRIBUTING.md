# Contributing to CryptoTrade

First off, thank you for considering contributing to CryptoTrade! 🎉

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Commit Messages](#commit-messages)
- [Testing](#testing)

## 📜 Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## 🤝 How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

- Use a clear and descriptive title
- Describe the exact steps to reproduce the problem
- Provide specific examples
- Describe the behavior you observed and what you expected
- Include screenshots if applicable
- Note your environment (OS, browser, versions)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- Use a clear and descriptive title
- Provide a detailed description of the proposed enhancement
- Explain why this enhancement would be useful
- List any alternative solutions you've considered

### Pull Requests

1. Fork the repo and create your branch from `main`
2. Make your changes
3. Add tests if applicable
4. Update documentation
5. Ensure tests pass
6. Submit a pull request

## 🛠️ Development Setup

### Prerequisites

- Docker Desktop (v20.10+)
- Docker Compose (v2.0+)
- Git

### Setup Steps

```bash
# 1. Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/cryptoTrade.git
cd cryptoTrade

# 2. Run installation
./install.sh

# 3. Verify everything works
docker-compose ps
curl http://localhost:5001/api/v1/health
```

### Development Workflow

```bash
# Start services
./start.sh

# View logs
./logs.sh backend     # Backend logs
./logs.sh frontend    # Frontend logs

# Access services
# Frontend: http://localhost:3000
# Backend: http://localhost:5001
# Swagger: http://localhost:5001/api/docs

# Stop services
./stop.sh

# Clean everything (for fresh start)
./clean.sh
```

### Backend Development

```bash
# Enter backend container
docker-compose exec backend bash

# Create migration
flask db revision -m "your message"

# Apply migrations
flask db upgrade

# Run Python shell
flask shell

# Run tests
pytest

# Format code
black app/
flake8 app/
```

### Frontend Development

```bash
# Enter frontend container
docker-compose exec frontend sh

# Install new package
npm install package-name

# Run linter
npm run lint

# Format code
npm run format

# Build production
npm run build
```

## 🔄 Pull Request Process

1. **Update Documentation**: Ensure README.md and relevant docs are updated
2. **Add Tests**: Include tests for new features
3. **Follow Style Guide**: Ensure code follows project conventions
4. **Update Changelog**: Add entry to CHANGELOG.md
5. **Link Issues**: Reference related issues in PR description
6. **Request Review**: Ask for code review from maintainers

### PR Title Format

```
<type>(<scope>): <subject>

Types: feat, fix, docs, style, refactor, test, chore
Examples:
- feat(trading): add limit order functionality
- fix(auth): resolve 2FA token expiration issue
- docs(api): update swagger documentation
```

## 📝 Coding Standards

### Python (Backend)

```python
# Follow PEP 8
# Use type hints
def get_user(user_id: int) -> User:
    """Get user by ID.

    Args:
        user_id: The user's unique identifier

    Returns:
        User object

    Raises:
        NotFoundError: If user doesn't exist
    """
    return User.query.get_or_404(user_id)

# Use f-strings for formatting
message = f"User {user.email} logged in"

# Prefer list comprehensions
active_users = [u for u in users if u.is_active]
```

### TypeScript (Frontend)

```typescript
// Use interfaces for types
interface User {
  id: number;
  email: string;
  isAdmin: boolean;
}

// Use functional components with hooks
const UserProfile: React.FC<Props> = ({ userId }) => {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    fetchUser(userId).then(setUser);
  }, [userId]);

  return <div>{user?.email}</div>;
};

// Use async/await
const fetchUser = async (id: number): Promise<User> => {
  const response = await api.get(`/users/${id}`);
  return response.data;
};
```

### General Guidelines

- **DRY**: Don't Repeat Yourself
- **SOLID**: Follow SOLID principles
- **KISS**: Keep It Simple, Stupid
- **Comments**: Write self-documenting code, comment only when necessary
- **Security**: Never commit secrets, use environment variables
- **Error Handling**: Always handle errors gracefully

## 📦 Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `perf`: Performance improvements
- `ci`: CI/CD changes
- `build`: Build system changes
- `revert`: Revert previous commit

### Examples

```bash
feat(auth): add 2FA support

Add two-factor authentication using TOTP.
Users can now enable 2FA in their account settings.

Closes #123

---

fix(trading): resolve order cancellation bug

Orders were not being cancelled correctly due to race condition.
Added row-level locking to prevent concurrent modifications.

Fixes #456

---

docs(readme): update installation instructions

Added troubleshooting section and Docker prerequisites.
```

## 🧪 Testing

### Backend Tests

```bash
# Run all tests
docker-compose exec backend pytest

# Run specific test file
docker-compose exec backend pytest tests/test_auth.py

# Run with coverage
docker-compose exec backend pytest --cov=app tests/

# Run specific test
docker-compose exec backend pytest tests/test_auth.py::test_login
```

### Frontend Tests

```bash
# Run tests
docker-compose exec frontend npm test

# Run with coverage
docker-compose exec frontend npm test -- --coverage

# Update snapshots
docker-compose exec frontend npm test -- -u
```

### Writing Tests

#### Backend Test Example

```python
import pytest
from app import create_app, db
from app.models.user import User

@pytest.fixture
def client():
    app = create_app('testing')
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()

def test_user_registration(client):
    """Test user registration endpoint."""
    response = client.post('/api/v1/auth/register', json={
        'email': 'test@example.com',
        'password': 'SecurePass123'
    })
    assert response.status_code == 201
    assert 'user' in response.json
```

#### Frontend Test Example

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import LoginForm from './LoginForm';

describe('LoginForm', () => {
  it('submits form with email and password', () => {
    const handleSubmit = jest.fn();
    render(<LoginForm onSubmit={handleSubmit} />);

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: 'test@example.com' }
    });

    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'password123' }
    });

    fireEvent.click(screen.getByRole('button', { name: /login/i }));

    expect(handleSubmit).toHaveBeenCalledWith({
      email: 'test@example.com',
      password: 'password123'
    });
  });
});
```

## 🏗️ Project Structure

```
cryptoTrade/
├── backend/
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── models/       # Database models
│   │   ├── services/     # Business logic
│   │   └── utils/        # Utilities
│   └── tests/            # Backend tests
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   ├── redux/        # Redux store
│   │   └── services/     # API services
│   └── tests/            # Frontend tests
└── .github/              # GitHub configs
```

## 🔒 Security

- Never commit `.env` files
- Never commit API keys or secrets
- Always validate user input
- Use parameterized queries
- Follow OWASP guidelines
- Report security issues privately

## 📞 Getting Help

- 💬 [Discussions](https://github.com/yourusername/cryptoTrade/discussions)
- 🐛 [Issues](https://github.com/yourusername/cryptoTrade/issues)
- 📧 Email: your-email@example.com

## 📄 License

By contributing, you agree that your contributions will be licensed under the same license as the project.

## 🙏 Thank You!

Your contributions make this project better! 🎉
