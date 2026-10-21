"""
fiado_ctrl.py — Controller de Fiado (Contas a Receber) com Vencimento Fluido
"""

from datetime import datetime
from database.conexao import get_session
from database.models import Cliente, ContaFiado
from sqlalchemy.orm import joinedload


# ---------------------------------------------------------------------------
# HELPER — CÁLCULO UNIFICADO DE PERFIL (Amortização FIFO + Ranking)
# ---------------------------------------------------------------------------
def _calcular_perfil_cliente(cliente) -> dict:
    """Calcula saldo devedor, próximo vencimento, ranking e status de caixa
    de um cliente usando amortização FIFO.

    Args:
        cliente: Instância de Cliente com movimentacoes já carregadas (joinedload).

    Returns:
        Dict com: saldo_devedor, proximo_vencimento, ranking, status_tempo,
                  lote_urgente (ou None).
    """
    # 1. Calcula o Saldo Devedor Total (Débitos - Créditos)
    debitos = sum(m.valor for m in cliente.movimentacoes if m.tipo_movimentacao == 'DEBITO')
    creditos = sum(m.valor for m in cliente.movimentacoes if m.tipo_movimentacao == 'CREDITO')
    saldo_total = round(debitos - creditos, 2)

    # 2. Lógica de Amortização para achar o lote em aberto mais próximo de vencer
    pagamentos_acumulados = creditos
    lotes_compras = [m for m in cliente.movimentacoes if m.tipo_movimentacao == 'DEBITO']
    # Ordena as compras da mais antiga para a mais recente
    lotes_compras.sort(key=lambda m: m.data_movimentacao if m.data_movimentacao else datetime.min)

    proximo_vencimento = "Nenhum"
    status_caixa = "Conta Zerada / Em Dia"

    # Abate o saldo pago nos lotes antigos para ver qual lote ainda está pendente
    lote_urgente = None
    for lote in lotes_compras:
        if pagamentos_acumulados >= lote.valor:
            pagamentos_acumulados -= lote.valor
        else:
            # Este lote não foi totalmente pago, logo ele dita a urgência da conta
            lote_urgente = lote
            break

    # 3. Define o Ranking baseado no lote pendente mais urgente
    if saldo_total <= 0:
        ranking = "💎 DIAMANTE"
    else:
        if lote_urgente and hasattr(lote_urgente, 'data_vencimento_lote') and lote_urgente.data_vencimento_lote:
            dt_venc = lote_urgente.data_vencimento_lote
            proximo_vencimento = dt_venc.strftime('%d/%m/%Y')

            if dt_venc < datetime.now():
                dias_atraso_max = (datetime.now() - dt_venc).days
                status_caixa = f"⚠️ Vencido há {dias_atraso_max} dias"

                if dias_atraso_max <= 15:
                    ranking = "🥇 OURO"
                elif dias_atraso_max <= 45:
                    ranking = "🥈 PRATA"
                else:
                    ranking = "☠️ FERRO"
            else:
                ranking = "🥇 OURO"
                status_caixa = "No prazo (Pagador Fluido)"
        else:
            # Fallback caso não tenha data gravada
            ranking = "🥉 BRONZE"
            status_caixa = "Aguardando Acerto"

    return {
        'saldo_devedor': max(0.0, saldo_total),
        'proximo_vencimento': proximo_vencimento,
        'ranking': ranking,
        'status_tempo': status_caixa,
        'lote_urgente': lote_urgente,
    }


def _montar_dict_cliente(cliente, perfil: dict) -> dict:
    """Monta o dicionário padrão de retorno de um cliente com seu perfil calculado."""
    return {
        'id': cliente.id,
        'nome': cliente.nome,
        'telefone': cliente.telefone,
        'limite_credito': cliente.limite_credito,
        'saldo_devedor': perfil['saldo_devedor'],
        'proximo_vencimento': perfil['proximo_vencimento'],
        'ranking': perfil['ranking'],
        'status_tempo': perfil['status_tempo'],
        'dia_preferencial_pagamento': cliente.dia_preferencial_pagamento
    }


