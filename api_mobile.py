"""
api_mobile.py — API Unificada Mobile & Desktop (FastAPI + sqlite3 nativo)
Conectada diretamente ao banco 'loja_daniel_v2.db' na raiz do projeto.
"""

import io
import json
import os
import secrets
import sqlite3
import socket
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# CONFIGURAÇÃO DE CAMINHOS, .ENV NATIVO E BANCO DE DADOS (SQLITE3 NATIVO)
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "loja_daniel_v2.db")
STATIC_DIR = os.path.join(BASE_DIR, "static")
STATIC_SISTEMA_DIR = os.path.join(BASE_DIR, "static_sistema")
BACKUPS_DIR = os.path.join(BASE_DIR, "backups")
LOGO_PATH = os.path.join(BASE_DIR, "logo_kanemberg.png")
ENV_PATH = os.path.join(BASE_DIR, ".env")
PORTA_SERVIDOR = int(os.getenv("PORTA_SERVIDOR", "8000"))

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(STATIC_SISTEMA_DIR, exist_ok=True)
os.makedirs(BACKUPS_DIR, exist_ok=True)


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
# CLASSIFICAÇÃO DE GRUPOS (COMPARTILHADA COM O DASHBOARD)
# ---------------------------------------------------------------------------
GRUPOS_META = {
    "cima": {
        "chave": "cima",
        "nome": "Parte de Cima",
        "rotulo": "Cima",
        "palavras": (
            "blusa", "camisa", "camiseta", "casaco", "vestido",
            "regata", "cropped", "sueter", "suéter", "moletom", "polo", "jaqueta",
        ),
    },
    "baixo": {
        "chave": "baixo",
        "nome": "Parte de Baixo / Praia",
        "rotulo": "Baixo",
        "palavras": (
            "calça", "calca", "shorts", "short", "bermuda",
            "sunga", "saia", "biquini", "biquíni", "maio", "maiô",
        ),
    },
    "calcados": {
        "chave": "calcados",
        "nome": "Calçados / Meias",
        "rotulo": "Calçados",
        "palavras": (
            "chinelo", "meia", "sandalia", "sandália",
            "tenis", "tênis", "sapato", "bota", "sapatenis", "sapatênis",
        ),
    },
    "acessorios": {
        "chave": "acessorios",
        "nome": "Acessórios",
        "rotulo": "Acessórios",
        "palavras": (
            "boné", "bone", "óculos", "oculos", "relógio", "relogio",
            "cinto", "carteira", "bolsa", "corrente", "pulseira", "chapéu", "chapeu", "touca",
        ),
    },
    "perfumaria": {
        "chave": "perfumaria",
        "nome": "Perfumaria",
        "rotulo": "Perfumes",
        "palavras": (
            "perfume", "colonia", "colônia", "fragrancia",
            "fragrância", "desodorante", "body splash", "hidratante",
        ),
    },
}


def _classificar_grupo_produto(modelo_nome: str) -> dict:
    texto = (modelo_nome or "").lower().strip()
    for info in GRUPOS_META.values():
        for palavra in info["palavras"]:
            if texto.startswith(palavra) or f" {palavra}" in texto:
                return info
    return GRUPOS_META["cima"]


# ---------------------------------------------------------------------------
# INICIALIZAÇÃO DO FASTAPI, CORS E CONTROLE DE ACESSO MOBILE (ON/OFF)
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Kanemberg PDV — API Mobile & Desktop",
    description="API integrada ao banco loja_daniel_v2.db",
    version="2.6.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

acesso_mobile_ativo: bool = True
_HOSTS_LOCAIS = ("127.0.0.1", "::1", "localhost", "testclient")
_MSG_MOBILE_OFF = "Acesso Mobile temporariamente desativado no computador do caixa."


def _requisicao_local_direta(request: Request) -> bool:
    """Verifica se a requisição vem da própria máquina (sem túnel/proxy externo)."""
    host = (request.client.host if request.client else "").strip().lower()
    if host not in _HOSTS_LOCAIS:
        return False
    for hdr in ("x-forwarded-for", "cf-connecting-ip", "x-real-ip"):
        val = (request.headers.get(hdr) or "").strip().lower()
        if val and val not in _HOSTS_LOCAIS:
            return False
    return True


def _acesso_permitido_quando_mobile_off(request: Request) -> bool:
    """Quando Mobile está OFF, permite o computador local do caixa (/sistema e header X-Sistema-Desktop)."""
    eh_desktop_hdr = request.headers.get("x-sistema-desktop") == "1"
    referer = (request.headers.get("referer") or "").lower()
    caminho = request.url.path or "/"

    if not _requisicao_local_direta(request):
        return False

    if eh_desktop_hdr or "/sistema" in referer:
        return True

    # Rotas exclusivas do Desktop local (abertura da janela /sistema, assets e imagens QR)
    if (
        caminho == "/sistema"
        or caminho.startswith("/sistema/")
        or caminho.startswith("/static_sistema")
        or caminho == "/logo_kanemberg.png"
        or caminho == "/robots.txt"
        or caminho.startswith("/api/qrcode/svg/")
        or caminho.startswith("/api/sistema/")
    ):
        return True

    return False


@app.middleware("http")
async def _middleware_seguranca_e_acesso_mobile(request: Request, call_next):
    ua = (request.headers.get("user-agent") or "").lower()
    bots_bloqueados = (
        "googlebot", "adsbot", "safebrowsing", "headlesschrome", "crawler", "spider", "censys"
    )
    if any(b in ua for b in bots_bloqueados):
        return HTMLResponse(
            content="<!DOCTYPE html><html><head><title>OK</title></head><body>OK</body></html>",
            status_code=200,
        )

    if not acesso_mobile_ativo and not _acesso_permitido_quando_mobile_off(request):
        accept = (request.headers.get("accept") or "").lower()
        if "text/html" in accept and not request.url.path.startswith("/api/"):
            html_bloqueio = (
                "<!DOCTYPE html><html lang='pt-BR'><head><meta charset='UTF-8'>"
                "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                "<title>Acesso Mobile Desativado</title>"
                "<style>body{margin:0;min-height:100vh;display:flex;align-items:center;"
                "justify-content:center;background:#0b1120;color:#f8fafc;"
                "font-family:system-ui,-apple-system,sans-serif;padding:24px;text-align:center}"
                ".box{max-width:420px;background:#111827;border:1px solid #334155;"
                "border-radius:12px;padding:28px}h1{font-size:18px;margin:0 0 10px}"
                "p{margin:0;color:#94a3b8;font-size:14px;line-height:1.5}</style></head>"
                f"<body><div class='box'><h1>Conexão Externa Bloqueada</h1><p>{_MSG_MOBILE_OFF}</p></div></body></html>"
            )
            return HTMLResponse(content=html_bloqueio, status_code=403)
        return JSONResponse(status_code=403, content={"detail": _MSG_MOBILE_OFF})

    response = await call_next(request)
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive, nosnippet"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/robots.txt")
def robots_txt():
    return HTMLResponse(content="User-agent: *\nDisallow: /\n", media_type="text/plain")


# ---------------------------------------------------------------------------
# AUTENTICAÇÃO POR BEARER TOKEN + BYPASS DO SISTEMA DESKTOP LOCAL
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
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Valida o Bearer Token enviado no header Authorization e verifica expiração.
    Também autentica automaticamente requisições vindas do Sistema Desktop (/sistema).
    """
    if credentials and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
        usuario_info = TOKENS_ATIVOS.get(token)
        if usuario_info:
            if datetime.now() <= usuario_info["expira_em"]:
                return usuario_info
            TOKENS_ATIVOS.pop(token, None)

    referer = (request.headers.get("referer") or "").lower()
    if request.headers.get("x-sistema-desktop") == "1" or "/sistema" in referer:
        return {
            "usuario": os.getenv("ADMIN_USER", "admin").strip().lower(),
            "role": "admin",
            "expira_em": datetime.now() + timedelta(hours=TOKEN_TTL_HORAS),
        }

    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação ausente ou inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado. Faça login novamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def exigir_acesso_local_caixa(request: Request) -> None:
    """Garante que operações sensíveis do servidor rodem apenas no computador do caixa."""
    if not _requisicao_local_direta(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operação permitida apenas diretamente no computador do caixa.",
        )


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
    preco_custo: Optional[float] = Field(default=None)
    preco_venda: Optional[float] = Field(default=None)


class ProdutoInput(BaseModel):
    modelo_nome: str
    marca: Optional[str] = ""
    tecido: Optional[str] = ""
    corte: Optional[str] = ""
    grupo: Optional[str] = ""
    cores_tags: Optional[str] = ""
    cores: Optional[object] = None
    cor: Optional[str] = ""
    cor_hex: Optional[str] = ""
    preco_custo: Optional[float] = 0.0
    preco_venda: Optional[float] = 0.0
    variacoes: Optional[list[VariacaoInput]] = None
    grade: Optional[object] = None


class AtributoInput(BaseModel):
    categoria: Optional[str] = None
    tipo: Optional[str] = None
    valor: Optional[str] = None
    nome: Optional[str] = None
    cor_hex: Optional[str] = None


class ItemVendaInput(BaseModel):
    codigo_barras: Optional[str] = ""
    variacao_id: Optional[int] = None
    quantidade: int = Field(default=1, gt=0)
    preco_unitario: Optional[float] = None


class VendaRequest(BaseModel):
    itens: list[ItemVendaInput]
    desconto_total: float = Field(default=0.0, ge=0.0)
    desconto: Optional[float] = None
    forma_pagamento: str = Field(default="DINHEIRO")
    cliente_id: Optional[int] = None
    data_vencimento_lote: Optional[str] = None


class PagamentoFiadoRequest(BaseModel):
    cliente_id: int
    valor: float = Field(..., gt=0)
    descricao: Optional[str] = "Pagamento de Fiado"


class DebitoFiadoRequest(BaseModel):
    cliente_id: int
    valor: float = Field(..., gt=0)
    descricao: Optional[str] = "Débito avulso"
    data_vencimento_lote: Optional[str] = ""


class ClienteInput(BaseModel):
    nome: str
    telefone: Optional[str] = ""
    limite_credito: float = Field(default=500.0, ge=0.0)
    dia_preferencial_pagamento: Optional[int] = Field(default=None)
    dia_vencimento: Optional[int] = Field(default=None)


class ClienteUpdateInput(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    limite_credito: Optional[float] = Field(default=None, ge=0.0)
    dia_preferencial_pagamento: Optional[int] = None
    dia_vencimento: Optional[int] = None


class MobileToggleInput(BaseModel):
    ativo: bool


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
# 2. ESTOQUE, PRODUTOS E ATRIBUTOS
# ---------------------------------------------------------------------------
@app.get("/api/estoque")
def listar_estoque(
    busca: str = Query(default="", description="Termo de busca tokenizada"),
    _user: dict = Depends(verificar_token),
):
    """Lista os produtos pai com suas variações aninhadas e busca tokenizada."""
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

        produtos_lista.append(
            {
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
        )

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


def _garantir_atributo(cur: sqlite3.Cursor, categoria: str, valor: str) -> None:
    limpo = (valor or "").strip()
    if not limpo or limpo.upper() in ("N/A", "NA", "-", "—", "SEM MARCA", "PADRÃO", "PADRAO"):
        return
    cur.execute(
        "SELECT id FROM atributos WHERE LOWER(categoria) = LOWER(?) AND LOWER(nome) = LOWER(?) LIMIT 1",
        (categoria, limpo),
    )
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO atributos (categoria, nome) VALUES (?, ?)",
            (categoria, limpo),
        )


@app.get("/api/atributos")
def listar_atributos(_user: dict = Depends(verificar_token)):
    """Lista atributos dinâmicos agrupados por categoria (marca, corte, tecido, tipo_peca, cor)."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, categoria, nome FROM atributos ORDER BY id ASC")
        rows = cur.fetchall()

    agrupados: dict[str, list] = {
        "marca": [],
        "corte": [],
        "tecido": [],
        "tipo_peca": [],
        "cor": [],
    }

    for r in rows:
        cat = (r["categoria"] or "").strip().lower()
        nome_raw = (r["nome"] or "").strip()
        if not cat or not nome_raw:
            continue
        if cat == "cor":
            if "|" in nome_raw:
                nome_c, hex_c = nome_raw.split("|", 1)
                agrupados["cor"].append({"nome": nome_c.strip(), "cor_hex": hex_c.strip() or "#808080"})
            else:
                agrupados["cor"].append({"nome": nome_raw, "cor_hex": "#808080"})
        else:
            lista_cat = agrupados.setdefault(cat, [])
            if nome_raw not in lista_cat:
                lista_cat.append(nome_raw)

    return {"sucesso": True, "atributos": agrupados}


