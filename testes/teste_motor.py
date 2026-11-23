"""Testes do motor de conciliacao.

Rode com:  python -m testes.testar

Cada teste descreve uma situacao real do dia a dia da conciliacao.
Sao os mesmos casos da versao em JavaScript, pra garantir que as duas
decidem igual.
"""

from datetime import date
from decimal import Decimal

from concilia.motor import conciliar, conferir_taxas, taxa_contratada_para
from concilia.formato import para_numero, para_data

HOJE = date(2026, 10, 16)

_seq = [0]


def rec(dia, liquido, **extra):
    _seq[0] += 1
    base = {
        "id": f"r{_seq[0]}",
        "estabelecimento_id": "e1",
        "data_prevista": para_data(dia),
        "valor_liquido": Decimal(str(liquido)),
        "valor_bruto": Decimal(str(liquido)),
        "status": "previsto",
    }
    base.update(extra)
    return base


def mov(dia, valor, **extra):
    _seq[0] += 1
    base = {"id": f"m{_seq[0]}", "data": para_data(dia), "valor": Decimal(str(valor))}
    base.update(extra)
    return base


TAXA_PADRAO = {
    "id": "t1",
    "estabelecimento_id": "e1",
    "bandeira": None,
    "modalidade": "credito_vista",
    "parcelas_de": 1,
    "parcelas_ate": 1,
    "taxa_percentual": Decimal("3.0"),
    "vigencia_inicio": date(2026, 1, 1),
    "vigencia_fim": None,
}


def venda(**extra):
    base = {
        "id": "v1",
        "estabelecimento_id": "e1",
        "data_venda": date(2026, 10, 1),
        "modalidade": "credito_vista",
        "bandeira": "VISA",
        "parcelas": 1,
        "valor_bruto": Decimal("1000"),
        "valor_taxa": Decimal("30"),
    }
    base.update(extra)
    return base


# =====================================================================
TESTES = []


def teste(grupo, nome):
    def registrar(fn):
        TESTES.append((grupo, nome, fn))
        return fn
    return registrar


def igual(obtido, esperado, oque):
    if obtido != esperado:
        raise AssertionError(f"{oque}: obtive {obtido!r}, esperava {esperado!r}")


G1 = "CONCILIACAO DO LOTE DIARIO"


@teste(G1, "a adquirente junta o dia num deposito so, e tudo concilia")
def _():
    r = conciliar(
        recebiveis=[rec("2026-10-01", 100), rec("2026-10-01", "250.50"), rec("2026-10-01", "49.50")],
        movimentos=[mov("2026-10-01", 400)],
        hoje=HOJE,
    )
    igual(len(r["conciliacoes"]), 3, "conciliados")
    igual(len(r["divergencias"]), 0, "divergencias")


@teste(G1, "cada parcela caiu separada, e tudo concilia")
def _():
    r = conciliar(
        recebiveis=[rec("2026-10-01", 100), rec("2026-10-01", 300)],
        movimentos=[mov("2026-10-01", 100), mov("2026-10-01", 300)],
        hoje=HOJE,
    )
    igual(len(r["conciliacoes"]), 2, "conciliados")
    igual(len(r["divergencias"]), 0, "divergencias")


@teste(G1, "diferenca de um centavo e arredondamento, nao divergencia")
def _():
    r = conciliar(
        recebiveis=[rec("2026-10-01", "100.005"), rec("2026-10-01", "99.995")],
        movimentos=[mov("2026-10-01", 200)],
        hoje=HOJE,
    )
    igual(len(r["conciliacoes"]), 2, "conciliados")
    igual(len(r["divergencias"]), 0, "divergencias")


@teste(G1, "caiu um dia depois, dentro da tolerancia, concilia sem reclamar")
def _():
    r = conciliar(
        recebiveis=[rec("2026-10-01", 500)],
        movimentos=[mov("2026-10-02", 500)],
        hoje=HOJE,
    )
    igual(len(r["conciliacoes"]), 1, "conciliados")
    igual(r["conciliacoes"][0]["diferenca_dias"], 1, "dias de diferenca")
    igual(len(r["divergencias"]), 0, "divergencias")


G2 = "O QUE NAO BATE VIRA DIVERGENCIA, NUNCA E FORCADO"


@teste(G2, "venceu e nao caiu no banco, vira nao recebido")
def _():
    r = conciliar(recebiveis=[rec("2026-09-10", 1200)], movimentos=[], hoje=HOJE)
    igual(len(r["conciliacoes"]), 0, "conciliados")
    igual(len(r["divergencias"]), 1, "divergencias")
    d = r["divergencias"][0]
    igual(d["tipo"], "nao_recebido", "tipo")
    igual(d["diferenca"], Decimal("-1200.00"), "diferenca")
    igual(d["gravidade"], "alta", "gravidade")


