import requests
from flask import Flask, jsonify, request
from tools.auth import validate_user
from tools.auth import require_auth
from config_bd.configs import DataConfig, hash_senha
from tools.prince import Price
import re
from collections import defaultdict
from flasgger import Swagger

app = Flask(__name__)
prc = Price()


swagger_template = {
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header"
        }
    }
}

Swagger(app, template=swagger_template)

# Válida informações da placa como padrão mercosul (EOI7D98) como padrão antigo (EOI8965)
def valid_plate(plate):
    plate = plate.upper().replace("-", "").strip()
    default_old = r'^[A-Z]{3}[0-9]{4}$'
    default_new = r'^[A-Z]{3}[0-9][A-Z][0-9]{2}$'
    return bool(re.match(default_old, plate) or re.match(default_new, plate))

# Válida os campos nescessario para cada rota
def valid_fields(fields_request, fields_required):
    missing = [c for c in fields_required if c not in fields_request]
    if missing:
        return False, f"Campos obrigatórios faltando: {','.join(missing)}"
    return True, None

@app.route('/')
def index():
    return jsonify({'message': 'Hello World!'})

@app.route('/login', methods=['POST'])
def login():
    """
        Autenticação de usuário
        ---
        tags:
          - Auth
        summary: Realiza login e retorna um token JWT
        description: Endpoint responsável por autenticar o usuário com username e password.

        consumes:
          - application/json

        parameters:
          - in: body
            name: body
            required: true
            schema:
              type: object
              required:
                - username
                - password
              properties:
                username:
                  type: string
                  example: marcos.neto
                password:
                  type: string
                  example: 123456

        responses:
          200:
            description: Login realizado com sucesso
            schema:
              type: object
              properties:
                access_token:
                  type: string
                  example: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

          400:
            description: Erro na requisição
            schema:
              type: object
              properties:
                erro:
                  type: string
                  example: Usuario ou senha inválido
        """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'erro': 'Json enviado é inválido'}), 400

    valid, message = valid_fields(data, ["username", "password"])
    if not valid:
        return jsonify({"erro": message}), 400

    access_token = validate_user(data.get("username"), str(data.get("password")))

    if not access_token:
        return jsonify({"erro": "Usuario ou senhah inválido"}), 400
    else:
        return jsonify({"access_token": access_token})

@app.route('/sign-up', methods=['POST'])
@require_auth(type_user="admin")
def sign_up():
    """
    Criar usuário
    ---
    tags:
      - Usuários
    summary: Cria um novo usuário
    description: |
      Cria um novo usuário no sistema.

      - A senha é criptografada automaticamente antes de salvar
      - Apenas usuários com perfil admin podem acessar este endpoint

    security:
      - Bearer: []

    consumes:
      - application/json

    parameters:
      - in: body
        name: body
        required: true
        description: Dados do usuário
        schema:
          type: object
          required:
            - nome_usuario
            - perfil
            - senha
          properties:
            nome_usuario:
              type: string
              example: marcos.neto
            perfil:
              type: string
              example: admin
            senha:
              type: string
              example: 123456

    responses:
      201:
        description: Usuário criado com sucesso
        schema:
          type: object
          properties:
            mensagem:
              type: string
              example: Usuário criado com sucesso

      400:
        description: Erro de validação
        schema:
          type: object
          properties:
            erro:
              type: string
              example: Campos faltantes (nome_usuario)

      401:
        description: Não autorizado

      409:
        description: Conflito (usuário já existe)
        schema:
          type: object
          properties:
            erro:
              type: string
              example: Values duplicated in table

      500:
        description: Erro interno do servidor
    """
    data = request.get_json(silent=True)
    db = DataConfig()
    valid, message = valid_fields(data, ["nome_usuario", "perfil", "senha"])
    if not valid:
       return jsonify({"erro": message}), 400

    fields = []
    values = []
    for k, v in data.items():
        fields.append(k)
        if k == "senha":
            values.append(hash_senha(str(v)))
        else:
            values.append(str(v))
    try:
        db.execute_command(f"INSERT INTO usuarios ({','.join(fields)}) VALUES ({','.join(['?'] * len(values))})", values)
        return jsonify({"mensagem": "Usúario criado com sucesso"}), 201
    except Exception as e:
        status_code = 500
        if "Values duplicated in table" in str(e):
            status_code = 409
        return jsonify({"erro": str(e)}), status_code


