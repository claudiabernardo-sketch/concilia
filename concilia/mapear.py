"""Descobre de qual coluna vem cada informacao.

Cada adquirente nomeia as colunas do seu jeito. Em vez de escrever um
leitor por adquirente, o sistema olha o nome da coluna e chuta. Acerta a
maioria. Quando falta um campo obrigatorio, o sistema para e pergunta,
nunca adivinha.
"""

import unicodedata

from .formato import para_numero, para_data

# Os campos que o sistema entende, por tipo de arquivo.
CAMPOS = {
    "recebiveis": {
        "titulo": "Agenda de recebiveis",
        "campos": [
            ("data_prevista",     "Data prevista",        "data",   True),
            ("valor_liquido",     "Valor liquido",        "numero", True),
            ("valor_bruto",       "Valor bruto",          "numero", False),
            ("valor_taxa",        "Valor da taxa (R$)",   "numero", False),
            ("valor_antecipacao", "Custo de antecipacao", "numero", False),
            ("numero_parcela",    "Parcela numero",       "inteiro", False),
            ("total_parcelas",    "Total de parcelas",    "inteiro", False),
            ("data_paga",         "Data do pagamento",    "data",   False),
            ("status",            "Situacao",             "texto",  False),
            ("modalidade",        "Modalidade",           "texto",  False),
            ("bandeira",          "Bandeira",             "texto",  False),
        ],
    },
    "extrato": {
        "titulo": "Extrato bancario",
        "campos": [
            ("data",       "Data",          "data",   True),
            ("valor",      "Valor",         "numero", True),
            ("descricao",  "Historico",     "texto",  False),
            ("id_externo", "Identificador", "texto",  False),
        ],
    },
    "vendas": {
        "titulo": "Vendas no cartao",
        "campos": [
            ("data_venda",         "Data da venda",         "data",   True),
            ("valor_bruto",        "Valor bruto",           "numero", True),
            ("nsu",                "NSU / Doc",             "texto",  False),
            ("codigo_autorizacao", "Codigo de autorizacao", "texto",  False),
            ("bandeira",           "Bandeira",              "texto",  False),
            ("modalidade",         "Modalidade",            "texto",  False),
            ("parcelas",           "Parcelas",              "inteiro", False),
            ("valor_taxa",         "Valor da taxa (R$)",    "numero", False),
            ("taxa_percentual",    "Taxa (%)",              "numero", False),
            ("valor_liquido",      "Valor liquido",         "numero", False),
        ],
    },
}

PISTAS = {
    "data_venda":         ["data da venda", "data venda", "dt venda", "data transacao", "data da transacao"],
    "data_prevista":      ["data prevista", "previsao", "data de pagamento", "data pagamento", "vencimento"],
    "data_paga":          ["data paga", "data do credito", "data credito", "pago em"],
    "data":               ["data", "dt"],
    "valor_bruto":        ["valor bruto", "bruto", "valor da venda", "valor original"],
    "valor_liquido":      ["valor liquido", "liquido", "valor a receber", "valor recebido"],
    "valor_taxa":         ["valor da taxa", "taxa r$", "desconto", "valor mdr", "comissao"],
    "taxa_percentual":    ["taxa %", "percentual", "taxa (%)", "mdr"],
    "valor_antecipacao":  ["antecipacao", "custo antecipacao", "desconto antecipacao"],
    "valor":              ["valor"],
    "nsu":                ["nsu", "doc", "documento"],
    "codigo_autorizacao": ["autorizacao", "cod autorizacao", "authorization"],
    "bandeira":           ["bandeira", "produto", "brand"],
    "modalidade":         ["modalidade", "tipo de venda", "forma de pagamento", "tipo"],
    "parcelas":           ["parcelas", "qtd parcelas", "total de parcelas"],
    "numero_parcela":     ["parcela", "n parcela", "numero da parcela"],
    "total_parcelas":     ["total de parcelas", "qtd parcelas"],
    "status":             ["status", "situacao"],
    "descricao":          ["historico", "descricao", "lancamento", "memo"],
    "id_externo":         ["fitid", "identificador", "id"],
}


def _limpar(texto) -> str:
    texto = str(texto or "").lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return " ".join(texto.split())


def sugerir(cabecalhos, tipo) -> dict:
    """Devolve {nome_da_coluna: campo_do_sistema} com o melhor palpite."""
    definicao = CAMPOS.get(tipo)
    if definicao is None:
        return {}

    chaves_validas = [c[0] for c in definicao["campos"]]
    de_para = {}
    ja_usados = set()

    for cabecalho in cabecalhos:
        alvo = _limpar(cabecalho)
        if not alvo:
            continue

        melhor, melhor_nota = None, 0
        for chave in chaves_validas:
            if chave in ja_usados:
                continue
            for pista in PISTAS.get(chave, []):
                # Nota maior pra igualdade exata, menor pra "contem".
                if alvo == pista:
                    nota = 100
                elif pista in alvo:
                    nota = len(pista)
                else:
                    nota = 0
                if nota > melhor_nota:
                    melhor_nota, melhor = nota, chave

        if melhor:
            de_para[cabecalho] = melhor
            ja_usados.add(melhor)

    return de_para


def converter(valor, tipo):
    if tipo == "numero":
        return para_numero(valor)
    if tipo == "data":
        return para_data(valor)
    if tipo == "inteiro":
        n = para_numero(valor)
        return None if n is None else int(n)
    texto = None if valor is None else str(valor).strip()
    return texto or None


def aplicar(linhas, de_para, tipo) -> tuple[list[dict], int]:
    """Transforma as linhas cruas em registros que o motor entende.

    Devolve (registros_validos, quantidade_ignorada).
    """
    definicao = CAMPOS[tipo]
    por_chave = {c[0]: c for c in definicao["campos"]}
    obrigatorios = [c[0] for c in definicao["campos"] if c[3]]

    registros = []
    ignoradas = 0

    for i, linha in enumerate(linhas):
        registro = {"id": f"{tipo}-{i + 1}"}
        for cabecalho, chave in de_para.items():
            campo = por_chave.get(chave)
            if campo is None:
                continue
            registro[chave] = converter(linha.get(cabecalho), campo[2])

        if any(registro.get(c) is None for c in obrigatorios):
            ignoradas += 1
            continue

        # O motor precisa do bruto, mesmo quando a planilha so traz o liquido.
        if tipo == "recebiveis" and registro.get("valor_bruto") is None:
            registro["valor_bruto"] = registro["valor_liquido"]

        registros.append(registro)

    return registros, ignoradas


def faltando(de_para, tipo) -> list[str]:
    """Quais campos obrigatorios ainda nao foram encontrados."""
    definicao = CAMPOS[tipo]
    usados = set(de_para.values())
    return [c[1] for c in definicao["campos"] if c[3] and c[0] not in usados]
