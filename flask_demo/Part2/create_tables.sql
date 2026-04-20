-- Schema definitions for the refined Air Ticket Reservation System

CREATE TABLE Airline (
    name VARCHAR(50) PRIMARY KEY
);

CREATE TABLE Airport (
    name VARCHAR(10) PRIMARY KEY,
    city VARCHAR(50) NOT NULL
);

CREATE TABLE Airplane (
    id INTEGER PRIMARY KEY,
    airline_name VARCHAR(50) NOT NULL,
    FOREIGN KEY (airline_name)
        REFERENCES Airline(name)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE TABLE SeatClass (
    airplane_id INTEGER NOT NULL,
    seat_class VARCHAR(20) NOT NULL,
    capacity INTEGER NOT NULL,
    PRIMARY KEY (airplane_id, seat_class),
    FOREIGN KEY (airplane_id)
        REFERENCES Airplane(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

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
    FOREIGN KEY (airline_name)
        REFERENCES Airline(name)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    FOREIGN KEY (airplane_id)
        REFERENCES Airplane(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    FOREIGN KEY (departure_airport)
        REFERENCES Airport(name),
    FOREIGN KEY (arrival_airport)
        REFERENCES Airport(name)
);

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
);

CREATE TABLE BookingAgent (
    email VARCHAR(100) PRIMARY KEY,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE AirlineStaff (
    username VARCHAR(50) PRIMARY KEY,
    airline_name VARCHAR(50) NOT NULL,
    password VARCHAR(255) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    date_of_birth DATE,
    FOREIGN KEY (airline_name)
        REFERENCES Airline(name)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE TABLE StaffPermission (
    username VARCHAR(50) NOT NULL,
    permission VARCHAR(20) NOT NULL,
    PRIMARY KEY (username, permission),
    FOREIGN KEY (username)
        REFERENCES AirlineStaff(username)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CHECK (permission IN ('admin', 'operator'))
);

CREATE TABLE Ticket (
    ticket_id INTEGER PRIMARY KEY AUTO_INCREMENT,
    flight_num VARCHAR(10) NOT NULL,
    seat_class VARCHAR(20) NOT NULL,
    airplane_id INTEGER NOT NULL,
    price_charged DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (flight_num)
        REFERENCES Flight(flight_num)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    FOREIGN KEY (airplane_id, seat_class)
        REFERENCES SeatClass(airplane_id, seat_class)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE TABLE Purchases (
    ticket_id INTEGER NOT NULL,
    customer_email VARCHAR(100) NOT NULL,
    booking_agent_email VARCHAR(100),
    purchase_date DATE NOT NULL,
    PRIMARY KEY (ticket_id, customer_email),
    FOREIGN KEY (ticket_id)
        REFERENCES Ticket(ticket_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    FOREIGN KEY (customer_email)
        REFERENCES Customer(email)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    FOREIGN KEY (booking_agent_email)
        REFERENCES BookingAgent(email)
        ON DELETE SET NULL
        ON UPDATE CASCADE
);

CREATE TABLE AuthorizedBy (
    booking_agent_email VARCHAR(100) NOT NULL,
    airline_name VARCHAR(50) NOT NULL,
    PRIMARY KEY (booking_agent_email, airline_name),
    FOREIGN KEY (booking_agent_email)
        REFERENCES BookingAgent(email)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    FOREIGN KEY (airline_name)
        REFERENCES Airline(name)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- Indexes for public search, dashboards, analytics, and session-protected lookups.
CREATE INDEX idx_flight_departure_status
    ON Flight (departure_time, status);

CREATE INDEX idx_flight_route_departure
    ON Flight (departure_airport, arrival_airport, departure_time);

CREATE INDEX idx_flight_airline_departure
    ON Flight (airline_name, departure_time);

CREATE INDEX idx_ticket_flight_class
    ON Ticket (flight_num, seat_class);

CREATE INDEX idx_purchases_customer_date
    ON Purchases (customer_email, purchase_date);

CREATE INDEX idx_purchases_agent_date
    ON Purchases (booking_agent_email, purchase_date);

CREATE INDEX idx_authorized_by_airline
    ON AuthorizedBy (airline_name, booking_agent_email);

DELIMITER //

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
END//

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
END//

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

    IF seat_capacity IS NULL THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Seat class is not configured for this airplane.';
    END IF;

    SELECT COUNT(*)
    INTO booked_count
    FROM Ticket
    WHERE flight_num = NEW.flight_num
      AND seat_class = NEW.seat_class;

    IF booked_count >= seat_capacity THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Seat capacity has been reached for this class.';
    END IF;
END//

DELIMITER ;
