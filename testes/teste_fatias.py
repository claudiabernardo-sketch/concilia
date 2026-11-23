"""Testes do dia fatiado e do dinheiro que nao e da maquininha.

Na vida real a adquirente costuma depositar debito e credito separados,
as vezes tambem uma bandeira por deposito. E o extrato tem PIX e TED de
cliente misturados com o credito da maquininha.

Esses testes entram na mesma lista do teste_motor, e rodam juntos com:
    python -m testes.testar
"""

from decimal import Decimal

from concilia import mapear
from concilia.motor import conciliar, parece_fora_da_maquininha
from testes.teste_motor import HOJE, igual, mov, rec, teste


G7 = "DEPOSITOS SEPARADOS NO MESMO DIA (DEBITO, CREDITO, BANDEIRA)"


@teste(G7, "debito e credito do dia caem em dois depositos, e tudo concilia")
def _():
    r = conciliar(
        recebiveis=[
            rec("2026-10-01", "98.00", modalidade="Debito"),
            rec("2026-10-01", "196.00", modalidade="Debito"),
            rec("2026-10-01", "485.00", modalidade="Credito"),
            rec("2026-10-01", "970.00", modalidade="Credito"),
        ],
        movimentos=[mov("2026-10-01", "294.00"), mov("2026-10-01", "1455.00")],
        hoje=HOJE,
    )
    igual(len(r["conciliacoes"]), 4, "conciliados")
    igual(len(r["divergencias"]), 0, "divergencias")
    igual({c["como"] for c in r["conciliacoes"]}, {"lote do dia por modalidade"}, "como casou")


@teste(G7, "cada deposito casa com a sua modalidade, nao com a outra")
def _():
    deb1 = rec("2026-10-01", "98.00", modalidade="Debito")
    deb2 = rec("2026-10-01", "196.00", modalidade="Debito")
    cre = rec("2026-10-01", "1455.00", modalidade="Credito")
    m_deb = mov("2026-10-01", "294.00")
    m_cre = mov("2026-10-01", "1455.00")
    r = conciliar(recebiveis=[deb1, deb2, cre], movimentos=[m_cre, m_deb], hoje=HOJE)
    casou = {c["recebivel_id"]: c["movimento_banco_id"] for c in r["conciliacoes"]}
    igual(casou, {deb1["id"]: m_deb["id"], deb2["id"]: m_deb["id"], cre["id"]: m_cre["id"]},
          "pares")


@teste(G7, "modalidade escrita de jeitos diferentes ainda separa debito de credito")
def _():
    r = conciliar(
        recebiveis=[
            rec("2026-10-01", "50.00", modalidade="DÉBITO"),
            rec("2026-10-01", "60.00", modalidade="debito pre-pago"),
            rec("2026-10-01", "300.00", modalidade="Crédito à vista"),
            rec("2026-10-01", "200.00", modalidade="CREDITO PARCELADO"),
        ],
        movimentos=[mov("2026-10-01", "110.00"), mov("2026-10-01", "500.00")],
        hoje=HOJE,
    )
    igual(len(r["conciliacoes"]), 4, "conciliados")
    igual(len(r["divergencias"]), 0, "divergencias")


@teste(G7, "a vista e parcelado em depositos separados tambem concilia")
def _():
    r = conciliar(
        recebiveis=[
            rec("2026-10-01", "300.00", modalidade="Crédito à vista"),
            rec("2026-10-01", "120.00", modalidade="Crédito à vista"),
            rec("2026-10-01", "200.00", modalidade="Crédito parcelado"),
            rec("2026-10-01", "80.00", modalidade="Crédito parcelado"),
        ],
        movimentos=[mov("2026-10-01", "420.00"), mov("2026-10-01", "280.00")],
        hoje=HOJE,
    )
    igual(len(r["conciliacoes"]), 4, "conciliados")
    igual(len(r["divergencias"]), 0, "divergencias")


