import database
import issue_return
import member_manager
from datetime import date


class ReportManager:
    def __init__(self, db_path=None):
        self.db_path = db_path
        self.transactions = issue_return.IssueReturnManager(db_path)
        self.members = member_manager.MemberManager(db_path)

    def get_dashboard_stats(self):
        with database.get_connection(self.db_path) as connection:
            books = connection.execute(
                "SELECT COUNT(*) AS total_titles, "
                "COALESCE(SUM(total_copies), 0) AS total_copies, "
                "COALESCE(SUM(available_copies), 0) AS available_copies "
                "FROM books"
            ).fetchone()
            members = connection.execute(
                "SELECT COUNT(*) AS total_members FROM members"
            ).fetchone()["total_members"]
            loans = connection.execute(
                "SELECT "
                "SUM(CASE WHEN status = 'Issued' THEN 1 ELSE 0 END) AS active_loans, "
                "COALESCE(SUM(fine), 0) AS total_fines "
                "FROM transactions"
            ).fetchone()
            overdue = connection.execute(
                "SELECT COUNT(*) AS overdue_loans FROM transactions "
                "WHERE status = 'Issued' AND due_date < ?",
                (date.today().isoformat(),),
            ).fetchone()["overdue_loans"]

        stats = database.row_to_dict(books)
        stats["total_members"] = members
        stats["active_loans"] = loans["active_loans"] or 0
        stats["total_fines"] = round(loans["total_fines"] or 0, 2)
        stats["overdue_loans"] = overdue
        stats["borrowed_copies"] = stats["total_copies"] - stats["available_copies"]
        return stats

    def get_available_books(self):
        with database.get_connection(self.db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM books WHERE available_copies > 0 ORDER BY title"
            ).fetchall()
        return database.rows_to_dicts(rows)

    def get_borrowed_books(self):
        with database.get_connection(self.db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM books WHERE available_copies < total_copies ORDER BY title"
            ).fetchall()
        return database.rows_to_dicts(rows)

    def get_overdue_books(self):
        return self.transactions.get_overdue_transactions()

    def get_member_borrowing_history(self, member_id):
        return self.members.get_borrowing_history(member_id)

    def get_total_fines_collected(self):
        return self.get_dashboard_stats()["total_fines"]

    def get_popular_books(self, limit=5):
        with database.get_connection(self.db_path) as connection:
            rows = connection.execute(
                "SELECT b.book_id, b.title, COUNT(*) AS times_issued "
                "FROM transactions t JOIN books b ON b.book_id = t.book_id "
                "GROUP BY b.book_id ORDER BY times_issued DESC, b.title LIMIT ?",
                (limit,),
            ).fetchall()
        return database.rows_to_dicts(rows)

    def get_monthly_borrowing_stats(self, limit=6):
        with database.get_connection(self.db_path) as connection:
            rows = connection.execute(
                "SELECT substr(issue_date, 1, 7) AS month, COUNT(*) AS issues "
                "FROM transactions GROUP BY month ORDER BY month DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return database.rows_to_dicts(rows)
