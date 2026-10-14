import sqlite3, os, sys

_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

# Cria tabelas novas via SQLAlchemy (clientes, conta_fiado, vendas, etc)
from database.conexao import inicializar_banco
inicializar_banco()
print('OK: tabelas clientes e conta_fiado criadas (se nao existiam)')

db = os.path.join(_root, 'loja_daniel_v2.db')
conn = sqlite3.connect(db)
cur = conn.cursor()

# Verifica e adiciona coluna forma_pagamento em vendas
cur.execute('PRAGMA table_info(vendas)')
cols = [r[1] for r in cur.fetchall()]
print('Colunas em vendas:', cols)

if 'forma_pagamento' not in cols:
    cur.execute("ALTER TABLE vendas ADD COLUMN forma_pagamento TEXT DEFAULT 'DINHEIRO'")
    print('OK: forma_pagamento adicionada')

conn.commit()
conn.close()


# Testa o controller de fiado
from controllers import fiado_ctrl
clientes = fiado_ctrl.listar_clientes()
print(f'Clientes cadastrados: {len(clientes)}')

resumo = fiado_ctrl.resumo_fiado()
print(f'Resumo: {resumo}')

# Testa geração de QR Code e etiqueta
from controllers import estoque_ctrl
from utils_impressao import gerar_etiqueta, gerar_qrcode_preview

preview_img = gerar_qrcode_preview('KNB000010001')
assert preview_img is not None
print('OK: preview do QR Code gerado com sucesso')

etiqueta_path = gerar_etiqueta('KNB000010001', 'Produto Teste QR', 'M', 89.90, quantidade=1)
assert etiqueta_path and os.path.exists(etiqueta_path)
print(f'OK: etiqueta com QR Code gerada em {etiqueta_path}')

# Testa busca por código inteligente
res_busca = estoque_ctrl.buscar_por_codigo('KNB000010001')
print(f'OK: buscar_por_codigo executado com sucesso (resultado: {res_busca is not None})')

print('TODOS OS TESTES PASSARAM!')
