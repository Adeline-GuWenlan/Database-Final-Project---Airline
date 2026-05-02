-- Sample dataset aligned with the refined Part 3 application
-- Demo passwords:
--   Customers: password123
--   Booking agent: agentpass
--   Admin staff: adminpass
--   Regular staff: staffpass

INSERT INTO Airline (name) VALUES
    ('SkyJet'),
    ('AirAsia'),
    ('Delta');

INSERT INTO Airport (name, city) VALUES
    ('JFK', 'New York'),
    ('LAX', 'Los Angeles'),
    ('PVG', 'Shanghai'),
    ('NRT', 'Tokyo'),
    ('LHR', 'London'),
    ('SFO', 'San Francisco');

INSERT INTO Airplane (id, airline_name) VALUES
    (1, 'SkyJet'),
    (2, 'AirAsia'),
    (3, 'Delta'),
    (4, 'SkyJet'),
    (5, 'SkyJet');

INSERT INTO SeatClass (airplane_id, seat_class, capacity) VALUES
    (1, 'economy', 150),
    (1, 'business', 30),
    (1, 'first', 10),
    (2, 'economy', 200),
    (2, 'business', 40),
    (3, 'economy', 180),
    (3, 'business', 35),
    (3, 'first', 15),
    (4, 'economy', 120),
    (4, 'business', 25),
    (5, 'economy', 1);

INSERT INTO Flight (
    flight_num, departure_time, arrival_time, price, status,
    airline_name, airplane_id, departure_airport, arrival_airport
) VALUES
    ('SJ101', '2026-05-15 08:00:00', '2026-05-15 11:30:00', 299.00, 'upcoming', 'SkyJet', 1, 'JFK', 'LAX'),
    ('SJ102', '2026-05-16 14:00:00', '2026-05-17 06:00:00', 899.00, 'upcoming', 'SkyJet', 1, 'JFK', 'PVG'),
    ('SJ103', '2026-05-17 10:00:00', '2026-05-17 13:30:00', 320.00, 'upcoming', 'SkyJet', 4, 'LAX', 'SFO'),
    ('SJ900', '2026-05-12 12:00:00', '2026-05-12 15:00:00', 199.00, 'upcoming', 'SkyJet', 5, 'JFK', 'SFO'),
    ('AA201', '2026-05-15 09:00:00', '2026-05-15 22:00:00', 750.00, 'upcoming', 'AirAsia', 2, 'LAX', 'NRT'),
    ('AA202', '2026-05-18 11:00:00', '2026-05-19 05:00:00', 680.00, 'upcoming', 'AirAsia', 2, 'NRT', 'PVG'),
    ('DL301', '2026-05-16 07:00:00', '2026-05-16 15:00:00', 550.00, 'upcoming', 'Delta', 3, 'JFK', 'LHR'),
    ('DL302', '2026-05-20 16:00:00', '2026-05-20 19:30:00', 275.00, 'upcoming', 'Delta', 3, 'LAX', 'JFK'),
    ('SJ104', '2026-04-30 09:00:00', '2026-04-30 13:00:00', 310.00, 'in-progress', 'SkyJet', 1, 'SFO', 'JFK'),
    ('AA203', '2026-05-13 10:00:00', '2026-05-13 14:00:00', 420.00, 'delayed', 'AirAsia', 2, 'PVG', 'NRT');

INSERT INTO Customer (
    email, name, password, city, phone_number,
    passport_number, passport_country, date_of_birth
) VALUES
    ('alice@example.com', 'Alice Chen', 'pbkdf2_sha256$260000$alice$ffe4b974dd6aea3275eb4515035bf6dc3c4a5ec84cbe1aba26ae9028ea03f691', 'New York', '212-555-0101', 'P123456', 'USA', '1990-06-15'),
    ('bob@example.com', 'Bob Li', 'pbkdf2_sha256$260000$bob$f245efe741ef3b22bc31593fdbdb9715c1e0b522430b9d75adfa10b992a9fcd1', 'Shanghai', '86-21-5555-0102', 'P789012', 'China', '1985-03-22');

INSERT INTO BookingAgent (email, password) VALUES
    ('agent1@travel.com', 'pbkdf2_sha256$260000$agent1$d07c0fd56102830ec5020c143c8a1e353bf21f4c9645ca4bdc81ab2dcb00616c');

INSERT INTO AirlineStaff (
    username, airline_name, password, first_name, last_name, date_of_birth
) VALUES
    ('admin_skyjet', 'SkyJet', 'pbkdf2_sha256$260000$admin_skyjet$244a53050b3ec59b0ad088824d2d541372b91d0ab15ec99884fb5c51167495dc', 'Avery', 'Admin', '1980-01-15'),
    ('staff_skyjet', 'SkyJet', 'pbkdf2_sha256$260000$staff_skyjet$0723042c3a0219fdc7bb149b7cc70623c813dc164e2d1145a2ce18b9f352c4d6', 'Sam', 'Staff', '1985-07-20');

INSERT INTO StaffPermission (username, permission) VALUES
    ('admin_skyjet', 'admin'),
    ('admin_skyjet', 'operator'),
    ('staff_skyjet', 'operator');

INSERT INTO Ticket (ticket_id, flight_num, seat_class, airplane_id, price_charged) VALUES
    (1, 'SJ101', 'economy', 1, 299.00),
    (2, 'SJ101', 'business', 1, 448.50),
    (3, 'SJ102', 'economy', 1, 899.00),
    (4, 'DL301', 'business', 3, 825.00),
    (5, 'SJ900', 'economy', 5, 199.00);

INSERT INTO Purchases (ticket_id, customer_email, booking_agent_email, purchase_date) VALUES
    (1, 'alice@example.com', NULL, '2026-03-01'),
    (2, 'bob@example.com', 'agent1@travel.com', '2026-03-05'),
    (3, 'alice@example.com', NULL, '2026-03-10'),
    (4, 'bob@example.com', NULL, '2026-03-15'),
    (5, 'alice@example.com', NULL, '2026-04-25');

INSERT INTO AuthorizedBy (booking_agent_email, airline_name) VALUES
    ('agent1@travel.com', 'SkyJet');
