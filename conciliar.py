"""Concilia, conciliadora de cartao.

Use assim:

    python conciliar.py agenda.xlsx extrato.xlsx

Nao precisa de internet, de conta em lugar nenhum, nem de instalar banco
de dados. Le as duas planilhas, cruza, e escreve um relatorio em Excel.
"""

import argparse
import sys
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from concilia import mapear, planilha
from concilia.formato import data_br, moeda
from concilia.motor import conciliar

NOMES_TIPO = {
    "taxa_maior":        "Taxa cobrada a maior",
    "taxa_menor":        "Taxa cobrada a menor",
    "nao_recebido":      "Previsto e nao recebido",
    "valor_divergente":  "Valor diferente do previsto",
    "recebido_atrasado": "Recebido com atraso",
    "chargeback":        "Chargeback",
    "nao_identificado":  "Entrada sem origem identificada",
}


def carregar(caminho, tipo, rotulo):
    """Le a planilha, descobre as colunas e devolve os registros."""
    print(f"\n{rotulo}: {Path(caminho).name}")

    linhas = planilha.ler(caminho)
    if not linhas:
        erro(f"O arquivo {Path(caminho).name} esta vazio ou nao tem cabecalho.")

    cabecalhos = list(linhas[0].keys())
    de_para = mapear.sugerir(cabecalhos, tipo)

    pendentes = mapear.faltando(de_para, tipo)
    if pendentes:
        print(f"  Li {len(linhas)} linhas, mas nao achei: {', '.join(pendentes)}")
        print("  Colunas que o arquivo tem:")
        for c in cabecalhos:
            print(f"    - {c}")
        erro(
            "Renomeie a coluna na planilha pra um nome que o sistema reconheca "
            "(por exemplo 'Data prevista' e 'Valor liquido') e rode de novo."
        )

    por_chave = {c[0]: c[1] for c in mapear.CAMPOS[tipo]["campos"]}
    for cabecalho, chave in sorted(de_para.items(), key=lambda x: x[1]):
        print(f"  {por_chave[chave]:<24} <- coluna \"{cabecalho}\"")

    registros, ignoradas = mapear.aplicar(linhas, de_para, tipo)
    print(f"  {len(registros)} linhas lidas", end="")
    print(f", {ignoradas} ignoradas por falta de dado" if ignoradas else "")

    return registros


def erro(mensagem):
    print(f"\nPAROU AQUI: {mensagem}\n")
    sys.exit(1)


def mostrar_resultado(resultado):
    resumo = resultado["resumo"]

    print("\n" + "=" * 68)
    print("RESULTADO")
    print("=" * 68)
    print(f"  Recebiveis analisados   {resumo['recebiveis_analisados']:>6}")
    print(f"  Lancamentos do banco    {resumo['movimentos_analisados']:>6}")
    print(f"  Conciliados             {resumo['conciliados']:>6}")
    print(f"  Precisam de atencao     {resumo['divergencias']:>6}")

    if not resumo["por_tipo"]:
        print("\n  Nenhuma divergencia. Tudo bateu.\n")
        return

    print("\n  Dinheiro em jogo, por tipo de problema:\n")
    ordenado = sorted(resumo["por_tipo"].items(), key=lambda x: x[1]["valor"], reverse=True)
    for tipo, info in ordenado:
        nome = NOMES_TIPO.get(tipo, tipo)
        casos = f"{info['quantidade']} caso" + ("s" if info["quantidade"] > 1 else "")
        print(f"    {nome:<34} {casos:>10}   {moeda(info['valor']):>16}")
    print()