@app.post("/api/atributos")
def adicionar_atributo(payload: AtributoInput, _user: dict = Depends(verificar_token)):
    """Cadastra um novo atributo dinâmico (marca, corte, tecido ou cor)."""
    cat = (payload.categoria or payload.tipo or "").strip().lower()
    val = (payload.valor or payload.nome or "").strip()
    if not cat or not val:
        raise HTTPException(status_code=400, detail="Categoria e valor do atributo são obrigatórios.")

    valor_banco = f"{val}|{payload.cor_hex.strip()}" if cat == "cor" and payload.cor_hex else val

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM atributos WHERE LOWER(categoria) = LOWER(?) AND LOWER(nome) = LOWER(?) LIMIT 1",
            (cat, valor_banco),
        )
        existente = cur.fetchone()
        if not existente:
            cur.execute(
                "INSERT INTO atributos (categoria, nome) VALUES (?, ?)",
                (cat, valor_banco),
            )
            conn.commit()

    return {"sucesso": True, "mensagem": f"Atributo '{val}' registrado em '{cat}'."}


@app.post("/api/produtos")
@app.post("/api/estoque/produto")
def criar_produto(
    payload: ProdutoInput,
    _user: dict = Depends(verificar_token),
):
    """Cadastra um novo produto Pai e suas variações gerando código de barras KNB."""
    modelo = (payload.modelo_nome or "").strip()
    if not modelo:
        raise HTTPException(status_code=400, detail="O nome/modelo do produto é obrigatório.")

    custo_pai = round(float(payload.preco_custo or 0.0), 2)
    venda_pai = round(float(payload.preco_venda or 0.0), 2)
    cor_pai = (payload.cor or "").strip()
    hex_pai = (payload.cor_hex or "#3b82f6").strip()

    if not cor_pai and payload.cores:
        if isinstance(payload.cores, str):
            cor_pai = payload.cores.split(",")[0].split("|")[0].strip()
        elif isinstance(payload.cores, list) and payload.cores:
            primeiro_c = payload.cores[0]
            if isinstance(primeiro_c, dict):
                cor_pai = str(primeiro_c.get("nome") or primeiro_c.get("cor") or "").strip()
                hex_pai = str(primeiro_c.get("cor_hex") or hex_pai).strip()
            else:
                cor_pai = str(primeiro_c).strip()

    variacoes_lista: list[VariacaoInput] = list(payload.variacoes or [])
    if not variacoes_lista and payload.grade:
        if isinstance(payload.grade, dict):
            for tam_k, qtd_v in payload.grade.items():
                if int(qtd_v or 0) > 0:
                    variacoes_lista.append(
                        VariacaoInput(
                            tamanho=str(tam_k),
                            cor=cor_pai or "Padrão",
                            cor_hex=hex_pai,
                            estoque=int(qtd_v),
                            preco_custo=custo_pai,
                            preco_venda=venda_pai,
                        )
                    )
        elif isinstance(payload.grade, list):
            for g_item in payload.grade:
                if isinstance(g_item, dict):
                    qtd_g = int(g_item.get("quantidade") or g_item.get("estoque") or 0)
                    if qtd_g > 0:
                        variacoes_lista.append(
                            VariacaoInput(
                                tamanho=str(g_item.get("tamanho") or "U"),
                                cor=cor_pai or "Padrão",
                                cor_hex=hex_pai,
                                estoque=qtd_g,
                                preco_custo=custo_pai,
                                preco_venda=venda_pai,
                            )
                        )

    if not variacoes_lista:
        raise HTTPException(status_code=400, detail="Adicione pelo menos uma variação (tamanho).")

    cores_tags = _montar_cores_tags(payload.cores_tags or "", variacoes_lista)

    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
            marca_limpa = (payload.marca or "").strip()
            tecido_limpo = (payload.tecido or "").strip()
            corte_limpo = (payload.corte or "").strip()

            cur.execute(
                """
                INSERT INTO produtos (modelo_nome, marca, tecido, corte, cores_tags)
                VALUES (?, ?, ?, ?, ?)
                """,
                (modelo, marca_limpa, tecido_limpo, corte_limpo, cores_tags),
            )
            produto_id = cur.lastrowid

            _garantir_atributo(cur, "marca", marca_limpa)
            _garantir_atributo(cur, "tecido", tecido_limpo)
            _garantir_atributo(cur, "corte", corte_limpo)

            total_pecas = 0
            codigos_gerados = []

            for v in variacoes_lista:
                tam = (v.tamanho or "U").strip()
                if not tam.lower().endswith("ml"):
                    tam = tam.upper()
                cor = (v.cor or cor_pai or "").strip()
                cor_hex = (v.cor_hex or hex_pai or "#3b82f6").strip()
                cod = (v.codigo_barras or "").strip()
                qtd_est = max(0, int(v.estoque or 0))
                p_custo = round(float(v.preco_custo if v.preco_custo is not None else custo_pai), 2)
                p_venda = round(float(v.preco_venda if v.preco_venda is not None else venda_pai), 2)

                cur.execute(
                    """
                    INSERT INTO produto_variacoes (
                        produto_id, tamanho, cor, cor_hex, codigo_barras,
                        estoque, preco_custo, preco_venda
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (produto_id, tam, cor, cor_hex, cod, qtd_est, p_custo, p_venda),
                )
                vid = cur.lastrowid
                if not cod:
                    cod = f"KNB{produto_id:05d}{vid:04d}"
                    cur.execute(
                        "UPDATE produto_variacoes SET codigo_barras = ? WHERE id = ?",
                        (cod, vid),
                    )
                total_pecas += qtd_est
                codigos_gerados.append(cod)

            conn.commit()
            return {
                "sucesso": True,
                "mensagem": f"Produto '{modelo}' cadastrado com sucesso!",
                "produto_id": produto_id,
                "total_pecas": total_pecas,
                "codigos_barras": codigos_gerados,
            }
        except Exception as exc:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Erro ao cadastrar produto: {exc}") from exc


@app.put("/api/produtos/{produto_id}")
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
    custo_pai = round(float(payload.preco_custo or 0.0), 2)
    venda_pai = round(float(payload.preco_venda or 0.0), 2)

    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
            cur.execute("SELECT id FROM produtos WHERE id = ?", (produto_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Produto não encontrado.")

            marca_limpa = (payload.marca or "").strip()
            tecido_limpo = (payload.tecido or "").strip()
            corte_limpo = (payload.corte or "").strip()

            cur.execute(
                """
                UPDATE produtos
                SET modelo_nome = ?, marca = ?, tecido = ?, corte = ?, cores_tags = ?
                WHERE id = ?
                """,
                (modelo, marca_limpa, tecido_limpo, corte_limpo, cores_tags, produto_id),
            )

            _garantir_atributo(cur, "marca", marca_limpa)
            _garantir_atributo(cur, "tecido", tecido_limpo)
            _garantir_atributo(cur, "corte", corte_limpo)

            cur.execute(
                "SELECT id FROM produto_variacoes WHERE produto_id = ?",
                (produto_id,),
            )
            ids_existentes = {r["id"] for r in cur.fetchall()}
            ids_recebidos = set()

            for v in payload.variacoes:
                tam = (v.tamanho or "U").strip()
                if not tam.lower().endswith("ml"):
                    tam = tam.upper()
                cor = (v.cor or "").strip()
                cor_hex = (v.cor_hex or "#3b82f6").strip()
                cod = (v.codigo_barras or "").strip()
                qtd_est = max(0, int(v.estoque or 0))
                p_custo = round(float(v.preco_custo if v.preco_custo is not None else custo_pai), 2)
                p_venda = round(float(v.preco_venda if v.preco_venda is not None else venda_pai), 2)

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
                        (tam, cor, cor_hex, cod, qtd_est, p_custo, p_venda, v.id, produto_id),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO produto_variacoes (
                            produto_id, tamanho, cor, cor_hex, codigo_barras,
                            estoque, preco_custo, preco_venda
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (produto_id, tam, cor, cor_hex, cod, qtd_est, p_custo, p_venda),
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


@app.delete("/api/produtos/{produto_id}")
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
# 3. QR CODE OFFLINE (SVG VETORIAL DE ALTO CONTRASTE + BUSCA DE CÓDIGO KNB)
# ---------------------------------------------------------------------------
def _gerar_svg_qrcode_alto_contraste(conteudo: str, border: int = 2) -> bytes:
    """Gera QR Code vetorial SVG 100% offline (#000000 sobre #ffffff) nítido para impressão."""
    import qrcode

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=border,
    )
    qr.add_data(conteudo)
    qr.make(fit=True)
    matriz = qr.get_matrix()
    n = len(matriz)

    comandos = []
    for y, linha in enumerate(matriz):
        for x, escuro in enumerate(linha):
            if escuro:
                comandos.append(f"M{x},{y}h1v1h-1z")

    caminho_d = "".join(comandos)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" '
        f'width="256" height="256" shape-rendering="crispEdges">'
        f'<rect width="{n}" height="{n}" fill="#ffffff"/>'
        f'<path d="{caminho_d}" fill="#000000"/>'
        f"</svg>"
    )
    return svg.encode("utf-8")


