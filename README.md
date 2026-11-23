# Concilia, conciliadora de cartão

Confere se o dinheiro que a maquininha prometeu pagar caiu mesmo no banco.

Você baixa a **agenda de recebíveis** no portal da adquirente, baixa o **extrato** no banco, e o Concilia cruza os dois. Sai uma planilha de Excel com tudo que bateu e, principalmente, com tudo que **não** bateu: o que não caiu, o que caiu a menos e o dinheiro que entrou sem ninguém saber de onde veio.

Roda no seu computador. Não precisa de internet, de conta, de login nem de banco de dados.

## Para quem serve

Para quem faz BPO Financeiro e confere cartão de cliente todo mês. Serve para qualquer adquirente (Cielo, Rede, Stone, Getnet, PagBank e outras), desde que o portal exporte a agenda em Excel ou CSV.

## Como instalar

Abra o Claude (aba **Code**) ou o ChatGPT (modo **Work**), escolha uma **pasta vazia** e cole:

```
Instale https://github.com/claudiabernardo-sketch/concilia
```

O agente baixa o projeto, instala o que falta e roda um exemplo para mostrar que funcionou. Se ele pedir para instalar o Python, pode aceitar.

## Como usar no dia a dia

1. Baixe a agenda de recebíveis do cliente no portal da adquirente (Excel ou CSV).
2. Baixe o extrato do banco do mesmo período (Excel ou CSV).
3. Coloque os dois arquivos na pasta do Concilia. Use um **apelido** do cliente no nome, nunca o nome verdadeiro. Exemplo: `agenda-padaria-outubro.xlsx` e `extrato-padaria-outubro.xlsx`.
4. Peça ao agente:

```
Concilie agenda-padaria-outubro.xlsx com extrato-padaria-outubro.xlsx
```

O relatório sai na mesma pasta, numa planilha chamada `relatorio-` com a data de hoje.

Se preferir rodar você mesma no terminal, o comando é:

```
python conciliar.py agenda-padaria-outubro.xlsx extrato-padaria-outubro.xlsx
```

## O que precisa ter nos arquivos

**Na agenda de recebíveis:** a data prevista de pagamento e o valor líquido.
**No extrato:** a data e o valor.

Se tiver, ele também usa: modalidade (débito, crédito à vista, parcelado), bandeira, valor bruto, taxa, parcela, situação (chargeback, cancelado) e o histórico do banco.

Ele lê `.xlsx` e `.csv`, entende valor no formato brasileiro (`1.234,56`, `R$ 1.234,56`, `(1.234,56)` como negativo) e pula sozinho as linhas de título que os portais colocam antes da tabela.

Ele descobre cada coluna pelo nome do cabeçalho e mostra na tela o que entendeu. **Se não achar uma coluna obrigatória, ele para**, mostra as colunas que o arquivo tem e pede para você renomear. Ele nunca adivinha.

Arquivo `.xls` antigo: abra no Excel e salve como `.xlsx`. PDF ainda não é lido.

## O relatório

A planilha tem três abas:

- **Divergencias:** cada problema, com a data, o valor esperado, o valor encontrado, a diferença e uma explicação. Os mais graves vêm primeiro.
- **Resumo:** quanto dinheiro está em jogo em cada tipo de problema. Dá para entender em 5 segundos.
- **Conciliados:** o que bateu, com o depósito correspondente e como o sistema casou, para você conferir.

Os tipos de problema são: previsto e não recebido, valor diferente do previsto, entrada sem origem identificada e chargeback.

## Como ele decide

Regra fixa, sem inteligência artificial. O mesmo arquivo gera sempre o mesmo resultado.

1. Junta os recebíveis de cada dia e procura **um depósito** com a soma do dia, porque a adquirente costuma pagar tudo junto.
2. Se não achar, separa o dia por **modalidade** (débito de um lado, crédito do outro) e depois por **bandeira**, e procura um depósito para cada parte. Isso cobre a adquirente que deposita débito e crédito separados.
3. Se ainda faltar, tenta **parcela por parcela**.
4. Se não achar, procura um depósito na data certa com valor **até 5% diferente** e aponta, **sem conciliar**.
5. O que venceu e não apareceu vira **previsto e não recebido**.
6. Dinheiro que entrou e não casa com nada vira **entrada sem origem identificada**.
7. Chargeback nunca é conciliado, vira alerta. Venda cancelada é ignorada.

Ele aceita até 2 centavos de arredondamento e até 2 dias de diferença na data. Um lançamento do banco nunca é usado duas vezes. Saídas do banco são ignoradas.

**PIX, TED, DOC, transferência, depósito e boleto de cliente nunca são casados com a agenda**, mesmo com o valor igual, porque coincidência de valor acontece. A exceção é quando o histórico do banco traz o nome da adquirente (por exemplo `PIX RECEBIDO STONE` ou `TED CIELO`): aí ele sabe que veio da maquininha.

