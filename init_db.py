import sqlite3
import os

DB_PATH = os.path.join("data", "app.db")
SCHEMA_FILE = "schema.sql"

def init_db():
    if not os.path.exists("data"):
        os.makedirs("data")

    if os.path.exists(DB_PATH):
        print("La base de données existe déjà. Supprimez-la si vous souhaitez la recréer.")
        return

    with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
        schema = f.read()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executescript(schema)
    conn.commit()
    conn.close()
    print("Base de données créée avec succès dans data/app.db")

if __name__ == "__main__":
    init_db()
