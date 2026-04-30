import os
import re
import hashlib
import hmac
import secrets
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from functools import wraps

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
import mysql.connector
from mysql.connector import Error


PASSWORD_MIN_LENGTH = 8
COMMISSION_RATE = Decimal("0.10")
PRICE_MULTIPLIERS = {
    "economy": Decimal("1.00"),
    "business": Decimal("1.50"),
    "first": Decimal("2.50"),
}
STAFF_PERMISSIONS = ("admin", "operator")
FLIGHT_STATUSES = ("upcoming", "in-progress", "delayed")


app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("FLASK_SECRET_KEY", "change-this-before-demo"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
)

DB_CONFIG = {
    "host": os.getenv("AIRLINE_DB_HOST", "localhost"),
    "user": os.getenv("AIRLINE_DB_USER", "root"),
    "password": os.getenv("AIRLINE_DB_PASSWORD", ""),
    "database": os.getenv("AIRLINE_DB_NAME", "airline"),
    "unix_socket": "/Applications/XAMPP/xamppfiles/var/mysql/mysql.sock"
}


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def dict_cursor(connection):
    return connection.cursor(dictionary=True)


def clean_text(value):
    return (value or "").strip()


def normalize_airport_code(value):
    return clean_text(value).upper()


def normalize_flight_num(value):
    return clean_text(value).upper()


def parse_date_value(value, label, allow_blank=True):
    value = clean_text(value)
    if not value:
        if allow_blank:
            return None
        raise ValueError(f"{label} is required.")
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"{label} must be a valid date.") from exc


def parse_datetime_value(value, label):
    value = clean_text(value)
    if not value:
        raise ValueError(f"{label} is required.")
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"{label} must be a valid date and time.")


def parse_positive_int(value, label):
    value = clean_text(value)
    if not value:
        raise ValueError(f"{label} is required.")
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be a whole number.") from exc
    if parsed <= 0:
        raise ValueError(f"{label} must be greater than 0.")
    return parsed


def parse_non_negative_int(value, label):
    value = clean_text(value)
    if not value:
        return 0
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be a whole number.") from exc
    if parsed < 0:
        raise ValueError(f"{label} cannot be negative.")
    return parsed


def parse_positive_decimal(value, label):
    value = clean_text(value)
    if not value:
        raise ValueError(f"{label} is required.")
    try:
        parsed = Decimal(value)
    except Exception as exc:
        raise ValueError(f"{label} must be a valid amount.") from exc
    if parsed <= 0:
        raise ValueError(f"{label} must be greater than 0.")
    return parsed.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def validate_email(value):
    value = clean_text(value).lower()
    if not value:
        raise ValueError("Email is required.")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        raise ValueError("Email format is invalid.")
    return value


def validate_password(password, confirm_password):
    password = password or ""
    confirm_password = confirm_password or ""
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters.")
    if password != confirm_password:
        raise ValueError("Password confirmation does not match.")
    return password


def validate_name(value, label):
    value = clean_text(value)
    if not value:
        raise ValueError(f"{label} is required.")
    if len(value) > 100:
        raise ValueError(f"{label} must be 100 characters or fewer.")
    return value


def validate_username(value):
    value = clean_text(value)
    if not value:
        raise ValueError("Username is required.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,50}", value):
        raise ValueError("Username must be 3-50 characters and use only letters, numbers, dots, underscores, or hyphens.")
    return value


def validate_phone(value):
    value = clean_text(value)
    if not value:
        return ""
    if not re.fullmatch(r"[0-9+\-()\s]{7,20}", value):
        raise ValueError("Phone number format is invalid.")
    return value


def validate_airport_code(value):
    value = normalize_airport_code(value)
    if not value:
        raise ValueError("Airport code is required.")
    if not re.fullmatch(r"[A-Z0-9]{3,10}", value):
        raise ValueError("Airport code must be 3-10 uppercase letters or numbers.")
    return value


def validate_flight_num(value):
    value = normalize_flight_num(value)
    if not value:
        raise ValueError("Flight number is required.")
    if not re.fullmatch(r"[A-Z0-9-]{2,10}", value):
        raise ValueError("Flight number must be 2-10 uppercase letters, numbers, or hyphens.")
    return value


def is_password_hash(value):
    return isinstance(value, str) and value.startswith("pbkdf2_sha256$")


def verify_password(stored_password, provided_password):
    if is_password_hash(stored_password):
        try:
            _, iterations, salt, digest = stored_password.split("$", 3)
            candidate = hashlib.pbkdf2_hmac(
                "sha256",
                provided_password.encode("utf-8"),
                salt.encode("utf-8"),
                int(iterations),
            ).hex()
        except (TypeError, ValueError):
            return False
        return hmac.compare_digest(candidate, digest)
    return stored_password == provided_password


def hash_password(password):
    salt = secrets.token_hex(16)
    iterations = 260000
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def maybe_upgrade_password(cursor, table_name, key_column, key_value, stored_password, provided_password):
    if is_password_hash(stored_password):
        return
    if stored_password != provided_password:
        return
    cursor.execute(
        f"UPDATE {table_name} SET password = %s WHERE {key_column} = %s",
        (hash_password(provided_password), key_value),
    )


def first_day_of_month(day):
    return date(day.year, day.month, 1)


def shift_month(day, offset):
    total_months = (day.year * 12 + day.month - 1) + offset
    year = total_months // 12
    month = total_months % 12 + 1
    return date(year, month, 1)


def month_diff(start_month, end_month):
    return (end_month.year - start_month.year) * 12 + end_month.month - start_month.month


def build_bar_series(rows, start_month, month_count):
    values_by_month = {row["month_key"]: float(row["total"]) for row in rows}
    series = []
    max_value = max(values_by_month.values(), default=0)

    for offset in range(month_count):
        current_month = shift_month(start_month, offset)
        key = current_month.strftime("%Y-%m")
        value = values_by_month.get(key, 0.0)
        height = 0 if max_value == 0 or value == 0 else max(12, int((value / max_value) * 100))
        series.append(
            {
                "label": current_month.strftime("%b %Y"),
                "value": value,
                "height": height,
            }
        )
    return series