@app.get("/api/qrcode/svg/{codigo}")
def gerar_qrcode_svg_etiqueta(codigo: str):
    """Retorna imagem SVG vetorial de alto contraste para etiquetas QR Code."""
    codigo_limpo = (codigo or "").strip()
    if not codigo_limpo:
        raise HTTPException(status_code=400, detail="Código vazio.")
    svg_bytes = _gerar_svg_qrcode_alto_contraste(codigo_limpo, border=1)
    return Response(
        content=svg_bytes,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/api/qrcode/{codigo}")
def buscar_qrcode(
    codigo: str,
    _user: dict = Depends(verificar_token),
):
    """Busca peça por codigo_barras (case-insensitive) retornando dados para Mobile e Desktop."""
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
        "encontrado": True,
        "produto": item_dict,
        "item": item_dict,
        **item_dict,
    }


# ---------------------------------------------------------------------------
# 4. VENDAS (PDV), HISTÓRICO DE HOJE, RECENTES E ESTORNO DE BALCÃO
# ---------------------------------------------------------------------------
@app.get("/api/vendas/hoje")
def listar_vendas_hoje(_user: dict = Depends(verificar_token)):
    """Retorna as vendas registradas na data de hoje e resumo financeiro."""
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
            LIMIT 150
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

    fat_round = round(faturamento_hoje, 2)
    return {
        "sucesso": True,
        "data": hoje_prefixo,
        "faturamento_hoje": fat_round,
        "total_vendido": fat_round,
        "pecas_hoje": pecas_hoje,
        "pecas_vendidas": pecas_hoje,
        "vendas": vendas,
    }


@app.post("/api/vendas")
def registrar_venda(
    payload: VendaRequest,
    _user: dict = Depends(verificar_token),
):
    """Registra venda em transação atômica: valida e baixa estoque, grava em vendas
    e, se FIADO, lança DEBITO em conta_fiado respeitando o limite do cliente.
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

            itens_agrupados: dict[str, dict] = {}
            for item in payload.itens:
                cod = (item.codigo_barras or "").strip()
                vid_in = item.variacao_id
                qtd = int(item.quantidade or 0)
                if qtd <= 0 or (not cod and not vid_in):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Quantidade ou identificador inválido para o item '{cod or vid_in}'.",
                    )
                chave = f"cod:{cod.lower()}" if cod else f"vid:{int(vid_in)}"
                if chave not in itens_agrupados:
                    itens_agrupados[chave] = {
                        "codigo_barras": cod.lower(),
                        "variacao_id": int(vid_in) if vid_in else None,
                        "quantidade": 0,
                    }
                itens_agrupados[chave]["quantidade"] += qtd

            for info_agrup in itens_agrupados.values():
                cod_lower = info_agrup["codigo_barras"]
                vid_alvo = info_agrup["variacao_id"]
                qtd = info_agrup["quantidade"]

                if cod_lower:
                    cur.execute(
                        """
                        SELECT
                            pv.id, pv.produto_id, pv.tamanho, pv.cor, pv.codigo_barras,
                            pv.estoque, pv.preco_custo, pv.preco_venda,
                            p.modelo_nome, p.marca, p.cores_tags
                        FROM produto_variacoes pv
                        INNER JOIN produtos p ON p.id = pv.produto_id
                        WHERE LOWER(pv.codigo_barras) = ?
                        LIMIT 1
                        """,
                        (cod_lower,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT
                            pv.id, pv.produto_id, pv.tamanho, pv.cor, pv.codigo_barras,
                            pv.estoque, pv.preco_custo, pv.preco_venda,
                            p.modelo_nome, p.marca, p.cores_tags
                        FROM produto_variacoes pv
                        INNER JOIN produtos p ON p.id = pv.produto_id
                        WHERE pv.id = ?
                        LIMIT 1
                        """,
                        (vid_alvo,),
                    )

                v_row = cur.fetchone()
                if not v_row and vid_alvo:
                    cur.execute(
                        """
                        SELECT
                            pv.id, pv.produto_id, pv.tamanho, pv.cor, pv.codigo_barras,
                            pv.estoque, pv.preco_custo, pv.preco_venda,
                            p.modelo_nome, p.marca, p.cores_tags
                        FROM produto_variacoes pv
                        INNER JOIN produtos p ON p.id = pv.produto_id
                        WHERE pv.id = ?
                        LIMIT 1
                        """,
                        (vid_alvo,),
                    )
                    v_row = cur.fetchone()

                if not v_row:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Produto '{cod_lower or vid_alvo}' não encontrado no estoque.",
                    )

                estoque_atual = int(v_row["estoque"] or 0)
                if estoque_atual < qtd:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Estoque insuficiente para '{v_row['modelo_nome']}' "
                            f"({v_row['tamanho']}). Disponível: {estoque_atual}, solicitado: {qtd}."
                        ),
                    )

                preco_venda = float(v_row["preco_venda"] or 0.0)
                subtotal_item = preco_venda * qtd
                subtotal_geral += subtotal_item

                cor_item = v_row["cor"] or ""
                if not cor_item and v_row["cores_tags"]:
                    cor_item = ", ".join(
                        [t.split("|")[0] for t in v_row["cores_tags"].split(",") if "|" in t]
                    )

                itens_processados.append(
                    {
                        "variacao_id": v_row["id"],
                        "codigo_barras": v_row["codigo_barras"] or "",
                        "modelo_nome": v_row["modelo_nome"] or "",
                        "marca": v_row["marca"] or "",
                        "cor": cor_item,
                        "tamanho": v_row["tamanho"] or "",
                        "quantidade": qtd,
                        "preco_custo": float(v_row["preco_custo"] or 0.0),
                        "preco_unitario": preco_venda,
                        "subtotal": subtotal_item,
                    }
                )

            desc_raw = payload.desconto if payload.desconto is not None else payload.desconto_total
            desconto_aplicado = min(max(0.0, float(desc_raw or 0.0)), subtotal_geral)
            fator = (
                (subtotal_geral - desconto_aplicado) / subtotal_geral
                if subtotal_geral > 0
                else 1.0
            )

            data_venda_str = datetime.now().strftime("%d/%m/%Y %H:%M")
            valor_total_liquido = 0.0
            resumo_pecas = []
            itens_recibo = []
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
                itens_recibo.append(
                    {
                        "modelo_nome": item["modelo_nome"],
                        "marca": item["marca"],
                        "tamanho": item["tamanho"],
                        "cor": item["cor"],
                        "quantidade": item["quantidade"],
                        "valor_unitario": valor_unitario_final,
                        "valor_total": valor_item_final,
                    }
                )

            nome_cliente_fiado = ""
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
                nome_cliente_fiado = cliente_row["nome"] or ""

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
                limite_cli = round(float(cliente_row["limite_credito"] or 0.0), 2)
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

                if payload.data_vencimento_lote and payload.data_vencimento_lote.strip():
                    raw_venc = payload.data_vencimento_lote.strip()
                    vencimento_iso = raw_venc
                    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                        try:
                            dt_parsed = datetime.strptime(raw_venc[:10], fmt)
                            vencimento_iso = dt_parsed.strftime("%Y-%m-%d %H:%M:%S.%f")
                            break
                        except ValueError:
                            pass
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
                "data_hora": data_venda_str,
                "subtotal": round(subtotal_geral, 2),
                "desconto_total": round(desconto_aplicado, 2),
                "valor_total": total_final,
                "total_cobrado": total_final,
                "forma_pagamento": forma_pgto,
                "cliente_id": payload.cliente_id,
                "cliente_nome": nome_cliente_fiado,
                "itens_resumo": itens_recibo,
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


def _agrupar_linhas_venda(rows: list) -> list[dict]:
    """Agrupa linhas consecutivas de 'vendas' do mesmo checkout (mesma data/hora, forma_pgto e IDs contíguos)."""
    grupos: list[dict] = []
    for r in rows:  # rows ordenadas por id DESC
        dv = r["data_venda"] or ""
        fp = r["forma_pagamento"] or "DINHEIRO"
        if (
            grupos
            and grupos[-1]["data_venda"] == dv
            and grupos[-1]["forma_pagamento"] == fp
            and abs(grupos[-1]["linhas"][-1]["id"] - r["id"]) == 1
        ):
            grupos[-1]["linhas"].append(r)
        else:
            grupos.append({"data_venda": dv, "forma_pagamento": fp, "linhas": [r]})
    for g in grupos:
        g["linhas"].sort(key=lambda x: x["id"])
    return grupos


def _localizar_debito_fiado_venda(cur: sqlite3.Cursor, grupo: dict):
    linhas = grupo["linhas"]
    descricao_esperada = "Compra: " + ", ".join(
        f"{int(l['quantidade'] or 0)}x {l['modelo_nome']} ({l['tamanho']})" for l in linhas
    )
    total_esperado = round(sum(float(l["valor_total"] or 0.0) for l in linhas), 2)
    prefixo_iso = ""
    try:
        prefixo_iso = datetime.strptime(grupo["data_venda"], "%d/%m/%Y %H:%M").strftime("%Y-%m-%d %H:%M")
    except ValueError:
        prefixo_iso = ""

    cur.execute(
        """
        SELECT cf.id, cf.cliente_id, cf.valor, cf.descricao, c.nome AS cliente_nome
        FROM conta_fiado cf
        LEFT JOIN clientes c ON c.id = cf.cliente_id
        WHERE cf.tipo_movimentacao = 'DEBITO'
          AND cf.descricao = ?
          AND (? = '' OR cf.data_movimentacao LIKE ?)
        ORDER BY cf.id DESC
        """,
        (descricao_esperada, prefixo_iso, f"{prefixo_iso}%"),
    )
    for row in cur.fetchall():
        if abs(float(row["valor"] or 0.0) - total_esperado) <= 0.05:
            return row

    # Fallback: busca pelo texto sem filtro de minuto exato
    cur.execute(
        """
        SELECT cf.id, cf.cliente_id, cf.valor, cf.descricao, c.nome AS cliente_nome
        FROM conta_fiado cf
        LEFT JOIN clientes c ON c.id = cf.cliente_id
        WHERE cf.tipo_movimentacao = 'DEBITO' AND cf.descricao = ?
        ORDER BY cf.id DESC
        LIMIT 5
        """,
        (descricao_esperada,),
    )
    for row in cur.fetchall():
        if abs(float(row["valor"] or 0.0) - total_esperado) <= 0.05:
            return row
    return None


