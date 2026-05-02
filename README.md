# Database Final Project - Airline Reservation System

This repository contains the full project workspace for the airline reservation final project, including the main Flask + MySQL application, supporting SQL files, project writeups, and course/reference materials that were kept in the working folder.

The primary deliverable is the refined Part 3 web application in `flask_demo/Part2`.

## Repository Walkthrough

- `flask_demo/Part2/`: main airline reservation system application
- `flask_demo/init_db.py`: shared database initializer used by the app setup flow
- `flask_demo/example1`, `flask_demo/example2`, `flask_demo/example3`: smaller Flask examples kept for reference
- `Readme_HumanFacing.txt`: original short setup notes from the workspace
- `Syllabus and Rubrix.txt`: project requirements and grading notes
- `AgentPrompt.txt`: project planning / optimization prompt used during development
- `FlaskOverview - Copy.pptx`: supporting class material kept with the project files

## Main App Features

- Public flight search and in-progress flight status lookup
- Role-based login and registration for customers, booking agents, and airline staff
- Customer booking and spending views
- Booking agent sales and commission analytics
- Airline staff operations, analytics, and admin/operator actions
- Database-side integrity support through indexes and triggers

## Saved Flights Feature (Bonus)

A new customer-exclusive feature allowing users to save flights for later reference or booking.

### How It Works

- **Save Flights**: Logged-in customers can save upcoming flights from the search results page (`/flights`) or individual flight detail pages (`/flight/<flight_num>`).
- **View Saved Flights**: Access a dedicated page (`/saved-flights`) to view all saved flights with full details including route, schedule, and status.
- **Remove Saved Flights**: Easily remove flights from the saved list with a single click.

### Technical Implementation

- **Database**: New `SavedFlight` table with foreign keys to `Customer` and `Flight` tables.
- **Security**: Customer-only access using session validation and parameterized queries.
- **UI Integration**: Save buttons appear only for logged-in customers on flight search and detail pages.
- **Navigation**: "Saved Flights" link added to the main navigation for customers.

### Database Schema Addition

```sql
CREATE TABLE IF NOT EXISTS SavedFlight (
    customer_email VARCHAR(100) NOT NULL,
    flight_num VARCHAR(10) NOT NULL,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (customer_email, flight_num),
    FOREIGN KEY (customer_email) REFERENCES Customer(email) ON DELETE CASCADE,
    FOREIGN KEY (flight_num) REFERENCES Flight(flight_num) ON DELETE CASCADE
);
```

### API Endpoints

- `POST /saved-flights/save/<flight_num>`: Save a flight (customers only)
- `GET /saved-flights`: View saved flights (customers only)
- `POST /saved-flights/remove/<flight_num>`: Remove a saved flight (customers only)

### Usage

1. Log in as a customer (e.g., alice@example.com / password123)
2. Search for flights or view flight details
3. Click "Save Flight" or "Save This Flight" buttons
4. Access "Saved Flights" from the navigation to view and manage saved flights

## Quick Start

1. Install dependencies:

```bash
pip install flask mysql-connector-python
```

2. If your MySQL user is not `root` with an empty password, set the connection values before running the app:

```bash
export AIRLINE_DB_USER=root
export AIRLINE_DB_PASSWORD='your_mysql_password'
export AIRLINE_DB_HOST=127.0.0.1
```

For XAMPP or another socket-based MySQL setup, set the socket explicitly:

```bash
export AIRLINE_DB_UNIX_SOCKET=/Applications/XAMPP/xamppfiles/var/mysql/mysql.sock
```

3. Initialize the database:

```bash
cd flask_demo/Part2
python init_db.py
```

4. Start the web app:

```bash
cd flask_demo/Part2
python app.py
```

5. Open `http://127.0.0.1:5000` in a browser.

## Notes

- This repo intentionally excludes macOS metadata files and Python cache artifacts.
- More detailed app-specific documentation is available in `flask_demo/Part2/README.md`.
