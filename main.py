"""
main.py — Ponto de entrada do Sistema Kanemberg v2
Inicializa o banco de dados, dispara backup de segurança e lança a interface.
"""

import sys
import os

# Garante que o diretório raiz do projeto esteja no path do Python
_PROJETO_DIR = os.path.dirname(os.path.abspath(__file__))
if _PROJETO_DIR not in sys.path:
    sys.path.insert(0, _PROJETO_DIR)


def inicializar():
    """Inicializa o banco, faz backup de segurança e lança a janela principal."""
    from database.conexao import inicializar_banco
    from controllers.config_ctrl import popular_dados_padrao
    from backup import disparar_backup

    print("[Sistema] Iniciando Sistema Kanemberg v2...")

    # ① Cria as tabelas (se não existirem) e aplica migrações
    inicializar_banco()

    # ② Insere dados de fábrica nas categorias vazias
    popular_dados_padrao()

    # ③ Backup de segurança na INICIALIZAÇÃO — roda em thread separada,
    #    nunca atrasa a abertura da janela para o Daniel
    disparar_backup(motivo="inicialização")

    # ④ Lança a interface gráfica
    from views.tela_principal import TelaPrincipal
    app = TelaPrincipal()
    app.mainloop()

    # ⑤ Backup de segurança no ENCERRAMENTO LIMPO — disparado após
    #    app.mainloop() retornar, quando a janela já está fechada.
    #    Thread não é daemon, precisamos aguardar para garantir o backup.
    t_backup = disparar_backup(motivo="encerramento")
    if t_backup:
        t_backup.join(timeout=10)
    print("[Sistema] Encerramento limpo concluído.")


if __name__ == "__main__":
    inicializar()
