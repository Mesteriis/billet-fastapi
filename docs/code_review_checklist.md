# Code Review Checklist

This checklist ensures consistent code quality and proper documentation across the project.

## 📋 Pre-Review Automated Checks

Before manual review, ensure all automated checks pass:

- [ ] `make check-docstrings` - Docstring language and format check
- [ ] `make lint` - Code formatting and linting
- [ ] `make typecheck` - Type checking with mypy
- [ ] `make test` - All tests pass
- [ ] `make check-imports` - Inter-app import validation
- [ ] `pre-commit run --all-files` - All pre-commit hooks pass

## 📝 Documentation Review

### ✅ Docstring Requirements

**For API Modules (src/apps/\*/api/, src/core/, src/tools/)**:

- [ ] All docstrings are in **English**
- [ ] Follow **Sphinx format** with proper sections
- [ ] Include **Args** section with parameter types and descriptions
- [ ] Include **Returns** section with return type and description
- [ ] Include **Raises** section for potential exceptions
- [ ] Include **Example** section with practical usage
- [ ] API routes include **curl examples** and **response examples**

**For Classes and Functions**:

- [ ] Class docstrings describe purpose and main functionality
- [ ] Method docstrings explain what they do, not how
- [ ] Public methods have complete documentation
- [ ] Private methods (`_method`) have brief descriptions if complex

**Exceptions**:

- [ ] Simple `__init__.py` files (exports only) - no docstrings needed
- [ ] Entry points (`main.py`, `cli.py`) - simple one-liners only
- [ ] Test files - brief descriptions only

### ❌ Documentation Red Flags

- [ ] **Russian text in API docstrings** (автоматически проверяется)
- [ ] Missing docstrings in new public APIs
- [ ] Vague descriptions ("Does stuff", "Helper function")
- [ ] Missing parameter documentation
- [ ] No examples for complex functions
- [ ] API routes without curl examples

## 🏗️ Code Architecture Review

### Import Checks

- [ ] No direct imports between apps (only through interfaces)
- [ ] Proper dependency injection usage
- [ ] Core modules don't import from apps
- [ ] TYPE_CHECKING imports used correctly for circular dependencies

### FastAPI Best Practices

- [ ] Proper HTTP status codes
- [ ] Consistent error handling with HTTPException
- [ ] Request/Response models use Pydantic
- [ ] Dependency injection follows established patterns
- [ ] Route functions have proper type hints

### Database & Repository Layer

- [ ] Repository pattern followed correctly
- [ ] No direct SQLAlchemy usage in API routes
- [ ] Proper async/await usage
- [ ] Database sessions managed correctly
- [ ] No N+1 query problems

## 🧪 Testing Requirements

### Test Coverage

- [ ] New features have corresponding tests
- [ ] Critical paths have integration tests
- [ ] API endpoints have request/response tests
- [ ] Error conditions are tested
- [ ] Tests use factory patterns for data creation

### Test Quality

- [ ] Test names clearly describe what is being tested
- [ ] Tests are isolated and can run independently
- [ ] No hardcoded values (use factories and fixtures)
- [ ] Tests follow AAA pattern (Arrange, Act, Assert)

## 🔒 Security Review

### Authentication & Authorization

- [ ] Sensitive endpoints require proper authentication
- [ ] Role-based access control implemented correctly
- [ ] No sensitive data in logs or responses
- [ ] Input validation and sanitization

### Data Protection

- [ ] No plain text passwords
- [ ] Personal data handling follows privacy rules
- [ ] SQL injection prevention
- [ ] XSS prevention measures

## ⚡ Performance Considerations

### Database Performance

- [ ] Efficient database queries (no SELECT N+1)
- [ ] Proper indexing for new database columns
- [ ] Pagination implemented for list endpoints
- [ ] Bulk operations where appropriate

### API Performance

- [ ] Response times acceptable for endpoint type
- [ ] Proper caching where applicable
- [ ] File uploads handled efficiently
- [ ] Large responses paginated

## 🎨 Code Style & Quality

### Code Organization

