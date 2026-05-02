# Manifest

## Application Files

- `app.py`: Main Flask application with role-aware authentication, session handling, booking logic, dashboards, and staff actions.
- `init_db.py`: Local wrapper that calls the shared database initializer from `flask_demo/init_db.py`.
- `templates/base.html`: Shared layout, navigation, alerts, and styling used by all active pages.
- `templates/index.html`: Public landing page with system overview and featured flights.
- `templates/login.html`: Unified login page for customers, booking agents, and airline staff.
- `templates/register.html`: Customer and booking-agent registration page with role-specific validations.
- `templates/flights.html`: Structured public flight search page.
- `templates/status.html`: Public flight-status lookup for in-progress flights.
- `templates/flight_detail.html`: Flight detail page with seat-class-aware booking form.
- `templates/booking_result.html`: Booking confirmation or rollback result page.
- `templates/customer_portal.html`: Customer dashboard for bookings and spending analytics.
- `templates/agent_portal.html`: Booking-agent dashboard for sold tickets and commission analytics.
- `templates/staff_portal.html`: Airline-staff dashboard with operations, analytics, and admin/operator actions.
- `templates/error.html`: Shared error page for 403, 404, and 500 responses.

## Database Files

- `create_tables.sql`: Refined schema definitions, indexes, integrity triggers, and the `purchase_ticket` stored procedure.
- `insert_data.sql`: Sample data with hashed passwords, future-facing test records, and required demo accounts.
- `../init_db.py`: Shared MySQL initializer that creates the schema and inserts sample data programmatically.
- `select_queries_with_results.sql`: Representative SQL queries used by the refined app.

## Documentation Files

- `README.md`: Setup guide and high-level overview of the refined Part 3 application.
- `SECURITY_AND_DEMO.md`: SQL-injection/security explanation, role-by-role controls, stored procedure/trigger notes, credentials, and demo script.
- `FEATURE_QUERY_MAP.md`: Mapping from user-facing functionality to the database queries it issues.
- `System_Optimization_Proposals.md`: Narrative document responding to the optimization prompt and tying changes back to the rubric.
- `deviation_note.txt`: Existing note file retained from prior work.
