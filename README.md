# Library Automation System Using Python

A modular Python application for automated book inventory management, member
registration, book issuing, returns, fine calculation and reporting. It uses a
Tkinter desktop interface and a permanent SQLite database.

## 1. Project description

Traditional libraries maintain book details, member information and borrowing
records manually. That causes duplicate entries, lost records and difficulty
tracking borrowed books. This system stores all records in one SQLite database
and automates the daily operations of a librarian.

## 2. Objectives

- Apply modular Python programming using separate files for each responsibility.
- Validate every important user input before saving it.
- Process book issues, returns, due dates and overdue fines automatically.
- Handle invalid input, missing records, duplicate entries and database errors.
- Provide a simple graphical interface with a dashboard and reports.

## 3. Features

- Add, update, delete, search and list books with total and available copies.
- Register, update, delete and search members with automatically generated IDs.
- Issue books only to registered members when copies are available.
- Automatic 14-day due date (configurable).
- Return processing with overdue-day calculation and fine calculation.
- Configurable fine rate (default Rs. 5 per overdue day).
- Search books by title, author, category or book ID; members by name or ID.
- Dashboard cards, recent activity, overdue books, popular books and monthly
  borrowing statistics.
- Borrowing history for each member.
- Error logging to `library.log`.
- Sample data option for quick demonstrations.

## 4. Technologies used

| Technology | Purpose |
| --- | --- |
| Python 3.10+ | Main programming language |
| Tkinter | Graphical user interface |
| SQLite (`sqlite3`) | Data storage |
| `datetime` | Issue dates, due dates and overdue calculations |
| `os` | File and directory paths |
| `logging` | Error log file |
| `unittest` | Unit tests |

No external dependencies are needed.

## 5. Folder structure

```text
Library_Automation_System/
├── main.py                 Application entry point
├── database.py             SQLite connection, tables, settings and logging
├── book_manager.py         Book operations
├── member_manager.py       Member operations
├── issue_return.py         Issue, return and fine calculations
├── validation.py           Input validation functions
├── reports.py              Dashboard and reports
├── gui.py                  Tkinter user interface
├── library.db              SQLite database (created automatically)
├── library.log             Error log (created automatically)
├── requirements.txt        Project dependencies
├── README.md               This documentation
├── tests/
│   └── test_library.py     Unit tests
└── screenshots/            Application screenshots
```

## 6. Installation

```powershell
cd Library_Automation_System
python --version
```

Python 3.10 or newer is required. Install nothing else; `tkinter` and
`sqlite3` are part of the standard Python installation on Windows.

## 7. How to run

Start with an empty database:

```powershell
python main.py
```

Start with sample books, members and borrowing records for demonstration:

```powershell
python main.py --seed
```

Use a different database file:

```powershell
python main.py --db my_library.db
```

## 8. Database information

`database.py` creates the following tables on first run.

### books

| Column | Type | Description |
| --- | --- | --- |
| book_id | TEXT | Primary key |
| title | TEXT | Book title |
| author | TEXT | Author name |
| category | TEXT | Category |
| total_copies | INTEGER | Total copies, greater than zero |
| available_copies | INTEGER | Available copies, never negative |

### members

| Column | Type | Description |
| --- | --- | --- |
| member_id | TEXT | Primary key |
| name | TEXT | Member name |
| email | TEXT | Email address |
| phone | TEXT | 10-digit phone number, unique |
| join_date | TEXT | Registration date (YYYY-MM-DD) |

### transactions

| Column | Type | Description |
| --- | --- | --- |
| transaction_id | INTEGER | Primary key (auto increment) |
| book_id | TEXT | Foreign key to books |
| member_id | TEXT | Foreign key to members |
| issue_date | TEXT | Date of issue |
| due_date | TEXT | Expected return date |
| return_date | TEXT | Actual return date |
| fine | REAL | Fine amount |
| status | TEXT | Issued or Returned |

A `settings` table stores the configurable borrowing period and fine rate.
Foreign keys are enabled, and issuing or returning uses a single SQLite
transaction so book availability and transaction status cannot become
inconsistent.

## 9. Validation and error handling

- Book and member IDs: required and unique.
- Titles, authors, categories and names: required, not numbers only.
- Total copies: positive integer; availability cannot be negative.
- Email: standard email format.
- Phone: exactly 10 digits in Indian format (starts with 6-9).
- Dates: `YYYY-MM-DD`; return date cannot be earlier than issue date.
- Books without available copies cannot be issued.
- A transaction can be returned only once.
- Expected problems show a dialog; unexpected problems are written to
  `library.log`.

## 10. Testing

```powershell
python -m unittest discover -s tests -v
```

The test suite uses a temporary database and covers validation, duplicate
entries, missing records, issuing, returns, overdue fines and search.

## 11. Future enhancements

- Librarian login with username and password.
- Barcode scanning for book IDs.
- Due-date reminders and email notifications.
- Charts for borrowing trends and fine collection.
- Export reports to CSV or PDF.
