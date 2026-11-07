# MAPA_SISTEMA.md — Kanemberg Sistema Desktop (`static_sistema/`)

> Leia ESTE arquivo antes de qualquer tarefa. Não abra `aba_estoque.js`, `aba_cadastro.js`, `aba_venda.js` nem `core.js` a menos que seja pedido.
> Não tocar em `static/` (App Mobile). Rodar: `py -3 main.py` → `http://localhost:8000/sistema`. Python no Windows = `py -3`.

## 1. Arquivos
| Arquivo | Função |
|---|---|
| `sistema.html` | Sidebar (5 abas operacionais) + 5 `<section>` + modais. Scripts (ordem: core → estoque → cadastro → venda → fiado → dashboard) |
| `sistema.css` | Estilos únicos (vars `--bg-card`, `--fg-primary`, `--border-color`...; classes `.hidden`, `.modal-backdrop`, `.btn-salvar-sistema`, `.btn-secundario-sistema`, `.pill-grupo`, `.estado-vazio`, `.txt-verde/.txt-vermelho`) |
| `js/core.js` | Estado, DOM refs, utilitários, API, toasts, navegação, modais, init |
| `js/aba_estoque.js` | Aba 1 ✅ · `js/aba_cadastro.js` Aba 2 ✅ · `js/aba_venda.js` Aba 3 ✅ · `js/aba_fiado.js` Aba 4 ✅ · `js/aba_dashboard.js` Aba 5 ✅ |

Sections (`data-view` do menu = sufixo do id): `#view-estoque` `#view-cadastro` `#view-venda` `#view-fiado` `#view-dashboard`. Todas as 5 abas estão 100% concluídas (`margens` redireciona automaticamente para a sub-visão `MARGENS` dentro de `#view-dashboard`).
Modais existentes: `modal-editar`, `modal-excluir`, `modal-detalhes`, `modal-vender`, `modal-cliente-rapido`, `modal-recibo-venda`, `modal-qrcode` (padrão: `.modal-backdrop.hidden > .modal-window > header.modal-header / .modal-body / footer.modal-footer`; botão `data-fechar-modal="id"` fecha sozinho; `[data-ir-view="x"]` navega). Container dedicado de impressão isolada: `#area-impressao-qrcode`.

## 2. Como criar uma nova aba (ex.: `js/aba_fiado.js`)
1. Criar `js/aba_X.js` com funções globais da aba + `function registrarEventosX(){...}`.
2. No fim: `KanembergApp.eventos.push(registrarEventosX); KanembergApp.inicializadores.push(carregarX);`
3. Adicionar `<script defer src="/static_sistema/js/aba_X.js">` ao final do `sistema.html`.
4. Se precisar de dados ao abrir a aba, estender `alternarView` (core.js, bloco `if (nomeView === ...)`).
5. Novos IDs do DOM: declarar em `dom` (core.js) ou usar `document.getElementById`/`$()` dentro da aba.
Tudo é escopo global de script clássico (sem ES Modules). `const`/`function` de um arquivo são visíveis nos outros em tempo de chamada.

## 3. Contrato global (`core.js`)
**Objeto/consts:** `KanembergApp {eventos[], inicializadores[]}` · `$(id)` · `dom{}` (refs de todos os IDs das 3 abas + modais + `views{estoque,cadastro,venda,fiado,margens,dashboard,config}`, `navItems`, `toastContainer`) ·
`estado{ viewAtual, modoEscuro, produtos[] (cache /api/estoque), filtroGrupo, termoBusca, produtoEditando, coresEditando, produtoExcluindo, produtoDetalhes, camaleao{...}, pdv{ carrinho[], filtroGrupo, termoBusca, modoDesconto('RS'|'PCT'), valorDescontoInput, formaPagamento, clientes[], buscaCliente, clienteIdSelecionado, enviandoVenda } }` ·
`GRUPOS_CONFIG` (5 grupos: cima `#00d2ff`, baixo `#4ade80`, calcados `#ff7b00`, acessorios `#ff1744`, perfumaria `#ffd700`) · `ORDEM_TAMANHOS` · `MARCAS_PADRAO` · `PALETA_CORES_PADRAO` · `PERFIS_CAMALEAO` · `DICIONARIO_CORES_HEX` · `VALORES_VAZIOS`.

