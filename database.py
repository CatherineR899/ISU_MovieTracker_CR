import sqlite3

conn = sqlite3.connect("users.db")

cursor = conn.cursor()

# ==========================
# USERS
# ==========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    username TEXT UNIQUE NOT NULL,

    password TEXT NOT NULL
)
""")

# ==========================
# WATCHED MOVIES
# ==========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS watched_movies (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER NOT NULL,

    movie_id INTEGER NOT NULL,

    FOREIGN KEY (user_id)
    REFERENCES users(id)
)
""")

# ==========================
# WATCHLIST
# ==========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS watchlist_movies (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER NOT NULL,

    movie_id INTEGER NOT NULL,

    FOREIGN KEY (user_id)
    REFERENCES users(id)
)
""")


# ==========================
# REVIEWS
# ==========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS movie_reviews (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER NOT NULL,

    movie_id INTEGER NOT NULL,

    rating INTEGER,

    comment TEXT,

    FOREIGN KEY (user_id)
    REFERENCES users(id)
)
""")

conn.commit()

conn.close()

print("Database created successfully")