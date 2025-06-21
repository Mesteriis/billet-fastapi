# Docstring Templates for Developers

This document provides standard templates for writing consistent Sphinx-format docstrings in English across the project.

## 📋 General Rules

1. **Language**: All docstrings in API modules, services, models, and core libraries must be in **English**
2. **Format**: Use **Sphinx format** with proper sections
3. **Required Sections**: Args, Returns, Raises, Example (for public APIs)
4. **Style**: Professional, concise, and informative

## 📁 Module-Level Docstring

```python
"""
Brief module description.

Detailed description of what this module provides, its main purpose,
and how it fits into the larger system architecture.

Example:
    >>> from module import SomeClass
    >>> instance = SomeClass()
    >>> result = instance.method()
    >>> assert result is not None
"""
```

## 🏛️ Class Docstring

```python
class UserService:
    """
    User management service with CRUD operations.

    Provides comprehensive user management functionality including
    registration, authentication, profile management, and permissions.

    Attributes:
        user_repo (UserRepository): Repository for user data operations
        session_service (SessionService): Session management service

    Example:
        >>> user_service = UserService(user_repo, session_service)
        >>> user = await user_service.create_user(user_data)
        >>> assert user.id is not None
    """
```

## ⚙️ Function/Method Docstring

### Simple Function

```python
def calculate_age(birth_date: date) -> int:
    """
    Calculate age in years from birth date.

    Args:
        birth_date (date): Date of birth

    Returns:
        int: Age in complete years

    Example:
        >>> from datetime import date
        >>> age = calculate_age(date(1990, 5, 15))
        >>> assert isinstance(age, int)
        >>> assert age >= 0
    """
```

### Async Function with Exceptions

```python
async def authenticate_user(email: str, password: str) -> User | None:
    """
    Authenticate user with email and password.

    Validates user credentials against the database and returns
    the user object if authentication is successful.

    Args:
        email (str): User email address
        password (str): Plain text password

    Returns:
        User | None: User object if authenticated, None if invalid credentials

    Raises:
        ValidationError: If email format is invalid
        DatabaseError: If database connection fails

    Example:
        >>> user = await authenticate_user("john@example.com", "password123")
        >>> if user:
        ...     assert user.email == "john@example.com"
        ...     assert user.is_authenticated
    """
```

### API Route Function

````python
@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    user_data: UserCreateRequest,
    user_service: UserServiceDep,
) -> UserResponse:
    """
    Create new user account.

    Creates a new user account with provided information and returns
    the created user data. Validates input and handles duplicates.

    Args:
        user_data (UserCreateRequest): User creation data
        user_service (UserService): Service for user operations

    Returns:
        UserResponse: Created user information

    Raises:
        HTTPException: 400 if user data is invalid
        HTTPException: 409 if email already exists
        HTTPException: 500 if creation fails

    Example:
        ```bash
        curl -X POST "http://localhost:8000/users" \
             -H "Content-Type: application/json" \
             -d '{
               "username": "johndoe",
               "email": "john@example.com",
               "password": "securepass123"
             }'
        ```

        Response:
        ```json
        {
          "id": 1,
          "username": "johndoe",
          "email": "john@example.com",
          "is_active": true,
          "created_at": "2024-01-15T10:30:00Z"
        }
        ```
    """
````

## 🔧 Property Docstring

```python
@property
def is_active(self) -> bool:
    """
    Check if user account is active.

    Returns:
        bool: True if user can perform operations, False otherwise

    Example:
        >>> user = User(status=UserStatus.ACTIVE)
        >>> assert user.is_active is True
    """
```

## 📊 Enum Docstring

```python
class UserRole(str, Enum):
    """
    User role enumeration with hierarchical permissions.

    Defines user roles in the system with built-in permission hierarchy.
    Higher roles inherit permissions from lower roles.

    Attributes:
        USER: Basic user role with standard permissions
        MODERATOR: Moderation role with enhanced permissions
        ADMIN: Administrative role with full system access

    Example:
        >>> role = UserRole.ADMIN
        >>> assert role.has_permission(UserRole.USER)
        >>> assert role.value == "admin"
    """
```