# ---------------------------------------------------------------------------
# CLIENTES & RANKINGS FLUIDOS
# ---------------------------------------------------------------------------
def listar_clientes(termo: str = '') -> list[dict]:
    """Retorna todos os clientes calculando o saldo, próximo vencimento e ranking."""
    with get_session() as session:
        query = session.query(Cliente).options(joinedload(Cliente.movimentacoes))
        if termo:
            query = query.filter(Cliente.nome.ilike(f'%{termo}%'))
        clientes = query.order_by(Cliente.nome).all()

        resultado = []
        for c in clientes:
            perfil = _calcular_perfil_cliente(c)
            resultado.append(_montar_dict_cliente(c, perfil))
            
        return sorted(resultado, key=lambda x: x['saldo_devedor'], reverse=True)


def buscar_nomes_clientes() -> list[str]:
    """Retorna lista de nomes para popular Combobox no PDV."""
    with get_session() as session:
        clientes = session.query(Cliente.nome).order_by(Cliente.nome).all()
        return [c[0] for c in clientes]


def buscar_cliente_por_nome(nome: str) -> dict | None:
    """Retorna os dados de um cliente pelo nome exato, calculando saldo, vencimento e ranking para evitar KeyErrors."""
    with get_session() as session:
        c = (
            session.query(Cliente)
            .options(joinedload(Cliente.movimentacoes))
            .filter(Cliente.nome == nome)
            .first()
        )
        if not c:
            return None
        
        perfil = _calcular_perfil_cliente(c)
        return _montar_dict_cliente(c, perfil)

def buscar_cliente_por_id(cliente_id: int) -> dict | None:
    """Retorna os dados de um cliente pelo ID, calculando saldo, vencimento e ranking para evitar KeyErrors."""
    with get_session() as session:
        c = (
            session.query(Cliente)
            .options(joinedload(Cliente.movimentacoes))
            .filter(Cliente.id == cliente_id)
            .first()
        )
        if not c:
            return None
        
        perfil = _calcular_perfil_cliente(c)
        return _montar_dict_cliente(c, perfil)


def adicionar_cliente(nome: str, telefone: str = '',
                      limite: float = 500.0, dia_preferencial: int = 5) -> tuple[bool, str]:
    """Cadastra um novo cliente."""
    nome = nome.strip()
    if not nome:
        return False, "O nome não pode ser vazio."

    with get_session() as session:
        existente = session.query(Cliente).filter(
            Cliente.nome.ilike(nome)
        ).first()
        if existente:
            return False, f"Cliente '{nome}' já cadastrado."

        session.add(Cliente(
            nome=nome,
            telefone=telefone.strip(),
            limite_credito=float(limite),
            dia_preferencial_pagamento=dia_preferencial
        ))
    return True, f"Cliente '{nome}' cadastrado com sucesso."


def atualizar_cliente(cliente_id: int, nome: str, telefone: str,
                      limite: float, dia_preferencial: int) -> tuple[bool, str]:
    """Atualiza os dados cadastrais de um cliente."""
    with get_session() as session:
        c = session.get(Cliente, cliente_id)
        if not c:
            return False, "Cliente nao encontrado."
        c.nome                       = nome.strip()
        c.telefone                   = telefone.strip()
        c.limite_credito             = float(limite)
        c.dia_preferencial_pagamento = dia_preferencial
    return True, "Dados atualizados."


def excluir_cliente(cliente_id: int) -> tuple[bool, str]:
    """Remove um cliente e todo o seu historico em cascata.
    So permite remover se o saldo for zero.
    """
    with get_session() as session:
        c = session.query(Cliente).options(
            joinedload(Cliente.movimentacoes)
        ).filter(Cliente.id == cliente_id).first()

        if not c:
            return False, "Cliente nao encontrado."

        if abs(c.saldo_devedor) > 0.01:
            return False, (
                f"Nao e possivel remover. "
                f"Cliente ainda deve ou possui saldo de R$ {c.saldo_devedor:.2f}."
            )

        session.delete(c)

    return True, "Cliente removido com sucesso."


# ---------------------------------------------------------------------------
# MOVIMENTAÇÕES COM DATA FLUIDA
# ---------------------------------------------------------------------------
def registrar_compra_fiado(cliente_id: int, valor: float,
                           observacao: str = '', data_vencimento: datetime = None,
                           session=None) -> tuple[bool, str]:
    """Lança um DÉBITO atrelando uma data de vencimento combinada para este lote."""
    if valor <= 0:
        return False, "O valor deve ser maior que zero."
    if not data_vencimento:
        data_vencimento = datetime.now() # Fallback de segurança

    if session is not None:
        return _executar_registro_compra_fiado(session, cliente_id, valor, observacao, data_vencimento)
    else:
        with get_session() as session_ativa:
            return _executar_registro_compra_fiado(session_ativa, cliente_id, valor, observacao, data_vencimento)


