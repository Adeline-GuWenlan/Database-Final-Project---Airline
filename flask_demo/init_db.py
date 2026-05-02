import hashlib

import mysql.connector


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
}


def sample_hash(password, salt):
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        260000,
    ).hex()
    return f"pbkdf2_sha256$260000${salt}${digest}"


def init_database():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    print("Resetting database 'airline'...")
    cursor.execute("DROP DATABASE IF EXISTS airline")
    cursor.execute("CREATE DATABASE airline")
    cursor.execute("USE airline")

    schema_statements = [
        """
        CREATE TABLE Airline (
            name VARCHAR(50) PRIMARY KEY
        )
        """,
        """
        CREATE TABLE Airport (
            name VARCHAR(10) PRIMARY KEY,
            city VARCHAR(50) NOT NULL
        )
        """,
        """
        CREATE TABLE Airplane (
            id INTEGER PRIMARY KEY,
            airline_name VARCHAR(50) NOT NULL,
            FOREIGN KEY (airline_name) REFERENCES Airline(name)
                ON DELETE CASCADE ON UPDATE CASCADE
        )
        """,
        """
        CREATE TABLE SeatClass (
            airplane_id INTEGER NOT NULL,
            seat_class VARCHAR(20) NOT NULL,
            capacity INTEGER NOT NULL,
            PRIMARY KEY (airplane_id, seat_class),
            FOREIGN KEY (airplane_id) REFERENCES Airplane(id)
                ON DELETE CASCADE ON UPDATE CASCADE
        )
        """,
        """
        CREATE TABLE Flight (
            flight_num VARCHAR(10) PRIMARY KEY,
            departure_time DATETIME NOT NULL,
            arrival_time DATETIME NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            status VARCHAR(20) NOT NULL CHECK (status IN ('upcoming', 'in-progress', 'delayed')),
            airline_name VARCHAR(50) NOT NULL,
            airplane_id INTEGER NOT NULL,
            departure_airport VARCHAR(10) NOT NULL,
            arrival_airport VARCHAR(10) NOT NULL,
            FOREIGN KEY (airline_name) REFERENCES Airline(name)
                ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY (airplane_id) REFERENCES Airplane(id)
                ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY (departure_airport) REFERENCES Airport(name),
            FOREIGN KEY (arrival_airport) REFERENCES Airport(name)
        )
        """,
        """
        CREATE TABLE Customer (
            email VARCHAR(100) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            password VARCHAR(255) NOT NULL,
            building_number INTEGER,
            street VARCHAR(100),
            city VARCHAR(50),
            state VARCHAR(50),
            phone_number VARCHAR(20),
            passport_number VARCHAR(20),
            passport_expiration_date DATE,
            passport_country VARCHAR(50),
            date_of_birth DATE
        )
        """,
        """
        CREATE TABLE BookingAgent (
            email VARCHAR(100) PRIMARY KEY,
            password VARCHAR(255) NOT NULL
        )
        """,
        """
        CREATE TABLE AirlineStaff (
            username VARCHAR(50) PRIMARY KEY,
            airline_name VARCHAR(50) NOT NULL,
            password VARCHAR(255) NOT NULL,
            first_name VARCHAR(50) NOT NULL,
            last_name VARCHAR(50) NOT NULL,
            date_of_birth DATE,
            FOREIGN KEY (airline_name) REFERENCES Airline(name)
                ON DELETE CASCADE ON UPDATE CASCADE
        )
        """,
        """
        CREATE TABLE StaffPermission (
            username VARCHAR(50) NOT NULL,
            permission VARCHAR(20) NOT NULL,
            PRIMARY KEY (username, permission),
            FOREIGN KEY (username) REFERENCES AirlineStaff(username)
                ON DELETE CASCADE ON UPDATE CASCADE,
            CHECK (permission IN ('admin', 'operator'))
        )
        """,
        """
        CREATE TABLE Ticket (
            ticket_id INTEGER PRIMARY KEY AUTO_INCREMENT,
            flight_num VARCHAR(10) NOT NULL,
            seat_class VARCHAR(20) NOT NULL,
            airplane_id INTEGER NOT NULL,
            price_charged DECIMAL(10,2) NOT NULL,
            FOREIGN KEY (flight_num) REFERENCES Flight(flight_num)
                ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY (airplane_id, seat_class) REFERENCES SeatClass(airplane_id, seat_class)
                ON DELETE CASCADE ON UPDATE CASCADE
        )
        """,
        """
        CREATE TABLE Purchases (
            ticket_id INTEGER NOT NULL,
            customer_email VARCHAR(100) NOT NULL,
            booking_agent_email VARCHAR(100),
            purchase_date DATE NOT NULL,
            PRIMARY KEY (ticket_id, customer_email),
            FOREIGN KEY (ticket_id) REFERENCES Ticket(ticket_id)
                ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY (customer_email) REFERENCES Customer(email)
                ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY (booking_agent_email) REFERENCES BookingAgent(email)
                ON DELETE SET NULL ON UPDATE CASCADE
        )
        """,
        """
        CREATE TABLE AuthorizedBy (
            booking_agent_email VARCHAR(100) NOT NULL,
            airline_name VARCHAR(50) NOT NULL,
            PRIMARY KEY (booking_agent_email, airline_name),
            FOREIGN KEY (booking_agent_email) REFERENCES BookingAgent(email)
                ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY (airline_name) REFERENCES Airline(name)
                ON DELETE CASCADE ON UPDATE CASCADE
        )
        """,
        "CREATE INDEX idx_flight_departure_status ON Flight (departure_time, status)",
        "CREATE INDEX idx_flight_route_departure ON Flight (departure_airport, arrival_airport, departure_time)",
        "CREATE INDEX idx_flight_airline_departure ON Flight (airline_name, departure_time)",
        "CREATE INDEX idx_ticket_flight_class ON Ticket (flight_num, seat_class)",
        "CREATE INDEX idx_purchases_customer_date ON Purchases (customer_email, purchase_date)",
        "CREATE INDEX idx_purchases_agent_date ON Purchases (booking_agent_email, purchase_date)",
        "CREATE INDEX idx_authorized_by_airline ON AuthorizedBy (airline_name, booking_agent_email)",
        """
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
        """,
        """
        CREATE TRIGGER validate_flight_update
        BEFORE UPDATE ON Flight
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
        """,
        """
        CREATE TRIGGER enforce_ticket_capacity
        BEFORE INSERT ON Ticket
        FOR EACH ROW
        BEGIN
            DECLARE flight_airplane_id INT DEFAULT NULL;
            DECLARE flight_count INT DEFAULT 0;
            DECLARE seat_capacity INT DEFAULT NULL;
            DECLARE seat_class_count INT DEFAULT 0;
            DECLARE booked_count INT DEFAULT 0;

            SELECT COUNT(*), MAX(airplane_id)
            INTO flight_count, flight_airplane_id
            FROM Flight
            WHERE flight_num = NEW.flight_num;

            IF flight_count = 0 THEN
                SIGNAL SQLSTATE '45000'
                    SET MESSAGE_TEXT = 'Flight does not exist for this ticket.';
            END IF;

            IF flight_airplane_id <> NEW.airplane_id THEN
                SIGNAL SQLSTATE '45000'
                    SET MESSAGE_TEXT = 'Ticket airplane must match the flight airplane.';
            END IF;

            SELECT COUNT(*), MAX(capacity)
            INTO seat_class_count, seat_capacity
            FROM SeatClass
            WHERE airplane_id = NEW.airplane_id
              AND seat_class = NEW.seat_class;

            IF seat_class_count = 0 THEN
                SIGNAL SQLSTATE '45000'
                    SET MESSAGE_TEXT = 'Seat class is not configured for this airplane.';
            END IF;

            SELECT COUNT(*) INTO booked_count
            FROM Ticket
            WHERE flight_num = NEW.flight_num
              AND seat_class = NEW.seat_class;

            IF booked_count >= seat_capacity THEN
                SIGNAL SQLSTATE '45000'
                    SET MESSAGE_TEXT = 'Seat capacity has been reached for this class.';
            END IF;
        END
        """,
        """
        CREATE PROCEDURE purchase_ticket(
            IN p_flight_num VARCHAR(10),
            IN p_seat_class VARCHAR(20),
            IN p_customer_email VARCHAR(100),
            IN p_booking_agent_email VARCHAR(100)
        )
        BEGIN
            DECLARE v_airline_name VARCHAR(50);
            DECLARE v_airplane_id INTEGER;
            DECLARE v_base_price DECIMAL(10,2);
            DECLARE v_status VARCHAR(20);
            DECLARE v_departure_time DATETIME;
            DECLARE v_flight_count INT DEFAULT 0;
            DECLARE v_customer_count INT DEFAULT 0;
            DECLARE v_seat_count INT DEFAULT 0;
            DECLARE v_authorized_count INT DEFAULT 0;
            DECLARE v_capacity INT DEFAULT 0;
            DECLARE v_booked_count INT DEFAULT 0;
            DECLARE v_price_charged DECIMAL(10,2);
            DECLARE v_ticket_id INT;

            SELECT COUNT(*) INTO v_customer_count
            FROM Customer
            WHERE email = p_customer_email;

            IF v_customer_count = 0 THEN
                SIGNAL SQLSTATE '45000'
                    SET MESSAGE_TEXT = 'Customer email was not found.';
            END IF;

            SELECT COUNT(*) INTO v_flight_count
            FROM Flight
            WHERE flight_num = p_flight_num;

            IF v_flight_count = 0 THEN
                SIGNAL SQLSTATE '45000'
                    SET MESSAGE_TEXT = 'That flight no longer exists.';
            END IF;

            SELECT airline_name, airplane_id, price, status, departure_time
            INTO v_airline_name, v_airplane_id, v_base_price, v_status, v_departure_time
            FROM Flight
            WHERE flight_num = p_flight_num
            FOR UPDATE;

            IF v_status NOT IN ('upcoming', 'delayed') THEN
                SIGNAL SQLSTATE '45000'
                    SET MESSAGE_TEXT = 'This flight is not open for booking.';
            END IF;

            IF v_departure_time <= NOW() THEN
                SIGNAL SQLSTATE '45000'
                    SET MESSAGE_TEXT = 'This flight has already departed and cannot be booked.';
            END IF;

            IF p_booking_agent_email IS NOT NULL THEN
                SELECT COUNT(*) INTO v_authorized_count
                FROM AuthorizedBy
                WHERE booking_agent_email = p_booking_agent_email
                  AND airline_name = v_airline_name;

                IF v_authorized_count = 0 THEN
                    SIGNAL SQLSTATE '45000'
                        SET MESSAGE_TEXT = 'This booking agent is not authorized to sell tickets for that airline.';
                END IF;
            END IF;

            SELECT COUNT(*) INTO v_seat_count
            FROM SeatClass
            WHERE airplane_id = v_airplane_id
              AND seat_class = p_seat_class;

            IF v_seat_count = 0 THEN
                SIGNAL SQLSTATE '45000'
                    SET MESSAGE_TEXT = 'That seat class is not available for this airplane.';
            END IF;

            SELECT capacity INTO v_capacity
            FROM SeatClass
            WHERE airplane_id = v_airplane_id
              AND seat_class = p_seat_class
            FOR UPDATE;

            SELECT COUNT(*) INTO v_booked_count
            FROM Ticket
            WHERE flight_num = p_flight_num
              AND seat_class = p_seat_class;

            IF v_booked_count >= v_capacity THEN
                SIGNAL SQLSTATE '45000'
                    SET MESSAGE_TEXT = 'No seats remain in the selected class.';
            END IF;

            IF p_seat_class = 'economy' THEN
                SET v_price_charged = ROUND(v_base_price * 1.00, 2);
            ELSEIF p_seat_class = 'business' THEN
                SET v_price_charged = ROUND(v_base_price * 1.50, 2);
            ELSEIF p_seat_class = 'first' THEN
                SET v_price_charged = ROUND(v_base_price * 2.50, 2);
            ELSE
                SIGNAL SQLSTATE '45000'
                    SET MESSAGE_TEXT = 'Please choose a supported seat class.';
            END IF;

            INSERT INTO Ticket (flight_num, seat_class, airplane_id, price_charged)
            VALUES (p_flight_num, p_seat_class, v_airplane_id, v_price_charged);

            SET v_ticket_id = LAST_INSERT_ID();

            INSERT INTO Purchases (ticket_id, customer_email, booking_agent_email, purchase_date)
            VALUES (v_ticket_id, p_customer_email, p_booking_agent_email, CURRENT_DATE());

            SELECT v_ticket_id AS ticket_id, v_price_charged AS price_charged;
        END
        """,
    ]

    print("Creating schema...")
    for statement in schema_statements:
        cursor.execute(statement)

    print("Inserting sample data...")
    sample_statements = [
        "INSERT INTO Airline (name) VALUES ('SkyJet'), ('AirAsia'), ('Delta')",
        """
        INSERT INTO Airport (name, city) VALUES
            ('JFK', 'New York'),
            ('LAX', 'Los Angeles'),
            ('PVG', 'Shanghai'),
            ('NRT', 'Tokyo'),
            ('LHR', 'London'),
            ('SFO', 'San Francisco')
        """,
        """
        INSERT INTO Airplane (id, airline_name) VALUES
            (1, 'SkyJet'),
            (2, 'AirAsia'),
            (3, 'Delta'),
            (4, 'SkyJet'),
            (5, 'SkyJet')
        """,
        """
        INSERT INTO SeatClass (airplane_id, seat_class, capacity) VALUES
            (1, 'economy', 150), (1, 'business', 30), (1, 'first', 10),
            (2, 'economy', 200), (2, 'business', 40),
            (3, 'economy', 180), (3, 'business', 35), (3, 'first', 15),
            (4, 'economy', 120), (4, 'business', 25),
            (5, 'economy', 1)
        """,
        """
        INSERT INTO Flight (flight_num, departure_time, arrival_time, price, status,
            airline_name, airplane_id, departure_airport, arrival_airport) VALUES
            ('SJ101', '2026-05-15 08:00:00', '2026-05-15 11:30:00', 299.00, 'upcoming', 'SkyJet', 1, 'JFK', 'LAX'),
            ('SJ102', '2026-05-16 14:00:00', '2026-05-17 06:00:00', 899.00, 'upcoming', 'SkyJet', 1, 'JFK', 'PVG'),
            ('SJ103', '2026-05-17 10:00:00', '2026-05-17 13:30:00', 320.00, 'upcoming', 'SkyJet', 4, 'LAX', 'SFO'),
            ('SJ900', '2026-05-12 12:00:00', '2026-05-12 15:00:00', 199.00, 'upcoming', 'SkyJet', 5, 'JFK', 'SFO'),
            ('AA201', '2026-05-15 09:00:00', '2026-05-15 22:00:00', 750.00, 'upcoming', 'AirAsia', 2, 'LAX', 'NRT'),
            ('AA202', '2026-05-18 11:00:00', '2026-05-19 05:00:00', 680.00, 'upcoming', 'AirAsia', 2, 'NRT', 'PVG'),
            ('DL301', '2026-05-16 07:00:00', '2026-05-16 15:00:00', 550.00, 'upcoming', 'Delta', 3, 'JFK', 'LHR'),
            ('DL302', '2026-05-20 16:00:00', '2026-05-20 19:30:00', 275.00, 'upcoming', 'Delta', 3, 'LAX', 'JFK'),
            ('SJ104', '2026-04-30 09:00:00', '2026-04-30 13:00:00', 310.00, 'in-progress', 'SkyJet', 1, 'SFO', 'JFK'),
            ('AA203', '2026-05-13 10:00:00', '2026-05-13 14:00:00', 420.00, 'delayed', 'AirAsia', 2, 'PVG', 'NRT')
        """,
        f"""
        INSERT INTO Customer (email, name, password, city, phone_number, passport_number, passport_country, date_of_birth) VALUES
            ('alice@example.com', 'Alice Chen', '{sample_hash("password123", "alice")}', 'New York', '212-555-0101', 'P123456', 'USA', '1990-06-15'),
            ('bob@example.com', 'Bob Li', '{sample_hash("password123", "bob")}', 'Shanghai', '86-21-5555-0102', 'P789012', 'China', '1985-03-22')
        """,
        f"""
        INSERT INTO BookingAgent (email, password) VALUES
            ('agent1@travel.com', '{sample_hash("agentpass", "agent1")}')
        """,
        f"""
        INSERT INTO AirlineStaff (username, airline_name, password, first_name, last_name, date_of_birth) VALUES
            ('admin_skyjet', 'SkyJet', '{sample_hash("adminpass", "admin_skyjet")}', 'Avery', 'Admin', '1980-01-15'),
            ('staff_skyjet', 'SkyJet', '{sample_hash("staffpass", "staff_skyjet")}', 'Sam', 'Staff', '1985-07-20')
        """,
        """
        INSERT INTO StaffPermission (username, permission) VALUES
            ('admin_skyjet', 'admin'),
            ('admin_skyjet', 'operator'),
            ('staff_skyjet', 'operator')
        """,
        """
        INSERT INTO Ticket (ticket_id, flight_num, seat_class, airplane_id, price_charged) VALUES
            (1, 'SJ101', 'economy', 1, 299.00),
            (2, 'SJ101', 'business', 1, 448.50),
            (3, 'SJ102', 'economy', 1, 899.00),
            (4, 'DL301', 'business', 3, 825.00),
            (5, 'SJ900', 'economy', 5, 199.00)
        """,
        """
        INSERT INTO Purchases (ticket_id, customer_email, booking_agent_email, purchase_date) VALUES
            (1, 'alice@example.com', NULL, '2026-03-01'),
            (2, 'bob@example.com', 'agent1@travel.com', '2026-03-05'),
            (3, 'alice@example.com', NULL, '2026-03-10'),
            (4, 'bob@example.com', NULL, '2026-03-15'),
            (5, 'alice@example.com', NULL, '2026-04-25')
        """,
        "INSERT INTO AuthorizedBy (booking_agent_email, airline_name) VALUES ('agent1@travel.com', 'SkyJet')",
    ]

    for statement in sample_statements:
        cursor.execute(statement)

    conn.commit()
    cursor.close()
    conn.close()

    print("Database initialized successfully.")
    print("Demo logins:")
    print("  Customer: alice@example.com / password123")
    print("  Customer: bob@example.com / password123")
    print("  Booking agent: agent1@travel.com / agentpass")
    print("  Admin staff: admin_skyjet / adminpass")
    print("  Regular staff: staff_skyjet / staffpass")


if __name__ == "__main__":
    init_database()