@teste(G7, "um deposito por bandeira, e tudo concilia")
def _():
    r = conciliar(
        recebiveis=[
            rec("2026-10-01", "100.00", modalidade="Credito", bandeira="Visa"),
            rec("2026-10-01", "150.00", modalidade="Credito", bandeira="Visa"),
            rec("2026-10-01", "70.00", modalidade="Credito", bandeira="Mastercard"),
            rec("2026-10-01", "30.00", modalidade="Credito", bandeira="Mastercard"),
        ],
        movimentos=[mov("2026-10-01", "250.00"), mov("2026-10-01", "100.00")],
        hoje=HOJE,
    )
    igual(len(r["conciliacoes"]), 4, "conciliados")
    igual(len(r["divergencias"]), 0, "divergencias")


@teste(G7, "debito junto e credito separado por bandeira, e tudo concilia")
def _():
    r = conciliar(
        recebiveis=[
            rec("2026-10-01", "40.00", modalidade="Debito", bandeira="Visa"),
            rec("2026-10-01", "60.00", modalidade="Debito", bandeira="Elo"),
            rec("2026-10-01", "300.00", modalidade="Credito", bandeira="Visa"),
            rec("2026-10-01", "500.00", modalidade="Credito", bandeira="Elo"),
        ],
        movimentos=[mov("2026-10-01", "100.00"), mov("2026-10-01", "300.00"),
                    mov("2026-10-01", "500.00")],
        hoje=HOJE,
    )
    igual(len(r["conciliacoes"]), 4, "conciliados")
    igual(len(r["divergencias"]), 0, "divergencias")


@teste(G7, "debito caiu certo e credito veio a menor: concilia um, aponta o outro")
def _():
    r = conciliar(
        recebiveis=[
            rec("2026-10-01", "294.00", modalidade="Debito"),
            rec("2026-10-01", "1000.00", modalidade="Credito"),
        ],
        movimentos=[mov("2026-10-01", "294.00"), mov("2026-10-01", "970.00")],
        hoje=HOJE,
    )
    igual(len(r["conciliacoes"]), 1, "conciliados")
    igual(len(r["divergencias"]), 1, "divergencias")
    igual(r["divergencias"][0]["tipo"], "valor_divergente", "tipo")
    igual(r["divergencias"][0]["valor_esperado"], Decimal("1000.00"), "esperado")
    igual(r["divergencias"][0]["diferenca"], Decimal("-30.00"), "diferenca")


@teste(G7, "debito e credito vieram os dois errados: dois alertas, nada conciliado")
def _():
    r = conciliar(
        recebiveis=[
            rec("2026-10-01", "300.00", modalidade="Debito"),
            rec("2026-10-01", "1000.00", modalidade="Credito"),
        ],
        movimentos=[mov("2026-10-01", "295.00"), mov("2026-10-01", "970.00")],
        hoje=HOJE,
    )
    igual(len(r["conciliacoes"]), 0, "conciliados")
    igual(sorted(d["tipo"] for d in r["divergencias"]),
          ["valor_divergente", "valor_divergente"], "tipos")


@teste(G7, "so caiu o debito: concilia o debito e o credito vira nao recebido")
def _():
    r = conciliar(
        recebiveis=[
            rec("2026-09-01", "100.00", modalidade="Debito"),
            rec("2026-09-01", "250.00", modalidade="Debito"),
            rec("2026-09-01", "900.00", modalidade="Credito"),
        ],
        movimentos=[mov("2026-09-01", "350.00")],
        hoje=HOJE,
    )
    igual(len(r["conciliacoes"]), 2, "conciliados")
    igual([d["tipo"] for d in r["divergencias"]], ["nao_recebido"], "tipos")
    igual(r["divergencias"][0]["valor_esperado"], Decimal("900.00"), "o que faltou")


