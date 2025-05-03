## TwinCore Prototype Testing Strategy

**Version:** 1.0
**Date:** May 23, 2024

**1. Introduction**

This document outlines the testing strategy for the **TwinCore Backend Prototype**, the service responsible for managing digital twin memory, ingestion, and retrieval using FastAPI, Qdrant, and Neo4j. The primary goal is to ensure the backend service is robust, reliable, and adheres to its defined API contract, providing confidence for integration with the Canvas/Orchestration layer (Dev A). This strategy adopts a Test-Driven Development (TDD) approach.

**2. Goals**

*   Ensure functional correctness of all API endpoints and internal logic.
*   Validate data persistence and relationships across Qdrant and Neo4j.
*   Verify the accuracy of retrieval logic based on various scoping parameters (user, session, project, privacy).
*   Guarantee adherence to the defined OpenAPI/API contract for seamless integration.
*   Enable rapid, confident iteration by catching regressions early.
*   Build a maintainable and understandable test suite.

**3. Testing Philosophy**

*   **Test-Driven Development (TDD):** Tests will be written *before* the implementation code for features or bug fixes (Red-Green-Refactor cycle). This drives design and ensures testability.
*   **Testing Pyramid:** We will strive for a balanced test suite, emphasizing faster, more isolated unit tests at the base, followed by integration tests, and fewer, broader API/contract tests at the top.
*   **Test at the Right Level:** Avoid testing external library functionality (assume `qdrant-client` works). Focus tests on *our* code – how we use libraries, our business logic, and the integration points between components and databases.
*   **Isolation:** Unit tests should run without external dependencies (databases, network). Integration tests will require managed test environments (e.g., test databases).

**4. Testing Layers & Scope**

This strategy focuses on the **TwinCore Backend (FastAPI Service)**. Testing the Streamlit UI is out of scope for this document. We adapt the provided testing layers:

| Layer                 | Scope within TwinCore           | Frameworks / Tools                                      | What it Checks                                                                                                 | TDD Focus Priority |
| :-------------------- | :------------------------------ | :------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------- | :----------------- |
| **Unit**              | Services, DAL utils, Core utils | `pytest`, `pytest-mock`, `Hypothesis`                   | Pure function behavior, class logic in isolation (dependencies mocked), property testing for complex algorithms. | High               |
| **Integration (DAL)** | DAL Modules (`dal/`)            | `pytest`, `pytest-asyncio`                              | Correct interaction with *real* (test instance) Qdrant & Neo4j. Schema adherence, query correctness, data CRUD. | High               |
| **Integration (Service)** | Service Modules (`services/`) | `pytest`, `pytest-asyncio`, `pytest-mock`               | Service logic orchestrating calls to mocked DALs. Verifies the flow of control and data transformation.          | Medium             |
| **API / Contract**    | API Routers (`api/`)            | `pytest`, `pytest-asyncio`, `HTTPX`, `Schemathesis`     | API request/response validation (schema), status codes, basic auth (if any), endpoint routing.                   | High               |
| **End-to-End (Backend)** | Full Request Flow             | `pytest`, `pytest-asyncio`, `HTTPX`                     | Simulates API calls -> Service -> DAL -> *Real* Test DBs. Verifies data persistence & retrieval across layers. | Medium             |

**Scope for Prototype:**

*   **In Scope:** Unit, DAL Integration, Service Integration, and API/Contract tests covering the core features: seeding, message/document ingestion, context retrieval (group/private), preference query.
*   **Out of Scope (for Prototype):** Streamlit UI testing, performance/load testing, security penetration testing, testing external ingestion connectors (GDrive, GCal - as these aren't built yet), complex `Hypothesis` strategies (start simple).

**5. Test-Driven Development Workflow**

For each new feature, endpoint, or significant logic change:

1.  **Red:** Write a failing test first.
    *   For a new API endpoint: Start with an API/Contract test (`HTTPX`) checking the expected success response (e.g., 200 OK) and response schema. It will fail (404).
    *   For new service logic: Write a Service Integration test, mocking the DAL, defining expected DAL calls and return values. It will fail (method not found or assertion error).
    *   For complex DAL query: Write a DAL Integration test against the test database. It will fail (data not found or incorrect query).
    *   For pure logic/utility: Write a Unit test. It will fail.
2.  **Green:** Write the minimum amount of application code required to make the failing test pass.
    *   Implement the basic API route structure.
    *   Implement the service method, initially calling placeholder DAL methods.
    *   Implement the DAL method.
    *   Implement the utility function.
3.  **Refactor:** Improve the implementation code (clarity, efficiency, structure) *while ensuring all related tests still pass*. Add more tests (unit tests for edge cases, more integration tests) as needed during refactoring.
4.  **Repeat:** Move to the next test case or layer (e.g., after API test passes, write service/DAL integration tests).

**6. Tools & Frameworks**

*   **Test Runner:** `pytest` (for discovery, fixtures, assertions)
*   **Asynchronous Testing:** `pytest-asyncio` (for testing FastAPI/async code)
*   **HTTP Client (API Tests):** `HTTPX` (modern async HTTP client)
*   **API Schema Testing:** `Schemathesis` (generates test cases from OpenAPI spec)
*   **Mocking:** `pytest-mock` (or standard `unittest.mock`)
*   **Property-Based Testing:** `Hypothesis` (for generating diverse test inputs for unit tests)
*   **Test Environment:** Docker / Docker Compose (to run isolated Qdrant & Neo4j instances for integration/E2E tests)
*   **Code Coverage:** `pytest-cov` (to measure test coverage)

**7. Test Environment & Data**

*   **Databases:** Integration and Backend E2E tests will run against dedicated Qdrant and Neo4j instances, ideally spun up and torn down for the test suite run (e.g., using Docker Compose managed by `pytest` fixtures).
*   **Test Data:** Use `pytest` fixtures to seed necessary data into the test databases before specific tests run. Leverage the `twin_core_mock_data.py` structure for defining test data scenarios. Ensure data cleanup between tests or test modules where necessary.
*   **Configuration:** Test configurations (DB connection strings for test instances) should be separate from development/production configurations (e.g., via `.env.test` files or environment variables).

**8. Metrics**

*   **Test Coverage:** Aim for >85% line coverage as a starting point, measured by `pytest-cov`. Focus coverage on logic in services and DALs.
*   **Passing Tests:** Maintain a 100% pass rate on the main development branch. Failed tests in CI should block merges.

**9. Future Considerations**

*   **Performance Testing:** Introduce load testing (e.g., using `locust`) once core functionality is stable.
*   **External Ingestion Tests:** Develop strategies for testing GDrive/GCal connectors (likely involving mocking the external APIs).
*   **Security Testing:** Incorporate security-focused tests (dependency scanning, basic vulnerability checks).
*   **More Sophisticated Hypothesis:** Apply property-based testing more broadly as complex logic evolves.