## 🧪 Test Function Docstring

```python
async def test_user_creation_success():
    """
    Test successful user creation with valid data.

    Verifies that user creation works correctly with valid input data,
    returns proper user object, and stores data in database.
    """
```

## 🚨 Error Handling Examples

### Custom Exceptions

```python
class UserNotFoundError(Exception):
    """
    Raised when requested user cannot be found.

    Args:
        user_id (int): ID of the user that was not found
        message (str): Optional custom error message

    Example:
        >>> raise UserNotFoundError(user_id=123, message="User deleted")
    """
```

### Service Method with Multiple Exceptions

```python
async def update_user_role(self, user_id: int, new_role: UserRole) -> User:
    """
    Update user role with authorization checks.

    Args:
        user_id (int): ID of user to update
        new_role (UserRole): New role to assign

    Returns:
        User: Updated user object

    Raises:
        UserNotFoundError: If user doesn't exist
        PermissionError: If current user lacks permission
        ValidationError: If role is invalid
        DatabaseError: If update operation fails

    Example:
        >>> updated_user = await service.update_user_role(123, UserRole.MODERATOR)
        >>> assert updated_user.role == UserRole.MODERATOR
    """
```

## 🎯 Best Practices

### ✅ DO:

- Use present tense ("Creates user" not "Create user")
- Be concise but informative
- Include practical examples
- Document all parameters and return values
- Mention important side effects
- Use proper type hints
- Include curl examples for API endpoints

### ❌ DON'T:

- Mix languages (Russian/English)
- Use vague descriptions ("Does stuff")
- Forget to document exceptions
- Write overly long docstrings
- Include implementation details in public APIs
- Use abbreviations without explanation

## 📚 Sphinx Directives Reference

```python
"""
Brief description.

Detailed description with multiple paragraphs if needed.
Can include links to other functions or classes.

Args:
    param1 (type): Description of parameter
    param2 (type | None): Optional parameter description

Returns:
    return_type: Description of return value

Raises:
    ExceptionType: When this exception is raised
    AnotherException: Another exception condition

Yields:
    yield_type: For generator functions

Note:
    Additional notes about usage or behavior

Warning:
    Important warnings about usage

See Also:
    related_function: Related functionality
    :class:`ClassName`: Link to related class

Example:
    >>> # Code example showing usage
    >>> result = function_call()
    >>> assert result == expected_value
"""
```

## 🚀 API Endpoint Examples

For API endpoints, always include both curl and response examples:

````python
@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int) -> UserResponse:
    """
    Get user information by ID.

    Args:
        user_id (int): User identifier

    Returns:
        UserResponse: User profile information

    Example:
        ```bash
        curl -X GET "http://localhost:8000/users/123" \
             -H "Authorization: Bearer your_token_here"
        ```

        Response:
        ```json
        {
          "id": 123,
          "username": "johndoe",
          "email": "john@example.com",
          "profile": {
            "display_name": "John Doe",
            "bio": "Software Developer"
          }
        }
        ```
    """
````

## 🔄 Template Shortcuts

For VS Code users, add these snippets to your settings:

```json
{
  "sphinx-docstring": {
    "prefix": "docstring",
    "body": [
      "\"\"\"",
      "${1:Brief description}.",
      "",
      "${2:Detailed description}.",
      "",
      "Args:",
      "    ${3:param} (${4:type}): ${5:Description}",
      "",
      "Returns:",
      "    ${6:return_type}: ${7:Description}",
      "",
      "Example:",
      "    >>> ${8:example_code}",
      "    >>> assert ${9:assertion}",
      "\"\"\""
    ]
  }
}
```
