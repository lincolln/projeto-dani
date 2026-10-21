"""
script_backup_pendrive.py — Exportação Total de Dados para Unidade Removível (Pendrive)
Sistema Kanemberg Multimarcas

Funcionalidades:
  • Localiza automaticamente todos os discos removíveis conectados ao Windows (Pendrives, HDs Externos).
  • Se houver mais de um, seleciona o primeiro disponível.
  • Cria a pasta "Backup_Kanemberg_Data_[DATA]_[HORA]" na raiz do Pendrive.
  • Copia 100% da pasta "imagens_produtos" e o banco de dados SQLite "loja_daniel_v2.db".
  • Exibe uma interface gráfica simples de aviso (messagebox) para o Daniel saber que concluiu.
"""

import os
import sys
import sqlite3
import shutil
import ctypes
from datetime import datetime
from tkinter import messagebox
import tkinter as tk

# Constantes de Origem
_RAIZ_SISTEMA = (os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__)))
_ARQUIVO_DB   = os.path.join(_RAIZ_SISTEMA, "loja_daniel_v2.db")
_DIR_IMAGENS  = os.path.join(_RAIZ_SISTEMA, "imagens_produtos")


def _obter_root_tk():
    """Cria e esconde uma janela Tk temporária para usar com messagebox."""
    root = tk.Tk()
    root.withdraw()
    return root


def obter_unidades_removiveis() -> list[str]:
    """
    Usa a API nativa do Windows (GetDriveTypeW) para listar todas as letras de
    drive conectadas que sejam do tipo DRIVE_REMOVABLE (ex: Pendrives).
    Retorna uma lista de strings, ex: ['E:\\', 'F:\\'].
    """
    drives_removiveis = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    
    for letra_int in range(26):
        if bitmask & (1 << letra_int):
            letra_str = chr(65 + letra_int) + ":\\"
            # 2 = DRIVE_REMOVABLE (Pendrive / Cartão SD)
            tipo_drive = ctypes.windll.kernel32.GetDriveTypeW(letra_str)
            if tipo_drive == 2:
                drives_removiveis.append(letra_str)
                
    return drives_removiveis


def executar_backup_pendrive():
    root = _obter_root_tk()
    try:
        print("[Backup Pendrive] Procurando unidades removíveis...")
        unidades = obter_unidades_removiveis()
        
        if not unidades:
            msg = "Nenhum Pendrive ou HD Externo detectado.\nConecte um dispositivo e tente novamente."
            print(f"[Erro] {msg}")
            messagebox.showerror("Backup Kanemberg", msg)
            return

        # Pega o primeiro pendrive encontrado (ex: "E:\")
        pendrive = unidades[0]
        print(f"[Backup Pendrive] Dispositivo detectado na unidade: {pendrive}")

        # Monta a pasta de destino com data e hora exatas
        timestamp = datetime.now().strftime("%d_%m_%Y__%H_%M")
        pasta_destino_raiz = os.path.join(pendrive, f"Backup_Kanemberg_Data_{timestamp}")
        
        try:
            # Cria a pasta raiz no pendrive
            os.makedirs(pasta_destino_raiz, exist_ok=True)
            
            # 1. Copia o Banco de Dados via API segura do SQLite (backup atômico)
            if os.path.exists(_ARQUIVO_DB):
                destino_db = os.path.join(pasta_destino_raiz, "loja_daniel_v2.db")
                origem = sqlite3.connect(_ARQUIVO_DB)
                destino_conn = sqlite3.connect(destino_db)
                try:
                    origem.backup(destino_conn)
                finally:
                    destino_conn.close()
                    origem.close()
                print(f"[Backup Pendrive] Banco de dados copiado com sucesso.")
            
            # 2. Copia a pasta de Imagens dos Produtos (se existir e tiver arquivos)
            if os.path.exists(_DIR_IMAGENS):
                destino_img = os.path.join(pasta_destino_raiz, "imagens_produtos")
                # shutil.copytree cria a pasta de destino automaticamente e copia tudo recursivamente
                shutil.copytree(_DIR_IMAGENS, destino_img, dirs_exist_ok=True)
                print(f"[Backup Pendrive] Galeria de imagens copiada com sucesso.")

            msg = f"Backup concluído com sucesso!\n\nDestino: {pasta_destino_raiz}\n\nVocê já pode remover o Pendrive com segurança."
            print(f"[Sucesso] {msg}")
            messagebox.showinfo("Backup Kanemberg", msg)

        except Exception as e:
            msg = f"Falha ao realizar o backup no Pendrive:\n\n{str(e)}"
            print(f"[Erro] {msg}")
            messagebox.showerror("Erro de Backup", msg)
    finally:
        root.destroy()


if __name__ == "__main__":
    executar_backup_pendrive()
