import sqlite3

from werkzeug.security import generate_password_hash


DATABASE = "helpgenie.db"


print("======================================")
print("       HELPGENIE ADMIN CREATOR")
print("======================================")


name = input("Enter admin name: ").strip()

email = input("Enter admin email: ").strip().lower()

password = input("Enter admin password: ")


if not name or not email or not password:

    print("\nAll fields are required.")

    exit()


if len(password) < 6:

    print("\nPassword must contain at least 6 characters.")

    exit()


connection = sqlite3.connect(DATABASE)

cursor = connection.cursor()


# Check whether email already exists

existing_user = cursor.execute(
    """
    SELECT id
    FROM users
    WHERE email = ?
    """,
    (email,)
).fetchone()


if existing_user:

    # Update existing account to admin

    cursor.execute(
        """
        UPDATE users

        SET
            name = ?,
            password = ?,
            role = 'admin'

        WHERE email = ?
        """,
        (
            name,
            generate_password_hash(password),
            email
        )
    )

    print("\nExisting account converted to ADMIN.")


else:

    # Create new admin

    cursor.execute(
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
            name,
            email,
            generate_password_hash(password)
        )
    )

    print("\nNew ADMIN account created.")


connection.commit()

connection.close()


print("\n======================================")
print("       ADMIN ACCOUNT READY")
print("======================================")
print(f"Name  : {name}")
print(f"Email : {email}")
print("Role  : admin")
print("======================================")