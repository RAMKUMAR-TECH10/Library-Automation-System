import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "library.db")
LOG_PATH = os.path.join(BASE_DIR, "library.log")

DATE_FORMAT = "%Y-%m-%d"
DEFAULT_BORROW_DAYS = 14
DEFAULT_FINE_PER_DAY = 5.0

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.ERROR,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("library")


def connect(db_path=None):
    path = db_path or DB_PATH
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def get_connection(db_path=None):
    connection = None
    try:
        connection = connect(db_path)
        yield connection
        connection.commit()
    except Exception as error:
        if connection is not None:
            connection.rollback()
        if isinstance(error, sqlite3.Error):
            logger.exception("Database transaction failed")
        raise
    finally:
        if connection is not None:
            connection.close()


def initialize_database(db_path=None):
    try:
        with get_connection(db_path) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS books (
                    book_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    category TEXT NOT NULL,
                    total_copies INTEGER NOT NULL CHECK (total_copies > 0),
                    available_copies INTEGER NOT NULL
                        CHECK (available_copies >= 0 AND available_copies <= total_copies)
                );

                CREATE TABLE IF NOT EXISTS members (
                    member_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    phone TEXT NOT NULL UNIQUE,
                    join_date TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id TEXT NOT NULL,
                    member_id TEXT NOT NULL,
                    issue_date TEXT NOT NULL,
                    due_date TEXT NOT NULL,
                    return_date TEXT,
                    fine REAL NOT NULL DEFAULT 0,
                    status TEXT NOT NULL CHECK (status IN ('Issued', 'Returned')),
                    FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE RESTRICT,
                    FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE RESTRICT
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_books_title ON books(title);
                CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
                CREATE INDEX IF NOT EXISTS idx_books_category ON books(category);
                CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
                CREATE INDEX IF NOT EXISTS idx_transactions_member ON transactions(member_id);
                CREATE INDEX IF NOT EXISTS idx_transactions_book ON transactions(book_id);
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                ("borrow_days", str(DEFAULT_BORROW_DAYS)),
            )
            connection.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                ("fine_per_day", str(DEFAULT_FINE_PER_DAY)),
            )
    except sqlite3.Error:
        logger.exception("Could not initialize the database")
        raise


def get_setting(key, db_path=None):
    with get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
    return row["value"] if row else None


def set_setting(key, value, db_path=None):
    with get_connection(db_path) as connection:
        connection.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )


def row_to_dict(row):
    return dict(row) if row is not None else None


def rows_to_dicts(rows):
    return [dict(row) for row in rows]


def seed_sample_data(db_path=None):
    books = [
        ("B101", "Python Basics", "John Smith", "Programming", 5),
        ("B102", "Data Structures", "Mark Lee", "Programming", 3),
        ("B103", "Database Systems", "David Miller", "Databases", 4),
        ("B104", "Computer Networks", "Anna Thomas", "Networking", 2),
        ("B105", "Operating Systems", "Peter Jones", "Systems", 3),
    ]
    members = [
        ("M101", "Arun Kumar", "arun@example.com", "9876543210"),
        ("M102", "Kumar Raja", "kumar@example.com", "9876543211"),
        ("M103", "Priya Sharma", "priya@example.com", "9876543212"),
    ]
    today = date.today()
    with get_connection(db_path) as connection:
        connection.executemany(
            "INSERT OR IGNORE INTO books "
            "(book_id, title, author, category, total_copies, available_copies) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [(b[0], b[1], b[2], b[3], b[4], b[4]) for b in books],
        )
        connection.executemany(
            "INSERT OR IGNORE INTO members "
            "(member_id, name, email, phone, join_date) VALUES (?, ?, ?, ?, ?)",
            [(m[0], m[1], m[2], m[3], today.isoformat()) for m in members],
        )
        for member_id, book_id, issue_date, return_date in [
            ("M101", "B101", today - timedelta(days=20), None),
            ("M102", "B102", today - timedelta(days=5), None),
            ("M103", "B103", today - timedelta(days=40), today - timedelta(days=25)),
        ]:
            exists = connection.execute(
                "SELECT 1 FROM transactions WHERE member_id = ? AND book_id = ? "
                "AND issue_date = ?",
                (member_id, book_id, issue_date.isoformat()),
            ).fetchone()
            if exists:
                continue
            due_date = issue_date + timedelta(days=DEFAULT_BORROW_DAYS)
            connection.execute(
                "INSERT INTO transactions "
                "(book_id, member_id, issue_date, due_date, return_date, fine, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    book_id,
                    member_id,
                    issue_date.isoformat(),
                    due_date.isoformat(),
                    return_date.isoformat() if return_date else None,
                    DEFAULT_FINE_PER_DAY * 15 if return_date else 0,
                    "Returned" if return_date else "Issued",
                ),
            )
            connection.execute(
                "UPDATE books SET available_copies = available_copies - 1 "
                "WHERE book_id = ?",
                (book_id,),
            )
