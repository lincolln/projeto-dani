"""
migrate.py — Migracao do Banco Legado para o Sistema v2
Le os dados do banco SQLite antigo (sistema_loja.db) e os importa
para o novo esquema SQLAlchemy (loja_daniel_v2.db).

Execute UMA UNICA VEZ antes de abrir o sistema novo:
    python migrate.py
"""

import sys
import os
import sqlite3

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

# Caminho do banco ANTIGO (na pasta do projeto legado)
BANCO_ANTIGO = os.path.join(_THIS_DIR, 'sistema_loja.db')


def migrar():
    """Executa a migracao completa dos dados do banco legado."""

    if not os.path.exists(BANCO_ANTIGO):
        print(f"[Migracão] Banco antigo nao encontrado em: {BANCO_ANTIGO}")
        print("[Migracão] Nada a migrar. O sistema v2 iniciara vazio.")
        return

    print(f"[Migracão] Lendo banco antigo: {BANCO_ANTIGO}")

    # Inicializa o banco v2 antes de importar os modelos
    from database.conexao import inicializar_banco, get_session
    from database.models import Atributo, Produto, ProdutoVariacao, Venda, Cliente, ContaFiado
    from datetime import datetime
    from controllers.config_ctrl import popular_dados_padrao

    inicializar_banco()

    conn_antigo = sqlite3.connect(BANCO_ANTIGO)
    conn_antigo.text_factory = lambda x: str(x, 'utf-8', 'ignore')
    cur = conn_antigo.cursor()

    contadores = {
        'atributos': 0,
        'produtos':  0,
        'variacoes': 0,
        'vendas':    0,
        'erros':     0,
    }

    # ------------------------------------------------------------------
    # 1. MIGRAR ATRIBUTOS das 5 tabelas separadas
    # ------------------------------------------------------------------
    mapeamento_tabelas = {
        'marcas':      'marca',
        'tipos_pecas': 'tipo_peca',
        'tecidos':     'tecido',
        'cortes':      'corte',
        'cores':       'cor',
    }

    with get_session() as session:
        for tabela_antiga, categoria_nova in mapeamento_tabelas.items():
            try:
                cur.execute(f"SELECT nome FROM {tabela_antiga}")
                nomes = [row[0] for row in cur.fetchall()]
            except sqlite3.OperationalError:
                print(f"  [aviso] Tabela '{tabela_antiga}' nao existe no banco antigo, pulando.")
                continue

            for nome in nomes:
                if not nome:
                    continue
                # Verifica se ja existe para evitar duplicatas
                existente = session.query(Atributo).filter(
                    Atributo.categoria == categoria_nova,
                    Atributo.nome == nome
                ).first()
                if not existente:
                    session.add(Atributo(categoria=categoria_nova, nome=nome))
                    contadores['atributos'] += 1

    print(f"  ✅ {contadores['atributos']} atributos migrados.")

    # ------------------------------------------------------------------
    # 2. MIGRAR PRODUTOS (tabela antiga 'produtos' = SKU flat)
    # Agrupa por modelo_nome + marca + tecido + corte para criar o Mestre.
    # Cada linha vira uma ProdutoVariacao (Detalhe).
    # ------------------------------------------------------------------
    try:
        cur.execute("""
            SELECT id, modelo_nome, marca, tecido, corte, tamanho, cor,
                   preco_custo, preco_venda, estoque, foto_path
            FROM produtos
        """)
        linhas_antigas = cur.fetchall()
    except sqlite3.OperationalError as e:
        print(f"  [erro] Nao foi possivel ler tabela 'produtos': {e}")
        linhas_antigas = []

    # Agrupa linhas em produtos mestres pela chave (modelo, marca, tecido, corte)
    grupos_mestre: dict[tuple, list] = {}
    sku_info = {}
    for linha in linhas_antigas:
        id_a, modelo, marca, tecido, corte, tam, cor, custo, venda, est, foto = linha
        chave = (modelo or '', marca or '', tecido or '', corte or '')
        if chave not in grupos_mestre:
            grupos_mestre[chave] = []
        grupos_mestre[chave].append({
            'id_antigo': id_a,
            'tamanho':   tam or 'M',
            'cor':       cor or '',
            'custo':     float(custo or 0.0),
            'venda':     float(venda or 0.0),
            'estoque':   int(est or 0),
            'foto':      foto,
        })
        sku_info[id_a] = {
            'marca': marca or '',
            'cor': cor or '',
            'tamanho': tam or 'M',
            'custo': float(custo or 0.0)
        }

    # Mapa de id_antigo -> variacao_id_novo (para migrar vendas)
    mapa_ids: dict[int, int] = {}

    with get_session() as session:
        from utils_cores import resolver_cor_hex
        for (modelo, marca, tecido, corte), skus in grupos_mestre.items():
            try:
                cores_unicas = set(sku['cor'] for sku in skus if sku['cor'])
                cores_tags_lista = []
                for c in cores_unicas:
                    hex_val = resolver_cor_hex(c) or ""
                    cores_tags_lista.append(f"{c}|{hex_val}")
                
                produto = Produto(
                    modelo_nome = modelo,
                    marca       = marca,
                    tecido      = tecido,
                    corte       = corte,
                    cores_tags  = ",".join(cores_tags_lista),
                )
                session.add(produto)
                session.flush()  # Obtém o ID gerado

                for sku in skus:
                    var = ProdutoVariacao(
                        produto_id  = produto.id,
                        tamanho     = sku['tamanho'],
                        cor         = sku['cor'],
                        estoque     = sku['estoque'],
                        preco_custo = sku['custo'],
                        preco_venda = sku['venda'],
                        foto_path   = sku['foto'],
                    )
                    session.add(var)
                    session.flush()
                    mapa_ids[sku['id_antigo']] = var.id
                    contadores['variacoes'] += 1

                contadores['produtos'] += 1
            except Exception as e:
                contadores['erros'] += 1
                print(f"  [erro] Produto '{modelo}': {e}")

    print(f"  ✅ {contadores['produtos']} modelos migrados "
          f"({contadores['variacoes']} variacoes/SKUs).")

    # ------------------------------------------------------------------
    # 3. MIGRAR VENDAS
    # ------------------------------------------------------------------
    try:
        cur.execute("PRAGMA table_info(vendas)")
        colunas_vendas = {col[1] for col in cur.fetchall()}
        
        sel_cols = ["id", "produto_id", "modelo", "quantidade", "valor_unitario", "valor_total", "data_venda"]
        
        has_forma = "forma_pagamento" in colunas_vendas
        if has_forma:
            sel_cols.append("forma_pagamento")
            
        query = f"SELECT {', '.join(sel_cols)} FROM vendas"
        cur.execute(query)
        vendas_antigas = cur.fetchall()
    except sqlite3.OperationalError as e:
        print(f"  [aviso] Nao foi possivel ler tabela 'vendas': {e}")
        vendas_antigas = []

    with get_session() as session:
        for v in vendas_antigas:
            vid = v[0]
            pid_antigo = v[1]
            modelo = v[2]
            qtd = v[3]
            unit = v[4]
            total = v[5]
            data = v[6]
            
            forma_pag = "DINHEIRO"
            if has_forma:
                forma_pag = v[7] or "DINHEIRO"
                
            variacao_id_novo = mapa_ids.get(pid_antigo)
            info = sku_info.get(pid_antigo, {})

            try:
                venda = Venda(
                    variacao_id    = variacao_id_novo,
                    modelo_nome    = modelo or '',
                    marca          = info.get('marca', ''),
                    cor            = info.get('cor', ''),
                    tamanho        = info.get('tamanho', ''),
                    quantidade     = int(qtd or 1),
                    valor_unitario = float(unit or 0.0),
                    valor_total    = float(total or 0.0),
                    preco_custo    = float(info.get('custo', 0.0)),
                    data_venda     = data or '',
                    forma_pagamento= forma_pag,
                )
                session.add(venda)
                contadores['vendas'] += 1
            except Exception as e:
                contadores['erros'] += 1

    print(f"  ✅ {contadores['vendas']} vendas migradas.")

    # ------------------------------------------------------------------
    # 4. MIGRAR CLIENTES E CONTA FIADO
    # ------------------------------------------------------------------
    try:
        cur.execute("SELECT id, nome, telefone, limite_credito, dia_preferencial_pagamento FROM clientes")
        clientes_antigos = cur.fetchall()
    except sqlite3.OperationalError as e:
        print(f"  [aviso] Nao foi possivel ler tabela 'clientes': {e}")
        clientes_antigos = []

    with get_session() as session:
        mapa_clientes = {}
        for c in clientes_antigos:
            cid, nome, telefone, limite, dia = c
            try:
                cliente = Cliente(
                    nome=nome,
                    telefone=telefone or '',
                    limite_credito=float(limite or 500.0),
                    dia_preferencial_pagamento=int(dia or 5)
                )
                session.add(cliente)
                session.flush()
                mapa_clientes[cid] = cliente.id
                contadores['clientes'] = contadores.get('clientes', 0) + 1
            except Exception as e:
                contadores['erros'] += 1

    try:
        cur.execute("SELECT id, cliente_id, tipo_movimentacao, valor, data_movimentacao, descricao FROM conta_fiado")
        fiado_antigo = cur.fetchall()
    except sqlite3.OperationalError as e:
        print(f"  [aviso] Nao foi possivel ler tabela 'conta_fiado': {e}")
        fiado_antigo = []

    with get_session() as session:
        for f in fiado_antigo:
            fid, cid_antigo, tipo, valor, data, desc = f
            cid_novo = mapa_clientes.get(cid_antigo)
            if not cid_novo:
                continue
            
            try:
                dt = datetime.strptime(data, '%Y-%m-%d %H:%M:%S.%f') if data else datetime.now()
            except ValueError:
                try:
                    dt = datetime.strptime(data, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    dt = datetime.now()

            try:
                conta = ContaFiado(
                    cliente_id=cid_novo,
                    tipo_movimentacao=tipo,
                    valor=float(valor or 0.0),
                    data_movimentacao=dt,
                    descricao=desc or ''
                )
                session.add(conta)
                contadores['fiado'] = contadores.get('fiado', 0) + 1
            except Exception as e:
                contadores['erros'] += 1

    print(f"  ✅ {contadores.get('clientes', 0)} clientes migrados.")
    print(f"  ✅ {contadores.get('fiado', 0)} movimentos de fiado migrados.")

    conn_antigo.close()

    # Popula dados padrao que nao existiam no legado
    popular_dados_padrao()

    print("\n" + "="*50)
    print("MIGRACAO CONCLUIDA COM SUCESSO!")
    print("="*50)
    print(f"  Atributos migrados : {contadores['atributos']}")
    print(f"  Modelos migrados   : {contadores['produtos']}")
    print(f"  SKUs migrados      : {contadores['variacoes']}")
    print(f"  Vendas migradas    : {contadores['vendas']}")
    if contadores['erros']:
        print(f"  ⚠️  Erros ignorados : {contadores['erros']}")
    print("="*50)
    print("\nAgora execute: python loja_daniel_v2/main.py")


if __name__ == "__main__":
    migrar()
