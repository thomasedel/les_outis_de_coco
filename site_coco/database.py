import sqlite3
import os


def get_db_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, 'depenses.db')


def get_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            couleur TEXT DEFAULT '#3498db',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS depenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            montant REAL NOT NULL,
            categorie_id INTEGER,
            date TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (categorie_id) REFERENCES categories(id)
        );
    ''')

    # Catégories par défaut (insérées uniquement si la table est vide)
    cursor.execute('SELECT COUNT(*) FROM categories')
    if cursor.fetchone()[0] == 0:
        categories_defaut = [
            ('Alimentation', '#2ecc71'),
            ('Transport', '#3498db'),
            ('Logement', '#e74c3c'),
            ('Loisirs', '#9b59b6'),
            ('Santé', '#1abc9c'),
            ('Autres', '#95a5a6'),
        ]

        for nom, couleur in categories_defaut:
            cursor.execute(
                'INSERT OR IGNORE INTO categories (nom, couleur) VALUES (?, ?)',
                (nom, couleur)
            )

    conn.commit()
    conn.close()
