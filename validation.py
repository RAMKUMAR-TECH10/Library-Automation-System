import re
from datetime import date, datetime

import database


class ValidationError(ValueError):
    pass


EMAIL_PATTERN = re.compile(r"^[\w.+-]+@[\w.-]+\.\w+$")
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,19}$")


def _ensure_not_empty(value, field_name):
    if value is None or str(value).strip() == "":
        raise ValidationError(f"{field_name} is required.")
    return str(value).strip()


def require_book_id(book_id):
    book_id = _ensure_not_empty(book_id, "Book ID")
    if not ID_PATTERN.match(book_id):
        raise ValidationError("Book ID must be 2-20 chars: letters, numbers, _ or -.")
    return book_id


def require_member_id(member_id):
    member_id = _ensure_not_empty(member_id, "Member ID")
    if not ID_PATTERN.match(member_id):
        raise ValidationError("Member ID must be 2-20 chars: letters, numbers, _ or -.")
    return member_id


def require_book_title(title):
    return _ensure_not_empty(title, "Book title")


def require_author(author):
    author = _ensure_not_empty(author, "Author")
    if author.isdigit():
        raise ValidationError("Author cannot contain only numbers.")
    return author


def require_category(category):
    category = _ensure_not_empty(category, "Category")
    if category.isdigit():
        raise ValidationError("Category cannot contain only numbers.")
    return category


def require_member_name(name):
    name = _ensure_not_empty(name, "Member name")
    if name.isdigit() or not re.search(r"[A-Za-z]", name):
        raise ValidationError("Member name must contain letters and cannot be only numbers.")
    return name


def require_email(email):
    email = _ensure_not_empty(email, "Email").lower()
    if not EMAIL_PATTERN.match(email):
        raise ValidationError("Enter a valid email address.")
    return email


def require_phone(phone):
    phone = _ensure_not_empty(phone, "Phone")
    if not (phone.isdigit() and len(phone) == 10):
        raise ValidationError("Phone must contain exactly 10 digits.")
    return phone


def require_total_copies(copies, allow_zero=False):
    raw = _ensure_not_empty(copies, "Total copies")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValidationError("Total copies must be a positive integer.")
    if value < 0 or (value == 0 and not allow_zero):
        raise ValidationError("Total copies must be a positive integer.")
    return value


def parse_date(value, field_name):
    value = _ensure_not_empty(value, field_name)
    try:
        return datetime.strptime(value, database.DATE_FORMAT).date()
    except ValueError:
        raise ValidationError(
            f"{field_name} must be in YYYY-MM-DD format (e.g. {date.today().isoformat()})."
        )


def require_date(value, field_name="Date", allow_future=True):
    parsed = parse_date(value, field_name)
    if not allow_future and parsed > date.today():
        raise ValidationError(f"{field_name} cannot be in the future.")
    return parsed


def require_issue_date(issue_date):
    return require_date(issue_date, "Issue date", allow_future=False)


def require_return_date(return_date, issue_date_value=None):
    return_dt = require_date(return_date, "Return date", allow_future=False)
    if issue_date_value:
        issue_dt = parse_date(issue_date_value, "Issue date")
        if return_dt < issue_dt:
            raise ValidationError("Return date cannot be earlier than issue date.")
    return return_dt


def require_borrow_days(days):
    raw = _ensure_not_empty(days, "Borrow days")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValidationError("Borrow days must be a positive integer.")
    if value <= 0:
        raise ValidationError("Borrow days must be a positive integer.")
    return value


def require_fine_per_day(amount):
    raw = _ensure_not_empty(amount, "Fine per day")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValidationError("Fine per day must be a non-negative number.")
    if value < 0:
        raise ValidationError("Fine per day must be a non-negative number.")
    return value


def require_transaction_id(transaction_id):
    raw = _ensure_not_empty(transaction_id, "Transaction ID")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValidationError("Transaction ID must be a positive integer.")
    if value <= 0:
        raise ValidationError("Transaction ID must be a positive integer.")
    return value


def require_book_data(book_id, title, author, category, total_copies):
    return {
        "book_id": require_book_id(book_id),
        "title": require_book_title(title),
        "author": require_author(author),
        "category": require_category(category),
        "total_copies": require_total_copies(total_copies),
    }


def require_member_data(member_id, name, email, phone):
    return {
        "member_id": require_member_id(member_id),
        "name": require_member_name(name),
        "email": require_email(email),
        "phone": require_phone(phone),
    }


def _is_valid(requirement, *args, **kwargs):
    try:
        requirement(*args, **kwargs)
        return True
    except ValidationError:
        return False


def validate_book_id(book_id):
    return _is_valid(require_book_id, book_id)


def validate_member_id(member_id):
    return _is_valid(require_member_id, member_id)


def validate_book_title(title):
    return _is_valid(require_book_title, title)


def validate_author(author):
    return _is_valid(require_author, author)


def validate_category(category):
    return _is_valid(require_category, category)


def validate_member_name(name):
    return _is_valid(require_member_name, name)


def validate_email(email):
    return _is_valid(require_email, email)


def validate_phone(phone):
    return _is_valid(require_phone, phone)


def validate_total_copies(copies):
    return _is_valid(require_total_copies, copies)


def validate_date(value, field_name="Date"):
    return _is_valid(require_date, value, field_name)


def validate_issue_date(issue_date):
    return _is_valid(require_issue_date, issue_date)


def validate_return_date(return_date, issue_date_value=None):
    return _is_valid(require_return_date, return_date, issue_date_value)


def validate_borrow_days(days):
    return _is_valid(require_borrow_days, days)


def validate_fine_per_day(amount):
    return _is_valid(require_fine_per_day, amount)


def validate_transaction_id(transaction_id):
    return _is_valid(require_transaction_id, transaction_id)
