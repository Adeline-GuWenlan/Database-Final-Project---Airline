# Member Contributions Summary

This summary is based on Git history, commit messages, and project comments.

## Adeline

- Created the initial project import and baseline application structure.
- Hardened the booking flow by moving purchase checks toward database-backed validation and adding database integrity mechanisms.
- Merged the saved-flights and cancellation feature work into the main project history.
- Added airport-city consistency validation in the backend so selected airports must match selected cities.
- Expanded sample data with multiple airports per city, including New York, Los Angeles, London, Tokyo, and San Francisco examples.
- Added intelligent flight-search autofill behavior in the flight search template.
- Cleaned technical explanatory text from user-facing templates to make the UI more demo-ready.
- Created and maintained a broad project cheat sheet covering authentication, search, booking, customer features, agent features, staff features, database design, security, performance, SQL patterns, testing, and demo guidance.
- Added security and demo documentation, including authorization and CSRF/security notes.
- Aligned documentation with the merged booking flow after branch integration.

## LynnGan

- Implemented the saved-flights feature, including the `SavedFlight` table behavior, save buttons, saved-flight listing page, and remove-saved-flight route.
- Implemented customer booking cancellation and improved the customer portal so customers can manage future bookings.
- Refined cancellation cleanup so the route is customer-only, verifies ownership, runs in a transaction, deletes both `Purchases` and `Ticket`, rolls back on database errors, and frees seat capacity.
- Fixed the booking flow branch by replacing the fragile stored-procedure call with direct transaction-safe SQL after a local MariaDB `mysql.proc` metadata error.

## Shared / Integrated Work

- The final app combines public flight search/status lookup, customer booking and analytics, saved flights, cancellation, booking-agent sales and commission tools, staff operations, staff analytics, admin actions, and operator status updates.
- Both members contributed to making the project defensible through feature implementation, database integrity work, security improvements, demo documentation, and query/feature explanations.