**Funções:**
- `exibirToast(msg, tipo='info'|'sucesso'|'erro'|'aviso', duracaoMs=3200)` (alias `mostrarToast`)
- `requisitarApi(url, {metodo='GET', corpo})` → Promise<JSON>; lança `Error(detail)` em HTTP != 2xx (envia o token automaticamente)
- `alternarView(nome)` (alias `alternarAba`) · `aplicarTema(bool)` · `fecharModal(id)` · `fecharTodosModais()`
- `formatarMoeda(n)`→"R$ 1.234,50" · `num(v, padrao=0)` · `escapeHtml(s)` · `formatarCustoCurto(n)` · `valorValido(v)` · `normalizarTamanhoFront(t)` · `resolverCorHex(nome, hex)`
- `obterGrupoProduto(modelo_nome, tipo_peca)`→`{chave,nome,cor}` · `extrairCoresProduto(prod)`→`[{nome,cor_hex}]` · `agruparTamanhosProduto(prod)`→`[{tamanho,estoque,variacao_id,codigo_barras,preco_venda}]`
**Em outras abas (globais, reutilizáveis):** `carregarEstoque(silencioso=false)` (recarrega `estado.produtos`, re-renderiza Vitrine e PDV) · `buscarProdutoEmMemoria(id)` · `abrirModalQrCodeProduto(produtoId, quantidadesPersonalizadas?)` · `carregarClientesPDV(silencioso)` (→ `estado.pdv.clientes`) · `carregarKpisVendasHoje()` · `acionarEnviarParaVenda(produtoId, tamanho?)`.
Monitor: a cada 5s recarrega estoque se aba ativa = estoque/venda e sem modal aberto.

