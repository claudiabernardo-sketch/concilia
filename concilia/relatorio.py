"""O relatorio em Excel que a pessoa manda pro cliente.

Tres abas: Resumo (a capa, pra entender em 5 segundos), Divergências
(cada problema) e Conciliados (o que bateu e como bateu).
"""

from decimal import Decimal

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# Cores do visual (as mesmas da tela)
INDIGO = "6366F1"
ROXO = "A855F7"
TINTA = "1E293B"
CINZA = "64748B"
BORDA = "E2E8F0"
FUNDO = "F8FAFC"
FUNDO_INDIGO = "EEF2FF"
VERDE = "059669"
FUNDO_VERDE = "ECFDF5"
VERMELHO = "DC2626"
FUNDO_VERMELHO = "FEF2F2"
AMBAR = "B45309"
FUNDO_AMBAR = "FFFBEB"

FONTE = "Calibri"
MOEDA = 'R$ #,##0.00;[Red]-R$ #,##0.00;"-"'

_linha = Side(style="thin", color=BORDA)
BORDA_CELULA = Border(left=_linha, right=_linha, top=_linha, bottom=_linha)

CORES_GRAVIDADE = {
    "alta": (VERMELHO, FUNDO_VERMELHO),
    "media": (AMBAR, FUNDO_AMBAR),
    "baixa": (CINZA, FUNDO),
}


def _valor(texto):
    return None if texto is None else float(Decimal(texto))


def _cabecalho(aba, linha, titulos):
    for i, titulo in enumerate(titulos, start=1):
        c = aba.cell(row=linha, column=i, value=titulo)
        c.font = Font(name=FONTE, bold=True, color="FFFFFF", size=11)
        c.fill = PatternFill("solid", fgColor=INDIGO)
        c.alignment = Alignment(vertical="center", horizontal="left", indent=1)
        c.border = BORDA_CELULA
    aba.row_dimensions[linha].height = 26


def _corpo(aba, linha, valores, zebra, moedas=(), quebra=()):
    for i, v in enumerate(valores, start=1):
        c = aba.cell(row=linha, column=i, value=v)
        c.font = Font(name=FONTE, color=TINTA, size=11)
        c.border = BORDA_CELULA
        c.alignment = Alignment(vertical="center", indent=1, wrap_text=i in quebra)
        if zebra:
            c.fill = PatternFill("solid", fgColor=FUNDO)
        if i in moedas:
            c.number_format = MOEDA
            c.alignment = Alignment(vertical="center", horizontal="right", indent=1)


def _larguras(aba, larguras):
    for i, w in enumerate(larguras, start=1):
        aba.column_dimensions[get_column_letter(i)].width = w


def _aba_resumo(aba, dados):
    r = dados["resumo"]
    aba.sheet_view.showGridLines = False
    _larguras(aba, (2, 34, 22, 22, 22, 2))

    aba["B2"] = "Relatório de conciliação de cartão"
    aba["B2"].font = Font(name=FONTE, bold=True, size=20, color=TINTA)
    aba.row_dimensions[2].height = 32
    arquivos = dados.get("arquivos", {})
    agendas = [i["nome"] for i in arquivos.get("agendas", [])] or [arquivos.get("agenda", {}).get("nome", "")]
    extratos = [i["nome"] for i in arquivos.get("extratos", [])] or [arquivos.get("extrato", {}).get("nome", "")]
    rot_a = "Agendas" if len(agendas) > 1 else "Agenda"
    rot_e = "Extratos" if len(extratos) > 1 else "Extrato"
    aba["B3"] = (f"Gerado em {dados.get('gerado_em', '')}  ·  {rot_a}: {', '.join(agendas)}"
                 f"  ·  {rot_e}: {', '.join(extratos)}")
    aba["B3"].font = Font(name=FONTE, size=10, color=CINZA)

    # Faixa colorida embaixo do titulo
    for col in range(2, 6):
        aba.cell(row=4, column=col).fill = PatternFill(
            "solid", fgColor=INDIGO if col < 4 else ROXO)
    aba.row_dimensions[4].height = 4

    cartoes = [
        ("Conciliados", f"{r['conciliados']} de {r['recebiveis']}", VERDE, FUNDO_VERDE),
        ("Valor conciliado", _valor(r["valor_conciliado"]), VERDE, FUNDO_VERDE),
        ("Precisam de atenção", r["atencao"], VERMELHO if r["atencao"] else VERDE,
         FUNDO_VERMELHO if r["atencao"] else FUNDO_VERDE),
        ("Dinheiro em jogo", _valor(r["valor_em_jogo"]), INDIGO, FUNDO_INDIGO),
    ]
    # Dois cartoes por linha, nas colunas B-C e D-E
    posicoes = [(6, 2), (6, 4), (9, 2), (9, 4)]
    for (rotulo, valor, cor, fundo), (lin, col) in zip(cartoes, posicoes):
        for dl in (0, 1):
            for dc in (0, 1):
                aba.cell(row=lin + dl, column=col + dc).fill = PatternFill("solid", fgColor=fundo)
        aba.merge_cells(start_row=lin, start_column=col, end_row=lin, end_column=col + 1)
        aba.merge_cells(start_row=lin + 1, start_column=col, end_row=lin + 1, end_column=col + 1)
        t = aba.cell(row=lin, column=col, value=rotulo)
        t.font = Font(name=FONTE, size=10, bold=True, color=CINZA)
        t.alignment = Alignment(indent=1, vertical="bottom")
        v = aba.cell(row=lin + 1, column=col, value=valor)
        v.font = Font(name=FONTE, size=18, bold=True, color=cor)
        v.alignment = Alignment(indent=1, vertical="top", horizontal="left")
        if isinstance(valor, float):
            v.number_format = 'R$ #,##0.00'
        aba.row_dimensions[lin].height = 20
        aba.row_dimensions[lin + 1].height = 30

    linha = 12
    aba.cell(row=linha, column=2, value="Onde está o dinheiro em jogo").font = Font(
        name=FONTE, bold=True, size=13, color=TINTA)
    linha += 1
    if r["por_tipo"]:
        aba.cell(row=linha, column=1)
        for i, titulo in enumerate(["Tipo de problema", "Casos", "Valor"], start=2):
            c = aba.cell(row=linha, column=i, value=titulo)
            c.font = Font(name=FONTE, bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor=INDIGO)
            c.alignment = Alignment(indent=1, vertical="center")
            c.border = BORDA_CELULA
        aba.row_dimensions[linha].height = 24
        for n, t in enumerate(r["por_tipo"]):
            linha += 1
            for i, v in enumerate([t["nome"], t["quantidade"], _valor(t["valor"])], start=2):
                c = aba.cell(row=linha, column=i, value=v)
                c.font = Font(name=FONTE, color=TINTA)
                c.border = BORDA_CELULA
                c.alignment = Alignment(indent=1, vertical="center",
                                        horizontal="right" if i > 2 else "left")
                if n % 2:
                    c.fill = PatternFill("solid", fgColor=FUNDO)
                if i == 4:
                    c.number_format = 'R$ #,##0.00'
            aba.row_dimensions[linha].height = 22
    else:
        c = aba.cell(row=linha, column=2, value="Tudo bateu. Nenhuma divergência.")
        c.font = Font(name=FONTE, bold=True, color=VERDE, size=12)

    linha += 2
    aba.cell(row=linha, column=2,
             value="Os detalhes estão nas abas Divergências e Conciliados.").font = Font(
        name=FONTE, size=10, color=CINZA)
    aba.cell(row=linha + 1, column=2,
             value="Versão de teste: confira o relatório antes de mandar para o cliente.").font = Font(
        name=FONTE, size=10, italic=True, color=CINZA)
    aba.sheet_properties.tabColor = INDIGO