Atenção: se o seu banco mostra o depósito da adquirente só como `TED RECEBIDA`, sem o nome dela, o Concilia não casa. Aparecem duas linhas no relatório (não recebido e entrada sem origem) e você confere na mão. Se isso acontecer sempre com um banco, peça ao agente para ensinar o nome que aparece no seu extrato.

## Onde ficam os seus dados

**Só no seu computador**, na pasta do Concilia. Nada vai para a internet, nem para a Cláudia, nem para o GitHub. As planilhas dos clientes ficam fora do controle de versão de propósito (o arquivo `.gitignore` já bloqueia `.xlsx` e `.csv`, menos os exemplos).

Para apagar tudo de um cliente, é só apagar os arquivos dele na pasta.

## Quer testar antes de ter arquivo real?

```
python conciliar.py exemplos/agenda-exemplo.xlsx exemplos/extrato-exemplo.xlsx
```

Os exemplos são de mentira e contam uma história: um dia que bate certinho, um depósito que veio R$ 75 a menos, um dia em que não caiu nada (e entrou um PIX de cliente com o mesmo valor, que o sistema não casa), um dia com débito e crédito em depósitos separados, e uma TED sem origem. O resultado esperado é **6 conciliados e 4 que precisam de atenção**.

## O que ainda não faz

- Ler PDF.
- Conferir a taxa cobrada contra a taxa combinada (o motor já sabe, falta onde cadastrar as taxas).
- Lançar no ERP (Conta Azul, Omie, Bling, Tiny).
- Guardar histórico entre um mês e outro. Cada execução é independente.

---

## Para o agente: instalar pelo link

Se o usuário colou "Instale https://github.com/claudiabernardo-sketch/concilia", siga estes passos, explicando cada um em português simples. Leia também o `AGENTS.md` antes de mexer em qualquer coisa.

1. **Pasta vazia.** Confira que a pasta atual está vazia. Se não estiver, crie uma subpasta `concilia` e trabalhe dentro dela.
2. **Baixar.** Se tiver `git`: `git clone https://github.com/claudiabernardo-sketch/concilia .`. Se não tiver, baixe `https://github.com/claudiabernardo-sketch/concilia/archive/refs/heads/main.zip`, extraia e mova o conteúdo da pasta `concilia-main` para a pasta atual.
3. **Python.** Precisa do Python 3.10 ou mais novo. Confira com `python --version` (no Windows, se não responder, tente `py --version`; no Mac, `python3 --version`). Se não tiver:
   - Windows: `winget install -e --id Python.Python.3.12` e depois feche e abra o terminal. Sem winget, mande o usuário baixar em python.org e marcar **Add python.exe to PATH** na instalação.
   - Mac: `brew install python` ou o instalador de python.org.
   Use nos passos seguintes o comando que funcionou (`python`, `py` ou `python3`).
4. **Dependências.** `python -m pip install -r requisitos.txt` (só o `openpyxl`, para ler e escrever Excel).
5. **Testes.** `python -m testes.testar`. Tem que terminar com `TODOS OS 48 TESTES PASSARAM`.
6. **Exemplo.** `python conciliar.py exemplos/agenda-exemplo.xlsx exemplos/extrato-exemplo.xlsx --saida relatorio-exemplo.xlsx`.
7. **Conferir.** O resultado tem que mostrar `Conciliados 6` e `Precisam de atencao 4`, e o arquivo `relatorio-exemplo.xlsx` tem que existir com as abas Divergencias, Resumo e Conciliados. Mostre ao usuário o resumo e onde o arquivo ficou.
8. **Explicar o próximo passo:** baixar a agenda e o extrato de um cliente, salvar nesta pasta com um apelido no nome, e pedir "Concilie agenda-APELIDO.xlsx com extrato-APELIDO.xlsx".

Se algum passo falhar, pare, diga o erro em português simples e não invente contorno que mude o motor.

## Para quem quer conferir o código

```
conciliar.py              o comando que você roda e o relatório em Excel
concilia/motor.py         as regras de conciliação
concilia/mapear.py        descobre de qual coluna vem cada informação
concilia/planilha.py      leitura de Excel e CSV
concilia/formato.py       valor e data no padrão brasileiro
testes/                   48 testes, cada um uma situação real
exemplos/                 planilhas de mentira para testar
```

Rode os testes com `python -m testes.testar`. Dinheiro é tratado com `Decimal`, não com número quebrado comum, para `0,10 + 0,20` dar exatamente `0,30`.

---

Feito por Cláudia Bernardo para o BPO Financeiro. O Concilia é da Cláudia Bernardo.

**Licença PolyForm Shield 1.0.0** (arquivo `LICENSE`). Em português simples: você pode usar de graça, inclusive no seu BPO com clientes pagantes, e pode adaptar para o seu uso. O que não pode é usar o Concilia para vender um produto ou serviço de conciliação que concorra com o dela. Distribuído sem garantia: confira sempre o relatório antes de mandar para o cliente.
