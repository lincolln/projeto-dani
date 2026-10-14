"""
estoque_ctrl.py — Controller de Estoque
Responsabilidade: CRUD completo de Produtos (mestre) e ProdutoVariacoes (SKUs),
alem da logica de venda (abate de estoque e registro de vendas).
"""

from datetime import datetime
from database.conexao import get_session
from database.models import Produto, ProdutoVariacao, Venda
from sqlalchemy.orm import contains_eager, joinedload


# ---------------------------------------------------------------------------
# CONSULTAS DE LISTAGEM
# ---------------------------------------------------------------------------

def listar_produtos_vitrine(termo: str = '') -> list[dict]:
    """Retorna produtos com suas variacoes para a tela de estoque.
    Limita a 20 resultados para performance em notebooks.

    Args:
        termo: Texto de busca (filtra por modelo, marca, cor).

    Returns:
        Lista de dicts com dados resumidos de cada variacao.
    """
    with get_session() as session:
        query = (
            session.query(ProdutoVariacao)
            .join(Produto)
            .options(contains_eager(ProdutoVariacao.produto))
        )
        if termo:
            like = f'%{termo}%'
            query = query.filter(
                (Produto.modelo_nome.ilike(like)) |
                (Produto.marca.ilike(like)) |
                (ProdutoVariacao.cor.ilike(like)) |
                (Produto.cores_tags.ilike(like))
            )
        variacoes = query.order_by(ProdutoVariacao.id.desc()).limit(20).all()

        resultado = []
        for v in variacoes:
            resultado.append({
                'variacao_id': v.id,
                'produto_id':  v.produto_id,
                'modelo_nome': v.produto.modelo_nome,
                'marca':       v.produto.marca,
                'tecido':      v.produto.tecido,
                'corte':       v.produto.corte,
                'tamanho':     v.tamanho,
                'cor':         v.cor,
                'estoque':     v.estoque,
                'preco_custo': v.preco_custo,
                'preco_venda': v.preco_venda,
                'foto_path':   v.foto_path,
            })
        return resultado


def listar_produtos_vitrine_grade() -> list[dict]:
    """Retorna produtos agrupados por PAI para o Card Vertical da vitrine.

    Cada item da lista representa um produto mestre (Pai) com:
      - Suas cores únicas + hexadecimais (para os círculos coloridos).
      - Resumo de tamanhos e quantidades totais por tamanho.
      - Primeira variação com estoque como candidata para a ação Vender.
      - Preços e caminho de imagem.

    Não usa limite de 20 (a filtragem Pandas na view se encarrega do recorte).

    Returns:
        Lista de dicts prontos para construir ``CardProdutoVertical``.
    """
    with get_session() as session:
        variacoes = (
            session.query(ProdutoVariacao)
            .join(Produto)
            .options(contains_eager(ProdutoVariacao.produto))
            .order_by(Produto.id.desc(), ProdutoVariacao.tamanho)
            .all()
        )

        # Agrupa por produto_id em memória
        grupos: dict[int, dict] = {}
        for v in variacoes:
            pid = v.produto_id
            if pid not in grupos:
                cores_dict = {}
                tags = getattr(v.produto, 'cores_tags', '')
                if tags:
                    for tag in tags.split(','):
                        if '|' in tag:
                            n, h = tag.split('|', 1)
                            cores_dict[n] = h

                grupos[pid] = {
                    "produto_id":    pid,
                    "tipo_peca":     v.produto.modelo_nome,
                    "marca":         v.produto.marca,
                    "corte":         v.produto.corte  or '',
                    "tecido":        v.produto.tecido or '',
                    "preco_custo":   v.preco_custo,
                    "preco_venda":   v.preco_venda,
                    "foto_path":     v.foto_path,
                    # Cores extraídas diretamente das tags do Produto Pai
                    "_cores_dict":   cores_dict,
                    # Tamanhos: {tamanho: total_estoque}
                    "_tams_dict":    {},
                    # IDs de variações com estoque > 0 (para Vender)
                    "variacoes_ids": [],
                }

            g = grupos[pid]

            # Atualiza preço para usar o maior encontrado (último cadastrado)
            if v.preco_venda > 0:
                g["preco_custo"] = v.preco_custo
                g["preco_venda"] = v.preco_venda
            if v.foto_path:
                g["foto_path"] = v.foto_path

            # Acumula estoque por tamanho
            tam = (v.tamanho or "").strip().upper()
            if tam:
                g["_tams_dict"][tam] = g["_tams_dict"].get(tam, 0) + (v.estoque or 0)

            # Registra variação com estoque disponível
            if v.estoque and v.estoque > 0:
                g["variacoes_ids"].append(v.id)

        # Formata saída final
        resultado = []
        for g in grupos.values():
            resultado.append({
                "produto_id":     g["produto_id"],
                "tipo_peca":      g["tipo_peca"],
                "marca":          g["marca"],
                "corte":          g["corte"],
                "tecido":         g["tecido"],
                "preco_custo":    g["preco_custo"],
                "preco_venda":    g["preco_venda"],
                "foto_path":      g["foto_path"],
                # Lista de (nome_cor, hex_cor) para os círculos
                "cores_lista":    list(g["_cores_dict"].items()),
                # Dict {tamanho: total_estoque} para o painel direito
                "tamanhos_resumo": g["_tams_dict"],
                # IDs de variações com estoque (primeiro = candidato a Vender)
                "variacoes_ids":  g["variacoes_ids"],
            })

        return resultado



