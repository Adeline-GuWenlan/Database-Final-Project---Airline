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

## Quick Start

1. Install dependencies:

```bash
pip install flask mysql-connector-python
```

2. Update database credentials in:

- `flask_demo/init_db.py`
- `flask_demo/Part2/app.py`

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
