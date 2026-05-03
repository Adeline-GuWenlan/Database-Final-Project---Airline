# Airline Reservation System - Technical Cheatsheet

This document explains the interface → Flask → Database flow for each feature in the application.

---

## Table of Contents
1. [Authentication & Authorization](#authentication--authorization)
2. [Public Flight Search](#public-flight-search)
3. [Flight Status Lookup](#flight-status-lookup)
4. [Ticket Booking](#ticket-booking)
5. [Customer Features](#customer-features)
6. [Booking Agent Features](#booking-agent-features)
7. [Staff Features](#staff-features)
8. [Database Design Highlights](#database-design-highlights)

---

## Authentication & Authorization

### Login (Customer/Agent/Staff)
**Interface**: `/login` - Role selection, identifier input, password input

**Flask Processing** (`app.py:783-876`):
- Role determines which table to query (Customer, BookingAgent, or AirlineStaff)
- Email validation for customers/agents, username validation for staff
- Password verification using `verify_password()` with PBKDF2-SHA256 hashing

**Database Queries**:
```sql
-- Customer login
SELECT email, name, password FROM Customer WHERE email = %s

-- Booking Agent login
SELECT email, password FROM BookingAgent WHERE email = %s

-- Staff login
SELECT username, first_name, last_name, airline_name, password
FROM AirlineStaff WHERE username = %s

-- Load staff permissions
SELECT permission FROM StaffPermission WHERE username = %s
```

**Security Features**:
- PBKDF2-SHA256 password hashing (260,000 iterations)
- Automatic password upgrade from plaintext to hash on successful login
- CSRF protection on all POST requests
- HTTP-only session cookies with 2-hour expiration

---

## Public Flight Search

### Search Flights by Route, Date, Airline
**Interface**: `/flights` - Multiple filter fields (airports, cities, date, airline, flight number, status)

**Flask Processing** (`app.py:994-1075`):
- Input validation and normalization (airport codes to uppercase)
- **Airport-city consistency validation** - verifies selected airport actually exists in selected city
- Filters passed to `get_public_flights()` query builder

**Database Query** (`app.py:441-479`):
```sql
SELECT
    f.flight_num, f.airline_name, f.departure_airport, dep.city AS departure_city,
    f.arrival_airport, arr.city AS arrival_city, f.departure_time, f.arrival_time,
    f.price, f.status,
    COALESCE((SELECT SUM(sc.capacity) FROM SeatClass sc WHERE sc.airplane_id = f.airplane_id), 0) AS total_capacity,
    COALESCE((SELECT COUNT(*) FROM Ticket t WHERE t.flight_num = f.flight_num), 0) AS booked_tickets
FROM Flight f
JOIN Airport dep ON dep.name = f.departure_airport
JOIN Airport arr ON arr.name = f.arrival_airport
WHERE f.departure_time >= NOW()
  AND f.status IN ('upcoming', 'delayed')
  [+ dynamic filters for airports, cities, dates, flight number, airline]
ORDER BY f.departure_time, f.flight_num
```

**Frontend Features**:
- Auto-fill: Selecting airport auto-fills corresponding city
- Auto-fill: Selecting city with single airport auto-fills that airport
- Validation: Prevents selecting mismatched airport-city combinations

---

## Flight Status Lookup

### Check Real-Time Flight Status
**Interface**: `/flights` with `status=in-progress` filter

**Flask Processing**: Same as flight search, but with status filter

**Database Query**:
```sql
-- Same as flight search, but:
WHERE f.status = 'in-progress'
  AND f.flight_num = %s  -- specific flight
  AND f.airline_name = %s  -- specific airline
```

**Use Case**: Public can look up any in-progress flight by airline + flight number without login

---

## Ticket Booking

### Purchase Ticket (Customer or Agent for Customer)
**Interface**: `/book` - Flight number, seat class, customer email (if agent)

**Flask Processing** (`app.py:1283-1405`):
- Validates flight number and seat class
- Determines customer email (session for customer, form input for agent)
- Opens a transaction and locks the target flight and seat class rows with `FOR UPDATE`
- Re-checks flight status, departure time, agent authorization, customer existence for agent sales, seat capacity, and price
- Inserts `Ticket` and `Purchases` rows using parameterized queries

**Main Booking Query Pattern**:
```sql
SELECT flight_num, airline_name, airplane_id, price, status, departure_time
FROM Flight
WHERE flight_num = %s
FOR UPDATE;

SELECT capacity
FROM SeatClass
WHERE airplane_id = %s AND seat_class = %s
FOR UPDATE;

INSERT INTO Ticket (flight_num, seat_class, airplane_id, price_charged)
VALUES (%s, %s, %s, %s);

INSERT INTO Purchases (ticket_id, customer_email, booking_agent_email, purchase_date)
VALUES (%s, %s, %s, %s);
```

**Booking Logic**:
1. **Validates customer exists** in Customer table
2. **Validates flight exists** and is bookable (status = 'upcoming'/'delayed', departure > NOW())
3. **Validates booking agent authorization** (if agent booking) via AuthorizedBy table
4. **Validates seat class** exists for airplane via SeatClass table
5. **Checks capacity** - counts existing tickets vs. seat capacity
6. **Calculates price** based on base price × seat class multiplier (economy 1.0x, business 1.5x, first 2.5x)
7. **Creates ticket** with auto-increment ticket_id
8. **Creates purchase record** linking ticket to customer (and optionally agent)
9. **Returns ticket_id and price_charged**

**Trigger Enforcement** (`enforce_ticket_capacity` trigger):
- Double-checks airplane_id matches flight
- Verifies seat class is configured for airplane
- Enforces capacity limits (prevents overbooking)

**Trigger Enforcement** (`enforce_agent_purchase_authorization_insert` trigger):
- Double-checks direct `Purchases` inserts for booking-agent authorization

---

## Customer Features

### View My Bookings
**Interface**: `/customer` - Filters by scope (upcoming/past/all), date range, airports

**Database Query** (`app.py:1244-1288`):
```sql
SELECT
    t.ticket_id, t.seat_class, t.price_charged, p.purchase_date,
    f.flight_num, f.airline_name, f.departure_airport, dep.city AS departure_city,
    f.arrival_airport, arr.city AS arrival_city, f.departure_time, f.arrival_time, f.status
FROM Purchases p
JOIN Ticket t ON t.ticket_id = p.ticket_id
JOIN Flight f ON f.flight_num = t.flight_num
JOIN Airport dep ON dep.name = f.departure_airport
JOIN Airport arr ON arr.name = f.arrival_airport
WHERE p.customer_email = %s
  AND [scope filters: f.departure_time >= NOW() for upcoming]
  [+ optional date range and airport filters]
ORDER BY f.departure_time, t.ticket_id
```

### Spending Analytics
**Interface**: `/customer` - Custom date range or default (last 12 months)

**Database Queries** (`app.py:471-540`):
```sql
-- Total spending
SELECT COALESCE(SUM(t.price_charged), 0) AS total
FROM Purchases p
JOIN Ticket t ON t.ticket_id = p.ticket_id
WHERE p.customer_email = %s
  AND p.purchase_date >= [start_date]
  AND p.purchase_date <= [end_date]

-- Monthly spending for chart
SELECT DATE_FORMAT(p.purchase_date, '%Y-%m') AS month_key,
       COALESCE(SUM(t.price_charged), 0) AS total
FROM Purchases p
JOIN Ticket t ON t.ticket_id = p.ticket_id
WHERE p.customer_email = %s
  AND p.purchase_date >= [start_date]
GROUP BY month_key
ORDER BY month_key
```

### Save Flight for Later
**Interface**: "Save Flight" button on flight search results

**Flask Processing** (`app.py:1318-1356`):
- Validates flight exists and is upcoming (departure_time >= NOW())
- Prevents duplicate saves via PRIMARY KEY constraint

**Database Queries**:
```sql
-- Check flight exists and is upcoming
SELECT flight_num FROM Flight
WHERE flight_num = %s AND departure_time >= NOW()

-- Save flight
INSERT INTO SavedFlight (customer_email, flight_num)
VALUES (%s, %s)
```

**Table Schema**:
```sql
CREATE TABLE SavedFlight (
    customer_email VARCHAR(100) NOT NULL,
    flight_num VARCHAR(10) NOT NULL,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (customer_email, flight_num),
    FOREIGN KEY (customer_email) REFERENCES Customer(email) ON DELETE CASCADE,
    FOREIGN KEY (flight_num) REFERENCES Flight(flight_num) ON DELETE CASCADE
)
```

### View Saved Flights
**Interface**: `/saved-flights` - List of all saved flights

**Database Query** (`app.py:1359-1397`):
```sql
SELECT
    sf.saved_at, f.flight_num, f.airline_name, f.departure_airport,
    dep.city AS departure_city, f.arrival_airport, arr.city AS arrival_city,
    f.departure_time, f.arrival_time, f.price, f.status
FROM SavedFlight sf
JOIN Flight f ON sf.flight_num = f.flight_num
JOIN Airport dep ON dep.name = f.departure_airport
JOIN Airport arr ON arr.name = f.arrival_airport
WHERE sf.customer_email = %s
ORDER BY sf.saved_at DESC
```

### Cancel Booking
**Interface**: "Cancel" button on upcoming flights in customer portal

**Flask Processing** (`app.py:1911-1958`):
- Validates booking belongs to customer
- Checks flight hasn't departed yet
- **Uses transaction with FOR UPDATE lock** to prevent race conditions

**Database Operations**:
```sql
-- Verify ownership and lock the record
SELECT t.ticket_id, t.flight_num, f.departure_time
FROM Purchases p
JOIN Ticket t ON t.ticket_id = p.ticket_id
JOIN Flight f ON f.flight_num = t.flight_num
WHERE p.ticket_id = %s AND p.customer_email = %s
FOR UPDATE

-- Delete ticket (cascades to Purchases via ON DELETE CASCADE)
DELETE FROM Ticket WHERE ticket_id = %s
```

**Cascade Behavior**:
- Deleting Ticket automatically deletes corresponding Purchases record
- This is enforced by foreign key constraint

---

## Booking Agent Features

### View My Sales
**Interface**: `/agent` - Filters by date range, airports

**Database Query** (`app.py:1453-1492`):
```sql
SELECT
    p.customer_email, t.ticket_id, t.seat_class, t.price_charged, p.purchase_date,
    f.flight_num, f.airline_name, f.departure_airport, dep.city AS departure_city,
    f.arrival_airport, arr.city AS arrival_city, f.departure_time, f.status
FROM Purchases p
JOIN Ticket t ON t.ticket_id = p.ticket_id
JOIN Flight f ON f.flight_num = t.flight_num
JOIN AuthorizedBy ab
  ON ab.booking_agent_email = p.booking_agent_email
 AND ab.airline_name = f.airline_name
JOIN Airport dep ON dep.name = f.departure_airport
JOIN Airport arr ON arr.name = f.arrival_airport
WHERE p.booking_agent_email = %s
  [+ optional date and airport filters]
ORDER BY p.purchase_date DESC, t.ticket_id DESC
```

### Commission Analytics
**Interface**: `/agent` - Last 30 days metrics

**Database Queries** (`app.py:543-595`):
```sql
-- 30-day performance metrics
SELECT
    COUNT(*) AS tickets_sold,
    COALESCE(SUM(t.price_charged * 0.10), 0) AS total_commission,
    COALESCE(AVG(t.price_charged * 0.10), 0) AS avg_commission
FROM Purchases p
JOIN Ticket t ON t.ticket_id = p.ticket_id
JOIN Flight f ON f.flight_num = t.flight_num
JOIN AuthorizedBy ab
  ON ab.booking_agent_email = p.booking_agent_email
 AND ab.airline_name = f.airline_name
WHERE p.booking_agent_email = %s
  AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)

-- Top customers by tickets (last 6 months)
SELECT p.customer_email, c.name, COUNT(*) AS tickets_sold
FROM Purchases p
JOIN Ticket t ON t.ticket_id = p.ticket_id
JOIN Flight f ON f.flight_num = t.flight_num
JOIN AuthorizedBy ab
  ON ab.booking_agent_email = p.booking_agent_email
 AND ab.airline_name = f.airline_name
JOIN Customer c ON c.email = p.customer_email
WHERE p.booking_agent_email = %s
  AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
GROUP BY p.customer_email, c.name
ORDER BY tickets_sold DESC, p.customer_email
LIMIT 5

-- Top customers by commission (last year)
SELECT p.customer_email, c.name, COALESCE(SUM(t.price_charged * 0.10), 0) AS commission_total
FROM Purchases p
JOIN Ticket t ON t.ticket_id = p.ticket_id
JOIN Flight f ON f.flight_num = t.flight_num
JOIN AuthorizedBy ab
  ON ab.booking_agent_email = p.booking_agent_email
 AND ab.airline_name = f.airline_name
JOIN Customer c ON c.email = p.customer_email
WHERE p.booking_agent_email = %s
  AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
GROUP BY p.customer_email, c.name
ORDER BY commission_total DESC, p.customer_email
LIMIT 5
```

**Business Logic**:
- Commission rate: 10% of ticket price
- Calculated in Python: `price_charged * COMMISSION_RATE`
- Stored as constant: `COMMISSION_RATE = Decimal("0.10")`

---

## Staff Features

### View Airline Flights (Next 30 Days)
**Interface**: `/staff` - Default view + filters

**Database Query** (`app.py:1561-1599`):
```sql
SELECT
    f.flight_num, f.airplane_id, f.price, f.status,
    f.departure_airport, dep.city AS departure_city,
    f.arrival_airport, arr.city AS arrival_city,
    f.departure_time, f.arrival_time,
    COALESCE((SELECT SUM(sc.capacity) FROM SeatClass sc WHERE sc.airplane_id = f.airplane_id), 0) AS total_capacity,
    COALESCE((SELECT COUNT(*) FROM Ticket t WHERE t.flight_num = f.flight_num), 0) AS sold_tickets
FROM Flight f
JOIN Airport dep ON dep.name = f.departure_airport
JOIN Airport arr ON arr.name = f.arrival_airport
WHERE f.airline_name = %s
  AND f.departure_time >= NOW()
  AND f.departure_time <= DATE_ADD(NOW(), INTERVAL 30 DAY)
  [+ optional filters]
ORDER BY f.departure_time, f.flight_num
```

### View Passenger List by Flight
**Interface**: `/staff` - Input flight number in lookup form

**Database Query** (`app.py:1601-1621`):
```sql
SELECT c.email, c.name, t.ticket_id, t.seat_class, p.purchase_date
FROM Purchases p
JOIN Ticket t ON t.ticket_id = p.ticket_id
JOIN Flight f ON f.flight_num = t.flight_num
JOIN Customer c ON c.email = p.customer_email
WHERE f.airline_name = %s
  AND f.flight_num = %s
ORDER BY c.name, t.ticket_id
```

### View Customer Flight History
**Interface**: `/staff` - Input customer email in lookup form

**Database Query** (`app.py:1623-1648`):
```sql
SELECT
    f.flight_num, f.status, f.departure_airport, dep.city AS departure_city,
    f.arrival_airport, arr.city AS arrival_city, f.departure_time,
    p.purchase_date, t.seat_class
FROM Purchases p
JOIN Ticket t ON t.ticket_id = p.ticket_id
JOIN Flight f ON f.flight_num = t.flight_num
JOIN Airport dep ON dep.name = f.departure_airport
JOIN Airport arr ON arr.name = f.arrival_airport
WHERE f.airline_name = %s
  AND p.customer_email = %s
ORDER BY f.departure_time DESC, t.ticket_id DESC
```

### Airline Analytics
**Interface**: `/staff` - Multiple analytics sections

**Database Queries** (`app.py:598-710`):

```sql
-- Most frequent customer (last year)
SELECT p.customer_email, c.name, COUNT(*) AS trips_taken
FROM Purchases p
JOIN Ticket t ON t.ticket_id = p.ticket_id
JOIN Flight f ON f.flight_num = t.flight_num
JOIN Customer c ON c.email = p.customer_email
WHERE f.airline_name = %s
  AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
GROUP BY p.customer_email, c.name
ORDER BY trips_taken DESC, p.customer_email
LIMIT 1

-- Tickets sold per month (last 6 months)
SELECT DATE_FORMAT(p.purchase_date, '%Y-%m') AS month_key, COUNT(*) AS total
FROM Purchases p
JOIN Ticket t ON t.ticket_id = p.ticket_id
JOIN Flight f ON f.flight_num = t.flight_num
WHERE f.airline_name = %s
  AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
GROUP BY month_key
ORDER BY month_key

-- Delay statistics
SELECT
    SUM(CASE WHEN status = 'delayed' THEN 1 ELSE 0 END) AS delayed_count,
    SUM(CASE WHEN status <> 'delayed' THEN 1 ELSE 0 END) AS non_delayed_count
FROM Flight
WHERE airline_name = %s

-- Top destinations (last 3 months and last year)
SELECT f.arrival_airport, arr.city AS arrival_city, COUNT(*) AS tickets_sold
FROM Purchases p
JOIN Ticket t ON t.ticket_id = p.ticket_id
JOIN Flight f ON f.flight_num = t.flight_num
JOIN Airport arr ON arr.name = f.arrival_airport
WHERE f.airline_name = %s
  AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL {3 MONTH | 1 YEAR})
GROUP BY f.arrival_airport, arr.city
ORDER BY tickets_sold DESC, f.arrival_airport
LIMIT 5

-- Top booking agents (this month and this year, by tickets and by commission)
SELECT
    p.booking_agent_email,
    COUNT(*) AS tickets_sold,
    COALESCE(SUM(t.price_charged * 0.10), 0) AS commission_total
FROM Purchases p
JOIN Ticket t ON t.ticket_id = p.ticket_id
JOIN Flight f ON f.flight_num = t.flight_num
WHERE f.airline_name = %s
  AND p.booking_agent_email IS NOT NULL
  AND {period_filter}  -- current month or current year
GROUP BY p.booking_agent_email
ORDER BY {tickets_sold DESC | commission_total DESC}
LIMIT 5
```

---

## Admin Actions (Staff with 'admin' Permission)

### Add Airport
**Interface**: `/staff` - Airport code and city input

**Flask Processing** (`app.py:1670-1698`):
- Validates airport code format (3-10 uppercase letters/numbers)
- Checks for duplicate airport codes

**Database Query**:
```sql
-- Check if exists
SELECT 1 FROM Airport WHERE name = %s

-- Insert new airport
INSERT INTO Airport (name, city) VALUES (%s, %s)
```

### Add Airplane
**Interface**: `/staff` - Airplane ID and seat capacities

**Flask Processing** (`app.py:1701-1748`):
- Validates at least one seat class has capacity > 0
- Uses **transaction** to create airplane and seat class records atomically

**Database Queries**:
```sql
-- Check if airplane ID exists
SELECT 1 FROM Airplane WHERE id = %s

-- Create airplane
INSERT INTO Airplane (id, airline_name) VALUES (%s, %s)

-- Create seat classes (economy, business, first as needed)
INSERT INTO SeatClass (airplane_id, seat_class, capacity)
VALUES (%s, %s, %s)
-- repeated for each non-zero capacity class
```

### Create Flight
**Interface**: `/staff` - Flight details form

**Flask Processing** (`app.py:1751-1816`):
- Validates airplane belongs to airline
- Validates arrival time > departure time
- Validates departure ≠ arrival airports
- **Database triggers** perform additional validation

**Database Query**:
```sql
-- Verify airplane ownership
SELECT 1 FROM Airplane WHERE id = %s AND airline_name = %s

-- Check flight number uniqueness
SELECT 1 FROM Flight WHERE flight_num = %s

-- Insert flight
INSERT INTO Flight (
    flight_num, departure_time, arrival_time, price, status,
    airline_name, airplane_id, departure_airport, arrival_airport
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
```

**Trigger Enforcement** (`validate_flight_insert` and `validate_flight_update`):
```sql
-- Before insert/update on Flight
IF NEW.departure_airport = NEW.arrival_airport THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Departure and arrival airports must differ.'
END IF

IF NEW.arrival_time <= NEW.departure_time THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Arrival time must be later than departure time.'
END IF
```

### Authorize Booking Agent
**Interface**: `/staff` - Select agent email from dropdown

**Flask Processing** (`app.py:1819-1857`):
- Validates agent exists
- Checks for duplicate authorization

**Database Queries**:
```sql
-- Verify agent exists
SELECT 1 FROM BookingAgent WHERE email = %s

-- Check if already authorized
SELECT 1 FROM AuthorizedBy
WHERE booking_agent_email = %s AND airline_name = %s

-- Create authorization
INSERT INTO AuthorizedBy (booking_agent_email, airline_name)
VALUES (%s, %s)
```

---

## Operator Actions (Staff with 'operator' Permission)

### Update Flight Status
**Interface**: `/staff` - Flight number and new status dropdown

**Flask Processing** (`app.py:1860-1894`):
- Validates flight belongs to airline
- Validates status is one of: upcoming, in-progress, delayed

**Database Query**:
```sql
-- Verify ownership
SELECT 1 FROM Flight
WHERE flight_num = %s AND airline_name = %s

-- Update status
UPDATE Flight SET status = %s WHERE flight_num = %s
```

---

## Database Design Highlights

### 1. Triggers for Data Integrity

#### Flight Validation (`validate_flight_insert`, `validate_flight_update`)
- Enforces departure ≠ arrival airports
- Enforces arrival time > departure time
- Runs on INSERT and UPDATE of Flight table

#### Capacity Enforcement (`enforce_ticket_capacity`)
- Validates ticket's airplane_id matches flight's airplane_id
- Validates seat class exists for airplane
- Prevents overbooking by checking: `booked_count < seat_capacity`
- Runs on INSERT of Ticket table

#### Agent Purchase Authorization (`enforce_agent_purchase_authorization_insert`, `enforce_agent_purchase_authorization_update`)
- Validates direct `Purchases` inserts/updates against `AuthorizedBy`
- Allows direct customer purchases where `booking_agent_email` is `NULL`
- Prevents seeded or manually inserted agent sales for unauthorized airlines

### 2. Stored Procedure for Complex Transactions

#### `purchase_ticket()` Procedure
**Advantages**:
- **Atomic transaction**: All validations and inserts happen in one database transaction
- **Server-side validation**: Reduces network round-trips
- **Consistent business logic**: Price calculation and capacity checks happen in one place
- **Better performance**: Uses FOR UPDATE locks to prevent race conditions

**Steps**:
1. Validate customer exists
2. Lock flight record (FOR UPDATE)
3. Check flight is bookable (status and departure time)
4. Validate agent authorization (if applicable)
5. Lock seat class capacity (FOR UPDATE)
6. Check available seats
7. Calculate price with multiplier
8. Insert ticket (auto-increment ID)
9. Insert purchase record
10. Return ticket_id and price_charged

### 3. Indexes for Performance

```sql
CREATE INDEX idx_flight_departure_status ON Flight (departure_time, status)
CREATE INDEX idx_flight_route_departure ON Flight (departure_airport, arrival_airport, departure_time)
CREATE INDEX idx_flight_airline_departure ON Flight (airline_name, departure_time)
CREATE INDEX idx_ticket_flight_class ON Ticket (flight_num, seat_class)
CREATE INDEX idx_purchases_customer_date ON Purchases (customer_email, purchase_date)
CREATE INDEX idx_purchases_agent_date ON Purchases (booking_agent_email, purchase_date)
CREATE INDEX idx_authorized_by_airline ON AuthorizedBy (airline_name, booking_agent_email)
```

**Why These Indexes**:
- `idx_flight_departure_status`: Fast filtering of upcoming/in-progress flights
- `idx_flight_route_departure`: Optimizes route-based searches
- `idx_flight_airline_departure`: Staff dashboard queries (airline + date range)
- `idx_ticket_flight_class`: Capacity check queries (count tickets per flight/class)
- `idx_purchases_customer_date`: Customer spending analytics
- `idx_purchases_agent_date`: Agent commission analytics
- `idx_authorized_by_airline`: Agent authorization checks during booking

### 4. Cascade Deletes for Referential Integrity

```sql
-- Deleting Customer cascades to Purchases and SavedFlight
FOREIGN KEY (customer_email) REFERENCES Customer(email)
    ON DELETE CASCADE

-- Deleting Ticket cascades to Purchases
FOREIGN KEY (ticket_id) REFERENCES Ticket(ticket_id)
    ON DELETE CASCADE

-- Deleting Flight cascades to Tickets and SavedFlight
FOREIGN KEY (flight_num) REFERENCES Flight(flight_num)
    ON DELETE CASCADE
```

**Rationale**:
- Maintains data consistency when entities are removed
- Prevents orphaned records
- Simplifies deletion logic in application code

### 5. Composite Primary Keys

```sql
PRIMARY KEY (customer_email, flight_num)  -- SavedFlight
PRIMARY KEY (ticket_id, customer_email)   -- Purchases
PRIMARY KEY (airplane_id, seat_class)     -- SeatClass
PRIMARY KEY (username, permission)        -- StaffPermission
PRIMARY KEY (booking_agent_email, airline_name)  -- AuthorizedBy
```

**Benefits**:
- Natural uniqueness constraints (customer can only save flight once)
- Prevents duplicate records
- Efficient lookups using composite keys

### 6. TIMESTAMP for Audit Trails

```sql
saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- SavedFlight
```

**Use Case**: Track when customer saved a flight for later

### 7. CHECK Constraints for Valid Values

```sql
status VARCHAR(20) NOT NULL CHECK (status IN ('upcoming', 'in-progress', 'delayed'))
permission VARCHAR(20) NOT NULL CHECK (permission IN ('admin', 'operator'))
```

**Enforcement**: Database rejects invalid status/permission values

---

## Security Features

### 1. CSRF Protection
- Every form includes CSRF token: `<input type="hidden" name="_csrf_token" value="{{ csrf_token() }}">`
- `@app.before_request` validates token on all POST requests
- Token stored in session, compared using constant-time comparison

### 2. Password Security
- PBKDF2-SHA256 hashing with 260,000 iterations
- 16-byte random salt per password
- Automatic upgrade from plaintext to hash on login (for demo accounts)
- Passwords never logged or displayed

### 3. SQL Injection Prevention
- **Parameterized queries**: All user input passed as parameters (`%s`), never string concatenation
- **Prepared-statement style binding**: MySQL connector binds values separately from SQL text
- **Allowlisted SQL fragments**: Dynamic table names, analytics periods, and sort clauses come from server constants
- **Input validation**: Whitelisting of flight statuses, seat classes, etc.

### 4. Authorization Checks
- **Role-based access control**: `@roles_required('customer', 'booking_agent')`
- **Permission-based actions**: `@permission_required('admin')` or `@permission_required('operator')`
- **Ownership verification**: Customers can only cancel their own bookings
- **Agent authorization**: Agents can only book for airlines they're authorized for

### 5. Session Security
- HTTP-only cookies (JavaScript cannot access)
- SameSite=Lax (CSRF protection)
- Role-specific identity fields required on protected requests
- Absolute 2-hour expiration (`PERMANENT_SESSION_LIFETIME`, `_session_created_at`, and `SESSION_REFRESH_EACH_REQUEST=False`)
- Session cleared on logout
- No-store cache headers on authenticated/protected responses

---

## Performance Optimizations

### 1. Connection Pooling
- MySQL Connector handles connection pooling automatically
- `get_db_connection()` creates new connection per request
- Connection closed after request completes

### 2. Query Optimization
- Use of indexes for common query patterns
- Efficient JOINs (indexed foreign keys)
- Aggregate functions (SUM, COUNT) pushed to database
- Subqueries used for complex calculations (capacity, booked tickets)

### 3. Frontend Optimizations
- Auto-fill reduces user input errors and speeds up form completion
- Client-side validation (JavaScript) reduces unnecessary server requests
- Pre-loaded dropdowns (airports, cities, airlines) reduce query load

---

## Common SQL Patterns

### Aggregate with COALESCE for Zero Defaults
```sql
COALESCE(SUM(t.price_charged), 0) AS total
COALESCE(AVG(t.price_charged), 0) AS average
COALESCE(COUNT(*), 0) AS count
```
**Why**: Returns 0 instead of NULL when no rows match, simplifying application logic

### Date Filtering with Intervals
```sql
WHERE p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
WHERE f.departure_time >= NOW()
WHERE f.departure_time <= DATE_ADD(NOW(), INTERVAL 30 DAY)
```
**Why**: Database-native date arithmetic, works correctly across DST and leap years

### Conditional Aggregation
```sql
SUM(CASE WHEN status = 'delayed' THEN 1 ELSE 0 END) AS delayed_count
SUM(CASE WHEN status <> 'delayed' THEN 1 ELSE 0 END) AS non_delayed_count
```
**Why**: Single query instead of multiple queries for different conditions

### Transaction Locking
```sql
SELECT ... FROM ... WHERE ... FOR UPDATE
```
**Why**: Prevents race conditions during booking (two users booking last seat simultaneously)

---

## Testing Scenarios

### 1. Capacity Enforcement
- Try to book 2 tickets on SJ900 (capacity: 1 economy seat)
- First booking succeeds, second fails with "No seats remain"

### 2. Trigger Validation
- Try to create flight with same departure and arrival airport
- Rejected by `validate_flight_insert` trigger

### 3. Authorization
- Booking agent `agent1@travel.com` is authorized for SkyJet only
- Booking agent `agent2@travel.com` is authorized for SkyJet and AirAsia
- Try to book AirAsia flight → fails with "not authorized" error

### 4. Cascade Delete
- Cancel a booking → Ticket and Purchases records both deleted
- Delete a flight → all associated Tickets, Purchases, SavedFlights deleted

### 5. Concurrent Booking
- Two users try to book the last seat simultaneously
- Booking transaction uses FOR UPDATE locks so only one succeeds

---

## Demonstration Tips

### Show These Features
1. **Airport-city auto-fill** on flight search
2. **Validation error** when selecting LHR (London) airport but San Francisco city
3. **Flight status lookup** by entering flight number + status "In Progress"
4. **Saved flights** feature (save, view list, remove)
5. **Booking cancellation** (only available for future flights)
6. **Admin vs Operator permissions** (different staff accounts see different actions)
7. **Analytics charts** (customer spending, staff ticket sales over time)
8. **Booking transaction** in action (confirmation message mentions server-side capacity checks)

### Talk About These Database Features
1. **Triggers** preventing invalid data (mention flight validation, capacity enforcement, agent authorization)
2. **Transactional booking** handling complex booking logic atomically
3. **Indexes** making searches fast (demonstrate search speed)
4. **Foreign key cascades** maintaining referential integrity
5. **Transaction isolation** preventing race conditions during booking
6. **Check constraints** enforcing valid flight statuses
7. **Composite primary keys** preventing duplicate saves/authorizations

---

## Quick Reference - Demo Accounts

| Role | Username/Email | Password | Airline | Permissions |
|------|---------------|----------|---------|-------------|
| Customer | alice@example.com | password123 | - | - |
| Customer | bob@example.com | password123 | - | - |
| Customer | charlie@example.com | password123 | - | - |
| Booking Agent | agent1@travel.com | agentpass | SkyJet (authorized) | - |
| Booking Agent | agent2@travel.com | agentpass | SkyJet, AirAsia | - |
| Admin Staff | SkyJet_admin | adminpass | SkyJet | admin, operator |
| Admin Staff | AirAsia_admin | adminpass | AirAsia | admin, operator |
| Admin Staff | Delta_admin | adminpass | Delta | admin, operator |
| Regular Staff | SkyJet_staff | staffpass | SkyJet | operator |

---

## Routes Summary

| Route | Method | Authentication | Purpose |
|-------|--------|----------------|---------|
| `/` | GET | Public | Home page, featured flights |
| `/login` | GET/POST | Public | Login for all roles |
| `/register` | GET/POST | Public | Customer/agent registration |
| `/logout` | GET | Required | Clear session |
| `/flights` | GET | Public | Flight search + status lookup |
| `/flight/<num>` | GET | Public | Flight details |
| `/book` | POST | Customer/Agent | Purchase ticket |
| `/customer` | GET | Customer | Dashboard, bookings, analytics |
| `/saved-flights` | GET | Customer | View saved flights list |
| `/saved-flights/save/<num>` | POST | Customer | Save a flight |
| `/saved-flights/remove/<num>` | POST | Customer | Remove saved flight |
| `/cancel_booking/<id>` | POST | Customer | Cancel booking |
| `/agent` | GET | Agent | Dashboard, sales, commission |
| `/staff` | GET | Staff | Dashboard, analytics, lookups |
| `/staff/airport` | POST | Admin | Add airport |
| `/staff/airplane` | POST | Admin | Add airplane |
| `/staff/flight` | POST | Admin | Create flight |
| `/staff/authorize-agent` | POST | Admin | Authorize booking agent |
| `/staff/status` | POST | Operator | Update flight status |
| `/status` | GET | Public | Redirects to `/flights` |

---

End of Cheatsheet
