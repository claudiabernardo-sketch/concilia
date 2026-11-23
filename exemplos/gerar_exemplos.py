"""Gera planilhas de exemplo pra voce testar o sistema antes de ter dado real.

Rode:  python exemplos/gerar_exemplos.py

Os nomes das colunas imitam o que os portais das adquirentes exportam,
com titulo antes da tabela e valor no formato brasileiro, que e como
chega de verdade.
"""

from pathlib import Path

from openpyxl import Workbook

AQUI = Path(__file__).parent

# Tudo aqui e de mentira: empresa, estabelecimento e valores.
#
# A historia que esses arquivos contam:
#   02/10  lote do dia bate certinho num deposito so
#   03/10  o deposito veio R$ 75 a menos
#   06/10  nao caiu nada da maquininha, e entrou um PIX de cliente com o
#          mesmo valor (o sistema NAO casa um com o outro)
#   07/10  debito e credito cairam em dois depositos separados
#   08/10  entrou uma TED que ninguem sabe de onde veio
AGENDA = [
    # data prevista, modalidade, bandeira, bruto, liquido
    ("02/10/2026", "Credito a vista", "Visa",       "1.200,00", "1.164,00"),
    ("02/10/2026", "Debito",          "Mastercard",   "800,00",   "776,00"),
    ("03/10/2026", "Credito a vista", "Elo",        "2.500,00", "2.425,00"),
    ("06/10/2026", "Credito a vista", "Visa",         "640,00",   "620,80"),
    ("07/10/2026", "Debito",          "Visa",         "300,00",   "294,00"),
    ("07/10/2026", "Debito",          "Elo",          "150,00",   "147,00"),
    ("07/10/2026", "Credito a vista", "Mastercard", "1.000,00",   "970,00"),
    ("07/10/2026", "Credito parcelado", "Visa",       "500,00",   "480,00"),
]

EXTRATO = [
    ("02/10/2026", "CRED MAQUININHA 0000001", "1.940,00"),
    ("03/10/2026", "CRED MAQUININHA 0000001", "2.350,00"),
    ("06/10/2026", "PIX RECEBIDO CLIENTE",      "620,80"),
    ("07/10/2026", "CRED MAQUININHA DEBITO",    "441,00"),
    ("07/10/2026", "CRED MAQUININHA CREDITO", "1.450,00"),
    ("08/10/2026", "TED RECEBIDA",              "450,00"),
    ("09/10/2026", "PAGAMENTO FORNECEDOR",   "-1.200,00"),
]


def gerar_agenda(destino):
    pasta = Workbook()
    aba = pasta.active
    aba.title = "Pagamentos"

    # Os portais costumam jogar um titulo antes da tabela de verdade.
    aba.append(["RELATORIO DE PAGAMENTOS"])
    aba.append(["Estabelecimento 0000001 (exemplo ficticio)"])
    aba.append([])
    aba.append(["Data prevista de pagamento", "Modalidade", "Bandeira", "Valor bruto",
                "Valor liquido"])

    for linha in AGENDA:
        aba.append(list(linha))

    for coluna, largura in (("A", 28), ("B", 20), ("C", 14), ("D", 16), ("E", 16)):
        aba.column_dimensions[coluna].width = largura

    pasta.save(destino)
    return destino


def gerar_extrato(destino):
    pasta = Workbook()
    aba = pasta.active
    aba.title = "Extrato"

    aba.append(["Data", "Historico", "Valor"])
    for linha in EXTRATO:
        aba.append(list(linha))

    for coluna, largura in (("A", 14), ("B", 30), ("C", 16)):
        aba.column_dimensions[coluna].width = largura

    pasta.save(destino)
    return destino


if __name__ == "__main__":
    agenda = gerar_agenda(AQUI / "agenda-exemplo.xlsx")
    extrato = gerar_extrato(AQUI / "extrato-exemplo.xlsx")
    print(f"Gerado: {agenda}")
    print(f"Gerado: {extrato}")
    print("\nAgora rode:")
    print("  python conciliar.py exemplos/agenda-exemplo.xlsx exemplos/extrato-exemplo.xlsx")
