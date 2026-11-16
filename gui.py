from datetime import date
import tkinter as tk
from tkinter import messagebox, ttk

import book_manager
import database
import issue_return
import member_manager
import reports
import validation

NAVY = "#0d2745"
BLUE = "#2563eb"
LIGHT = "#f4f7fb"
WHITE = "#ffffff"
TEXT = "#1f2937"
MUTED = "#6b7280"


def safe_action(action):
    def wrapped(*args, **kwargs):
        try:
            return action(*args, **kwargs)
        except (validation.ValidationError, ValueError, LookupError, RuntimeError) as error:
            messagebox.showerror("Error", str(error))
        except Exception as error:
            database.logger.exception("Unhandled error in GUI action")
            messagebox.showerror("Unexpected error", str(error))
    return wrapped


def populate_tree(tree, rows, columns):
    tree.delete(*tree.get_children())
    for row in rows:
        tree.insert(
            "",
            "end",
            values=[("" if row.get(column) is None else row.get(column)) for column in columns],
        )


def selected_values(tree, columns):
    item = tree.focus()
    if not item:
        return None
    return dict(zip(columns, tree.item(item, "values")))


class LibraryApp(tk.Tk):
    BOOK_COLUMNS = ("book_id", "title", "author", "category", "total_copies", "available_copies")
    MEMBER_COLUMNS = ("member_id", "name", "email", "phone", "join_date")
    TRANSACTION_COLUMNS = (
        "transaction_id", "book_id", "title", "member_id", "name",
        "issue_date", "due_date", "return_date", "fine", "status",
    )

    def __init__(self, db_path=None):
        super().__init__()
        self.db_path = db_path
        self.books = book_manager.BookManager(db_path)
        self.members = member_manager.MemberManager(db_path)
        self.transactions = issue_return.IssueReturnManager(db_path)
        self.reports = reports.ReportManager(db_path)
        self.card_labels = {}
        self.current_screen = tk.StringVar(value="dashboard")

        self.title("Library Automation System")
        self.geometry("1150x720")
        self.minsize(1000, 650)
        self.configure(bg=LIGHT)

        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TButton", padding=6)
        style.configure("Treeview", rowheight=26, fieldbackground=WHITE)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

        self._build_layout()
        self.show_screen("dashboard")

    def _build_layout(self):
        sidebar = tk.Frame(self, bg=NAVY, width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(
            sidebar, text="LIBRARY", bg=NAVY, fg=WHITE,
            font=("Segoe UI", 20, "bold"),
        ).pack(pady=(28, 0))
        tk.Label(
            sidebar, text="AUTOMATION SYSTEM", bg=NAVY, fg="#9ec5ff",
            font=("Segoe UI", 10, "bold"),
        ).pack(pady=(0, 28))

        navigation = [
            ("Dashboard", "dashboard"),
            ("Books", "books"),
            ("Members", "members"),
            ("Issue Book", "issue"),
            ("Return Book", "return"),
            ("Reports", "reports"),
        ]
        for text, screen in navigation:
            tk.Button(
                sidebar,
                text=text,
                anchor="w",
                padx=20,
                pady=9,
                bg=NAVY,
                fg=WHITE,
                activebackground=BLUE,
                activeforeground=WHITE,
                relief="flat",
                font=("Segoe UI", 11),
                command=lambda target=screen: self.show_screen(target),
            ).pack(fill="x", pady=2)

        tk.Label(
            sidebar, text="Python + SQLite + Tkinter", bg=NAVY,
            fg="#7fa6d0", font=("Segoe UI", 9),
        ).pack(side="bottom", pady=18)

        self.content = tk.Frame(self, bg=LIGHT)
        self.content.pack(side="right", fill="both", expand=True)

        self.screens = {
            "dashboard": self._build_dashboard(),
            "books": self._build_books(),
            "members": self._build_members(),
            "issue": self._build_issue(),
            "return": self._build_return(),
            "reports": self._build_reports(),
        }

    def _label(self, parent, text, size=16, bold=True):
        return tk.Label(
            parent, text=text, bg=LIGHT, fg=TEXT,
            font=("Segoe UI", size, "bold" if bold else "normal"),
        )

    def _field(self, parent, label, row, column, variable=None, width=24):
        variable = variable or tk.StringVar()
        tk.Label(parent, text=label, bg=LIGHT, fg=TEXT, font=("Segoe UI", 10)).grid(
            row=row, column=column, padx=(12, 4), pady=5, sticky="w"
        )
        ttk.Entry(parent, textvariable=variable, width=width).grid(
            row=row, column=column + 1, padx=(0, 12), pady=5, sticky="w"
        )
        return variable

    def _make_tree(self, parent, columns, headings, height=10, widths=None):
        frame = ttk.Frame(parent)
        tree = ttk.Treeview(frame, columns=columns, show="headings", height=height)
        for index, column in enumerate(columns):
            tree.heading(column, text=headings[index])
            tree.column(column, width=(widths[index] if widths else 140), anchor=tk.W)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)
        return frame, tree

    def show_screen(self, name):
        self.current_screen.set(name)
        for frame in self.screens.values():
            frame.pack_forget()
        self.screens[name].pack(fill="both", expand=True)
        refresh = getattr(self, f"refresh_{name}", None)
        if refresh:
            refresh()

    def _build_dashboard(self):
        frame = tk.Frame(self.content, bg=LIGHT)
        header = tk.Frame(frame, bg=LIGHT)
        header.pack(fill="x", padx=24, pady=(22, 6))
        self._label(header, "Dashboard").pack(side="left")
        ttk.Button(header, text="Refresh", command=self.refresh_dashboard).pack(side="right")

        cards = tk.Frame(frame, bg=LIGHT)
        cards.pack(fill="x", padx=18, pady=10)
        definitions = [
            ("total_copies", "TOTAL COPIES", BLUE),
            ("total_members", "MEMBERS", "#0f9d76"),
            ("active_loans", "BOOKS ISSUED", "#d97706"),
            ("overdue_loans", "OVERDUE BOOKS", "#dc2626"),
        ]
        for index, (key, title, color) in enumerate(definitions):
            card = tk.Frame(cards, bg=WHITE, bd=1, relief="ridge")
            card.grid(row=0, column=index, padx=8, pady=8, sticky="nsew")
            cards.columnconfigure(index, weight=1)
            tk.Label(card, text=title, bg=WHITE, fg=MUTED,
                     font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=16, pady=(14, 0))
            value = tk.Label(card, text="0", bg=WHITE, fg=color,
                             font=("Segoe UI", 28, "bold"))
            value.pack(anchor="w", padx=16, pady=(2, 4))
            self.card_labels[key] = value
            tk.Label(card, text="Updated just now", bg=WHITE, fg=MUTED,
                     font=("Segoe UI", 9)).pack(anchor="w", padx=16, pady=(0, 12))

        recent = tk.LabelFrame(
            frame, text="Recent borrowing activity", bg=LIGHT,
            font=("Segoe UI", 11, "bold"),
        )
        recent.pack(fill="both", expand=True, padx=24, pady=12)
        columns = ("transaction_id", "title", "name", "issue_date", "due_date", "status")
        headings = ("Txn ID", "Book", "Member", "Issue Date", "Due Date", "Status")
        tree_frame, self.dashboard_tree = self._make_tree(
            recent, columns, headings, height=12,
            widths=(90, 230, 170, 130, 130, 110),
        )
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        return frame

    @safe_action
    def refresh_dashboard(self):
        stats = self.reports.get_dashboard_stats()
        for key, value in self.card_labels.items():
            value.configure(text=str(stats[key]))
        recent = self.transactions.get_all_transactions()[:8]
        populate_tree(
            self.dashboard_tree, recent,
            ("transaction_id", "title", "name", "issue_date", "due_date", "status"),
        )

    def _build_books(self):
        frame = tk.Frame(self.content, bg=LIGHT)
        self._label(frame, "Book management").pack(anchor="w", padx=24, pady=(22, 8))

        search = tk.LabelFrame(frame, text="Search books", bg=LIGHT,
                               font=("Segoe UI", 11, "bold"))
        search.pack(fill="x", padx=24, pady=6)
        tk.Label(search, text="Search:", bg=LIGHT).grid(row=0, column=0, padx=(12, 4), pady=10)
        self.book_search_var = tk.StringVar()
        ttk.Entry(search, textvariable=self.book_search_var, width=32).grid(row=0, column=1)
        tk.Label(search, text="Field:", bg=LIGHT).grid(row=0, column=2, padx=(12, 4))
        self.book_search_field = ttk.Combobox(
            search, values=["all", "book_id", "title", "author", "category"],
            state="readonly", width=14,
        )
        self.book_search_field.set("all")
        self.book_search_field.grid(row=0, column=3)
        ttk.Button(search, text="Search", command=self.search_books).grid(row=0, column=4, padx=8)
        ttk.Button(search, text="Show All", command=self.refresh_books).grid(row=0, column=5)

        form = tk.LabelFrame(frame, text="Book details", bg=LIGHT,
                             font=("Segoe UI", 11, "bold"))
        form.pack(fill="x", padx=24, pady=8)
        self.book_vars = {
            key: tk.StringVar() for key in
            ("book_id", "title", "author", "category", "total_copies")
        }
        self._field(form, "Book ID", 0, 0, self.book_vars["book_id"])
        self._field(form, "Title", 0, 2, self.book_vars["title"], 30)
        self._field(form, "Author", 1, 0, self.book_vars["author"])
        self._field(form, "Category", 1, 2, self.book_vars["category"])
        self._field(form, "Total copies", 2, 0, self.book_vars["total_copies"], 10)

        buttons = tk.Frame(form, bg=LIGHT)
        buttons.grid(row=2, column=2, columnspan=2, sticky="w", padx=(0, 12), pady=5)
        ttk.Button(buttons, text="Add Book", command=self.add_book).pack(side="left", padx=3)
        ttk.Button(buttons, text="Update", command=self.update_book).pack(side="left", padx=3)
        ttk.Button(buttons, text="Delete", command=self.delete_book).pack(side="left", padx=3)
        ttk.Button(buttons, text="Clear", command=self.clear_book_form).pack(side="left", padx=3)

        table = tk.LabelFrame(frame, text="Books", bg=LIGHT, font=("Segoe UI", 11, "bold"))
        table.pack(fill="both", expand=True, padx=24, pady=(8, 18))
        headings = ("Book ID", "Title", "Author", "Category", "Total", "Available")
        tree_frame, self.book_tree = self._make_tree(
            table, self.BOOK_COLUMNS, headings, height=11,
            widths=(100, 230, 170, 140, 80, 95),
        )
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.book_tree.bind("<<TreeviewSelect>>", self.on_book_selected)
        return frame

    @safe_action
    def refresh_books(self):
        populate_tree(self.book_tree, self.books.get_all_books(), self.BOOK_COLUMNS)

    @safe_action
    def search_books(self):
        results = self.books.search_books(
            self.book_search_var.get(), self.book_search_field.get()
        )
        populate_tree(self.book_tree, results, self.BOOK_COLUMNS)
        if not results:
            messagebox.showinfo("Search", "No matching books found.")

    def clear_book_form(self):
        for variable in self.book_vars.values():
            variable.set("")
        self.book_tree.selection_remove(self.book_tree.selection())

    def on_book_selected(self, event=None):
        selected = selected_values(self.book_tree, self.BOOK_COLUMNS)
        if selected:
            for key, variable in self.book_vars.items():
                variable.set(selected[key])

    @safe_action
    def add_book(self):
        values = [self.book_vars[key].get() for key in
                  ("book_id", "title", "author", "category", "total_copies")]
        book = self.books.add_book(*values)
        messagebox.showinfo("Success", f"Book '{book['title']}' added successfully.")
        self.clear_book_form()
        self.refresh_books()

    @safe_action
    def update_book(self):
        values = [self.book_vars[key].get() for key in
                  ("book_id", "title", "author", "category", "total_copies")]
        book = self.books.update_book(*values)
        messagebox.showinfo("Success", f"Book '{book['title']}' updated successfully.")
        self.refresh_books()

    @safe_action
    def delete_book(self):
        book_id = self.book_vars["book_id"].get()
        if not messagebox.askyesno("Confirm", f"Delete book '{book_id}'?"):
            return
        self.books.delete_book(book_id)
        messagebox.showinfo("Success", "Book deleted successfully.")
        self.clear_book_form()
        self.refresh_books()

    def _build_members(self):
        frame = tk.Frame(self.content, bg=LIGHT)
        self._label(frame, "Member management").pack(anchor="w", padx=24, pady=(22, 8))

        search = tk.LabelFrame(frame, text="Search members", bg=LIGHT,
                               font=("Segoe UI", 11, "bold"))
        search.pack(fill="x", padx=24, pady=6)
        tk.Label(search, text="Search:", bg=LIGHT).grid(row=0, column=0, padx=(12, 4), pady=10)
        self.member_search_var = tk.StringVar()
        ttk.Entry(search, textvariable=self.member_search_var, width=32).grid(row=0, column=1)
        tk.Label(search, text="Field:", bg=LIGHT).grid(row=0, column=2, padx=(12, 4))
        self.member_search_field = ttk.Combobox(
            search, values=["all", "member_id", "name", "email", "phone"],
            state="readonly", width=14,
        )
        self.member_search_field.set("all")
        self.member_search_field.grid(row=0, column=3)
        ttk.Button(search, text="Search", command=self.search_members).grid(row=0, column=4, padx=8)
        ttk.Button(search, text="Show All", command=self.refresh_members).grid(row=0, column=5)

        form = tk.LabelFrame(frame, text="Member details", bg=LIGHT,
                             font=("Segoe UI", 11, "bold"))
        form.pack(fill="x", padx=24, pady=8)
        self.member_vars = {
            key: tk.StringVar() for key in ("member_id", "name", "email", "phone")
        }
        self._field(form, "Member ID", 0, 0, self.member_vars["member_id"])
        self._field(form, "Name", 0, 2, self.member_vars["name"], 28)
        self._field(form, "Email", 1, 0, self.member_vars["email"], 30)
        self._field(form, "Phone", 1, 2, self.member_vars["phone"])

        buttons = tk.Frame(form, bg=LIGHT)
        buttons.grid(row=2, column=0, columnspan=4, padx=8, pady=6)
        ttk.Button(buttons, text="Register", command=self.add_member).pack(side="left", padx=3)
        ttk.Button(buttons, text="Update", command=self.update_member).pack(side="left", padx=3)
        ttk.Button(buttons, text="Delete", command=self.delete_member).pack(side="left", padx=3)
        ttk.Button(buttons, text="History", command=self.show_member_history).pack(side="left", padx=3)
        ttk.Button(buttons, text="Clear", command=self.clear_member_form).pack(side="left", padx=3)
        ttk.Label(
            form, text="Leave Member ID empty to generate one automatically.",
            background=LIGHT, foreground=MUTED,
        ).grid(row=3, column=0, columnspan=4, sticky="w", padx=10, pady=(0, 8))

        table = tk.LabelFrame(frame, text="Members", bg=LIGHT,
                              font=("Segoe UI", 11, "bold"))
        table.pack(fill="both", expand=True, padx=24, pady=(8, 18))
        headings = ("Member ID", "Name", "Email", "Phone", "Joined")
        tree_frame, self.member_tree = self._make_tree(
            table, self.MEMBER_COLUMNS, headings, height=10,
            widths=(110, 180, 230, 140, 130),
        )
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.member_tree.bind("<<TreeviewSelect>>", self.on_member_selected)
        return frame

    @safe_action
    def refresh_members(self):
        populate_tree(self.member_tree, self.members.get_all_members(), self.MEMBER_COLUMNS)

    @safe_action
    def search_members(self):
        results = self.members.search_members(
            self.member_search_var.get(), self.member_search_field.get()
        )
        populate_tree(self.member_tree, results, self.MEMBER_COLUMNS)
        if not results:
            messagebox.showinfo("Search", "No matching members found.")

    def clear_member_form(self):
        for variable in self.member_vars.values():
            variable.set("")
        self.member_tree.selection_remove(self.member_tree.selection())

    def on_member_selected(self, event=None):
        selected = selected_values(self.member_tree, self.MEMBER_COLUMNS)
        if selected:
            for key, variable in self.member_vars.items():
                variable.set(selected[key])

    @safe_action
    def add_member(self):
        member = self.members.add_member(
            self.member_vars["name"].get(),
            self.member_vars["email"].get(),
            self.member_vars["phone"].get(),
            self.member_vars["member_id"].get() or None,
        )
        messagebox.showinfo(
            "Success", f"Member '{member['name']}' registered with ID {member['member_id']}."
        )
        self.clear_member_form()
        self.refresh_members()

    @safe_action
    def update_member(self):
        member = self.members.update_member(
            self.member_vars["member_id"].get(),
            self.member_vars["name"].get(),
            self.member_vars["email"].get(),
            self.member_vars["phone"].get(),
        )
        messagebox.showinfo("Success", f"Member '{member['name']}' updated successfully.")
        self.refresh_members()

    @safe_action
    def delete_member(self):
        member_id = self.member_vars["member_id"].get()
        if not messagebox.askyesno("Confirm", f"Delete member '{member_id}'?"):
            return
        self.members.delete_member(member_id)
        messagebox.showinfo("Success", "Member deleted successfully.")
        self.clear_member_form()
        self.refresh_members()

    @safe_action
    def show_member_history(self):
        member_id = self.member_vars["member_id"].get()
        history = self.members.get_borrowing_history(member_id)
        columns = ("transaction_id", "title", "issue_date", "due_date", "return_date", "fine", "status")
        headings = ("Txn ID", "Book", "Issue", "Due", "Returned", "Fine", "Status")
        self._show_table_window(
            f"Borrowing history - {member_id}", columns, headings, history,
            widths=(80, 200, 120, 120, 120, 80, 100),
        )

    def _show_table_window(self, title, columns, headings, rows, widths=None):
        window = tk.Toplevel(self)
        window.title(title)
        window.geometry("900x420")
        window.configure(bg=LIGHT)
        tree_frame, tree = self._make_tree(
            window, columns, headings, height=15, widths=widths
        )
        tree_frame.pack(fill="both", expand=True, padx=12, pady=12)
        populate_tree(tree, rows, columns)

    def _build_issue(self):
        frame = tk.Frame(self.content, bg=LIGHT)
        self._label(frame, "Issue a book").pack(anchor="w", padx=24, pady=(22, 8))

        form = tk.LabelFrame(frame, text="Issue details", bg=LIGHT,
                             font=("Segoe UI", 11, "bold"))
        form.pack(fill="x", padx=24, pady=6)
        tk.Label(form, text="Book ID", bg=LIGHT).grid(row=0, column=0, padx=(12, 4), pady=8, sticky="w")
        self.issue_book_var = tk.StringVar()
        self.issue_book_combo = ttk.Combobox(form, textvariable=self.issue_book_var, width=20)
        self.issue_book_combo.grid(row=0, column=1, padx=(0, 14), sticky="w")
        tk.Label(form, text="Member ID", bg=LIGHT).grid(row=0, column=2, padx=(12, 4), sticky="w")
        self.issue_member_var = tk.StringVar()
        self.issue_member_combo = ttk.Combobox(form, textvariable=self.issue_member_var, width=20)
        self.issue_member_combo.grid(row=0, column=3, sticky="w")
        self.issue_date_var = self._field(
            form, "Issue date (YYYY-MM-DD)", 1, 0, width=22
        )
        self.issue_date_var.set(date.today().isoformat())
        ttk.Button(form, text="Issue Book", command=self.issue_book).grid(
            row=1, column=2, padx=(12, 4), pady=8, sticky="w"
        )
        ttk.Button(form, text="Refresh Lists", command=self.refresh_issue).grid(
            row=1, column=3, pady=8, sticky="w"
        )
        self.issue_settings_var = tk.StringVar()
        tk.Label(form, textvariable=self.issue_settings_var, bg=LIGHT, fg=MUTED,
                 font=("Segoe UI", 9)).grid(
            row=2, column=0, columnspan=4, padx=12, pady=(0, 10), sticky="w"
        )

        table = tk.LabelFrame(frame, text="Currently issued books", bg=LIGHT,
                              font=("Segoe UI", 11, "bold"))
        table.pack(fill="both", expand=True, padx=24, pady=(8, 18))
        tree_frame, self.issue_tree = self._make_tree(
            table, self.TRANSACTION_COLUMNS,
            ("Txn ID", "Book ID", "Title", "Member ID", "Name",
             "Issue Date", "Due Date", "Return", "Fine", "Status"),
            height=12,
            widths=(80, 90, 180, 100, 150, 120, 120, 120, 80, 100),
        )
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        return frame

    @safe_action
    def refresh_issue(self):
        self.issue_book_combo.configure(
            values=[book["book_id"] for book in self.books.get_available_books()]
        )
        self.issue_member_combo.configure(
            values=[member["member_id"] for member in self.members.get_all_members()]
        )
        self.issue_settings_var.set(
            f"Borrowing period: {self.transactions.borrow_days} days | "
            f"Fine: Rs. {self.transactions.fine_per_day:g} per overdue day"
        )
        populate_tree(
            self.issue_tree,
            self.transactions.get_active_transactions(),
            self.TRANSACTION_COLUMNS,
        )

    @safe_action
    def issue_book(self):
        result = self.transactions.issue_book(
            self.issue_book_var.get(),
            self.issue_member_var.get(),
            self.issue_date_var.get(),
        )
        messagebox.showinfo(
            "Book issued",
            f"Transaction #{result['transaction_id']}\n"
            f"Book: {result['title']}\nMember: {result['name']}\n"
            f"Due date: {result['due_date']}",
        )
        self.issue_date_var.set(date.today().isoformat())
        self.refresh_issue()

    def _build_return(self):
        frame = tk.Frame(self.content, bg=LIGHT)
        self._label(frame, "Process a return").pack(anchor="w", padx=24, pady=(22, 8))

        form = tk.LabelFrame(frame, text="Return details", bg=LIGHT,
                             font=("Segoe UI", 11, "bold"))
        form.pack(fill="x", padx=24, pady=6)
        self.return_tx_var = self._field(form, "Transaction ID", 0, 0, width=18)
        self.return_date_var = self._field(
            form, "Return date (YYYY-MM-DD)", 0, 2, width=24
        )
        self.return_date_var.set(date.today().isoformat())
        ttk.Button(form, text="Find Transaction", command=self.find_transaction).grid(
            row=0, column=4, padx=8, sticky="w"
        )
        ttk.Button(form, text="Process Return", command=self.return_book).grid(
            row=1, column=4, padx=8, pady=6, sticky="w"
        )
        self.return_detail_var = tk.StringVar(
            value="Select a transaction from the table or enter its ID."
        )
        tk.Label(form, textvariable=self.return_detail_var, bg=LIGHT, fg=TEXT,
                 justify="left", font=("Segoe UI", 10)).grid(
            row=2, column=0, columnspan=5, padx=12, pady=(2, 10), sticky="w"
        )

        table = tk.LabelFrame(frame, text="Issued transactions", bg=LIGHT,
                              font=("Segoe UI", 11, "bold"))
        table.pack(fill="both", expand=True, padx=24, pady=(8, 18))
        tree_frame, self.return_tree = self._make_tree(
            table, self.TRANSACTION_COLUMNS,
            ("Txn ID", "Book ID", "Title", "Member ID", "Name",
             "Issue Date", "Due Date", "Return", "Fine", "Status"),
            height=12,
            widths=(80, 90, 180, 100, 150, 120, 120, 120, 80, 100),
        )
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.return_tree.bind("<<TreeviewSelect>>", self.on_return_selected)
        return frame

    @safe_action
    def refresh_return(self):
        populate_tree(
            self.return_tree,
            self.transactions.get_active_transactions(),
            self.TRANSACTION_COLUMNS,
        )

    def on_return_selected(self, event=None):
        selected = selected_values(self.return_tree, self.TRANSACTION_COLUMNS)
        if selected:
            self.return_tx_var.set(str(selected["transaction_id"]))

    @safe_action
    def find_transaction(self):
        transaction = self.transactions.get_transaction(self.return_tx_var.get())
        self.return_detail_var.set(
            f"Book: {transaction['title']} | Member: {transaction['name']} | "
            f"Issued: {transaction['issue_date']} | Due: {transaction['due_date']} | "
            f"Status: {transaction['status']}"
        )

    @safe_action
    def return_book(self):
        result = self.transactions.return_book(
            self.return_tx_var.get(), self.return_date_var.get()
        )
        messagebox.showinfo(
            "Return processed",
            f"Book: {result['title']}\nReturn date: {result['return_date']}\n"
            f"Overdue days: {result['overdue_days']}\nFine: Rs. {result['fine']:.2f}",
        )
        self.return_tx_var.set("")
        self.return_detail_var.set("Select a transaction from the table or enter its ID.")
        self.refresh_return()

    def _build_reports(self):
        frame = tk.Frame(self.content, bg=LIGHT)
        self._label(frame, "Reports and settings").pack(anchor="w", padx=24, pady=(22, 8))

        self.report_summary_var = tk.StringVar()
        tk.Label(frame, textvariable=self.report_summary_var, bg=LIGHT, fg=TEXT,
                 font=("Segoe UI", 11)).pack(anchor="w", padx=26, pady=(0, 8))

        settings = tk.LabelFrame(frame, text="Configuration", bg=LIGHT,
                                 font=("Segoe UI", 11, "bold"))
        settings.pack(fill="x", padx=24, pady=6)
        self.borrow_days_var = self._field(settings, "Borrow days", 0, 0, width=10)
        self.fine_rate_var = self._field(settings, "Fine per day (Rs.)", 0, 2, width=10)
        ttk.Button(settings, text="Save Settings", command=self.save_settings).grid(
            row=0, column=4, padx=12
        )

        tables = tk.Frame(frame, bg=LIGHT)
        tables.pack(fill="both", expand=True, padx=18, pady=10)
        tables.columnconfigure(0, weight=1)
        tables.columnconfigure(1, weight=1)

        overdue = tk.LabelFrame(tables, text="Overdue books", bg=LIGHT,
                               font=("Segoe UI", 11, "bold"))
        overdue.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        overdue_columns = ("transaction_id", "title", "name", "due_date")
        overdue_frame, self.overdue_tree = self._make_tree(
            overdue, overdue_columns, ("Txn ID", "Book", "Member", "Due Date"),
            height=8, widths=(80, 200, 160, 120),
        )
        overdue_frame.pack(fill="both", expand=True, padx=8, pady=8)

        popular = tk.LabelFrame(tables, text="Popular books", bg=LIGHT,
                               font=("Segoe UI", 11, "bold"))
        popular.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
        popular_columns = ("book_id", "title", "times_issued")
        popular_frame, self.popular_tree = self._make_tree(
            popular, popular_columns, ("Book ID", "Title", "Times Issued"),
            height=8, widths=(100, 280, 120),
        )
        popular_frame.pack(fill="both", expand=True, padx=8, pady=8)

        monthly = tk.LabelFrame(tables, text="Monthly borrowing statistics", bg=LIGHT,
                               font=("Segoe UI", 11, "bold"))
        monthly.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=6, pady=6)
        monthly_columns = ("month", "issues")
        monthly_frame, self.monthly_tree = self._make_tree(
            monthly, monthly_columns, ("Month", "Books Issued"),
            height=5, widths=(160, 140),
        )
        monthly_frame.pack(fill="both", expand=True, padx=8, pady=8)

        actions = tk.Frame(frame, bg=LIGHT)
        actions.pack(fill="x", padx=24, pady=(0, 18))
        ttk.Button(actions, text="Refresh Reports", command=self.refresh_reports).pack(
            side="left", padx=4
        )
        ttk.Button(actions, text="View All Transactions",
                   command=self.show_all_transactions).pack(side="left", padx=4)
        return frame

    @safe_action
    def refresh_reports(self):
        stats = self.reports.get_dashboard_stats()
        self.report_summary_var.set(
            f"Titles: {stats['total_titles']} | Copies: {stats['total_copies']} | "
            f"Available: {stats['available_copies']} | Borrowed: {stats['borrowed_copies']} | "
            f"Members: {stats['total_members']} | Active loans: {stats['active_loans']} | "
            f"Overdue: {stats['overdue_loans']} | Fines: Rs. {stats['total_fines']:.2f}"
        )
        self.borrow_days_var.set(str(self.transactions.borrow_days))
        self.fine_rate_var.set(str(self.transactions.fine_per_day))
        populate_tree(self.overdue_tree, self.reports.get_overdue_books(),
                      ("transaction_id", "title", "name", "due_date"))
        populate_tree(self.popular_tree, self.reports.get_popular_books(),
                      ("book_id", "title", "times_issued"))
        populate_tree(self.monthly_tree, self.reports.get_monthly_borrowing_stats(),
                      ("month", "issues"))

    @safe_action
    def save_settings(self):
        days = self.transactions.set_borrow_period(self.borrow_days_var.get())
        rate = self.transactions.set_fine_rate(self.fine_rate_var.get())
        messagebox.showinfo(
            "Success",
            f"Settings saved: borrowing period {days} days, fine Rs. {rate:g} per day.",
        )
        self.refresh_reports()

    @safe_action
    def show_all_transactions(self):
        rows = self.transactions.get_all_transactions()
        self._show_table_window(
            "All transactions", self.TRANSACTION_COLUMNS,
            ("Txn ID", "Book ID", "Title", "Member ID", "Name", "Issue Date",
             "Due Date", "Return", "Fine", "Status"),
            rows, widths=(80, 90, 180, 100, 150, 120, 120, 120, 80, 100),
        )