@app.get("/api/vendas/recentes")
def listar_vendas_recentes(
    limite: int = Query(default=15, ge=1, le=50),
    _user: dict = Depends(verificar_token),
):
    """Retorna as últimas vendas registradas para consulta rápida e estorno no balcão."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                id, variacao_id, modelo_nome, marca, cor, tamanho,
                quantidade, valor_unitario, valor_total, preco_custo,
                data_venda, forma_pagamento
            FROM vendas
            ORDER BY id DESC
            LIMIT ?
            """,
            (limite * 25,),
        )
        grupos = _agrupar_linhas_venda(cur.fetchall())[:limite]

        vendas_out = []
        for g in grupos:
            cliente_nome = ""
            if g["forma_pagamento"] == "FIADO":
                deb = _localizar_debito_fiado_venda(cur, g)
                if deb:
                    cliente_nome = deb["cliente_nome"] or ""

            itens_lista = [
                {
                    "id": l["id"],
                    "variacao_id": l["variacao_id"],
                    "quantidade": int(l["quantidade"] or 0),
                    "modelo_nome": l["modelo_nome"] or "",
                    "marca": l["marca"] or "",
                    "cor": l["cor"] or "",
                    "tamanho": l["tamanho"] or "",
                    "valor_unitario": round(float(l["valor_unitario"] or 0.0), 2),
                    "valor_total": round(float(l["valor_total"] or 0.0), 2),
                }
                for l in g["linhas"]
            ]
            total_grupo = round(sum(it["valor_total"] for it in itens_lista), 2)
            pecas_grupo = sum(it["quantidade"] for it in itens_lista)
            resumo_str = ", ".join(
                f"{it['quantidade']}x {it['modelo_nome']} ({it['tamanho']})" for it in itens_lista
            )

            vendas_out.append(
                {
                    "id": g["linhas"][0]["id"],
                    "vendas_ids": [l["id"] for l in g["linhas"]],
                    "data_venda": g["data_venda"],
                    "valor_total": total_grupo,
                    "desconto_total": 0.0,
                    "pecas_total": pecas_grupo,
                    "forma_pagamento": g["forma_pagamento"],
                    "cliente_nome": cliente_nome,
                    "resumo_itens": resumo_str,
                    "itens": itens_lista,
                }
            )

    return {"sucesso": True, "vendas": vendas_out}


@app.post("/api/vendas/{venda_id}/estornar")
def estornar_venda(
    venda_id: int,
    _user: dict = Depends(verificar_token),
):
    """Estorna uma venda em transação segura: devolve estoque às variações,
    remove eventual débito no fiado e exclui o registro de vendas.
    """
    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
            cur.execute(
                """
                SELECT id, variacao_id, modelo_nome, marca, cor, tamanho,
                       quantidade, valor_total, data_venda, forma_pagamento
                FROM vendas
                WHERE id = ?
                """,
                (venda_id,),
            )
            alvo = cur.fetchone()
            if not alvo:
                raise HTTPException(status_code=404, detail=f"Venda #{venda_id} não encontrada.")

            cur.execute(
                """
                SELECT id, variacao_id, modelo_nome, marca, cor, tamanho,
                       quantidade, valor_total, data_venda, forma_pagamento
                FROM vendas
                WHERE data_venda IS ? AND forma_pagamento IS ?
                ORDER BY id ASC
                """,
                (alvo["data_venda"], alvo["forma_pagamento"]),
            )
            candidatas = cur.fetchall()

            # Isola o bloco contíguo de IDs que contém venda_id
            blocos: list[list] = []
            atual: list = []
            for r in candidatas:
                if atual and (r["id"] - atual[-1]["id"]) > 1:
                    blocos.append(atual)
                    atual = []
                atual.append(r)
            if atual:
                blocos.append(atual)

            linhas_estorno = next(
                (b for b in blocos if any(x["id"] == venda_id for x in b)),
                [alvo],
            )

            grupo = {
                "data_venda": alvo["data_venda"] or "",
                "forma_pagamento": alvo["forma_pagamento"] or "DINHEIRO",
                "linhas": linhas_estorno,
            }

            pecas_devolvidas = 0
            for l in linhas_estorno:
                qtd = max(0, int(l["quantidade"] or 0))
                vid = l["variacao_id"]
                devolveu = False
                if vid:
                    cur.execute(
                        "UPDATE produto_variacoes SET estoque = estoque + ? WHERE id = ?",
                        (qtd, vid),
                    )
                    devolveu = cur.rowcount > 0
                if not devolveu and l["modelo_nome"]:
                    cur.execute(
                        """
                        UPDATE produto_variacoes
                        SET estoque = estoque + ?
                        WHERE id = (
                            SELECT pv.id
                            FROM produto_variacoes pv
                            INNER JOIN produtos p ON p.id = pv.produto_id
                            WHERE LOWER(p.modelo_nome) = LOWER(?)
                              AND UPPER(pv.tamanho) = UPPER(?)
                            LIMIT 1
                        )
                        """,
                        (qtd, l["modelo_nome"], l["tamanho"] or "U"),
                    )
                pecas_devolvidas += qtd

            if grupo["forma_pagamento"] == "FIADO":
                deb = _localizar_debito_fiado_venda(cur, grupo)
                if deb:
                    cur.execute("DELETE FROM conta_fiado WHERE id = ?", (deb["id"],))

            ids_apagar = [l["id"] for l in linhas_estorno]
            placeholders = ",".join("?" for _ in ids_apagar)
            cur.execute(f"DELETE FROM vendas WHERE id IN ({placeholders})", ids_apagar)

            conn.commit()
            return {
                "ok": True,
                "sucesso": True,
                "venda_id": venda_id,
                "pecas_devolvidas": pecas_devolvidas,
                "mensagem": f"Venda #{venda_id} estornada e peças devolvidas ao estoque.",
            }
        except HTTPException:
            conn.rollback()
            raise
        except Exception as exc:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Erro ao estornar venda: {exc}") from exc


# ---------------------------------------------------------------------------
# 5. FIADO / CREDIÁRIO COMPLETO (/api/clientes E /api/fiado/*)
# ---------------------------------------------------------------------------
@app.get("/api/clientes")
@app.get("/api/fiado/clientes")
def listar_clientes_fiado(_user: dict = Depends(verificar_token)):
    """Lista todos os clientes com saldo_devedor calculado e últimos 10 lançamentos."""
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
                id, cliente_id, tipo_movimentacao, valor,
                data_movimentacao, data_vencimento_lote, descricao
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
        saldo = round(max(0.0, float(c["saldo_devedor"] or 0.0)), 2)
        disponivel = round(max(0.0, limite - saldo), 2)
        dia_pref = c["dia_preferencial_pagamento"] or 5

        resultado.append(
            {
                "id": cid,
                "nome": c["nome"],
                "telefone": c["telefone"] or "",
                "limite_credito": limite,
                "dia_preferencial_pagamento": dia_pref,
                "dia_vencimento": dia_pref,
                "saldo_devedor": saldo,
                "disponivel": disponivel,
                "historico": ultimos_lancamentos,
                "ultimos_lancamentos": ultimos_lancamentos,
                "lancamentos": ultimos_lancamentos,
            }
        )

    return {"sucesso": True, "clientes": resultado}


@app.post("/api/clientes")
@app.post("/api/fiado/clientes")
def cadastrar_cliente_fiado(
    payload: ClienteInput,
    _user: dict = Depends(verificar_token),
):
    """Cadastra um novo cliente na tabela clientes."""
    nome = (payload.nome or "").strip()
    if not nome:
        raise HTTPException(status_code=400, detail="O nome do cliente é obrigatório.")

    dia_pref = payload.dia_preferencial_pagamento or payload.dia_vencimento or 5
    dia_pref = max(1, min(31, int(dia_pref)))

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
                    round(float(payload.limite_credito if payload.limite_credito is not None else 500.0), 2),
                    dia_pref,
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


@app.put("/api/clientes/{cliente_id}")
@app.put("/api/fiado/clientes/{cliente_id}")
def atualizar_cliente_fiado(
    cliente_id: int,
    payload: ClienteUpdateInput,
    _user: dict = Depends(verificar_token),
):
    """Atualiza dados cadastrais e limite de crédito de um cliente."""
    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT id, nome, telefone, limite_credito, dia_preferencial_pagamento FROM clientes WHERE id = ?",
                (cliente_id,),
            )
            atual = cur.fetchone()
            if not atual:
                raise HTTPException(status_code=404, detail="Cliente não encontrado.")

            novo_nome = (payload.nome.strip() if payload.nome is not None else atual["nome"]).strip()
            if not novo_nome:
                raise HTTPException(status_code=400, detail="O nome do cliente não pode ser vazio.")

            cur.execute(
                "SELECT id FROM clientes WHERE LOWER(nome) = LOWER(?) AND id != ?",
                (novo_nome, cliente_id),
            )
            if cur.fetchone():
                raise HTTPException(
                    status_code=400, detail=f"Já existe outro cliente com o nome '{novo_nome}'."
                )

            novo_tel = payload.telefone.strip() if payload.telefone is not None else (atual["telefone"] or "")
            novo_lim = (
                round(float(payload.limite_credito), 2)
                if payload.limite_credito is not None
                else round(float(atual["limite_credito"] or 0.0), 2)
            )
            dia_in = payload.dia_preferencial_pagamento or payload.dia_vencimento
            novo_dia = (
                max(1, min(31, int(dia_in)))
                if dia_in is not None
                else int(atual["dia_preferencial_pagamento"] or 5)
            )

            cur.execute(
                """
                UPDATE clientes
                SET nome = ?, telefone = ?, limite_credito = ?, dia_preferencial_pagamento = ?
                WHERE id = ?
                """,
                (novo_nome, novo_tel, novo_lim, novo_dia, cliente_id),
            )
            conn.commit()
            return {
                "sucesso": True,
                "mensagem": f"Dados de '{novo_nome}' atualizados com sucesso!",
                "cliente_id": cliente_id,
            }
        except HTTPException:
            conn.rollback()
            raise
        except Exception as exc:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Erro ao atualizar cliente: {exc}") from exc


@app.delete("/api/clientes/{cliente_id}")
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
            if saldo > 0.01:
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


