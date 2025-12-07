# Permissions-as-Data Hybrid Authorization Service

## Project Overview

This service is a high-performance, centralized authorization engine built on the **Permissions-as-Data** architecture. It provides clear, explainable access control decisions by evaluating policies stored externally in a database, eliminating hardcoded authorization logic within client applications.

The service implements a **Hybrid RBAC (Role-Based Access Control) and ABAC (Attribute-Based Access Control)** model.

| Feature | Key Requirement Met |
| :--- | :--- |
| **Performance** | Sub-10ms latency via **In-Memory Caching** (Mock Redis). |
| **Security** | **API Key Authentication** for management endpoints; **Implicit Deny** principle. |
| **Compliance** | **Audit Logging** with full **Explanation Trace** for every decision. |
| **Flexibility** | **Policy Versioning** and **Graph-based Role Inheritance**. |

-----

##  Tech Stack & Dependencies

  * **Language:** Python 3.11+
  * **Web Framework:** **FastAPI** (Chosen for performance and async capabilities).
  * **Database:** **SQLite** (Local development); **SQLAlchemy 2.0 ORM**.
  * **Validation:** **Pydantic** (For robust schema validation).
  * **Testing:** **Pytest** (For automated testing).

### Setup & Installation

1.  **Clone the Repository:**

    ```bash
    git clone https://github.com/the-ivii/Permissions-As-Data-OJT.git
    ```

2.  **Create & Activate Virtual Environment:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the Server:**

    ```bash
    uvicorn main:app --reload
    ```

    *(The service starts on [http://127.0.0.1:8000](https://www.google.com/search?q=http://127.0.0.1:8000))*

-----

## API Usage & Testing Instructions

The service exposes two types of APIs: **The Public Data Plane** (Authorization Checks) and **The Secured Management Plane** (Policy Changes).

###  Security Note (API Key)

All management endpoints require an **API Key** passed in the `Authorization` header.

  * **API Key:** `SUPER_SECRET_ADMIN_KEY_2404`
  * **Header Format:** `Authorization: Bearer SUPER_SECRET_ADMIN_KEY_2404`

### Phase 1: Setup (Using Swagger UI at `/docs`)

1.  **Create Roles:** (Requires API Key)

      * **Endpoint:** `POST /roles/`
      * **Goal:** Establish hierarchy.
      * **Payload Example:**
        ```json
        { "name": "employee" }
        { "name": "manager", "parent_names": ["employee"] }
        ```

2.  **Activate Policy:** (Requires API Key)

      * **Goal:** Make the first set of rules live.
      * **Process:**
        a. Create Policy (Payload defines rules for `manager` and `employee`).
        b. Send `POST /policies/{id}/activate` to make it active.

### Phase 2: Core Authorization (Public Data Plane)

These checks are **public** and demonstrate the core logic.

| Scenario | Endpoint | Required Logic |
| :--- | :--- | :--- |
| **RBAC Inheritance Check** | `POST /access` | User role `manager` inherits the right to `write` from `employee` (ALLOW). |
| **ABAC Condition Check** | `POST /access` | Check if user is `manager` **AND** resource `status` is `DRAFT` (ALLOW/DENY). |
| **Performance Check** | `POST /access/batch` | Send 10 simultaneous requests to test the **In-Memory Cache**. |

-----

##  Verification & Evaluation Readiness

### Running Automated Tests

To prove the entire system is robust and secure, run the full test suite in your terminal. This validates all CRUD, security, and complex evaluation logic.

```bash
# Must be run from the root directory
pytest test_main.py
```

  * **Expected Output:** All 7 tests should **PASS**, confirming:
      * Policy versioning and activation works.
      * Role cycle detection prevents database corruption.
      * The core engine correctly applies **Implicit Deny** and **First-Match-Wins**.
