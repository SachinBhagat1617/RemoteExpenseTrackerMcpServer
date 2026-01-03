from fastmcp import FastMCP
import os
import sqlite3

db_path = os.path.join(os.path.dirname(__file__), 'expenses.db')
categories_path = os.path.join(os.path.dirname(__file__), 'categories.json')

mcp= FastMCP(name="Expense Tracker")

def init_db():
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                note TEXT DEFAULT ''   
            )
        ''')
        conn.commit()
init_db()

@mcp.tool()
def add_expense(date,amount,category,subcategory="",note=""):
    """Add a new expense to the tracker."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO expenses (date, amount, category, note)
            VALUES (?, ?, ?, ?)
        ''', (date, amount, category if not subcategory else f"{category} - {subcategory}", note))
        conn.commit()
    return {"status": "success", "id": cursor.lastrowid, "message": "Expense added successfully."}

@mcp.tool()
def list_expenses(start_date,end_date):
    """List expenses within a date range."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, date, amount, category, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY date ASC
        ''', (start_date, end_date))
        expenses = cursor.fetchall()
    return [{"id": row[0], "date": row[1], "amount": row[2], "category": row[3], "note": row[4]} for row in expenses]

@mcp.tool()
def summarize_expenses(start_date,end_date,category=None):
    """Summarize expenses by category within a inclusive date range."""
    with sqlite3.connet(db_path) as conn:
        cursor=conn.cursor()
        query='''
            SELECT category, SUM(amount) as total
            FROM expenses
            WHERE date BETWEEN ? AND ?
            GROUP BY category
        '''
        params=[start_date,end_date]
        if category:
            query+=' AND category=?'
            params.append(category)
        query +=" GROUP BY category ORDER BY total DESC"
        cursor.execute(query, params)
        results = cursor.fetchall()
    return [{"category": row[0], "total": row[1]} for row in results]

@mcp.resource("expense://categories",mime_type="application/json")
def categories():
    """Provide the categories JSON file as a resource."""
    with open(categories_path, 'r', encoding='utf-8') as f:
        return f.read()

if __name__ == "__main__":
    mcp.run()
