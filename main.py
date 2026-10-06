import sqlite3
from datetime import datetime
from pathlib import Path
from fastmcp import FastMCP

# Create MCP Server
mcp = FastMCP(name="Expense Tracker")

# SQLite DB path
DB_PATH = Path(__file__).parent / "expenses.db"

# Allowed categories
ALLOWED_CATEGORIES = [
    "food",
    "travel",
    "shopping",
    "rent",
    "utilities",
    "health",
    "education",
    "salary",
    "business",
    "entertainment",
    "other",
]


def get_connection():
    """
    Create SQLite database connection.
    """
    return sqlite3.connect(DB_PATH)


def init_db():
    """
    Create transactions table if it does not already exist.
    This function is safe to call multiple times.
    """
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def validate_category(category: str) -> str:
    """
    Validate category before inserting/updating data.
    """
    if not category:
        raise ValueError("Category is required.")

    category = category.lower().strip()

    if category not in ALLOWED_CATEGORIES:
        raise ValueError(
            f"Invalid category '{category}'. "
            f"Allowed categories are: {', '.join(ALLOWED_CATEGORIES)}"
        )

    return category


def validate_amount(amount: float) -> float:
    """
    Validate amount before inserting/updating data.
    """
    if amount <= 0:
        raise ValueError("Amount must be greater than 0.")

    return amount


@mcp.tool()
def add_expense(amount: float, category: str, description: str = "") -> str:
    """
    Add a new expense transaction.

    Example:
    add_expense(25, "food", "Lunch at restaurant")
    """
    init_db()

    amount = validate_amount(amount)
    category = validate_category(category)
    description = description.strip() if description else ""
    created_at = datetime.now().isoformat(timespec="seconds")

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO transactions (type, amount, category, description, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("expense", amount, category, description, created_at),
        )
        conn.commit()

    return f"Expense added successfully with ID {cursor.lastrowid}."


@mcp.tool()
def add_credit(amount: float, category: str = "salary", description: str = "") -> str:
    """
    Add a credit/income transaction.

    Example:
    add_credit(5000, "salary", "Monthly salary")
    """
    init_db()

    amount = validate_amount(amount)
    category = validate_category(category)
    description = description.strip() if description else ""
    created_at = datetime.now().isoformat(timespec="seconds")

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO transactions (type, amount, category, description, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("credit", amount, category, description, created_at),
        )
        conn.commit()

    return f"Credit added successfully with ID {cursor.lastrowid}."


@mcp.tool()
def list_transactions(limit: int = 10) -> list[dict]:
    """
    List latest transactions.

    Example:
    list_transactions(5)
    """
    init_db()

    if limit <= 0:
        limit = 10

    if limit > 100:
        limit = 100

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, type, amount, category, description, created_at
            FROM transactions
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


@mcp.tool()
def summarize_transactions() -> dict:
    """
    Summarize total credit, total expense, available balance,
    and category-wise summary.
    """
    init_db()

    with get_connection() as conn:
        expense_total = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE type = 'expense'
            """
        ).fetchone()[0]

        credit_total = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE type = 'credit'
            """
        ).fetchone()[0]

        category_rows = conn.execute(
            """
            SELECT category, type, COALESCE(SUM(amount), 0) AS total
            FROM transactions
            GROUP BY category, type
            ORDER BY total DESC
            """
        ).fetchall()

    balance = credit_total - expense_total

    return {
        "total_credit": credit_total,
        "total_expense": expense_total,
        "balance": balance,
        "category_summary": [
            {
                "category": row[0],
                "type": row[1],
                "total": row[2],
            }
            for row in category_rows
        ],
    }


@mcp.tool()
def edit_transaction(
    transaction_id: int,
    amount: float,
    category: str,
    description: str = "",
) -> str:
    """
    Edit an existing transaction by ID.

    Example:
    edit_transaction(1, 30, "food", "Updated lunch amount")
    """
    init_db()

    if transaction_id <= 0:
        raise ValueError("Transaction ID must be greater than 0.")

    amount = validate_amount(amount)
    category = validate_category(category)
    description = description.strip() if description else ""

    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE transactions
            SET amount = ?, category = ?, description = ?
            WHERE id = ?
            """,
            (amount, category, description, transaction_id),
        )
        conn.commit()

    if cursor.rowcount == 0:
        return f"No transaction found with ID {transaction_id}."

    return f"Transaction {transaction_id} updated successfully."


@mcp.tool()
def delete_transaction(transaction_id: int) -> str:
    """
    Delete a transaction by ID.

    Example:
    delete_transaction(1)
    """
    init_db()

    if transaction_id <= 0:
        raise ValueError("Transaction ID must be greater than 0.")

    with get_connection() as conn:
        cursor = conn.execute(
            """
            DELETE FROM transactions
            WHERE id = ?
            """,
            (transaction_id,),
        )
        conn.commit()

    if cursor.rowcount == 0:
        return f"No transaction found with ID {transaction_id}."

    return f"Transaction {transaction_id} deleted successfully."


@mcp.tool()
def list_categories() -> list[str]:
    """
    List allowed transaction categories.
    """
    return ALLOWED_CATEGORIES


@mcp.tool()
def get_database_location() -> str:
    """
    Show the local SQLite database file location.
    Useful for debugging.
    """
    init_db()
    return str(DB_PATH)


@mcp.resource("expense://categories")
def expense_categories() -> str:
    """
    Provide allowed expense categories as a resource.
    """
    return "\n".join(ALLOWED_CATEGORIES)


if __name__ == "__main__":
    init_db()
    mcp.run()