def buscar_por_codigo(codigo: str) -> dict | None:
    """Busca uma variação pelo código identificador (QR Code ou Código de Barras).

    Suporta códigos diretos (ex: 'KNB000010001') e extração inteligente de
    leituras de scanners 2D ou URLs de celular.

    Retorna dict com dados completos da variação para o PDV, ou None.
    """
    codigo = (codigo or "").strip()
    if not codigo:
        return None

    # Tratamento para possíveis URLs ou quebras vindas de câmeras/scanners 2D
    if "/" in codigo:
        codigo = codigo.rstrip("/").split("/")[-1].strip()
    if "=" in codigo:
        codigo = codigo.split("=")[-1].strip()

    with get_session() as session:
        v = (
            session.query(ProdutoVariacao)
            .join(Produto)
            .filter(
                (ProdutoVariacao.codigo_barras == codigo) |
                (ProdutoVariacao.codigo_barras.ilike(codigo))
            )
            .first()
        )
        if not v:
            return None
        if v.estoque <= 0:
            return None

        cor_exibicao = v.cor
        if not cor_exibicao and getattr(v.produto, 'cores_tags', ''):
            cor_exibicao = ', '.join([t.split('|')[0] for t in v.produto.cores_tags.split(',') if '|' in t])

        return {
            'variacao_id': v.id,
            'modelo_nome': v.produto.modelo_nome,
            'marca':       v.produto.marca,
            'cor':         cor_exibicao,
            'tamanho':     v.tamanho,
            'preco_venda': v.preco_venda,
            'estoque':     v.estoque,
            'codigo':      v.codigo_barras,
        }


# Mantém compatibilidade total com chamadas legadas
buscar_por_codigo_barras = buscar_por_codigo



def listar_variacoes_com_estoque() -> list[dict]:
    """Retorna todas as variacoes com estoque positivo para o PDV (Caixa).

    Returns:
        Lista de dicts com dados para popular o Combobox de vendas.
    """
    with get_session() as session:
        variacoes = (
            session.query(ProdutoVariacao)
            .join(Produto)
            .options(contains_eager(ProdutoVariacao.produto))
            .filter(ProdutoVariacao.estoque > 0)
            .order_by(Produto.modelo_nome)
            .all()
        )
        return [
            {
                'variacao_id': v.id,
                'modelo_nome': v.produto.modelo_nome,
                'marca':       v.produto.marca,
                'corte':       v.produto.corte  or '',
                'tecido':      v.produto.tecido or '',
                'cor':         v.cor if v.cor else (', '.join([t.split('|')[0] for t in getattr(v.produto, 'cores_tags', '').split(',') if '|' in t]) if getattr(v.produto, 'cores_tags', '') else ''),
                'tamanho':     v.tamanho,
                'preco_venda': v.preco_venda,
                'estoque':     v.estoque,
            }
            for v in variacoes
        ]


