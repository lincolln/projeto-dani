from sqlalchemy import Column, Integer, String, Float, Numeric, ForeignKey, Text, DateTime
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


# ---------------------------------------------------------------------------
# TABELA DE CONFIGURACOES UNIFICADA
# ---------------------------------------------------------------------------
class Atributo(Base):
    __tablename__ = 'atributos'

    id        = Column(Integer, primary_key=True, autoincrement=True)
    categoria = Column(String(50), nullable=False, index=True)
    nome      = Column(String(100), nullable=False)

    def __repr__(self):
        return f"<Atributo {self.categoria}='{self.nome}'>"


# ---------------------------------------------------------------------------
# PRODUTO — TABELA MESTRE
# ---------------------------------------------------------------------------
class Produto(Base):
    __tablename__ = 'produtos'

    id          = Column(Integer, primary_key=True, autoincrement=True)
    modelo_nome = Column(String(150), nullable=False)
    marca       = Column(String(100), default='')
    tecido      = Column(String(100), default='')
    corte       = Column(String(100), default='')
    cores_tags  = Column(String(500), default='')  # Tags visuais de cores (ex: "Preto|#000000,Branco|#FFFFFF")

    variacoes = relationship(
        'ProdutoVariacao',
        back_populates='produto',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f"<Produto id={self.id} modelo='{self.modelo_nome}'>"


# ---------------------------------------------------------------------------
# PRODUTO VARIACAO — TABELA DETALHE (SKU)
# ---------------------------------------------------------------------------
class ProdutoVariacao(Base):
    __tablename__ = 'produto_variacoes'

    id             = Column(Integer, primary_key=True, autoincrement=True)
    produto_id     = Column(Integer, ForeignKey('produtos.id'), nullable=False, index=True)

    tamanho        = Column(String(20),  nullable=False, default='M')
    cor            = Column(String(50),  nullable=False, default='')
    # Hexadecimal da cor (ex: '#FFD700') para pintar os círculos do Card Vertical
    cor_hex        = Column(String(10),  nullable=True,  default='')
    # Código de barras individual desta variação (EAN-13 ou personalizado)
    codigo_barras  = Column(String(30),  nullable=True,  default='', index=True)
    estoque        = Column(Integer,     default=0)
    preco_custo    = Column(Numeric(10, 2, asdecimal=False), default=0.0)
    preco_venda    = Column(Numeric(10, 2, asdecimal=False), default=0.0)
    foto_path      = Column(String(300), nullable=True)

    produto = relationship('Produto', back_populates='variacoes')
    vendas  = relationship('Venda',   back_populates='variacao', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<ProdutoVariacao id={self.id} tam={self.tamanho} cor='{self.cor}' hex='{self.cor_hex}'>"


# ---------------------------------------------------------------------------
# VENDA — HISTORICO DE TRANSACOES
# ---------------------------------------------------------------------------
class Venda(Base):
    __tablename__ = 'vendas'

    id             = Column(Integer, primary_key=True, autoincrement=True)
    variacao_id    = Column(Integer, ForeignKey('produto_variacoes.id'), nullable=True, index=True)

    # Campos desnormalizados para preservar historico mesmo se o produto for deletado
    modelo_nome    = Column(String(150), default='')
    marca          = Column(String(100), default='')
    cor            = Column(String(50),  default='')
    tamanho        = Column(String(20),  default='')

    quantidade     = Column(Integer,        default=1)
    valor_unitario = Column(Numeric(10, 2, asdecimal=False), default=0.0)
    valor_total    = Column(Numeric(10, 2, asdecimal=False), default=0.0)
    preco_custo    = Column(Numeric(10, 2, asdecimal=False), default=0.0)
    data_venda     = Column(String(30), nullable=False, index=True)

    # Forma de pagamento: 'DINHEIRO', 'PIX', 'CARTAO', 'FIADO'
    forma_pagamento = Column(String(20), default='DINHEIRO')

    variacao = relationship('ProdutoVariacao', back_populates='vendas')

    def __repr__(self):
        return f"<Venda id={self.id} total=R${self.valor_total:.2f} data='{self.data_venda}'>"


# ---------------------------------------------------------------------------
# CLIENTE — CADASTRO DE CLIENTES
# ---------------------------------------------------------------------------
class Cliente(Base):
    __tablename__ = 'clientes'

    id             = Column(Integer, primary_key=True, autoincrement=True)
    nome           = Column(String(150), nullable=False, unique=True)
    telefone       = Column(String(20),  default='')
    limite_credito = Column(Numeric(10, 2, asdecimal=False), default=500.0)  # Teto maximo de fiado permitido
    # ATIVADO: Guarda o dia do mês que o cliente prefere acertar (ex: 5, 10, 20)
    dia_preferencial_pagamento = Column(Integer, nullable=True, default=5)

    # Conta corrente do cliente (debitos e creditos)
    movimentacoes = relationship(
        'ContaFiado',
        back_populates='cliente',
        cascade='all, delete-orphan',
        order_by='ContaFiado.data_movimentacao'
    )

    @property
    def saldo_devedor(self) -> float:
        """Calcula o saldo liquido: soma dos debitos menos soma dos creditos."""
        debitos  = sum(h.valor for h in self.movimentacoes if h.tipo_movimentacao == 'DEBITO')
        creditos = sum(h.valor for h in self.movimentacoes if h.tipo_movimentacao == 'CREDITO')
        return round(debitos - creditos, 2)

    def __repr__(self):
        return f"<Cliente id={self.id} nome='{self.nome}' saldo=R${self.saldo_devedor:.2f}>"


# ---------------------------------------------------------------------------
# CONTA FIADO — EXTRATO DE DEBITOS E PAGAMENTOS
# Cada linha e uma movimentacao financeira do cliente:
#   tipo_movimentacao='DEBITO'  -> ele comprou fiado (deve mais)
#   tipo_movimentacao='CREDITO' -> ele veio pagar (abate a divida)
# ---------------------------------------------------------------------------
class ContaFiado(Base):
    __tablename__ = 'conta_fiado'

    id                = Column(Integer, primary_key=True, autoincrement=True)
    cliente_id        = Column(Integer, ForeignKey('clientes.id'), nullable=False, index=True)

    tipo_movimentacao = Column(String(10), nullable=False)   # 'DEBITO' | 'CREDITO'
    valor             = Column(Numeric(10, 2, asdecimal=False), nullable=False)
    data_movimentacao = Column(DateTime, default=datetime.now, index=True)
    data_vencimento_lote = Column(DateTime, nullable=True, index=True)   # Vencimento acordado para o lote de compra
    descricao         = Column(String(255), default='')      # Ex: "Venda #42" ou "Pago em dinheiro"

    cliente = relationship('Cliente', back_populates='movimentacoes')

    def __repr__(self):
        return f"<ContaFiado {self.tipo_movimentacao} R${self.valor:.2f}>"