## 4. Endpoints (`api_mobile.py`, FastAPI :8000, JWT Bearer exceto login/estáticos)
| Método URL | Envio → Resposta |
|---|---|
| POST `/api/login` | `{usuario,senha}` → token |
| GET `/api/estoque` | → `{produtos:[{id,modelo_nome,marca,tecido,corte,cores_tags,preco_custo,preco_venda,variacoes:[{id,tamanho,cor,cor_hex,estoque,preco_custo,preco_venda,codigo_barras}]}]}` |
| GET/POST `/api/atributos` | `{categoria,valor,cor_hex?}` · GET → `{atributos:{marca:[],tecido:[],corte:[],...}}` |
| POST `/api/produtos` (alias `/api/estoque/produto`) | `{modelo_nome,marca,tecido,corte,cores_tags,cor,cor_hex,preco_custo,preco_venda,variacoes:[{tamanho,cor,cor_hex,codigo_barras:"",estoque,preco_custo,preco_venda}]}` → `{mensagem,total_pecas,codigos_barras[]}` (gera `KNB...`) |
| PUT `/api/produtos/{id}` | campos opcionais de ProdutoInput + `variacoes[]` (com `id` p/ existentes) |
| DELETE `/api/produtos/{id}` | remove produto e variações |
| GET `/api/qrcode/svg/{codigo}` | → `image/svg+xml` (QR Code vetorial 100% offline, alto contraste `#000000`/`#ffffff`, cacheável) |
| GET `/api/qrcode/{codigo}` | → `{encontrado, produto:{produto_id,variacao_id,modelo_nome,marca,cor,cor_hex,tamanho,estoque,preco_venda,codigo_barras}}` |
| GET `/api/vendas/hoje` | → `{faturamento_hoje,total_vendido,pecas_hoje,pecas_vendidas,vendas[]}` |
| POST `/api/vendas` | `{itens:[{codigo_barras?,variacao_id?,quantidade}], desconto|desconto_total, forma_pagamento:'PIX'|'CARTAO'|'DINHEIRO'|'FIADO', cliente_id?, data_vencimento_lote?('YYYY-MM-DD'|'DD/MM/YYYY')}` → `{vendas_ids,data_hora,subtotal,desconto_total,valor_total,cliente_nome,itens_resumo[]}`; baixa estoque, grava `vendas`, e `conta_fiado` DEBITO se FIADO |
| GET `/api/clientes` (= `/api/fiado/clientes`) | → `{clientes:[{id,nome,telefone,limite_credito,dia_preferencial_pagamento(=dia_vencimento),saldo_devedor,disponivel,historico[]}]}` |
| POST `/api/clientes` (= `/api/fiado/clientes`) | `{nome,telefone,limite_credito,dia_preferencial_pagamento|dia_vencimento}` → `{cliente_id,mensagem}` |
| DELETE `/api/fiado/clientes/{id}` | remove cliente (só sem saldo) |
| PUT `/api/clientes/{id}` (= `/api/fiado/clientes/{id}`) | `{nome?,telefone?,limite_credito?,dia_preferencial_pagamento?}` → `{mensagem}` |
| GET `/api/fiado/clientes/{id}/extrato` | → `{movimentacoes:[{id,tipo_movimentacao,valor,data_movimentacao,data_vencimento_lote,descricao}]}` (todas, recente primeiro) |
| GET `/api/fiado/resumo` | → `{total_a_receber,clientes_com_divida,total_clientes,clientes_estourados,recebido_30_dias}` |
| POST `/api/fiado/debito` | `{cliente_id,valor,descricao?,data_vencimento_lote?}` → `{mensagem,lancamento_id}` (DEBITO avulso) |
| POST `/api/fiado/pagar` | `{cliente_id,valor,descricao?}` → `{valor_pago,saldo_devedor}` (CREDITO) |
| GET `/api/financeiro/resumo` | → `{hoje{faturamento_bruto,custo_total,lucro_liquido,pecas_vendidas}, semana{...}, por_pagamento_hoje{DINHEIRO,PIX,CARTAO,FIADO}}` |
| GET `/api/dashboard/completo?periodo=30d&grupo=todos` | → `{kpis, serie_temporal[], por_pagamento[], estoque_por_grupo[], ranking_marcas[], ranking_tipos[], ranking_cortes[], ranking_tecidos[], resumo_margens, auditoria_margens[], alertas{reposicao_estoque_baixo[], encalhados_sem_giro[]}}` |
| GET `/sistema`, `/`, `/logo_kanemberg.png`; mounts `/static`, `/static_sistema` | estáticos |

## 5. SQLite `loja_daniel_v2.db`
- `produtos(id, modelo_nome, marca, tecido, corte, cores_tags "Nome|#hex,...")`
- `produto_variacoes(id, produto_id, tamanho, cor, estoque, preco_custo, preco_venda, foto_path, cor_hex, codigo_barras)`
- `vendas(id, variacao_id, modelo_nome, marca, cor, tamanho, quantidade, valor_unitario, valor_total, data_venda 'DD/MM/YYYY HH:MM', forma_pagamento, preco_custo)`
- `clientes(id, nome, telefone, limite_credito, dia_preferencial_pagamento)`
- `conta_fiado(id, cliente_id, tipo_movimentacao 'DEBITO'|'CREDITO', valor, data_movimentacao, data_vencimento_lote, descricao)`
- `atributos(id, categoria, nome)`

## 6. Status
- ✅ **100% Concluídas (NÃO LER a menos que solicitado):**
  1. `aba_estoque.js` (`📦 Estoque`)
  2. `aba_cadastro.js` (`➕ Cadastrar` — Camaleão v6.0)
  3. `aba_venda.js` (`🛒 Nova Venda` — PDV Widescreen)
  4. `aba_fiado.js` (`💳 Fiado` — Gestão de Crédito e Extrato)
  5. `aba_dashboard.js` (`📊 Dashboard` — BI Executivo + Saúde das Margens + Giro de Estoque; globais `carregarDashboard(silencioso)`, `selecionarVisaoDashboard(visao)`, `reajustarPrecoProdutoDash(id)`)
- Backup do monolito antigo: `sistema_monolito_backup.js.txt` (raiz; não é carregado).
