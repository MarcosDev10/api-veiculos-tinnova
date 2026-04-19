from dotenv import load_dotenv
from functools import wraps
from config_bd.configs import DataConfig
import os
import jwt
from datetime import datetime, timedelta
from flask import request, jsonify
import bcrypt

base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, "..", ".env")

load_dotenv(env_path)

SECRET_JWT = os.getenv("KEY_ACCESS")
ALGORITHMS_JWT = "HS256"

def decode_jwt(token):
    try:
        return jwt.decode(token, SECRET_JWT, algorithms=[ALGORITHMS_JWT])
    except jwt.ExpiredSignatureError:
        return {"error": "Token expirado"}
    except jwt.InvalidTokenError:
        return {"error": "Token inválido"}

# Válida o token enviado no header da requisição
def require_auth(type_user="all"):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return jsonify({"error": "Token não informado"}), 401
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({"error": "Formato do header inválido"}), 401
            decoded = decode_jwt(token)

            if "error" in decoded:
                return jsonify(decoded), 401

            if type_user == "admin" and decoded.get("profile") != "admin":
                return jsonify({"error": "Acesso negado"}), 403

            request.user = decoded
            return f(*args, **kwargs)
        return decorated
    return decorator

# Descriptografa a senha e válida se está correta ou não
def validate_password(send_password, password_hash):
    return bcrypt.checkpw( send_password.encode('utf-8'),password_hash.encode('utf-8'))

# Válida as informaões enviadas no payload de login
def validate_user(username, password):
    db = DataConfig()
    data_user = db.query(f"SELECT * FROM usuarios WHERE nome_usuario='{username}' and deleted_at is null")
    if data_user:
        if validate_password(send_password=password, password_hash=data_user[0]["senha"]):
            db.execute_command(f"update usuarios set lasted_at=datetime('now') where nome_usuario='{username}'")
            return jwt.encode({
                "username": data_user[0]["nome_usuario"],
                "profile": data_user[0]["perfil"],
                "exp": datetime.utcnow() + timedelta(hours=12)
            }, SECRET_JWT, algorithm=ALGORITHMS_JWT)
        return False
    else:
        return False




