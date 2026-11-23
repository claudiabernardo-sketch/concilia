# Regras para agentes (Claude, ChatGPT, Codex e outros)

Este projeto concilia a agenda de recebíveis da maquininha com o extrato do banco de clientes de BPO Financeiro. Quem usa costuma ser leiga em tecnologia: explique em português simples, um passo de cada vez.

Para instalar pelo link, siga a seção "Para o agente: instalar pelo link" do `README.md`.

## Regras que não mudam

1. **Nunca invente coluna.** Se o `conciliar.py` disser que não achou uma coluna obrigatória (data prevista e valor líquido na agenda, data e valor no extrato), mostre ao usuário as colunas que o arquivo tem e pergunte qual é qual. Não chute, não crie coluna, não preencha valor que não está no arquivo. Renomear o cabeçalho numa **cópia** do arquivo, depois que o usuário confirmar qual coluna é, pode.
2. **A IA não decide conciliação.** Quem decide o que bateu é o motor (`concilia/motor.py`), com regra fixa. Você não casa recebível com depósito "no olho", não tira divergência do relatório, não muda tolerância (`PARAMETROS_PADRAO`) para fazer bater, e não edita o relatório gerado. Você pode explicar o relatório e sugerir o que a pessoa deve conferir.
3. **Dados do cliente com apelido.** Arquivos de cliente levam apelido no nome (`agenda-padaria.xlsx`), nunca nome real, CNPJ ou CPF. Não copie dados de cliente para o chat além do necessário, não cole em sites, não suba para o GitHub. O `.gitignore` bloqueia `.xlsx` e `.csv` fora de `exemplos/`; não remova isso.
4. **Exemplos são de mentira.** Nada em `exemplos/` ou `testes/` pode ter dado real de cliente, nome de empresa real ou número de estabelecimento real.
5. **Não adivinhe layout de adquirente.** Para ensinar o sistema a ler um portal novo ou um histórico de banco novo, peça um arquivo real ao usuário (com dados que ele possa mostrar) e escreva um teste com valores fictícios no mesmo formato.

## Como o motor decide (resumo)

Lote do dia inteiro, depois o dia separado por modalidade e por bandeira, depois parcela por parcela, depois aproximado (até 5%, só aponta, não concilia). Tolerância de R$ 0,02 e 2 dias. Um lançamento do banco nunca é usado duas vezes. Entrada com histórico de PIX, TED, DOC, transferência, depósito ou boleto sem nome de adquirente nunca é casada (`parece_fora_da_maquininha`). Chargeback vira alerta, cancelado é ignorado.

## Se for mexer no código

- Rode `python -m testes.testar` antes e depois. Todos os testes têm que passar.
- Toda regra nova ganha um teste em `testes/` que descreve a situação real em português.
- Dinheiro sempre com `Decimal` (veja `concilia/formato.py`), nunca `float`.
- Mensagens na tela sem acento (o terminal do Windows às vezes quebra acento).
- Se o banco do usuário mostra o depósito da adquirente com um nome que o sistema não conhece, acrescente o nome em `ADQUIRENTES` no `motor.py`, com teste, usando o texto exato do extrato que o usuário mostrou.