def listar_variacoes_por_produto(produto_id: int) -> list[dict]:
    """Retorna todas as variações de um produto PAI para o picker de tamanho no PDV.

    Inclui variações com estoque zerado (exibidas como indisponíveis no picker).

    Args:
        produto_id: ID do produto mestre (Pai).

    Returns:
        Lista de dicts ordenados por tamanho com dados de cada variação.
    """
    with get_session() as session:
        variacoes = (
            session.query(ProdutoVariacao)
            .filter(ProdutoVariacao.produto_id == produto_id)
            .order_by(ProdutoVariacao.tamanho)
            .all()
        )
        return [
            {
                'variacao_id':   v.id,
                'tamanho':       v.tamanho,
                'preco_venda':   v.preco_venda,
                'estoque':       v.estoque,
                'codigo_barras': getattr(v, 'codigo_barras', '') or '',
            }
            for v in variacoes
        ]


def buscar_produto_completo(produto_id: int) -> dict | None:
    """Retorna os dados completos de um produto com suas variacoes.
    Usado pela tela de cadastro no modo edicao.
    """
    with get_session() as session:
        p = session.get(Produto, produto_id)
        if not p:
            return None
            
        cores_lista = []
        tags = getattr(p, 'cores_tags', '')
        if tags:
            for tag in tags.split(','):
                if '|' in tag:
                    n, h = tag.split('|', 1)
                    cores_lista.append((n, h))

        return {
            'id':          p.id,
            'modelo_nome': p.modelo_nome,
            'marca':       p.marca,
            'tecido':      p.tecido,
            'corte':       p.corte,
            'cores_lista': cores_lista,
            'variacoes': [
                {
                    'id':            v.id,
                    'tamanho':       v.tamanho,
                    'codigo_barras': getattr(v, 'codigo_barras', '') or '',
                    'estoque':       v.estoque,
                    'preco_custo':   v.preco_custo,
                    'preco_venda':   v.preco_venda,
                    'foto_path':     v.foto_path,
                }
                for v in p.variacoes
            ]
        }



# ---------------------------------------------------------------------------
# OPERACOES DE ESCRITA — PRODUTO
# ---------------------------------------------------------------------------

def salvar_produto(modelo_nome: str, marca: str, tecido: str, corte: str,
                   produto_id: int | None = None) -> tuple[bool, str, int | None]:
    """Cria ou atualiza o registro mestre (Produto).

    Args:
        modelo_nome: Nome do modelo.
        marca: Marca da peca.
        tecido: Tipo de tecido.
        corte: Tipo de corte.
        produto_id: Se informado, atualiza o produto existente.

    Returns:
        Tupla (sucesso, mensagem, id_do_produto).
    """
    modelo_nome = modelo_nome.strip()
    if not modelo_nome:
        return False, "O nome do modelo nao pode ser vazio.", None

    with get_session() as session:
        if produto_id:
            produto = session.get(Produto, produto_id)
            if not produto:
                return False, "Produto nao encontrado.", None
        else:
            produto = Produto()
            session.add(produto)

        produto.modelo_nome = modelo_nome
        produto.marca       = marca.strip()
        produto.tecido      = tecido.strip()
        produto.corte       = corte.strip()
        session.flush()  # Garante que o ID e gerado antes do commit
        pid = produto.id

    return True, "Produto salvo com sucesso.", pid


def excluir_produto(produto_id: int) -> tuple[bool, str, list[str]]:
    """Remove o produto e todas as suas variacoes em cascata.

    Returns:
        Tupla (sucesso, mensagem, lista_de_fotos_para_deletar).
    """
    with get_session() as session:
        produto = session.get(Produto, produto_id)
        if not produto:
            return False, "Produto nao encontrado.", []

        fotos = [v.foto_path for v in produto.variacoes if v.foto_path]
        session.delete(produto)

    return True, "Produto e todas as suas variacoes foram removidos.", fotos


# ---------------------------------------------------------------------------
# OPERACOES DE ESCRITA — VARIACAO (SKU)
# ---------------------------------------------------------------------------

