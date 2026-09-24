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
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "development-secret-key"
)


# ============================================================
# CONFIGURATION
# ============================================================

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
# TEAM MAPPING
# ============================================================

TEAM_MAPPING = {

    "Network": "Network Support Team",

    "Hardware": "Hardware Support Team",

    "Software": "Software Support Team",

    "Account": "Account Support Team",

    "Email": "Email Support Team",

    "Security": "Cybersecurity Team",

    "Printer": "Hardware Support Team"

}


# ============================================================
# ALLOWED TEAMS
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

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_db():

    connection = get_db()

    # USERS TABLE
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

    # TICKETS TABLE
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
# CREATE ADMIN FROM RENDER ENVIRONMENT VARIABLES
# ============================================================

def create_admin_from_env():

    admin_name = os.environ.get("ADMIN_NAME")

    admin_email = os.environ.get("ADMIN_EMAIL")

    admin_password = os.environ.get("ADMIN_PASSWORD")

    if not admin_name or not admin_email or not admin_password:

        print("Admin environment variables not configured.")

        return

    admin_email = admin_email.strip().lower()

    connection = get_db()

    existing = connection.execute(

        "SELECT id FROM users WHERE email = ?",

        (admin_email,)

    ).fetchone()

    if not existing:

        connection.execute(

            """
            INSERT INTO users
            (name, email, password, role)

            VALUES (?, ?, ?, 'admin')
            """,

            (
                admin_name.strip(),

                admin_email,

                generate_password_hash(admin_password)

            )

        )

        connection.commit()

        print("Admin account created successfully.")

    else:

        print("Admin account already exists.")

    connection.close()


# ============================================================
# LOGIN CHECK
# ============================================================

def login_required():

    return "user_id" in session


# ============================================================
# ADMIN CHECK
# ============================================================

def admin_required():

    return (

        "user_id" in session

        and

        session.get("role") == "admin"

    )


# ============================================================
# DETERMINE PRIORITY
# ============================================================

def determine_priority(ticket_text):

    text = ticket_text.lower()

    for word in HIGH_PRIORITY_WORDS:

        if word in text:

            return "High"

    for word in LOW_PRIORITY_WORDS:

        if word in text:

            return "Low"

    return "Medium"


# ============================================================
# ASSIGN SUPPORT TEAM
# ============================================================

def assign_team(category):

    return TEAM_MAPPING.get(

        category,

        "General IT Support Team"

    )


# ============================================================
# HOME / USER DASHBOARD
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

        if not name or not email or not password:

            flash(
                "Please fill in all fields.",
                "error"
            )

            return redirect(
                url_for("register")
            )

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
                "Email already registered.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        hashed_password = generate_password_hash(
            password
        )

        connection.execute(

            """
            INSERT INTO users
            (name, email, password, role)

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
            "Registration successful. Please login.",
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

        if user and check_password_hash(

            user["password"],

            password

        ):

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

        return redirect(
            url_for("login")
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
# CREATE TICKET / AI PREDICTION
# ============================================================

@app.route("/predict", methods=["POST"])
def predict():

    if not login_required():

        return jsonify({

            "success": False,

            "message": "Please login first."

        }), 401

    if model is None:

        return jsonify({

            "success": False,

            "message": "AI model is not available."

        }), 500

    data = request.get_json(
        silent=True
    )

    ticket_text = ""

    if data:

        ticket_text = data.get(
            "ticket",
            ""
        ).strip()

    if not ticket_text:

        ticket_text = request.form.get(
            "ticket",
            ""
        ).strip()

    if not ticket_text:

        return jsonify({

            "success": False,

            "message": "Please enter your IT problem."

        }), 400

    # AI CATEGORY
    prediction = model.predict(
        [ticket_text]
    )[0]

    category = str(prediction)

    # CONFIDENCE
    confidence = 0.0

    try:

        probabilities = model.predict_proba(
            [ticket_text]
        )[0]

        confidence = float(
            max(probabilities)
        ) * 100

    except Exception:

        confidence = 0.0

    # PRIORITY
    priority = determine_priority(
        ticket_text
    )

    # TEAM
    assigned_team = assign_team(
        category
    )

    # SAVE TICKET
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

            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

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

        "created_at": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

        "message": "Ticket created successfully."

    })


# ============================================================
# USER TICKET HISTORY
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

    tickets = connection.execute(

        """
        SELECT
            tickets.*,
            users.name AS user_name,
            users.email AS user_email

        FROM tickets

        JOIN users
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
            users.name AS user_name,
            users.email AS user_email

        FROM tickets

        JOIN users
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
# ADMIN STATISTICS
# ============================================================

@app.route("/admin/stats")
def admin_stats():

    if not admin_required():

        return jsonify({

            "success": False,

            "message": "Admin access required."

        }), 403

    connection = get_db()

    category_rows = connection.execute(

        """
        SELECT
            category,
            COUNT(*) AS count

        FROM tickets

        GROUP BY category

        ORDER BY count DESC
        """

    ).fetchall()

    priority_rows = connection.execute(

        """
        SELECT
            priority,
            COUNT(*) AS count

        FROM tickets

        GROUP BY priority
        """

    ).fetchall()

    status_rows = connection.execute(

        """
        SELECT
            status,
            COUNT(*) AS count

        FROM tickets

        GROUP BY status
        """

    ).fetchall()

    team_rows = connection.execute(

        """
        SELECT
            assigned_team,
            COUNT(*) AS count

        FROM tickets

        GROUP BY assigned_team

        ORDER BY count DESC
        """

    ).fetchall()

    connection.close()

    return jsonify({

        "success": True,

        "categories": [

            {
                "category": row["category"],
                "count": row["count"]
            }

            for row in category_rows

        ],

        "priorities": [

            {
                "priority": row["priority"],
                "count": row["count"]
            }

            for row in priority_rows

        ],

        "statuses": [

            {
                "status": row["status"],
                "count": row["count"]
            }

            for row in status_rows

        ],

        "teams": [

            {
                "team": row["assigned_team"],
                "count": row["count"]
            }

            for row in team_rows

        ]

    })


# ============================================================
# ADMIN UPDATE STATUS
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
    ) or {}

    ticket_id = data.get(
        "ticket_id"
    )

    status = data.get(
        "status"
    )

    allowed_statuses = [

        "Open",

        "In Progress",

        "Resolved",

        "Closed"

    ]

    if not ticket_id:

        return jsonify({

            "success": False,

            "message": "Ticket ID is required."

        }), 400

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
# ADMIN UPDATE TEAM
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
    ) or {}

    ticket_id = data.get(
        "ticket_id"
    )

    team = data.get(
        "team"
    )

    if not ticket_id:

        return jsonify({

            "success": False,

            "message": "Ticket ID is required."

        }), 400

    if team not in ALLOWED_TEAMS:

        return jsonify({

            "success": False,

            "message": "Invalid support team."

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

        "application": "HelpGenie",

        "ai_model": (

            "loaded"

            if model is not None

            else "not loaded"

        )

    })


# ============================================================
# INITIALIZE DATABASE
# ============================================================

init_db()


# ============================================================
# CREATE ADMIN
# ============================================================

create_admin_from_env()


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(

        debug=True,

        host="0.0.0.0",

        port=5000

    )