@teste(G2, "ainda nao venceu, nao e divergencia nenhuma")
def _():
    r = conciliar(recebiveis=[rec("2026-11-30", 800)], movimentos=[], hoje=HOJE)
    igual(len(r["conciliacoes"]), 0, "conciliados")
    igual(len(r["divergencias"]), 0, "divergencias")


@teste(G2, "deposito com a data certa e valor errado aponta o lugar, sem conciliar")
def _():
    r = conciliar(
        recebiveis=[rec("2026-10-01", 1000)], movimentos=[mov("2026-10-01", 970)], hoje=HOJE
    )
    igual(len(r["conciliacoes"]), 0, "conciliados")
    igual(len(r["divergencias"]), 1, "divergencias")
    igual(r["divergencias"][0]["tipo"], "valor_divergente", "tipo")
    igual(r["divergencias"][0]["diferenca"], Decimal("-30.00"), "diferenca")


@teste(G2, "diferenca grande nao vira valor divergente, vira nao recebido e nao identificado")
def _():
    r = conciliar(
        recebiveis=[rec("2026-09-01", 1000)], movimentos=[mov("2026-09-01", 400)], hoje=HOJE
    )
    igual(len(r["conciliacoes"]), 0, "conciliados")
    igual(sorted(d["tipo"] for d in r["divergencias"]),
          ["nao_identificado", "nao_recebido"], "tipos")


@teste(G2, "entrou dinheiro que ninguem sabe de onde veio")
def _():
    r = conciliar(
        recebiveis=[],
        movimentos=[mov("2026-10-05", 333, descricao="TED NAO IDENTIFICADA")],
        hoje=HOJE,
    )
    igual(len(r["divergencias"]), 1, "divergencias")
    igual(r["divergencias"][0]["tipo"], "nao_identificado", "tipo")
    igual(r["divergencias"][0]["valor_encontrado"], Decimal("333.00"), "valor")


@teste(G2, "saida do banco e ignorada, so entrada conta")
def _():
    r = conciliar(
        recebiveis=[],
        movimentos=[mov("2026-10-05", -500, descricao="PAGAMENTO FORNECEDOR")],
        hoje=HOJE,
    )
    igual(len(r["divergencias"]), 0, "divergencias")


@teste(G2, "chargeback vira alerta e sai da conciliacao")
def _():
    r = conciliar(
        recebiveis=[rec("2026-10-01", 600, status="chargeback")], movimentos=[], hoje=HOJE
    )
    igual(len(r["conciliacoes"]), 0, "conciliados")
    igual(len(r["divergencias"]), 1, "divergencias")
    igual(r["divergencias"][0]["tipo"], "chargeback", "tipo")
    igual(r["divergencias"][0]["gravidade"], "alta", "gravidade")


@teste(G2, "venda cancelada e simplesmente ignorada")
def _():
    r = conciliar(
        recebiveis=[rec("2026-09-01", 600, status="cancelado")], movimentos=[], hoje=HOJE
    )
    igual(len(r["conciliacoes"]), 0, "conciliados")
    igual(len(r["divergencias"]), 0, "divergencias")


@teste(G2, "caiu muito atrasado, concilia mas registra o atraso")
def _():
    r = conciliar(
        recebiveis=[rec("2026-10-01", 500)], movimentos=[mov("2026-10-20", 500)], hoje=HOJE
    )
    # Fora da tolerancia de dias, o motor nao casa por conta propria.
    igual(len(r["conciliacoes"]), 0, "conciliados")
    igual(sorted(d["tipo"] for d in r["divergencias"]),
          ["nao_identificado", "nao_recebido"], "tipos")


G3 = "UM MOVIMENTO NAO PODE SER USADO DUAS VEZES"


@teste(G3, "dois recebiveis de valor igual nao casam com um deposito so")
def _():
    r = conciliar(
        recebiveis=[rec("2026-09-01", 100), rec("2026-09-02", 100)],
        movimentos=[mov("2026-09-01", 100)],
        hoje=HOJE,
    )
    igual(len(r["conciliacoes"]), 1, "conciliados")
    igual(len([d for d in r["divergencias"] if d["tipo"] == "nao_recebido"]), 1, "nao recebidos")


G4 = "CONFERENCIA DE TAXA"


@teste(G4, "taxa cobrada igual ao combinado, nada a reclamar")
def _():
    igual(len(conferir_taxas([venda()], [TAXA_PADRAO])), 0, "divergencias")


