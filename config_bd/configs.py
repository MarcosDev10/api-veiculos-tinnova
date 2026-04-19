import sqlite3
import os
from dotenv import load_dotenv
import bcrypt

base_dir = os.path.dirname(os.path.abspath(__file__))
path_db = os.path.join(base_dir, "banco.db")


base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, "..", ".env")
load_dotenv(env_path)

USER = os.getenv("USER_ADM")
PASSWORD = os.getenv("PASSWORD_ADM")

# Gerador de senha com rash
def hash_senha(senha):
    salt = bcrypt.gensalt()
    senha_hash = bcrypt.hashpw(senha.encode('utf-8'), salt)
    return senha_hash.decode('utf-8')

class DataConfig:
    def __init__(self):
        execute_first_command = False if os.path.exists(path_db) else True
        self.conn = sqlite3.connect(path_db)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        if execute_first_command:
            self.create_table()

    # Estrutura padrão do banco de dados
    def create_table(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_usuario TEXT NOT NULL UNIQUE,
            perfil TEXT,
            senha TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            lasted_at TEXT,
            deleted_at TEXT
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS veiculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            marca TEXT NOT NULL,
            ano INTEGER NOT NULL,
            cor TEXT NOT NULL,
            placa TEXT NOT NULL UNIQUE,
            preco INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT
        )
        """)

        conn.execute("PRAGMA journal_mode=WAL;")

        self.cursor.execute(f"""
        INSERT INTO
        usuarios (nome_usuario, perfil, senha) VALUES
        ('{USER}', 'admin', '{hash_senha(PASSWORD)}')
        """)

        self.conn.commit()

    def get_con(self):
        return self.conn

    def close(self):
        self.conn.close()

    # Apenas consulta no banco com retorno em dicionario
    def query(self, query, parameters=None):
        if parameters:
            self.cursor.execute(query, parameters)
        else:
            self.cursor.execute(query)
        return [dict(row) for row in self.cursor.fetchall()]

    # Executa comandos como update, insert e delete
    def execute_command(self, comando, parameters = None):
        try:
            if parameters:
                self.cursor.execute(comando, parameters)
            else:
                self.cursor.execute(comando)

            self.conn.commit()

            return {"registers_validate": self.cursor.rowcount}

        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                raise Exception("Values duplicated in table")
            else:
                raise Exception(f"Error: {str(e)}")

        except Exception as e:
            raise Exception(f"Error execute command: {str(e)}")