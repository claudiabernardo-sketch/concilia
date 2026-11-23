# Concilia, conciliadora de cartão

> **Versão de teste.** O Concilia está sendo testado pelas alunas da Cláudia com arquivos reais de várias maquininhas. Confira sempre o relatório antes de mandar para o cliente, e conte para a Cláudia o que aconteceu.

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

1. Baixe a agenda de recebíveis do cliente no portal da maquininha (Excel ou CSV).
2. Baixe o extrato do banco do mesmo período (Excel ou CSV).
3. Salve os dois com um **apelido** do cliente no nome, nunca o nome verdadeiro. Exemplo: `agenda-padaria-outubro.xlsx` e `extrato-padaria-outubro.xlsx`.
4. Abra o Concilia. Peça ao agente:

```
Abra o Concilia
```

Ou dê dois cliques no arquivo **Abrir Concilia** que está na pasta (no Mac, **Abrir Concilia.command**).

5. Abre uma tela no navegador. **Arraste a agenda** para o quadro 1, **o extrato** para o quadro 2 e clique em **Conciliar**.
6. Na hora aparece o resultado: quanto bateu, o que precisa de atenção e onde está o dinheiro em jogo. Clique em **Baixar relatório em Excel** para guardar ou mandar ao cliente.

Na primeira vez, clique em **Veja com um exemplo de mentira** para conhecer a tela sem usar arquivo de cliente.

Enquanto usa, deixe aberta a janela preta que aparece junto: é ela que faz o Concilia funcionar. Para fechar, é só fechar essa janela.

**Prefere pedir sem abrir a tela?** Coloque os dois arquivos na pasta do Concilia e peça ao agente:

```
Concilie agenda-padaria-outubro.xlsx com extrato-padaria-outubro.xlsx
```

O relatório sai na mesma pasta, numa planilha chamada `relatorio-` com a data de hoje. O comando por trás é `python conciliar.py agenda.xlsx extrato.xlsx`.

## Como atualizar

Durante o teste, o Concilia recebe correções. Para pegar a versão nova, abra o agente na pasta do Concilia e peça:

```
Atualize o Concilia
```

As planilhas dos seus clientes que estão na pasta não são apagadas.

## O que precisa ter nos arquivos

**Na agenda de recebíveis:** a data prevista de pagamento e o valor líquido.
**No extrato:** a data e o valor.

Se tiver, ele também usa: modalidade (débito, crédito à vista, parcelado), bandeira, valor bruto, taxa, parcela, situação (chargeback, cancelado) e o histórico do banco.

Ele lê `.xlsx` e `.csv`, entende valor no formato brasileiro (`1.234,56`, `R$ 1.234,56`, `(1.234,56)` como negativo) e pula sozinho as linhas de título que os portais colocam antes da tabela.

Ele descobre cada coluna pelo nome do cabeçalho e mostra na tela o que entendeu. **Se não achar uma coluna obrigatória, ele para**, mostra as colunas que o arquivo tem e pede para você renomear. Ele nunca adivinha.

Arquivo `.xls` antigo: abra no Excel e salve como `.xlsx`. PDF ainda não é lido.

## O relatório

A planilha tem três abas:

- **Resumo:** a capa. Quantos conciliou, o valor que bateu, quantos precisam de atenção e onde está o dinheiro em jogo. Dá para entender em 5 segundos e mandar para o cliente.
- **Divergências:** cada problema, com a data, o valor esperado, o valor encontrado, a diferença e uma explicação. Os mais graves vêm primeiro, com a gravidade em cor.
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

**Só no seu computador**, na pasta do Concilia. A tela abre no navegador, mas não é um site: ela roda no próprio computador (o endereço começa com `127.0.0.1`) e funciona até sem internet. Nada vai para a internet, nem para a Cláudia, nem para o GitHub. As planilhas dos clientes ficam fora do controle de versão de propósito (o arquivo `.gitignore` já bloqueia `.xlsx` e `.csv`, menos os exemplos).

Para apagar tudo de um cliente, é só apagar os arquivos dele na pasta.

## Quer testar antes de ter arquivo real?

Abra o Concilia e clique em **Veja com um exemplo de mentira**. Ou, pelo comando:

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
5. **Testes.** `python -m testes.testar`. Tem que terminar com `TODOS OS 61 TESTES PASSARAM`.
6. **Exemplo.** `python conciliar.py exemplos/agenda-exemplo.xlsx exemplos/extrato-exemplo.xlsx --saida relatorio-exemplo.xlsx`.
7. **Conferir.** O resultado tem que mostrar `Conciliados 6` e `Precisam de atencao 4`, e o arquivo `relatorio-exemplo.xlsx` tem que existir com as abas Resumo, Divergências e Conciliados. Mostre ao usuário o resumo e onde o arquivo ficou.
8. **Abrir a tela.** Rode `python abrir_concilia.py` **em segundo plano** (ele fica rodando, não espere terminar). O navegador abre sozinho em `http://127.0.0.1:8765/` (se a porta estiver ocupada, o endereço aparece na saída). Diga ao usuário para clicar em **Veja com um exemplo de mentira**.
9. **Explicar o próximo passo:** baixar a agenda e o extrato de um cliente, salvar com um apelido no nome e, nas próximas vezes, pedir "Abra o Concilia" ou dar dois cliques em **Abrir Concilia** na pasta.

Se o usuário pedir "Abra o Concilia": na pasta do projeto, rode `python abrir_concilia.py` em segundo plano e diga que a tela abriu no navegador. Se ele pedir "Concilie X com Y", rode `python conciliar.py X Y` e explique o resultado.

Se o usuário pedir "Atualize o Concilia": na pasta do projeto, rode `git pull` (se a pasta veio do `git clone`). Se veio do zip, baixe o zip de novo e substitua só os arquivos do projeto (`conciliar.py`, `abrir_concilia.py`, `Abrir Concilia.bat`, `Abrir Concilia.command`, `concilia/`, `testes/`, `exemplos/`, `requisitos.txt`, `README.md`, `AGENTS.md`, `CLAUDE.md`, `LICENSE`), sem apagar as planilhas do usuário. Depois rode `python -m pip install -r requisitos.txt` e `python -m testes.testar` e diga quantos testes passaram.

Se algum passo falhar, pare, diga o erro em português simples e não invente contorno que mude o motor.

## Para quem quer conferir o código

```
abrir_concilia.py         abre a tela no navegador (Abrir Concilia.bat no Windows)
conciliar.py              o comando, para quem prefere pedir sem tela
concilia/motor.py         as regras de conciliação
concilia/servico.py       lê os arquivos e monta o resultado (tela e comando usam o mesmo)
concilia/relatorio.py     o relatório em Excel
concilia/servidor.py      a tela, que roda só no computador (127.0.0.1)
concilia/tela/index.html  a página que aparece no navegador
concilia/mapear.py        descobre de qual coluna vem cada informação
concilia/planilha.py      leitura de Excel e CSV
concilia/formato.py       valor e data no padrão brasileiro
testes/                   61 testes, cada um uma situação real
exemplos/                 planilhas de mentira para testar
```

Rode os testes com `python -m testes.testar`. Dinheiro é tratado com `Decimal`, não com número quebrado comum, para `0,10 + 0,20` dar exatamente `0,30`.

---

Feito por Cláudia Bernardo para o BPO Financeiro. O Concilia é da Cláudia Bernardo.

**Licença PolyForm Shield 1.0.0** (arquivo `LICENSE`). Em português simples: você pode usar de graça, inclusive no seu BPO com clientes pagantes, e pode adaptar para o seu uso. O que não pode é usar o Concilia para vender um produto ou serviço de conciliação que concorra com o dela. Distribuído sem garantia: confira sempre o relatório antes de mandar para o cliente.