@teste(G7, "deposito de um dia nao e usado pra fatia de outro dia")
def _():
    r = conciliar(
        recebiveis=[
            rec("2026-09-01", "100.00", modalidade="Debito"),
            rec("2026-09-01", "400.00", modalidade="Credito"),
            rec("2026-09-20", "100.00", modalidade="Debito"),
        ],
        movimentos=[mov("2026-09-01", "100.00"), mov("2026-09-01", "400.00")],
        hoje=HOJE,
    )
    igual(len(r["conciliacoes"]), 2, "conciliados")
    igual([d["tipo"] for d in r["divergencias"]], ["nao_recebido"], "tipos")


@teste(G7, "lote do dia inteiro continua tendo prioridade sobre as fatias")
def _():
    r = conciliar(
        recebiveis=[
            rec("2026-10-01", "100.00", modalidade="Debito"),
            rec("2026-10-01", "400.00", modalidade="Credito"),
        ],
        movimentos=[mov("2026-10-01", "500.00")],
        hoje=HOJE,
    )
    igual(len(r["conciliacoes"]), 2, "conciliados")
    igual({c["como"] for c in r["conciliacoes"]}, {"lote do dia"}, "como casou")


G8 = "DINHEIRO QUE NAO E DA MAQUININHA NAO E CASADO POR ENGANO"


@teste(G8, "PIX de cliente com o mesmo valor do recebivel nao concilia")
def _():
    r = conciliar(
        recebiveis=[rec("2026-09-10", "620.80")],
        movimentos=[mov("2026-09-10", "620.80", descricao="PIX RECEBIDO CLIENTE")],
        hoje=HOJE,
    )
    igual(len(r["conciliacoes"]), 0, "conciliados")
    igual(sorted(d["tipo"] for d in r["divergencias"]),
          ["nao_identificado", "nao_recebido"], "tipos")
    obs = [d for d in r["divergencias"] if d["tipo"] == "nao_identificado"][0]["observacao"]
    igual("dinheiro de cliente" in obs, True, "observacao explica o motivo")


@teste(G8, "TED de cliente com o valor do lote do dia nao concilia")
def _():
    r = conciliar(
        recebiveis=[rec("2026-09-10", "100.00"), rec("2026-09-10", "200.00")],
        movimentos=[mov("2026-09-10", "300.00", descricao="TED RECEBIDA 341 FULANO")],
        hoje=HOJE,
    )
    igual(len(r["conciliacoes"]), 0, "conciliados")


@teste(G8, "PIX de cliente com o valor de uma fatia do dia nao concilia")
def _():
    r = conciliar(
        recebiveis=[rec("2026-09-10", "100.00", modalidade="Debito"),
                    rec("2026-09-10", "700.00", modalidade="Credito")],
        movimentos=[mov("2026-09-10", "100.00", descricao="PIX RECEBIDO CLIENTE"),
                    mov("2026-09-10", "700.00", descricao="CRED CIELO")],
        hoje=HOJE,
    )
    igual(len(r["conciliacoes"]), 1, "conciliados")
    igual(sorted(d["tipo"] for d in r["divergencias"]),
          ["nao_identificado", "nao_recebido"], "tipos")


@teste(G8, "transferencia, deposito, boleto e DOC tambem ficam de fora")
def _():
    for historico in ("TRANSF RECEBIDA", "Transferência entre contas", "DEPOSITO EM DINHEIRO",
                      "Depósito", "LIQUIDACAO BOLETO", "DOC RECEBIDO", "Pix recebido"):
        igual(parece_fora_da_maquininha(historico), True, historico)
        r = conciliar(
            recebiveis=[rec("2026-09-10", "500.00")],
            movimentos=[mov("2026-09-10", "500.00", descricao=historico)],
            hoje=HOJE,
        )
        igual(len(r["conciliacoes"]), 0, "conciliados com " + historico)


