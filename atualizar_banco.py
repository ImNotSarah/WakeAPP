import sqlite3

conn = sqlite3.connect("usuarios.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE ocorrencias ADD COLUMN cidade TEXT")
    print("Coluna 'cidade' adicionada.")
except sqlite3.OperationalError as e:
    print("Coluna 'cidade' já existe ou erro:", e)

try:
    cursor.execute("ALTER TABLE ocorrencias ADD COLUMN estado TEXT")
    print("Coluna 'estado' adicionada.")
except sqlite3.OperationalError as e:
    print("Coluna 'estado' já existe ou erro:", e)

try:
    cursor.execute("ALTER TABLE ocorrencias ADD COLUMN pais TEXT")
    print("Coluna 'pais' adicionada.")
except sqlite3.OperationalError as e:
    print("Coluna 'pais' já existe ou erro:", e)

conn.commit()
conn.close()