def adicionar_variacao(produto_id: int, tamanho: str, cor: str,
                       estoque: int, preco_custo: float,
                       preco_venda: float, foto_path: str | None = None) -> tuple[bool, str]:
    """Adiciona uma nova variacao (SKU) a um produto existente.

    Returns:
        Tupla (sucesso, mensagem).
    """
    with get_session() as session:
        produto = session.get(Produto, produto_id)
        if not produto:
            return False, "Produto pai nao encontrado."

        variacao = ProdutoVariacao(
            produto_id=produto_id,
            tamanho=tamanho.strip(),
            cor=cor.strip(),
            estoque=max(0, int(estoque)),
            preco_custo=float(preco_custo),
            preco_venda=float(preco_venda),
            foto_path=foto_path,
        )
        session.add(variacao)

    return True, f"Variacao {tamanho}/{cor} adicionada."


def atualizar_variacao(variacao_id: int, tamanho: str, cor: str,
                       estoque: int, preco_custo: float,
                       preco_venda: float, foto_path: str | None = None) -> tuple[bool, str]:
    """Atualiza os dados de uma variacao existente.

    Returns:
        Tupla (sucesso, mensagem).
    """
    with get_session() as session:
        v = session.get(ProdutoVariacao, variacao_id)
        if not v:
            return False, "Variacao nao encontrada."

        v.tamanho     = tamanho.strip()
        v.cor         = cor.strip()
        v.estoque     = max(0, int(estoque))
        v.preco_custo = float(preco_custo)
        v.preco_venda = float(preco_venda)
        if foto_path:
            v.foto_path = foto_path

    return True, "Variacao atualizada."


def excluir_variacao(variacao_id: int) -> tuple[bool, str, str | None]:
    """Remove uma variacao (SKU) especifica.

    Returns:
        Tupla (sucesso, mensagem, foto_path_para_deletar).
    """
    with get_session() as session:
        v = session.get(ProdutoVariacao, variacao_id)
        if not v:
            return False, "Variacao nao encontrada.", None
        foto = v.foto_path
        session.delete(v)

    return True, "Variacao removida.", foto


def cadastrar_lote_produtos(modelo_nome: str, marca: str, tecido: str, corte: str,
                            tamanhos: list[str], cores: list[str],
                            custo: float, venda: float, qtd_inicial: int,
                            produto_id: int | None = None,
                            foto_path: str | None = None) -> tuple[bool, str]:
    """Cadastra um produto mestre e cria multiplas variacoes (lote/grade) no banco.
    Se o produto_id for fornecido, atualiza-se esse produto existente.
    Caso contrario, cria-se um novo ou busca-se um com os mesmos atributos.
    """
    if not modelo_nome or not marca or not tecido or not corte:
        return False, "Preencha todas as caracteristicas do modelo."
    if not tamanhos:
        return False, "Selecione pelo menos um tamanho."
    if not cores:
        return False, "Selecione pelo menos uma cor."

    with get_session() as session:
        # 1. Verifica ou cria o Produto (mestre)
        if produto_id:
            produto = session.get(Produto, produto_id)
            if not produto:
                return False, f"Produto ID {produto_id} não encontrado."
            # Atualiza os dados mestre
            produto.modelo_nome = modelo_nome
            produto.marca = marca
            produto.tecido = tecido
            produto.corte = corte
        else:
            produto = (
                session.query(Produto)
                .filter(
                    Produto.modelo_nome == modelo_nome,
                    Produto.marca == marca,
                    Produto.tecido == tecido,
                    Produto.corte == corte
                )
                .first()
            )
            if not produto:
                produto = Produto(
                    modelo_nome=modelo_nome,
                    marca=marca,
                    tecido=tecido,
                    corte=corte
                )
                session.add(produto)
                session.flush() # obtém o ID

        # 2. Insere ou atualiza as variacoes de tamanho e cor
        criados = 0
        atualizados = 0
        
        variacoes_existentes = session.query(ProdutoVariacao).filter(ProdutoVariacao.produto_id == produto.id).all()
        variacoes_dict = {(v.tamanho, v.cor): v for v in variacoes_existentes}

        for cor in cores:
            for tam in tamanhos:
                variacao = variacoes_dict.get((tam, cor))
                if variacao:
                    # Incrementa o estoque e atualiza os preços
                    variacao.estoque += qtd_inicial
                    variacao.preco_custo = custo
                    variacao.preco_venda = venda
                    atualizados += 1
                else:
                    nova_var = ProdutoVariacao(
                        produto_id=produto.id,
                        tamanho=tam,
                        cor=cor,
                        estoque=qtd_inicial,
                        preco_custo=custo,
                        preco_venda=venda,
                        foto_path=foto_path or None,
                    )
                    session.add(nova_var)
                    criados += 1

        total = criados + atualizados
    return True, f"Grade gerada! {total} variações salvas ({criados} novas, {atualizados} atualizadas)."


