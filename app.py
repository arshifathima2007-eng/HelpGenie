from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    session,
    flash
)

import os
import sqlite3
import joblib
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


# ============================================================
# APP CONFIGURATION
# ============================================================

app = Flask(__name__)

# Secret key for sessions
# On Render, we will set SECRET_KEY as an environment variable.
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "development-secret-key"
)

DATABASE = "helpgenie.db"
MODEL_FILE = "model.pkl"


# ============================================================
# LOAD AI MODEL
# ============================================================

try:

    model = joblib.load(MODEL_FILE)

    print("AI model loaded successfully.")

except Exception as e:

    model = None

    print("Error loading AI model:", e)


# ============================================================
# SUPPORT TEAM MAPPING
# ============================================================

TEAM_MAPPING = {

    "Network":
        "Network Support Team",

    "Hardware":
        "Hardware Support Team",

    "Software":
        "Software Support Team",

    "Account":
        "Account Support Team",

    "Email":
        "Email Support Team",

    "Security":
        "Cybersecurity Team",

    "Printer":
        "Hardware Support Team"

}


# ============================================================
# ALLOWED SUPPORT TEAMS
# ============================================================

ALLOWED_TEAMS = [

    "Network Support Team",

    "Hardware Support Team",

    "Software Support Team",

    "Account Support Team",

    "Email Support Team",

    "Cybersecurity Team",

    "General IT Support Team"

]


# ============================================================
# PRIORITY KEYWORDS
# ============================================================

HIGH_PRIORITY_WORDS = [

    "hacked",
    "hack",
    "virus",
    "malware",
    "security",
    "data breach",
    "stolen",
    "ransomware",
    "phishing",
    "urgent",
    "emergency"

]


LOW_PRIORITY_WORDS = [

    "question",
    "information",
    "help",
    "request"

]


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db():

    connection = sqlite3.connect(
        DATABASE
    )

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_db():

    connection = get_db()

    # --------------------------------------------------------
    # USERS TABLE
    # --------------------------------------------------------

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL,

            role TEXT DEFAULT 'user'

        )
        """
    )

    # --------------------------------------------------------
    # TICKETS TABLE
    # --------------------------------------------------------

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

            status TEXT DEFAULT 'Open',

            created_at TEXT NOT NULL,

            FOREIGN KEY (user_id)
            REFERENCES users(id)

        )
        """
    )

    connection.commit()

    connection.close()

    print("Database initialized successfully.")


# ============================================================
# PRIORITY DETECTION
# ============================================================

def determine_priority(ticket, category):

    text = ticket.lower()

    # Security problems are automatically high priority
    if category == "Security":

        return "High"

    # Check high priority keywords
    for word in HIGH_PRIORITY_WORDS:

        if word in text:

            return "High"

    # Check low priority keywords
    for word in LOW_PRIORITY_WORDS:

        if word in text:

            return "Low"

    # Default
    return "Medium"


# ============================================================
# LOGIN REQUIRED CHECK
# ============================================================

def login_required():

    if "user_id" not in session:

        return False

    return True


# ============================================================
# ADMIN ACCESS CHECK
# ============================================================

def admin_required():

    if "user_id" not in session:

        return False

    if session.get("role") != "admin":

        return False

    return True


# ============================================================
# HOME / USER DASHBOARD
# ============================================================

@app.route("/")
def home():

    # User must login
    if not login_required():

        return redirect(
            url_for("login")
        )

    # Admin goes to admin dashboard
    if session.get("role") == "admin":

        return redirect(
            url_for("admin_dashboard")
        )

    return render_template(
        "index.html",
        name=session.get("name"),
        email=session.get("email")
    )


