import os
import sys
import tempfile
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import book_manager
import database
import issue_return
import member_manager
import reports
import validation


class TestValidation(unittest.TestCase):
    def test_valid_phone(self):
        self.assertTrue(validation.validate_phone("9876543210"))

    def test_invalid_phone(self):
        self.assertFalse(validation.validate_phone("12345"))

    def test_valid_title(self):
        self.assertTrue(validation.validate_book_title("Python Basics"))

    def test_empty_title(self):
        self.assertFalse(validation.validate_book_title(""))

    def test_valid_email(self):
        self.assertTrue(validation.validate_email("student@gmail.com"))

    def test_invalid_email(self):
        self.assertFalse(validation.validate_email("student-at-gmail.com"))

    def test_invalid_date(self):
        self.assertFalse(validation.validate_date("31-11-2026"))

    def test_return_before_issue(self):
        self.assertFalse(validation.validate_return_date("2026-11-10", "2026-11-16"))

    def test_name_cannot_be_only_numbers(self):
        self.assertFalse(validation.validate_member_name("12345"))


class TestLibrary(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_library.db")
        database.initialize_database(self.db_path)
        self.books = book_manager.BookManager(self.db_path)
        self.members = member_manager.MemberManager(self.db_path)
        self.transactions = issue_return.IssueReturnManager(self.db_path)
        self.report_manager = reports.ReportManager(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def add_sample_book(self, book_id="B101", copies=2):
        return self.books.add_book(book_id, "Python Basics", "John Smith", "Programming", copies)

    def add_sample_member(self):
        return self.members.add_member("Arun", "arun@example.com", "9876543210")

    def test_add_valid_book(self):
        book = self.add_sample_book()
        self.assertEqual(book["title"], "Python Basics")
        self.assertEqual(book["available_copies"], 2)

    def test_add_duplicate_book_id(self):
        self.add_sample_book()
        with self.assertRaises(ValueError):
            self.add_sample_book()

    def test_add_book_with_invalid_copies(self):
        with self.assertRaises(validation.ValidationError):
            self.books.add_book("B110", "Title", "Author", "Category", -1)

    def test_register_valid_member_with_generated_id(self):
        member = self.add_sample_member()
        self.assertEqual(member["member_id"], "M101")

    def test_register_member_with_invalid_email(self):
        with self.assertRaises(validation.ValidationError):
            self.members.add_member("Arun", "bad-email", "9876543210")

    def test_search_existing_book(self):
        self.add_sample_book()
        results = self.books.search_books("Python", "title")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["book_id"], "B101")

    def test_search_invalid_id(self):
        self.add_sample_book()
        with self.assertRaises(LookupError):
            self.books.get_book("B999")

    def test_delete_book_with_history_is_blocked(self):
        self.add_sample_book()
        member = self.add_sample_member()
        self.transactions.issue_book("B101", member["member_id"])
        with self.assertRaises(ValueError):
            self.books.delete_book("B101")

    def test_issue_available_book(self):
        self.add_sample_book()
        member = self.add_sample_member()
        result = self.transactions.issue_book("B101", member["member_id"])
        expected_due = date.today() + timedelta(days=14)
        self.assertEqual(result["due_date"], expected_due.isoformat())
        self.assertEqual(result["status"], "Issued")
        self.assertEqual(self.books.get_book("B101")["available_copies"], 1)

    def test_issue_unavailable_book(self):
        self.add_sample_book(copies=1)
        member = self.add_sample_member()
        self.transactions.issue_book("B101", member["member_id"])
        with self.assertRaises(RuntimeError):
            self.transactions.issue_book("B101", member["member_id"])

    def test_issue_unknown_book(self):
        self.add_sample_member()
        with self.assertRaises(LookupError):
            self.transactions.issue_book("B404", "M101")

    def test_issue_with_invalid_date(self):
        self.add_sample_book()
        self.add_sample_member()
        with self.assertRaises(validation.ValidationError):
            self.transactions.issue_book("B101", "M101", "16/11/2026")

    def test_return_issued_book_without_fine(self):
        self.add_sample_book()
        member = self.add_sample_member()
        issued = self.transactions.issue_book("B101", member["member_id"])
        result = self.transactions.return_book(issued["transaction_id"])
        self.assertEqual(result["status"], "Returned")
        self.assertEqual(result["fine"], 0)
        self.assertEqual(self.books.get_book("B101")["available_copies"], 2)

    def test_return_overdue_book_calculates_fine(self):
        self.add_sample_book()
        member = self.add_sample_member()
        issue_date = date.today() - timedelta(days=20)
        return_date = date.today() - timedelta(days=3)
        issued = self.transactions.issue_book(
            "B101", member["member_id"], issue_date.isoformat()
        )
        result = self.transactions.return_book(
            issued["transaction_id"], return_date.isoformat()
        )
        self.assertEqual(result["overdue_days"], 3)
        self.assertEqual(result["fine"], 15.0)

    def test_return_twice_is_rejected(self):
        self.add_sample_book()
        member = self.add_sample_member()
        issued = self.transactions.issue_book("B101", member["member_id"])
        self.transactions.return_book(issued["transaction_id"])
        with self.assertRaises(RuntimeError):
            self.transactions.return_book(issued["transaction_id"])

    def test_return_date_before_issue_is_rejected(self):
        self.add_sample_book()
        member = self.add_sample_member()
        issued = self.transactions.issue_book("B101", member["member_id"])
        with self.assertRaises(validation.ValidationError):
            self.transactions.return_book(issued["transaction_id"], "2000-01-01")

    def test_configurable_period_and_fine(self):
        self.assertEqual(self.transactions.borrow_days, 14)
        self.assertEqual(self.transactions.fine_per_day, 5.0)
        self.transactions.set_borrow_period(7)
        self.transactions.set_fine_rate(10.5)
        self.add_sample_book()
        member = self.add_sample_member()
        issued = self.transactions.issue_book("B101", member["member_id"])
        self.assertEqual(
            issued["due_date"],
            (date.today() + timedelta(days=7)).isoformat(),
        )
        self.assertEqual(self.transactions.fine_per_day, 10.5)

    def test_dashboard_statistics(self):
        self.add_sample_book(copies=3)
        self.add_sample_member()
        self.transactions.issue_book("B101", "M101")
        stats = self.report_manager.get_dashboard_stats()
        self.assertEqual(stats["total_copies"], 3)
        self.assertEqual(stats["available_copies"], 2)
        self.assertEqual(stats["borrowed_copies"], 1)
        self.assertEqual(stats["total_members"], 1)
        self.assertEqual(stats["active_loans"], 1)

    def test_member_borrowing_history(self):
        self.add_sample_book()
        member = self.add_sample_member()
        self.transactions.issue_book("B101", member["member_id"])
        history = self.members.get_borrowing_history("M101")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["title"], "Python Basics")


if __name__ == "__main__":
    unittest.main()