- [ ] Functions are focused and do one thing well
- [ ] Classes have clear responsibilities
- [ ] Code is readable without extensive comments
- [ ] Consistent naming conventions

### Error Handling

- [ ] Proper exception handling
- [ ] Meaningful error messages
- [ ] Consistent error response format
- [ ] Logging at appropriate levels

### Type Safety

- [ ] All functions have type hints
- [ ] Modern Python type syntax (`str | None` not `Optional[str]`)
- [ ] No `# type: ignore` without justification
- [ ] Generic types used appropriately

## 📊 API-Specific Checklist

### New API Endpoints

- [ ] **Curl examples in docstring** showing request format
- [ ] **Response examples** showing expected JSON structure
- [ ] Proper OpenAPI documentation generation
- [ ] Consistent URL patterns and naming
- [ ] Appropriate HTTP methods

### Request/Response Models

- [ ] Pydantic models with proper validation
- [ ] Clear field descriptions
- [ ] Appropriate field types and constraints
- [ ] Example values in schema

### Authentication Flow

- [ ] Token validation works correctly
- [ ] Session management follows security best practices
- [ ] Refresh token rotation implemented
- [ ] Logout invalidates tokens properly

## 🚀 Feature Completion

### New Features

- [ ] Feature works as described in requirements
- [ ] Edge cases handled appropriately
- [ ] Backward compatibility maintained
- [ ] Database migrations if needed

### Bug Fixes

- [ ] Root cause addressed, not just symptoms
- [ ] Regression tests added
- [ ] Related functionality still works
- [ ] Performance impact considered

## 📚 Documentation Updates

### Additional Documentation

- [ ] README updated if public API changed
- [ ] Migration notes if database changes
- [ ] Configuration documentation updated
- [ ] API documentation generated correctly

### Examples and Guides

- [ ] Working examples for new features
- [ ] Integration guides updated
- [ ] Troubleshooting information added
- [ ] Developer setup instructions current

## ✅ Final Approval Criteria

Before approving a PR, all of these must be satisfied:

1. **✅ All automated checks pass**
2. **✅ Documentation meets English/Sphinx requirements**
3. **✅ Code follows established patterns**
4. **✅ Tests provide adequate coverage**
5. **✅ Security considerations addressed**
6. **✅ Performance impact acceptable**
7. **✅ No breaking changes without discussion**

## 🚨 Immediate Rejection Criteria

Reject immediately if any of these are found:

- **❌ Russian text in API docstrings** (automation should catch this)
- **❌ Hardcoded secrets or credentials**
- **❌ SQL injection vulnerabilities**
- **❌ Breaks existing tests without justification**
- **❌ Removes security features**
- **❌ Direct database queries in API routes**

## 🛠️ Review Tools

### Automated Tools

```bash
# Run full quality check
make quality

# Check specific aspects
make check-docstrings
make check-imports
make lint
make typecheck
make test-cov
```

### Manual Review Commands

```bash
# Check for Russian text manually
grep -r "а-я" src/apps/*/api/ || echo "No Cyrillic found"

# Check docstring coverage
scripts/check_docstring_language.py src/apps/auth/api/auth_routes.py

# Validate OpenAPI generation
curl http://localhost:8000/openapi.json | jq .
```

## 💡 Review Tips

### For Reviewers

- Focus on **architecture and design** first, then details
- Check that **documentation examples actually work**
- Verify **error handling** is comprehensive
- Look for **security implications** of changes
- Ensure **consistency** with existing codebase

### For Authors

- **Self-review** before requesting review
- **Test all examples** in docstrings manually
- **Run automated checks** locally first
- **Provide context** about design decisions
- **Update documentation** proactively

## 📈 Continuous Improvement

### Monthly Review

- [ ] Update checklist based on common issues
- [ ] Review automated check coverage
- [ ] Assess documentation quality trends
- [ ] Identify recurring problems

### Tool Updates

- [ ] Keep linting tools updated
- [ ] Add new automated checks as needed
- [ ] Improve developer experience
- [ ] Share best practices with team

---

**Remember**: Good code review is about maintaining quality, sharing knowledge, and building better software together! 🚀
