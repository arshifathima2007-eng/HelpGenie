import os
import sqlite3
from datetime import datetime
from functools import wraps

import joblib
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "helpgenie-development-secret-key"
)


# ============================================================
# DATABASE
# ============================================================

DATABASE = "helpgenie.db"


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():

    connection = get_db()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ticket TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL,
            assigned_team TEXT NOT NULL,
            confidence REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Open',
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )

    connection.commit()
    connection.close()

    print("Database initialized successfully.")


# ============================================================
# LOAD ML MODEL
# ============================================================

try:

    model = joblib.load("model.pkl")

    print("AI model loaded successfully.")

except Exception as error:

    model = None

    print("Error loading AI model:", error)


# ============================================================
# TEAM MAPPING
# ============================================================

TEAM_MAPPING = {

    "Network": "Network Support",

    "Hardware": "Hardware Support",

    "Software": "Software Support",

    "Account": "Account Support",

    "Email": "Email Support",

    "Security": "Security Team",

    "Printer": "Printer Support"
}


ALLOWED_TEAMS = [
    "Network Support",
    "Hardware Support",
    "Software Support",
    "Account Support",
    "Email Support",
    "Security Team",
    "Printer Support"
]


# ============================================================
# PRIORITY KEYWORDS
# ============================================================

HIGH_PRIORITY_WORDS = [
    "hack",
    "hacked",
    "virus",
    "ransomware",
    "data breach",
    "security breach",
    "stolen",
    "urgent",
    "critical",
    "cannot access",
    "system down",
    "server down"
]


MEDIUM_PRIORITY_WORDS = [
    "not working",
    "error",
    "problem",
    "issue",
    "failed",
    "failure",
    "unable"
]


def determine_priority(ticket_text):

    text = ticket_text.lower()

    for word in HIGH_PRIORITY_WORDS:

        if word in text:
            return "High"

    for word in MEDIUM_PRIORITY_WORDS:

        if word in text:
            return "Medium"

    return "Low"


# ============================================================
# ADMIN ACCOUNT
# ============================================================

def create_admin_from_env():

    admin_name = os.environ.get("ADMIN_NAME")
    admin_email = os.environ.get("ADMIN_EMAIL")
    admin_password = os.environ.get("ADMIN_PASSWORD")

    if not admin_name or not admin_email or not admin_password:

        print("Admin environment variables not configured.")

        return

    admin_name = admin_name.strip()
    admin_email = admin_email.strip().lower()
    admin_password = admin_password.strip()

    connection = get_db()

    existing = connection.execute(
        """
        SELECT id
        FROM users
        WHERE LOWER(email) = ?
        """,
        (admin_email,)
    ).fetchone()

    password_hash = generate_password_hash(
        admin_password
    )

    if existing:

        # If the email already exists,
        # make sure it becomes the admin account.

        connection.execute(
            """
            UPDATE users

            SET
                name = ?,
                password = ?,
                role = 'admin'

            WHERE id = ?
            """,
            (
                admin_name,
                password_hash,
                existing["id"]
            )
        )

        connection.commit()

        print("Admin account updated successfully.")

    else:

        connection.execute(
            """
            INSERT INTO users
            (
                name,
                email,
                password,
                role
            )

            VALUES (?, ?, ?, 'admin')
            """,
            (
                admin_name,
                admin_email,
                password_hash
            )
        )

        connection.commit()

        print("Admin account created successfully.")

    connection.close()


# ============================================================
# LOGIN REQUIRED
# ============================================================

def login_required():

    return "user_id" in session


def admin_required():

    return (
        "user_id" in session
        and session.get("role") == "admin"
    )


# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():

    if not login_required():

        return redirect(
            url_for("login")
        )

    connection = get_db()

    tickets = connection.execute(
        """
        SELECT *

        FROM tickets

        WHERE user_id = ?

        ORDER BY id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    connection.close()

    return render_template(
        "index.html",
        username=session.get("name"),
        email=session.get("email"),
        tickets=tickets
    )


# ============================================================
# REGISTER
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        # Basic validation only.
        # This accepts normal Gmail,
        # Outlook, Yahoo, college emails, etc.

        if not name:

            flash(
                "Please enter your name.",
                "error"
            )

            return render_template(
                "register.html"
            )

        if not email or "@" not in email:

            flash(
                "Please enter a valid email address.",
                "error"
            )

            return render_template(
                "register.html"
            )

        if not password:

            flash(
                "Please enter a password.",
                "error"
            )

            return render_template(
                "register.html"
            )

        if len(password) < 6:

            flash(
                "Password must contain at least 6 characters.",
                "error"
            )

            return render_template(
                "register.html"
            )

        connection = get_db()

        existing_user = connection.execute(
            """
            SELECT id

            FROM users

            WHERE LOWER(email) = ?
            """,
            (email,)
        ).fetchone()

        if existing_user:

            connection.close()

            flash(
                "An account with this email already exists. Please login.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        password_hash = generate_password_hash(
            password
        )

        connection.execute(
            """
            INSERT INTO users
            (
                name,
                email,
                password,
                role
            )

            VALUES (?, ?, ?, 'user')
            """,
            (
                name,
                email,
                password_hash
            )
        )

        connection.commit()

        connection.close()

        flash(
            "Account created successfully. Please login.",
            "success"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not email:

            flash(
                "Please enter your email.",
                "error"
            )

            return render_template(
                "login.html"
            )

        if not password:

            flash(
                "Please enter your password.",
                "error"
            )

            return render_template(
                "login.html"
            )

        connection = get_db()

        user = connection.execute(
            """
            SELECT *

            FROM users

            WHERE LOWER(email) = ?
            """,
            (email,)
        ).fetchone()

        connection.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session.clear()

            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["email"] = user["email"]
            session["role"] = user["role"]

            if user["role"] == "admin":

                return redirect(
                    url_for("admin")
                )

            return redirect(
                url_for("index")
            )

        flash(
            "Invalid email or password.",
            "error"
        )

    return render_template(
        "login.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("login")
    )


# ============================================================
# PREDICT / CREATE TICKET
# ============================================================

@app.route("/predict", methods=["POST"])
def predict():

    if not login_required():

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    data = request.get_json(
        silent=True
    )

    if data:

        ticket_text = data.get(
            "ticket",
            ""
        ).strip()

    else:

        ticket_text = request.form.get(
            "ticket",
            ""
        ).strip()

    if not ticket_text:

        return jsonify({
            "success": False,
            "message": "Please enter your IT problem."
        }), 400

    if model is None:

        return jsonify({
            "success": False,
            "message": "AI model is not available."
        }), 500

    # ========================================================
    # AI PREDICTION
    # ========================================================

    category = model.predict(
        [ticket_text]
    )[0]

    # ========================================================
    # CONFIDENCE
    # ========================================================

    confidence = 0.0

    try:

        probabilities = model.predict_proba(
            [ticket_text]
        )

        confidence = max(
            probabilities[0]
        ) * 100

    except Exception:

        confidence = 0.0

    # ========================================================
    # PRIORITY
    # ========================================================

    priority = determine_priority(
        ticket_text
    )

    # ========================================================
    # TEAM
    # ========================================================

    assigned_team = TEAM_MAPPING.get(
        category,
        "General IT Support"
    )

    # ========================================================
    # SAVE TICKET
    # ========================================================

    created_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    connection = get_db()

    cursor = connection.execute(
        """
        INSERT INTO tickets
        (
            user_id,
            ticket,
            category,
            priority,
            assigned_team,
            confidence,
            status,
            created_at
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session["user_id"],
            ticket_text,
            category,
            priority,
            assigned_team,
            confidence,
            "Open",
            created_at
        )
    )

    ticket_id = cursor.lastrowid

    connection.commit()

    connection.close()

    return jsonify({

        "success": True,

        "ticket_id": ticket_id,

        "ticket": ticket_text,

        "category": category,

        "priority": priority,

        "assigned_team": assigned_team,

        "confidence": round(
            confidence,
            2
        ),

        "status": "Open",

        "created_at": created_at,

        "message": "Ticket created successfully."

    })


# ============================================================
# MY TICKETS
# ============================================================

