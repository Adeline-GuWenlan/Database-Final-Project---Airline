# System Optimization Proposals

Note: I did not find a strong NYU or NYUSH public repository for this exact project shape, so the references below use other public database-course or database-focused airline projects on GitHub.

## 1. Role-Aware Session Authentication with Hashed Password Storage

- **Problem**:  
  The original prototype only supported customer login, stored passwords in plain text, and did not separate customer, booking-agent, and airline-staff permissions inside the session layer.

- **Implementation**:  
  Replace the customer-only login flow with a unified authentication flow that checks the correct table for each role, stores a server-side session containing `role`, `identity`, display name, airline, and permissions, and hashes passwords before insertion using PBKDF2-SHA256. On login, load booking-agent airline authorizations and staff permissions into the session so every protected route can validate access without relying on client-side assumptions.

- **Syllabus Alignment**:  
  This stays within a typical database-systems course because it uses basic authentication, server-side validation, session management, and relational lookups on authorization tables. It does not rely on advanced cryptography or external identity infrastructure.

- **Reference (if any)**:  
  [SyedMuhammadFaheem/AirOpsManager-AirlinesManagementSystem](https://github.com/SyedMuhammadFaheem/AirOpsManager-AirlinesManagementSystem) shows separate admin and customer panels in a database course project, which supports the idea of role-scoped views and permissions.  
  [Lakshan-Banneheke/Airline-Reservation-System](https://github.com/Lakshan-Banneheke/Airline-Reservation-System) models staff-facing and passenger-facing responsibilities in an airline reservation setting.

---

## 2. Structured Flight Search and Public Flight-Status Lookup

- **Problem**:  
  Free-form or under-constrained search inputs create ambiguous queries, weak validation, and a higher risk of incorrect or overly broad results. The Part 3 rubric also explicitly requires a public flight-status lookup for in-progress flights.

- **Implementation**:  
  Use guided search fields for departure airport, departure city, arrival airport, arrival city, departure date, and airline, then build parameterized SQL with only the selected predicates. Add a separate public status-lookup page that requires airline plus flight number and returns only `in-progress` flights. This improves usability and makes the generated SQL easier to explain during the check-off.

- **Syllabus Alignment**:  
  The implementation uses parameterized `SELECT` queries, joins with `Airport`, and ordinary filter predicates. This is directly aligned with SQL query design, input validation, and usability improvements inside a standard course scope.

- **Reference (if any)**:  
  [Lakshan-Banneheke/Airline-Reservation-System](https://github.com/Lakshan-Banneheke/Airline-Reservation-System) emphasizes search pages and schedule-driven booking flows, which is a useful pattern for structuring route and date input.  
  [amirashhf/sql-airline-database-project](https://github.com/amirashhf/sql-airline-database-project) highlights normalized flight, airport, seat, ticket, and booking entities that support structured querying cleanly.

---

## 3. Transaction-Safe Seat-Class Booking with Capacity Enforcement

- **Problem**:  
  A plain insert-based booking flow can oversell seats if two requests race at the same time, and it can also misprice tickets if seat-class logic is handled inconsistently.

- **Implementation**:  
  Wrap booking in a transaction. Lock the target `Flight` row and the relevant `SeatClass` row using `SELECT ... FOR UPDATE`, count already booked tickets in the chosen class, compute the seat-class-specific price multiplier on the server, then insert into `Ticket` and `Purchases` only if capacity remains. Add a database trigger on `Ticket` as a second line of defense so overselling is rejected even if a future code path forgets the application-layer check.

- **Syllabus Alignment**:  
  This is a direct application of transactions, isolation-aware updates, integrity constraints, and trigger usage. All of these are standard database-systems topics and fit the prompt’s request to include meaningful trigger-based ideas where relevant.

- **Reference (if any)**:  
  [Lakshan-Banneheke/Airline-Reservation-System](https://github.com/Lakshan-Banneheke/Airline-Reservation-System) explicitly discusses avoiding double assignment of seats and overbooking, which closely matches this refinement direction.  
  [SyedMuhammadFaheem/AirOpsManager-AirlinesManagementSystem](https://github.com/SyedMuhammadFaheem/AirOpsManager-AirlinesManagementSystem) includes role-specific booking workflows that motivate stronger booking integrity rules.

---

## 4. Query-Oriented Indexing for Search, Dashboards, and Analytics

- **Problem**:  
  Once the app grows beyond a few demo rows, repeated dashboard queries on flights, purchases, and authorizations will degrade because the database must scan large tables for every search, history view, or analytics panel.

- **Implementation**:  
  Add indexes that match the actual workload: `Flight(departure_time, status)` for public search windows, `Flight(departure_airport, arrival_airport, departure_time)` for route filtering, `Flight(airline_name, departure_time)` for staff operations, `Ticket(flight_num, seat_class)` for inventory checks, `Purchases(customer_email, purchase_date)` and `Purchases(booking_agent_email, purchase_date)` for customer and agent analytics, and `AuthorizedBy(airline_name, booking_agent_email)` for authorization checks. Document these indexes so they can be defended in the demo as read-performance trade-offs that slightly increase write overhead.

- **Syllabus Alignment**:  
  This is exactly the kind of B+ tree indexing analysis expected in an undergraduate database course: identify common predicates, choose composite indexes that support them, and explain the read/write trade-off.

- **Reference (if any)**:  
  [amirashhf/sql-airline-database-project](https://github.com/amirashhf/sql-airline-database-project) is a good reference point for normalized relational design that benefits from query-aware indexing.  
  [Lakshan-Banneheke/Airline-Reservation-System](https://github.com/Lakshan-Banneheke/Airline-Reservation-System) also explicitly mentions indexing where necessary in the database task description.

---

## 5. Analytics Views for Customers, Booking Agents, and Airline Staff

- **Problem**:  
  Without role-specific analytics, the application feels like a simple CRUD demo rather than a convincing reservation system. The rubric expects spending summaries, commission reports, and staff-facing operational insight.

- **Implementation**:  
  Add role-scoped aggregate queries: customer total spending over the last 12 months and month-by-month spending bars; booking-agent commission totals, average commission, and top customers by ticket count and commission; airline-staff reports for top agents, most frequent customer, ticket volume by month, delay vs. non-delay counts, and top destinations over 3-month and 1-year windows. Present the results as lightweight tables and CSS-based bar charts so the analytics are visible without needing external chart libraries.

- **Syllabus Alignment**:  
  These features use `JOIN`, `GROUP BY`, `COUNT`, `SUM`, `AVG`, date filters, and ordering. That is well within the SQL analytics expected in the syllabus and provides technical depth without over-engineering.

- **Reference (if any)**:  
  [amirashhf/sql-airline-database-project](https://github.com/amirashhf/sql-airline-database-project) showcases airline analytics such as revenue and average ticket price, which supports the use of grouped reporting in this app.  
  [SyedMuhammadFaheem/AirOpsManager-AirlinesManagementSystem](https://github.com/SyedMuhammadFaheem/AirOpsManager-AirlinesManagementSystem) demonstrates the value of separate customer and admin workflows, which maps naturally onto role-specific analytics.

---

## 6. Permission-Separated Staff Operations with Database Integrity Triggers

- **Problem**:  
  Staff actions such as adding airports, adding airplanes, creating flights, and changing flight status should not all be available to every employee. Separately, invalid flight schedules should not depend only on application code to be rejected.

- **Implementation**:  
  Use `StaffPermission` to distinguish `admin` from `operator`. Admin users can add airports, airplanes, flights, and booking-agent associations. Operators can update flight status. Add database triggers on `Flight` insert and update to reject schedules where departure and arrival airports are the same or arrival time is not later than departure time. This makes the airline-staff workflow defensible both in the Flask layer and in the database layer.

- **Syllabus Alignment**:  
  This uses basic role-based access control through relational tables plus simple triggers for integrity enforcement. Both ideas are standard course material and stay far away from advanced enterprise IAM or distributed security systems.

- **Reference (if any)**:  
  [SyedMuhammadFaheem/AirOpsManager-AirlinesManagementSystem](https://github.com/SyedMuhammadFaheem/AirOpsManager-AirlinesManagementSystem) includes a permissioned admin panel, which supports separating staff responsibilities.  
  [Lakshan-Banneheke/Airline-Reservation-System](https://github.com/Lakshan-Banneheke/Airline-Reservation-System) discusses procedures, functions, and triggers as part of the database design task, which makes it a strong conceptual reference for this optimization.