def gravar_excel(resultado, destino, recebiveis=(), movimentos=()):
    """Escreve o relatorio que voce manda pro cliente."""
    rec_por_id = {r["id"]: r for r in recebiveis}
    mov_por_id = {m["id"]: m for m in movimentos}

    def data_da(d):
        if d["referencia_tipo"] == "recebivel" and d["referencia_id"] in rec_por_id:
            return data_br(rec_por_id[d["referencia_id"]]["data_prevista"])
        if d["referencia_tipo"] == "movimento" and d["referencia_id"] in mov_por_id:
            return data_br(mov_por_id[d["referencia_id"]]["data"])
        return "-"

    pasta = Workbook()

    aba = pasta.active
    aba.title = "Divergencias"

    cabecalho = ["Problema", "Gravidade", "Data", "Competencia", "Esperado", "Encontrado",
                 "Diferenca", "Observacao"]
    aba.append(cabecalho)

    negrito = Font(bold=True, color="FFFFFF")
    fundo = PatternFill("solid", fgColor="0F766E")
    for celula in aba[1]:
        celula.font = negrito
        celula.fill = fundo
        celula.alignment = Alignment(vertical="center")

    ordem = {"alta": 0, "media": 1, "baixa": 2}
    divergencias = sorted(
        resultado["divergencias"],
        key=lambda d: (ordem.get(d["gravidade"], 9), -abs(d.get("diferenca") or 0)),
    )

    for d in divergencias:
        aba.append([
            NOMES_TIPO.get(d["tipo"], d["tipo"]),
            d["gravidade"],
            data_da(d),
            f"{d['competencia']:%m/%Y}",
            float(d["valor_esperado"]) if d["valor_esperado"] is not None else None,
            float(d["valor_encontrado"]) if d["valor_encontrado"] is not None else None,
            float(d["diferenca"]) if d["diferenca"] is not None else None,
            d["observacao"],
        ])

    for coluna in ("E", "F", "G"):
        for celula in aba[coluna][1:]:
            celula.number_format = 'R$ #,##0.00'

    larguras = {"A": 34, "B": 12, "C": 12, "D": 12, "E": 14, "F": 14, "G": 14, "H": 70}
    for coluna, largura in larguras.items():
        aba.column_dimensions[coluna].width = largura
    aba.freeze_panes = "A2"

    # Segunda aba: o resumo, pra abrir e entender em 5 segundos.
    resumo_aba = pasta.create_sheet("Resumo")
    resumo_aba.append(["Tipo de problema", "Casos", "Valor"])
    for celula in resumo_aba[1]:
        celula.font = negrito
        celula.fill = fundo

    for tipo, info in sorted(
        resultado["resumo"]["por_tipo"].items(), key=lambda x: x[1]["valor"], reverse=True
    ):
        resumo_aba.append([NOMES_TIPO.get(tipo, tipo), info["quantidade"], float(info["valor"])])

    for celula in resumo_aba["C"][1:]:
        celula.number_format = 'R$ #,##0.00'
    resumo_aba.column_dimensions["A"].width = 34
    resumo_aba.column_dimensions["B"].width = 10
    resumo_aba.column_dimensions["C"].width = 16

    # Terceira aba: o que bateu, pra voce conferir de onde veio cada casamento.
    ok_aba = pasta.create_sheet("Conciliados")
    ok_aba.append(["Data prevista", "Modalidade", "Bandeira", "Valor liquido",
                   "Caiu no banco em", "Valor do deposito", "Historico do banco", "Como casou"])
    for celula in ok_aba[1]:
        celula.font = negrito
        celula.fill = fundo
    for c in resultado["conciliacoes"]:
        r = rec_por_id.get(c["recebivel_id"], {})
        m = mov_por_id.get(c["movimento_banco_id"], {})
        ok_aba.append([
            data_br(r.get("data_prevista")),
            r.get("modalidade") or "",
            r.get("bandeira") or "",
            float(r["valor_liquido"]) if r.get("valor_liquido") is not None else None,
            data_br(m.get("data")),
            float(m["valor"]) if m.get("valor") is not None else None,
            m.get("descricao") or "",
            c.get("como", ""),
        ])
    for coluna in ("D", "F"):
        for celula in ok_aba[coluna][1:]:
            celula.number_format = 'R$ #,##0.00'
    for coluna, largura in zip("ABCDEFGH", (14, 20, 14, 14, 16, 16, 32, 40)):
        ok_aba.column_dimensions[coluna].width = largura
    ok_aba.freeze_panes = "A2"

    pasta.save(destino)
    return destino


def main():
    analisador = argparse.ArgumentParser(
        description="Concilia a agenda de recebiveis da maquininha com o extrato do banco.",
    )
    analisador.add_argument("agenda", help="planilha da agenda de recebiveis (.xlsx ou .csv)")
    analisador.add_argument("extrato", help="planilha do extrato bancario (.xlsx ou .csv)")
    analisador.add_argument("-s", "--saida", help="onde gravar o relatorio (.xlsx)")
    argumentos = analisador.parse_args()

    print("=" * 68)
    print("CONCILIA")
    print("=" * 68)
    print("VERSAO DE TESTE: confira o relatorio antes de mandar para o cliente.")

    try:
        recebiveis = carregar(argumentos.agenda, "recebiveis", "Agenda de recebiveis")
        movimentos = carregar(argumentos.extrato, "extrato", "Extrato bancario")
    except (FileNotFoundError, ValueError) as e:
        erro(str(e))

    resultado = conciliar(recebiveis=recebiveis, movimentos=movimentos)
    mostrar_resultado(resultado)

    saida = argumentos.saida or f"relatorio-{date.today():%Y-%m-%d}.xlsx"
    try:
        gravar_excel(resultado, saida, recebiveis, movimentos)
    except PermissionError:
        erro(f"Nao consegui gravar {saida}. Se ele estiver aberto no Excel, feche e rode de novo.")

    print(f"Relatorio gravado em: {Path(saida).resolve()}\n")


if __name__ == "__main__":
    main()
