# Source Zip Manifest

Zip file: `airline_source_code.zip`

This manifest lists every file included in the source-code zip and briefly describes its purpose. Coding-agent prompt files, Git metadata, local caches, and course/reference-only files are excluded.

## Root Application Files

- `README.md`: Repository-level overview and setup notes for the airline reservation project.
- `flask_demo/flake.nix`: Nix development environment definition.
- `flask_demo/flake.lock`: Locked Nix dependency metadata.
- `flask_demo/init_db.py`: Shared MySQL/XAMPP database initializer used by the Part 2 app wrapper.

## Flask App Source

- `flask_demo/Part2/app.py`: Main Flask application with authentication, CSRF protection, role dashboards, flight search, booking, saved flights, cancellation, analytics, and staff actions.
- `flask_demo/Part2/init_db.py`: Local wrapper that calls the shared initializer in `flask_demo/init_db.py`.
- `flask_demo/Part2/create_tables.sql`: SQL schema, indexes, triggers, and stored procedure definition retained for database reference.
- `flask_demo/Part2/insert_data.sql`: SQL sample data for the airline reservation database.
- `flask_demo/Part2/select_queries_with_results.sql`: Representative SQL queries and expected-style results.

## Templates

- `flask_demo/Part2/templates/base.html`: Shared layout, navigation, CSRF-enabled forms, flash messages, and page styling.
- `flask_demo/Part2/templates/index.html`: Public homepage with featured flights and search entry points.
- `flask_demo/Part2/templates/login.html`: Unified login page for customers, booking agents, and airline staff.
- `flask_demo/Part2/templates/register.html`: Role-aware registration form.
- `flask_demo/Part2/templates/flights.html`: Public and role-aware flight search page.
- `flask_demo/Part2/templates/status.html`: Public in-progress flight status lookup page.
- `flask_demo/Part2/templates/flight_detail.html`: Flight details, seat-class inventory, save button, and booking form.
- `flask_demo/Part2/templates/booking_result.html`: Booking success/failure result page.
- `flask_demo/Part2/templates/customer_portal.html`: Customer dashboard for search, bookings, cancellation, and spending analytics.
- `flask_demo/Part2/templates/saved_flights.html`: Customer saved-flight list and removal controls.
- `flask_demo/Part2/templates/agent_portal.html`: Booking-agent dashboard for sales history and commission analytics.
- `flask_demo/Part2/templates/staff_portal.html`: Airline-staff dashboard for operations, analytics, admin actions, and operator status updates.
- `flask_demo/Part2/templates/error.html`: Shared error page for denied, missing, bad, or failed requests.

## App Documentation Included With Source

- `flask_demo/Part2/README.md`: Part 2 app setup and feature overview.
- `flask_demo/Part2/MANIFEST.md`: Existing app-level manifest.
- `flask_demo/Part2/FEATURE_QUERY_MAP.md`: Existing feature-to-query mapping.
- `flask_demo/Part2/SECURITY_AND_DEMO.md`: Security notes and demo guidance.
- `flask_demo/Part2/Cheatsheet.md`: Defense/demo cheat sheet.
- `flask_demo/Part2/System_Optimization_Proposals.md`: Optimization and design rationale document.
- `flask_demo/Part2/deviation_note.txt`: Schema/design deviation note.
- `flask_demo/Part2/Relational.drawio.pdf`: Relational schema diagram export.
- `flask_demo/Part2/relational schema diagram.pdf`: Relational schema diagram export.

