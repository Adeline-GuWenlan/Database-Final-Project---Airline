# Security and Demo Guide

## Security Concern: SQL Injection

SQL injection happens when an application builds SQL by mixing trusted query text with untrusted user input. For example, if a login query directly concatenated an email field, an attacker could type SQL syntax into the form and change the meaning of the query.

This project mitigates SQL injection by using MySQL Connector parameter binding everywhere user input reaches SQL. Queries use `%s` placeholders and pass values separately, so emails, airport codes, flight numbers, dates, and role inputs are treated as data rather than executable SQL. Dynamic query fragments are limited to server-owned clauses such as fixed filter conditions and generated placeholder counts. The remaining dynamic SQL helpers use allowlists for table/key names, analytics sort clauses, and date intervals; request values never choose SQL identifiers or raw SQL fragments.

## Security Management by Role

- Customer: passwords are PBKDF2-SHA256 hashes, sessions store the authenticated customer email, purchase history is filtered by that session email, and ticket purchase runs inside a transaction that validates the flight before inserting a ticket.
- Booking agent: the session stores the authenticated agent email and authorized airlines. Searches are restricted to those airlines, `/book` re-checks `AuthorizedBy` before allowing agent sales, and the agent dashboard/analytics join `AuthorizedBy` so the logged-in agent only sees currently authorized airline sales.
- Regular staff: staff login loads airline and permissions from `StaffPermission`. A staff user with only `operator` permission cannot see admin forms, and admin POST attempts are rejected before any insert.
- Admin staff: admin-only endpoints can add airports, add airplanes, create flights, and authorize booking agents. Airplanes and flights are tied to the admin's airline on the server side.
- All POST forms: CSRF tokens are required for login, registration, booking, and staff actions, which prevents a third-party page from silently submitting state-changing requests through a logged-in browser.
- Sessions: cookies are `HttpOnly` and `SameSite=Lax`; login stores the role plus role-specific identity fields in the signed Flask session; protected decorators reject missing, wrong-role, or incomplete session data; logout clears the session and deletes the session cookie.

## Sessions and Browser Cache

Sessions and cache solve different problems. A session is authentication state: it tells the server who the current browser is logged in as and which role/permissions that request has. Browser cache is local page storage: it can keep a copy of a rendered page for faster back/forward navigation, but it must not be trusted for authorization.

The app uses sessions for access control and uses cache headers only to prevent private pages from being reused after logout or expiry. Authenticated and protected responses include `Cache-Control: no-store, no-cache, must-revalidate, max-age=0`, `Pragma: no-cache`, and `Expires: 0`. That means the browser should ask the server again instead of showing an old customer, agent, or staff page from cache.

## Current Security/UI State Helpers

- CSRF tokens: `csrf_token()` stores a random token in the session; every POST form sends it in `_csrf_token`; `@app.before_request` checks it with `hmac.compare_digest`.
- Session guards: `@login_required`, `@roles_required`, and `@permission_required` read the signed Flask session on every protected request, then check role, identity fields, and staff permissions.
- Two-hour session expiry: `login_user()` marks the session permanent and stores `_session_created_at`; `PERMANENT_SESSION_LIFETIME` is two hours; `SESSION_REFRESH_EACH_REQUEST=False` prevents silent sliding renewal; `expire_authenticated_sessions()` clears old sessions before protected views run.
- Private-page cache control: `@app.after_request` adds no-store headers to authenticated and protected responses.
- Sticky forms: route handlers pass `filters` or `form_data` back into Jinja templates, and templates render `value=...`, `selected`, and `checked` from those objects so user choices remain visible after search or validation errors.
- Jinja escaping: templates use normal `{{ value }}` output, so Jinja auto-escapes displayed user/database values in HTML contexts.
- Cookie hardening: Flask session cookies are `HttpOnly` and `SameSite=Lax`, limiting JavaScript access and reducing cross-site form abuse.

## Stored Procedures and Triggers

- `/book` transaction: validates customer existence for agent sales, flight status, departure time, booking-agent authorization, seat-class availability, and remaining capacity. It then creates both `Ticket` and `Purchases` rows in one transaction.
- `purchase_ticket`: retained in the schema as the equivalent database-side booking procedure for reference/demo discussion.
- `validate_flight_insert` and `validate_flight_update`: reject same-airport routes and arrival times that are not later than departure times.
- `enforce_ticket_capacity`: rejects ticket inserts that use the wrong airplane for the flight, an unavailable seat class, or a seat class whose capacity has already been reached.
- `enforce_agent_purchase_authorization_insert` and `enforce_agent_purchase_authorization_update`: reject direct `Purchases` inserts/updates where a booking agent is attached to a flight from an unauthorized airline.

## Prepared Demo Accounts

Run `python init_db.py` from `flask_demo/Part2` before the demo.

- Customer 1: `alice@example.com` / `password123`
- Customer 2: `bob@example.com` / `password123`
- Customer 3: `charlie@example.com` / `password123`
- Booking agent 1: `agent1@travel.com` / `agentpass`
- Booking agent 2: `agent2@travel.com` / `agentpass`
- Admin staff: `SkyJet_admin` / `adminpass`
- Admin staff: `AirAsia_admin` / `adminpass`
- Admin staff: `Delta_admin` / `adminpass`
- Regular staff: `SkyJet_staff` / `staffpass`

## Demo Script

1. Register a new account: open `/register`, create a customer or booking-agent account, and confirm it logs in automatically.
2. Log out: click `Logout`, then open `/customer`, `/agent`, or `/staff`; the app redirects to `/login` because the session role has been cleared.
3. Staff cannot create airport: log in as `SkyJet_staff`; the admin actions section is locked. A POST to `/staff/airport` cannot insert anything; without CSRF it is rejected as `400`, and with a valid staff session token it reaches the permission check and is rejected as `403`.
4. Admin can create airport: log in as `SkyJet_admin`, use `Add Airport`, for example `SZX` / `Shenzhen`.
5. Build a new plane: as `SkyJet_admin`, add an airplane such as id `6` with economy and business capacities.
6. Create a new flight: as `SkyJet_admin`, create a future SkyJet flight using the new airplane, different departure/arrival airports, and a future schedule.
7. Purchase as customer: log in as `alice@example.com` or `bob@example.com`, search future flights, and book an available seat.
8. Purchase as agent: log in as `agent1@travel.com`, choose a SkyJet flight, enter a customer email, and book on that customer's behalf.
9. Ticket-limit check: search flight `SJ900`. It uses airplane `5` with one economy seat, and that seat is already sold. The detail page shows it is sold out; any direct purchase attempt is rejected by transaction checks and trigger-backed capacity checks.