def _executar_registro_compra_fiado(session, cliente_id, valor, observacao, data_vencimento):
    c = session.query(Cliente).options(
        joinedload(Cliente.movimentacoes)
    ).filter(Cliente.id == cliente_id).first()

    if not c:
        return False, "Cliente nao encontrado."

    nova_divida = c.saldo_devedor + valor
    if nova_divida > c.limite_credito:
        return False, (
            f"Limite de credito excedido!\n"
            f"Saldo atual: R$ {c.saldo_devedor:.2f} | "
            f"Limite: R$ {c.limite_credito:.2f}\n"
            f"Esta compra de R$ {valor:.2f} ultrapassaria o limite."
        )

    novo_debito = ContaFiado(
        cliente_id=cliente_id,
        tipo_movimentacao='DEBITO',
        valor=valor,
        data_movimentacao=datetime.now(),
        data_vencimento_lote=data_vencimento, # Salvando a data combinada na boca com o cliente
        descricao=observacao or f'Compra fiada em {datetime.now().strftime("%d/%m/%Y %H:%M")}',
    )
    session.add(novo_debito)
    nome_cliente = c.nome

    return True, f"Compra de R$ {valor:.2f} lançada no fiado de '{nome_cliente}'."


def registrar_pagamento(cliente_id: int, valor: float,
                        observacao: str = '') -> tuple[bool, str]:
    """Lança um CRÉDITO na conta corrente para abater os lotes antigos."""
    if valor <= 0:
        return False, "O valor deve ser maior que zero."

    with get_session() as session:
        c = session.query(Cliente).options(
            joinedload(Cliente.movimentacoes)
        ).filter(Cliente.id == cliente_id).first()

        if not c:
            return False, "Cliente nao encontrado."

        valor_original = None
        if valor > c.saldo_devedor:
            if c.saldo_devedor <= 0:
                return False, f"'{c.nome}' nao possui divida em aberto."
            valor_original = valor
            valor = c.saldo_devedor  # Trava no saldo atual

        novo_credito = ContaFiado(
            cliente_id=cliente_id,
            tipo_movimentacao='CREDITO',
            valor=valor,
            data_movimentacao=datetime.now(),
            descricao=observacao or "Pagamento de Fiado Recorrente"
        )
        session.add(novo_credito)
        nome = c.nome

    if valor_original is not None:
        return True, f"Pagamento de R$ {valor:.2f} registrado (valor ajustado de R$ {valor_original:.2f})."
    return True, f"Pagamento de R$ {valor:.2f} registrado para '{nome}'."


def buscar_extrato(cliente_id: int) -> list[dict]:
    """Retorna o extrato completo de movimentações de um cliente, incluindo o vencimento fluido
    e o status FIFO de cada lote de compra (PAGO, ATRASADO, HOJE, ABERTO).
    """
    with get_session() as session:
        movs = (
            session.query(ContaFiado)
            .filter(ContaFiado.cliente_id == cliente_id)
            .order_by(ContaFiado.data_movimentacao.desc(), ContaFiado.id.desc())
            .all()
        )
        # Calcula amortização FIFO das compras (da mais antiga para a mais nova)
        creditos_disp = sum(m.valor for m in movs if m.tipo_movimentacao == 'CREDITO')
        debitos_cron = sorted(
            [m for m in movs if m.tipo_movimentacao == 'DEBITO'],
            key=lambda x: (x.data_movimentacao or datetime.min, x.id or 0),
        )
        status_por_id: dict[int, tuple[str, float]] = {}
        hoje_dt = datetime.now()
        hoje_date = hoje_dt.date()

        for d in debitos_cron:
            if creditos_disp >= d.valor - 0.009:
                creditos_disp -= d.valor
                status_por_id[d.id] = ("PAGO", 0.0)
            else:
                restante_lote = round(d.valor - max(0.0, creditos_disp), 2)
                creditos_disp = 0.0
                if d.data_vencimento_lote:
                    venc_date = d.data_vencimento_lote.date()
                    if venc_date < hoje_date:
                        status_por_id[d.id] = ("ATRASADO", restante_lote)
                    elif venc_date == hoje_date:
                        status_por_id[d.id] = ("HOJE", restante_lote)
                    else:
                        status_por_id[d.id] = ("ABERTO", restante_lote)
                else:
                    status_por_id[d.id] = ("ABERTO", restante_lote)

        resultado = []
        for m in movs:
            venc_str = "—"
            if m.tipo_movimentacao == 'DEBITO' and m.data_vencimento_lote:
                venc_str = m.data_vencimento_lote.strftime('%d/%m/%Y')

            st_lote, rest_lote = status_por_id.get(m.id, ("CREDITO", 0.0))
            resultado.append({
                'id':              m.id,
                'tipo':            m.tipo_movimentacao,
                'valor':           m.valor,
                'data':            m.data_movimentacao.strftime('%d/%m/%Y %H:%M') if m.data_movimentacao else '',
                'vencimento_lote': venc_str,
                'obs':             m.descricao or '',
                'status_lote':     st_lote,
                'restante_lote':   rest_lote,
            })
        return resultado


