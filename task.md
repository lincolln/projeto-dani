# Refatoração da Regra de Negócio: Edição de Produtos e Desacoplamento de Cores

- [x] Atualizar `models.py` (Adicionar `cores_tags` na tabela `Produto`)
- [x] Atualizar `conexao.py` (Adicionar script de migração para `cores_tags`)
- [x] Atualizar `estoque_ctrl.py`
  - [x] `salvar_grade_dinamica` (Remover produto cartesiano, implementar Soft-Update)
  - [x] `buscar_produto_completo` (Ler cores_tags do pai)
  - [x] `listar_produtos_vitrine_grade` (Ler cores_tags do pai)
- [x] Atualizar `tela_cadastro.py` (Ajustar extração de dados para refletir o novo modelo desacoplado)
- [x] Verificar integridade (Validações completas e migração de dados velhos OK)