@teste(G4, "cobraram a maior, e o sistema diz quanto")
def _():
    d = conferir_taxas([venda(valor_taxa=Decimal("38.50"))], [TAXA_PADRAO])
    igual(len(d), 1, "divergencias")
    igual(d[0]["tipo"], "taxa_maior", "tipo")
    igual(d[0]["valor_esperado"], Decimal("30.00"), "esperado")
    igual(d[0]["valor_encontrado"], Decimal("38.50"), "cobrado")
    igual(d[0]["diferenca"], Decimal("8.50"), "diferenca")
    igual(d[0]["gravidade"], "alta", "gravidade")


@teste(G4, "cobraram a menor, registra mas sem alarme")
def _():
    d = conferir_taxas([venda(valor_taxa=Decimal("22"))], [TAXA_PADRAO])
    igual(d[0]["tipo"], "taxa_menor", "tipo")
    igual(d[0]["gravidade"], "baixa", "gravidade")


@teste(G4, "sem taxa combinada cadastrada, o motor nao acusa nada")
def _():
    igual(len(conferir_taxas([venda(valor_taxa=Decimal("99"))], [])), 0, "divergencias")


@teste(G4, "taxa de outra vigencia nao e aplicada")
def _():
    antiga = {**TAXA_PADRAO, "vigencia_fim": date(2026, 6, 30)}
    igual(len(conferir_taxas([venda(valor_taxa=Decimal("99"))], [antiga])), 0, "divergencias")


@teste(G4, "regra com bandeira ganha da regra generica")
def _():
    especifica = {**TAXA_PADRAO, "id": "t2", "bandeira": "VISA",
                  "taxa_percentual": Decimal("2.5")}
    regra = taxa_contratada_para(venda(), [TAXA_PADRAO, especifica])
    igual(regra["id"], "t2", "regra escolhida")


@teste(G4, "parcelado nao usa a taxa do credito a vista")
def _():
    v = venda(modalidade="credito_parcelado", parcelas=6, valor_taxa=Decimal("90"))
    igual(len(conferir_taxas([v], [TAXA_PADRAO])), 0, "divergencias")


G5 = "RESUMO DO MES"


@teste(G5, "soma o dinheiro em jogo por tipo de problema")
def _():
    r = conciliar(
        recebiveis=[rec("2026-09-01", 1000), rec("2026-09-02", 500)],
        movimentos=[],
        vendas=[venda(valor_taxa=Decimal("40"))],
        taxas=[TAXA_PADRAO],
        hoje=HOJE,
    )
    igual(r["resumo"]["por_tipo"]["nao_recebido"]["quantidade"], 2, "qtd nao recebido")
    igual(r["resumo"]["por_tipo"]["nao_recebido"]["valor"], Decimal("1500.00"), "valor nao recebido")
    igual(r["resumo"]["por_tipo"]["taxa_maior"]["valor"], Decimal("10.00"), "valor taxa a maior")


G6 = "LEITURA DE VALOR E DATA DO BRASIL"


@teste(G6, "le valor em qualquer formato que a adquirente mandar")
def _():
    casos = [
        ("1.234,56", Decimal("1234.56")), ("1234.56", Decimal("1234.56")),
        ("R$ 1.234,56", Decimal("1234.56")), ("(1.234,56)", Decimal("-1234.56")),
        ("-45,90", Decimal("-45.90")), ("0,00", Decimal("0")),
        ("1,234.56", Decimal("1234.56")), ("89", Decimal("89")),
        ("", None), (None, None),
    ]
    for entrada, esperado in casos:
        igual(para_numero(entrada), esperado, f"para_numero({entrada!r})")


@teste(G6, "le data em qualquer formato, inclusive o numero interno do Excel")
def _():
    casos = [
        ("31/12/2025", date(2025, 12, 31)), ("2025-12-31", date(2025, 12, 31)),
        ("01-02-2026", date(2026, 2, 1)), ("05/06/26", date(2026, 6, 5)),
        (45658, date(2025, 1, 1)), ("", None), ("abc", None),
    ]
    for entrada, esperado in casos:
        igual(para_data(entrada), esperado, f"para_data({entrada!r})")


@teste(G6, "centavo quebrado nao vira erro de ponto flutuante")
def _():
    # Em float, 0.1 + 0.2 da 0.30000000000000004 e a conciliacao reclamaria
    # de um centavo inexistente. Com Decimal, bate exato.
    r = conciliar(
        recebiveis=[rec("2026-10-01", "0.10"), rec("2026-10-01", "0.20")],
        movimentos=[mov("2026-10-01", "0.30")],
        hoje=HOJE,
    )
    igual(len(r["conciliacoes"]), 2, "conciliados")
    igual(len(r["divergencias"]), 0, "divergencias")
