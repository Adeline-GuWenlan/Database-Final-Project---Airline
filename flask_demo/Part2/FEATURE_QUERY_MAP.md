# Feature Query Map

This document maps each major user-facing feature to the database queries or query patterns it uses.

## Public Users

| Feature | Main Tables | Query Pattern |
| --- | --- | --- |
| Search upcoming flights | `Flight`, `Airport`, `SeatClass`, `Ticket` | `SELECT` with joins on departure/arrival airports, future-time filtering, optional airport/city/date/airline predicates, and subqueries for sold tickets and seat capacity |
| Look up in-progress flight status | `Flight`, `Airport` | `SELECT` by `airline_name`, `flight_num`, and `status = 'in-progress'` |
| Register customer | `Customer` | `INSERT` new row after uniqueness check on email |
| Register booking agent | `BookingAgent` | `INSERT` new row after uniqueness check on email |
| Register airline staff | `AirlineStaff`, `StaffPermission` | Public self-registration is blocked; admin and staff demo accounts are provisioned by seed data |
| Sign in | `Customer` or `BookingAgent` or `AirlineStaff`, plus `AuthorizedBy` / `StaffPermission` | `SELECT` credentials by identity, then load authorization metadata for session variables |

## Customers

| Feature | Main Tables | Query Pattern |
| --- | --- | --- |
| View filtered bookings | `Purchases`, `Ticket`, `Flight`, `Airport` | `SELECT` joined purchase history filtered by customer email, date window, route, and trip scope (`upcoming`, `past`, or `all`) |
| Book a flight | `Flight`, `SeatClass`, `Ticket`, `Purchases` | Transaction calls stored procedure `purchase_ticket`, which validates flight/customer/inventory, inserts the ticket, and inserts the purchase |
| Default spending analytics | `Purchases`, `Ticket` | `SUM(price_charged)` over last 12 months plus grouped monthly totals for last 6 months |
| Custom spending analytics | `Purchases`, `Ticket` | `SUM(price_charged)` and month-by-month grouping over user-supplied date range |

## Booking Agents

| Feature | Main Tables | Query Pattern |
| --- | --- | --- |
| View sold tickets by customer | `Purchases`, `Ticket`, `Flight`, `Airport` | `SELECT` joined purchase history filtered by `booking_agent_email`, date range, and route |
| Restrict searchable flights to authorized airlines | `AuthorizedBy`, `Flight` | Authorized airline list loaded into session, then used as a server-side filter on flight search |
| Book on behalf of a customer | `AuthorizedBy`, `Customer`, `Flight`, `SeatClass`, `Ticket`, `Purchases` | Transaction calls stored procedure `purchase_ticket`, which verifies agent-airline authorization, validates customer email, locks inventory rows, and inserts ticket + purchase |
| 30-day commission analytics | `Purchases`, `Ticket` | `COUNT`, `SUM`, and `AVG` over recent agent-issued purchases using a fixed commission rate |
| Top customers by tickets | `Purchases`, `Customer` | `GROUP BY customer_email` and `COUNT(*)` over last 6 months |
| Top customers by commission | `Purchases`, `Ticket`, `Customer` | `GROUP BY customer_email` and `SUM(price_charged * 0.10)` over last year |

## Airline Staff

| Feature | Main Tables | Query Pattern |
| --- | --- | --- |
| View flights in next 30 days | `Flight`, `Airport`, `SeatClass`, `Ticket` | `SELECT` airline-owned flights in a 30-day window with route filters and load subqueries |
| View passenger list for a flight | `Purchases`, `Ticket`, `Flight`, `Customer` | `SELECT` all customers on a chosen airline-owned flight |
| View customer travel history on the airline | `Purchases`, `Ticket`, `Flight`, `Airport` | `SELECT` airline-owned flights filtered by customer email |
| Top booking agents this month / year | `Purchases`, `Ticket`, `Flight` | `GROUP BY booking_agent_email` with either month or year date predicates, sorted by tickets or commission |
| Most frequent customer | `Purchases`, `Ticket`, `Flight`, `Customer` | `GROUP BY customer_email` and `COUNT(*)` over last year |
| Tickets sold per month | `Purchases`, `Ticket`, `Flight` | Monthly grouped counts for the airline |
| Delay vs non-delay stats | `Flight` | `SUM(CASE WHEN status = 'delayed' THEN 1 ELSE 0 END)` plus complementary count |
| Top destinations | `Purchases`, `Ticket`, `Flight`, `Airport` | `GROUP BY arrival_airport` and ticket count over 3-month and 1-year windows |

## Admin Actions

| Feature | Main Tables | Query Pattern |
| --- | --- | --- |
| Add airport | `Airport` | Uniqueness check, then `INSERT` |
| Add airplane with seat classes | `Airplane`, `SeatClass` | Transaction with `INSERT` airplane, then one `INSERT` per offered seat class |
| Create flight | `Airplane`, `Flight` | Ownership validation on airplane, then `INSERT` flight |
| Associate booking agent with airline | `BookingAgent`, `AuthorizedBy` | Existence check and duplicate check, then `INSERT` authorization row |

## Operator Actions

| Feature | Main Tables | Query Pattern |
| --- | --- | --- |
| Update flight status | `Flight` | Airline ownership check, then `UPDATE Flight SET status = ... WHERE flight_num = ...` |

## Database-Side Integrity

| Mechanism | Tables | Purpose |
| --- | --- | --- |
| `idx_flight_departure_status`, `idx_flight_route_departure`, `idx_flight_airline_departure` | `Flight` | Speed up public search, staff windows, and status-aware filtering |
| `idx_ticket_flight_class` | `Ticket` | Speed up ticket-count lookups for seat inventory |
| `idx_purchases_customer_date`, `idx_purchases_agent_date` | `Purchases` | Speed up customer and agent dashboards plus analytics windows |
| `idx_authorized_by_airline` | `AuthorizedBy` | Speed up authorization checks for booking agents |
| `validate_flight_insert`, `validate_flight_update` | `Flight` | Reject invalid schedules and same-airport routes at the database level |
| `enforce_ticket_capacity` | `Ticket` | Reject wrong-airplane tickets and oversold seat-class inserts even if an application-side check is missed |
| `purchase_ticket` | `Flight`, `SeatClass`, `Customer`, `AuthorizedBy`, `Ticket`, `Purchases` | Centralize ticket purchase validation, pricing, authorization, and insert behavior in the database |