@app.route("/my_tickets")
def my_tickets():

    if not login_required():

        return redirect(
            url_for("login")
        )

    connection = get_db()

    tickets = connection.execute(
        """
        SELECT *

        FROM tickets

        WHERE user_id = ?

        ORDER BY id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    connection.close()

    return render_template(
        "index.html",
        username=session.get("name"),
        email=session.get("email"),
        tickets=tickets
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin")
def admin():

    if not admin_required():

        flash(
            "Admin access required.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    connection = get_db()

    total_tickets = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM tickets
        """
    ).fetchone()["count"]

    open_tickets = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM tickets
        WHERE status = 'Open'
        """
    ).fetchone()["count"]

    in_progress = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM tickets
        WHERE status = 'In Progress'
        """
    ).fetchone()["count"]

    resolved = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM tickets
        WHERE status = 'Resolved'
        """
    ).fetchone()["count"]

    high_priority = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM tickets
        WHERE priority = 'High'
        """
    ).fetchone()["count"]

    # LEFT JOIN ensures tickets still appear
    # even if a user record is missing.

    tickets = connection.execute(
        """
        SELECT
            tickets.*,

            COALESCE(
                users.name,
                'Unknown User'
            ) AS user_name,

            COALESCE(
                users.email,
                'Unknown Email'
            ) AS user_email

        FROM tickets

        LEFT JOIN users

        ON tickets.user_id = users.id

        ORDER BY tickets.id DESC

        LIMIT 100
        """
    ).fetchall()

    connection.close()

    return render_template(
        "admin.html",

        tickets=tickets,

        total_tickets=total_tickets,

        open_tickets=open_tickets,

        in_progress=in_progress,

        resolved=resolved,

        high_priority=high_priority
    )


# ============================================================
# ADMIN TICKETS API
# ============================================================

@app.route("/admin/tickets")
def admin_tickets():

    if not admin_required():

        return jsonify({

            "success": False,

            "message": "Admin access required."

        }), 403

    connection = get_db()

    tickets = connection.execute(
        """
        SELECT
            tickets.*,

            COALESCE(
                users.name,
                'Unknown User'
            ) AS user_name,

            COALESCE(
                users.email,
                'Unknown Email'
            ) AS user_email

        FROM tickets

        LEFT JOIN users

        ON tickets.user_id = users.id

        ORDER BY tickets.id DESC
        """
    ).fetchall()

    connection.close()

    result = []

    for ticket in tickets:

        result.append({

            "id": ticket["id"],

            "user_name": ticket["user_name"],

            "user_email": ticket["user_email"],

            "ticket": ticket["ticket"],

            "category": ticket["category"],

            "priority": ticket["priority"],

            "assigned_team": ticket["assigned_team"],

            "confidence": round(
                ticket["confidence"],
                2
            ),

            "status": ticket["status"],

            "created_at": ticket["created_at"]

        })

    return jsonify({

        "success": True,

        "tickets": result

    })


# ============================================================
# UPDATE TICKET STATUS
# ============================================================

@app.route(
    "/admin/update_status",
    methods=["POST"]
)
def update_status():

    if not admin_required():

        return jsonify({
            "success": False,
            "message": "Admin access required."
        }), 403

    data = request.get_json(
        silent=True
    )

    if data:

        ticket_id = data.get("ticket_id")
        status = data.get("status")

    else:

        ticket_id = request.form.get(
            "ticket_id"
        )

        status = request.form.get(
            "status"
        )

    allowed_statuses = [
        "Open",
        "In Progress",
        "Resolved"
    ]

    if status not in allowed_statuses:

        return jsonify({
            "success": False,
            "message": "Invalid status."
        }), 400

    connection = get_db()

    connection.execute(
        """
        UPDATE tickets

        SET status = ?

        WHERE id = ?
        """,
        (
            status,
            ticket_id
        )
    )

    connection.commit()

    connection.close()

    return jsonify({

        "success": True,

        "message": "Ticket status updated."

    })


# ============================================================
# UPDATE TEAM
# ============================================================

@app.route(
    "/admin/update_team",
    methods=["POST"]
)
def update_team():

    if not admin_required():

        return jsonify({
            "success": False,
            "message": "Admin access required."
        }), 403

    data = request.get_json(
        silent=True
    )

    if data:

        ticket_id = data.get("ticket_id")
        team = data.get("team")

    else:

        ticket_id = request.form.get(
            "ticket_id"
        )

        team = request.form.get(
            "team"
        )

    if team not in ALLOWED_TEAMS:

        return jsonify({
            "success": False,
            "message": "Invalid team."
        }), 400

    connection = get_db()

    connection.execute(
        """
        UPDATE tickets

        SET assigned_team = ?

        WHERE id = ?
        """,
        (
            team,
            ticket_id
        )
    )

    connection.commit()

    connection.close()

    return jsonify({

        "success": True,

        "message": "Support team updated."

    })


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    return jsonify({

        "status": "healthy",

        "application": "HelpGenie"

    })


# ============================================================
# INITIALIZE DATABASE
# ============================================================

init_db()

create_admin_from_env()


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )