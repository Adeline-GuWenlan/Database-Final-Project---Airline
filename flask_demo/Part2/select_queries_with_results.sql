-- Representative queries used by the refined Part 3 application

-- 1. Public search for upcoming flights
SELECT
    f.flight_num,
    f.airline_name,
    f.departure_airport,
    dep.city AS departure_city,
    f.arrival_airport,
    arr.city AS arrival_city,
    f.departure_time,
    f.price,
    f.status
FROM Flight f
JOIN Airport dep ON dep.name = f.departure_airport
JOIN Airport arr ON arr.name = f.arrival_airport
WHERE f.departure_time >= NOW()
  AND f.status IN ('upcoming', 'delayed')
ORDER BY f.departure_time, f.flight_num;

-- 2. Public lookup for an in-progress flight
SELECT
    f.flight_num,
    f.airline_name,
    f.status,
    f.departure_time,
    f.arrival_time
FROM Flight f
WHERE f.airline_name = 'SkyJet'
  AND f.flight_num = 'SJ104'
  AND f.status = 'in-progress';

-- 3. Customer spending total over the last 12 months
SELECT COALESCE(SUM(t.price_charged), 0) AS total_spending
FROM Purchases p
JOIN Ticket t ON t.ticket_id = p.ticket_id
WHERE p.customer_email = 'alice@example.com'
  AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH);

-- 4. Booking-agent commission analytics over the last 30 days
SELECT
    COUNT(*) AS tickets_sold,
    COALESCE(SUM(t.price_charged * 0.10), 0) AS total_commission,
    COALESCE(AVG(t.price_charged * 0.10), 0) AS avg_commission
FROM Purchases p
JOIN Ticket t ON t.ticket_id = p.ticket_id
WHERE p.booking_agent_email = 'agent1@travel.com'
  AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY);

-- 5. Airline-staff view of the next 30 days of flights
SELECT
    f.flight_num,
    f.departure_time,
    f.arrival_time,
    f.status,
    f.departure_airport,
    f.arrival_airport
FROM Flight f
WHERE f.airline_name = 'SkyJet'
  AND f.departure_time >= NOW()
  AND f.departure_time <= DATE_ADD(NOW(), INTERVAL 30 DAY)
ORDER BY f.departure_time, f.flight_num;

-- 6. Stored procedure used for customer or agent ticket purchase
CALL purchase_ticket('SJ101', 'economy', 'bob@example.com', NULL);
