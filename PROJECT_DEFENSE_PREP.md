# Airline Reservation System - Project Defense Preparation Guide

**Date**: May 2, 2026  
**Project**: Air Ticket Reservation System (Part 3 Refined)  
**Tech Stack**: Flask + MySQL + Jinja2 + CSS

---

## Table of Contents
1. [What is This Project?](#what-is-this-project)
2. [System Overview](#system-overview)
3. [Architecture & Design Decisions](#architecture--design-decisions)
4. [Key Technical Decisions & Trade-offs](#key-technical-decisions--trade-offs)
5. [Database Design](#database-design)
6. [Security & Authentication](#security--authentication)
7. [Booking Logic & Transaction Safety](#booking-logic--transaction-safety)
8. [Analytics & Reporting](#analytics--reporting)
9. [Performance Optimizations](#performance-optimizations)
10. [Integrity Mechanisms](#integrity-mechanisms)
11. [Role-Based Access Control](#role-based-access-control)
12. [UI/UX Design Decisions](#uiux-design-decisions)
13. [Feature Logic Walkthrough](#feature-logic-walkthrough)
14. [Bonus Feature: Saved Flights](#bonus-feature-saved-flights)
15. [Customer Booking Cancellation](#customer-booking-cancellation)
16. [Known Limitations & Future Improvements](#known-limitations--future-improvements)
17. [Demo Walkthrough Tips](#demo-walkthrough-tips)

---

## What is This Project?

### First, What is a "Database Final Project"?

This is a **computer science course assignment** where students build a complete web application that stores and retrieves data from a database. The goal is to demonstrate understanding of:

- **Database design** (how to organize data efficiently)
- **Web development** (how to build interactive websites)
- **Data integrity** (ensuring data stays accurate and consistent)
- **Security** (protecting user data and preventing unauthorized access)
- **Performance** (making the system fast even with lots of data)

### What is an "Airline Reservation System"?

Imagine you're building a website like **Expedia**, **Kayak**, or an airline's own booking site (like Delta.com or United.com). Users can:

- **Search for flights** between cities on specific dates
- **Book tickets** for those flights
- **View their booking history** and spending
- **Manage flight operations** (for airline staff)

But instead of just making it work, you have to build it **from scratch** using programming languages and database concepts learned in class.

### What Technologies Are Used?

**Flask**: A Python "web framework" - a toolkit that makes it easier to build websites with Python. Think of it as pre-built components for handling web requests, user sessions, and HTML rendering.

**MySQL**: A "relational database" - a system for storing and organizing data in tables. Like a super-powered Excel spreadsheet that can handle millions of rows and complex relationships between data.

**Jinja2**: A "templating engine" - a system for generating HTML pages dynamically. Instead of writing static HTML, you write templates that get filled with data from the database.

**CSS**: "Cascading Style Sheets" - code that makes web pages look nice (colors, layouts, fonts).

### Why These Technologies?

- **Python + Flask**: Easy to learn, powerful for data processing, great for database interactions
- **MySQL**: Industry-standard database used by most websites, supports complex queries and transactions
- **Web technologies**: Because airline reservations happen online, not in desktop apps

---

## System Overview

### What is This System?

An **airline reservation platform** that allows customers to book flights, booking agents to sell tickets on behalf of airlines, and airline staff to manage operations. The system mimics real-world airline booking systems like Kayak, Expedia, or airline-native systems.

### High-level flow:
1. **Public users** → Search upcoming flights, look up in-progress flight status
2. **Customers** → Register, log in, book flights, cancel future bookings, save/remove flights, view bookings, analyze spending
3. **Booking agents** → Register, authorize with airlines, sell tickets on behalf of customers, track commissions
4. **Airline staff** → Admin: manage airports, airplanes, flights, authorize agents | Operator: update flight status

### Why These Three Roles?

**Real-world alignment**: Airlines actually have separate customer booking interfaces, travel agent relationships, and internal staff operations.

**SQL complexity**: Each role exercises different query patterns (search, analytics, authorization checks, admin CRUD).

**Authorization showcase**: Demonstrates role-based access control without needing external OAuth/SAML systems.

---

## Architecture & Design Decisions

### Decision 1: Unified Authentication with Role Separation

**What was chosen**: A single `login` endpoint that checks three different tables (`Customer`, `BookingAgent`, `AirlineStaff`) based on user input, then stores `role`, `identity`, and role-specific metadata in a server-side session.

**Why**:
- **UX simplicity**: One login page for all roles instead of three separate portals.
- **Consistency**: Unified password hashing (`PBKDF2-SHA256`) across all roles.
- **Security**: Passwords never stored as plain text; session-based authorization avoids client-side trust.
- **Flexibility**: Easy to add new roles without duplicating authentication logic.

**Trade-off**:
- **Single database call per login attempt**: Must check `Customer` table first, then `BookingAgent`, then `AirlineStaff`. Could be optimized by consolidating users into one table with a `role` column, but that would lose the normalization benefit of having role-specific columns (e.g., `Customer.passport_number` only exists in the `Customer` table).
- **Session memory**: Storing all staff permissions in the session means if permissions change in the database, the user must log out and log back in. Could add a "refresh permissions" endpoint for real-time updates.

### Decision 2: Three Separate User Tables Instead of One

**What was chosen**: `Customer`, `BookingAgent`, `AirlineStaff` as separate tables rather than a unified `User` table with a `role` column.

**Why**:
- **Normalization**: Customer has passport, phone, address; booking agent only needs email; staff needs airline affiliation. One table would have many NULL columns.
- **Constraints**: Each role has different required fields. `Customer.passport_expiration_date` only matters for customers.
- **Join efficiency**: Queries for customer bookings only hit the `Customer` and `Purchases` tables; no need to JOIN a bloated universal `User` table.

**Trade-off**:
- **Authentication logic is more complex**: Must check three tables instead of one. Mitigated by writing a clean `verify_password` helper that works with any table.
- **Duplicate columns**: `email` and `password` appear in both `Customer` and `BookingAgent`. Could normalize further, but the duplication is small.

---

## Key Technical Decisions & Trade-offs

### 1. **PBKDF2-SHA256 Password Hashing**

**What is password hashing?**
When users create accounts, you can't store their passwords as plain text (like "password123"). If someone hacks your database, they'd see everyone's passwords. Instead, you run the password through a mathematical function that transforms it into a scrambled string that can't be reversed.

**What is PBKDF2-SHA256?**
- **PBKDF2**: "Password-Based Key Derivation Function 2" - a standard algorithm for turning passwords into secure keys
- **SHA256**: The underlying hash function (Secure Hash Algorithm 256-bit)
- **260,000 iterations**: The password is hashed 260,000 times, making it slow for attackers to guess passwords

**Decision**: Hash passwords with PBKDF2-SHA256 (260,000 iterations) instead of plain text or simple MD5.

**Why**:
- **Security baseline**: Passwords are salted and iterated, making them resistant to brute-force attacks and rainbow tables.
- **Standard library**: Python's `hashlib.pbkdf2_hmac` is in the standard library; no external dependencies needed.
- **Backward compatibility**: Old plain-text passwords are upgraded on first login (see `maybe_upgrade_password` helper).

**Trade-off**:
- **Login latency**: Each password hash verification takes ~260ms due to 260,000 iterations. This is intentional (forces attackers to spend CPU), but means login feels slightly slower. Not user-facing enough to be a problem.
- **Not state-of-the-art**: Argon2 or Bcrypt would be slightly better, but PBKDF2 is industry-acceptable and doesn't require external packages.

### 2. **Session-Based Authorization vs. Token-Based**

**What is a session?**
When you log into a website, the server needs to remember "this is User X" for future requests. A session is like a temporary ID card that the server gives your browser. Every time you visit a page, you show this ID card, and the server knows who you are.

**What are tokens?**
Instead of storing session data on the server, you give the user a signed token (like a JWT - JSON Web Token) that contains their identity. The user sends this token with every request, and the server verifies it.

**Decision**: Use Flask's built-in sessions (server-side, cookie-stored) to maintain `role`, `identity`, and permissions.

**Why**:
- **Simplicity**: Flask handles session serialization, expiration, and CSRF protection out of the box.
- **Revocation**: User permissions can be revoked immediately by deleting the session server-side (e.g., if an admin removes an agent's authorization).
- **Course scope**: Tokens and JWTs are not covered in the database systems course; sessions are more aligned with classical web architecture.

**Trade-off**:
- **Server memory**: Sessions are stored in memory (or can be persisted to a database). For production, you'd need distributed session storage (Redis, Memcached). For a demo, in-memory is fine.
- **Scalability**: Cannot easily scale across multiple servers without session replication.
- **Stateless disadvantage**: Less suitable for microservices or APIs. But this is a monolithic web app, so it's appropriate.

### 3. **Parameterized Queries for SQL Injection Prevention**

**What is SQL injection?**
Imagine a login form where users enter their email. If you build the SQL query like this:
```sql
SELECT * FROM Customer WHERE email = 'user_input'
```
A malicious user could enter: `' OR '1'='1` making the query:
```sql
SELECT * FROM Customer WHERE email = '' OR '1'='1'
```
This would log in as the first customer in the database!

**What are parameterized queries?**
Instead of inserting user input directly into SQL strings, you use placeholders and pass the values separately:
```python
cursor.execute("SELECT * FROM Customer WHERE email = %s", (user_email,))
```

**Decision**: All queries use `cursor.execute(query_string, params)` with `%s` placeholders instead of string concatenation.

**Why**:
- **Security**: SQL injection is impossible when parameters are passed separately.
- **Database efficiency**: The database can cache query plans for repeated parameterized queries.
- **Course alignment**: This is SQL best practice taught in every database course.

**Trade-off**:
- **Slightly more verbose code**: Have to list parameters separately. Mitigated by careful query formatting.
- **No string-based search optimization**: Cannot use LIKE predicates with wildcards dynamically, but this system doesn't need full-text search.

---

## Database Design

### What is a Database?

A database is like a digital filing cabinet for storing and organizing information. Instead of paper folders, you have **tables** (spreadsheets) with **rows** (records) and **columns** (fields).

### What is Normalization?

**Normalization** is the process of organizing data to minimize redundancy and dependency. Think of it like organizing your closet:

**Bad (not normalized)**: One big drawer with everything mixed together
- T-shirt with jeans
- Socks with hats
- Everything jumbled

**Good (normalized)**: Separate drawers for each type
- Drawer 1: T-shirts only
- Drawer 2: Pants only  
- Drawer 3: Socks only

**Why third normal form (3NF)?**
- **No anomalies**: Removing non-key dependencies ensures inserting a flight doesn't force inserting an airline; deleting an airline cascades to its flights.
- **Constraints**: Each role has different required fields. `Customer.passport_expiration_date` only matters for customers.
- **Join efficiency**: Queries for customer bookings only hit the `Customer` and `Purchases` tables; no need to JOIN a bloated universal `User` table.

### Schema Overview

**Core entities**:
- `Airline` - Airlines operating in the system
- `Airport` - Airports (departure/arrival points)
- `Airplane` - Aircraft owned by airlines, with `SeatClass` variants (economy, business, first)
- `Flight` - Scheduled flights (departure, arrival, price, status)
- `Customer` - End users booking flights
- `Ticket` - Individual seat reservations
- `Purchases` - Links tickets to customers and booking agents
- `BookingAgent` - Travel agents authorized to sell flights
- `AuthorizedBy` - Mapping of which agents can sell which airlines' flights
- `AirlineStaff` - Airline employees
- `StaffPermission` - Admin vs. operator permissions for staff
- `SavedFlight` - Bonus feature: customer-saved flights for later review

### Normalization & Integrity

**Why third normal form (3NF)?**
- **No anomalies**: Removing non-key dependencies ensures inserting a flight doesn't force inserting an airline; deleting an airline cascades to its flights.
- **Constraints**: Each role has different required fields. `Customer.passport_expiration_date` only matters for customers.
- **Join efficiency**: Queries for customer bookings only hit the `Customer` and `Purchases` tables; no need to JOIN a bloated universal `User` table.

**Normalization trade-off**:
- **More JOINs required**: A customer booking report requires joining `Purchases → Ticket → Flight → Airport`. Could denormalize by storing airport names in `Flight`, but that risks inconsistency.
- **Slightly slower queries**: Multiple JOINs are slower than scanning a single denormalized table. However, indexes mitigate this (see [Performance Optimizations](#performance-optimizations)).

### Composite Key Design

**`Purchases(ticket_id, customer_email)` as composite primary key**:
- Ensures each ticket is associated with exactly one customer and one booking agent (if applicable).
- Prevents the same ticket being purchased by multiple customers.

**Why composite?** 
- A ticket (row in `Ticket`) is meaningless without knowing who bought it. The `Purchases` table links them.
- Natural composite key: `(ticket_id, customer_email)` uniquely identifies a purchase.

---

## Security & Authentication

### Authentication Flow

```
1. User selects an account type and submits identifier + password on `/login`.
2. The route checks only the table for that selected role:
   - Customer: validates email, fetches `Customer.email`, `Customer.name`, `Customer.password`.
   - Booking agent: validates email, fetches `BookingAgent.email`, `BookingAgent.password`.
   - Airline staff: validates username, fetches staff name, airline, and password from `AirlineStaff`.
3. `verify_password()` checks the submitted password. If an older plain-text sample password is detected, `maybe_upgrade_password()` replaces it with a PBKDF2 hash after successful login.
4. Role-specific data is loaded into the session:
   - Customer: `customer_email`.
   - Booking agent: `agent_email` and `authorized_airlines`.
   - Airline staff: `airline_name` and `permissions`.
5. User is redirected to the matching portal through `/home`.
6. Later requests use `roles_required()` or `permission_required()` to enforce access control before running feature logic.
```

### Password Security Details

**Storage format**: `pbkdf2_sha256$260000$<salt>$<hash>`
- `pbkdf2_sha256`: Algorithm name
- `260000`: Number of iterations
- `<salt>`: Random 16-byte hex salt (unique per password)
- `<hash>`: 64-byte hex digest

**Verification**:
1. Parse the stored password to extract salt and iteration count
2. Re-hash the provided password with the same salt and iterations
3. Compare digests using `hmac.compare_digest()` (constant-time comparison to prevent timing attacks)

**Why constant-time comparison?**
- If you use regular string comparison (`==`), an attacker can measure how many characters match before failure, reducing the search space. `hmac.compare_digest()` takes the same time regardless of where a mismatch occurs.

### Session Security

**Cookies are**:
- `HttpOnly`: Cannot be accessed by JavaScript (prevents XSS attacks from stealing cookies).
- `SameSite=Lax`: Sent in same-site requests and top-level navigations, but not in cross-site iframes or image loads (prevents CSRF attacks).
- `Secure` flag: Not set in demo (because we use `http://`), but in production would only be sent over HTTPS.

**Session lifetime**: 2 hours. If idle for 2 hours, user must log in again.

---

## Booking Logic & Transaction Safety

### The Race Condition Problem

**What is a race condition?**
Imagine two customers trying to book the last seat on a flight at the exact same moment. Both see "1 seat available" and both try to book it. Without protection, both bookings could succeed, creating an overbooking (selling more tickets than seats available).

**Without transactions**:
```
Flight ABC has 1 economy seat available.
Customer 1 checks availability: 1 seat left ✓
Customer 2 checks availability: 1 seat left ✓
Customer 1 books: INSERT Ticket (seat_class='economy', flight='ABC')
Customer 2 books: INSERT Ticket (seat_class='economy', flight='ABC')
Result: 2 tickets sold for 1 seat. Overbooking!
```

**Why it happens**: Between the "check availability" and "insert ticket" steps, another customer could have booked the same seat.

### Transaction-Safe Booking Implementation

**What is a transaction?**
A transaction is like a "bundle" of database operations that either all succeed together or all fail together. It's like transferring money between bank accounts - you can't have money leave one account without arriving in the other.

**Code logic**:
```python
try:
    connection.start_transaction()
    
    # Step 1: Lock the Flight row
    cursor.execute("SELECT * FROM Flight WHERE flight_num = %s FOR UPDATE", (flight_num,))
    flight = cursor.fetchone()
    
    # Step 2: Lock the SeatClass row
    cursor.execute(
        "SELECT * FROM SeatClass WHERE airplane_id = %s AND seat_class = %s FOR UPDATE",
        (airplane_id, seat_class)
    )
    seat_class = cursor.fetchone()
    
    # Step 3: Count already booked tickets in this class
    cursor.execute(
        "SELECT COUNT(*) FROM Ticket WHERE flight_num = %s AND seat_class = %s",
        (flight_num, seat_class)
    )
    booked_count = cursor.fetchone()['COUNT(*)']
    
    # Step 4: Check capacity
    if booked_count >= seat_class['capacity']:
        connection.rollback()
        flash("No seats available in this class.")
        return redirect(url_for('flights'))
    
    # Step 5: Insert ticket and purchase (all locked, atomic)
    cursor.execute(
        "INSERT INTO Ticket (flight_num, seat_class, airplane_id, price_charged) VALUES (%s, %s, %s, %s)",
        (flight_num, seat_class, airplane_id, price_charged)
    )
    ticket_id = cursor.lastrowid
    
    cursor.execute(
        "INSERT INTO Purchases (ticket_id, customer_email, booking_agent_email, purchase_date) VALUES (%s, %s, %s, %s)",
        (ticket_id, customer_email, agent_email, today)
    )
    
    connection.commit()
    flash("Booking confirmed!")
    
except Exception as e:
    connection.rollback()
    flash("Booking failed. Please try again.")
```

### Why `SELECT ... FOR UPDATE` is Important

**What is row locking?**
Normally, multiple users can read the same database row simultaneously. But `FOR UPDATE` tells the database: "Lock this row so no one else can modify it until I'm done."

**Without locking**:
- Customer 1 counts booked tickets: 10
- Customer 2 counts booked tickets: 10 (no lock, so they see the same count)
- Both customers see 11/11 seats available and proceed
- Both inserts succeed even though only 1 seat remained

**With `FOR UPDATE`**:
- Customer 1 locks the `SeatClass` row
- Customer 2 tries to lock the same row → **WAITS** until Customer 1 releases the lock
- Customer 1 counts booked, inserts ticket, commits
- Customer 2's lock is released, they count booked (now 11), see 0 seats available, roll back
- Only Customer 1's booking succeeds

### Trade-offs

| Aspect | Decision | Benefit | Cost |
|--------|----------|---------|------|
| **Transactional isolation** | SERIALIZABLE-equivalent using row locks | Guarantees no overbooking | Slightly increased latency (locks held during booking) |
| **Two-phase commit** | Application coordinates locked rows | Simpler than database-level 2PC | Deadlock possible if many bookings happen simultaneously |
| **Trigger backup** | Database-side `enforce_ticket_capacity` trigger prevents overselling even if app code is bypassed | Defense-in-depth | Slight insert overhead; redundant with app-side check |

---

## Analytics & Reporting

### What are Analytics?

Analytics are reports that help users understand patterns in their data. Instead of just showing raw data, analytics summarize and visualize trends.

### Customer Spending Analytics

**Default view**:
- Total spending over the last 12 months
- Monthly breakdown for the last 6 months (bar chart)

**Custom view**:
- User selects start and end dates
- System recalculates total and monthly breakdown for that range

**Query pattern**:
```sql
SELECT 
    COALESCE(SUM(t.price_charged), 0) AS total
FROM Purchases p
JOIN Ticket t ON t.ticket_id = p.ticket_id
WHERE p.customer_email = ?
  AND p.purchase_date BETWEEN ? AND ?
```

**Why this matters**:
- Shows customers their spending trends (good for personal budgeting).
- Demonstrates SQL aggregation (`SUM`, `GROUP BY`, date filtering).
- Common in real reservation systems (Expedia, Kayak show spending summaries).

### Booking Agent Commission Analytics

**30-day commission report**:
- Count of tickets sold
- Sum of commissions (10% of ticket price)
- Average commission per ticket
- Top customers by ticket count
- Top customers by commission earned

**Query pattern**:
```sql
SELECT 
    booking_agent_email,
    COUNT(*) AS tickets_sold,
    SUM(t.price_charged * 0.10) AS total_commission
FROM Purchases p
JOIN Ticket t ON t.ticket_id = p.ticket_id
WHERE p.booking_agent_email = ?
  AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
GROUP BY p.booking_agent_email
```

**Trade-off**: Commission rate (10%) is hardcoded. In a real system, this would be per-airline or per-tier (loyalty levels). Hardcoding simplifies the demo but loses flexibility.

### Airline Staff Analytics

**Most frequent customer** (last 12 months):
```sql
SELECT 
    p.customer_email,
    COUNT(*) AS flight_count
FROM Purchases p
JOIN Ticket t ON t.ticket_id = p.ticket_id
JOIN Flight f ON f.flight_num = t.flight_num
WHERE f.airline_name = ?
  AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
GROUP BY p.customer_email
ORDER BY flight_count DESC
LIMIT 1
```

**Delay statistics**:
```sql
SELECT 
    SUM(CASE WHEN status = 'delayed' THEN 1 ELSE 0 END) AS delayed_count,
    SUM(CASE WHEN status != 'delayed' THEN 1 ELSE 0 END) AS on_time_count
FROM Flight
WHERE airline_name = ?
  AND departure_time >= NOW()
```

**Why these matter**:
- Help airlines identify VIP customers for loyalty programs.
- Provide operational insight (are delays increasing?).
- Demonstrates advanced SQL (`CASE`, `GROUP BY`, window functions implicitly).

---

## Performance Optimizations

### What is Database Performance?

As databases grow, queries can become slow. A query that takes 0.1 seconds with 100 rows might take 10 seconds with 1 million rows. Performance optimization makes systems fast even with large amounts of data.

### Index Strategy

**What is an index?**
An index is like the index at the back of a book. Instead of reading every page to find a topic, you look it up in the index and go directly to the right page.

**Index on `Flight(departure_time, status)`**:
- **Workload**: Public flight search filters by `departure_time >= NOW()` and `status IN ('upcoming', 'delayed')`.
- **Without index**: Full table scan of `Flight` table.
- **With index**: Seek to the first matching `departure_time`, then filter by `status`. ~100x faster for large tables.

**Index on `Flight(departure_airport, arrival_airport, departure_time)`**:
- **Workload**: Route-specific searches (e.g., "New York to Boston on May 15").
- **Covers**: All three filter columns, so the database can satisfy the query without reading the main table (index-only scan).

**Index on `Purchases(customer_email, purchase_date)`**:
- **Workload**: Customer dashboard shows recent bookings filtered by date window.
- **Without index**: Must scan all 1M purchases to find this customer's bookings.
- **With index**: Seek to the customer's email, then range scan by date.

**Index on `AuthorizedBy(airline_name, booking_agent_email)`**:
- **Workload**: Checking which agents are authorized to sell for an airline.
- **Used in**: Booking agent login to pre-filter searchable flights, agent authorization check before booking.

### Index Trade-offs

| Aspect | Decision | Benefit | Cost |
|--------|----------|---------|------|
| **Number of indexes** | 7 indexes (covering main query patterns) | Faster searches, dashboards, analytics | Slower writes (inserts, updates hit all relevant indexes) |
| **Composite vs. single** | Use composite indexes (e.g., `(departure_time, status)`) instead of single-column | Reduce index size, enable index-only scans | More specific; don't help different query patterns |
| **Covering indexes** | Some indexes include all columns needed for a query | Avoid reading main table; faster | More disk space; tricky to maintain if schema changes |

### Query Performance Estimation

**Scenario**: 1M flights, 10M tickets, 100K customers

| Query | Without Index | With Index | Speed-up |
|-------|---------------|-----------|----------|
| `SELECT * FROM Flight WHERE departure_time >= ? AND status = 'upcoming'` | Full scan: 1M rows, ~500ms | Index seek + filter: ~50 rows, ~5ms | 100x |
| `SELECT * FROM Purchases WHERE customer_email = ? AND purchase_date > ?` | Full scan: 10M rows, ~5000ms | Index seek: ~100 rows, ~10ms | 500x |
| `SELECT * FROM Ticket WHERE flight_num = ? AND seat_class = ?` | Full scan: 10M rows, ~5000ms | Index seek: ~200 rows, ~5ms | 1000x |

---

## Integrity Mechanisms

### What is Data Integrity?

Data integrity means your data stays accurate and consistent. If you have a flight from New York to Boston, you don't want the system to accidentally create a flight from New York to New York.

### Database-Level Constraints

**CHECK constraint on `Flight.status`**:
```sql
CHECK (status IN ('upcoming', 'in-progress', 'delayed'))
```
- Prevents invalid status values (e.g., 'cancelled') from being inserted, even if the app layer makes a mistake.

**FOREIGN KEY constraints with CASCADE**:
```sql
FOREIGN KEY (airline_name) REFERENCES Airline(name) ON DELETE CASCADE
```
- If an airline is deleted, all its flights, airplanes, staff are automatically deleted.
- Maintains referential integrity without manual cleanup.

### Triggers for Complex Validation

**What is a trigger?**
A trigger is like an automatic rule that runs when data changes. "When someone inserts a flight, automatically check if the departure and arrival times make sense."

**Trigger: `validate_flight_insert` and `validate_flight_update`**

```sql
CREATE TRIGGER validate_flight_insert
BEFORE INSERT ON Flight
FOR EACH ROW
BEGIN
    IF NEW.departure_airport = NEW.arrival_airport THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Departure and arrival airports must differ.';
    END IF;

    IF NEW.arrival_time <= NEW.departure_time THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Arrival time must be later than departure time.';
    END IF;
END
```

**Why triggers?**
- **Data integrity**: Even if a future developer forgets to validate in the app, the database will reject invalid flights.
- **Bypasses front-end**: Works for direct SQL queries, not just app-mediated inserts.
- **Single source of truth**: One place to define business rules, not repeated in app code.

**Trigger: `enforce_ticket_capacity`**

```sql
CREATE TRIGGER enforce_ticket_capacity
BEFORE INSERT ON Ticket
FOR EACH ROW
BEGIN
    DECLARE seat_capacity INT DEFAULT NULL;
    DECLARE booked_count INT DEFAULT 0;

    SELECT capacity
    INTO seat_capacity
    FROM SeatClass
    WHERE airplane_id = NEW.airplane_id
      AND seat_class = NEW.seat_class;

    SELECT COUNT(*)
    INTO booked_count
    FROM Ticket
    WHERE flight_num = NEW.flight_num
      AND seat_class = NEW.seat_class;

    IF booked_count >= seat_capacity THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Seat capacity has been reached for this class.';
    END IF;
END
```

**Why this?**
- **Defense-in-depth**: Even if the app-side transaction lock fails, the database trigger prevents overselling.
- **Safety net**: New code paths (e.g., batch API for bulk bookings) won't accidentally oversell.

### Trigger Trade-offs

| Aspect | Pro | Con |
|--------|-----|-----|
| **Debugging** | Logic is centralized in the database | Harder to debug; errors are SQL, not Python stack traces |
| **Performance** | Prevents invalid inserts early | Trigger logic adds overhead to inserts (but prevents costly rollbacks) |
| **Testability** | Can test in SQL directly | Requires database running; harder to mock |
| **Maintenance** | Single source of truth | Requires SQL expertise; not all developers know trigger syntax |

---

## Role-Based Access Control

### What is Role-Based Access Control (RBAC)?

RBAC is a security system where users are assigned roles, and roles have permissions. Instead of giving each user individual permissions, you group permissions by job function.

**Example**: 
- **Customer role**: Can book flights, view bookings, see spending
- **Booking agent role**: Can book on behalf of customers, view commissions
- **Airline staff role**: Can manage flights, view analytics

### Three Roles: Customer, Booking Agent, Airline Staff

**Customer**:
- Can search flights and book them.
- Can view their past and upcoming bookings.
- Can see spending analytics.
- Can save flights for later.

**Booking Agent**:
- Can search flights, but only for authorized airlines.
- Can book flights on behalf of customers.
- Can view their own sales and commission analytics.
- Cannot add flights or manage airplanes.

**Airline Staff**:
- **Admin**: Can add airports, airplanes, flights, authorize agents.
- **Operator**: Can only update flight status (e.g., mark as delayed).

### Permission Separation Logic

**At login time**:
```python
# Staff login
cursor.execute("SELECT * FROM AirlineStaff WHERE username = %s", (username,))
staff = cursor.fetchone()

if staff and verify_password(staff['password'], provided_password):
    # Load permissions
    cursor.execute("SELECT permission FROM StaffPermission WHERE username = %s", (username,))
    permissions = [row['permission'] for row in cursor.fetchall()]
    
    login_user(
        role='airline_staff',
        identity=username,
        display_name=f"{staff['first_name']} {staff['last_name']}",
        airline=staff['airline_name'],
        permissions=permissions
    )
    return redirect(url_for('staff_portal'))
```

**At request time**:
```python
@permission_required('admin')
def add_flight():
    # Only staff with 'admin' permission can reach here
    # If session['permissions'] doesn't include 'admin', abort(403)
    ...

@permission_required('operator')
def update_flight_status():
    # Only staff with 'operator' permission can reach here
    ...
```

### Authorization Trade-offs

| Approach | Decision | Benefit | Cost |
|----------|----------|---------|------|
| **Session-based permissions** | Load permissions at login | Fast per-request checks (no DB query) | Permissions are stale if changed during session |
| **Database-based permissions** | Query DB on every protected request | Always current permissions | Slower (extra DB query per request); can be optimized with caching |
| **Fine-grained RBAC** | Implemented in this system | Clear separation of concerns | More tables (`StaffPermission`) and logic |

---

## UI/UX Design Decisions

### What is UI/UX?

**UI (User Interface)**: How the website looks and what buttons/forms are available.

**UX (User Experience)**: How easy and pleasant it is to use the website.

### Customer Portal Redesign (May 2, 2026)

**Problem addressed**: The original customer portal displayed verbose educational content about trip filtering and analytics, forcing users to scroll past marketing copy before accessing core features.

**Design logic**:
1. **Action-first layout**: Flight search form prominently displayed immediately after login.
2. **Progressive disclosure**: Booking history and analytics remain available but below the fold.
3. **Minimize friction**: User logs in → immediately sees "Where to?" search box → books or saves flight.

**Before vs. After**:

**Before** (multi-section with explanations):
```
Hero: "Customer Dashboard"
Subtitle: "Review trips, filter bookings, and inspect spending trends."
[Long paragraph explaining the system]
[Trip filters form spanning 40+ lines]
[Spending analytics section]
```

**After** (action-centric):
```
Hero: "Search and book flights"
[Quick flight search: From | To | Date | [Search] button]
[Booking history and analytics below]
```

**Why this matters**:
- **Conversion**: Users are more likely to complete an action if it's immediately visible.
- **Cognitive load**: Reduces decision paralysis; clear next step.
- **Mobile-friendly**: Responsive design; key action fits above the fold on small screens.

### Trade-off: Feature discoverability vs. simplicity

| Aspect | Decision | Benefit | Cost |
|--------|----------|---------|------|
| **Visible filters** | Collapsed under "Advanced Filters" or side panel | Uncluttered; fast for typical searches | Power users must click to access options |
| **Analytics graphs** | CSS-based bars (no Chart.js, D3) | Lightweight; no external JS dependency | Less interactive (no hover tooltips); harder to add complex visualizations later |
| **Navigation** | Top bar with role-aware menu | Consistent across all pages | Uses screen real estate; fixed position on mobile |

---

## Feature Logic Walkthrough

This section is the quick "how the code works" map for defense questions. The app keeps most business logic in `flask_demo/Part2/app.py`, while Jinja templates render forms, tables, buttons, and flash messages.

### Public Homepage and Search

**Routes**: `/`, `/flights`, `/flight/<flight_num>`

**Logic**:
1. `/` loads reference data from `Airport` and `Airline`, then calls `get_public_flights()` for a small featured list.
2. `/flights` reads structured query parameters such as departure airport, arrival city, date, and airline.
3. `collect_flight_filters()` normalizes airport and flight inputs, validates dates, and rejects same-airport trips.
4. `get_public_flights()` builds a parameterized SQL query that only returns flights with `departure_time >= NOW()` and status `upcoming` or `delayed`.
5. If a booking agent is logged in, the search adds an airline restriction based on `session["authorized_airlines"]`.
6. `/flight/<flight_num>` loads one flight, joins airport city names, loads all seat classes for the airplane, calculates remaining seats, and shows the booking form only when the logged-in role is allowed to book.

**Defense answer**: Search is dynamic but safe because only validated filters are appended, and all user values are still passed as SQL parameters.

### Public Flight Status Lookup

**Route**: `/status`

**Logic**:
1. User selects an airline and enters a flight number.
2. The route validates the airline against the database list and validates the flight-number format.
3. SQL joins `Flight` with both airport rows, but filters to `f.status = 'in-progress'`.
4. If no row matches, the app flashes a clear error instead of showing stale or unrelated flights.

**Defense answer**: This matches the rubric requirement for checking active flight status by airline and flight number.

### Registration

**Route**: `/register`

**Logic**:
1. The form supports three roles: customer, booking agent, and airline staff.
2. Passwords are validated for length and confirmation, then stored with `hash_password()`.
3. Customers require email and name, with optional phone/passport/city fields.
4. Booking agents require only email and password.
5. Staff require username, first name, last name, airline, date of birth, and at least one valid permission.
6. Staff permissions are inserted into `StaffPermission` in the same transaction as the staff account.
7. On success, `login_user()` immediately creates the correct session.

**Defense answer**: Separate registration branches preserve role-specific constraints while sharing validation and password hashing helpers.

### Role Portals

**Routes**: `/home`, `/customer`, `/agent`, `/staff`

**Logic**:
1. `/home` is a router: customer goes to `/customer`, booking agent to `/agent`, staff to `/staff`.
2. `/customer` queries the current customer's purchases, joins ticket and flight data, supports upcoming/past filtering, route filtering, date filtering, and spending analytics.
3. `/agent` queries purchases where `Purchases.booking_agent_email` matches the session agent, then calculates 30-day commission metrics and top customers.
4. `/staff` restricts operational data to `session["airline_name"]`, shows next-30-day flights, supports passenger lookup by flight, customer flight lookup, and airline analytics.

**Defense answer**: Every dashboard starts from session identity, so users only see records connected to their own customer email, agent email, or airline.

### Booking Tickets

**Route**: `POST /book`

**Logic**:
1. Only customers and booking agents can access the route.
2. The route validates `flight_num` and `seat_class`.
3. Customers book for their own `session["customer_email"]`; agents must provide a valid customer email.
4. The database transaction starts before checking availability.
5. The `Flight` row is selected `FOR UPDATE`, locking the flight while the booking is checked.
6. The selected `SeatClass` row is also selected `FOR UPDATE`.
7. The code counts existing `Ticket` rows for that flight and seat class.
8. If capacity remains, the app calculates the class price with `calculate_ticket_price()`, inserts a `Ticket`, then inserts the matching `Purchases` row.
9. `commit()` confirms both rows together; any exception triggers `rollback()`.

**Defense answer**: The booking feature is safe because it uses transactions, row locks, app-side capacity checks, and a database trigger as backup.

### Staff Admin Actions

**Routes**: `POST /staff/airport`, `POST /staff/airplane`, `POST /staff/flight`, `POST /staff/authorize-agent`

**Logic**:
1. All four routes use `@permission_required("admin")`.
2. Adding an airport validates airport code and city, then checks uniqueness before insert.
3. Adding an airplane validates capacities, requires at least one nonzero seat class, inserts the airplane, then inserts each offered seat class inside one transaction.
4. Creating a flight validates route, times, price, status, and verifies the airplane belongs to the staff member's airline.
5. Authorizing an agent checks the booking agent exists and that the `AuthorizedBy` relationship is not already present.

**Defense answer**: Admin routes are protected twice: by Flask permission checks and by database foreign keys/constraints.

### Staff Operator Action

**Route**: `POST /staff/status`

**Logic**:
1. Only staff with the `operator` permission can reach the route.
2. The route validates flight number and status.
3. It verifies the flight belongs to the staff user's airline.
4. It updates `Flight.status` to one of `upcoming`, `in-progress`, or `delayed`.

**Defense answer**: Operators can update operational state but cannot create airports, airplanes, flights, or agent authorizations.

---

## Bonus Feature: Saved Flights

### What and Why

**Feature**: Logged-in customers can save upcoming flights for later reference or booking.

**Use case**: Customer sees a flight they like but doesn't want to book immediately. They save it, browse other flights, then later decide to book from their "Saved Flights" page.

**Why included**:
- **Real-world relevance**: Expedia, Kayak, and airline websites all have "Save for later" features.
- **Database depth**: Adds another table (`SavedFlight`), another many-to-many relationship, and another feature to walk through in the demo.
- **Time-boxed scope**: Small feature that doesn't bloat the main application.

### Implementation

**Table**:
```sql
CREATE TABLE SavedFlight (
    customer_email VARCHAR(100) NOT NULL,
    flight_num VARCHAR(10) NOT NULL,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (customer_email, flight_num),
    FOREIGN KEY (customer_email) REFERENCES Customer(email) ON DELETE CASCADE,
    FOREIGN KEY (flight_num) REFERENCES Flight(flight_num) ON DELETE CASCADE
);
```

**Endpoints**:
- `POST /saved-flights/save/<flight_num>`: Insert row into `SavedFlight`
- `GET /saved-flights`: Query `SavedFlight JOIN Flight JOIN Airport` for current user
- `POST /saved-flights/remove/<flight_num>`: Delete row from `SavedFlight`

### Saved and Removed Flight Logic

**Save logic**:
1. `@roles_required("customer")` ensures only logged-in customers can save flights.
2. `validate_flight_num()` normalizes and validates the URL flight number.
3. The route checks that the flight exists and has not departed: `departure_time >= NOW()`.
4. It inserts `(customer_email, flight_num)` into `SavedFlight`.
5. The composite primary key blocks duplicates. If MySQL raises an integrity error, the app flashes "This flight is already saved."

**View logic**:
1. `/saved-flights` reads `session["customer_email"]`.
2. SQL joins `SavedFlight` to `Flight` and both airport records.
3. Results are ordered by `saved_at DESC`, so most recently saved flights appear first.

**Remove logic**:
1. `POST /saved-flights/remove/<flight_num>` validates the flight number.
2. SQL deletes only where both `customer_email` and `flight_num` match.
3. `cursor.rowcount` tells the app whether a row was actually removed.
4. The customer is redirected back to the saved flights page.

**Defense answer**: Removing a saved flight does not delete the real flight. It only deletes the customer's bookmark row from `SavedFlight`.

**Constraints**:
- Composite primary key `(customer_email, flight_num)` ensures no duplicate saves.
- `ON DELETE CASCADE` on `customer_email` and `flight_num` ensures cleanup (e.g., if customer deletes their account).

### Trade-offs

| Aspect | Decision | Benefit | Cost |
|--------|----------|---------|------|
| **Timestamp tracking** | `saved_at` is recorded | Can sort by recency; audit trail | Extra column; slightly more storage |
| **No user annotations** | No "notes" or tags column | Simpler schema | Users can't personalize saved flights (e.g., "cheap option", "quick flight") |
| **Soft limit on saves** | No limit (DB doesn't enforce max) | Users can save as many as they want | Could cause storage bloat; real systems often limit to 100 saves per user |

---

## Customer Booking Cancellation

### What and Why

**Feature**: Logged-in customers can cancel their own future bookings from the customer portal.

**Use case**: A customer books a ticket, changes plans before departure, and removes that booking so the ticket no longer appears in their purchase list.

### Implementation

**Route**:
- `POST /cancel_booking/<ticket_id>`: cancel one ticket belonging to the current logged-in customer.

**Template integration**:
- `templates/customer_portal.html` shows a Cancel button beside each booking.
- The button uses a browser confirmation dialog to reduce accidental cancellations.

### Cancellation Logic

1. The route receives `ticket_id` from the URL.
2. It reads the current customer from `session["customer_email"]`.
3. SQL joins `Purchases`, `Ticket`, and `Flight` to verify both ownership and departure time:
   - `Purchases.ticket_id = ticket_id`
   - `Purchases.customer_email = current customer`
4. If no row is found, the app flashes a permission/not-found error. This prevents one customer from cancelling another customer's booking.
5. If `departure_time <= datetime.now()`, the app refuses cancellation because the flight has already departed.
6. Otherwise, it runs the cancellation inside the active database transaction.
7. It explicitly deletes from `Purchases` using both `ticket_id` and `customer_email`, which removes the customer-booking link.
8. It then deletes the related `Ticket` row, which frees the seat because future capacity checks count rows in `Ticket`.
9. The route commits and redirects back to `/customer`. If a database error occurs, it rolls back so the system does not end up with a half-cancelled booking.

### Trade-offs

| Aspect | Decision | Benefit | Cost |
|--------|----------|---------|------|
| **Customer-only cancellation** | Uses current customer session | Prevents unauthorized cancellations | Booking agents cannot cancel on behalf of customers |
| **Future flights only** | Blocks cancellation after departure time | Avoids inconsistent travel history | No refund/dispute workflow for past flights |
| **Hard delete from `Purchases` and `Ticket`** | Removes booking and frees seat capacity | Simple demo behavior | No cancellation audit trail unless added later |

**Defense answer**: Cancellation is protected by ownership checks and time checks. It is intentionally simpler than a production refund system, but it demonstrates secure delete logic and session-based authorization.

---

## Known Limitations & Future Improvements

### Current Limitations

1. **In-memory sessions**: Sessions are stored in Flask's in-memory store. For production, need Redis or Memcached. For multiple servers, need distributed session storage.
   - *Workaround*: Use `SESSION_TYPE='filesystem'` for persistence to disk, or `SESSION_TYPE='sqlalchemy'` for database-backed sessions.

2. **No pagination for large datasets**: If a customer has 10,000 bookings, loading all at once is slow.
   - *Improvement*: Add `LIMIT 50 OFFSET ?` to queries, implement "Next" / "Previous" buttons on the frontend.

3. **No email notifications**: When a booking is confirmed, the system doesn't send a confirmation email.
   - *Improvement*: Use `smtplib` or a service like SendGrid to send transactional emails.

4. **Hardcoded commission rate**: 10% is coded in Python. Airlines with different agent tiers have different rates.
   - *Improvement*: Add a `CommissionTier` table, link agents to tiers, query the tier rate at booking time.

5. **Cancellation is implemented, but refund/audit history is limited**: Customers can cancel future bookings, but the system does not calculate refund amounts or preserve a cancellation ledger.
   - *Improvement*: Add a `Cancellation` or `Refund` table, store cancellation timestamp, refund amount, reason, and staff/agent reviewer if applicable.

6. **Single currency (USD assumed)**: Prices are stored as DECIMAL but no currency column.
   - *Improvement*: Add a `currency` column to `Flight`, implement currency conversion at display time.

7. **No seat selection**: All seats in a class are identical; customers can't choose aisle vs. window.
   - *Improvement*: Add a `Seat` table mapping `(airplane_id, seat_number, seat_class)`, allow customers to choose during booking.

### Future Improvements (Priority Order)

**High Priority**:
- [ ] Pagination for large result sets (bookings, search results).
- [ ] Error logging and monitoring (Sentry, DataDog).
- [ ] Email confirmations for bookings and account changes.

**Medium Priority**:
- [ ] Refund calculation and cancellation audit history.
- [ ] Multi-currency support.
- [ ] Real-time seat selection UI.
- [ ] Two-factor authentication for staff accounts.

**Low Priority**:
- [ ] Wishlist/price alert feature ("Notify me if this flight drops below $200").
- [ ] Social features ("Invite friends to book together").
- [ ] ML-based price prediction ("Book now or wait?").

---

## Demo Walkthrough Tips

### What You'll Need

1. **Database**: MySQL running with the schema initialized (`python init_db.py`).
2. **Flask app**: Running on `http://127.0.0.1:5000`.
3. **Browser**: Any modern browser (Chrome, Safari, Firefox).
4. **Demo credentials** (all passwords are `password123` except where noted):
   - **Customer**: `alice@example.com` (or any test customer)
   - **Booking Agent**: `agent1@travel.com`
   - **Airline Staff (Admin)**: `staff_skyjet` (airline: SkyJet)
   - **Airline Staff (Operator)**: `staff_op1` (airline: SkyJet)

### Suggested Flow

#### 1. Public Features (5 minutes)
- Navigate to homepage (no login required).
- Search for flights with various filters (city, airport, date, airline).
- Look up in-progress flight status using airline + flight number.
- *Emphasize*: Dynamic query building, parameterized inputs, no hardcoded filters.

#### 2. Customer Journey (10 minutes)
- Register a new customer account.
  - *Emphasize*: Password hashing, email validation, address/passport fields.
- Log in with the new account.
- Search for and view flight details.
- **Save a flight** (bonus feature).
  - View saved flights.
  - Remove a saved flight.
- Book a flight.
  - *Emphasize*: Transaction-safe booking, seat availability checks, transaction locks.
  - Show seat class pricing multiplier (economy, business, first).
- View booking history with date range filters.
- View spending analytics (default 12-month and 6-month chart).
- Access custom analytics (pick a date range and see custom totals and chart).

#### 3. Booking Agent Journey (10 minutes)
- Register a new booking agent.
  - *Emphasize*: Separate user table from customers, different required fields.
- Log in as the agent.
  - *Emphasize*: Session contains authorized airlines list.
- Search flights (show that results are restricted to authorized airlines).
- Book a flight on behalf of a customer (another email address).
  - *Emphasize*: Authorization check, customer email validation, agent-airline relationship checked at DB level.
- View sales history by customer.
- View commission analytics (30-day window, commission rate).
- View top customers by ticket count and commission earned.

#### 4. Airline Staff: Admin (10 minutes)
- Log in as staff admin (e.g., `staff_skyjet`).
- View operational dashboard (flights in next 30 days).
- Add a new airport.
  - *Emphasize*: Form validation, uniqueness check in DB, error handling.
- Add a new airplane with seat classes.
  - *Emphasize*: Seat class capacity, transaction to insert airplane and multiple seat classes.
- Create a new flight.
  - *Emphasize*: Validation that airplane is owned by the airline, route is valid (different departure/arrival), times are logical.
  - Trigger validation in action: Try to create a flight with same departure/arrival airport → see error from trigger.
- Authorize a booking agent to sell your airline's flights.
  - *Emphasize*: Authorization check, `AuthorizedBy` table relationship.

#### 5. Airline Staff: Operator (8 minutes)
- Log in as staff operator.
- View flights in next 30 days (should see fewer menu items than admin).
- Update flight status (mark a flight as delayed).
  - *Emphasize*: Permission-based access control, operator can only update status, not create flights.
- View passenger list for a flight.
  - *Emphasize*: JOINs across Purchases, Ticket, Customer, Flight.

#### 6. Airline Staff: Analytics (10 minutes)
- View top destinations (3-month and 1-year windows).
- View top booking agents (by ticket count and commission).
- View most frequent customer.
- View delay vs. on-time stats.
- View tickets sold per month (bar chart).
- *Emphasize*: GROUP BY, aggregation functions, date filtering, multi-table JOINs.

#### 7. Technical Q&A (remaining time)
Prepare to explain:
- **Transaction safety**: Why `SELECT ... FOR UPDATE` prevents overbooking.
- **Indexing strategy**: Which queries are slow without indexes, how indexes help.
- **Security**: Why passwords are hashed, why parameterized queries matter.
- **Triggers**: When and why they fire; defense-in-depth concept.
- **Role separation**: Why separate user tables, how session permissions work.

### Red Flags to Avoid

- **Don't manually edit the database** during the demo. If something breaks, restart the app and reinitialize the DB.
- **Don't claim live production readiness**. Acknowledge limitations (in-memory sessions, no email, no pagination).
- **Don't get lost in error states**. Test error paths before the demo (e.g., overbooking, invalid passwords, unauthorized access).
- **Don't ignore the bonus feature**. Spending 30 seconds on "Saved Flights" shows you went beyond the rubric.

### Talking Points During Demo

1. **Schema design**: "We have 3 separate user tables for different roles to avoid NULL columns and keep constraints clear."
2. **Transactions**: "When a customer books, we lock the flight row and seat class row to ensure no two bookings race."
3. **Indexes**: "Without indexes, customer dashboards would scan millions of purchases. With indexes on customer_email and purchase_date, it's instant."
4. **Triggers**: "Even if our app layer has a bug, the database trigger prevents overselling and invalid flight schedules."
5. **Role-based access**: "Operators can't create flights; admins can't update status. Permissions are checked in the session and enforced in the database via foreign keys."

---

## Summary: What Makes This System Defensible

1. **Normalization**: 3NF schema with clear entity relationships and minimal redundancy.
2. **Transactional integrity**: Bookings use locks and transactions to prevent overbooking.
3. **Security**: Passwords hashed, parameterized queries, session-based authorization, CSRF protection.
4. **Performance**: 7 strategic indexes covering main query patterns (search, dashboards, analytics).
5. **Data integrity**: Triggers enforce business rules at the database layer.
6. **Role-based design**: Three user roles with separate tables, permissions, and dashboards showcase authorization and multi-table queries.
7. **Real-world relevance**: Mirrors actual airline reservation systems (Expedia, Kayak, airline-native).
8. **Feature depth**: Main features (search, book, analytics) + bonus (saved flights) show completeness.
9. **Code clarity**: Clean Python with helper functions, meaningful variable names, SQL in docstrings.

---

## References & Further Reading

- **ACID transactions**: [MySQL documentation on transactions](https://dev.mysql.com/doc/refman/8.0/en/commit.html)
- **Row-level locking**: [MySQL SELECT ... FOR UPDATE](https://dev.mysql.com/doc/refman/8.0/en/innodb-locking-reads.html)
- **Database triggers**: [MySQL CREATE TRIGGER](https://dev.mysql.com/doc/refman/8.0/en/create-trigger.html)
- **Indexing strategies**: [B+ tree indexes](https://en.wikipedia.org/wiki/B%2B_tree) and [composite indexes](https://dev.mysql.com/doc/refman/8.0/en/multiple-column-indexes.html)
- **Password hashing**: [OWASP password storage cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- **Flask security**: [OWASP Top 10 Web Application Security Risks](https://owasp.org/www-project-top-ten/)

---

## Appendix: Quick Reference - Key Files

| File | Purpose | Key Content |
|------|---------|-------------|
| `app.py` | Main Flask application | Routes, business logic, password hashing, transaction handling |
| `create_tables.sql` | Database schema | 11 tables, 7 indexes, 3 triggers, check constraints |
| `insert_data.sql` | Sample data | Test records for all roles and airlines |
| `FEATURE_QUERY_MAP.md` | Feature-to-SQL mapping | What SQL each feature uses |
| `System_Optimization_Proposals.md` | Design rationale | 6 optimization proposals with trade-offs and references |
| `templates/base.html` | Layout template | Shared CSS, navigation, alerts |
| `templates/customer_portal.html` | Customer dashboard | Search form + analytics + booking history |
| `templates/agent_portal.html` | Booking agent dashboard | Sales and commission analytics |
| `templates/staff_portal.html` | Staff dashboard | Operations, analytics, admin/operator actions |

---

**Good luck with your defense! Remember to breathe, speak clearly, and if you don't know an answer, it's OK to say "That's a great question; let me think about that" or "In the interest of time, let me move on, but I'm happy to follow up after."**
