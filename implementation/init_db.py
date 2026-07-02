import os
import sqlite3
from pathlib import Path

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cohort TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    gpa REAL DEFAULT 0.0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    credits INTEGER DEFAULT 3
);

CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    score REAL DEFAULT NULL,
    status TEXT DEFAULT 'enrolled',
    enrolled_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
);
"""

SEED_SQL = """
INSERT OR IGNORE INTO students (id, name, cohort, email, gpa) VALUES
(1, 'Alice Nguyen', 'A1', 'alice.n@vinuni.edu.vn', 3.8),
(2, 'Bob Tran', 'A1', 'bob.t@vinuni.edu.vn', 3.4),
(3, 'Charlie Le', 'A2', 'charlie.l@vinuni.edu.vn', 3.9),
(4, 'David Pham', 'A2', 'david.p@vinuni.edu.vn', 3.2),
(5, 'Eva Hoang', 'B1', 'eva.h@vinuni.edu.vn', 3.75),
(6, 'Frank Vu', 'B1', 'frank.v@vinuni.edu.vn', 2.9);

INSERT OR IGNORE INTO courses (id, code, title, credits) VALUES
(1, 'COMP101', 'Introduction to Programming', 3),
(2, 'COMP201', 'Data Structures and Algorithms', 4),
(3, 'DATA301', 'Database Systems', 3),
(4, 'AI401', 'Artificial Intelligence', 4);

INSERT OR IGNORE INTO enrollments (id, student_id, course_id, score, status) VALUES
(1, 1, 3, 92.5, 'completed'),
(2, 2, 3, 85.0, 'completed'),
(3, 3, 3, 95.0, 'completed'),
(4, 4, 3, 78.0, 'completed'),
(5, 5, 3, 88.5, 'completed'),
(6, 6, 3, 65.0, 'completed'),
(7, 1, 4, 94.0, 'completed'),
(8, 3, 4, 91.0, 'completed'),
(9, 2, 1, 82.0, 'completed'),
(10, 4, 1, 75.5, 'completed');
"""


def create_database(db_path: str = None) -> str:
    """
    Creates the database schema and seeds sample data.
    If db_path is None, defaults to 'lab.db' inside the implementation directory.
    """
    if db_path is None:
        db_path = str(Path(__file__).parent / "lab.db")

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    with conn:
        conn.executescript(SCHEMA_SQL)
        conn.executescript(SEED_SQL)
    conn.close()
    return db_path


if __name__ == "__main__":
    db_file = create_database()
    print(f"Database successfully created and seeded at: {db_file}")