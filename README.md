# Employee Management API

Advanced Employee Management API built with **FastAPI**, **JWT authentication**, **SQLAlchemy**, and **MySQL**.

## Project structure

```
employee_api/
├── app/
│   ├── main.py              # FastAPI app, startup, global error handlers
│   ├── config.py            # Settings loaded from .env
│   ├── database.py          # SQLAlchemy engine/session, get_db dependency
│   ├── models.py            # ORM models: User, Employee, EmployeeActivity
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── auth.py               # Password hashing, JWT, current-user & role dependencies
│   ├── crud.py               # Database query logic
│   └── routers/
│       ├── auth_routes.py       # /auth/register, /auth/login
│       └── employee_routes.py   # /employees CRUD, search, filter, pagination, transfer
├── sql/
│   └── employee_management.sql  # DB creation, tables, sample data, management queries
├── requirements.txt
├── .env.example
└── README.md
```

## 1. Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # then edit .env with your real MySQL credentials and a strong JWT secret
```

## 2. Database

Open MySQL Workbench and run `sql/employee_management.sql`. It will:

- Create the `employee_management` database
- Create `users`, `employees`, and `employee_activity` tables with keys/constraints
- Insert sample data
- Include the management queries from the assignment (salary updates, JOINs, aggregates, etc.)

Alternatively, `app/main.py` calls `Base.metadata.create_all()` on startup, which will create the tables automatically if they don't exist yet (it will not, however, load sample data — use the SQL file for that, or the `/auth/register` and employee endpoints).

## 3. Run the API

```bash
uvicorn app.main:app --reload
```

Then open **http://127.0.0.1:8000/docs** for the interactive Swagger UI.

## 4. Typical flow

1. `POST /auth/register` — create a user (`role`: `admin`, `manager`, or `employee`).
2. `POST /auth/login` — log in via Swagger's **Authorize** button (username + password), which returns and attaches a JWT automatically. Or call it directly and use the returned `access_token` as a `Bearer` token.
3. Use the `/employees` endpoints. Permissions:
   - **admin**: create, view, update, delete (deactivate)
   - **manager**: create, view, update
   - **employee**: view only
4. `GET /employees` supports `search`, `department`, `min_salary`, `max_salary`, `active_only`, `sort_by`, `sort_order`, `page`, and `limit`.
5. `PUT /employees/{id}/transfer` demonstrates a multi-step transaction: it updates the employee's department **and** writes an audit row to `employee_activity` in one commit, rolling back both if either fails.

## 5. Security notes

- Passwords are hashed with bcrypt and never returned in API responses.
- JWTs carry the user ID, username, role, and an expiration time; access is checked on every request via `get_current_user`.
- Role checks are enforced server-side via the `require_roles(...)` dependency — a client cannot elevate its own role by relying on client-side logic.
- Employee "deletion" is a soft delete (`is_active = False`); rows are never removed by the API.