@app.route("/veiculo", methods=["GET"])
@require_auth(type_user="all")
def search_vehicle():
    """
    Buscar veículos
    ---
    tags:
      - Veículos
    summary: Consulta veículos com filtros, paginação e agrupamento
    description: |
      Retorna veículos com base em filtros opcionais como marca, ano, cor e faixa de preço.
      Também permite paginação e agrupamento dos resultados.

    security:
      - Bearer: []

    parameters:
      - name: marca
        in: query
        type: string
        required: false
        description: Filtrar por marca
        example: Toyota

      - name: ano
        in: query
        type: integer
        required: false
        description: Filtrar por ano
        example: 2020

      - name: cor
        in: query
        type: string
        required: false
        description: Filtrar por cor
        example: Preto

      - name: minPreco
        in: query
        type: number
        required: false
        description: Preço mínimo
        example: 50000

      - name: maxPreco
        in: query
        type: number
        required: false
        description: Preço máximo
        example: 100000

      - name: page
        in: query
        type: integer
        required: false
        default: 1
        description: Número da página

      - name: limit
        in: query
        type: integer
        required: false
        default: 10
        description: Quantidade de registros por página

      - name: agrupar
        in: query
        type: string
        required: false
        enum: [marca, nome]
        description: Agrupa os resultados por campo

    responses:
      200:
        description: Lista de veículos retornada com sucesso
        schema:
          type: object
          properties:
            data:
              oneOf:
                - type: array
                  items:
                    type: object
                    properties:
                      nome:
                        type: string
                      marca:
                        type: string
                      preco_usd:
                        type: number
                - type: object
                  additionalProperties:
                    type: array
                    items:
                      type: object
                      properties:
                        nome:
                          type: string
                        marca:
                          type: string
                        preco_usd:
                          type: number
            limite:
              type: integer
            pagina:
              type: integer

      400:
        description: Erro de validação de parâmetros
        schema:
          type: object
          properties:
            erro:
              type: string
              example: Parâmetros não permitidos

      401:
        description: Não autorizado (token inválido ou ausente)
    """
    db = DataConfig()
    get_params = request.args

    related = {
        "marca": {"operator": "="},
        "ano": {"operator": "="},
        "cor": {"operator": "="},
        "minPreco": {"operator": ">="},
        "maxPreco": {"operator": "<="},
    }

    control_params = ["agrupar", "page", "limit"]

    filters = "WHERE deleted_at IS NULL "
    values = []
    params_not_found = []

    for k, v in get_params.items():
        if k in related:
            column = "preco" if k in ["minPreco", "maxPreco"] else k
            filters += f"AND {column} {related[k]['operator']} ? "
            values.append(v)
        elif k not in control_params:
            params_not_found.append(k)
    if params_not_found:
        return jsonify({
            "erro": f"Parâmetros não permitidos ({', '.join(params_not_found)}). "
                    f"Permitidos: {', '.join(list(related.keys()) + control_params)}"
        }), 400

    try:
        page = int(get_params.get("page", 1))
        limit = int(get_params.get("limit", 10))
    except ValueError:
        return jsonify({"erro": "page e limit devem ser inteiros"}), 400

    offset = (page - 1) * limit

    data = db.query(f"SELECT nome, marca, preco as preco_usd FROM veiculos {filters} LIMIT {limit} OFFSET {offset}", values)

    agruped_per = request.args.get("agrupar")

    if agruped_per:
        allowed_group = ["marca", "nome"]
        if agruped_per not in allowed_group:
            return jsonify({"erro": "Agrupamento inválido"}), 400
        grouped = defaultdict(list)

        for d in data:
            grouped[d.get(agruped_per)].append(d)
        return jsonify({"data": grouped, "limite": limit, "pagina": page}), 200

    return jsonify({"data": data, "limite": limit, "pagina": page}), 200


@app.route("/veiculo/<id>", methods=["GET"])
@require_auth(type_user="all")
def search_vehicle_per_id(id):
    """
     Buscar veículo por ID
     ---
     tags:
       - Veículos
     summary: Retorna um veículo específico pelo ID
     description: |
       Busca um veículo pelo ID e retorna seus dados.
       Também converte o preço de USD para BRL.

     security:
       - Bearer: []

     parameters:
       - name: id
         in: path
         type: integer
         required: true
         description: ID do veículo
         example: 1

     responses:
       200:
         description: Veículo encontrado
         schema:
           type: object
           properties:
             data:
               type: object
               properties:
                 id:
                   type: integer
                 nome:
                   type: string
                 marca:
                   type: string
                 preco:
                   type: number
                 preco_brl:
                   type: number

       404:
         description: Veículo não encontrado
         schema:
           type: object
           properties:
             erro:
               type: string
               example: Veiculo não encontrado

       401:
         description: Não autorizado
     """
    db = DataConfig()
    data = db.query(f"select * from veiculos WHERE id = {id}")
    if data:
        data = data[0]
        data["preco_brl"] = prc.convert_to(data["preco"], to="usd_to_brl")
        return jsonify({"data": data}), 200
    else:
        return jsonify({"erro": "Veiculo não encontrado"}), 404

