"""
api_mobile.py — API Unificada Mobile & Desktop (FastAPI + sqlite3 nativo)
Conectada diretamente ao banco 'loja_daniel_v2.db' na raiz do projeto.
"""

import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# CONFIGURAÇÃO DE CAMINHOS, .ENV NATIVO E BANCO DE DADOS (SQLITE3 NATIVO)
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "loja_daniel_v2.db")
STATIC_DIR = os.path.join(BASE_DIR, "static")
ENV_PATH = os.path.join(BASE_DIR, ".env")

os.makedirs(STATIC_DIR, exist_ok=True)


def _carregar_env(caminho: str) -> None:
    """Carrega variáveis do arquivo .env sem depender de bibliotecas externas."""
    if not os.path.isfile(caminho):
        return
    with open(caminho, "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, valor = linha.split("=", 1)
            chave = chave.strip()
            valor = valor.strip().strip('"').strip("'")
            if chave and chave not in os.environ:
                os.environ[chave] = valor


_carregar_env(ENV_PATH)


@contextmanager
def get_db():
    """Gerenciador de contexto para conexão nativa com o SQLite3."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# INICIALIZAÇÃO DO FASTAPI & CORS
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Kanemberg PDV — API Mobile & Desktop",
    description="API integrada ao banco loja_daniel_v2.db",
    version="2.5.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _proteger_contra_crawlers(request, call_next):
    ua = (request.headers.get("user-agent") or "").lower()
    bots_bloqueados = ("googlebot", "adsbot", "safebrowsing", "headlesschrome", "crawler", "spider", "censys")
    if any(b in ua for b in bots_bloqueados):
        return HTMLResponse(content="<!DOCTYPE html><html><head><title>OK</title></head><body>OK</body></html>", status_code=200)
    response = await call_next(request)
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive, nosnippet"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/robots.txt")
def robots_txt():
    return HTMLResponse(content="User-agent: *\nDisallow: /\n", media_type="text/plain")


# ---------------------------------------------------------------------------
# AUTENTICAÇÃO POR BEARER TOKEN COM EXPIRAÇÃO
# ---------------------------------------------------------------------------
security = HTTPBearer(auto_error=False)
TOKEN_TTL_HORAS = int(os.getenv("TOKEN_TTL_HORAS", "24"))

USUARIOS_SISTEMA = {
    os.getenv("ADMIN_USER", "admin").strip().lower(): {
        "senha": os.getenv("ADMIN_PASS", "Kanemberg@2026"),
        "role": "admin",
    },
    os.getenv("VENDEDOR_USER", "vendedor").strip().lower(): {
        "senha": os.getenv("VENDEDOR_PASS", "Loja@2026"),
        "role": "vendedor",
    },
}

TOKENS_ATIVOS: dict[str, dict] = {}


def verificar_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Valida o Bearer Token enviado no header Authorization e verifica expiração."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação ausente ou inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    usuario_info = TOKENS_ATIVOS.get(token)
    if not usuario_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado. Faça login novamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if datetime.now() > usuario_info["expira_em"]:
        TOKENS_ATIVOS.pop(token, None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão expirada. Faça login novamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return usuario_info


# ---------------------------------------------------------------------------
# SCHEMAS PYDANTIC (REQUEST / RESPONSE)
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    usuario: str
    senha: str


class VariacaoInput(BaseModel):
    id: Optional[int] = None
    tamanho: str = Field(default="M")
    cor: str = Field(default="")
    cor_hex: str = Field(default="#3b82f6")
    codigo_barras: Optional[str] = ""
    estoque: int = Field(default=0, ge=0)
    preco_custo: float = Field(default=0.0, ge=0.0)
    preco_venda: float = Field(default=0.0, ge=0.0)


class ProdutoInput(BaseModel):
    modelo_nome: str
    marca: Optional[str] = ""
    tecido: Optional[str] = ""
    corte: Optional[str] = ""
    cores_tags: Optional[str] = ""
    variacoes: list[VariacaoInput]


class ItemVendaInput(BaseModel):
    codigo_barras: str
    quantidade: int = Field(default=1, gt=0)


class VendaRequest(BaseModel):
    itens: list[ItemVendaInput]
    desconto_total: float = Field(default=0.0, ge=0.0)
    forma_pagamento: str = Field(default="DINHEIRO")
    cliente_id: Optional[int] = None
    data_vencimento_lote: Optional[str] = None


class PagamentoFiadoRequest(BaseModel):
    cliente_id: int
    valor: float = Field(..., gt=0)
    descricao: Optional[str] = "Pagamento via App"


class ClienteInput(BaseModel):
    nome: str
    telefone: Optional[str] = ""
    limite_credito: float = Field(default=500.0, ge=0.0)
    dia_preferencial_pagamento: Optional[int] = Field(default=5, ge=1, le=31)


# ---------------------------------------------------------------------------
# 1. POST /api/login
# ---------------------------------------------------------------------------
@app.post("/api/login")
def login(dados: LoginRequest):
    """Recebe usuario e senha e retorna token e role ('admin' ou 'vendedor')."""
    user_key = dados.usuario.strip().lower()
    senha = dados.senha.strip()

    registro = USUARIOS_SISTEMA.get(user_key)
    if not registro or not secrets.compare_digest(registro["senha"], senha):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos.",
        )

    token = secrets.token_hex(32)
    role = registro["role"]
    TOKENS_ATIVOS[token] = {
        "usuario": user_key,
        "role": role,
        "expira_em": datetime.now() + timedelta(hours=TOKEN_TTL_HORAS),
    }

    return {
        "sucesso": True,
        "token": token,
        "access_token": token,
        "token_type": "bearer",
        "role": role,
        "usuario": user_key,
    }


# ---------------------------------------------------------------------------
# 2. GET /api/estoque?busca=
# ---------------------------------------------------------------------------
@app.get("/api/estoque")
def listar_estoque(
    busca: str = Query(default="", description="Termo de busca tokenizada"),
    _user: dict = Depends(verificar_token),
):
    """Lista os produtos pai com suas variações aninhadas e faz busca tokenizada
    (.split() + all()) convertendo o objeto para string.
    """
    with get_db() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT id, modelo_nome, marca, tecido, corte, cores_tags
            FROM produtos
            ORDER BY id DESC
            """
        )
        produtos_rows = cur.fetchall()

        cur.execute(
            """
            SELECT id, produto_id, tamanho, cor, cor_hex, codigo_barras,
                   estoque, preco_custo, preco_venda
            FROM produto_variacoes
            ORDER BY id ASC
            """
        )
        variacoes_rows = cur.fetchall()

    variacoes_por_produto: dict[int, list[dict]] = {}
    for v in variacoes_rows:
        v_dict = {
            "id": v["id"],
            "produto_id": v["produto_id"],
            "tamanho": v["tamanho"] or "",
            "cor": v["cor"] or "",
            "cor_hex": v["cor_hex"] or "",
            "codigo_barras": v["codigo_barras"] or "",
            "estoque": int(v["estoque"] or 0),
            "preco_custo": float(v["preco_custo"] or 0.0),
            "preco_venda": float(v["preco_venda"] or 0.0),
        }
        variacoes_por_produto.setdefault(v["produto_id"], []).append(v_dict)

    produtos_lista = []
    for p in produtos_rows:
        pid = p["id"]
        vars_produto = variacoes_por_produto.get(pid, [])
        estoque_total = sum(v["estoque"] for v in vars_produto)
        preco_venda_ref = max((v["preco_venda"] for v in vars_produto), default=0.0)
        preco_custo_ref = max((v["preco_custo"] for v in vars_produto), default=0.0)

        item_produto = {
            "id": pid,
            "modelo_nome": p["modelo_nome"] or "",
            "marca": p["marca"] or "",
            "tecido": p["tecido"] or "",
            "corte": p["corte"] or "",
            "cores_tags": p["cores_tags"] or "",
            "estoque_total": estoque_total,
            "preco_custo": preco_custo_ref,
            "preco_venda": preco_venda_ref,
            "variacoes": vars_produto,
        }
        produtos_lista.append(item_produto)

    if busca and busca.strip():
        tokens = busca.lower().split()
        produtos_lista = [
            prod
            for prod in produtos_lista
            if all(token in str(prod).lower() for token in tokens)
        ]

    return {
        "sucesso": True,
        "produtos": produtos_lista,
    }