@app.get("/api/fiado/clientes/{cliente_id}/extrato")
def obter_extrato_cliente_fiado(
    cliente_id: int,
    _user: dict = Depends(verificar_token),
):
    """Retorna todo o histórico de movimentações (DEBITO e CREDITO) de um cliente."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, nome FROM clientes WHERE id = ?", (cliente_id,))
        cli = cur.fetchone()
        if not cli:
            raise HTTPException(status_code=404, detail="Cliente não encontrado.")

        cur.execute(
            """
            SELECT
                id, cliente_id, tipo_movimentacao, valor,
                data_movimentacao, data_vencimento_lote, descricao
            FROM conta_fiado
            WHERE cliente_id = ?
            ORDER BY data_movimentacao DESC, id DESC
            """,
            (cliente_id,),
        )
        rows = cur.fetchall()

    movimentacoes = [
        {
            "id": r["id"],
            "cliente_id": r["cliente_id"],
            "tipo_movimentacao": r["tipo_movimentacao"],
            "valor": round(float(r["valor"] or 0.0), 2),
            "data_movimentacao": r["data_movimentacao"] or "",
            "data_vencimento_lote": r["data_vencimento_lote"] or "",
            "descricao": r["descricao"] or "",
        }
        for r in rows
    ]
    return {"sucesso": True, "cliente_id": cliente_id, "movimentacoes": movimentacoes}


@app.get("/api/fiado/resumo")
def obter_resumo_fiado(_user: dict = Depends(verificar_token)):
    """Retorna os 4 KPIs da aba Fiado: total a receber, devedores, estourados e recebido 30d."""
    limite_30d_iso = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                c.id,
                c.limite_credito,
                COALESCE(SUM(CASE WHEN cf.tipo_movimentacao = 'DEBITO' THEN cf.valor ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN cf.tipo_movimentacao = 'CREDITO' THEN cf.valor ELSE 0 END), 0) AS saldo
            FROM clientes c
            LEFT JOIN conta_fiado cf ON cf.cliente_id = c.id
            GROUP BY c.id, c.limite_credito
            """
        )
        clientes_rows = cur.fetchall()

        cur.execute(
            """
            SELECT COALESCE(SUM(valor), 0) AS rec_30d
            FROM conta_fiado
            WHERE tipo_movimentacao = 'CREDITO'
              AND data_movimentacao >= ?
            """,
            (limite_30d_iso,),
        )
        recebido_30d = round(float(cur.fetchone()["rec_30d"] or 0.0), 2)

    total_clientes = len(clientes_rows)
    total_a_receber = 0.0
    clientes_com_divida = 0
    clientes_estourados = 0

    for r in clientes_rows:
        saldo = round(max(0.0, float(r["saldo"] or 0.0)), 2)
        limite = round(float(r["limite_credito"] or 0.0), 2)
        if saldo > 0.009:
            total_a_receber += saldo
            clientes_com_divida += 1
            if limite > 0 and saldo >= limite:
                clientes_estourados += 1

    return {
        "sucesso": True,
        "total_a_receber": round(total_a_receber, 2),
        "clientes_com_divida": clientes_com_divida,
        "total_clientes": total_clientes,
        "clientes_estourados": clientes_estourados,
        "recebido_30_dias": recebido_30d,
    }


@app.post("/api/fiado/debito")
def registrar_debito_avulso_fiado(
    payload: DebitoFiadoRequest,
    _user: dict = Depends(verificar_token),
):
    """Lança um débito manual/avulso na conta de um cliente."""
    if payload.valor <= 0:
        raise HTTPException(status_code=400, detail="O valor do débito deve ser maior que zero.")

    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
            cur.execute("SELECT id, nome FROM clientes WHERE id = ?", (payload.cliente_id,))
            cli = cur.fetchone()
            if not cli:
                raise HTTPException(status_code=404, detail="Cliente não encontrado.")

            agora_dt = datetime.now()
            agora_iso = agora_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
            venc_iso = (agora_dt + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S.%f")
            if payload.data_vencimento_lote and payload.data_vencimento_lote.strip():
                raw_v = payload.data_vencimento_lote.strip()
                venc_iso = raw_v
                for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
                    try:
                        venc_iso = datetime.strptime(raw_v[:10], fmt).strftime("%Y-%m-%d %H:%M:%S.%f")
                        break
                    except ValueError:
                        pass

            desc = (payload.descricao or "Débito avulso").strip()
            valor_efetivo = round(float(payload.valor), 2)
            cur.execute(
                """
                INSERT INTO conta_fiado (
                    cliente_id, tipo_movimentacao, valor,
                    data_movimentacao, data_vencimento_lote, descricao
                ) VALUES (?, 'DEBITO', ?, ?, ?, ?)
                """,
                (payload.cliente_id, valor_efetivo, agora_iso, venc_iso, desc),
            )
            lancamento_id = cur.lastrowid
            conn.commit()
            return {
                "sucesso": True,
                "mensagem": f"Débito de R$ {valor_efetivo:.2f} lançado para {cli['nome']}.",
                "lancamento_id": lancamento_id,
            }
        except HTTPException:
            conn.rollback()
            raise
        except Exception as exc:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Erro ao lançar débito: {exc}") from exc


@app.post("/api/fiado/pagar")
def pagar_fiado(
    payload: PagamentoFiadoRequest,
    _user: dict = Depends(verificar_token),
):
    """Registra pagamento/abatimento (CREDITO) na conta do cliente."""
    if payload.valor <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O valor do pagamento deve ser maior que zero.",
        )

    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
            cur.execute("SELECT id, nome FROM clientes WHERE id = ?", (payload.cliente_id,))
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
                (payload.cliente_id, valor_efetivo, agora_iso, descricao),
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
# 6. RESUMO FINANCEIRO (MOBILE) E DASHBOARD EXECUTIVO COMPLETO (DESKTOP)
# ---------------------------------------------------------------------------
def _parse_data_venda(data_str: str) -> Optional[datetime]:
    s = (data_str or "").strip()
    if not s:
        return None
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[: len(fmt) + 2].strip(), fmt)
        except ValueError:
            pass
    try:
        return datetime.strptime(s[:10], "%d/%m/%Y")
    except ValueError:
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d")
        except ValueError:
            return None


