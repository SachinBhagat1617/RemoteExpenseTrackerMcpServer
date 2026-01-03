from fastmcp import FastMCP
import os
import aiosqlite
import tempfile

#use temporary directory for database so that it could be writtable in restricted environments
temp_dir=tempfile.gettempdir()
db_path=os.path.join(temp_dir, "expenses.db")
categories_path=os.path.join(os.path.dirname(__file__),"categories.json")

print(f"Using database path: {db_path}")
mcp = FastMCP("ExpenseTracker")

def init_db(): # Keep as sync for initialization
    try:
        import sqlite3 # just for initialization
        with sqlite3.connect(db_path) as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("""
                    CREATE TABLE IF NOT EXISTS expenses(
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL,
                        amount REAL NOT NULL,
                        category TEXT NOT NULL,
                        subcategory TEXT DEFAULT '',
                        note TEXT DEFAULT ''
                    )                        
                """)
             # Test write access
            c.execute("INSERT OR IGNORE INTO expenses(date, amount, category) VALUES ('2000-01-01', 0, 'test')")
            c.execute("DELETE FROM expenses WHERE category = 'test'")
            print("Database initialized successfully with write access")
    except Exception as e:
        print(f"Database initialization error: {e}")
        raise

init_db()

@mcp.tool()
async def add_expense(date,amount,category,subcategory="",note=""):
    """Add a new expense entry to the database"""
    try:
        async with aiosqlite.connect(db_path) as c:
            cur=await c.execute(
                "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?, ?, ?, ?, ?)",
                (date, amount, category, subcategory, note)
            )
            expense_id=cur.lastrowid
            await c.commit()
            return {"status": "success", "id": expense_id, "message": "Expense added successfully"}
    except Exception as e:
        if "readonly" in str(e).lower():
            return {"status": "error", "message": "Database is in read-only mode. Check file permissions."}
        return {"status": "error", "message": f"Database error: {str(e)}"}

@mcp.tool()
async def list_expenses(start_date,end_date):
    """List expenses between start_date and end_date"""
    try:
        async with aiosqlite.connect(db_path) as c:
            cur=await c.execute(
                "SELECT id, date, amount, category, subcategory, note FROM expenses WHERE date BETWEEN ? AND ? ORDER BY date ASC",
                (start_date, end_date)
            )
            rows=await cur.fetchall()
            expenses=[
                {
                    "id": row[0],
                    "date": row[1],
                    "amount": row[2],
                    "category": row[3],
                    "subcategory": row[4],
                    "note": row[5]
                }
                for row in rows
            ]
            return {"status": "success", "expenses": expenses}
    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}

@mcp.tool()
async def summarize(start_date,end_date,category=None):
    """Summarize expenses by category within an inclusive date range"""
    try:
        async with aiosqlite.connect(db_path) as c:
            query = """
                    SELECT category, SUM(amount) AS total_amount, COUNT(*) as count
                    FROM expenses
                    WHERE date BETWEEN ? AND ?
                """
            params = [start_date, end_date]

            if category:
                query += " AND category = ?"
                params.append(category) 
            query += " GROUP BY category ORDER BY total_amount DESC"   
            cur=await c.execute(query, params)
            rows=await cur.fetchall()
            summary=[
                {
                    "category": row[0],
                    "total_amount": row[1],
                    "count": row[2]
                }
                for row in rows
            ]
            return {"status": "success", "summary": summary}
    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}

@mcp.resource("expense:///categories", mime_type="application/json")  # Changed: expense:// → expense:///
def categories():
    try:
        # Provide default categories if file doesn't exist
        default_categories = {
            "categories": [
                "Food & Dining",
                "Transportation",
                "Shopping",
                "Entertainment",
                "Bills & Utilities",
                "Healthcare",
                "Travel",
                "Education",
                "Business",
                "Other"
            ]
        }
        
        try:
            with open(categories_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            import json
            return json.dumps(default_categories, indent=2)
    except Exception as e:
        return f'{{"error": "Could not load categories: {str(e)}"}}'

# Start the server
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
    # mcp.run()