# ---------------------------------------------------------------------------
# 2B. CRUD DE PRODUTOS E VARIAÇÕES (PARA O DESKTOP / MOBILE)
# ---------------------------------------------------------------------------
def _montar_cores_tags(cores_tags_str: str, variacoes: list[VariacaoInput]) -> str:
    """Garante cores_tags no formato 'Nome|#HEX,Nome2|#HEX2'."""
    if cores_tags_str and cores_tags_str.strip():
        return cores_tags_str.strip()
    vistos = {}
    for v in variacoes:
        nome_cor = (v.cor or "").strip()
        hex_cor = (v.cor_hex or "#3b82f6").strip()
        if nome_cor and nome_cor not in vistos:
            vistos[nome_cor] = hex_cor
    return ",".join(f"{n}|{h}" for n, h in vistos.items())


@app.post("/api/estoque/produto")
def criar_produto(
    payload: ProdutoInput,
    _user: dict = Depends(verificar_token),
):
    """Cadastra um novo produto Pai e suas variações gerando código de barras KNB."""
    modelo = (payload.modelo_nome or "").strip()
    if not modelo:
        raise HTTPException(status_code=400, detail="O nome/modelo do produto é obrigatório.")
    if not payload.variacoes:
        raise HTTPException(status_code=400, detail="Adicione pelo menos uma variação (tamanho).")

    cores_tags = _montar_cores_tags(payload.cores_tags or "", payload.variacoes)

    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
            cur.execute(
                """
                INSERT INTO produtos (modelo_nome, marca, tecido, corte, cores_tags)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    modelo,
                    (payload.marca or "").strip(),
                    (payload.tecido or "").strip(),
                    (payload.corte or "").strip(),
                    cores_tags,
                ),
            )
            produto_id = cur.lastrowid

            for v in payload.variacoes:
                tam = (v.tamanho or "U").strip().upper()
                cor = (v.cor or "").strip()
                cor_hex = (v.cor_hex or "#3b82f6").strip()
                cod = (v.codigo_barras or "").strip()

                cur.execute(
                    """
                    INSERT INTO produto_variacoes (
                        produto_id, tamanho, cor, cor_hex, codigo_barras,
                        estoque, preco_custo, preco_venda
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        produto_id,
                        tam,
                        cor,
                        cor_hex,
                        cod,
                        int(v.estoque or 0),
                        round(float(v.preco_custo or 0.0), 2),
                        round(float(v.preco_venda or 0.0), 2),
                    ),
                )
                vid = cur.lastrowid
                if not cod:
                    cod_gerado = f"KNB{produto_id:05d}{vid:04d}"
                    cur.execute(
                        "UPDATE produto_variacoes SET codigo_barras = ? WHERE id = ?",
                        (cod_gerado, vid),
                    )

            conn.commit()
            return {
                "sucesso": True,
                "mensagem": f"Produto '{modelo}' cadastrado com sucesso!",
                "produto_id": produto_id,
            }
        except Exception as exc:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Erro ao cadastrar produto: {exc}") from exc


