"""Concilia, conciliadora de cartao.

Use assim:

    python conciliar.py agenda.xlsx extrato.xlsx

Nao precisa de internet, de conta em lugar nenhum, nem de instalar banco
de dados. Le as duas planilhas, cruza, e escreve um relatorio em Excel.

Prefere uma tela? Rode  python abrir_concilia.py
"""

import argparse
import sys
from datetime import date
from pathlib import Path

from concilia import relatorio
from concilia.formato import moeda
from concilia.servico import ArquivoComProblema, executar_varios

NOMES_TIPO = {
    "taxa_maior":        "Taxa cobrada a maior",
    "taxa_menor":        "Taxa cobrada a menor",
    "nao_recebido":      "Previsto e nao recebido",
    "valor_divergente":  "Valor diferente do previsto",
    "recebido_atrasado": "Recebido com atraso",
    "chargeback":        "Chargeback",
    "nao_identificado":  "Entrada sem origem identificada",
}

ROTULOS = {"recebiveis": "Agenda de recebiveis", "extrato": "Extrato bancario"}


def mostrar_leitura(tipo, info):
    print(f"\n{ROTULOS[tipo]}: {info['nome']}")
    for campo, coluna in info["colunas"]:
        print(f"  {campo:<24} <- coluna \"{coluna}\"")
    print(f"  {info['linhas']} linhas lidas", end="")
    print(f", {info['ignoradas']} ignoradas por falta de dado" if info["ignoradas"] else "")


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


def main():
    analisador = argparse.ArgumentParser(
        description="Concilia a agenda de recebiveis da maquininha com o extrato do banco.",
    )
    analisador.add_argument("agenda", help="planilha da agenda de recebiveis (.xlsx ou .csv)")
    analisador.add_argument("extrato", help="planilha do extrato bancario (.xlsx ou .csv)")
    analisador.add_argument("-s", "--saida", help="onde gravar o relatorio (.xlsx)")
    analisador.add_argument("--outra-agenda", action="append", default=[], metavar="ARQUIVO",
                            help="mais uma agenda (ex.: vale-refeicao). Pode repetir.")
    analisador.add_argument("--outro-extrato", action="append", default=[], metavar="ARQUIVO",
                            help="extrato de mais uma conta. Pode repetir.")
    argumentos = analisador.parse_args()

    print("=" * 68)
    print("CONCILIA")
    print("=" * 68)
    print("VERSAO DE TESTE: confira o relatorio antes de mandar para o cliente.")

    try:
        agendas = [argumentos.agenda] + argumentos.outra_agenda
        extratos = [argumentos.extrato] + argumentos.outro_extrato
        tudo = executar_varios([(a, Path(a).name) for a in agendas],
                               [(e, Path(e).name) for e in extratos])
    except ArquivoComProblema as e:
        print(f"\n{ROTULOS[e.tipo]}: {e.nome}")
        if e.colunas:
            print(f"  Nao achei: {', '.join(e.faltando)}")
            print("  Colunas que o arquivo tem:")
            for c in e.colunas:
                print(f"    - {c}")
            erro("Renomeie a coluna na planilha pra um nome que o sistema reconheca "
                 "(por exemplo 'Data prevista' e 'Valor liquido') e rode de novo.")
        erro(e.mensagem)

    for info in tudo["dados"]["arquivos"]["agendas"]:
        mostrar_leitura("recebiveis", info)
    for info in tudo["dados"]["arquivos"]["extratos"]:
        mostrar_leitura("extrato", info)
    mostrar_resultado(tudo["resultado"])

    saida = argumentos.saida or f"relatorio-{date.today():%Y-%m-%d}.xlsx"
    try:
        relatorio.gravar(tudo["dados"], saida)
    except PermissionError:
        erro(f"Nao consegui gravar {saida}. Se ele estiver aberto no Excel, feche e rode de novo.")

    print(f"Relatorio gravado em: {Path(saida).resolve()}\n")


if __name__ == "__main__":
    main()
