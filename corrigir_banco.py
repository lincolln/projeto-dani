import sqlite3
import os

def consertar_tabela_fiado_para_banco(nome_banco):
    if not os.path.exists(nome_banco):
        print(f"[Info] Banco '{nome_banco}' nao encontrado. Pulando...")
        return

    print(f"[DB Patch] Iniciando correcao na tabela conta_fiado do banco '{nome_banco}'...")
    conn = sqlite3.connect(nome_banco)
    cursor = conn.cursor()
    
    try:
        # Verifica se a tabela conta_fiado existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conta_fiado';")
        if not cursor.fetchone():
            print(f"[Info] Tabela 'conta_fiado' nao encontrada no banco '{nome_banco}'. Pulando...")
            return

        # Verifica quais colunas realmente existem na tabela conta_fiado hoje
        cursor.execute("PRAGMA table_info(conta_fiado)")
        colunas = [col[1] for col in cursor.fetchall()]
        
        # Se a coluna tipo_movimentacao não existir, nós criamos ela
        if "tipo_movimentacao" not in colunas:
            cursor.execute("ALTER TABLE conta_fiado ADD COLUMN tipo_movimentacao TEXT;")
            print(" -> Coluna 'tipo_movimentacao' criada com sucesso!")
            
        # Se a coluna antiga 'tipo' existia e tinha dados, migra os dados para a nova
        if "tipo" in colunas:
            cursor.execute("UPDATE conta_fiado SET tipo_movimentacao = tipo WHERE tipo_movimentacao IS NULL;")
            print(" -> Dados antigos de 'tipo' copiados para 'tipo_movimentacao'.")

        # Se a coluna antiga 'observacao' existia, cria 'descricao' e migra
        if "descricao" not in colunas:
            cursor.execute("ALTER TABLE conta_fiado ADD COLUMN descricao TEXT;")
            print(" -> Coluna 'descricao' criada com sucesso!")
            
        if "observacao" in colunas:
            cursor.execute("UPDATE conta_fiado SET descricao = observacao WHERE descricao IS NULL;")
            print(" -> Dados antigos de 'observacao' copiados para 'descricao'.")
            
        conn.commit()
        print(f"[OK] Banco de dados '{nome_banco}' ajustado perfeitamente com os novos controladores!")
        
    except Exception as e:
        print(f"[Erro] Falha ao corrigir o banco '{nome_banco}': {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    # Corrige os bancos de dados que possam existir no projeto
    consertar_tabela_fiado_para_banco("sistema_loja.db")
    consertar_tabela_fiado_para_banco("loja_daniel_v2.db")