def resumo_fiado() -> dict:
    """Retorna numeros consolidados para o header da tela de fiado."""
    from sqlalchemy import func, text
    with get_session() as session:
        total_clientes = session.query(func.count(Cliente.id)).scalar() or 0
        
        query = session.execute(text("""
            SELECT cliente_id,
                   SUM(CASE WHEN tipo_movimentacao = 'DEBITO' THEN valor ELSE 0 END) - 
                   SUM(CASE WHEN tipo_movimentacao = 'CREDITO' THEN valor ELSE 0 END) as saldo
            FROM conta_fiado
            GROUP BY cliente_id
            HAVING saldo > 0
        """))
        saldos = query.fetchall()
        
        total_aberto = sum(row.saldo for row in saldos)
        total_devedores = len(saldos)

        return {
            'total_clientes':   total_clientes,
            'total_em_aberto':  round(total_aberto, 2),
            'clientes_devedores': total_devedores,
        }


def listar_clientes_acerto_hoje() -> list[dict]:
    """
    Varre o banco procurando clientes com saldo devedor > 0 cujo lote pendente
    vence HOJE ou já está VENCIDO (atrasado), além de clientes cujo dia preferencial é hoje.
    Ordena priorizando os mais atrasados primeiro.
    """
    hoje_dt   = datetime.now()
    hoje_date = hoje_dt.date()
    hoje_dia  = hoje_dt.day

    with get_session() as session:
        clientes = (
            session.query(Cliente)
            .options(joinedload(Cliente.movimentacoes))
            .all()
        )

        lista_retorno = []
        for c in clientes:
            perfil = _calcular_perfil_cliente(c)
            saldo  = perfil['saldo_devedor']
            if saldo <= 0:
                continue

            lote = perfil['lote_urgente']
            urgencia = None
            dias_atraso = 0

            if lote and getattr(lote, 'data_vencimento_lote', None):
                venc_date = lote.data_vencimento_lote.date()
                if venc_date < hoje_date:
                    urgencia = "ATRASADO"
                    dias_atraso = (hoje_date - venc_date).days
                elif venc_date == hoje_date:
                    urgencia = "HOJE"
            elif c.dia_preferencial_pagamento == hoje_dia:
                urgencia = "HOJE"

            if urgencia:
                lista_retorno.append({
                    "id": c.id,
                    "nome": c.nome,
                    "telefone": c.telefone or "",
                    "limite_credito": c.limite_credito,
                    "saldo_devedor": saldo,
                    "proximo_vencimento": perfil['proximo_vencimento'],
                    "ranking": perfil['ranking'],
                    "status_tempo": perfil['status_tempo'],
                    "urgencia": urgencia,
                    "dias_atraso": dias_atraso,
                    "dia_preferencial_pagamento": (
                        lote.data_vencimento_lote.day
                        if (lote and getattr(lote, 'data_vencimento_lote', None))
                        else c.dia_preferencial_pagamento
                    ),
                })

        lista_retorno.sort(key=lambda x: (0 if x["urgencia"] == "ATRASADO" else 1, -x["dias_atraso"], -x["saldo_devedor"]))
        return lista_retorno