def _aba_divergencias(aba, dados):
    aba.sheet_view.showGridLines = False
    _cabecalho(aba, 1, ["Problema", "Gravidade", "Data", "Competência", "Esperado",
                        "Encontrado", "Diferença", "Observação", "Arquivo"])
    for n, d in enumerate(dados["divergencias"]):
        linha = n + 2
        _corpo(aba, linha, [
            d["nome"], d["gravidade_nome"], d["data"], d["competencia"],
            _valor(d["esperado"]), _valor(d["encontrado"]), _valor(d["diferenca"]),
            d["observacao"], d.get("arquivo", ""),
        ], zebra=n % 2 == 1, moedas=(5, 6, 7), quebra=(8,))
        cor, fundo = CORES_GRAVIDADE.get(d["gravidade"], (CINZA, FUNDO))
        g = aba.cell(row=linha, column=2)
        g.font = Font(name=FONTE, bold=True, color=cor)
        g.fill = PatternFill("solid", fgColor=fundo)
        g.alignment = Alignment(horizontal="center", vertical="center")
        aba.cell(row=linha, column=1).font = Font(name=FONTE, bold=True, color=TINTA)
        aba.row_dimensions[linha].height = 34
    if not dados["divergencias"]:
        c = aba.cell(row=2, column=1, value="Nenhuma divergência. Tudo bateu.")
        c.font = Font(name=FONTE, bold=True, color=VERDE)
    _larguras(aba, (32, 12, 13, 13, 15, 15, 15, 70, 28))
    aba.freeze_panes = "A2"
    if dados["divergencias"]:
        aba.auto_filter.ref = f"A1:I{len(dados['divergencias']) + 1}"
    aba.sheet_properties.tabColor = VERMELHO


def _aba_conciliados(aba, dados):
    aba.sheet_view.showGridLines = False
    _cabecalho(aba, 1, ["Data prevista", "Modalidade", "Bandeira", "Valor líquido",
                        "Caiu no banco em", "Valor do depósito", "Histórico do banco",
                        "Como casou", "Conta (extrato)", "Agenda"])
    for n, c in enumerate(dados["conciliados"]):
        _corpo(aba, n + 2, [
            c["data_prevista"], c["modalidade"], c["bandeira"], _valor(c["valor_liquido"]),
            c["data_banco"], _valor(c["valor_deposito"]), c["historico"], c["como"],
            c.get("conta", ""), c.get("agenda", ""),
        ], zebra=n % 2 == 1, moedas=(4, 6))
        aba.cell(row=n + 2, column=8).font = Font(name=FONTE, color=VERDE)
        aba.row_dimensions[n + 2].height = 22
    if not dados["conciliados"]:
        aba.cell(row=2, column=1, value="Nada foi conciliado.").font = Font(name=FONTE, color=CINZA)
    _larguras(aba, (15, 20, 14, 16, 18, 18, 34, 34, 26, 26))
    aba.freeze_panes = "A2"
    if dados["conciliados"]:
        aba.auto_filter.ref = f"A1:J{len(dados['conciliados']) + 1}"
    aba.sheet_properties.tabColor = VERDE


def gravar(dados, destino):
    """Grava o relatorio. destino pode ser um caminho ou um arquivo em memoria."""
    pasta = Workbook()
    resumo = pasta.active
    resumo.title = "Resumo"
    _aba_resumo(resumo, dados)
    _aba_divergencias(pasta.create_sheet("Divergências"), dados)
    _aba_conciliados(pasta.create_sheet("Conciliados"), dados)
    pasta.active = 0
    pasta.save(destino)
    return destino
