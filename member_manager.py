import re
from datetime import date

import database
import validation


class MemberManager:
    SEARCH_FIELDS = ("member_id", "name", "email", "phone")

    def __init__(self, db_path=None):
        self.db_path = db_path

    def generate_member_id(self):
        with database.get_connection(self.db_path) as connection:
            rows = connection.execute("SELECT member_id FROM members").fetchall()
        numbers = [
            int(match.group(1))
            for row in rows
            for match in [re.match(r"^M(\d+)$", row["member_id"])]
            if match
        ]
        return f"M{max(numbers) + 1 if numbers else 101:03d}"

    def _fetch_member(self, connection, member_id):
        row = connection.execute(
            "SELECT * FROM members WHERE member_id = ?", (member_id,)
        ).fetchone()
        if row is None:
            raise LookupError(f"Member '{member_id}' was not found.")
        return database.row_to_dict(row)

    def add_member(self, name, email, phone, member_id=None):
        if member_id in (None, ""):
            member_id = self.generate_member_id()
        data = validation.require_member_data(member_id, name, email, phone)
        with database.get_connection(self.db_path) as connection:
            if connection.execute(
                "SELECT 1 FROM members WHERE member_id = ?", (data["member_id"],)
            ).fetchone():
                raise ValueError(f"Member ID '{data['member_id']}' already exists.")
            if connection.execute(
                "SELECT 1 FROM members WHERE phone = ?", (data["phone"],)
            ).fetchone():
                raise ValueError("A member with this phone number already exists.")
            connection.execute(
                "INSERT INTO members (member_id, name, email, phone, join_date) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    data["member_id"],
                    data["name"],
                    data["email"],
                    data["phone"],
                    date.today().isoformat(),
                ),
            )
        return self.get_member(data["member_id"])

    def update_member(self, member_id, name, email, phone):
        member_id = validation.require_member_id(member_id)
        data = validation.require_member_data(member_id, name, email, phone)
        with database.get_connection(self.db_path) as connection:
            self._fetch_member(connection, member_id)
            if connection.execute(
                "SELECT 1 FROM members WHERE phone = ? AND member_id <> ?",
                (data["phone"], member_id),
            ).fetchone():
                raise ValueError("A member with this phone number already exists.")
            connection.execute(
                "UPDATE members SET name = ?, email = ?, phone = ? "
                "WHERE member_id = ?",
                (data["name"], data["email"], data["phone"], member_id),
            )
        return self.get_member(member_id)

    def delete_member(self, member_id):
        member_id = validation.require_member_id(member_id)
        with database.get_connection(self.db_path) as connection:
            self._fetch_member(connection, member_id)
            history = connection.execute(
                "SELECT COUNT(*) AS count FROM transactions WHERE member_id = ?",
                (member_id,),
            ).fetchone()["count"]
            if history:
                raise ValueError(
                    "Cannot delete a member with borrowing history. "
                    "Keeping history is required for reports."
                )
            connection.execute("DELETE FROM members WHERE member_id = ?", (member_id,))

    def get_member(self, member_id):
        member_id = validation.require_member_id(member_id)
        with database.get_connection(self.db_path) as connection:
            return self._fetch_member(connection, member_id)

    def get_all_members(self):
        with database.get_connection(self.db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM members ORDER BY member_id"
            ).fetchall()
        return database.rows_to_dicts(rows)

    def search_members(self, query, field="all"):
        if field != "all" and field not in self.SEARCH_FIELDS:
            raise ValueError("Invalid search field for members.")
        query = str(query or "").strip()
        with database.get_connection(self.db_path) as connection:
            if field == "all":
                sql = (
                    "SELECT * FROM members WHERE member_id LIKE ? OR name LIKE ? "
                    "OR email LIKE ? OR phone LIKE ? ORDER BY member_id"
                )
                params = [f"%{query}%"] * 4
            else:
                sql = f"SELECT * FROM members WHERE {field} LIKE ? ORDER BY member_id"
                params = [f"%{query}%"]
            rows = connection.execute(sql, params).fetchall()
        return database.rows_to_dicts(rows)

    def get_borrowing_history(self, member_id):
        member_id = validation.require_member_id(member_id)
        with database.get_connection(self.db_path) as connection:
            self._fetch_member(connection, member_id)
            rows = connection.execute(
                "SELECT t.transaction_id, t.book_id, b.title, t.issue_date, "
                "t.due_date, t.return_date, t.fine, t.status "
                "FROM transactions t JOIN books b ON b.book_id = t.book_id "
                "WHERE t.member_id = ? ORDER BY t.issue_date DESC",
                (member_id,),
            ).fetchall()
        return database.rows_to_dicts(rows)