@teste(G8, "PIX ou TED que traz o nome da adquirente concilia normalmente")
def _():
    for historico in ("PIX RECEBIDO STONE INSTITUICAO", "TED CIELO S A",
                      "PIX PAGSEGURO INTERNET", "TRANSF GETNET", "CRED REDE VISA"):
        igual(parece_fora_da_maquininha(historico), False, historico)
        r = conciliar(
            recebiveis=[rec("2026-09-10", "500.00")],
            movimentos=[mov("2026-09-10", "500.00", descricao=historico)],
            hoje=HOJE,
        )
        igual(len(r["conciliacoes"]), 1, "conciliados com " + historico)


@teste(G8, "palavra parecida nao engana: CREDITO nao vira REDE, DOCE nao vira DOC")
def _():
    igual(parece_fora_da_maquininha("CREDITO EM CONTA"), False, "credito em conta")
    igual(parece_fora_da_maquininha("DOCERIA DA ANA PIXEL"), False, "doceria")


@teste(G8, "credito da maquininha concilia e o PIX do lado vira entrada sem origem")
def _():
    m_pix = mov("2026-09-10", "500.00", descricao="PIX RECEBIDO CLIENTE")
    m_rede = mov("2026-09-10", "500.00", descricao="CRED REDE VISA")
    r = conciliar(recebiveis=[rec("2026-09-10", "500.00")], movimentos=[m_pix, m_rede],
                  hoje=HOJE)
    igual(len(r["conciliacoes"]), 1, "conciliados")
    igual(r["conciliacoes"][0]["movimento_banco_id"], m_rede["id"], "casou com a Rede")
    igual([d["referencia_id"] for d in r["divergencias"]], [m_pix["id"]], "sobrou o PIX")


@teste(G8, "extrato sem historico continua conciliando pelo valor")
def _():
    r = conciliar(
        recebiveis=[rec("2026-10-01", 500)], movimentos=[mov("2026-10-01", 500)], hoje=HOJE
    )
    igual(len(r["conciliacoes"]), 1, "conciliados")


G9 = "SITUACAO DO RECEBIVEL ESCRITA DO JEITO DO PORTAL"


@teste(G9, "Chargeback com maiuscula ainda vira alerta")
def _():
    r = conciliar(recebiveis=[rec("2026-10-01", 600, status="Chargeback")], movimentos=[],
                  hoje=HOJE)
    igual([d["tipo"] for d in r["divergencias"]], ["chargeback"], "tipos")


@teste(G9, "CANCELADA ou Cancelamento sao ignorados")
def _():
    r = conciliar(
        recebiveis=[rec("2026-09-01", 600, status="CANCELADA"),
                    rec("2026-09-01", 300, status="Cancelamento")],
        movimentos=[], hoje=HOJE,
    )
    igual(len(r["divergencias"]), 0, "divergencias")


G10 = "COLUNAS DA AGENDA"


@teste(G10, "reconhece as colunas Modalidade e Bandeira na agenda")
def _():
    de_para = mapear.sugerir(
        ["Data prevista", "Valor liquido", "Modalidade", "Bandeira"], "recebiveis")
    igual(de_para.get("Modalidade"), "modalidade", "modalidade")
    igual(de_para.get("Bandeira"), "bandeira", "bandeira")


@teste(G10, "agenda sem Modalidade nem Bandeira funciona igual a antes")
def _():
    de_para = mapear.sugerir(["Data prevista", "Valor liquido"], "recebiveis")
    igual(mapear.faltando(de_para, "recebiveis"), [], "campos faltando")


G11 = "ARQUIVO NO FORMATO DA STONE (VALORES FICTICIOS)"

CABECALHO_STONE = (
    "DOCUMENTO;STONECODE;CATEGORIA;DATA DA VENDA;DATA DE VENCIMENTO;"
    "DATA DE VENCIMENTO ORIGINAL;BANDEIRA;PRODUTO;STONE ID;QTD DE PARCELAS;"
    "Nº DA PARCELA;VALOR BRUTO;VALOR LÍQUIDO;DESCONTO DE MDR;"
    "DESCONTO DE ANTECIPAÇÃO;DESCONTO UNIFICADO;ÚLTIMO STATUS;"
    "DATA DO ÚLTIMO STATUS;ENTRADAS BRUTAS;SAÍDAS BRUTAS"
)


