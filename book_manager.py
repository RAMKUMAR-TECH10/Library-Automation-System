import database
import validation


class BookManager:
    SEARCH_FIELDS = ("book_id", "title", "author", "category")

    def __init__(self, db_path=None):
        self.db_path = db_path

    def add_book(self, book_id, title, author, category, total_copies):
        data = validation.require_book_data(book_id, title, author, category, total_copies)
        with database.get_connection(self.db_path) as connection:
            if connection.execute(
                "SELECT 1 FROM books WHERE book_id = ?", (data["book_id"],)
            ).fetchone():
                raise ValueError(f"Book ID '{data['book_id']}' already exists.")
            connection.execute(
                "INSERT INTO books "
                "(book_id, title, author, category, total_copies, available_copies) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    data["book_id"],
                    data["title"],
                    data["author"],
                    data["category"],
                    data["total_copies"],
                    data["total_copies"],
                ),
            )
        return self.get_book(data["book_id"])

    def _fetch_book(self, connection, book_id):
        row = connection.execute(
            "SELECT * FROM books WHERE book_id = ?", (book_id,)
        ).fetchone()
        if row is None:
            raise LookupError(f"Book '{book_id}' was not found.")
        return database.row_to_dict(row)

    def update_book(self, book_id, title, author, category, total_copies):
        book_id = validation.require_book_id(book_id)
        data = validation.require_book_data(
            book_id, title, author, category, total_copies
        )
        with database.get_connection(self.db_path) as connection:
            book = self._fetch_book(connection, book_id)
            borrowed = book["total_copies"] - book["available_copies"]
            if data["total_copies"] < borrowed:
                raise ValueError(
                    f"Cannot set copies below {borrowed} currently borrowed copy/copies."
                )
            connection.execute(
                "UPDATE books SET title = ?, author = ?, category = ?, "
                "total_copies = ?, available_copies = ? WHERE book_id = ?",
                (
                    data["title"],
                    data["author"],
                    data["category"],
                    data["total_copies"],
                    book["available_copies"] + (data["total_copies"] - book["total_copies"]),
                    book_id,
                ),
            )
        return self.get_book(book_id)

    def delete_book(self, book_id):
        book_id = validation.require_book_id(book_id)
        with database.get_connection(self.db_path) as connection:
            self._fetch_book(connection, book_id)
            history = connection.execute(
                "SELECT COUNT(*) AS count FROM transactions WHERE book_id = ?",
                (book_id,),
            ).fetchone()["count"]
            if history:
                raise ValueError(
                    "Cannot delete a book with borrowing history. "
                    "Keeping history is required for reports."
                )
            connection.execute("DELETE FROM books WHERE book_id = ?", (book_id,))

    def get_book(self, book_id):
        book_id = validation.require_book_id(book_id)
        with database.get_connection(self.db_path) as connection:
            return self._fetch_book(connection, book_id)

    def get_all_books(self):
        with database.get_connection(self.db_path) as connection:
            rows = connection.execute("SELECT * FROM books ORDER BY book_id").fetchall()
        return database.rows_to_dicts(rows)

    def get_available_books(self):
        with database.get_connection(self.db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM books WHERE available_copies > 0 ORDER BY title"
            ).fetchall()
        return database.rows_to_dicts(rows)

    def search_books(self, query, field="all"):
        if field != "all" and field not in self.SEARCH_FIELDS:
            raise ValueError("Invalid search field for books.")
        query = str(query or "").strip()
        with database.get_connection(self.db_path) as connection:
            if field == "all":
                sql = (
                    "SELECT * FROM books WHERE book_id LIKE ? OR title LIKE ? "
                    "OR author LIKE ? OR category LIKE ? ORDER BY book_id"
                )
                params = [f"%{query}%"] * 4
            else:
                sql = f"SELECT * FROM books WHERE {field} LIKE ? ORDER BY book_id"
                params = [f"%{query}%"]
            rows = connection.execute(sql, params).fetchall()
        return database.rows_to_dicts(rows)
