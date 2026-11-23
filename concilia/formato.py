"""Leitura de valores e datas no padrao brasileiro.

Dinheiro aqui nunca vira numero quebrado comum (float). Vira Decimal, que
e o tipo do Python feito pra dinheiro. Sem isso, 0.1 + 0.2 da 0.30000000000004
e a conciliacao comeca a reclamar de centavos que nao existem.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re

CENTAVO = Decimal("0.01")
ZERO = Decimal("0")


def arredondar(valor) -> Decimal:
    """Deixa o valor com duas casas, arredondando como banco arredonda."""
    if valor is None:
        return ZERO
    if not isinstance(valor, Decimal):
        valor = Decimal(str(valor))
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def para_numero(bruto):
    """Le qualquer formato de valor que as adquirentes mandam.

    Entende '1.234,56', '1234.56', 'R$ 1.234,56', '(1.234,56)' como negativo,
    e numeros que ja vieram prontos da planilha.
    """
    if bruto is None or bruto == "":
        return None
    if isinstance(bruto, Decimal):
        return bruto
    if isinstance(bruto, bool):
        return None
    if isinstance(bruto, (int, float)):
        return Decimal(str(bruto))

    texto = str(bruto).strip()
    if not texto:
        return None

    # Contabilidade escreve negativo entre parenteses.
    negativo = texto.startswith("(") and texto.endswith(")")
    if "-" in texto:
        negativo = True

    texto = texto.replace("(", "").replace(")", "")
    texto = re.sub(r"R\$", "", texto, flags=re.IGNORECASE)
    texto = texto.replace(" ", "").replace("\xa0", "").replace("-", "")
    if not texto:
        return None

    tem_virgula = "," in texto
    tem_ponto = "." in texto

    if tem_virgula and tem_ponto:
        # O separador decimal e o que aparece por ultimo.
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif tem_virgula:
        texto = texto.replace(",", ".")

    try:
        valor = Decimal(texto)
    except InvalidOperation:
        return None

    return -valor if negativo else valor


def para_data(bruto):
    """Le a data em qualquer formato e devolve um date do Python.

    Entende 31/12/2025, 2025-12-31, 01-02-2026, 05/06/26, o numero de serie
    que o Excel usa por dentro, e datas que a planilha ja entregou prontas.
    """
    if bruto is None or bruto == "":
        return None
    if isinstance(bruto, datetime):
        return bruto.date()
    if isinstance(bruto, date):
        return bruto

    # Planilha antiga guarda data como quantidade de dias desde 1900.
    if isinstance(bruto, (int, float)) and not isinstance(bruto, bool):
        try:
            return date.fromordinal(date(1899, 12, 30).toordinal() + int(bruto))
        except (ValueError, OverflowError):
            return None

    texto = str(bruto).strip()

    achado = re.match(r"^(\d{4})-(\d{2})-(\d{2})", texto)
    if achado:
        return _montar(achado.group(1), achado.group(2), achado.group(3))

    achado = re.match(r"^(\d{2})[/-](\d{2})[/-](\d{4})", texto)
    if achado:
        return _montar(achado.group(3), achado.group(2), achado.group(1))

    achado = re.match(r"^(\d{2})[/-](\d{2})[/-](\d{2})$", texto)
    if achado:
        return _montar("20" + achado.group(3), achado.group(2), achado.group(1))

    return None


def _montar(ano, mes, dia):
    try:
        return date(int(ano), int(mes), int(dia))
    except ValueError:
        return None


def moeda(valor) -> str:
    """Formata pra leitura humana: R$ 1.234,56"""
    if valor is None:
        return "-"
    valor = arredondar(valor)
    texto = f"{abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    sinal = "-" if valor < 0 else ""
    return f"{sinal}R$ {texto}"


def data_br(valor) -> str:
    """Formata pra leitura humana: 31/12/2025"""
    if valor is None:
        return "-"
    if isinstance(valor, str):
        valor = para_data(valor)
        if valor is None:
            return "-"
    return valor.strftime("%d/%m/%Y")


def competencia_de(dia: date) -> date:
    """O mes de referencia de uma data, sempre no dia 1."""
    return date(dia.year, dia.month, 1)