@app.put("/api/estoque/produto/{produto_id}")
def atualizar_produto(
    produto_id: int,
    payload: ProdutoInput,
    _user: dict = Depends(verificar_token),
):
    """Atualiza um produto Pai e sincroniza suas variações (Soft-Update)."""
    modelo = (payload.modelo_nome or "").strip()
    if not modelo:
        raise HTTPException(status_code=400, detail="O nome/modelo do produto é obrigatório.")
    if not payload.variacoes:
        raise HTTPException(status_code=400, detail="O produto precisa ter ao menos uma variação.")

    cores_tags = _montar_cores_tags(payload.cores_tags or "", payload.variacoes)

    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
            cur.execute("SELECT id FROM produtos WHERE id = ?", (produto_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Produto não encontrado.")

            cur.execute(
                """
                UPDATE produtos
                SET modelo_nome = ?, marca = ?, tecido = ?, corte = ?, cores_tags = ?
                WHERE id = ?
                """,
                (
                    modelo,
                    (payload.marca or "").strip(),
                    (payload.tecido or "").strip(),
                    (payload.corte or "").strip(),
                    cores_tags,
                    produto_id,
                ),
            )

            cur.execute(
                "SELECT id FROM produto_variacoes WHERE produto_id = ?",
                (produto_id,),
            )
            ids_existentes = {r["id"] for r in cur.fetchall()}
            ids_recebidos = set()

            for v in payload.variacoes:
                tam = (v.tamanho or "U").strip().upper()
                cor = (v.cor or "").strip()
                cor_hex = (v.cor_hex or "#3b82f6").strip()
                cod = (v.codigo_barras or "").strip()

                if v.id and v.id in ids_existentes:
                    ids_recebidos.add(v.id)
                    if not cod:
                        cod = f"KNB{produto_id:05d}{v.id:04d}"
                    cur.execute(
                        """
                        UPDATE produto_variacoes
                        SET tamanho = ?, cor = ?, cor_hex = ?, codigo_barras = ?,
                            estoque = ?, preco_custo = ?, preco_venda = ?
                        WHERE id = ? AND produto_id = ?
                        """,
                        (
                            tam,
                            cor,
                            cor_hex,
                            cod,
                            int(v.estoque or 0),
                            round(float(v.preco_custo or 0.0), 2),
                            round(float(v.preco_venda or 0.0), 2),
                            v.id,
                            produto_id,
                        ),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO produto_variacoes (
                            produto_id, tamanho, cor, cor_hex, codigo_barras,
                            estoque, preco_custo, preco_venda
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            produto_id,
                            tam,
                            cor,
                            cor_hex,
                            cod,
                            int(v.estoque or 0),
                            round(float(v.preco_custo or 0.0), 2),
                            round(float(v.preco_venda or 0.0), 2),
                        ),
                    )
                    vid = cur.lastrowid
                    if not cod:
                        cod_gerado = f"KNB{produto_id:05d}{vid:04d}"
                        cur.execute(
                            "UPDATE produto_variacoes SET codigo_barras = ? WHERE id = ?",
                            (cod_gerado, vid),
                        )

            ids_remover = ids_existentes - ids_recebidos
            for rid in ids_remover:
                cur.execute("UPDATE vendas SET variacao_id = NULL WHERE variacao_id = ?", (rid,))
                cur.execute("DELETE FROM produto_variacoes WHERE id = ?", (rid,))

            conn.commit()
            return {
                "sucesso": True,
                "mensagem": f"Produto '{modelo}' atualizado com sucesso!",
                "produto_id": produto_id,
            }
        except HTTPException:
            conn.rollback()
            raise
        except Exception as exc:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Erro ao atualizar produto: {exc}") from exc


@app.delete("/api/estoque/produto/{produto_id}")
def excluir_produto(
    produto_id: int,
    _user: dict = Depends(verificar_token),
):
    """Remove um produto Pai e todas as suas variações (preservando histórico de vendas)."""
    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
            cur.execute("SELECT modelo_nome FROM produtos WHERE id = ?", (produto_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Produto não encontrado.")

            cur.execute(
                """
                UPDATE vendas
                SET variacao_id = NULL
                WHERE variacao_id IN (
                    SELECT id FROM produto_variacoes WHERE produto_id = ?
                )
                """,
                (produto_id,),
            )
            cur.execute("DELETE FROM produto_variacoes WHERE produto_id = ?", (produto_id,))
            cur.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
            conn.commit()
            return {
                "sucesso": True,
                "mensagem": f"Produto '{row['modelo_nome']}' excluído.",
            }
        except HTTPException:
            conn.rollback()
            raise
        except Exception as exc:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Erro ao excluir produto: {exc}") from exc


# ---------------------------------------------------------------------------
# 3. GET /api/qrcode/{codigo}
# ---------------------------------------------------------------------------
@app.get("/api/qrcode/{codigo}")
def buscar_qrcode(
    codigo: str,
    _user: dict = Depends(verificar_token),
):
    """Faz JOIN entre produto_variacoes e produtos buscando por codigo_barras
    (case-insensitive) e retorna os detalhes da peça.
    """
    codigo_limpo = (codigo or "").strip()
    if not codigo_limpo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código de barras não informado.",
        )

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                pv.id AS id,
                pv.id AS variacao_id,
                pv.produto_id,
                p.modelo_nome,
                p.marca,
                p.tecido,
                p.corte,
                p.cores_tags,
                pv.tamanho,
                pv.cor,
                pv.cor_hex,
                pv.codigo_barras,
                pv.estoque,
                pv.preco_custo,
                pv.preco_venda
            FROM produto_variacoes pv
            INNER JOIN produtos p ON p.id = pv.produto_id
            WHERE LOWER(pv.codigo_barras) = LOWER(?)
            LIMIT 1
            """,
            (codigo_limpo,),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Peça com código '{codigo_limpo}' não encontrada.",
        )

    cor_exibicao = row["cor"] or ""
    if not cor_exibicao and row["cores_tags"]:
        cor_exibicao = ", ".join(
            [t.split("|")[0] for t in row["cores_tags"].split(",") if "|" in t]
        )

    item_dict = {
        "id": row["id"],
        "variacao_id": row["variacao_id"],
        "produto_id": row["produto_id"],
        "modelo_nome": row["modelo_nome"] or "",
        "marca": row["marca"] or "",
        "tecido": row["tecido"] or "",
        "corte": row["corte"] or "",
        "cores_tags": row["cores_tags"] or "",
        "tamanho": row["tamanho"] or "",
        "cor": cor_exibicao,
        "cor_hex": row["cor_hex"] or "",
        "codigo_barras": row["codigo_barras"] or "",
        "estoque": int(row["estoque"] or 0),
        "preco_custo": float(row["preco_custo"] or 0.0),
        "preco_venda": float(row["preco_venda"] or 0.0),
    }

    return {
        "sucesso": True,
        "item": item_dict,
        **item_dict,
    }


# ---------------------------------------------------------------------------
# 4. POST /api/vendas  &  GET /api/vendas/hoje
# ---------------------------------------------------------------------------
@app.get("/api/vendas/hoje")
def listar_vendas_hoje(_user: dict = Depends(verificar_token)):
    """Retorna as vendas registradas na data de hoje e resumo por forma de pagamento."""
    hoje_prefixo = datetime.now().strftime("%d/%m/%Y")
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                id, variacao_id, modelo_nome, marca, cor, tamanho,
                quantidade, valor_unitario, valor_total, preco_custo,
                data_venda, forma_pagamento
            FROM vendas
            WHERE data_venda LIKE ?
            ORDER BY id DESC
            LIMIT 100
            """,
            (f"{hoje_prefixo}%",),
        )
        rows = cur.fetchall()

    vendas = []
    faturamento_hoje = 0.0
    pecas_hoje = 0
    for r in rows:
        vt = round(float(r["valor_total"] or 0.0), 2)
        qtd = int(r["quantidade"] or 0)
        faturamento_hoje += vt
        pecas_hoje += qtd
        vendas.append(
            {
                "id": r["id"],
                "variacao_id": r["variacao_id"],
                "modelo_nome": r["modelo_nome"] or "",
                "marca": r["marca"] or "",
                "cor": r["cor"] or "",
                "tamanho": r["tamanho"] or "",
                "quantidade": qtd,
                "valor_unitario": round(float(r["valor_unitario"] or 0.0), 2),
                "valor_total": vt,
                "data_venda": r["data_venda"] or "",
                "forma_pagamento": r["forma_pagamento"] or "DINHEIRO",
            }
        )

    return {
        "sucesso": True,
        "data": hoje_prefixo,
        "faturamento_hoje": round(faturamento_hoje, 2),
        "pecas_hoje": pecas_hoje,
        "vendas": vendas,
    }


@app.post("/api/vendas")
def registrar_venda(
    payload: VendaRequest,
    _user: dict = Depends(verificar_token),
):
    """Em uma transação atômica, valida estoque, abate de produto_variacoes,
    insere em vendas e, se forma_pagamento == 'FIADO', insere um registro
    'DEBITO' em conta_fiado.
    """
    if not payload.itens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A lista de itens da venda não pode estar vazia.",
        )

    forma_pgto = (payload.forma_pagamento or "DINHEIRO").strip().upper()
    if forma_pgto == "FIADO" and not payload.cliente_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cliente_id é obrigatório para vendas na modalidade FIADO.",
        )

    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")

            itens_processados = []
            subtotal_geral = 0.0

            # Agrupa itens com mesmo codigo_barras para validação exata de estoque
            itens_agrupados: dict[str, int] = {}
            for item in payload.itens:
                cod = (item.codigo_barras or "").strip()
                qtd = int(item.quantidade)
                if qtd <= 0 or not cod:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Quantidade inválida para o código '{cod}'.",
                    )
                chave = cod.lower()
                itens_agrupados[chave] = itens_agrupados.get(chave, 0) + qtd

            for cod_lower, qtd in itens_agrupados.items():
                cur.execute(
                    """
                    SELECT
                        pv.id,
                        pv.produto_id,
                        pv.tamanho,
                        pv.cor,
                        pv.codigo_barras,
                        pv.estoque,
                        pv.preco_custo,
                        pv.preco_venda,
                        p.modelo_nome,
                        p.marca,
                        p.cores_tags
                    FROM produto_variacoes pv
                    INNER JOIN produtos p ON p.id = pv.produto_id
                    WHERE LOWER(pv.codigo_barras) = ?
                    LIMIT 1
                    """,
                    (cod_lower,),
                )
                v_row = cur.fetchone()
                if not v_row:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Produto com código de barras '{cod_lower}' não encontrado.",
                    )

                estoque_atual = int(v_row["estoque"] or 0)
                if estoque_atual < qtd:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Estoque insuficiente para '{v_row['modelo_nome']}' "
                            f"({v_row['tamanho']}). Disponível: {estoque_atual}, "
                            f"solicitado: {qtd}."
                        ),
                    )

                preco_venda = float(v_row["preco_venda"] or 0.0)
                subtotal_item = preco_venda * qtd
                subtotal_geral += subtotal_item

                cor_item = v_row["cor"] or ""
                if not cor_item and v_row["cores_tags"]:
                    cor_item = ", ".join(
                        [
                            t.split("|")[0]
                            for t in v_row["cores_tags"].split(",")
                            if "|" in t
                        ]
                    )

                itens_processados.append(
                    {
                        "variacao_id": v_row["id"],
                        "codigo_barras": v_row["codigo_barras"],
                        "modelo_nome": v_row["modelo_nome"] or "",
                        "marca": v_row["marca"] or "",
                        "cor": cor_item,
                        "tamanho": v_row["tamanho"] or "",
                        "quantidade": qtd,
                        "preco_custo": float(v_row["preco_custo"] or 0.0),
                        "subtotal": subtotal_item,
                    }
                )

            desconto_aplicado = min(
                max(0.0, float(payload.desconto_total or 0.0)), subtotal_geral
            )
            fator = (
                (subtotal_geral - desconto_aplicado) / subtotal_geral
                if subtotal_geral > 0
                else 1.0
            )

            data_venda_str = datetime.now().strftime("%d/%m/%Y %H:%M")
            valor_total_liquido = 0.0
            resumo_pecas = []
            vendas_ids = []

            for item in itens_processados:
                cur.execute(
                    """
                    UPDATE produto_variacoes
                    SET estoque = estoque - ?
                    WHERE id = ? AND estoque >= ?
                    """,
                    (item["quantidade"], item["variacao_id"], item["quantidade"]),
                )
                if cur.rowcount == 0:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"Conflito de estoque ao abater '{item['modelo_nome']}' "
                            f"({item['tamanho']})."
                        ),
                    )

                valor_item_final = round(item["subtotal"] * fator, 2)
                valor_unitario_final = round(valor_item_final / item["quantidade"], 2)
                valor_total_liquido = round(valor_total_liquido + valor_item_final, 2)

                cur.execute(
                    """
                    INSERT INTO vendas (
                        variacao_id, modelo_nome, marca, cor, tamanho,
                        quantidade, valor_unitario, valor_total, preco_custo,
                        data_venda, forma_pagamento
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item["variacao_id"],
                        item["modelo_nome"],
                        item["marca"],
                        item["cor"],
                        item["tamanho"],
                        item["quantidade"],
                        valor_unitario_final,
                        valor_item_final,
                        item["preco_custo"],
                        data_venda_str,
                        forma_pgto,
                    ),
                )
                vendas_ids.append(cur.lastrowid)
                resumo_pecas.append(
                    f"{item['quantidade']}x {item['modelo_nome']} ({item['tamanho']})"
                )

            if forma_pgto == "FIADO":
                cur.execute(
                    """
                    SELECT id, nome, limite_credito, dia_preferencial_pagamento
                    FROM clientes
                    WHERE id = ?
                    """,
                    (payload.cliente_id,),
                )
                cliente_row = cur.fetchone()
                if not cliente_row:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Cliente id={payload.cliente_id} não encontrado.",
                    )

                cur.execute(
                    """
                    SELECT
                        COALESCE(SUM(CASE WHEN tipo_movimentacao = 'DEBITO' THEN valor ELSE 0 END), 0) -
                        COALESCE(SUM(CASE WHEN tipo_movimentacao = 'CREDITO' THEN valor ELSE 0 END), 0) AS saldo
                    FROM conta_fiado
                    WHERE cliente_id = ?
                    """,
                    (payload.cliente_id,),
                )
                saldo_atual = max(0.0, round(float(cur.fetchone()["saldo"] or 0.0), 2))
                limite_cli  = round(float(cliente_row["limite_credito"] or 0.0), 2)
                if limite_cli > 0 and (saldo_atual + valor_total_liquido) > limite_cli:
                    disponivel_cli = max(0.0, limite_cli - saldo_atual)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Limite de crédito excedido para {cliente_row['nome']}! "
                            f"Limite: R$ {limite_cli:.2f} | Disponível: R$ {disponivel_cli:.2f}"
                        ),
                    )

                agora_dt = datetime.now()
                agora_iso = agora_dt.strftime("%Y-%m-%d %H:%M:%S.%f")

                if payload.data_vencimento_lote:
                    vencimento_iso = payload.data_vencimento_lote
                else:
                    vencimento_dt = agora_dt + timedelta(days=30)
                    vencimento_iso = vencimento_dt.strftime("%Y-%m-%d %H:%M:%S.%f")

                descricao_fiado = f"Compra: {', '.join(resumo_pecas)}"

                cur.execute(
                    """
                    INSERT INTO conta_fiado (
                        cliente_id, tipo_movimentacao, valor,
                        data_movimentacao, data_vencimento_lote, descricao
                    ) VALUES (?, 'DEBITO', ?, ?, ?, ?)
                    """,
                    (
                        payload.cliente_id,
                        valor_total_liquido,
                        agora_iso,
                        vencimento_iso,
                        descricao_fiado,
                    ),
                )

            conn.commit()

            total_final = round(valor_total_liquido, 2)
            return {
                "sucesso": True,
                "mensagem": "Venda realizada com sucesso.",
                "vendas_ids": vendas_ids,
                "subtotal": round(subtotal_geral, 2),
                "desconto_total": round(desconto_aplicado, 2),
                "valor_total": total_final,
                "total_cobrado": total_final,
                "forma_pagamento": forma_pgto,
                "cliente_id": payload.cliente_id,
            }

        except HTTPException:
            conn.rollback()
            raise
        except Exception as exc:
            conn.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao processar venda: {str(exc)}",
            ) from exc


# ---------------------------------------------------------------------------
# 5. GET & POST & DELETE /api/fiado/clientes
# ---------------------------------------------------------------------------
@app.get("/api/fiado/clientes")
def listar_clientes_fiado(_user: dict = Depends(verificar_token)):
    """Lista todos os clientes calculando o saldo_devedor (soma de DEBITO menos
    soma de CREDITO em conta_fiado) e os últimos 10 lançamentos em lote (sem N+1).
    """
    with get_db() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                c.id,
                c.nome,
                c.telefone,
                c.limite_credito,
                c.dia_preferencial_pagamento,
                COALESCE(SUM(CASE WHEN cf.tipo_movimentacao = 'DEBITO' THEN cf.valor ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN cf.tipo_movimentacao = 'CREDITO' THEN cf.valor ELSE 0 END), 0) AS saldo_devedor
            FROM clientes c
            LEFT JOIN conta_fiado cf ON cf.cliente_id = c.id
            GROUP BY c.id, c.nome, c.telefone, c.limite_credito, c.dia_preferencial_pagamento
            ORDER BY saldo_devedor DESC, c.nome ASC
            """
        )
        clientes_rows = cur.fetchall()

        cur.execute(
            """
            SELECT
                id,
                cliente_id,
                tipo_movimentacao,
                valor,
                data_movimentacao,
                data_vencimento_lote,
                descricao
            FROM conta_fiado
            ORDER BY data_movimentacao DESC, id DESC
            """
        )
        todos_lancamentos = cur.fetchall()

        lancamentos_por_cliente: dict[int, list[dict]] = {}
        for m in todos_lancamentos:
            cid_m = m["cliente_id"]
            lista_c = lancamentos_por_cliente.setdefault(cid_m, [])
            if len(lista_c) < 10:
                lista_c.append(
                    {
                        "id": m["id"],
                        "cliente_id": cid_m,
                        "tipo_movimentacao": m["tipo_movimentacao"],
                        "valor": round(float(m["valor"] or 0.0), 2),
                        "data_movimentacao": m["data_movimentacao"],
                        "data_vencimento_lote": m["data_vencimento_lote"],
                        "descricao": m["descricao"] or "",
                    }
                )

        resultado = []
        for c in clientes_rows:
            cid = c["id"]
            ultimos_lancamentos = lancamentos_por_cliente.get(cid, [])

            limite = round(float(c["limite_credito"] or 0.0), 2)
            saldo = round(float(c["saldo_devedor"] or 0.0), 2)
            disponivel = round(max(0.0, limite - max(0.0, saldo)), 2)

            resultado.append(
                {
                    "id": cid,
                    "nome": c["nome"],
                    "telefone": c["telefone"] or "",
                    "limite_credito": limite,
                    "dia_preferencial_pagamento": c["dia_preferencial_pagamento"],
                    "saldo_devedor": saldo,
                    "disponivel": disponivel,
                    "historico": ultimos_lancamentos,
                    "ultimos_lancamentos": ultimos_lancamentos,
                    "lancamentos": ultimos_lancamentos,
                }
            )

    return {
        "sucesso": True,
        "clientes": resultado,
    }


