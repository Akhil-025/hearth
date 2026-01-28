"""
Hephaestus Domain (v0.2)

Code reasoning, debugging, design, and refactoring insights.

Triggered by keywords:
- "debug"
- "design"
- "refactor"
- "review"
- "code"

Characteristics:
- Pure deterministic reasoning (no LLM, no randomness)
- No memory writes
- No autonomy or planning
- No cross-domain calls
"""

from ..base_v2 import Domain


class HephaestusService(Domain):
    """Code reasoning and debugging domain.
    
    Provides:
    - Debug suggestions for common code issues
    - Design patterns and architectural guidance
    - Refactoring recommendations
    - Code review insights
    
    All responses are deterministic keyword-based reasoning
    with no external dependencies (no LLM, no memory).
    """

    # Pattern-based reasoning rules (deterministic)
    DEBUG_PATTERNS = {
        "null": "Null pointer or None type error detected. Check for uninitialized variables or missing null checks.",
        "index": "Array or list index out of bounds. Verify array length before accessing indices.",
        "key": "Dictionary/map key not found. Use .get() with default or check key existence first.",
        "type": "Type mismatch or conversion error. Check data types match expected values.",
        "import": "Module import failure. Verify package is installed and module path is correct.",
        "syntax": "Syntax error in code. Check parentheses, indentation, and valid Python syntax.",
        "timeout": "Timeout or performance issue. Consider caching, async operations, or algorithm optimization.",
        "memory": "Memory leak or excessive memory usage. Check for unreleased resources or circular references.",
        "concurrency": "Race condition or threading issue. Use locks/mutexes or async patterns.",
        "network": "Network error or connectivity issue. Check firewall, DNS, and connection timeouts.",
    }

    DESIGN_PATTERNS = {
        "api": "For API design: use RESTful conventions, versioning, consistent naming. Consider OpenAPI/Swagger documentation.",
        "database": "For database design: normalize schema, use indexes for frequently queried columns, plan for scaling.",
        "authentication": "For auth: use industry-standard protocols (OAuth, JWT), never store plain passwords, use HTTPS.",
        "cache": "For caching: use Redis/Memcached for distributed cache, implement TTL, consider cache invalidation strategy.",
        "messaging": "For messaging: use message queues (RabbitMQ, Kafka) for async communication, ensure idempotency.",
        "microservices": "For microservices: define clear boundaries, use API gateways, implement service discovery.",
        "testing": "For testing: use unit tests (Jest, pytest), integration tests, E2E tests. Aim for >80% coverage.",
        "monitoring": "For monitoring: log structured data, use distributed tracing, set up alerts for critical metrics.",
    }

    REFACTORING_PATTERNS = {
        "duplicate": "Extract duplicate code into shared function or utility. Use DRY principle.",
        "long": "Long function? Extract into smaller functions with single responsibility.",
        "nested": "Deeply nested conditionals? Use guard clauses or extracted methods.",
        "parameters": "Too many function parameters? Use data object or context object.",
        "comments": "Heavy comments? Refactor to self-documenting code with clear names.",
        "globals": "Global variables? Use dependency injection or context/environment.",
        "magic": "Magic numbers/strings? Extract into named constants with semantic meaning.",
        "dead": "Dead code? Remove unused variables, functions, and imports.",
    }

    REVIEW_PATTERNS = {
        "style": "Code style: follow PEP 8 for Python. Use linters (flake8, pylint) and formatters (black).",
        "complexity": "High complexity? Consider extracting methods, reducing nesting, simplifying logic.",
        "error": "Error handling? Check for proper exception handling, logging, and user feedback.",
        "security": "Security? Check for SQL injection, XSS, CSRF. Validate and sanitize inputs.",
        "performance": "Performance? Check for O(n²) loops, unnecessary allocations, missing indexes.",
        "maintainability": "Maintainability? Use clear names, extract magic values, add documentation.",
        "testing": "Testing? Check for proper test coverage, edge cases, mocking external dependencies.",
    }

    def handle(self, query: str) -> str:
        """Process code reasoning query.
        
        Args:
            query: User question about code, design, debugging, etc.
            
        Returns:
            str: Deterministic reasoning and suggestions
        """
        query_lower = query.lower()

        # Debug assistance
        if "debug" in query_lower or "error" in query_lower or "crash" in query_lower:
            return self._handle_debug(query)

        # Design guidance
        if "design" in query_lower or "architecture" in query_lower or "pattern" in query_lower:
            return self._handle_design(query)

        # Refactoring suggestions
        if "refactor" in query_lower or "improve" in query_lower or "clean" in query_lower:
            return self._handle_refactoring(query)

        # Code review
        if "review" in query_lower or "quality" in query_lower or "best" in query_lower:
            return self._handle_review(query)

        # Default: general code reasoning
        return self._default_response()

    def _handle_debug(self, query: str) -> str:
        """Provide debugging assistance."""
        query_lower = query.lower()

        # Find matching debug pattern
        for pattern, advice in self.DEBUG_PATTERNS.items():
            if pattern in query_lower:
                return f"Debug Guidance: {advice}"

        # Generic debug response
        return (
            "Debug Assistance: To debug effectively, gather more information:\n"
            "1. What's the exact error message or unexpected behavior?\n"
            "2. When does it occur (reproducible steps)?\n"
            "3. What changed recently?\n"
            "4. Add print/logging statements to trace execution flow."
        )

    def _handle_design(self, query: str) -> str:
        """Provide design and architecture guidance."""
        query_lower = query.lower()

        # Find matching design pattern
        for pattern, advice in self.DESIGN_PATTERNS.items():
            if pattern in query_lower:
                return f"Design Guidance: {advice}"

        # Generic design response
        return (
            "Design Principles:\n"
            "1. SOLID principles (Single Responsibility, Open/Closed, Liskov, Interface Segregation, Dependency Inversion)\n"
            "2. DRY (Don't Repeat Yourself)\n"
            "3. KISS (Keep It Simple, Stupid)\n"
            "4. YAGNI (You Aren't Gonna Need It)\n"
            "5. Modularity and clear separation of concerns"
        )

    def _handle_refactoring(self, query: str) -> str:
        """Provide refactoring recommendations."""
        query_lower = query.lower()

        # Find matching refactoring pattern
        for pattern, advice in self.REFACTORING_PATTERNS.items():
            if pattern in query_lower:
                return f"Refactoring Suggestion: {advice}"

        # Generic refactoring response
        return (
            "Refactoring Guidelines:\n"
            "1. Extract methods: break large functions into smaller, focused functions\n"
            "2. Extract classes: group related functionality\n"
            "3. Extract constants: replace magic numbers/strings with named constants\n"
            "4. Simplify conditionals: use early returns and guard clauses\n"
            "5. Remove dead code: delete unused variables and functions"
        )

    def _handle_review(self, query: str) -> str:
        """Provide code review insights."""
        query_lower = query.lower()

        # Find matching review pattern
        for pattern, advice in self.REVIEW_PATTERNS.items():
            if pattern in query_lower:
                return f"Code Review: {advice}"

        # Generic review response
        return (
            "Code Review Checklist:\n"
            "1. Readability: Is code clear and self-documenting?\n"
            "2. Functionality: Does it work correctly for all cases?\n"
            "3. Efficiency: Is it performant? Any obvious optimizations?\n"
            "4. Maintainability: Will future developers understand it?\n"
            "5. Testing: Are edge cases covered?\n"
            "6. Security: Are inputs validated? Any vulnerabilities?\n"
            "7. Style: Does it follow project conventions?"
        )

    def _default_response(self) -> str:
        """Fallback response for unmatched queries."""
        return (
            "Hephaestus Code Reasoning:\n"
            "I can help with:\n"
            "- Debugging: 'Debug: [error description]'\n"
            "- Design: 'Design: [component description]'\n"
            "- Refactoring: 'Refactor: [code pattern]'\n"
            "- Code Review: 'Review: [code snippet]'\n\n"
            "Ask for specific guidance on code issues, architecture patterns, "
            "refactoring suggestions, or code quality improvements."
        )
