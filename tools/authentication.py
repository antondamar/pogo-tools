import bcrypt
from psycopg2 import IntegrityError
from psycopg2.errorcodes import UNIQUE_VIOLATION
from tools.db import get_db_connection


def login(username, password):
    USER_LOGIN_QUERY = """
        SELECT * 
        FROM users 
        WHERE username = %s;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(USER_LOGIN_QUERY, (username,))
                user = cursor.fetchone()

                if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                    return (user["id"], user["username"])
                else:
                    return
    except Exception as e:
        return f"Error {e}"


def create_account(username, email, password):
    USER_INFO_UPLOAD = """
        INSERT INTO users (username, email, password_hash)
        VALUES (%s, %s, %s)
    """

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                pw_encrypt = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                cursor.execute(USER_INFO_UPLOAD, (username, email, pw_encrypt))
                conn.commit()
                return "success"
    except IntegrityError as e:
        if e.pgcode != UNIQUE_VIOLATION:
            raise
        constraint = e.diag.constraint_name
        if constraint and "username" in constraint:
            return "username"
        if constraint and "email" in constraint:
            return "email"
        return "unknown"
