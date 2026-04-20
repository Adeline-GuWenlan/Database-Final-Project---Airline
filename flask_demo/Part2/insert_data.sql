-- Sample dataset aligned with the refined Part 3 application
-- Demo passwords:
--   Customers: password123
--   Booking agent: agentpass
--   Airline staff: staffpass

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
    (4, 'SkyJet');

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
    (4, 'business', 25);

INSERT INTO Flight (
    flight_num, departure_time, arrival_time, price, status,
    airline_name, airplane_id, departure_airport, arrival_airport
) VALUES
    ('SJ101', '2026-04-15 08:00:00', '2026-04-15 11:30:00', 299.00, 'upcoming', 'SkyJet', 1, 'JFK', 'LAX'),
    ('SJ102', '2026-04-16 14:00:00', '2026-04-17 06:00:00', 899.00, 'upcoming', 'SkyJet', 1, 'JFK', 'PVG'),
    ('SJ103', '2026-04-17 10:00:00', '2026-04-17 13:30:00', 320.00, 'upcoming', 'SkyJet', 4, 'LAX', 'SFO'),
    ('AA201', '2026-04-15 09:00:00', '2026-04-15 22:00:00', 750.00, 'upcoming', 'AirAsia', 2, 'LAX', 'NRT'),
    ('AA202', '2026-04-18 11:00:00', '2026-04-19 05:00:00', 680.00, 'upcoming', 'AirAsia', 2, 'NRT', 'PVG'),
    ('DL301', '2026-04-16 07:00:00', '2026-04-16 15:00:00', 550.00, 'upcoming', 'Delta', 3, 'JFK', 'LHR'),
    ('DL302', '2026-04-20 16:00:00', '2026-04-20 19:30:00', 275.00, 'upcoming', 'Delta', 3, 'LAX', 'JFK'),
    ('SJ104', '2026-04-14 06:00:00', '2026-04-14 09:00:00', 310.00, 'in-progress', 'SkyJet', 1, 'SFO', 'JFK'),
    ('AA203', '2026-04-13 10:00:00', '2026-04-13 14:00:00', 420.00, 'delayed', 'AirAsia', 2, 'PVG', 'NRT');

INSERT INTO Customer (
    email, name, password, city, phone_number,
    passport_number, passport_country, date_of_birth
) VALUES
    ('alice@example.com', 'Alice Chen', 'pbkdf2_sha256$260000$alice$ffe4b974dd6aea3275eb4515035bf6dc3c4a5ec84cbe1aba26ae9028ea03f691', 'New York', '212-555-0101', 'P123456', 'USA', '1990-06-15'),
    ('bob@example.com', 'Bob Li', 'pbkdf2_sha256$260000$bob$f245efe741ef3b22bc31593fdbdb9715c1e0b522430b9d75adfa10b992a9fcd1', 'Shanghai', '86-21-5555-0102', 'P789012', 'China', '1985-03-22'),
    ('carol@example.com', 'Carol Johnson', 'pbkdf2_sha256$260000$carol$b47d899e263ad510c1121b2ba21895c009c620caa91ebaba3d22d7867e0f0662', 'Los Angeles', '310-555-0103', 'P345678', 'USA', '1992-11-08');

INSERT INTO BookingAgent (email, password) VALUES
    ('agent1@travel.com', 'pbkdf2_sha256$260000$agent1$d07c0fd56102830ec5020c143c8a1e353bf21f4c9645ca4bdc81ab2dcb00616c');

INSERT INTO AirlineStaff (
    username, airline_name, password, first_name, last_name, date_of_birth
) VALUES
    ('staff_skyjet', 'SkyJet', 'pbkdf2_sha256$260000$staff_skyjet$0723042c3a0219fdc7bb149b7cc70623c813dc164e2d1145a2ce18b9f352c4d6', 'John', 'Doe', '1980-01-15'),
    ('staff_airasia', 'AirAsia', 'pbkdf2_sha256$260000$staff_airasia$4a3e26ed7910abfa79265a478d82c82d21d4dcd3e6b01d0b3160f5cb11d9751f', 'Jane', 'Smith', '1985-07-20');

INSERT INTO StaffPermission (username, permission) VALUES
    ('staff_skyjet', 'admin'),
    ('staff_skyjet', 'operator'),
    ('staff_airasia', 'operator');

INSERT INTO Ticket (ticket_id, flight_num, seat_class, airplane_id, price_charged) VALUES
    (1, 'SJ101', 'economy', 1, 299.00),
    (2, 'SJ101', 'business', 1, 448.50),
    (3, 'SJ102', 'economy', 1, 899.00),
    (4, 'DL301', 'business', 3, 825.00);

INSERT INTO Purchases (ticket_id, customer_email, booking_agent_email, purchase_date) VALUES
    (1, 'alice@example.com', NULL, '2026-03-01'),
    (2, 'bob@example.com', 'agent1@travel.com', '2026-03-05'),
    (3, 'alice@example.com', NULL, '2026-03-10'),
    (4, 'carol@example.com', NULL, '2026-03-15');

INSERT INTO AuthorizedBy (booking_agent_email, airline_name) VALUES
    ('agent1@travel.com', 'SkyJet');
