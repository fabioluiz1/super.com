# mypy: Static Type Checking for Python

## Type Annotations in Python

Python is dynamically typed — variables can hold any type, and type errors only surface at runtime. However, Python 3.5 (2015) introduced **type annotations** ([PEP 484](https://peps.python.org/pep-0484/)) as a language feature:

```python
# Without type annotations
def get_user(email):
    ...

# With type annotations (Python 3.5+)
def get_user(email: str) -> User:
    ...
```

Type annotations are just syntax — Python ignores them at runtime. They're metadata for tools and humans. The interpreter doesn't enforce them; you can still pass an `int` where `str` is annotated.

## Why Use mypy?

mypy is a **static type checker** — it reads your type annotations and analyzes your code *without running it*. It catches type mismatches at commit time instead of at runtime. Think of it as a spell-checker for types.

Without a tool like mypy, type annotations are just documentation. With mypy, they become enforced contracts.

### Without mypy (bug discovered in production)

```python
class User:
    def __init__(self, email: str):
        self.email = email

def get_user_email(user):  # No type annotation
    return user.email

# This is how the function was intended to be used
user = User("alice@example.com")
email = get_user_email(user)  # Works correctly

# Months later, someone passes a dict instead of a User object
email = get_user_email({"email": "test@example.com"})  # Works by accident!
email = get_user_email({"mail": "test@example.com"})   # AttributeError at runtime
```

### With mypy (bug caught at commit time)

```python
class User:
    def __init__(self, email: str):
        self.email = email

def get_user_email(user: User) -> str:  # Type annotation requires User
    return user.email

# Intended usage still works
user = User("alice@example.com")
email = get_user_email(user)  # OK

# But the bug is now caught at commit time, not in production
email = get_user_email({"email": "test@example.com"})
# mypy error: Argument 1 has incompatible type "dict[str, str]"; expected "User"
```

The bug is caught before the code ever runs.

---

## Why `strict = true`?

mypy has many optional checks that are off by default. `strict = true` enables all of them at once. Without strict mode, mypy only checks *some* of your code — untyped functions are silently skipped, giving you false confidence.

**The problem with gradual typing:** Teams that start with loose settings rarely tighten them later. One untyped function returns `Any`, which propagates to everything that calls it, and suddenly half your codebase isn't actually type-checked.

Starting with `strict = true` means every function is properly typed from day one.

---

## What `strict = true` Enables

### `disallow_untyped_defs`

Every function must have type annotations for all parameters and the return type.

```python
# BAD — mypy skips this function entirely, no type checking happens
def calculate_total(items, tax_rate):
    return sum(item.price for item in items) * (1 + tax_rate)

# GOOD — mypy checks the implementation matches the signature
def calculate_total(items: list[Item], tax_rate: float) -> float:
    return sum(item.price for item in items) * (1 + tax_rate)
```

**Why it matters:** Without annotations, mypy can't check callers are passing the right types. The function becomes a black hole where type information disappears.

---

### `disallow_incomplete_defs`

Can't mix typed and untyped parameters in the same function.

```python
# BAD — tax_rate has no type, so mypy can't fully check this function
def calculate_total(items: list[Item], tax_rate) -> float:
    return sum(item.price for item in items) * (1 + tax_rate)

# GOOD — all parameters are typed
def calculate_total(items: list[Item], tax_rate: float) -> float:
    return sum(item.price for item in items) * (1 + tax_rate)
```

**Why it matters:** Partial annotations are worse than no annotations — they give the illusion of safety while leaving gaps. If you're going to type a function, type it completely.

---

### `disallow_untyped_calls`

Can't call untyped functions from typed code.

```python
# Somewhere in your codebase, an untyped function exists
def fetch_data(url):  # No types — returns Any
    return requests.get(url).json()

# BAD — calling untyped function from typed code
def get_user(user_id: int) -> User:
    data = fetch_data(f"/users/{user_id}")  # data is Any, defeating type safety
    return User(**data)

# GOOD — the called function is also typed
def fetch_data(url: str) -> dict[str, Any]:
    return requests.get(url).json()

def get_user(user_id: int) -> User:
    data = fetch_data(f"/users/{user_id}")  # data is dict[str, Any]
    return User(**data)
```

**Why it matters:** One untyped function can "infect" your entire codebase with `Any` types. This rule forces you to type your dependencies or explicitly acknowledge when you're opting out.

---

### `disallow_any_generics`

Must specify type parameters for generic types like `list`, `dict`, `set`.

```python
# BAD — list of what? mypy doesn't know, so it can't check element access
def get_emails(users: list) -> list:
    return [user.email for user in users]

# GOOD — mypy knows users contains User objects
def get_emails(users: list[User]) -> list[str]:
    return [user.email for user in users]
```

**Why it matters:** `list` without a type parameter is essentially `list[Any]`. mypy can't catch bugs like `users[0].nonexistent_method()` because it doesn't know what's in the list.

---

### `warn_return_any`

Flags when a function returns `Any` but claims to return a specific type.

```python
import json
from typing import cast

# BAD — json.loads returns Any, but we claim to return dict[str, str]
def parse_config(raw: str) -> dict[str, str]:
    return json.loads(raw)  # mypy warning: returning Any from function declared to return dict[str, str]

# GOOD (validation) — runtime check that raises if the type is wrong
def parse_config(raw: str) -> dict[str, str]:
    data = json.loads(raw)
    assert isinstance(data, dict)  # raises AssertionError if not a dict
    return data

# GOOD (casting) — tell mypy "trust me, I know the type"
def parse_config(raw: str) -> dict[str, str]:
    return cast(dict[str, str], json.loads(raw))  # no runtime check, just a mypy hint

# GOOD (Pydantic) — proper validation with clear error messages
from pydantic import TypeAdapter

config_adapter = TypeAdapter(dict[str, str])

def parse_config(raw: str) -> dict[str, str]:
    return config_adapter.validate_json(raw)  # raises ValidationError with details
```

**When to use each:**
- `assert` — quick checks in code you control, disabled with `python -O`
- `cast()` — when you're certain about the type (e.g., from a trusted API) and want zero runtime cost
- Pydantic — when parsing external input (user data, API responses) and you need clear error messages

**Why it matters:** When `Any` silently becomes a specific type, mypy loses track. Later code assumes it's a `dict[str, str]` but it might actually be a `list` or `None`. This rule makes you acknowledge when you're crossing from untyped to typed code.

---

### `no_implicit_optional`

A parameter with a `None` default must explicitly include `None` in its type.

```python
# BAD — type says str, but default is None. Which is it?
def greet(name: str = None) -> str:
    if name is None:
        return "Hello, stranger!"
    return f"Hello, {name}!"

# GOOD — type explicitly says str OR None
def greet(name: str | None = None) -> str:
    if name is None:
        return "Hello, stranger!"
    return f"Hello, {name}!"
```

**Why it matters:** The BAD example lies — the type says `str` but it can actually be `None`. If someone reads the signature and assumes `name` is always a string, they'll write code that crashes on `None`. Explicit `str | None` makes the optionality visible.

---

## Summary

| Check | What it prevents |
|-------|------------------|
| `disallow_untyped_defs` | Functions that mypy silently skips |
| `disallow_incomplete_defs` | Half-typed functions that give false confidence |
| `disallow_untyped_calls` | `Any` types leaking in from untyped code |
| `disallow_any_generics` | `list` and `dict` without element types |
| `warn_return_any` | `Any` silently becoming a specific type |
| `no_implicit_optional` | Types that lie about accepting `None` |

**Bottom line:** `strict = true` means when mypy passes, your types are actually checked. Without it, mypy might report "no errors" while large parts of your codebase aren't being analyzed at all.
