# API de Veículos

API REST desenvolvida em Flask para gerenciamento de veículos, com autenticação JWT, filtros avançados, paginação, ordenação e documentação via Swagger.

---

## uncionalidades

* Autenticação com JWT
* CRUD completo de veículos
* Filtros dinâmicos (marca, ano, cor, preço)
* Paginação (`page`, `limit`)
* Agrupamento (`agrupar`)
* Conversão de moeda (BRL ⇄ USD)
* Soft delete (`deleted_at`)
* Documentação Swagger

---

## 🚀 Tecnologias

* Python 3
* Flask
* SQLite
* JWT
* Swagger (Flasgger)
* Redis (cache opcional)

---

## Setup do Projeto

### 1. Clonar repositório

```bash
git clone <repo-url>
cd tinnova-api
```

### 2. Criar ambiente virtual

```bash
python -m venv .venv
source .venv/bin/activate  # Mac/Linux
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Variáveis de ambiente

Crie um arquivo `.env` na raiz:

```env
SECRET_JWT=seu_segredo
ALGORITHMS_JWT=HS256
```

---

## Rodar aplicação

```bash
python app.py
```

API disponível em:

```
http://localhost:5000
```

Swagger:

```
http://localhost:5000/apidocs
```

---

## Autenticação

### POST /login

```json
{
  "username": "usuario",
  "password": "senha"
}
```

Resposta:

```json
{
  "access_token": "jwt_token"
}
```

Use o token:

```
Authorization: Bearer <token>
```

---

## Endpoints

### Criar veículo

**POST /veiculo**

```json
{
  "nome": "Civic",
  "marca": "Honda",
  "ano": 2020,
  "cor": "Preto",
  "placa": "ABC1D23",
  "preco": 85000
}
```

---

### Listar veículos

**GET /veiculo**

Query params:

| Param    | Tipo   | Descrição         |
| -------- | ------ | ----------------- |
| marca    | string | Filtrar por marca |
| ano      | int    | Filtrar por ano   |
| cor      | string | Filtrar por cor   |
| minPreco | float  | Preço mínimo      |
| maxPreco | float  | Preço máximo      |
| page     | int    | Página            |
| limit    | int    | Limite            |
| agrupar  | string | (marca, nome)     |

Exemplo:

```
/veiculo?marca=Toyota&page=1&limit=10
```

---

### Buscar por ID

**GET /veiculo/{id}**

Retorna também:

```json
{
  "preco_brl": 50000
}
```

---

### Atualizar (completo)

**PUT /veiculo/{id}**

---

### Atualizar (parcial)

**PATCH /veiculo/{id}**

---

### Deletar (soft delete)

**DELETE /veiculo/{id}**

---

## Regras de negócio

* Placa validada automaticamente
* Preço armazenado em USD
* Conversão automática BRL → USD no cadastro
* Soft delete aplicado (não remove do banco)
* Não retorna registros deletados

