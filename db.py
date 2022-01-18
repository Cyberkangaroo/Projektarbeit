import sqlite3

conn = sqlite3.connect('user.sqlite')

cursor = conn.cursor()

sql_querry = """CREATE TABLE user ( 
    name text PRIMARY KEY,
    password text NOT NULL
)"""

cursor.execute(sql_querry)