def calculate_ticket_price(base_price, seat_class):
    base = Decimal(str(base_price))
    multiplier = PRICE_MULTIPLIERS.get(seat_class, Decimal("1.00"))
    return (base * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def login_user(role, identity, display_name, **extras):
    session.clear()
    session.permanent = True
    session["role"] = role
    session["identity"] = identity
    session["display_name"] = display_name
    for key, value in extras.items():
        session[key] = value


def current_role():
    return session.get("role")


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "role" not in session:
            flash("Please sign in to continue.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if "role" not in session:
                flash("Please sign in to continue.", "error")
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped_view

    return decorator


def permission_required(permission):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if "role" not in session:
                flash("Please sign in to continue.", "error")
                return redirect(url_for("login"))
            if session.get("role") != "airline_staff" or permission not in session.get("permissions", []):
                abort(403)
            return view(*args, **kwargs)

        return wrapped_view

    return decorator


def load_reference_data(cursor):
    cursor.execute("SELECT name, city FROM Airport ORDER BY city, name")
    airports = cursor.fetchall()
    cities = sorted({row["city"] for row in airports})
    cursor.execute("SELECT name FROM Airline ORDER BY name")
    airlines = [row["name"] for row in cursor.fetchall()]
    return airports, cities, airlines


def fetch_authorized_airlines(cursor, agent_email):
    cursor.execute(
        """
        SELECT airline_name
        FROM AuthorizedBy
        WHERE booking_agent_email = %s
        ORDER BY airline_name
        """,
        (agent_email,),
    )
    return [row["airline_name"] for row in cursor.fetchall()]


def fetch_staff_permissions(cursor, username):
    cursor.execute(
        """
        SELECT permission
        FROM StaffPermission
        WHERE username = %s
        ORDER BY permission
        """,
        (username,),
    )
    return [row["permission"] for row in cursor.fetchall()]


def collect_flight_filters(values):
    filters = {
        "departure_airport": normalize_airport_code(values.get("departure_airport")),
        "departure_city": clean_text(values.get("departure_city")),
        "arrival_airport": normalize_airport_code(values.get("arrival_airport")),
        "arrival_city": clean_text(values.get("arrival_city")),
        "departure_date": clean_text(values.get("departure_date")),
        "airline_name": clean_text(values.get("airline_name")),
    }

    if filters["departure_date"]:
        parse_date_value(filters["departure_date"], "Departure date")
    if filters["departure_airport"] and filters["arrival_airport"] and filters["departure_airport"] == filters["arrival_airport"]:
        raise ValueError("Departure and arrival airports cannot be the same.")
    return filters


def get_public_flights(cursor, filters, restrict_airlines=None):
    query = """
        SELECT
            f.flight_num,
            f.airline_name,
            f.departure_airport,
            dep.city AS departure_city,
            f.arrival_airport,
            arr.city AS arrival_city,
            f.departure_time,
            f.arrival_time,
            f.price,
            f.status,
            COALESCE((SELECT SUM(sc.capacity) FROM SeatClass sc WHERE sc.airplane_id = f.airplane_id), 0) AS total_capacity,
            COALESCE((SELECT COUNT(*) FROM Ticket t WHERE t.flight_num = f.flight_num), 0) AS booked_tickets
        FROM Flight f
        JOIN Airport dep ON dep.name = f.departure_airport
        JOIN Airport arr ON arr.name = f.arrival_airport
        WHERE f.departure_time >= NOW()
          AND f.status IN ('upcoming', 'delayed')
    """
    params = []

    if filters["departure_airport"]:
        query += " AND f.departure_airport = %s"
        params.append(filters["departure_airport"])
    if filters["departure_city"]:
        query += " AND dep.city = %s"
        params.append(filters["departure_city"])
    if filters["arrival_airport"]:
        query += " AND f.arrival_airport = %s"
        params.append(filters["arrival_airport"])
    if filters["arrival_city"]:
        query += " AND arr.city = %s"
        params.append(filters["arrival_city"])
    if filters["departure_date"]:
        query += " AND DATE(f.departure_time) = %s"
        params.append(filters["departure_date"])
    if filters["airline_name"]:
        query += " AND f.airline_name = %s"
        params.append(filters["airline_name"])
    if restrict_airlines is not None:
        if not restrict_airlines:
            return []
        placeholders = ", ".join(["%s"] * len(restrict_airlines))
        query += f" AND f.airline_name IN ({placeholders})"
        params.extend(restrict_airlines)

    query += " ORDER BY f.departure_time, f.flight_num"
    cursor.execute(query, params)
    return cursor.fetchall()


def get_customer_spending(cursor, customer_email, analytics_start="", analytics_end=""):
    custom_start = parse_date_value(analytics_start, "Analytics start date") if analytics_start else None
    custom_end = parse_date_value(analytics_end, "Analytics end date") if analytics_end else None

    if custom_start and custom_end and custom_start > custom_end:
        raise ValueError("Analytics start date cannot be after the end date.")

    if custom_start and custom_end:
        total_query = """
            SELECT COALESCE(SUM(t.price_charged), 0) AS total
            FROM Purchases p
            JOIN Ticket t ON t.ticket_id = p.ticket_id
            WHERE p.customer_email = %s
              AND p.purchase_date BETWEEN %s AND %s
        """
        monthly_query = """
            SELECT DATE_FORMAT(p.purchase_date, '%Y-%m') AS month_key, COALESCE(SUM(t.price_charged), 0) AS total
            FROM Purchases p
            JOIN Ticket t ON t.ticket_id = p.ticket_id
            WHERE p.customer_email = %s
              AND p.purchase_date BETWEEN %s AND %s
            GROUP BY month_key
            ORDER BY month_key
        """
        params = (customer_email, custom_start, custom_end)
        cursor.execute(total_query, params)
        total = float(cursor.fetchone()["total"])
        cursor.execute(monthly_query, params)
        start_month = first_day_of_month(custom_start)
        end_month = first_day_of_month(custom_end)
        month_count = month_diff(start_month, end_month) + 1
        chart = build_bar_series(cursor.fetchall(), start_month, month_count)
        return {
            "mode": "custom",
            "title": "Custom Spending Window",
            "date_label": f"{custom_start.isoformat()} to {custom_end.isoformat()}",
            "total": total,
            "chart": chart,
        }

    today = date.today()
    total_query = """
        SELECT COALESCE(SUM(t.price_charged), 0) AS total
        FROM Purchases p
        JOIN Ticket t ON t.ticket_id = p.ticket_id
        WHERE p.customer_email = %s
          AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
    """
    chart_query = """
        SELECT DATE_FORMAT(p.purchase_date, '%Y-%m') AS month_key, COALESCE(SUM(t.price_charged), 0) AS total
        FROM Purchases p
        JOIN Ticket t ON t.ticket_id = p.ticket_id
        WHERE p.customer_email = %s
          AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
        GROUP BY month_key
        ORDER BY month_key
    """
    cursor.execute(total_query, (customer_email,))
    total = float(cursor.fetchone()["total"])
    cursor.execute(chart_query, (customer_email,))
    end_month = first_day_of_month(today)
    start_month = shift_month(end_month, -5)
    chart = build_bar_series(cursor.fetchall(), start_month, 6)
    return {
        "mode": "default",
        "title": "Last 12 Months of Spending",
        "date_label": "Monthly bars show the last 6 months.",
        "total": total,
        "chart": chart,
    }


def get_agent_analytics(cursor, agent_email):
    metrics_query = """
        SELECT
            COUNT(*) AS tickets_sold,
            COALESCE(SUM(t.price_charged * %s), 0) AS total_commission,
            COALESCE(AVG(t.price_charged * %s), 0) AS avg_commission
        FROM Purchases p
        JOIN Ticket t ON t.ticket_id = p.ticket_id
        WHERE p.booking_agent_email = %s
          AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
    """
    cursor.execute(metrics_query, (float(COMMISSION_RATE), float(COMMISSION_RATE), agent_email))
    metrics = cursor.fetchone()

    top_tickets_query = """
        SELECT
            p.customer_email,
            c.name,
            COUNT(*) AS tickets_sold
        FROM Purchases p
        JOIN Customer c ON c.email = p.customer_email
        WHERE p.booking_agent_email = %s
          AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
        GROUP BY p.customer_email, c.name
        ORDER BY tickets_sold DESC, p.customer_email
        LIMIT 5
    """
    top_commission_query = """
        SELECT
            p.customer_email,
            c.name,
            COALESCE(SUM(t.price_charged * %s), 0) AS commission_total
        FROM Purchases p
        JOIN Ticket t ON t.ticket_id = p.ticket_id
        JOIN Customer c ON c.email = p.customer_email
        WHERE p.booking_agent_email = %s
          AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
        GROUP BY p.customer_email, c.name
        ORDER BY commission_total DESC, p.customer_email
        LIMIT 5
    """
    cursor.execute(top_tickets_query, (agent_email,))
    top_by_tickets = cursor.fetchall()
    cursor.execute(top_commission_query, (float(COMMISSION_RATE), agent_email))
    top_by_commission = cursor.fetchall()

    return {
        "tickets_sold": metrics["tickets_sold"] or 0,
        "total_commission": float(metrics["total_commission"] or 0),
        "avg_commission": float(metrics["avg_commission"] or 0),
        "top_by_tickets": top_by_tickets,
        "top_by_commission": top_by_commission,
    }


def get_staff_analytics(cursor, airline_name):
    top_agents_base = """
        SELECT
            p.booking_agent_email,
            COUNT(*) AS tickets_sold,
            COALESCE(SUM(t.price_charged * %s), 0) AS commission_total
        FROM Purchases p
        JOIN Ticket t ON t.ticket_id = p.ticket_id
        JOIN Flight f ON f.flight_num = t.flight_num
        WHERE f.airline_name = %s
          AND p.booking_agent_email IS NOT NULL
          AND {period_filter}
        GROUP BY p.booking_agent_email
        ORDER BY {order_clause}
        LIMIT 5
    """

    def run_top_agents(period_filter, order_clause):
        query = top_agents_base.format(period_filter=period_filter, order_clause=order_clause)
        cursor.execute(query, (float(COMMISSION_RATE), airline_name))
        return cursor.fetchall()

    most_frequent_customer_query = """
        SELECT
            p.customer_email,
            c.name,
            COUNT(*) AS trips_taken
        FROM Purchases p
        JOIN Ticket t ON t.ticket_id = p.ticket_id
        JOIN Flight f ON f.flight_num = t.flight_num
        JOIN Customer c ON c.email = p.customer_email
        WHERE f.airline_name = %s
          AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
        GROUP BY p.customer_email, c.name
        ORDER BY trips_taken DESC, p.customer_email
        LIMIT 1
    """
    tickets_per_month_query = """
        SELECT DATE_FORMAT(p.purchase_date, '%Y-%m') AS month_key, COUNT(*) AS total
        FROM Purchases p
        JOIN Ticket t ON t.ticket_id = p.ticket_id
        JOIN Flight f ON f.flight_num = t.flight_num
        WHERE f.airline_name = %s
          AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
        GROUP BY month_key
        ORDER BY month_key
    """
    delay_stats_query = """
        SELECT
            SUM(CASE WHEN status = 'delayed' THEN 1 ELSE 0 END) AS delayed_count,
            SUM(CASE WHEN status <> 'delayed' THEN 1 ELSE 0 END) AS non_delayed_count
        FROM Flight
        WHERE airline_name = %s
    """
    top_destinations_query = """
        SELECT
            f.arrival_airport,
            arr.city AS arrival_city,
            COUNT(*) AS tickets_sold
        FROM Purchases p
        JOIN Ticket t ON t.ticket_id = p.ticket_id
        JOIN Flight f ON f.flight_num = t.flight_num
        JOIN Airport arr ON arr.name = f.arrival_airport
        WHERE f.airline_name = %s
          AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL {interval_expression})
        GROUP BY f.arrival_airport, arr.city
        ORDER BY tickets_sold DESC, f.arrival_airport
        LIMIT 5
    """

    cursor.execute(most_frequent_customer_query, (airline_name,))
    most_frequent_customer = cursor.fetchone()

    cursor.execute(tickets_per_month_query, (airline_name,))
    ticket_rows = cursor.fetchall()
    end_month = first_day_of_month(date.today())
    start_month = shift_month(end_month, -5)
    tickets_per_month = build_bar_series(ticket_rows, start_month, 6)

    cursor.execute(delay_stats_query, (airline_name,))
    delay_stats = cursor.fetchone()

    cursor.execute(top_destinations_query.format(interval_expression="3 MONTH"), (airline_name,))
    top_destinations_3m = cursor.fetchall()
    cursor.execute(top_destinations_query.format(interval_expression="1 YEAR"), (airline_name,))
    top_destinations_1y = cursor.fetchall()

    return {
        "month_by_tickets": run_top_agents(
            "YEAR(p.purchase_date) = YEAR(CURDATE()) AND MONTH(p.purchase_date) = MONTH(CURDATE())",
            "tickets_sold DESC, commission_total DESC, p.booking_agent_email",
        ),
        "month_by_commission": run_top_agents(
            "YEAR(p.purchase_date) = YEAR(CURDATE()) AND MONTH(p.purchase_date) = MONTH(CURDATE())",
            "commission_total DESC, tickets_sold DESC, p.booking_agent_email",
        ),
        "year_by_tickets": run_top_agents(
            "YEAR(p.purchase_date) = YEAR(CURDATE())",
            "tickets_sold DESC, commission_total DESC, p.booking_agent_email",
        ),
        "year_by_commission": run_top_agents(
            "YEAR(p.purchase_date) = YEAR(CURDATE())",
            "commission_total DESC, tickets_sold DESC, p.booking_agent_email",
        ),
        "most_frequent_customer": most_frequent_customer,
        "tickets_per_month": tickets_per_month,
        "delay_stats": {
            "delayed": delay_stats["delayed_count"] or 0,
            "non_delayed": delay_stats["non_delayed_count"] or 0,
        },
        "top_destinations_3m": top_destinations_3m,
        "top_destinations_1y": top_destinations_1y,
    }


@app.template_filter("datetime_display")
def datetime_display(value):
    if not value:
        return ""
    return value.strftime("%b %d, %Y %H:%M")


@app.template_filter("date_display")
def date_display(value):
    if not value:
        return ""
    return value.strftime("%b %d, %Y")


@app.template_filter("money")
def money(value):
    amount = float(value or 0)
    return f"${amount:,.2f}"


@app.route("/")
def index():
    if "role" in session:
        return redirect(url_for("home"))

    featured_flights = []
    airlines = []
    airports = []
    cities = []

    try:
        conn = get_db_connection()
        cursor = dict_cursor(conn)
        airports, cities, airlines = load_reference_data(cursor)
        featured_flights = get_public_flights(
            cursor,
            {
                "departure_airport": "",
                "departure_city": "",
                "arrival_airport": "",
                "arrival_city": "",
                "departure_date": "",
                "airline_name": "",
            },
        )[:6]
        cursor.close()
        conn.close()
    except Error:
        flash("The database connection is unavailable right now. You can still review the app structure, but live data will be missing.", "error")

    return render_template(
        "index.html",
        featured_flights=featured_flights,
        airlines=airlines,
        airports=airports,
        cities=cities,
    )


@app.route("/home")
@login_required
def home():
    role = session["role"]
    if role == "customer":
        return redirect(url_for("customer_portal"))
    if role == "booking_agent":
        return redirect(url_for("agent_portal"))
    return redirect(url_for("staff_portal"))


@app.route("/login", methods=["GET", "POST"])
def login():
    form_data = {
        "role": request.form.get("role", "customer"),
        "identifier": clean_text(request.form.get("identifier")),
    }

    if request.method == "POST":
        role = form_data["role"]
        identifier = form_data["identifier"]
        password = request.form.get("password", "")

        if role not in ("customer", "booking_agent", "airline_staff"):
            flash("Please choose a valid account type.", "error")
            return render_template("login.html", form_data=form_data)

        try:
            conn = get_db_connection()
            cursor = dict_cursor(conn)

            if role == "customer":
                identity = validate_email(identifier)
                cursor.execute(
                    "SELECT email, name, password FROM Customer WHERE email = %s",
                    (identity,),
                )
                row = cursor.fetchone()
                if not row or not verify_password(row["password"], password):
                    flash("Invalid email or password.", "error")
                    cursor.close()
                    conn.close()
                    return render_template("login.html", form_data=form_data)
                maybe_upgrade_password(cursor, "Customer", "email", row["email"], row["password"], password)
                conn.commit()
                login_user("customer", row["email"], row["name"], customer_email=row["email"])

            elif role == "booking_agent":
                identity = validate_email(identifier)
                cursor.execute(
                    "SELECT email, password FROM BookingAgent WHERE email = %s",
                    (identity,),
                )
                row = cursor.fetchone()
                if not row or not verify_password(row["password"], password):
                    flash("Invalid booking agent credentials.", "error")
                    cursor.close()
                    conn.close()
                    return render_template("login.html", form_data=form_data)
                maybe_upgrade_password(cursor, "BookingAgent", "email", row["email"], row["password"], password)
                authorized_airlines = fetch_authorized_airlines(cursor, row["email"])
                conn.commit()
                login_user(
                    "booking_agent",
                    row["email"],
                    row["email"],
                    agent_email=row["email"],
                    authorized_airlines=authorized_airlines,
                )

            else:
                identity = validate_username(identifier)
                cursor.execute(
                    """
                    SELECT username, first_name, last_name, airline_name, password
                    FROM AirlineStaff
                    WHERE username = %s
                    """,
                    (identity,),
                )
                row = cursor.fetchone()
                if not row or not verify_password(row["password"], password):
                    flash("Invalid staff username or password.", "error")
                    cursor.close()
                    conn.close()
                    return render_template("login.html", form_data=form_data)
                maybe_upgrade_password(cursor, "AirlineStaff", "username", row["username"], row["password"], password)
                permissions = fetch_staff_permissions(cursor, row["username"])
                conn.commit()
                login_user(
                    "airline_staff",
                    row["username"],
                    f"{row['first_name']} {row['last_name']}",
                    airline_name=row["airline_name"],
                    permissions=permissions,
                )

            cursor.close()
            conn.close()
            flash("You are signed in.", "success")
            return redirect(url_for("home"))
        except (ValueError, Error) as exc:
            flash(str(exc), "error")

    return render_template("login.html", form_data=form_data)


@app.route("/register", methods=["GET", "POST"])
def register():
    form_data = {
        "role": request.form.get("role", "customer"),
        "email": clean_text(request.form.get("email")),
        "name": clean_text(request.form.get("name")),
        "city": clean_text(request.form.get("city")),
        "phone_number": clean_text(request.form.get("phone_number")),
        "passport_number": clean_text(request.form.get("passport_number")),
        "passport_country": clean_text(request.form.get("passport_country")),
        "customer_date_of_birth": clean_text(request.form.get("customer_date_of_birth")),
        "username": clean_text(request.form.get("username")),
        "first_name": clean_text(request.form.get("first_name")),
        "last_name": clean_text(request.form.get("last_name")),
        "airline_name": clean_text(request.form.get("airline_name")),
        "staff_date_of_birth": clean_text(request.form.get("staff_date_of_birth")),
        "permissions": request.form.getlist("permissions"),
    }

    conn = None
    cursor = None
    airlines = []
    try:
        conn = get_db_connection()
        cursor = dict_cursor(conn)
        _, _, airlines = load_reference_data(cursor)

        if request.method == "POST":
            role = form_data["role"]
            password = validate_password(request.form.get("password", ""), request.form.get("confirm_password", ""))
            hashed = hash_password(password)

            if role == "customer":
                email = validate_email(form_data["email"])
                name = validate_name(form_data["name"], "Full name")
                city = clean_text(form_data["city"])
                phone_number = validate_phone(form_data["phone_number"])
                passport_number = clean_text(form_data["passport_number"])
                passport_country = clean_text(form_data["passport_country"])
                date_of_birth = (
                    parse_date_value(form_data["customer_date_of_birth"], "Date of birth")
                    if form_data["customer_date_of_birth"]
                    else None
                )

                cursor.execute("SELECT 1 FROM Customer WHERE email = %s", (email,))
                if cursor.fetchone():
                    raise ValueError("That customer email is already registered.")

                cursor.execute(
                    """
                    INSERT INTO Customer (
                        email, name, password, city, phone_number,
                        passport_number, passport_country, date_of_birth
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (email, name, hashed, city or None, phone_number or None, passport_number or None, passport_country or None, date_of_birth),
                )
                conn.commit()
                login_user("customer", email, name, customer_email=email)

            elif role == "booking_agent":
                email = validate_email(form_data["email"])
                cursor.execute("SELECT 1 FROM BookingAgent WHERE email = %s", (email,))
                if cursor.fetchone():
                    raise ValueError("That booking agent email is already registered.")

                cursor.execute(
                    "INSERT INTO BookingAgent (email, password) VALUES (%s, %s)",
                    (email, hashed),
                )
                conn.commit()
                login_user(
                    "booking_agent",
                    email,
                    email,
                    agent_email=email,
                    authorized_airlines=[],
                )

            elif role == "airline_staff":
                username = validate_username(form_data["username"])
                first_name = validate_name(form_data["first_name"], "First name")
                last_name = validate_name(form_data["last_name"], "Last name")
                airline_name = clean_text(form_data["airline_name"])
                date_of_birth = (
                    parse_date_value(form_data["staff_date_of_birth"], "Date of birth")
                    if form_data["staff_date_of_birth"]
                    else None
                )
                permissions = [permission for permission in form_data["permissions"] if permission in STAFF_PERMISSIONS]
                if airline_name not in airlines:
                    raise ValueError("Please choose a valid airline for staff registration.")
                if not permissions:
                    raise ValueError("Staff registration requires at least one permission.")

                cursor.execute("SELECT 1 FROM AirlineStaff WHERE username = %s", (username,))
                if cursor.fetchone():
                    raise ValueError("That staff username is already registered.")

                cursor.execute(
                    """
                    INSERT INTO AirlineStaff (
                        username, airline_name, password, first_name, last_name, date_of_birth
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (username, airline_name, hashed, first_name, last_name, date_of_birth),
                )
                for permission in permissions:
                    cursor.execute(
                        "INSERT INTO StaffPermission (username, permission) VALUES (%s, %s)",
                        (username, permission),
                    )
                conn.commit()
                login_user(
                    "airline_staff",
                    username,
                    f"{first_name} {last_name}",
                    airline_name=airline_name,
                    permissions=sorted(set(permissions)),
                )
            else:
                raise ValueError("Please choose a valid account type.")

            flash("Registration completed successfully.", "success")
            return redirect(url_for("home"))
    except (ValueError, Error) as exc:
        if conn:
            conn.rollback()
        flash(str(exc), "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template("register.html", form_data=form_data, airlines=airlines)


@app.route("/status")
def status_lookup():
    result = None
    filters = {
        "airline_name": clean_text(request.args.get("airline_name")),
        "flight_num": normalize_flight_num(request.args.get("flight_num")),
    }

    try:
        conn = get_db_connection()
        cursor = dict_cursor(conn)
        _, _, airlines = load_reference_data(cursor)

        if filters["airline_name"] or filters["flight_num"]:
            if filters["airline_name"] not in airlines:
                raise ValueError("Please select a valid airline.")
            flight_num = validate_flight_num(filters["flight_num"])
            cursor.execute(
                """
                SELECT
                    f.flight_num,
                    f.airline_name,
                    f.status,
                    f.departure_time,
                    f.arrival_time,
                    f.departure_airport,
                    dep.city AS departure_city,
                    f.arrival_airport,
                    arr.city AS arrival_city
                FROM Flight f
                JOIN Airport dep ON dep.name = f.departure_airport
                JOIN Airport arr ON arr.name = f.arrival_airport
                WHERE f.airline_name = %s
                  AND f.flight_num = %s
                  AND f.status = 'in-progress'
                """,
                (filters["airline_name"], flight_num),
            )
            result = cursor.fetchone()
            if not result:
                flash("No in-progress flight matched that airline and flight number.", "error")

        cursor.close()
        conn.close()
    except (ValueError, Error) as exc:
        flash(str(exc), "error")
        airlines = []

    return render_template("status.html", airlines=airlines, result=result, filters=filters)


@app.route("/flights")
def flights():
    filters = {
        "departure_airport": request.args.get("departure_airport", ""),
        "departure_city": request.args.get("departure_city", ""),
        "arrival_airport": request.args.get("arrival_airport", ""),
        "arrival_city": request.args.get("arrival_city", ""),
        "departure_date": request.args.get("departure_date", ""),
        "airline_name": request.args.get("airline_name", ""),
    }

    flights_data = []
    airports = []
    cities = []
    airlines = []

    try:
        parsed_filters = collect_flight_filters(filters)
        conn = get_db_connection()
        cursor = dict_cursor(conn)
        airports, cities, airlines = load_reference_data(cursor)

        restrict_airlines = None
        if current_role() == "booking_agent":
            restrict_airlines = session.get("authorized_airlines", [])

        flights_data = get_public_flights(cursor, parsed_filters, restrict_airlines=restrict_airlines)
        cursor.close()
        conn.close()
        filters = parsed_filters
    except (ValueError, Error) as exc:
        flash(str(exc), "error")

    return render_template(
        "flights.html",
        flights=flights_data,
        filters=filters,
        airports=airports,
        cities=cities,
        airlines=airlines,
        can_book=current_role() in ("customer", "booking_agent"),
        authorized_airlines=session.get("authorized_airlines", []),
    )


@app.route("/flight/<flight_num>")
def flight_detail(flight_num):
    flight_number = validate_flight_num(flight_num)

    try:
        conn = get_db_connection()
        cursor = dict_cursor(conn)
        cursor.execute(
            """
            SELECT
                f.flight_num,
                f.airline_name,
                f.departure_airport,
                dep.city AS departure_city,
                f.arrival_airport,
                arr.city AS arrival_city,
                f.departure_time,
                f.arrival_time,
                f.price,
                f.status,
                f.airplane_id
            FROM Flight f
            JOIN Airport dep ON dep.name = f.departure_airport
            JOIN Airport arr ON arr.name = f.arrival_airport
            WHERE f.flight_num = %s
            """,
            (flight_number,),
        )
        flight = cursor.fetchone()
        if not flight:
            abort(404)

        cursor.execute(
            """
            SELECT
                sc.seat_class,
                sc.capacity,
                COALESCE((
                    SELECT COUNT(*)
                    FROM Ticket t
                    WHERE t.flight_num = %s
                      AND t.seat_class = sc.seat_class
                ), 0) AS booked
            FROM SeatClass sc
            WHERE sc.airplane_id = %s
            ORDER BY FIELD(sc.seat_class, 'economy', 'business', 'first'), sc.seat_class
            """,
            (flight_number, flight["airplane_id"]),
        )
        seat_classes = cursor.fetchall()
        cursor.close()
        conn.close()

        for row in seat_classes:
            row["remaining"] = max(row["capacity"] - row["booked"], 0)
            row["price"] = calculate_ticket_price(flight["price"], row["seat_class"])
        bookable_seat_classes = [row for row in seat_classes if row["remaining"] > 0]

        agent_can_book = True
        if current_role() == "booking_agent":
            agent_can_book = flight["airline_name"] in session.get("authorized_airlines", [])

        return render_template(
            "flight_detail.html",
            flight=flight,
            seat_classes=seat_classes,
            bookable_seat_classes=bookable_seat_classes,
            can_book=current_role() in ("customer", "booking_agent"),
            agent_can_book=agent_can_book,
        )
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("flights"))
    except Error as exc:
        flash(str(exc), "error")
        return redirect(url_for("flights"))


@app.route("/book", methods=["POST"])
@roles_required("customer", "booking_agent")
def book_ticket():
    conn = None
    cursor = None
    booking_context = {
        "success": False,
        "message": "Booking could not be completed.",
    }

    try:
        flight_num = validate_flight_num(request.form.get("flight_num"))
        seat_class = clean_text(request.form.get("seat_class")).lower()
        if seat_class not in PRICE_MULTIPLIERS:
            raise ValueError("Please choose a supported seat class.")

        customer_email = session.get("customer_email")
        booking_agent_email = None
        if current_role() == "booking_agent":
            booking_agent_email = session.get("agent_email")
            customer_email = validate_email(request.form.get("customer_email"))

        conn = get_db_connection()
        conn.start_transaction()
        cursor = dict_cursor(conn)

        cursor.execute(
            """
            SELECT flight_num, airline_name, airplane_id, price, status, departure_time
            FROM Flight
            WHERE flight_num = %s
            FOR UPDATE
            """,
            (flight_num,),
        )
        flight = cursor.fetchone()
        if not flight:
            raise ValueError("That flight no longer exists.")
        if flight["status"] not in ("upcoming", "delayed"):
            raise ValueError("This flight is not open for booking.")
        if flight["departure_time"] <= datetime.now():
            raise ValueError("This flight has already departed and cannot be booked.")

        if booking_agent_email:
            cursor.execute(
                """
                SELECT 1
                FROM AuthorizedBy
                WHERE booking_agent_email = %s AND airline_name = %s
                """,
                (booking_agent_email, flight["airline_name"]),
            )
            if not cursor.fetchone():
                raise ValueError("This booking agent is not authorized to sell tickets for that airline.")
            cursor.execute("SELECT 1 FROM Customer WHERE email = %s", (customer_email,))
            if not cursor.fetchone():
                raise ValueError("Customer email was not found.")

        cursor.execute(
            """
            SELECT capacity
            FROM SeatClass
            WHERE airplane_id = %s AND seat_class = %s
            FOR UPDATE
            """,
            (flight["airplane_id"], seat_class),
        )
        seat_row = cursor.fetchone()
        if not seat_row:
            raise ValueError("That seat class is not available for this airplane.")

        cursor.execute(
            """
            SELECT COUNT(*) AS booked
            FROM Ticket
            WHERE flight_num = %s AND seat_class = %s
            """,
            (flight_num, seat_class),
        )
        booked = cursor.fetchone()["booked"]
        if booked >= seat_row["capacity"]:
            raise ValueError("No seats remain in the selected class.")

        price = calculate_ticket_price(flight["price"], seat_class)
        cursor.execute(
            """
            INSERT INTO Ticket (flight_num, seat_class, airplane_id, price_charged)
            VALUES (%s, %s, %s, %s)
            """,
            (flight_num, seat_class, flight["airplane_id"], price),
        )
        ticket_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO Purchases (ticket_id, customer_email, booking_agent_email, purchase_date)
            VALUES (%s, %s, %s, %s)
            """,
            (ticket_id, customer_email, booking_agent_email, date.today()),
        )

        conn.commit()
        booking_context = {
            "success": True,
            "message": "Booking confirmed. Server-side capacity checks and pricing were applied successfully.",
            "ticket_id": ticket_id,
            "flight_num": flight_num,
            "seat_class": seat_class,
            "price": price,
            "customer_email": customer_email,
            "booking_agent_email": booking_agent_email,
        }
    except (ValueError, Error) as exc:
        if conn:
            conn.rollback()
        booking_context["message"] = str(exc)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template("booking_result.html", **booking_context)


@app.route("/customer")
@roles_required("customer")
def customer_portal():
    filters = {
        "scope": request.args.get("scope", "upcoming"),
        "start_date": request.args.get("start_date", ""),
        "end_date": request.args.get("end_date", ""),
        "departure_airport": request.args.get("departure_airport", ""),
        "arrival_airport": request.args.get("arrival_airport", ""),
        "analytics_start": request.args.get("analytics_start", ""),
        "analytics_end": request.args.get("analytics_end", ""),
    }

    purchases = []
    airports = []
    spending = None

    try:
        start_date = parse_date_value(filters["start_date"], "Start date") if filters["start_date"] else None
        end_date = parse_date_value(filters["end_date"], "End date") if filters["end_date"] else None
        if start_date and end_date and start_date > end_date:
            raise ValueError("Trip start date cannot be after the end date.")

        departure_airport = normalize_airport_code(filters["departure_airport"])
        arrival_airport = normalize_airport_code(filters["arrival_airport"])

        conn = get_db_connection()
        cursor = dict_cursor(conn)
        airports, _, _ = load_reference_data(cursor)

        query = """
            SELECT
                t.ticket_id,
                t.seat_class,
                t.price_charged,
                p.purchase_date,
                f.flight_num,
                f.airline_name,
                f.departure_airport,
                dep.city AS departure_city,
                f.arrival_airport,
                arr.city AS arrival_city,
                f.departure_time,
                f.arrival_time,
                f.status
            FROM Purchases p
            JOIN Ticket t ON t.ticket_id = p.ticket_id
            JOIN Flight f ON f.flight_num = t.flight_num
            JOIN Airport dep ON dep.name = f.departure_airport
            JOIN Airport arr ON arr.name = f.arrival_airport
            WHERE p.customer_email = %s
        """
        params = [session["customer_email"]]

        if filters["scope"] == "upcoming":
            query += " AND f.departure_time >= NOW()"
        elif filters["scope"] == "past":
            query += " AND f.departure_time < NOW()"

        if start_date:
            query += " AND DATE(f.departure_time) >= %s"
            params.append(start_date)
        if end_date:
            query += " AND DATE(f.departure_time) <= %s"
            params.append(end_date)
        if departure_airport:
            query += " AND f.departure_airport = %s"
            params.append(departure_airport)
        if arrival_airport:
            query += " AND f.arrival_airport = %s"
            params.append(arrival_airport)

        query += " ORDER BY f.departure_time, t.ticket_id"
        cursor.execute(query, params)
        purchases = cursor.fetchall()

        spending = get_customer_spending(
            cursor,
            session["customer_email"],
            filters["analytics_start"],
            filters["analytics_end"],
        )
        cursor.close()
        conn.close()
    except (ValueError, Error) as exc:
        flash(str(exc), "error")

    return render_template(
        "customer_portal.html",
        purchases=purchases,
        filters=filters,
        airports=airports,
        spending=spending,
    )


@app.route("/my-purchases")
@roles_required("customer")
def my_purchases():
    return redirect(url_for("customer_portal"))


@app.route("/saved-flights/save/<flight_num>", methods=["POST"])
@roles_required("customer")
def save_flight(flight_num):
    flight_number = validate_flight_num(flight_num)
    customer_email = session["customer_email"]

    try:
        conn = get_db_connection()
        cursor = dict_cursor(conn)

        # Check if flight exists and is upcoming
        cursor.execute(
            "SELECT flight_num FROM Flight WHERE flight_num = %s AND departure_time >= NOW()",
            (flight_number,),
        )
        if not cursor.fetchone():
            flash("Flight not found or has already departed.", "error")
            cursor.close()
            conn.close()
            return redirect(request.referrer or url_for("flights"))

        # Insert into SavedFlight
        cursor.execute(
            "INSERT INTO SavedFlight (customer_email, flight_num) VALUES (%s, %s)",
            (customer_email, flight_number),
        )
        conn.commit()
        flash("Flight saved successfully.", "success")
    except mysql.connector.IntegrityError:
        flash("This flight is already saved.", "error")
    except Error as exc:
        flash(str(exc), "error")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

    return redirect(request.referrer or url_for("flights"))


@app.route("/saved-flights")
@roles_required("customer")
def saved_flights():
    customer_email = session["customer_email"]
    saved_flights = []

    try:
        conn = get_db_connection()
        cursor = dict_cursor(conn)
        cursor.execute(
            """
            SELECT
                sf.saved_at,
                f.flight_num,
                f.airline_name,
                f.departure_airport,
                dep.city AS departure_city,
                f.arrival_airport,
                arr.city AS arrival_city,
                f.departure_time,
                f.arrival_time,
                f.price,
                f.status
            FROM SavedFlight sf
            JOIN Flight f ON sf.flight_num = f.flight_num
            JOIN Airport dep ON dep.name = f.departure_airport
            JOIN Airport arr ON arr.name = f.arrival_airport
            WHERE sf.customer_email = %s
            ORDER BY sf.saved_at DESC
            """,
            (customer_email,),
        )
        saved_flights = cursor.fetchall()
        cursor.close()
        conn.close()
    except Error as exc:
        flash(str(exc), "error")

    return render_template("saved_flights.html", saved_flights=saved_flights)


@app.route("/saved-flights/remove/<flight_num>", methods=["POST"])
@roles_required("customer")
def remove_saved_flight(flight_num):
    flight_number = validate_flight_num(flight_num)
    customer_email = session["customer_email"]

    try:
        conn = get_db_connection()
        cursor = dict_cursor(conn)
        cursor.execute(
            "DELETE FROM SavedFlight WHERE customer_email = %s AND flight_num = %s",
            (customer_email, flight_number),
        )
        if cursor.rowcount > 0:
            conn.commit()
            flash("Flight removed from saved list.", "success")
        else:
            flash("Flight not found in your saved list.", "error")
        cursor.close()
        conn.close()
    except Error as exc:
        flash(str(exc), "error")

    return redirect(url_for("saved_flights"))


@app.route("/agent")
@roles_required("booking_agent")
def agent_portal():
    filters = {
        "start_date": request.args.get("start_date", ""),
        "end_date": request.args.get("end_date", ""),
        "departure_airport": request.args.get("departure_airport", ""),
        "arrival_airport": request.args.get("arrival_airport", ""),
    }

    purchases = []
    airports = []
    analytics = None

    try:
        start_date = parse_date_value(filters["start_date"], "Start date") if filters["start_date"] else None
        end_date = parse_date_value(filters["end_date"], "End date") if filters["end_date"] else None
        if start_date and end_date and start_date > end_date:
            raise ValueError("Start date cannot be after the end date.")

        departure_airport = normalize_airport_code(filters["departure_airport"])
        arrival_airport = normalize_airport_code(filters["arrival_airport"])

        conn = get_db_connection()
        cursor = dict_cursor(conn)
        airports, _, _ = load_reference_data(cursor)

        query = """
            SELECT
                p.customer_email,
                t.ticket_id,
                t.seat_class,
                t.price_charged,
                p.purchase_date,
                f.flight_num,
                f.airline_name,
                f.departure_airport,
                dep.city AS departure_city,
                f.arrival_airport,
                arr.city AS arrival_city,
                f.departure_time,
                f.status
            FROM Purchases p
            JOIN Ticket t ON t.ticket_id = p.ticket_id
            JOIN Flight f ON f.flight_num = t.flight_num
            JOIN Airport dep ON dep.name = f.departure_airport
            JOIN Airport arr ON arr.name = f.arrival_airport
            WHERE p.booking_agent_email = %s
        """
        params = [session["agent_email"]]

        if start_date:
            query += " AND DATE(f.departure_time) >= %s"
            params.append(start_date)
        if end_date:
            query += " AND DATE(f.departure_time) <= %s"
            params.append(end_date)
        if departure_airport:
            query += " AND f.departure_airport = %s"
            params.append(departure_airport)
        if arrival_airport:
            query += " AND f.arrival_airport = %s"
            params.append(arrival_airport)

        query += " ORDER BY p.purchase_date DESC, t.ticket_id DESC"
        cursor.execute(query, params)
        purchases = cursor.fetchall()
        analytics = get_agent_analytics(cursor, session["agent_email"])
        cursor.close()
        conn.close()
    except (ValueError, Error) as exc:
        flash(str(exc), "error")

    return render_template(
        "agent_portal.html",
        purchases=purchases,
        filters=filters,
        airports=airports,
        analytics=analytics,
    )


@app.route("/staff")
@roles_required("airline_staff")
def staff_portal():
    filters = {
        "start_date": request.args.get("start_date", ""),
        "end_date": request.args.get("end_date", ""),
        "departure_airport": request.args.get("departure_airport", ""),
        "arrival_airport": request.args.get("arrival_airport", ""),
        "passenger_flight_num": request.args.get("passenger_flight_num", ""),
        "customer_email": request.args.get("customer_email", ""),
    }

    flights_data = []
    airports = []
    airplanes = []
    agents = []
    passengers = []
    customer_flights = []
    analytics = None

    try:
        start_date = parse_date_value(filters["start_date"], "Start date") if filters["start_date"] else None
        end_date = parse_date_value(filters["end_date"], "End date") if filters["end_date"] else None
        if start_date and end_date and start_date > end_date:
            raise ValueError("Start date cannot be after the end date.")

        departure_airport = normalize_airport_code(filters["departure_airport"])
        arrival_airport = normalize_airport_code(filters["arrival_airport"])

        conn = get_db_connection()
        cursor = dict_cursor(conn)
        airports, _, _ = load_reference_data(cursor)

        cursor.execute(
            """
            SELECT id
            FROM Airplane
            WHERE airline_name = %s
            ORDER BY id
            """,
            (session["airline_name"],),
        )
        airplanes = cursor.fetchall()

        cursor.execute(
            """
            SELECT ba.email
            FROM BookingAgent ba
            ORDER BY ba.email
            """,
        )
        agents = cursor.fetchall()

        query = """
            SELECT
                f.flight_num,
                f.airplane_id,
                f.price,
                f.status,
                f.departure_airport,
                dep.city AS departure_city,
                f.arrival_airport,
                arr.city AS arrival_city,
                f.departure_time,
                f.arrival_time,
                COALESCE((SELECT SUM(sc.capacity) FROM SeatClass sc WHERE sc.airplane_id = f.airplane_id), 0) AS total_capacity,
                COALESCE((SELECT COUNT(*) FROM Ticket t WHERE t.flight_num = f.flight_num), 0) AS sold_tickets
            FROM Flight f
            JOIN Airport dep ON dep.name = f.departure_airport
            JOIN Airport arr ON arr.name = f.arrival_airport
            WHERE f.airline_name = %s
              AND f.departure_time >= NOW()
              AND f.departure_time <= DATE_ADD(NOW(), INTERVAL 30 DAY)
        """
        params = [session["airline_name"]]

        if start_date:
            query += " AND DATE(f.departure_time) >= %s"
            params.append(start_date)
        if end_date:
            query += " AND DATE(f.departure_time) <= %s"
            params.append(end_date)
        if departure_airport:
            query += " AND f.departure_airport = %s"
            params.append(departure_airport)
        if arrival_airport:
            query += " AND f.arrival_airport = %s"
            params.append(arrival_airport)

        query += " ORDER BY f.departure_time, f.flight_num"
        cursor.execute(query, params)
        flights_data = cursor.fetchall()

        if filters["passenger_flight_num"]:
            passenger_flight_num = validate_flight_num(filters["passenger_flight_num"])
            cursor.execute(
                """
                SELECT
                    c.email,
                    c.name,
                    t.ticket_id,
                    t.seat_class,
                    p.purchase_date
                FROM Purchases p
                JOIN Ticket t ON t.ticket_id = p.ticket_id
                JOIN Flight f ON f.flight_num = t.flight_num
                JOIN Customer c ON c.email = p.customer_email
                WHERE f.airline_name = %s
                  AND f.flight_num = %s
                ORDER BY c.name, t.ticket_id
                """,
                (session["airline_name"], passenger_flight_num),
            )
            passengers = cursor.fetchall()

        if filters["customer_email"]:
            customer_email = validate_email(filters["customer_email"])
            cursor.execute(
                """
                SELECT
                    f.flight_num,
                    f.status,
                    f.departure_airport,
                    dep.city AS departure_city,
                    f.arrival_airport,
                    arr.city AS arrival_city,
                    f.departure_time,
                    p.purchase_date,
                    t.seat_class
                FROM Purchases p
                JOIN Ticket t ON t.ticket_id = p.ticket_id
                JOIN Flight f ON f.flight_num = t.flight_num
                JOIN Airport dep ON dep.name = f.departure_airport
                JOIN Airport arr ON arr.name = f.arrival_airport
                WHERE f.airline_name = %s
                  AND p.customer_email = %s
                ORDER BY f.departure_time DESC, t.ticket_id DESC
                """,
                (session["airline_name"], customer_email),
            )
            customer_flights = cursor.fetchall()

        analytics = get_staff_analytics(cursor, session["airline_name"])
        cursor.close()
        conn.close()
    except (ValueError, Error) as exc:
        flash(str(exc), "error")

    return render_template(
        "staff_portal.html",
        flights=flights_data,
        filters=filters,
        airports=airports,
        airplanes=airplanes,
        agents=agents,
        passengers=passengers,
        customer_flights=customer_flights,
        analytics=analytics,
        permissions=session.get("permissions", []),
    )


@app.route("/staff/airport", methods=["POST"])
@permission_required("admin")
def add_airport():
    conn = None
    cursor = None
    try:
        airport_code = validate_airport_code(request.form.get("airport_code"))
        city = validate_name(request.form.get("city"), "City")
        conn = get_db_connection()
        cursor = dict_cursor(conn)
        cursor.execute("SELECT 1 FROM Airport WHERE name = %s", (airport_code,))
        if cursor.fetchone():
            raise ValueError("That airport already exists.")
        cursor.execute(
            "INSERT INTO Airport (name, city) VALUES (%s, %s)",
            (airport_code, city),
        )
        conn.commit()
        flash("Airport added successfully.", "success")
    except (ValueError, Error) as exc:
        if conn:
            conn.rollback()
        flash(str(exc), "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return redirect(url_for("staff_portal"))


@app.route("/staff/airplane", methods=["POST"])
@permission_required("admin")
def add_airplane():
    conn = None
    cursor = None
    try:
        airplane_id = parse_positive_int(request.form.get("airplane_id"), "Airplane ID")
        economy_capacity = parse_non_negative_int(request.form.get("economy_capacity"), "Economy capacity")
        business_capacity = parse_non_negative_int(request.form.get("business_capacity"), "Business capacity")
        first_capacity = parse_non_negative_int(request.form.get("first_capacity"), "First capacity")

        capacities = {
            "economy": economy_capacity,
            "business": business_capacity,
            "first": first_capacity,
        }
        offered_classes = {seat_class: capacity for seat_class, capacity in capacities.items() if capacity > 0}
        if not offered_classes:
            raise ValueError("At least one seat class capacity must be greater than 0.")

        conn = get_db_connection()
        conn.start_transaction()
        cursor = dict_cursor(conn)
        cursor.execute("SELECT 1 FROM Airplane WHERE id = %s", (airplane_id,))
        if cursor.fetchone():
            raise ValueError("That airplane ID already exists.")

        cursor.execute(
            "INSERT INTO Airplane (id, airline_name) VALUES (%s, %s)",
            (airplane_id, session["airline_name"]),
        )
        for seat_class, capacity in offered_classes.items():
            cursor.execute(
                "INSERT INTO SeatClass (airplane_id, seat_class, capacity) VALUES (%s, %s, %s)",
                (airplane_id, seat_class, capacity),
            )
        conn.commit()
        flash("Airplane and seat classes added successfully.", "success")
    except (ValueError, Error) as exc:
        if conn:
            conn.rollback()
        flash(str(exc), "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return redirect(url_for("staff_portal"))


@app.route("/staff/flight", methods=["POST"])
@permission_required("admin")
def add_flight():
    conn = None
    cursor = None
    try:
        flight_num = validate_flight_num(request.form.get("flight_num"))
        airplane_id = parse_positive_int(request.form.get("airplane_id"), "Airplane ID")
        departure_airport = validate_airport_code(request.form.get("departure_airport"))
        arrival_airport = validate_airport_code(request.form.get("arrival_airport"))
        departure_time = parse_datetime_value(request.form.get("departure_time"), "Departure time")
        arrival_time = parse_datetime_value(request.form.get("arrival_time"), "Arrival time")
        price = parse_positive_decimal(request.form.get("price"), "Base price")
        status = clean_text(request.form.get("status")).lower() or "upcoming"

        if departure_airport == arrival_airport:
            raise ValueError("Departure and arrival airports cannot be the same.")
        if arrival_time <= departure_time:
            raise ValueError("Arrival time must be later than departure time.")
        if status not in FLIGHT_STATUSES:
            raise ValueError("Please choose a valid flight status.")

        conn = get_db_connection()
        conn.start_transaction()
        cursor = dict_cursor(conn)
        cursor.execute(
            "SELECT 1 FROM Airplane WHERE id = %s AND airline_name = %s",
            (airplane_id, session["airline_name"]),
        )
        if not cursor.fetchone():
            raise ValueError("The selected airplane does not belong to your airline.")
        cursor.execute("SELECT 1 FROM Flight WHERE flight_num = %s", (flight_num,))
        if cursor.fetchone():
            raise ValueError("That flight number already exists.")
        cursor.execute(
            """
            INSERT INTO Flight (
                flight_num, departure_time, arrival_time, price, status,
                airline_name, airplane_id, departure_airport, arrival_airport
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                flight_num,
                departure_time,
                arrival_time,
                price,
                status,
                session["airline_name"],
                airplane_id,
                departure_airport,
                arrival_airport,
            ),
        )
        conn.commit()
        flash("Flight created successfully.", "success")
    except (ValueError, Error) as exc:
        if conn:
            conn.rollback()
        flash(str(exc), "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return redirect(url_for("staff_portal"))


@app.route("/staff/authorize-agent", methods=["POST"])
@permission_required("admin")
def authorize_agent():
    conn = None
    cursor = None
    try:
        agent_email = validate_email(request.form.get("agent_email"))
        conn = get_db_connection()
        conn.start_transaction()
        cursor = dict_cursor(conn)
        cursor.execute("SELECT 1 FROM BookingAgent WHERE email = %s", (agent_email,))
        if not cursor.fetchone():
            raise ValueError("That booking agent does not exist.")
        cursor.execute(
            """
            SELECT 1
            FROM AuthorizedBy
            WHERE booking_agent_email = %s AND airline_name = %s
            """,
            (agent_email, session["airline_name"]),
        )
        if cursor.fetchone():
            raise ValueError("That booking agent is already associated with this airline.")
        cursor.execute(
            "INSERT INTO AuthorizedBy (booking_agent_email, airline_name) VALUES (%s, %s)",
            (agent_email, session["airline_name"]),
        )
        conn.commit()
        flash("Booking agent authorization added successfully.", "success")
    except (ValueError, Error) as exc:
        if conn:
            conn.rollback()
        flash(str(exc), "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return redirect(url_for("staff_portal"))


@app.route("/staff/status", methods=["POST"])
@permission_required("operator")
def update_flight_status():
    conn = None
    cursor = None
    try:
        flight_num = validate_flight_num(request.form.get("flight_num"))
        status = clean_text(request.form.get("status")).lower()
        if status not in FLIGHT_STATUSES:
            raise ValueError("Please choose a valid flight status.")
        conn = get_db_connection()
        conn.start_transaction()
        cursor = dict_cursor(conn)
        cursor.execute(
            "SELECT 1 FROM Flight WHERE flight_num = %s AND airline_name = %s",
            (flight_num, session["airline_name"]),
        )
        if not cursor.fetchone():
            raise ValueError("That flight does not belong to your airline.")
        cursor.execute(
            "UPDATE Flight SET status = %s WHERE flight_num = %s",
            (status, flight_num),
        )
        conn.commit()
        flash("Flight status updated successfully.", "success")
    except (ValueError, Error) as exc:
        if conn:
            conn.rollback()
        flash(str(exc), "error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return redirect(url_for("staff_portal"))


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("index"))


@app.errorhandler(403)
def forbidden(_error):
    return render_template("error.html", title="Access Denied", error="You do not have permission to view that page."), 403


@app.errorhandler(404)
def page_not_found(_error):
    return render_template("error.html", title="Page Not Found", error="The page you requested could not be found."), 404


@app.errorhandler(500)
def internal_error(_error):
    return render_template("error.html", title="Server Error", error="An unexpected server error occurred."), 500


if __name__ == "__main__":
    print("=" * 60)
    print("Air Ticket Reservation System - Part 3 App")
    print("=" * 60)
    print("Run the database initializer before starting the Flask server.")
    print("Server URL: http://127.0.0.1:5000")
    app.run("127.0.0.1", 5000, debug=True)