def salvar_grade_dinamica(
    modelo_nome:      str,
    marca:            str,
    tecido:           str,
    corte:            str,
    tamanhos_com_qtd: dict,
    cores_com_hex:    list,
    preco_custo:      float,
    preco_venda:      float,
    foto_path:        str | None = None,
    produto_id:       int | None = None,
) -> tuple[bool, str]:
    """Salva a grade completa Pai/Filho (Espelhamento Seguro).
    Desacopla Cores (tags visuais no Pai) de Quantidades (amarradas aos Tamanhos).
    """
    modelo_nome = (modelo_nome or "").strip()
    marca       = (marca or "").strip()
    tecido      = (tecido or "").strip()
    corte       = (corte or "").strip()

    if not modelo_nome:
        return False, "O Tipo/Peca nao pode estar vazio."
    if not marca:
        return False, "A Marca nao pode estar vazia."
    if not tamanhos_com_qtd:
        return False, "Marque pelo menos um tamanho e informe a quantidade."

    with get_session() as session:
        # Formatar cores_tags: "Nome|#HEX,Nome2|#HEX2"
        cores_formatadas = []
        for nome_cor, hex_cor in cores_com_hex:
            n = (nome_cor or "").strip()
            h = (hex_cor or "#808080").strip()
            if n:
                cores_formatadas.append(f"{n}|{h}")
        string_cores = ",".join(cores_formatadas)

        # ── 1. UPSERT do produto mestre ──────────────────────────────────────
        if produto_id:
            produto = session.get(Produto, produto_id)
            if not produto:
                return False, f"Produto ID {produto_id} nao encontrado no banco."
            produto.modelo_nome = modelo_nome
            produto.marca       = marca
            produto.tecido      = tecido
            produto.corte       = corte
            produto.cores_tags  = string_cores
        else:
            produto = (
                session.query(Produto)
                .filter(
                    Produto.modelo_nome == modelo_nome,
                    Produto.marca       == marca,
                    Produto.tecido      == tecido,
                    Produto.corte       == corte,
                )
                .first()
            )
            if not produto:
                produto = Produto(
                    modelo_nome=modelo_nome,
                    marca=marca,
                    tecido=tecido,
                    corte=corte,
                    cores_tags=string_cores
                )
                session.add(produto)
            else:
                produto.cores_tags = string_cores

        session.flush()
        pid = produto.id

        # Se for edicao, nao zeramos mais todas as variacoes cegas.
        # Apenas sobrescrevemos aquelas que vêm no dicionario tamanhos_com_qtd
        session.flush()

        # ── 2. INSERT / UPDATE das variacoes (apenas por Tamanho) ─────────────
        criados     = 0
        atualizados = 0
        idx_global  = 0
        
        variacoes_existentes = session.query(ProdutoVariacao).filter(ProdutoVariacao.produto_id == pid).all()
        variacoes_dict = {v.tamanho: v for v in variacoes_existentes}

        for tamanho, quantidade in tamanhos_com_qtd.items():
            tamanho = (tamanho or "").strip()
            idx_global += 1
            codigo_barras = f"KNB{pid:05d}{idx_global:04d}"

            variacao_existente = variacoes_dict.get(tamanho)

            if variacao_existente:
                # ESPELHAMENTO: Sobrescreve a quantidade exata da tela (ignora antigos pq ja zeramos)
                variacao_existente.estoque     = max(0, quantidade)
                variacao_existente.preco_custo = preco_custo
                variacao_existente.preco_venda = preco_venda
                variacao_existente.cor         = ''
                variacao_existente.cor_hex     = ''
                if foto_path:
                    variacao_existente.foto_path = foto_path
                atualizados += 1
            else:
                nova = ProdutoVariacao(
                    produto_id    = pid,
                    tamanho       = tamanho,
                    cor           = '',
                    cor_hex       = '',
                    estoque       = max(0, quantidade),
                    preco_custo   = preco_custo,
                    preco_venda   = preco_venda,
                    foto_path     = foto_path,
                    codigo_barras = codigo_barras,
                )
                session.add(nova)
                criados += 1

    total = criados + atualizados
    s = "variacao" if total == 1 else "variacoes"
    return True, (
        f"Grade salva! {total} {s} "
        f"({criados} novas, {atualizados} atualizadas). "
        f"Produto ID: {pid}."
    )