# ============================================================
# REGISTER
# ============================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
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

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not name or not email or not password:

            flash(
                "All fields are required.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        if len(password) < 6:

            flash(
                "Password must contain at least 6 characters.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        # ----------------------------------------------------
        # DATABASE
        # ----------------------------------------------------

        connection = get_db()

        existing_user = connection.execute(
            """
            SELECT id
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        if existing_user:

            connection.close()

            flash(
                "An account with this email already exists.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        # Hash password
        hashed_password = generate_password_hash(
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
                hashed_password
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

@app.route(
    "/login",
    methods=["GET", "POST"]
)
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

        connection = get_db()

        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        connection.close()

        # ----------------------------------------------------
        # CHECK LOGIN
        # ----------------------------------------------------

        if user and check_password_hash(
            user["password"],
            password
        ):

            # Store login information in session
            session["user_id"] = user["id"]

            session["name"] = user["name"]

            session["email"] = user["email"]

            session["role"] = user["role"]

            # Admin dashboard
            if user["role"] == "admin":

                return redirect(
                    url_for("admin_dashboard")
                )

            # Normal user dashboard
            return redirect(
                url_for("home")
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
# AI TICKET PREDICTION
# ============================================================

@app.route(
    "/predict",
    methods=["POST"]
)
def predict():

    # --------------------------------------------------------
    # LOGIN CHECK
    # --------------------------------------------------------

    if not login_required():

        return jsonify({
            "error":
                "Please login first."
        }), 401

    # --------------------------------------------------------
    # MODEL CHECK
    # --------------------------------------------------------

    if model is None:

        return jsonify({
            "error":
                "AI model is not available."
        }), 500

    # --------------------------------------------------------
    # REQUEST DATA
    # --------------------------------------------------------

    data = request.get_json()

    if not data:

        return jsonify({
            "error":
                "Invalid request."
        }), 400

    ticket_text = data.get(
        "ticket",
        ""
    ).strip()

    # --------------------------------------------------------
    # EMPTY TICKET CHECK
    # --------------------------------------------------------

    if not ticket_text:

        return jsonify({
            "error":
                "Please enter your IT problem."
        }), 400

    # Limit very large requests
    if len(ticket_text) > 1000:

        return jsonify({
            "error":
                "Ticket description cannot exceed 1000 characters."
        }), 400

    # --------------------------------------------------------
    # AI PREDICTION
    # --------------------------------------------------------

    try:

        prediction = model.predict(
            [ticket_text]
        )[0]

        category = str(
            prediction
        )

    except Exception as e:

        print(
            "Prediction error:",
            e
        )

        return jsonify({
            "error":
                "Unable to analyze the ticket."
        }), 500

    # --------------------------------------------------------
    # CONFIDENCE
    # --------------------------------------------------------

    confidence = 0.0

    try:

        probabilities = model.predict_proba(
            [ticket_text]
        )

        confidence = (
            float(
                max(probabilities[0])
            )
            * 100
        )

    except Exception as e:

        print(
            "Confidence calculation error:",
            e
        )

        confidence = 0.0

    # --------------------------------------------------------
    # ASSIGN SUPPORT TEAM
    # --------------------------------------------------------

    assigned_team = TEAM_MAPPING.get(
        category,
        "General IT Support Team"
    )

    # --------------------------------------------------------
    # DETERMINE PRIORITY
    # --------------------------------------------------------

    priority = determine_priority(
        ticket_text,
        category
    )

    # --------------------------------------------------------
    # DEFAULT STATUS
    # --------------------------------------------------------

    status = "Open"

    # --------------------------------------------------------
    # DATE / TIME
    # --------------------------------------------------------

    created_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # --------------------------------------------------------
    # SAVE TICKET
    # --------------------------------------------------------

    connection = get_db()

    try:

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
                status,
                created_at
            )
        )

        ticket_id = cursor.lastrowid

        connection.commit()

    except Exception as e:

        connection.rollback()

        print(
            "Database error:",
            e
        )

        connection.close()

        return jsonify({
            "error":
                "Unable to save the ticket."
        }), 500

    connection.close()

    # --------------------------------------------------------
    # SEND RESULT TO FRONTEND
    # --------------------------------------------------------

    return jsonify({

        "success":
            True,

        "ticket_id":
            ticket_id,

        "ticket":
            ticket_text,

        "category":
            category,

        "priority":
            priority,

        "team":
            assigned_team,

        "confidence":
            round(
                confidence,
                2
            ),

        "status":
            status,

        "created_at":
            created_at

    })


# ============================================================
# USER TICKET HISTORY
# ============================================================

@app.route("/my_tickets")
def my_tickets():

    if not login_required():

        return jsonify({
            "error":
                "Please login first."
        }), 401

    connection = get_db()

    tickets = connection.execute(
        """
        SELECT
            id,
            ticket,
            category,
            priority,
            assigned_team,
            confidence,
            status,
            created_at
        FROM tickets
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (
            session["user_id"],
        )
    ).fetchall()

    connection.close()

    ticket_list = []

    for ticket in tickets:

        ticket_list.append({

            "id":
                ticket["id"],

            "ticket":
                ticket["ticket"],

            "category":
                ticket["category"],

            "priority":
                ticket["priority"],

            "team":
                ticket["assigned_team"],

            "confidence":
                round(
                    float(
                        ticket["confidence"]
                    ),
                    2
                ),

            "status":
                ticket["status"],

            "created_at":
                ticket["created_at"]

        })

    return jsonify(
        ticket_list
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin")
def admin_dashboard():

    if not admin_required():

        flash(
            "Admin access required.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "admin.html",
        name=session.get("name")
    )


# ============================================================
# ADMIN — GET ALL TICKETS
# ============================================================

@app.route("/admin/tickets")
def admin_tickets():

    if not admin_required():

        return jsonify({
            "error":
                "Admin access required."
        }), 403

    connection = get_db()

    tickets = connection.execute(
        """
        SELECT
            tickets.id,
            tickets.ticket,
            tickets.category,
            tickets.priority,
            tickets.assigned_team,
            tickets.confidence,
            tickets.status,
            tickets.created_at,
            users.name AS user_name,
            users.email AS user_email

        FROM tickets

        INNER JOIN users
        ON tickets.user_id = users.id

        ORDER BY tickets.id DESC
        """
    ).fetchall()

    connection.close()

    ticket_list = []

    for ticket in tickets:

        ticket_list.append({

            "id":
                ticket["id"],

            "ticket":
                ticket["ticket"],

            "category":
                ticket["category"],

            "priority":
                ticket["priority"],

            "team":
                ticket["assigned_team"],

            "confidence":
                round(
                    float(
                        ticket["confidence"]
                    ),
                    2
                ),

            "status":
                ticket["status"],

            "created_at":
                ticket["created_at"],

            "user_name":
                ticket["user_name"],

            "user_email":
                ticket["user_email"]

        })

    return jsonify(
        ticket_list
    )


# ============================================================
# ADMIN — STATISTICS
# ============================================================

@app.route("/admin/stats")
def admin_stats():

    if not admin_required():

        return jsonify({
            "error":
                "Admin access required."
        }), 403

    connection = get_db()

    # Total tickets
    total = connection.execute(
        """
        SELECT COUNT(*)
        FROM tickets
        """
    ).fetchone()[0]

    # High priority tickets
    high = connection.execute(
        """
        SELECT COUNT(*)
        FROM tickets
        WHERE priority = 'High'
        """
    ).fetchone()[0]

    # Open tickets
    open_tickets = connection.execute(
        """
        SELECT COUNT(*)
        FROM tickets
        WHERE status = 'Open'
        """
    ).fetchone()[0]

    # In progress
    in_progress = connection.execute(
        """
        SELECT COUNT(*)
        FROM tickets
        WHERE status = 'In Progress'
        """
    ).fetchone()[0]

    # Resolved
    resolved = connection.execute(
        """
        SELECT COUNT(*)
        FROM tickets
        WHERE status = 'Resolved'
        """
    ).fetchone()[0]

    # Normal users
    total_users = connection.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE role = 'user'
        """
    ).fetchone()[0]

    connection.close()

    return jsonify({

        "total":
            total,

        "high":
            high,

        "open":
            open_tickets,

        "in_progress":
            in_progress,

        "resolved":
            resolved,

        "users":
            total_users

    })


# ============================================================
# ADMIN — UPDATE TICKET STATUS
# ============================================================

@app.route(
    "/admin/update_status",
    methods=["POST"]
)
def update_ticket_status():

    if not admin_required():

        return jsonify({
            "error":
                "Admin access required."
        }), 403

    data = request.get_json()

    if not data:

        return jsonify({
            "error":
                "Invalid request."
        }), 400

    ticket_id = data.get(
        "ticket_id"
    )

    status = data.get(
        "status"
    )

    allowed_statuses = [

        "Open",

        "In Progress",

        "Resolved"

    ]

    if not ticket_id:

        return jsonify({
            "error":
                "Ticket ID is required."
        }), 400

    if status not in allowed_statuses:

        return jsonify({
            "error":
                "Invalid status."
        }), 400

    connection = get_db()

    cursor = connection.execute(
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

    updated = cursor.rowcount

    connection.close()

    if updated == 0:

        return jsonify({
            "error":
                "Ticket not found."
        }), 404

    return jsonify({

        "success":
            True,

        "message":
            "Ticket status updated successfully."

    })


# ============================================================
# ADMIN — UPDATE ASSIGNED TEAM
# ============================================================

@app.route(
    "/admin/update_team",
    methods=["POST"]
)
def update_ticket_team():

    if not admin_required():

        return jsonify({
            "error":
                "Admin access required."
        }), 403

    data = request.get_json()

    if not data:

        return jsonify({
            "error":
                "Invalid request."
        }), 400

    ticket_id = data.get(
        "ticket_id"
    )

    team = data.get(
        "team"
    )

    if not ticket_id:

        return jsonify({
            "error":
                "Ticket ID is required."
        }), 400

    if team not in ALLOWED_TEAMS:

        return jsonify({
            "error":
                "Invalid support team."
        }), 400

    connection = get_db()

    cursor = connection.execute(
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

    updated = cursor.rowcount

    connection.close()

    if updated == 0:

        return jsonify({
            "error":
                "Ticket not found."
        }), 404

    return jsonify({

        "success":
            True,

        "message":
            "Support team updated successfully."

    })


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    return jsonify({

        "status":
            "healthy",

        "application":
            "HelpGenie",

        "ai_model":
            "loaded" if model is not None
            else "not loaded"

    })


# ============================================================
# APPLICATION START
# ============================================================

# ============================================================
# INITIALIZE DATABASE
# ============================================================

init_db()


# ============================================================
# APPLICATION START
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )