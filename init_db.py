import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# جدول المستخدمين
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    password TEXT,
    role TEXT
)
""")

# جدول السجل
cursor.execute("""
CREATE TABLE IF NOT EXISTS log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT,
    result TEXT
)
""")

conn.commit()
conn.close()

print("Database created successfully!")