from controllers import fiado_ctrl  # Garante a conexao direta entre os modulos



def registrar_venda_lote(itens_carrinho: list[dict],
                         desconto_total: float = 0.0,
                         forma_pagamento: str = 'DINHEIRO',
                         cliente_id: int | None = None,
                         dt_vencimento: datetime = None) -> tuple[bool, str]:
    """
    Registra todas as vendas do carrinho, abate o estoque em lote atômico
    e, se for FIADO, lança o débito no Saldo Rotativo do Cliente com a data atual e vencimento combinado.
    """
    if not itens_carrinho:
        return False, "Carrinho vazio."

    # VALIDAÇÃO CRÍTICA: Se for fiado, o ID do cliente precisa vir do front-end
    if forma_pagamento == 'FIADO' and not cliente_id:
        return False, "Erro: É necessário selecionar um cliente para vendas no Fiado."

    subtotal_geral = sum(i['subtotal'] for i in itens_carrinho)
    desconto_total = min(max(0.0, desconto_total), subtotal_geral)
    fator = (subtotal_geral - desconto_total) / subtotal_geral if subtotal_geral > 0 else 1.0
    data_atual = datetime.now().strftime('%d/%m/%Y %H:%M')

    with get_session() as session:
        valor_total_venda_com_desconto = 0.0
        nomes_itens = []

        for item in itens_carrinho:
            v = session.get(ProdutoVariacao, item['variacao_id'])
            if not v:
                raise ValueError(
                    f"Produto '{item['modelo']}' ({item['cor']}/{item['tamanho']}) "
                    f"não encontrado no estoque. A venda foi cancelada."
                )

            if v.estoque < item['qtd']:
                raise ValueError(
                    f"Estoque insuficiente para {item['modelo']} ({item['cor']}/{item['tamanho']}). "
                    f"Disponível: {v.estoque} un."
                )

            valor_com_desconto = item['subtotal'] * fator
            valor_unitario     = valor_com_desconto / item['qtd']
            
            valor_total_venda_com_desconto += valor_com_desconto
            nomes_itens.append(f"{item['qtd']}x {item['modelo']} ({item['tamanho']})")

            venda = Venda(
                variacao_id     = v.id,
                modelo_nome     = item['modelo'],
                marca           = item.get('marca', ''),
                cor             = item['cor'] if item.get('cor') else (', '.join([t.split('|')[0] for t in getattr(v.produto, 'cores_tags', '').split(',') if '|' in t]) if getattr(v.produto, 'cores_tags', '') else ''),
                tamanho         = item['tamanho'],
                quantidade      = item['qtd'],
                valor_unitario  = valor_unitario,
                valor_total     = valor_com_desconto,
                preco_custo     = v.preco_custo,
                data_venda      = data_atual,
                forma_pagamento = forma_pagamento,
            )
            session.add(venda)
            v.estoque = v.estoque - item['qtd']
            if v.estoque < 0:
                raise ValueError(
                    f"Estoque insuficiente para {item['modelo']} ({item['cor']}/{item['tamanho']}). "
                    f"Outra venda pode ter ocorrido simultaneamente."
                )

        # --- CONEXÃO COM O SALDO ROTATIVO DO FIADO ---
        if forma_pagamento == 'FIADO':
            descricao_extrato = ", ".join(nomes_itens)
            # Salva o DÉBITO com data e descrição na conta do cliente
            sucesso_fiado, msg_fiado = fiado_ctrl.registrar_compra_fiado(
                cliente_id=cliente_id,
                valor=valor_total_venda_com_desconto,
                observacao=f"Compra: {descricao_extrato}",
                data_vencimento=dt_vencimento,
                session=session
            )
            if not sucesso_fiado:
                raise ValueError(msg_fiado)

    return True, "Venda finalizada e registrada no saldo rotativo com sucesso!"


