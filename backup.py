"""
backup.py — Motor de Backup Automático de Segurança
Sistema Kanemberg Multimarcas

Funcionamento:
  • Copia o banco SQLite para a pasta  <raiz>/backups_kanemberg/
  • Nome do arquivo: backup_kanemberg_DD_MM_AAAA_HHMM.db
  • Mantém apenas os 5 backups mais recentes (rotação automática)
  • Executa em Thread daemon — nunca atrasa a abertura nem o fechamento
    visível da janela (o processo principal não espera por ele)

Uso:
    from backup import disparar_backup
    disparar_backup()           # dispara e retorna imediatamente
"""

import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

# ── Configurações centrais ───────────────────────────────────────────────────
_RAIZ           = os.path.dirname(os.path.abspath(__file__))
_ARQUIVO_DB     = os.path.join(_RAIZ, "loja_daniel_v2.db")
_PASTA_BACKUPS  = os.path.join(_RAIZ, "backups_kanemberg")
_MAX_BACKUPS    = 5            # número máximo de cópias mantidas
_PREFIXO        = "backup_kanemberg_"


# ── Função principal (executada na thread) ───────────────────────────────────

def executar_backup_seguranca() -> None:
    """
    Realiza a cópia de segurança do banco de dados SQLite.

    Etapas:
      1. Verifica se o arquivo de banco existe (proteção contra execução
         antes da primeira inicialização).
      2. Garante que a pasta backups_kanemberg/ exista.
      3. Copia o .db com nome datado (DD_MM_AAAA_HHMM).
      4. Lista todos os backups existentes e remove os mais antigos,
         mantendo apenas _MAX_BACKUPS.

    Esta função NÃO levanta exceções — todos os erros são absorvidos e
    impressos no console para não interferir no mainloop do Tkinter.
    """
    try:
        # ① Banco inexistente — nada a fazer ainda
        if not os.path.exists(_ARQUIVO_DB):
            print("[Backup] Banco de dados não encontrado. Backup ignorado.")
            return

        # ② Garante que a pasta de destino exista
        os.makedirs(_PASTA_BACKUPS, exist_ok=True)

        # ── VERIFICAÇÃO DE DELTA ─────────────────────────────────────────────
        mtime_db = os.path.getmtime(_ARQUIVO_DB)
        ultimo_backup_mtime = 0.0
        pasta_path = Path(_PASTA_BACKUPS)
        arquivos_bkp = list(pasta_path.glob(f"{_PREFIXO}*.db"))
        
        if arquivos_bkp:
            # Cache do mtime para encontrar o mais recente
            arquivos_com_mtime = [(f, f.stat().st_mtime) for f in arquivos_bkp if f.is_file()]
            if arquivos_com_mtime:
                ultimo_backup_mtime = max(arquivos_com_mtime, key=lambda item: item[1])[1]
                
        if mtime_db <= ultimo_backup_mtime:
            print("[Backup] Banco de dados inalterado desde o último backup. Ignorado.")
            return

        # ③ Gera o nome com data e hora exata
        timestamp   = datetime.now().strftime("%d_%m_%Y_%H%M")
        nome_backup = f"{_PREFIXO}{timestamp}.db"
        destino     = os.path.join(_PASTA_BACKUPS, nome_backup)

        # Copia via API nativa do SQLite (backup atômico e seguro, mesmo com o banco em uso)
        origem = None
        destino_conn = None
        try:
            origem = sqlite3.connect(_ARQUIVO_DB)
            destino_conn = sqlite3.connect(destino)
            origem.backup(destino_conn)
        finally:
            if destino_conn:
                destino_conn.close()
            if origem:
                origem.close()
        tamanho_kb = os.path.getsize(destino) / 1024
        print(f"[Backup] Cópia criada: {nome_backup}  ({tamanho_kb:.1f} KB)")

        # ④ Rotação: mantém apenas os _MAX_BACKUPS mais recentes
        _rotacionar_backups()

    except Exception as erro:
        # Absorve silenciosamente para não travar o mainloop
        print(f"[Backup] AVISO - Erro durante o backup: {erro}")


def _rotacionar_backups() -> None:
    """
    Lista todos os arquivos de backup na pasta, ordena por data de modificação
    (mais antigo primeiro) e remove os excedentes acima de _MAX_BACKUPS.
    """
    try:
        pasta = Path(_PASTA_BACKUPS)

        # Filtra apenas os arquivos gerados por este sistema
        arquivos = [f for f in pasta.glob(f"{_PREFIXO}*.db") if f.is_file()]
        
        # Cache do mtime para ordenação
        arquivos_com_mtime = [(f, f.stat().st_mtime) for f in arquivos]
        arquivos_com_mtime.sort(key=lambda item: item[1])
        arquivos_ordenados = [f for f, mtime in arquivos_com_mtime]

        excedentes = arquivos_ordenados[: max(0, len(arquivos_ordenados) - _MAX_BACKUPS)]
        for arquivo in excedentes:
            arquivo.unlink(missing_ok=True)
            print(f"[Backup] Backup antigo removido: {arquivo.name}")

        if excedentes:
            print(f"[Backup] {len(arquivos_ordenados) - len(excedentes)} backup(s) mantido(s) de {_MAX_BACKUPS} permitido(s).")

    except Exception as erro:
        print(f"[Backup] AVISO - Erro na rotação: {erro}")


# ── Disparo em thread daemon ─────────────────────────────────────────────────

def disparar_backup(motivo: str = "automático") -> None:
    """
    Lança executar_backup_seguranca() em uma Thread e retorna
    imediatamente ao chamador — nunca bloqueia a UI.

    Args:
        motivo: Rótulo para o log (ex: "inicialização", "encerramento").
    """
    print(f"[Backup] Iniciando backup de {motivo} em background...")
    t = threading.Thread(
        target=executar_backup_seguranca,
        name=f"BackupThread-{motivo}",
        daemon=False,   # encerra junto com o processo principal sem bloquear, mas espera concluir
    )
    t.start()
    return t