@app.post("/api/fiado/clientes")
def cadastrar_cliente_fiado(
    payload: ClienteInput,
    _user: dict = Depends(verificar_token),
):
    """Cadastra um novo cliente na tabela clientes."""
    nome = (payload.nome or "").strip()
    if not nome:
        raise HTTPException(status_code=400, detail="O nome do cliente é obrigatório.")

    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute("SELECT id FROM clientes WHERE LOWER(nome) = LOWER(?)", (nome,))
            if cur.fetchone():
                raise HTTPException(
                    status_code=400, detail=f"Já existe um cliente cadastrado como '{nome}'."
                )

            cur.execute(
                """
                INSERT INTO clientes (nome, telefone, limite_credito, dia_preferencial_pagamento)
                VALUES (?, ?, ?, ?)
                """,
                (
                    nome,
                    (payload.telefone or "").strip(),
                    round(float(payload.limite_credito or 500.0), 2),
                    int(payload.dia_preferencial_pagamento or 5),
                ),
            )
            novo_id = cur.lastrowid
            conn.commit()
            return {
                "sucesso": True,
                "mensagem": f"Cliente '{nome}' cadastrado com sucesso!",
                "cliente_id": novo_id,
            }
        except HTTPException:
            conn.rollback()
            raise
        except Exception as exc:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Erro ao cadastrar cliente: {exc}") from exc


