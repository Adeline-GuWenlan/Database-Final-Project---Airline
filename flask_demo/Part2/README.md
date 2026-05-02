# Air Ticket Reservation System - Refined Part 3 App

This Flask + MySQL project refines the airline reservation prototype so it aligns much more closely with the Part 3 rubric and the optimization prompt.

## What Changed

- Unified authentication for `customer`, `booking_agent`, and `airline_staff`
- Session-backed role routing and protected requests
- Password hashing with PBKDF2-SHA256 instead of plain-text storage
- CSRF protection for state-changing forms and explicit session-cookie clearing on logout
- Structured public flight search and public in-progress flight status lookup
- Customer dashboard with filtered trips and spending analytics
- Booking-agent dashboard with authorization checks and commission analytics
- Airline-staff dashboard with operational views, lookups, analytics, admin actions, and operator status updates
- Database indexes, integrity triggers, and a `purchase_ticket` stored procedure for transactional booking

## Setup

1. Install dependencies:

```bash
pip install flask mysql-connector-python
```

2. Update database credentials in:

- `flask_demo/init_db.py`
- `flask_demo/Part2/app.py`

3. Initialize the database:

```bash
cd flask_demo/Part2
python init_db.py
```

4. Start the application:

```bash
cd flask_demo/Part2
python app.py
```

5. Open:

```text
http://127.0.0.1:5000
```

## Demo Credentials

- Customer: `alice@example.com` / `password123`
- Customer: `bob@example.com` / `password123`
- Booking agent: `agent1@travel.com` / `agentpass`
- Admin staff: `admin_skyjet` / `adminpass`
- Regular staff: `staff_skyjet` / `staffpass`

## Demo Coverage

- Register a customer or booking-agent account and log in
- Log out and verify protected dashboards redirect to login
- Show `staff_skyjet` cannot create airports because the account has only `operator`
- Show `admin_skyjet` can add airports, airplanes, flights, and agent authorizations
- Purchase tickets as a customer or as `agent1@travel.com`
- Search `SJ900` to show a sold-out flight and the ticket-limit check

See `SECURITY_AND_DEMO.md` for the SQL injection explanation, role-by-role security controls, stored procedure/trigger details, and a complete demo script.

## Key Files

- `app.py`: main Flask application
- `init_db.py`: convenience wrapper for the shared database initializer
- `create_tables.sql`: refined schema, indexes, and triggers
- `insert_data.sql`: sample data with hashed passwords
- `SECURITY_AND_DEMO.md`: security explanation and exact demo script
- `MANIFEST.md`: file inventory for the rubric
- `FEATURE_QUERY_MAP.md`: user-facing features mapped to SQL behavior
- `System_Optimization_Proposals.md`: narrative document based on the prompt
