from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import os

# Caminho absoluto para o banco de dados dentro da pasta raiz do projeto
_DIR = os.path.dirname(os.path.abspath(__file__))
_DB_PATH = os.path.join(_DIR, '..', 'loja_daniel_v2.db')
_DB_URL = f'sqlite:///{os.path.normpath(_DB_PATH)}'

engine = create_engine(_DB_URL, connect_args={'check_same_thread': False})

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Configura PRAGMAs de performance do SQLite a cada nova conexão."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA cache_size=-64000")
    cursor.close()

Session = sessionmaker(bind=engine)


@contextmanager
def get_session():
    """Context manager para abrir e fechar uma sessao SQLAlchemy com seguranca.

    Exemplo de uso:
        with get_session() as session:
            session.add(obj)
    """
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def inicializar_banco():
    """Cria todas as tabelas no banco se ainda nao existirem."""
    from database.models import Base
    Base.metadata.create_all(engine)

    # Executa alterações automáticas de tabela (migrações) se necessário
    import sqlite3
    conn = sqlite3.connect(_DB_PATH)
    try:
        cur = conn.cursor()
        
        # 1. Adicionar dia_preferencial_pagamento na tabela clientes
        cur.execute("PRAGMA table_info(clientes)")
        cols_clientes = [r[1] for r in cur.fetchall()]
        if 'dia_preferencial_pagamento' not in cols_clientes:
            cur.execute("ALTER TABLE clientes ADD COLUMN dia_preferencial_pagamento INTEGER DEFAULT 5")
            print("[DB Migration] Coluna 'dia_preferencial_pagamento' adicionada à tabela 'clientes'.")
            
        # 2. Adicionar tipo_movimentacao na tabela conta_fiado
        cur.execute("PRAGMA table_info(conta_fiado)")
        cols_fiado = [r[1] for r in cur.fetchall()]
        if 'tipo_movimentacao' not in cols_fiado:
            cur.execute("ALTER TABLE conta_fiado ADD COLUMN tipo_movimentacao VARCHAR(10)")
            if 'tipo' in cols_fiado:
                cur.execute("UPDATE conta_fiado SET tipo_movimentacao = tipo")
            print("[DB Migration] Coluna 'tipo_movimentacao' adicionada à tabela 'conta_fiado'.")
            
        # 3. Adicionar descricao na tabela conta_fiado
        if 'descricao' not in cols_fiado:
            cur.execute("ALTER TABLE conta_fiado ADD COLUMN descricao VARCHAR(255)")
            if 'observacao' in cols_fiado:
                cur.execute("UPDATE conta_fiado SET descricao = observacao")
            print("[DB Migration] Coluna 'descricao' adicionada à tabela 'conta_fiado'.")
            
        # 4. Adicionar data_vencimento_lote na tabela conta_fiado
        if 'data_vencimento_lote' not in cols_fiado:
            cur.execute("ALTER TABLE conta_fiado ADD COLUMN data_vencimento_lote DATETIME")
            print("[DB Migration] Coluna 'data_vencimento_lote' adicionada à tabela 'conta_fiado'.")

        # 5. Adicionar cores_tags na tabela produtos (Novo modelo de variações desacoplado)
        cur.execute("PRAGMA table_info(produtos)")
        cols_produtos = [r[1] for r in cur.fetchall()]
        if 'cores_tags' not in cols_produtos:
            cur.execute("ALTER TABLE produtos ADD COLUMN cores_tags VARCHAR(500) DEFAULT ''")
            print("[DB Migration] Coluna 'cores_tags' adicionada à tabela 'produtos'.")

        # ── NOVAS MIGRAÇÕES — Grade de Produtos (Pai/Filho) ──────────────────
        cur.execute("PRAGMA table_info(produto_variacoes)")
        cols_variacoes = [r[1] for r in cur.fetchall()]

        # 5. Adicionar cor_hex para pintar os círculos coloridos do Card Vertical
        if 'cor_hex' not in cols_variacoes:
            cur.execute("ALTER TABLE produto_variacoes ADD COLUMN cor_hex VARCHAR(10) DEFAULT ''")
            print("[DB Migration] Coluna 'cor_hex' adicionada à tabela 'produto_variacoes'.")
            # Tenta resolver automaticamente os hexadecimais das cores já cadastradas
            try:
                import sys, os
                _raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if _raiz not in sys.path:
                    sys.path.insert(0, _raiz)
                from utils_cores import resolver_cor_hex
                cur.execute("SELECT DISTINCT cor FROM produto_variacoes WHERE cor IS NOT NULL AND cor != ''")
                cores_existentes = cur.fetchall()
                for (nome_cor,) in cores_existentes:
                    hex_val = resolver_cor_hex(nome_cor)
                    if hex_val:
                        cur.execute(
                            "UPDATE produto_variacoes SET cor_hex = ? WHERE cor = ? AND (cor_hex IS NULL OR cor_hex = '')",
                            (hex_val, nome_cor)
                        )
                        print(f"[DB Migration] Cor '{nome_cor}' -> '{hex_val}' aplicada automaticamente.")
            except Exception as e:
                print(f"[DB Migration] Aviso: não foi possível resolver cores automaticamente: {e}")

        # 6. Adicionar codigo_barras para o gerador de código de barras
        if 'codigo_barras' not in cols_variacoes:
            cur.execute("ALTER TABLE produto_variacoes ADD COLUMN codigo_barras VARCHAR(30) DEFAULT ''")
            print("[DB Migration] Coluna 'codigo_barras' adicionada à tabela 'produto_variacoes'.")

        # 7. Adicionar preco_custo na tabela vendas (custo histórico no momento da venda)
        cur.execute("PRAGMA table_info(vendas)")
        cols_vendas = [r[1] for r in cur.fetchall()]
        if 'preco_custo' not in cols_vendas:
            cur.execute("ALTER TABLE vendas ADD COLUMN preco_custo REAL DEFAULT 0.0")
            print("[DB Migration] Coluna 'preco_custo' adicionada à tabela 'vendas'.")

        conn.commit()
    except Exception as e:
        print(f"[DB Migration] Erro ao aplicar migrações: {e}")
    finally:
        conn.close()

    print("[DB] Banco de dados verificado e pronto.")

