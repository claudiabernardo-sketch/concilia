"""Leitura de planilhas das adquirentes (Excel e CSV).

Os portais exportam de tudo: xlsx, csv separado por ponto e virgula,
acentuacao em latin-1. Essa camada resolve isso antes de o motor ver
qualquer coisa.
"""

import csv
import io
from pathlib import Path

from openpyxl import load_workbook


def ler(caminho) -> list[dict]:
    """Le a planilha e devolve as linhas como dicionarios.

    As chaves sao os nomes das colunas, exatamente como estao no arquivo.
    """
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(f"Nao achei o arquivo: {caminho}")

    if caminho.suffix.lower() in (".xlsx", ".xlsm"):
        return _ler_excel(caminho)
    if caminho.suffix.lower() in (".csv", ".txt"):
        return _ler_csv(caminho)

    raise ValueError(
        f"Nao sei ler arquivo {caminho.suffix}. "
        "Use .xlsx ou .csv. Se voce tem .xls antigo, abra no Excel e salve como .xlsx."
    )


def _ler_excel(caminho) -> list[dict]:
    pasta = load_workbook(caminho, data_only=True, read_only=True)
    aba = pasta[pasta.sheetnames[0]]

    linhas = aba.iter_rows(values_only=True)
    cabecalhos = _achar_cabecalho(linhas)
    if cabecalhos is None:
        return []

    resultado = []
    for linha in linhas:
        if all(c is None or str(c).strip() == "" for c in linha):
            continue
        resultado.append(dict(zip(cabecalhos, linha)))

    pasta.close()
    return resultado


def _achar_cabecalho(linhas):
    """Pula as linhas de titulo que os portais colocam antes da tabela.

    O cabecalho de verdade e a primeira linha com pelo menos 2 celulas
    preenchidas e sem numeros soltos.
    """
    for linha in linhas:
        preenchidas = [c for c in linha if c is not None and str(c).strip() != ""]
        if len(preenchidas) >= 2:
            return [
                str(c).strip() if c is not None else f"coluna_{i + 1}"
                for i, c in enumerate(linha)
            ]
    return None


def _ler_csv(caminho) -> list[dict]:
    bruto = Path(caminho).read_bytes()

    texto = None
    for codificacao in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            texto = bruto.decode(codificacao)
            break
        except UnicodeDecodeError:
            continue
    if texto is None:
        raise ValueError("Nao consegui entender a acentuacao desse CSV.")

    # No Brasil o separador costuma ser ponto e virgula, porque a virgula
    # ja e usada no decimal.
    amostra = texto[:4000]
    separador = ";" if amostra.count(";") > amostra.count(",") else ","

    leitor = csv.reader(io.StringIO(texto), delimiter=separador)
    linhas = list(leitor)
    if not linhas:
        return []

    indice_cabecalho = 0
    for i, linha in enumerate(linhas):
        if len([c for c in linha if c.strip()]) >= 2:
            indice_cabecalho = i
            break

    cabecalhos = [c.strip() or f"coluna_{j + 1}" for j, c in enumerate(linhas[indice_cabecalho])]

    resultado = []
    for linha in linhas[indice_cabecalho + 1:]:
        if not any(c.strip() for c in linha):
            continue
        resultado.append(dict(zip(cabecalhos, linha)))

    return resultado
