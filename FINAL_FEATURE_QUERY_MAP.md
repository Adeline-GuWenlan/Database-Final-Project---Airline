# Final Feature Query Map

This document maps each user-facing feature to the main database queries or query patterns issued by the Flask application.

## Public Users

| Feature | Main Tables | Query Pattern |
| --- | --- | --- |
| Homepage featured flights | `Flight`, `Airport`, `SeatClass`, `Ticket` | Loads airports/airlines, then selects future `upcoming` or `delayed` flights with route joins and subqueries for capacity and sold tickets. |
| Search flights | `Flight`, `Airport`, `SeatClass`, `Ticket` | Builds a parameterized `SELECT` with optional departure/arrival airport, city, date, flight number, status, and airline filters. Airport-city consistency is validated when both are selected. |
| View flight details | `Flight`, `Airport`, `SeatClass`, `Ticket` | Selects one flight by `flight_num`, joins airport cities, then selects seat classes and counts booked tickets per class. |
| Check flight status | `Flight`, `Airport` | Selects by `airline_name`, `flight_num`, and `status = 'in-progress'`, with airport joins for route display. |
| Register customer | `Customer` | Checks duplicate email, then inserts customer row with hashed password. |
| Register booking agent | `BookingAgent` | Checks duplicate email, then inserts booking-agent row with hashed password. |
| Register airline staff | `AirlineStaff`, `StaffPermission`, `Airline` | Verifies selected airline, checks duplicate username, inserts staff row, then inserts selected staff permissions. |
| Sign in | `Customer`, `BookingAgent`, `AirlineStaff`, `AuthorizedBy`, `StaffPermission` | Selects credentials from the chosen role table, verifies password hash, then loads authorized airlines or staff permissions into session. |

## Customers

| Feature | Main Tables | Query Pattern |
| --- | --- | --- |
| View bookings | `Purchases`, `Ticket`, `Flight`, `Airport` | Selects joined purchases for `session["customer_email"]`, with optional upcoming/past scope, date range, and route filters. |
| Book flight | `Flight`, `SeatClass`, `Ticket`, `Purchases`, `AuthorizedBy`, `Customer` | Starts transaction, locks `Flight` with `FOR UPDATE`, validates status/time, locks `SeatClass`, counts sold tickets, inserts `Ticket`, inserts `Purchases`, then commits or rolls back. |
| Cancel booking | `Purchases`, `Ticket`, `Flight` | Starts transaction, selects owned booking with `FOR UPDATE`, blocks past flights, deletes matching `Purchases`, deletes related `Ticket`, commits or rolls back. |
| Spending analytics | `Purchases`, `Ticket` | Uses `SUM(price_charged)` and grouped monthly totals for default 12-month/6-month windows or a custom date range. |
| Save flight | `SavedFlight`, `Flight` | Verifies flight exists and has not departed, then inserts `(customer_email, flight_num)` into `SavedFlight`. |
| View saved flights | `SavedFlight`, `Flight`, `Airport` | Selects current customer's saved flights joined to flight and airport details, ordered by `saved_at DESC`. |
| Remove saved flight | `SavedFlight` | Deletes only the current customer's saved-flight row by `(customer_email, flight_num)`. |

## Booking Agents

| Feature | Main Tables | Query Pattern |
| --- | --- | --- |
| Search authorized flights | `AuthorizedBy`, `Flight`, `Airport`, `SeatClass`, `Ticket` | Authorized airline list is loaded into session and added as an `IN (...)` filter to public flight search. |
| Book for customer | `AuthorizedBy`, `Customer`, `Flight`, `SeatClass`, `Ticket`, `Purchases` | Uses the same transaction-safe booking flow as customer booking, plus authorization check for `booking_agent_email` and customer existence check. |
| View sold tickets | `Purchases`, `Ticket`, `Flight`, `Airport` | Selects purchases where `booking_agent_email` equals the logged-in agent, with optional date and route filters. |
| Commission summary | `Purchases`, `Ticket` | Counts tickets and calculates `SUM(price_charged * 0.10)` and `AVG(price_charged * 0.10)` for the last 30 days. |
| Top customers by tickets | `Purchases`, `Customer` | Groups by customer over the last 6 months and orders by ticket count. |
| Top customers by commission | `Purchases`, `Ticket`, `Customer` | Groups by customer over the last year and orders by commission total. |

## Airline Staff

| Feature | Main Tables | Query Pattern |
| --- | --- | --- |
| View next-30-day flights | `Flight`, `Airport`, `SeatClass`, `Ticket` | Selects flights for `session["airline_name"]` between `NOW()` and `DATE_ADD(NOW(), INTERVAL 30 DAY)`, with optional date and route filters. |
| View passenger list | `Purchases`, `Ticket`, `Flight`, `Customer` | Selects customers and ticket details for an airline-owned flight number. |
| View customer travel history | `Purchases`, `Ticket`, `Flight`, `Airport` | Selects all flights on the staff member's airline for a searched customer email. |
| Staff analytics: top agents | `Purchases`, `Ticket`, `Flight` | Groups by `booking_agent_email`, calculating ticket counts and commission totals for current month/current year windows. |
| Staff analytics: frequent customer | `Purchases`, `Ticket`, `Flight`, `Customer` | Groups by customer over the last year and returns the highest trip count. |
| Staff analytics: tickets per month | `Purchases`, `Ticket`, `Flight` | Groups purchases by `DATE_FORMAT(purchase_date, '%Y-%m')` for the last 6 months. |
| Staff analytics: delay stats | `Flight` | Uses `SUM(CASE WHEN status = 'delayed' THEN 1 ELSE 0 END)` and complementary count. |
| Staff analytics: top destinations | `Purchases`, `Ticket`, `Flight`, `Airport` | Groups by arrival airport/city for 3-month and 1-year windows. |

## Admin Staff Actions

| Feature | Main Tables | Query Pattern |
| --- | --- | --- |
| Add airport | `Airport` | Validates airport code/city, checks duplicate airport, then inserts row. |
| Add airplane with seat classes | `Airplane`, `SeatClass` | Starts transaction, checks duplicate airplane ID, inserts airplane, inserts one row per offered seat class, commits or rolls back. |
| Create flight | `Airplane`, `Flight` | Validates route/time/price/status, checks airplane ownership, checks duplicate flight number, then inserts flight. |
| Authorize booking agent | `BookingAgent`, `AuthorizedBy` | Checks agent exists, checks authorization does not already exist, then inserts row into `AuthorizedBy`. |

## Operator Staff Actions

| Feature | Main Tables | Query Pattern |
| --- | --- | --- |
| Update flight status | `Flight` | Validates status, confirms the flight belongs to the staff member's airline, then updates `Flight.status`. |

## Database Integrity Helpers

| Mechanism | Tables | Purpose |
| --- | --- | --- |
| Foreign keys and cascades | All relationship tables | Preserve valid references among airlines, airplanes, flights, tickets, purchases, saved flights, and users. |
| `validate_flight_insert` / `validate_flight_update` | `Flight` | Reject same-airport flights and arrival times that are not after departure times. |
| `enforce_ticket_capacity` | `Ticket`, `Flight`, `SeatClass` | Reject tickets for wrong airplanes, missing seat classes, or full seat classes. |
| Search and dashboard indexes | `Flight`, `Ticket`, `Purchases`, `AuthorizedBy` | Speed up flight search, capacity counting, dashboards, analytics, and authorization checks. |