@app.route("/veiculo/relatorios/por-marca", methods=["GET"])
@require_auth(type_user="all")
def search_vehicle_sumarize():
    """
    Relatório de veículos por marca
    ---
    tags:
      - Relatórios
    summary: Retorna a quantidade de veículos agrupados por marca
    description: |
      Retorna um resumo da quantidade de veículos por marca.

      - Apenas veículos não deletados são considerados
      - O resultado é agrupado pela marca

    security:
      - Bearer: []

    responses:
      200:
        description: Relatório gerado com sucesso
        schema:
          type: object
          properties:
            data:
              type: object
              additionalProperties:
                type: object
                properties:
                  quantidade:
                    type: integer
              example:
                Honda:
                  quantidade: 3
                Toyota:
                  quantidade: 5

      401:
        description: Não autorizado

      500:
        description: Erro interno do servidor
    """
    db = DataConfig()
    data = db.query("select * from veiculos where deleted_at is null")
    payload_return = defaultdict(lambda: {"quantidade": 0})
    for d in data:
        payload_return[d["marca"]]["quantidade"] += 1
    return jsonify({"data": payload_return}), 200


@app.route("/veiculo", methods=["POST"])
@require_auth(type_user="admin")
def create_vehicle(id=None):
    """
Criar veículo
---
tags:
  - Veículos
summary: Cria um novo veículo
description: |
  Cria um novo veículo no sistema.

  - O preço enviado deve estar em BRL
  - O sistema converte automaticamente para USD antes de salvar
  - A placa deve estar em formato válido (ex: ABC1D23)

security:
  - Bearer: []

consumes:
  - application/json

parameters:
  - in: body
    name: body
    required: true
    description: Dados do veículo
    schema:
      type: object
      required:
        - nome
        - marca
        - ano
        - cor
        - placa
        - preco
      properties:
        nome:
          type: string
          example: Civic
        marca:
          type: string
          example: Honda
        ano:
          type: integer
          example: 2020
        cor:
          type: string
          example: Preto
        placa:
          type: string
          example: ABC1D23
        preco:
          type: number
          example: 85000

responses:
  201:
    description: Veículo criado com sucesso
    schema:
      type: object
      properties:
        message:
          type: string
          example: Veiculo criado com sucesso

  400:
    description: Erro de validação
    schema:
      type: object
      properties:
        erro:
          type: string
          example: Campos faltantes (nome, marca)

  401:
    description: Não autorizado (token inválido ou ausente)

  409:
    description: Conflito (placa já cadastrada)
    schema:
      type: object
      properties:
        erro:
          type: string
          example: Values duplicated in table

  500:
    description: Erro interno do servidor
"""
    data = request.get_json(silent=True)
    db = DataConfig()

    valid, message = valid_fields(data, ["nome", "marca", "ano", "cor", "placa", "preco"])
    if not valid:
        return jsonify({"erro": message}), 400

    if not valid_plate(data["placa"]):
        return jsonify({"erro": "Placa incorreta"}), 400

    try:
        if data.get("preco"):
            value_price = prc.convert_to(data["preco"], to="brl_to_usd")

        fields = []
        values = []
        for k, v in data.items():
            fields.append(k)
            if k == "preco":
                values.append(value_price)
            else:
                values.append(v)

        db.execute_command(f"INSERT INTO veiculos ({','.join(fields)}) VALUES ({",".join(["?"] * len(values))})", parameters=values)
        return jsonify({"message": "Veiculo criado com sucesso"}), 201
    except Exception as e:
        status_code = 500
        if "Values duplicated in table" in str(e):
            status_code = 409
        return jsonify({"erro": str(e)}), status_code

