import sqlite3

def connect():
    db = sqlite3.connect(":memory:")
    db.execute("create table users (name text, email text)")
    db.executemany("insert into users values (?, ?)", [("ann", "ann@x.org"), ("bob", "bob@x.org")])
    return db

def find_user(db, name):
    return db.execute("select name, email from users where name = ?", (name,)).fetchone()

def add_user(db, name, email):
    db.execute("insert into users values (?, ?)", (name, email))
