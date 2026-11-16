from datetime import date, timedelta

import database
import validation


class IssueReturnManager:
    def __init__(self, db_path=None):
        self.db_path = db_path

    @property
    def borrow_days(self):
        return int(database.get_setting("borrow_days", self.db_path))

    @property
    def fine_per_day(self):
        return float(database.get_setting("fine_per_day", self.db_path))

    def set_borrow_period(self, days):
        value = validation.require_borrow_days(days)
        database.set_setting("borrow_days", value, self.db_path)
        return value

    def set_fine_rate(self, amount):
        value = validation.require_fine_per_day(amount)
        database.set_setting("fine_per_day", value, self.db_path)
        return value

    def _transaction_row(self, connection, transaction_id):
        row = connection.execute(
            "SELECT t.transaction_id, t.book_id, b.title, t.member_id, m.name, "
            "t.issue_date, t.due_date, t.return_date, t.fine, t.status "
            "FROM transactions t "
            "JOIN books b ON b.book_id = t.book_id "
            "JOIN members m ON m.member_id = t.member_id "
            "WHERE t.transaction_id = ?",
            (transaction_id,),
        ).fetchone()
        if row is None:
            raise LookupError(f"Transaction #{transaction_id} was not found.")
        return database.row_to_dict(row)

    def issue_book(self, book_id, member_id, issue_date=None):
        book_id = validation.require_book_id(book_id)
        member_id = validation.require_member_id(member_id)
        issue_dt = (
            validation.require_issue_date(issue_date) if issue_date else date.today()
        )
        due_dt = issue_dt + timedelta(days=self.borrow_days)

        with database.get_connection(self.db_path) as connection:
            book = connection.execute(
                "SELECT book_id, title, available_copies FROM books WHERE book_id = ?",
                (book_id,),
            ).fetchone()
            if book is None:
                raise LookupError(f"Book '{book_id}' was not found.")
            member = connection.execute(
                "SELECT member_id, name FROM members WHERE member_id = ?",
                (member_id,),
            ).fetchone()
            if member is None:
                raise LookupError(f"Member '{member_id}' was not found.")
            if book["available_copies"] <= 0:
                raise RuntimeError(
                    f"No copies of '{book['title']}' are currently available."
                )

            updated = connection.execute(
                "UPDATE books SET available_copies = available_copies - 1 "
                "WHERE book_id = ? AND available_copies > 0",
                (book_id,),
            )
            if updated.rowcount != 1:
                raise RuntimeError("Book availability changed; please try again.")

            transaction_id = connection.execute(
                "INSERT INTO transactions "
                "(book_id, member_id, issue_date, due_date, fine, status) "
                "VALUES (?, ?, ?, ?, 0, 'Issued')",
                (book_id, member_id, issue_dt.isoformat(), due_dt.isoformat()),
            ).lastrowid
            result = self._transaction_row(connection, transaction_id)

        return result

    def return_book(self, transaction_id, return_date=None):
        transaction_id = validation.require_transaction_id(transaction_id)
        fine_rate = self.fine_per_day

        with database.get_connection(self.db_path) as connection:
            transaction = self._transaction_row(connection, transaction_id)
            if transaction["status"] != "Issued":
                raise RuntimeError("This transaction has already been returned.")

            return_dt = (
                validation.parse_date(return_date, "Return date")
                if return_date
                else date.today()
            )
            validation.require_return_date(
                return_dt.isoformat(), transaction["issue_date"]
            )
            due_dt = validation.parse_date(transaction["due_date"], "Due date")
            overdue_days = max(0, (return_dt - due_dt).days)
            fine = round(overdue_days * fine_rate, 2)

            updated = connection.execute(
                "UPDATE books SET available_copies = "
                "MIN(total_copies, available_copies + 1) WHERE book_id = ?",
                (transaction["book_id"],),
            )
            if updated.rowcount != 1:
                raise RuntimeError("Could not update book availability.")

            connection.execute(
                "UPDATE transactions SET return_date = ?, fine = ?, "
                "status = 'Returned' WHERE transaction_id = ?",
                (return_dt.isoformat(), fine, transaction_id),
            )
            result = self._transaction_row(connection, transaction_id)

        result["overdue_days"] = overdue_days
        return result

    def get_transaction(self, transaction_id):
        transaction_id = validation.require_transaction_id(transaction_id)
        with database.get_connection(self.db_path) as connection:
            return self._transaction_row(connection, transaction_id)

    def get_all_transactions(self, status=None):
        if status is not None and status not in ("Issued", "Returned"):
            raise ValueError("Status must be 'Issued' or 'Returned'.")
        query = (
            "SELECT t.transaction_id, t.book_id, b.title, t.member_id, m.name, "
            "t.issue_date, t.due_date, t.return_date, t.fine, t.status "
            "FROM transactions t "
            "JOIN books b ON b.book_id = t.book_id "
            "JOIN members m ON m.member_id = t.member_id "
        )
        params = []
        if status:
            query += "WHERE t.status = ? "
            params.append(status)
        query += "ORDER BY t.transaction_id DESC"
        with database.get_connection(self.db_path) as connection:
            rows = connection.execute(query, params).fetchall()
        return database.rows_to_dicts(rows)

    def get_active_transactions(self):
        return self.get_all_transactions(status="Issued")

    def get_overdue_transactions(self, as_of=None):
        as_of = as_of or date.today()
        with database.get_connection(self.db_path) as connection:
            rows = connection.execute(
                "SELECT t.transaction_id, t.book_id, b.title, t.member_id, m.name, "
                "t.issue_date, t.due_date, t.return_date, t.fine, t.status "
                "FROM transactions t "
                "JOIN books b ON b.book_id = t.book_id "
                "JOIN members m ON m.member_id = t.member_id "
                "WHERE t.status = 'Issued' AND t.due_date < ? "
                "ORDER BY t.due_date",
                (as_of.isoformat(),),
            ).fetchall()
        return database.rows_to_dicts(rows)