@app.route("/veiculo/<id>", methods=["PUT"])
def update_vehicle_all_fields(id):
    """
    Atualizar veículo (completo)
    ---
    tags:
      - Veículos
    summary: Atualiza completamente um veículo pelo ID
    description: |
      Atualiza todos os campos de um veículo existente.

      - Todos os campos são obrigatórios
      - O preço deve ser enviado em BRL
      - O sistema converte automaticamente para USD
      - A placa deve estar em formato válido (ex: ABC1D23)

    security:
      - Bearer: []

    consumes:
      - application/json

    parameters:
      - in: path
        name: id
        type: integer
        required: true
        description: ID do veículo
        example: 1

      - in: body
        name: body
        required: true
        description: Dados completos do veículo
        schema:
          type: object
          required:
            - nome
            - marca
            - ano
            - cor
            - placa
            - preco
          properties:
            nome:
              type: string
              example: Civic
            marca:
              type: string
              example: Honda
            ano:
              type: integer
              example: 2022
            cor:
              type: string
              example: Preto
            placa:
              type: string
              example: ABC1D23
            preco:
              type: number
              example: 90000

    responses:
      200:
        description: Veículo atualizado com sucesso
        schema:
          type: object
          properties:
            message:
              type: string
              example: Veiculo atualizado com sucesso

      400:
        description: Erro de validação
        schema:
          type: object
          properties:
            erro:
              type: string
              example: Campos faltantes (nome, marca)

      404:
        description: Veículo não encontrado
        schema:
          type: object
          properties:
            erro:
              type: string
              example: ID informado não encontrado

      401:
        description: Não autorizado

      409:
        description: Conflito (placa duplicada)

      500:
        description: Erro interno do servidor
    """
    data = request.get_json(silent=True)
    db = DataConfig()

    valid, message = valid_fields(data, ["nome", "marca", "ano", "cor", "placa", "preco"])
    if not valid:
        return jsonify({"erro": message}), 400

    if not valid_plate(data["placa"]):
        return jsonify({"erro": "Placa incorreta"}), 400

    try:
        if data.get("preco"):
            value_price = prc.convert_to(data["preco"], to="brl_to_usd")

        fields = []
        values = []
        for k, v in data.items():
            fields.append(f"{k} = ?")
            if k == "preco":
                values.append(value_price)
            else:
                values.append(v)

        return_db = db.execute_command( f"UPDATE veiculos set {','.join(fields)} WHERE id = {id}", parameters=values)
        if return_db["registers_validate"] > 0:
            return jsonify({"message": "Veiculo atualizado com sucesso"}), 200
        else:
            return jsonify({"message": "ID informado não encontrado"}), 204

    except Exception as e:
        status_code = 500
        if "Values duplicated in table" in str(e):
            status_code = 409
        return jsonify({"erro": str(e)}), status_code


@app.route("/veiculo/<id>", methods=["PATCH"])
@require_auth(type_user="admin")
def update_vehicle(id):
    """
       Atualizar parcialmente veículo
       ---
       tags:
         - Veículos
       summary: Atualiza campos específicos de um veículo
       description: |
         Atualiza apenas os campos enviados no body.
         Diferente do PUT, não exige todos os campos.

       security:
         - Bearer: []

       consumes:
         - application/json

       parameters:
         - in: path
           name: id
           type: integer
           required: true
           description: ID do veículo

         - in: body
           name: body
           required: true
           schema:
             type: object
             properties:
               nome:
                 type: string
                 example: Civic
               marca:
                 type: string
                 example: Honda
               ano:
                 type: integer
                 example: 2022
               cor:
                 type: string
                 example: Preto
               placa:
                 type: string
                 example: ABC1D23
               preco:
                 type: number
                 example: 90000

       responses:
         200:
           description: Atualizado com sucesso
         400:
           description: Erro de validação
         401:
           description: Não autorizado
         404:
           description: Veículo não encontrado
         409:
           description: Conflito (duplicidade)
       """
    data = request.get_json(silent=True)
    allowed_fields = ["nome", "marca", "ano", "cor", "placa", "preco"]

    invalid = [k for k in data.keys() if k not in allowed_fields]
    if invalid:
        return jsonify({ "erro": f"Parâmetros inválidos ({', '.join(invalid)})" }), 400

    fields = []
    values = []

    for k, v in data.items():
        fields.append(f"{k} = ?")
        values.append(v)

    values.append(id)

    db = DataConfig()
    try:
        result = db.get_con().execute(f"UPDATE veiculos SET {', '.join(fields)} WHERE id = ?", values)
        db.get_con().commit()
        if result.rowcount == 0:
            return jsonify({"erro": "Veículo não encontrado"}), 404
        return jsonify({"message": "Atualizado com sucesso"}), 200

    except Exception as e:
        status_code = 500
        if "UNIQUE constraint failed" in str(e):
            status_code = 409
        return jsonify({"erro": str(e)}), status_code


@app.route("/veiculo/<id>", methods=["DELETE"])
@require_auth(type_user="admin")
def delete_vehicle(id):
    """
        Remover veículo (soft delete)
        ---
        tags:
          - Veículos
        summary: Remove um veículo logicamente
        description: |
          Realiza um soft delete do veículo, preenchendo o campo `deleted_at`.
          O registro não é removido fisicamente do banco.

        security:
          - Bearer: []

        parameters:
          - name: id
            in: path
            type: integer
            required: true
            description: ID do veículo

        responses:
          200:
            description: Veículo removido com sucesso
          404:
            description: Veículo não encontrado
          401:
            description: Não autorizado
        """
    db = DataConfig()
    try:
        db.execute_command(f"UPDATE veiculos SET deleted_at = datetime('now') WHERE id = {id}")
        return jsonify({
            "message": "Veiculo deletado com sucesso"
        }), 200
    except Exception as e:
        status_code = 500
        if "Values duplicated in table" in str(e):
            status_code = 409
        return jsonify({"erro": str(e)}), status_code


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003)