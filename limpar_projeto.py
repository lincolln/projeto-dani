import os
import shutil

def limpar_projeto():
    # Caminho do projeto baseado onde o script está sendo executado
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    print(f"[*] Iniciando limpeza profunda em: {diretorio_atual}\n")

    # 1. LISTA DE PRESERVAÇÃO (O que MANDATORIAMENTE fica na Versão 2.0)
    arquivos_v2_permitidos = [
        "main.py",                  # Ponto de entrada unificado v2
        "main.spec",                # Configuração do PyInstaller
        "Kanemberg_v2.spec",        # Configuração do PyInstaller (alternativa)
        "migrate.py",               # Script de migração de dados
        "test_integracao.py",       # Testes de validação v2
        "loja_daniel_v2.db",        # Banco de dados v2 (Importante preservar!)
        "logo_kanemberg.png",       # Logo principal Kanemberg
        "_temp_logo.ico",           # Ícone temporário da janela
        "temp_logo.ico",            # Ícone temporário da janela (alt)
        "utils_cores.py",           # Utilitário de resolução de cores
        "utils_impressao.py",       # Utilitário de impressão de etiquetas
        "backup.py",                # Motor de backup automático
        "corrigir_banco.py",        # Script de correção do banco
        "script_backup_pendrive.py",# Backup para pendrive
        "task.md",                  # Notas de tarefas
    ]
    
    pastas_v2_permitidas = [
        "database",             # Modelos SQLAlchemy e conexão
        "controllers",          # Lógica de negócio (Estoque, Fiado, Dash)
        "views",                # Telas do sistema
        "imagens_produtos",     # Imagens físicas das roupas do Daniel
        "backups_kanemberg",    # Pasta de backups automáticos
    ]

    # 2. VARREDURA E DELEÇÃO DE ARQUIVOS AVULSOS DA V1
    for item in os.listdir(diretorio_atual):
        caminho_item = os.path.join(diretorio_atual, item)
        
        # Ignora o próprio script de limpeza para ele não se auto-deletar
        if item == "limpar_projeto.py":
            continue

        # Se for um arquivo solto na raiz
        if os.path.isfile(caminho_item):
            if item not in arquivos_v2_permitidos:
                try:
                    os.remove(caminho_item)
                    print(f"[-] Arquivo legado removido: {item}")
                except Exception as e:
                    print(f"[!] Nao foi possivel remover o arquivo {item}: {e}")

        # Se for uma pasta
        elif os.path.isdir(caminho_item):
            # Remove lixos de compilação automáticos do Python e PyInstaller
            if item in ["__pycache__", "build", "dist"] or item.endswith(".egg-info"):
                try:
                    shutil.rmtree(caminho_item)
                    print(f"[-] Pasta de cache eliminada: {item}")
                except Exception as e:
                    print(f"[!] Falha ao limpar cache {item}: {e}")
            
            # Se for uma pasta que não pertence ao escopo da V2
            elif item not in pastas_v2_permitidas:
                try:
                    shutil.rmtree(caminho_item)
                    print(f"[-] Diretorio legado v1 removido: {item}")
                except Exception as e:
                    print(f"[!] Nao foi possivel remover a pasta {item}: {e}")

    print("\n[+] Limpeza concluida! A estrutura esta 100% limpa para a Versao 2.0.")

if __name__ == "__main__":
    # Confirmação de segurança para evitar acidentes
    try:
        confirmar = input("Deseja apagar os arquivos que nao pertencem a V2.0? (sim/nao): ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        confirmar = "nao"
        
    if confirmar == "sim":
        limpar_projeto()
    else:
        print("Operacao cancelada pelo usuario.")
