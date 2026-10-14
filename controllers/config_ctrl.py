"""
config_ctrl.py — Controller de Atributos (Marcas, Cores, Tecidos, Cortes, Tipos de Peca)
Responsabilidade: toda a logica de negocio para gerenciar os atributos de configuracao.
A camada de View nunca acessa o banco diretamente — sempre passa por aqui.
"""

from database.conexao import get_session
from database.models import Atributo
from sqlalchemy.exc import IntegrityError


# Categorias validas (usadas para validacao interna)
CATEGORIAS_VALIDAS = {'marca', 'tipo_peca', 'tecido', 'corte', 'cor'}


def listar_atributos(categoria: str) -> list[dict]:
    """Retorna todos os atributos de uma categoria em ordem alfabetica.

    Args:
        categoria: Uma das categorias validas (ex: 'marca', 'cor').

    Returns:
        Lista de dicts: [{'id': int, 'nome': str}, ...]
    """
    with get_session() as session:
        itens = (
            session.query(Atributo.id, Atributo.nome)
            .filter(Atributo.categoria == categoria)
            .order_by(Atributo.nome)
            .all()
        )
        return [{'id': i.id, 'nome': i.nome} for i in itens]


def listar_nomes(categoria: str) -> list[str]:
    """Versao simplificada de listar_atributos que retorna apenas os nomes.
    Util para popular Comboboxes na interface.

    Args:
        categoria: Categoria do atributo.

    Returns:
        Lista de strings com os nomes em ordem alfabetica.
    """
    return [item['nome'] for item in listar_atributos(categoria)]


def adicionar_atributo(categoria: str, nome: str) -> tuple[bool, str]:
    """Adiciona um novo atributo ao banco de dados.

    Args:
        categoria: Categoria do atributo (ex: 'marca').
        nome: Nome do novo atributo.

    Returns:
        Tupla (sucesso: bool, mensagem: str).
    """
    nome = nome.strip()
    if not nome:
        return False, "O nome nao pode ser vazio."

    if categoria not in CATEGORIAS_VALIDAS:
        return False, f"Categoria invalida: '{categoria}'."

    # Verifica duplicata ignorando maiusculas/minusculas
    with get_session() as session:
        existente = (
            session.query(Atributo)
            .filter(
                Atributo.categoria == categoria,
                Atributo.nome.ilike(nome)
            )
            .first()
        )
        if existente:
            return False, f"'{nome}' ja esta cadastrado em '{categoria}'."

        novo = Atributo(categoria=categoria, nome=nome)
        session.add(novo)

    return True, f"'{nome}' adicionado com sucesso!"


def excluir_atributo(atributo_id: int) -> tuple[bool, str]:
    """Remove um atributo pelo ID.

    Args:
        atributo_id: ID do registro a ser excluido.

    Returns:
        Tupla (sucesso: bool, mensagem: str).
    """
    with get_session() as session:
        atributo = session.get(Atributo, atributo_id)
        if not atributo:
            return False, "Atributo nao encontrado."
        nome = atributo.nome
        session.delete(atributo)

    return True, f"'{nome}' removido com sucesso."


def popular_dados_padrao():
    """Insere os dados de fabrica se as tabelas de atributos estiverem vazias.
    Chamado automaticamente na inicializacao do sistema.
    """
    padroes = {
        'tipo_peca': ['Blusa', 'Calca', 'Casaco', 'Tenis', 'Vestido', 'Shorts'],
        'marca':     ['Nike', 'Adidas', 'Zara', "Levi's", 'H&M', 'Renner'],
        'tecido':    ['Algodao', 'Jeans', 'Poliester', 'Linho', 'Malha'],
        'corte':     ['Slim Fit', 'Oversized', 'Reto', 'Skinny', 'Regular'],
        'cor':       ['Preto', 'Branco', 'Azul Marinho', 'Cinza', 'Vermelho', 'Verde'],
    }
    with get_session() as session:
        existentes = session.query(Atributo.categoria).distinct().all()
        cats_existentes = {r[0] for r in existentes}
        
        for cat, nomes in padroes.items():
            if cat not in cats_existentes:
                for nome in nomes:
                    session.add(Atributo(categoria=cat, nome=nome))
    print("[Config] Dados padrao verificados.")