def buscar_vendas_por_data(data_str: str) -> list[dict]:
    """Retorna o historico de vendas de um dia especifico.

    Args:
        data_str: Data no formato 'DD/MM/AAAA'.

    Returns:
        Lista de dicts com os campos de cada venda.
    """
    with get_session() as session:
        vendas = (
            session.query(Venda)
            .filter(Venda.data_venda.like(f'{data_str}%'))
            .order_by(Venda.id.desc())
            .limit(50)
            .all()
        )
        return [
            {
                'id':          v.id,
                'modelo_nome': v.modelo_nome,
                'marca':       v.marca,
                'cor':         v.cor,
                'tamanho':     v.tamanho,
                'quantidade':  v.quantidade,
                'valor_total': v.valor_total,
                'data_venda':  v.data_venda,
            }
            for v in vendas
        ]


def buscar_dados_dashboard(f_tipo="TODOS", f_marca="TODAS", f_tecido="TODOS", f_corte="TODOS", f_cor="TODAS") -> list[dict]:
    """Retorna todos os dados de vendas para o Dashboard (Pandas).

    Returns:
        Lista de dicts compativel com pd.DataFrame().
    """
    with get_session() as session:
        query = session.query(Venda).options(joinedload(Venda.variacao).joinedload(ProdutoVariacao.produto))

        if f_tipo != "TODOS":
            query = query.filter(Venda.modelo_nome == f_tipo)
        if f_marca != "TODAS":
            query = query.filter(Venda.marca == f_marca)
        if f_cor != "TODAS":
            query = query.filter(Venda.cor == f_cor)
            
        if f_tecido != "TODOS" or f_corte != "TODOS":
            query = query.join(ProdutoVariacao, Venda.variacao_id == ProdutoVariacao.id, isouter=True) \
                         .join(Produto, ProdutoVariacao.produto_id == Produto.id, isouter=True)
            if f_tecido != "TODOS":
                query = query.filter(Produto.tecido == f_tecido)
            if f_corte != "TODOS":
                query = query.filter(Produto.corte == f_corte)

        vendas = query.all()
        resultado = []
        for v in vendas:
            preco_custo = getattr(v, 'preco_custo', 0.0)
            if (not preco_custo or preco_custo == 0.0) and v.variacao and getattr(v.variacao, 'preco_custo', None):
                preco_custo = v.variacao.preco_custo
            
            tecido = 'Desconhecido'
            corte = 'Desconhecido'
            if v.variacao and v.variacao.produto:
                tecido = v.variacao.produto.tecido or 'Desconhecido'
                corte = v.variacao.produto.corte or 'Desconhecido'

            resultado.append({
                'id':          v.id,
                'valor_total': v.valor_total,
                'preco_custo': preco_custo,
                'quantidade':  v.quantidade,
                'marca':       v.marca or 'Desconhecido',
                'cor':         v.cor or 'Desconhecido',
                'tipo':        v.modelo_nome or 'Desconhecido',
                'tecido':      tecido,
                'corte':       corte,
                'data_venda':  v.data_venda,
            })
        return resultado



def buscar_dados_estoque_dashboard() -> list[dict]:
    """Retorna dados de estoque atual para o grafico de rosca.

    Returns:
        Lista de dicts compativel com pd.DataFrame().
    """
    with get_session() as session:
        variacoes = session.query(ProdutoVariacao).join(Produto).options(contains_eager(ProdutoVariacao.produto)).all()
        return [
            {
                'tipo':    v.produto.modelo_nome,
                'marca':   v.produto.marca,
                'tecido':  v.produto.tecido,
                'corte':   v.produto.corte,
                'cor':     v.cor,
                'estoque': v.estoque,
            }
            for v in variacoes
        ]
