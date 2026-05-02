# Security and Demo Guide

## Security Concern: SQL Injection

SQL injection happens when an application builds SQL by mixing trusted query text with untrusted user input. For example, if a login query directly concatenated an email field, an attacker could type SQL syntax into the form and change the meaning of the query.

This project mitigates SQL injection by using MySQL Connector parameter binding everywhere user input reaches SQL. Queries use `%s` placeholders and pass values separately, so emails, airport codes, flight numbers, dates, and role inputs are treated as data rather than executable SQL. Dynamic query fragments are limited to server-owned clauses such as fixed filter conditions and generated placeholder counts.

## Security Management by Role

- Customer: passwords are PBKDF2-SHA256 hashes, sessions store the authenticated customer email, purchase history is filtered by that session email, and ticket purchase uses a stored procedure that validates the customer before inserting a ticket.
- Booking agent: the session stores the authenticated agent email and authorized airlines. Searches are restricted to those airlines, and `purchase_ticket` re-checks `AuthorizedBy` before allowing agent sales.
- Regular staff: staff login loads airline and permissions from `StaffPermission`. A staff user with only `operator` permission cannot see admin forms, and admin POST attempts are rejected before any insert.
- Admin staff: admin-only endpoints can add airports, add airplanes, create flights, and authorize booking agents. Airplanes and flights are tied to the admin's airline on the server side.
- All POST forms: CSRF tokens are required for login, registration, booking, and staff actions, which prevents a third-party page from silently submitting state-changing requests through a logged-in browser.
- Sessions: cookies are `HttpOnly` and `SameSite=Lax`; logout clears the Flask session and deletes the session cookie.

## Stored Procedures and Triggers

- `purchase_ticket`: stored procedure used by the Flask `/book` route. It validates customer existence, flight status, departure time, booking-agent authorization, seat-class availability, and remaining capacity. It then creates both `Ticket` and `Purchases` rows in one transaction and returns the new ticket id and price.
- `validate_flight_insert` and `validate_flight_update`: reject same-airport routes and arrival times that are not later than departure times.
- `enforce_ticket_capacity`: rejects ticket inserts that use the wrong airplane for the flight, an unavailable seat class, or a seat class whose capacity has already been reached.

## Prepared Demo Accounts

Run `python init_db.py` from `flask_demo/Part2` before the demo.

- Customer 1: `alice@example.com` / `password123`
- Customer 2: `bob@example.com` / `password123`
- Booking agent: `agent1@travel.com` / `agentpass`
- Admin staff: `admin_skyjet` / `adminpass`
- Regular staff: `staff_skyjet` / `staffpass`

## Demo Script

1. Register a new account: open `/register`, create a customer or booking-agent account, and confirm it logs in automatically.
2. Log out: click `Logout`, then open `/customer`, `/agent`, or `/staff`; the app redirects to `/login` because the session role has been cleared.
3. Staff cannot create airport: log in as `staff_skyjet`; the admin actions section is locked. A POST to `/staff/airport` cannot insert anything; without CSRF it is rejected as `400`, and with a valid staff session token it reaches the permission check and is rejected as `403`.
4. Admin can create airport: log in as `admin_skyjet`, use `Add Airport`, for example `SZX` / `Shenzhen`.
5. Build a new plane: as `admin_skyjet`, add an airplane such as id `6` with economy and business capacities.
6. Create a new flight: as `admin_skyjet`, create a future SkyJet flight using the new airplane, different departure/arrival airports, and a future schedule.
7. Purchase as customer: log in as `alice@example.com` or `bob@example.com`, search future flights, and book an available seat.
8. Purchase as agent: log in as `agent1@travel.com`, choose a SkyJet flight, enter a customer email, and book on that customer's behalf.
9. Ticket-limit check: search flight `SJ900`. It uses airplane `5` with one economy seat, and that seat is already sold. The detail page shows it is sold out; any direct purchase attempt is rejected by the stored procedure and trigger-backed capacity checks.