@app.delete("/api/fiado/clientes/{cliente_id}")
def remover_cliente_fiado(
    cliente_id: int,
    _user: dict = Depends(verificar_token),
):
    """Remove um cliente caso não possua saldo devedor em aberto."""
    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute("SELECT id, nome FROM clientes WHERE id = ?", (cliente_id,))
            cli = cur.fetchone()
            if not cli:
                raise HTTPException(status_code=404, detail="Cliente não encontrado.")

            cur.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN tipo_movimentacao = 'DEBITO' THEN valor ELSE 0 END), 0) -
                    COALESCE(SUM(CASE WHEN tipo_movimentacao = 'CREDITO' THEN valor ELSE 0 END), 0) AS saldo
                FROM conta_fiado
                WHERE cliente_id = ?
                """,
                (cliente_id,),
            )
            saldo = round(float(cur.fetchone()["saldo"] or 0.0), 2)
            if abs(saldo) > 0.01:
                raise HTTPException(
                    status_code=400,
                    detail=f"Não é possível excluir '{cli['nome']}' com saldo pendente de R$ {saldo:.2f}.",
                )

            cur.execute("DELETE FROM conta_fiado WHERE cliente_id = ?", (cliente_id,))
            cur.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
            conn.commit()
            return {
                "sucesso": True,
                "mensagem": f"Cliente '{cli['nome']}' removido com sucesso.",
            }
        except HTTPException:
            conn.rollback()
            raise
        except Exception as exc:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Erro ao remover cliente: {exc}") from exc


# ---------------------------------------------------------------------------
# 6. POST /api/fiado/pagar
# ---------------------------------------------------------------------------
@app.post("/api/fiado/pagar")
def pagar_fiado(
    payload: PagamentoFiadoRequest,
    _user: dict = Depends(verificar_token),
):
    """Insere um lançamento 'CREDITO' na tabela conta_fiado para abater
    a dívida do cliente (limitando ao saldo devedor atual para evitar saldo negativo).
    """
    if payload.valor <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O valor do pagamento deve ser maior que zero.",
        )

    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")

            cur.execute(
                "SELECT id, nome FROM clientes WHERE id = ?",
                (payload.cliente_id,),
            )
            cliente = cur.fetchone()
            if not cliente:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Cliente id={payload.cliente_id} não encontrado.",
                )

            cur.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN tipo_movimentacao = 'DEBITO' THEN valor ELSE 0 END), 0) -
                    COALESCE(SUM(CASE WHEN tipo_movimentacao = 'CREDITO' THEN valor ELSE 0 END), 0) AS saldo
                FROM conta_fiado
                WHERE cliente_id = ?
                """,
                (payload.cliente_id,),
            )
            saldo_atual = round(float(cur.fetchone()["saldo"] or 0.0), 2)
            if saldo_atual <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{cliente['nome']} não possui dívida em aberto.",
                )

            valor_efetivo = round(min(float(payload.valor), saldo_atual), 2)
            agora_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            descricao = (payload.descricao or "Pagamento de Fiado").strip()

            cur.execute(
                """
                INSERT INTO conta_fiado (
                    cliente_id, tipo_movimentacao, valor,
                    data_movimentacao, data_vencimento_lote, descricao
                ) VALUES (?, 'CREDITO', ?, ?, NULL, ?)
                """,
                (
                    payload.cliente_id,
                    valor_efetivo,
                    agora_iso,
                    descricao,
                ),
            )
            lancamento_id = cur.lastrowid
            novo_saldo = round(max(0.0, saldo_atual - valor_efetivo), 2)

            conn.commit()

            return {
                "sucesso": True,
                "mensagem": f"Pagamento de R$ {valor_efetivo:.2f} registrado para {cliente['nome']}.",
                "lancamento_id": lancamento_id,
                "cliente_id": payload.cliente_id,
                "valor_pago": valor_efetivo,
                "saldo_devedor": novo_saldo,
            }
        except HTTPException:
            conn.rollback()
            raise
        except Exception as exc:
            conn.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao registrar pagamento: {str(exc)}",
            ) from exc


# ---------------------------------------------------------------------------
# 7. SERVIR ARQUIVOS ESTÁTICOS (/static E / -> static/index.html)
# ---------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index_root():
    """Serve 'static/index.html' na rota raiz '/'."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return HTMLResponse(
        content="<h1>Kanemberg Mobile API</h1><p>Coloque o arquivo <code>static/index.html</code> para servir a interface web.</p>",
        status_code=200,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