def _linha_stone(vencimento, original, bandeira, produto, bruto, liquido):
    return (f"00.000.000/0001-00;000000000;Venda;{vencimento} 10:00:00;{vencimento};"
            f"{original};{bandeira};{produto};00000000000000;1;1;{bruto};{liquido};"
            f"0,000000;0,000000;-0,272000;Pago;{vencimento} 00:00:00;{bruto};0,000000")


@teste(G11, "liquido com 6 casas: soma exata, sem acumular centavo de arredondamento")
def _():
    # 20 vendas de 19,728: exato da 394,56. Arredondando uma por uma (19,73)
    # daria 394,60 e o lote nunca bateria.
    r = conciliar(
        recebiveis=[rec("2026-10-01", "19.728000") for _ in range(20)],
        movimentos=[mov("2026-10-01", "394.56")],
        hoje=HOJE,
    )
    igual(len(r["conciliacoes"]), 20, "conciliados")
    igual(len(r["divergencias"]), 0, "divergencias")


@teste(G11, "reconhece as colunas da agenda da Stone")
def _():
    de_para = mapear.sugerir(CABECALHO_STONE.split(";"), "recebiveis")
    igual(de_para.get("DATA DE VENCIMENTO"), "data_prevista", "data prevista")
    igual(de_para.get("VALOR LÍQUIDO"), "valor_liquido", "valor liquido")
    igual(de_para.get("PRODUTO"), "modalidade", "modalidade")
    igual(de_para.get("BANDEIRA"), "bandeira", "bandeira")
    igual(de_para.get("QTD DE PARCELAS"), "total_parcelas", "total de parcelas")
    igual(de_para.get("Nº DA PARCELA"), "numero_parcela", "numero da parcela")
    igual(de_para.get("ÚLTIMO STATUS"), "status", "situacao")
    igual("DATA DE VENCIMENTO ORIGINAL" in de_para, False, "vencimento original fica de fora")


@teste(G11, "CSV da Stone do inicio ao fim: debito e credito em depositos separados")
def _():
    import os
    import tempfile
    from concilia import planilha
    linhas = [
        CABECALHO_STONE,
        _linha_stone("01/10/2026", "01/10/2026", "MasterCard", "Debito", "20,000000", "19,728000"),
        _linha_stone("01/10/2026", "01/10/2026", "Visa", "Debito Pre-pago", "13,000000", "12,823200"),
        _linha_stone("01/10/2026", "31/10/2026", "Visa", "Credito", "22,000000", "21,155200"),
        _linha_stone("01/10/2026", "31/10/2026", "Elo", "Credito Pre-pago", "9,000000", "8,654400"),
    ]
    with tempfile.TemporaryDirectory() as pasta:
        caminho = os.path.join(pasta, "agenda-stone.csv")
        with open(caminho, "w", encoding="utf-8-sig") as f:
            f.write("\n".join(linhas) + "\n")
        brutas = planilha.ler(caminho)
    de_para = mapear.sugerir(list(brutas[0].keys()), "recebiveis")
    registros, ignoradas = mapear.aplicar(brutas, de_para, "recebiveis")
    igual(ignoradas, 0, "linhas ignoradas")
    r = conciliar(
        recebiveis=registros,
        movimentos=[mov("2026-10-01", "32.55", descricao="TED STONE INSTITUICAO DE PAGAMENTO"),
                    mov("2026-10-01", "29.81", descricao="TED STONE INSTITUICAO DE PAGAMENTO")],
        hoje=HOJE,
    )
    igual(len(r["conciliacoes"]), 4, "conciliados")
    igual(len(r["divergencias"]), 0, "divergencias")
