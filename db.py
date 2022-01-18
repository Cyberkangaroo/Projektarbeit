import sqlite3

conn = sqlite3.connect('user.sqlite')

cursor = conn.cursor()

table_querry = """CREATE TABLE user ( 
    name text PRIMARY KEY,
    password text NOT NULL,
    salt NOT NULL
)"""

#cursor.execute(sql_querry)

drop_querry = """DROP TABLE user"""

insert_querry = """INSERT INTO user (name, password) VALUES(?, ?)"""
cursor.execute(table_querry)
conn.commit()