@app.get("/api/financeiro/resumo")
def obter_resumo_financeiro(_user: dict = Depends(verificar_token)):
    """Resumo rápido de faturamento/custo/lucro de Hoje e 7 dias para o App Mobile."""
    agora = datetime.now()
    hoje_inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    semana_inicio = hoje_inicio - timedelta(days=6)

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT quantidade, valor_total, preco_custo, data_venda, forma_pagamento
            FROM vendas
            """
        )
        rows = cur.fetchall()

    hoje = {"faturamento_bruto": 0.0, "custo_total": 0.0, "lucro_liquido": 0.0, "pecas_vendidas": 0}
    semana = {"faturamento_bruto": 0.0, "custo_total": 0.0, "lucro_liquido": 0.0, "pecas_vendidas": 0}
    pgto_hoje = {"DINHEIRO": 0.0, "PIX": 0.0, "CARTAO": 0.0, "FIADO": 0.0}

    for r in rows:
        dt = _parse_data_venda(r["data_venda"] or "")
        if not dt:
            continue
        vt = float(r["valor_total"] or 0.0)
        qtd = int(r["quantidade"] or 0)
        custo = float(r["preco_custo"] or 0.0) * qtd
        fp = (r["forma_pagamento"] or "DINHEIRO").strip().upper()

        if dt >= semana_inicio:
            semana["faturamento_bruto"] += vt
            semana["custo_total"] += custo
            semana["pecas_vendidas"] += qtd

        if dt >= hoje_inicio:
            hoje["faturamento_bruto"] += vt
            hoje["custo_total"] += custo
            hoje["pecas_vendidas"] += qtd
            pgto_hoje[fp] = pgto_hoje.get(fp, 0.0) + vt

    hoje["faturamento_bruto"] = round(hoje["faturamento_bruto"], 2)
    hoje["custo_total"] = round(hoje["custo_total"], 2)
    hoje["lucro_liquido"] = round(hoje["faturamento_bruto"] - hoje["custo_total"], 2)

    semana["faturamento_bruto"] = round(semana["faturamento_bruto"], 2)
    semana["custo_total"] = round(semana["custo_total"], 2)
    semana["lucro_liquido"] = round(semana["faturamento_bruto"] - semana["custo_total"], 2)

    for k in list(pgto_hoje.keys()):
        pgto_hoje[k] = round(pgto_hoje[k], 2)

    return {
        "sucesso": True,
        "hoje": hoje,
        "semana": semana,
        "por_pagamento_hoje": pgto_hoje,
    }


@app.get("/api/dashboard/completo")
def obter_dashboard_completo(
    periodo: str = Query(default="30d"),
    grupo: str = Query(default="todos"),
    _user: dict = Depends(verificar_token),
):
    """Retorna todos os indicadores, séries SVG, rankings, auditoria de margens e alertas do Dashboard."""
    agora = datetime.now()
    hoje_inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    per_key = (periodo or "30d").strip().lower()
    grp_key = (grupo or "todos").strip().lower()

    if per_key == "hoje":
        dt_inicio = hoje_inicio
    elif per_key == "7d":
        dt_inicio = hoje_inicio - timedelta(days=6)
    elif per_key == "mes":
        dt_inicio = hoje_inicio.replace(day=1)
    elif per_key == "tudo":
        dt_inicio = None
    else:
        dt_inicio = hoje_inicio - timedelta(days=29)

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

        cur.execute(
            """
            SELECT
                v.id, v.variacao_id, v.modelo_nome, v.marca, v.cor, v.tamanho,
                v.quantidade, v.valor_unitario, v.valor_total, v.preco_custo,
                v.data_venda, v.forma_pagamento,
                pv.produto_id AS pv_produto_id,
                pv.preco_custo AS pv_custo,
                p.corte AS prod_corte,
                p.tecido AS prod_tecido
            FROM vendas v
            LEFT JOIN produto_variacoes pv ON pv.id = v.variacao_id
            LEFT JOIN produtos p ON p.id = pv.produto_id
            ORDER BY v.id ASC
            """
        )
        vendas_rows = cur.fetchall()

        cur.execute(
            """
            SELECT
                c.id,
                COALESCE(SUM(CASE WHEN cf.tipo_movimentacao = 'DEBITO' THEN cf.valor ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN cf.tipo_movimentacao = 'CREDITO' THEN cf.valor ELSE 0 END), 0) AS saldo
            FROM clientes c
            LEFT JOIN conta_fiado cf ON cf.cliente_id = c.id
            GROUP BY c.id
            """
        )
        fiado_rua = sum(max(0.0, float(r["saldo"] or 0.0)) for r in cur.fetchall())

        if dt_inicio is not None:
            cur.execute(
                """
                SELECT COALESCE(SUM(valor), 0) AS abat
                FROM conta_fiado
                WHERE tipo_movimentacao = 'CREDITO' AND data_movimentacao >= ?
                """,
                (dt_inicio.strftime("%Y-%m-%d"),),
            )
        else:
            cur.execute(
                "SELECT COALESCE(SUM(valor), 0) AS abat FROM conta_fiado WHERE tipo_movimentacao = 'CREDITO'"
            )
        abatimentos_fiado = round(float(cur.fetchone()["abat"] or 0.0), 2)

    # 1. Estrutura de produtos e estoque
    vars_por_prod: dict[int, list] = {}
    prod_por_id: dict[int, dict] = {}
    for v in variacoes_rows:
        vars_por_prod.setdefault(v["produto_id"], []).append(v)

    estoque_por_grupo_map = {
        ch: {
            "chave": ch,
            "nome": info["nome"],
            "rotulo": info["rotulo"],
            "modelos": 0,
            "pecas": 0,
            "pct_pecas": 0.0,
            "custo_total": 0.0,
            "venda_potencial": 0.0,
        }
        for ch, info in GRUPOS_META.items()
    }

    estoque_pecas_filtrado = 0
    estoque_custo_filtrado = 0.0
    estoque_venda_filtrado = 0.0
    auditoria_margens = []
    criticas_cnt = 0
    moderadas_cnt = 0
    saudaveis_cnt = 0
    soma_markup = 0.0

    for p in produtos_rows:
        pid = p["id"]
        info_grp = _classificar_grupo_produto(p["modelo_nome"] or "")
        ch_grp = info_grp["chave"]
        vlist = vars_por_prod.get(pid, [])

        est_prod = sum(max(0, int(v["estoque"] or 0)) for v in vlist)
        custo_ref = max((float(v["preco_custo"] or 0.0) for v in vlist), default=0.0)
        venda_ref = max((float(v["preco_venda"] or 0.0) for v in vlist), default=0.0)
        custo_est_prod = sum(max(0, int(v["estoque"] or 0)) * float(v["preco_custo"] or 0.0) for v in vlist)
        venda_est_prod = sum(max(0, int(v["estoque"] or 0)) * float(v["preco_venda"] or 0.0) for v in vlist)

        prod_por_id[pid] = {
            "id": pid,
            "modelo_nome": p["modelo_nome"] or "",
            "marca": p["marca"] or "Sem Marca",
            "corte": p["corte"] or "",
            "tecido": p["tecido"] or "",
            "grupo": info_grp,
            "estoque_total": est_prod,
            "preco_custo": custo_ref,
            "preco_venda": venda_ref,
            "variacoes": vlist,
        }

        g_entry = estoque_por_grupo_map[ch_grp]
        g_entry["modelos"] += 1
        g_entry["pecas"] += est_prod
        g_entry["custo_total"] += custo_est_prod
        g_entry["venda_potencial"] += venda_est_prod

        if grp_key in ("todos", ch_grp):
            estoque_pecas_filtrado += est_prod
            estoque_custo_filtrado += custo_est_prod
            estoque_venda_filtrado += venda_est_prod

            lucro_un = round(venda_ref - custo_ref, 2)
            margem_pct = round((lucro_un / venda_ref) * 100, 1) if venda_ref > 0 else 0.0
            markup_pct = round((lucro_un / custo_ref) * 100, 1) if custo_ref > 0 else 0.0
            soma_markup += markup_pct

            if margem_pct < 25:
                faixa = "critica"
                criticas_cnt += 1
            elif margem_pct <= 45:
                faixa = "moderada"
                moderadas_cnt += 1
            else:
                faixa = "saudavel"
                saudaveis_cnt += 1

            auditoria_margens.append(
                {
                    "id": pid,
                    "modelo_nome": p["modelo_nome"] or "",
                    "marca": p["marca"] or "Sem Marca",
                    "corte": p["corte"] or "",
                    "tecido": p["tecido"] or "",
                    "grupo_chave": ch_grp,
                    "grupo_nome": info_grp["nome"],
                    "grupo_rotulo": info_grp["rotulo"],
                    "estoque_total": est_prod,
                    "preco_custo": round(custo_ref, 2),
                    "preco_venda": round(venda_ref, 2),
                    "lucro_unitario": lucro_un,
                    "margem_pct": margem_pct,
                    "markup_pct": markup_pct,
                    "faixa": faixa,
                }
            )

    total_pecas_geral = sum(g["pecas"] for g in estoque_por_grupo_map.values())
    estoque_por_grupo = []
    for g in estoque_por_grupo_map.values():
        g["custo_total"] = round(g["custo_total"], 2)
        g["venda_potencial"] = round(g["venda_potencial"], 2)
        g["pct_pecas"] = round((g["pecas"] / total_pecas_geral) * 100, 1) if total_pecas_geral > 0 else 0.0
        estoque_por_grupo.append(g)

    # 2. Processamento das vendas filtradas por período e grupo
    faturamento_bruto = 0.0
    cmv_total = 0.0
    pecas_vendidas = 0
    vendas_avista = 0.0
    chaves_checkout = set()
    qtd_vendida_por_prod: dict[int, int] = {}

    serie_por_dia: dict[str, dict] = {}
    pgto_stats = {
        "PIX": {"chave": "PIX", "forma": "PIX", "valor": 0.0, "qtd": 0},
        "CARTAO": {"chave": "CARTAO", "forma": "Cartão", "valor": 0.0, "qtd": 0},
        "DINHEIRO": {"chave": "DINHEIRO", "forma": "Dinheiro", "valor": 0.0, "qtd": 0},
        "FIADO": {"chave": "FIADO", "forma": "Fiado / Crediário", "valor": 0.0, "qtd": 0},
    }

    rk_marcas: dict[str, dict] = {}
    rk_tipos: dict[str, dict] = {}
    rk_cortes: dict[str, dict] = {}
    rk_tecidos: dict[str, dict] = {}

    def _acumular_rk(mapa: dict, chave_nome: str, qtd_v: int, fat_v: float, luc_v: float):
        limpo = (chave_nome or "").strip()
        if not limpo or limpo.upper() in ("N/A", "NA", "-", "—", "DESCONHECIDO"):
            return
        item = mapa.setdefault(limpo, {"nome": limpo, "qtd": 0, "faturamento": 0.0, "lucro": 0.0})
        item["qtd"] += qtd_v
        item["faturamento"] += fat_v
        item["lucro"] += luc_v

    for v in vendas_rows:
        dt = _parse_data_venda(v["data_venda"] or "")
        if dt_inicio is not None and (not dt or dt < dt_inicio):
            continue

        modelo_v = v["modelo_nome"] or ""
        info_grp_v = _classificar_grupo_produto(modelo_v)
        if grp_key != "todos" and info_grp_v["chave"] != grp_key:
            continue

        qtd = int(v["quantidade"] or 0)
        vt = float(v["valor_total"] or 0.0)
        custo_un = float(v["preco_custo"] or v["pv_custo"] or 0.0)
        custo_item = custo_un * qtd
        lucro_item = vt - custo_item
        fp = (v["forma_pagamento"] or "DINHEIRO").strip().upper()

        faturamento_bruto += vt
        cmv_total += custo_item
        pecas_vendidas += qtd
        if fp != "FIADO":
            vendas_avista += vt

        chave_ck = f"{v['data_venda']}|{fp}"
        chaves_checkout.add(chave_ck)

        if v["pv_produto_id"]:
            pid_v = int(v["pv_produto_id"])
            qtd_vendida_por_prod[pid_v] = qtd_vendida_por_prod.get(pid_v, 0) + qtd

        if dt:
            dia_iso = dt.strftime("%Y-%m-%d")
            dia_lbl = dt.strftime("%d/%m")
            s_dia = serie_por_dia.setdefault(
                dia_iso, {"data": dia_iso, "data_label": dia_lbl, "faturamento": 0.0, "lucro": 0.0, "qtd": 0}
            )
            s_dia["faturamento"] += vt
            s_dia["lucro"] += lucro_item
            s_dia["qtd"] += qtd

        p_stat = pgto_stats.setdefault(fp, {"chave": fp, "forma": fp.title(), "valor": 0.0, "qtd": 0})
        p_stat["valor"] += vt
        p_stat["qtd"] += 1

        _acumular_rk(rk_marcas, v["marca"] or "Sem Marca", qtd, vt, lucro_item)
        _acumular_rk(rk_tipos, modelo_v or "Peça", qtd, vt, lucro_item)
        _acumular_rk(rk_cortes, v["prod_corte"] or "", qtd, vt, lucro_item)
        _acumular_rk(rk_tecidos, v["prod_tecido"] or "", qtd, vt, lucro_item)

    # Preenche dias sem venda em períodos curtos (7d / 30d / mes) para gráfico contínuo
    if dt_inicio is not None and per_key in ("hoje", "7d", "30d", "mes"):
        cursor_dia = dt_inicio
        hoje_fim = hoje_inicio
        while cursor_dia <= hoje_fim:
            d_iso = cursor_dia.strftime("%Y-%m-%d")
            serie_por_dia.setdefault(
                d_iso,
                {
                    "data": d_iso,
                    "data_label": cursor_dia.strftime("%d/%m"),
                    "faturamento": 0.0,
                    "lucro": 0.0,
                    "qtd": 0,
                },
            )
            cursor_dia += timedelta(days=1)

    serie_temporal = [
        {
            "data": s["data"],
            "data_label": s["data_label"],
            "faturamento": round(s["faturamento"], 2),
            "lucro": round(s["lucro"], 2),
            "qtd": s["qtd"],
        }
        for s in sorted(serie_por_dia.values(), key=lambda x: x["data"])
    ]

    por_pagamento = []
    for p in pgto_stats.values():
        val_p = round(p["valor"], 2)
        pct_p = round((val_p / faturamento_bruto) * 100, 1) if faturamento_bruto > 0 else 0.0
        por_pagamento.append(
            {
                "chave": p["chave"],
                "forma": p["forma"],
                "valor": val_p,
                "qtd": p["qtd"],
                "pct": pct_p,
            }
        )
    por_pagamento.sort(key=lambda x: x["valor"], reverse=True)

    def _finalizar_rk(mapa: dict) -> list[dict]:
        saida = []
        for it in mapa.values():
            fat = round(it["faturamento"], 2)
            luc = round(it["lucro"], 2)
            mg = round((luc / fat) * 100, 1) if fat > 0 else 0.0
            saida.append(
                {
                    "nome": it["nome"],
                    "qtd": it["qtd"],
                    "faturamento": fat,
                    "lucro": luc,
                    "margem_pct": mg,
                }
            )
        saida.sort(key=lambda x: x["faturamento"], reverse=True)
        return saida[:15]

    # 3. Alertas de Reposição (<= 2 un.) e Capital Parado (0 vendas no período)
    reposicao_lista = []
    encalhados_lista = []
    for pid, pinfo in prod_por_id.items():
        if grp_key != "todos" and pinfo["grupo"]["chave"] != grp_key:
            continue
        est_t = pinfo["estoque_total"]
        qtd_vend = qtd_vendida_por_prod.get(pid, 0)
        resumo_tams = ", ".join(
            f"{v['tamanho']}:{int(v['estoque'] or 0)}" for v in pinfo["variacoes"]
        ) or "Sem grade"

        if est_t <= 2:
            reposicao_lista.append(
                {
                    "id": pid,
                    "modelo_nome": pinfo["modelo_nome"],
                    "marca": pinfo["marca"],
                    "estoque_total": est_t,
                    "tamanhos_resumo": resumo_tams,
                    "qtd_vendida_periodo": qtd_vend,
                }
            )
        if est_t > 0 and qtd_vend == 0:
            cap_parado = round(
                sum(max(0, int(v["estoque"] or 0)) * float(v["preco_custo"] or 0.0) for v in pinfo["variacoes"]),
                2,
            )
            encalhados_lista.append(
                {
                    "id": pid,
                    "modelo_nome": pinfo["modelo_nome"],
                    "marca": pinfo["marca"],
                    "estoque_total": est_t,
                    "preco_custo": round(pinfo["preco_custo"], 2),
                    "preco_venda": round(pinfo["preco_venda"], 2),
                    "capital_parado": cap_parado,
                    "sugestao_promo_15": round(pinfo["preco_venda"] * 0.85, 2),
                }
            )

    reposicao_lista.sort(key=lambda x: (x["estoque_total"], -x["qtd_vendida_periodo"]))
    encalhados_lista.sort(key=lambda x: x["capital_parado"], reverse=True)

    qtd_vendas_total = len(chaves_checkout)
    lucro_liquido = round(faturamento_bruto - cmv_total, 2)
    margem_media = round((lucro_liquido / faturamento_bruto) * 100, 1) if faturamento_bruto > 0 else 0.0
    ticket_medio = round(faturamento_bruto / qtd_vendas_total, 2) if qtd_vendas_total > 0 else 0.0
    caixa_real = round(vendas_avista + (abatimentos_fiado if grp_key == "todos" else 0.0), 2)
    total_modelos_audit = len(auditoria_margens)

    return {
        "sucesso": True,
        "periodo": per_key,
        "grupo": grp_key,
        "kpis": {
            "faturamento_bruto": round(faturamento_bruto, 2),
            "qtd_vendas": qtd_vendas_total,
            "pecas_vendidas": pecas_vendidas,
            "caixa_real_recebido": caixa_real,
            "vendas_avista_periodo": round(vendas_avista, 2),
            "abatimentos_fiado_periodo": abatimentos_fiado if grp_key == "todos" else 0.0,
            "lucro_liquido": lucro_liquido,
            "margem_media_pct": margem_media,
            "ticket_medio": ticket_medio,
            "custo_mercadoria_vendida": round(cmv_total, 2),
            "estoque_venda_potencial": round(estoque_venda_filtrado, 2),
            "estoque_custo_total": round(estoque_custo_filtrado, 2),
            "estoque_pecas": estoque_pecas_filtrado,
            "fiado_a_receber": round(fiado_rua, 2),
        },
        "serie_temporal": serie_temporal,
        "por_pagamento": por_pagamento,
        "estoque_por_grupo": estoque_por_grupo,
        "ranking_marcas": _finalizar_rk(rk_marcas),
        "ranking_tipos": _finalizar_rk(rk_tipos),
        "ranking_cortes": _finalizar_rk(rk_cortes),
        "ranking_tecidos": _finalizar_rk(rk_tecidos),
        "resumo_margens": {
            "total_modelos": total_modelos_audit,
            "markup_medio_pct": round(soma_markup / total_modelos_audit, 1) if total_modelos_audit > 0 else 0.0,
            "criticas": criticas_cnt,
            "moderadas": moderadas_cnt,
            "saudaveis": saudaveis_cnt,
        },
        "auditoria_margens": auditoria_margens,
        "alertas": {
            "reposicao_estoque_baixo": reposicao_lista,
            "encalhados_sem_giro": encalhados_lista,
        },
    }


# ---------------------------------------------------------------------------
# 7. CONTROLE DO SISTEMA, PORTEIRO INTELIGENTE (CLOUDFLARE + GITHUB PAGES),
#    CONEXÃO MOBILE ON/OFF, BACKUP E DESLIGAMENTO SEGURO
# ---------------------------------------------------------------------------
import re
import shutil
import subprocess
import urllib.request

DOCS_DIR = os.path.join(BASE_DIR, "docs")
TUNNEL_STATUS_PATH = os.path.join(DOCS_DIR, "tunnel_status.json")
URL_PORTEIRO_FIXO = "https://lincolln.github.io/projeto-dani/"
CLOUDFLARED_DOWNLOAD_URL = (
    "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
)
_REGEX_TRYCLOUDFLARE = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
_LOCK_TUNEL = threading.Lock()

ESTADO_SERVIDOR = {
    "url_cloudflare": "",
    "processo_tunel": None,
    "iniciando_tunel": False,
    "atualizado_em": None,
}


class CloudflareUrlInput(BaseModel):
    url: str = ""


class IniciarTunelInput(BaseModel):
    reiniciar: bool = False


def _detectar_ip_rede() -> str:
    """Detecta o IP local da máquina na rede Wi-Fi/LAN (ex: 192.168.x.x) com fallback seguro."""
    for destino in (("8.8.8.8", 80), ("192.168.1.1", 80), ("10.0.0.1", 80)):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.settimeout(0.8)
            sock.connect(destino)
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
                return ip
        except Exception:
            pass
        finally:
            sock.close()

    try:
        _, _, ips_host = socket.gethostbyname_ex(socket.gethostname())
        for ip_cand in ips_host:
            if ip_cand.startswith(("192.168.", "10.", "172.")):
                return ip_cand
        for ip_cand in ips_host:
            if ip_cand and not ip_cand.startswith("127.") and not ip_cand.startswith("169.254."):
                return ip_cand
    except Exception:
        pass

    return "127.0.0.1"


def _localizar_ou_baixar_cloudflared() -> Optional[str]:
    """Localiza cloudflared na pasta do projeto ou no PATH; se ausente, baixa o binário oficial."""
    candidatos = [
        os.path.join(BASE_DIR, "cloudflared.exe"),
        os.path.join(BASE_DIR, "cloudflared"),
        shutil.which("cloudflared"),
        shutil.which("cloudflared.exe"),
        os.path.expandvars(r"%ProgramFiles%\cloudflared\cloudflared.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\cloudflared\cloudflared.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\cloudflared.exe"),
    ]
    for caminho in candidatos:
        if caminho and os.path.isfile(caminho):
            return caminho

    destino_local = os.path.join(BASE_DIR, "cloudflared.exe")
    try:
        urllib.request.urlretrieve(CLOUDFLARED_DOWNLOAD_URL, destino_local)
        if os.path.isfile(destino_local) and os.path.getsize(destino_local) > 1_000_000:
            return destino_local
    except Exception:
        pass

    return None


def sincronizar_porteiro_github() -> None:
    """Faz commit e push silencioso de docs/tunnel_status.json em background sem travar o servidor."""
    def _worker():
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            subprocess.run(
                ["git", "add", "docs/tunnel_status.json"],
                cwd=BASE_DIR,
                capture_output=True,
                timeout=15,
                creationflags=flags,
            )
            res_commit = subprocess.run(
                ["git", "commit", "-m", "chore: update active tunnel url"],
                cwd=BASE_DIR,
                capture_output=True,
                timeout=15,
                creationflags=flags,
            )
            if res_commit.returncode == 0:
                subprocess.run(
                    ["git", "push"],
                    cwd=BASE_DIR,
                    capture_output=True,
                    timeout=25,
                    creationflags=flags,
                )
        except Exception:
            pass

    threading.Thread(target=_worker, daemon=True).start()


def _salvar_tunnel_status_json(url_ativa: str) -> dict:
    """Grava docs/tunnel_status.json e dispara sincronização assíncrona com o GitHub Pages."""
    os.makedirs(DOCS_DIR, exist_ok=True)
    ip_apenas = _detectar_ip_rede()
    ip_local_http = f"http://{ip_apenas}:{PORTA_SERVIDOR}"
    agora_iso = datetime.now().isoformat(timespec="seconds")

    url_limpa = (url_ativa or "").strip().rstrip("/")
    ESTADO_SERVIDOR["url_cloudflare"] = url_limpa
    ESTADO_SERVIDOR["atualizado_em"] = agora_iso

    payload = {
        "url_ativa": url_limpa,
        "ip_local": ip_local_http,
        "atualizado_em": agora_iso,
    }
    try:
        with open(TUNNEL_STATUS_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    if url_limpa:
        sincronizar_porteiro_github()

    return payload


def _ler_tunel_existente_log_externo() -> str:
    """Verifica se o iniciar_mobile.bat já abriu um túnel gravado em %TEMP%\\kanemberg_tunnel.log."""
    log_temp = os.path.join(os.getenv("TEMP", ""), "kanemberg_tunnel.log")
    if os.path.isfile(log_temp):
        try:
            # Só considera log recente (modificado nas últimas 12 horas)
            if (datetime.now().timestamp() - os.path.getmtime(log_temp)) < 43200:
                with open(log_temp, "r", encoding="utf-8", errors="ignore") as f:
                    conteudo = f.read()
                m = _REGEX_TRYCLOUDFLARE.search(conteudo)
                if m:
                    return m.group(0).rstrip("/")
        except Exception:
            pass
    return ""


def iniciar_ou_obter_tunel_cloudflare(forcar_reinicio: bool = False, aguardar_segundos: float = 14.0) -> str:
    """Inicia ou reaproveita o túnel Cloudflare Quick Tunnel e captura a URL https://*.trycloudflare.com."""
    with _LOCK_TUNEL:
        proc_atual = ESTADO_SERVIDOR.get("processo_tunel")
        url_atual = ESTADO_SERVIDOR.get("url_cloudflare") or ""

        if not forcar_reinicio:
            if url_atual and proc_atual is not None and proc_atual.poll() is None:
                return url_atual
            url_ext = _ler_tunel_existente_log_externo()
            if url_ext and not url_atual:
                _salvar_tunnel_status_json(url_ext)
                return url_ext

        # Encerra processo anterior se existir
        if proc_atual is not None:
            try:
                proc_atual.terminate()
                proc_atual.wait(timeout=3)
            except Exception:
                try:
                    proc_atual.kill()
                except Exception:
                    pass
            ESTADO_SERVIDOR["processo_tunel"] = None

        ESTADO_SERVIDOR["url_cloudflare"] = ""
        ESTADO_SERVIDOR["iniciando_tunel"] = True

        bin_cf = _localizar_ou_baixar_cloudflared()
        if not bin_cf:
            ESTADO_SERVIDOR["iniciando_tunel"] = False
            return ""

        evento_url = threading.Event()
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        try:
            proc = subprocess.Popen(
                [
                    bin_cf,
                    "tunnel",
                    "--no-autoupdate",
                    "--config",
                    "NUL",
                    "--url",
                    f"http://localhost:{PORTA_SERVIDOR}",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=BASE_DIR,
                creationflags=flags,
            )
            ESTADO_SERVIDOR["processo_tunel"] = proc
        except Exception:
            ESTADO_SERVIDOR["iniciando_tunel"] = False
            return ""

        def _leitor_stdout(processo: subprocess.Popen):
            try:
                if not processo.stdout:
                    return
                for linha in processo.stdout:
                    if not linha:
                        continue
                    match = _REGEX_TRYCLOUDFLARE.search(linha)
                    if match and not ESTADO_SERVIDOR.get("url_cloudflare"):
                        url_encontrada = match.group(0).rstrip("/")
                        _salvar_tunnel_status_json(url_encontrada)
                        ESTADO_SERVIDOR["iniciando_tunel"] = False
                        evento_url.set()
            except Exception:
                pass
            finally:
                ESTADO_SERVIDOR["iniciando_tunel"] = False
                evento_url.set()

        threading.Thread(target=_leitor_stdout, args=(proc,), daemon=True).start()

    if aguardar_segundos > 0:
        evento_url.wait(timeout=aguardar_segundos)

    return ESTADO_SERVIDOR.get("url_cloudflare") or ""


@app.on_event("startup")
def _auto_iniciar_tunel_no_boot():
    """Inicia automaticamente o túnel Cloudflare em background ao subir o servidor."""
    threading.Thread(
        target=lambda: iniciar_ou_obter_tunel_cloudflare(forcar_reinicio=False, aguardar_segundos=0.0),
        daemon=True,
    ).start()


def _criar_backup_sqlite() -> str:
    """Cria cópia íntegra do banco SQLite (compatível com modo WAL) dentro de backups/."""
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    carimbo = datetime.now().strftime("%Y%m%d_%H%M")
    nome_arquivo = f"backup_kanemberg_{carimbo}.db"
    caminho_destino = os.path.join(BACKUPS_DIR, nome_arquivo)

    conn_origem = sqlite3.connect(DB_PATH)
    try:
        conn_destino = sqlite3.connect(caminho_destino)
        try:
            conn_origem.backup(conn_destino)
        finally:
            conn_destino.close()
    finally:
        conn_origem.close()

    return caminho_destino


def _montar_status_sistema() -> dict:
    ip_apenas = _detectar_ip_rede()
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = "servidor-kanemberg"

    ip_rede_http = f"http://{ip_apenas}:{PORTA_SERVIDOR}"
    url_ip_local = f"{ip_rede_http}/app"

    proc_tunel = ESTADO_SERVIDOR.get("processo_tunel")
    if proc_tunel is not None and proc_tunel.poll() is not None:
        ESTADO_SERVIDOR["processo_tunel"] = None
        ESTADO_SERVIDOR["url_cloudflare"] = ""

    url_cloudflare = (ESTADO_SERVIDOR.get("url_cloudflare") or "").strip().rstrip("/")
    if not url_cloudflare:
        url_ext = _ler_tunel_existente_log_externo()
        if url_ext:
            url_cloudflare = url_ext
            ESTADO_SERVIDOR["url_cloudflare"] = url_cloudflare

    # Prioriza url_cloudflare se ativa para o QR Code abrir direto em HTTPS (WebAPK puro sem ícone do Chrome)
    url_mobile = url_cloudflare if url_cloudflare else url_ip_local

    tamanho_kb = round(os.path.getsize(DB_PATH) / 1024, 1) if os.path.isfile(DB_PATH) else 0.0
    ultimo_backup = None
    if os.path.isdir(BACKUPS_DIR):
        arquivos = [
            os.path.join(BACKUPS_DIR, f)
            for f in os.listdir(BACKUPS_DIR)
            if f.lower().endswith(".db")
        ]
        if arquivos:
            mais_recente = max(os.path.getmtime(a) for a in arquivos)
            ultimo_backup = datetime.fromtimestamp(mais_recente).strftime("%d/%m/%Y %H:%M")

    return {
        "online": True,
        "acesso_mobile_ativo": acesso_mobile_ativo,
        "tunel_ativo": bool(url_cloudflare),
        "iniciando_tunel": bool(ESTADO_SERVIDOR.get("iniciando_tunel")),
        "url_cloudflare": url_cloudflare,
        "url_porteiro_fixo": URL_PORTEIRO_FIXO,
        "ip_rede": ip_rede_http,
        "ip_apenas": ip_apenas,
        "url_ip_local": url_ip_local,
        "hostname": hostname,
        "porta": PORTA_SERVIDOR,
        "url_mobile": url_mobile,
        "origem_chrome_flag": ip_rede_http,
        "chrome_flag_url": "chrome://flags/#unsafely-treat-insecure-origin-as-secure",
        "tamanho_banco_kb": tamanho_kb,
        "ultimo_backup": ultimo_backup,
        "atualizado_em": ESTADO_SERVIDOR.get("atualizado_em"),
    }


@app.get("/api/sistema/status")
def sistema_status(request: Request):
    exigir_acesso_local_caixa(request)
    return _montar_status_sistema()


@app.get("/api/sistema/tunnel-status")
def sistema_tunnel_status():
    """Retorna o JSON público de status do túnel e IP local para reconexão do Porteiro/PWA."""
    st = _montar_status_sistema()
    return {
        "url_ativa": st["url_cloudflare"],
        "ip_local": st["ip_rede"],
        "url_porteiro_fixo": st["url_porteiro_fixo"],
        "atualizado_em": st["atualizado_em"] or datetime.now().isoformat(timespec="seconds"),
    }


@app.post("/api/sistema/iniciar-tunel")
def sistema_iniciar_tunel(
    request: Request,
    dados: Optional[IniciarTunelInput] = None,
):
    exigir_acesso_local_caixa(request)
    reiniciar = bool(dados.reiniciar) if dados else True
    url_gerada = iniciar_ou_obter_tunel_cloudflare(
        forcar_reinicio=reiniciar,
        aguardar_segundos=15.0,
    )
    status_atual = _montar_status_sistema()
    status_atual["sucesso"] = bool(url_gerada)
    status_atual["mensagem"] = (
        f"Túnel HTTPS ativo: {url_gerada}"
        if url_gerada
        else "Não foi possível obter a URL do Cloudflare agora. Verifique a conexão com a internet."
    )
    return status_atual


@app.post("/api/sistema/cloudflare-url")
def sistema_definir_cloudflare_url(dados: CloudflareUrlInput, request: Request):
    exigir_acesso_local_caixa(request)
    url_limpa = (dados.url or "").strip().rstrip("/")
    _salvar_tunnel_status_json(url_limpa)
    status_atual = _montar_status_sistema()
    status_atual["sucesso"] = True
    return status_atual


@app.post("/api/sistema/mobile-toggle")
def sistema_mobile_toggle(dados: MobileToggleInput, request: Request):
    global acesso_mobile_ativo
    exigir_acesso_local_caixa(request)
    acesso_mobile_ativo = bool(dados.ativo)
    return _montar_status_sistema()


@app.get("/api/sistema/qrcode-acesso")
def sistema_qrcode_acesso(request: Request, url: Optional[str] = Query(None)):
    exigir_acesso_local_caixa(request)
    destino = (url or "").strip() or _montar_status_sistema()["url_mobile"]
    svg_bytes = _gerar_svg_qrcode_alto_contraste(destino, border=2)
    return Response(
        content=svg_bytes,
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


@app.get("/api/sistema/backup")
def sistema_backup_download(request: Request):
    exigir_acesso_local_caixa(request)
    caminho_backup = _criar_backup_sqlite()
    return FileResponse(
        caminho_backup,
        media_type="application/octet-stream",
        filename=os.path.basename(caminho_backup),
    )


@app.post("/api/sistema/desligar")
def sistema_desligar_seguro(request: Request):
    exigir_acesso_local_caixa(request)
    arquivo_bkp = None
    try:
        caminho = _criar_backup_sqlite()
        arquivo_bkp = os.path.basename(caminho)
    except Exception:
        arquivo_bkp = None

    proc_tunel = ESTADO_SERVIDOR.get("processo_tunel")
    if proc_tunel is not None:
        try:
            proc_tunel.terminate()
        except Exception:
            pass

    threading.Timer(1.0, lambda: os._exit(0)).start()
    return {
        "ok": True,
        "sucesso": True,
        "backup": arquivo_bkp,
        "mensagem": "Sistema encerrado com segurança. Você já pode fechar esta janela.",
    }


# ---------------------------------------------------------------------------
# 8. SERVIR ARQUIVOS ESTÁTICOS, PWA MANIFEST/SW (/manifest.json, /sw.js, / E /app)
# ---------------------------------------------------------------------------
import mimetypes

mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/manifest+json", ".webmanifest")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("image/png", ".png")


@app.get("/manifest.json")
@app.get("/manifest.webmanifest")
@app.get("/static/manifest.json")
def servir_manifest_pwa():
    """Serve o Web App Manifest com Content-Type oficial exigido pelo Chrome Android."""
    manifest_path = os.path.join(STATIC_DIR, "manifest.json")
    if os.path.isfile(manifest_path):
        return FileResponse(
            manifest_path,
            media_type="application/manifest+json",
            headers={"Cache-Control": "no-cache"},
        )
    raise HTTPException(status_code=404, detail="manifest.json não encontrado.")


@app.get("/sw.js")
@app.get("/static/sw.js")
def servir_service_worker_pwa():
    """Serve o Service Worker do PWA com escopo raiz '/' liberado."""
    sw_path = os.path.join(STATIC_DIR, "sw.js")
    if os.path.isfile(sw_path):
        return FileResponse(
            sw_path,
            media_type="application/javascript",
            headers={
                "Service-Worker-Allowed": "/",
                "Cache-Control": "no-cache, no-store, must-revalidate",
            },
        )
    raise HTTPException(status_code=404, detail="sw.js não encontrado.")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/static_sistema", StaticFiles(directory=STATIC_SISTEMA_DIR), name="static_sistema")


@app.get("/logo_kanemberg.png")
def servir_logo_kanemberg():
    """Serve a logo oficial Kanemberg para o Sistema Desktop."""
    if os.path.isfile(LOGO_PATH):
        return FileResponse(LOGO_PATH, media_type="image/png")
    raise HTTPException(status_code=404, detail="Logo não encontrada.")


@app.get("/sistema")
@app.get("/sistema/")
def sistema_desktop_root():
    """Serve 'static_sistema/sistema.html' na rota '/sistema'."""
    sistema_path = os.path.join(STATIC_SISTEMA_DIR, "sistema.html")
    if os.path.isfile(sistema_path):
        return FileResponse(
            sistema_path,
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
    return HTMLResponse(
        content="<h1>Kanemberg Sistema Desktop</h1><p>Arquivo <code>static_sistema/sistema.html</code> não encontrado.</p>",
        status_code=200,
    )


_PWA_SW_SCRIPT = """
  <script>
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(function () {});
    });
  }
  </script>
</body>"""


@app.get("/")
@app.get("/app")
@app.get("/app/")
def index_root():
    """Serve 'static/index.html' na rota raiz '/' e '/app' com registro automático do Service Worker PWA."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.isfile(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()
        html = html.replace(
            'href="/static/manifest.json?v=4"',
            'href="/manifest.json"',
        )
        if "navigator.serviceWorker.register" not in html and "</body>" in html:
            html = html.replace("</body>", _PWA_SW_SCRIPT, 1)
        return HTMLResponse(
            content=html,
            status_code=200,
            headers={"Cache-Control": "no-cache"},
        )
    return HTMLResponse(
        content="<h1>Kanemberg Mobile API</h1><p>Coloque o arquivo <code>static/index.html</code> para servir a interface web.</p>",
        status_code=200,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORTA_SERVIDOR)
