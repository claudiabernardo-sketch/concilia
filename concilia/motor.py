"""Motor de conciliacao.

Regras fixas, sem IA, sem chute. O mesmo conjunto de dados gera sempre o
mesmo resultado.

A regra de ouro: so concilia quando bate com certeza. O que nao bate vira
divergencia pra olho humano, nunca e forcado.
"""

import re
import unicodedata
from datetime import date
from decimal import Decimal

from .formato import arredondar, competencia_de, data_br, ZERO

PARAMETROS_PADRAO = {
    # R$ de diferenca aceita, pro arredondamento da adquirente
    "tolerancia_valor": Decimal("0.02"),
    # dias de atraso aceitos sem virar divergencia
    "tolerancia_dias": 2,
    # pontos percentuais de folga na conferencia de taxa
    "tolerancia_taxa_pp": Decimal("0.05"),
    # ate 5% de diferenca ainda e "o mesmo deposito, valor errado"
    "faixa_valor_divergente": Decimal("0.05"),
}


def _perto(a, b, tolerancia) -> bool:
    return abs(arredondar(a) - arredondar(b)) <= arredondar(tolerancia)


def _dias_entre(inicio: date, fim: date):
    if inicio is None or fim is None:
        return None
    return (fim - inicio).days


# ---------------------------------------------------------------------
# Qual taxa foi combinada pra essa venda?
# ---------------------------------------------------------------------
def taxa_contratada_para(venda, taxas):
    """Procura a regra de taxa mais especifica que valia na data da venda."""
    candidatas = []

    for taxa in taxas:
        if taxa.get("estabelecimento_id") != venda.get("estabelecimento_id"):
            continue
        if taxa.get("modalidade") != venda.get("modalidade"):
            continue

        parcelas = venda.get("parcelas") or 1
        if parcelas < (taxa.get("parcelas_de") or 1):
            continue
        if parcelas > (taxa.get("parcelas_ate") or 1):
            continue

        inicio = taxa.get("vigencia_inicio")
        fim = taxa.get("vigencia_fim")
        if inicio and venda["data_venda"] < inicio:
            continue
        if fim and venda["data_venda"] > fim:
            continue

        # bandeira vazia na regra = vale pra qualquer bandeira
        if taxa.get("bandeira") and taxa["bandeira"] != venda.get("bandeira"):
            continue

        candidatas.append(taxa)

    if not candidatas:
        return None

    # Regra com bandeira definida ganha da regra generica. Entre duas, a
    # que comecou a valer mais recentemente.
    candidatas.sort(
        key=lambda t: (1 if t.get("bandeira") else 0, t.get("vigencia_inicio") or date.min),
        reverse=True,
    )
    return candidatas[0]


# ---------------------------------------------------------------------
# A adquirente cobrou o que foi combinado?
# ---------------------------------------------------------------------
def conferir_taxas(vendas, taxas, parametros=None):
    p = {**PARAMETROS_PADRAO, **(parametros or {})}
    divergencias = []

    for venda in vendas:
        if venda.get("valor_taxa") is None:
            continue
        bruto = venda.get("valor_bruto")
        if not bruto:
            continue

        regra = taxa_contratada_para(venda, taxas)
        if regra is None:
            # Sem combinado cadastrado nao da pra acusar nada.
            continue

        esperado = arredondar(bruto * regra["taxa_percentual"] / 100)
        cobrado = arredondar(venda["valor_taxa"])
        folga = arredondar(bruto * p["tolerancia_taxa_pp"] / 100)

        if _perto(cobrado, esperado, folga):
            continue

        diferenca = arredondar(cobrado - esperado)
        percentual_real = arredondar(cobrado / bruto * 100)

        divergencias.append({
            "tipo": "taxa_maior" if diferenca > 0 else "taxa_menor",
            "referencia_tipo": "venda",
            "referencia_id": venda.get("id"),
            "competencia": competencia_de(venda["data_venda"]),
            "valor_esperado": esperado,
            "valor_encontrado": cobrado,
            "diferenca": diferenca,
            "gravidade": "alta" if diferenca > 0 else "baixa",
            "observacao": (
                f"Combinado {regra['taxa_percentual']}% sobre {bruto}. "
                f"Cobrado o equivalente a {percentual_real}%."
            ),
        })

    return divergencias


# ---------------------------------------------------------------------
# De onde veio esse dinheiro?
#
# Entrada que o banco descreve como PIX, TED, DOC, transferencia, deposito
# ou boleto, sem o nome de nenhuma adquirente, e dinheiro de cliente, nao
# da maquininha. Ela nunca e casada automaticamente com recebivel, mesmo
# com o valor igual, porque coincidencia de valor acontece.
# ---------------------------------------------------------------------
ADQUIRENTES = re.compile(
    r"\b(cielo|rede|redecard|stone|getnet|pagseguro|pagbank|safrapay|sipag|"
    r"sicredi|sicoob|vero|banrisul|mercado ?pago|sumup|ton|infinitepay|"
    r"granito|bin|adiq|elavon|global payments|c6 ?pay|pagar\.?me|cappta|"
    r"bananinha|caixa pagamentos|ticket|alelo|sodexo|pluxee|vr|valecard)\b"
)
FORA_DA_MAQUININHA = re.compile(
    r"\b(pix|ted|doc|transf\w*|deposito|boleto|cobranca)\b"
)


def _normalizar(texto) -> str:
    """Minusculo, sem acento, sem espaco sobrando. None vira ''."""
    texto = str(texto or "").lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return " ".join(texto.split())


def parece_fora_da_maquininha(descricao) -> bool:
    texto = _normalizar(descricao)
    if not texto:
        return False  # sem historico, nao da pra saber, entao nao exclui
    if ADQUIRENTES.search(texto):
        return False
    return bool(FORA_DA_MAQUININHA.search(texto))


def _situacao(recebivel) -> str:
    texto = _normalizar(recebivel.get("status"))
    if "chargeback" in texto or "contestacao" in texto:
        return "chargeback"
    if "cancel" in texto:
        return "cancelado"
    return texto


def _familia(modalidade):
    """Debito e credito costumam cair em depositos separados."""
    texto = _normalizar(modalidade)
    if not texto:
        return None
    if "debit" in texto:
        return "debito"
    if "credit" in texto:
        return "credito"
    return texto


# Quando o lote do dia inteiro nao bate, o motor tenta separar o dia
# nessas fatias, nessa ordem, antes de cair para parcela por parcela.
# Cada fatia so concilia se a soma dela bater com UM deposito.
FATIAS = [
    ("lote do dia por modalidade",
     lambda r: _familia(r.get("modalidade"))),
    ("lote do dia por modalidade detalhada",
     lambda r: _normalizar(r.get("modalidade")) or None),
    ("lote do dia por bandeira",
     lambda r: _normalizar(r.get("bandeira")) or None),
    ("lote do dia por modalidade e bandeira",
     lambda r: (_familia(r.get("modalidade")), _normalizar(r.get("bandeira")) or None)),
    ("lote do dia por modalidade detalhada e bandeira",
     lambda r: (_normalizar(r.get("modalidade")) or None,
                _normalizar(r.get("bandeira")) or None)),
]


def _fatiar(grupo, chave):
    fatias = {}
    for r in grupo:
        fatias.setdefault(chave(r), []).append(r)
    return [fatias[k] for k in sorted(fatias, key=str)]


# ---------------------------------------------------------------------
# O que a adquirente prometeu pagar caiu no banco?
#
# A adquirente quase nunca deposita uma venda por vez. Ela junta o que
# vence no dia, e muitas vezes separa debito de credito (as vezes tambem
# por bandeira). Por isso o motor tenta, nessa ordem:
#   1. o LOTE do dia inteiro num deposito so
#   2. o dia fatiado por modalidade e por bandeira, uma fatia por deposito
#   3. parcela por parcela
#   4. um deposito na data certa com valor parecido, que vira alerta
# ---------------------------------------------------------------------
def conciliar_recebiveis(recebiveis, movimentos, hoje=None, parametros=None):
    p = {**PARAMETROS_PADRAO, **(parametros or {})}
    hoje = hoje or date.today()

    conciliacoes = []
    divergencias = []

    # Chargeback e cancelamento nao entram na conciliacao.
    para_conciliar = []
    for r in recebiveis:
        situacao = _situacao(r)
        if situacao == "chargeback":
            divergencias.append({
                "tipo": "chargeback",
                "referencia_tipo": "recebivel",
                "referencia_id": r.get("id"),
                "competencia": competencia_de(r["data_prevista"]),
                "valor_esperado": arredondar(r["valor_liquido"]),
                "valor_encontrado": ZERO,
                "diferenca": arredondar(-r["valor_liquido"]),
                "gravidade": "alta",
                "observacao": "Chargeback. Confira se o valor foi debitado em outro lançamento.",
            })
            continue
        if situacao == "cancelado":
            continue
        para_conciliar.append(r)

    # So entradas de dinheiro interessam aqui.
    disponiveis = [
        {**m, "usado": False, "fora_da_maquininha": parece_fora_da_maquininha(m.get("descricao"))}
        for m in sorted(movimentos, key=lambda m: m["data"])
        if para_numero_seguro(m.get("valor")) > 0
    ]

    def achar_movimento(valor_alvo, data_alvo, tolerancia):
        melhor = None
        melhor_distancia = None

        for m in disponiveis:
            if m["usado"] or m["fora_da_maquininha"]:
                continue
            if not _perto(m["valor"], valor_alvo, tolerancia):
                continue

            dias = _dias_entre(data_alvo, m["data"])
            if dias is None or abs(dias) > p["tolerancia_dias"]:
                continue

            # Entre dois candidatos, fica o mais perto da data prevista.
            if melhor_distancia is None or abs(dias) < melhor_distancia:
                melhor_distancia = abs(dias)
                melhor = m

        return melhor

    def registrar(lote, movimento, como, data_prevista):
        movimento["usado"] = True
        dias = _dias_entre(data_prevista, movimento["data"])
        for r in lote:
            conciliacoes.append({
                "recebivel_id": r.get("id"),
                "movimento_banco_id": movimento.get("id"),
                "origem": "automatica",
                "como": como,
                "diferenca_valor": ZERO,
                "diferenca_dias": dias,
            })

    def soma_de(lote):
        # Soma o valor exato e so arredonda no fim. A Stone, por exemplo,
        # manda o liquido com 6 casas; arredondar venda por venda antes de
        # somar acumula centavos (R$ 0,15 num dia de 248 vendas).
        return arredondar(sum(para_numero_seguro(r["valor_liquido"]) for r in lote))

    def apontar_valor_divergente(lote, data_prevista):
        soma = soma_de(lote)
        aproximado = achar_movimento(
            soma, data_prevista, arredondar(soma * p["faixa_valor_divergente"])
        )
        if aproximado is None:
            return False
        aproximado["usado"] = True
        divergencias.append({
            "tipo": "valor_divergente",
            "referencia_tipo": "movimento",
            "referencia_id": aproximado.get("id"),
            "competencia": competencia_de(data_prevista),
            "valor_esperado": soma,
            "valor_encontrado": arredondar(aproximado["valor"]),
            "diferenca": arredondar(arredondar(aproximado["valor"]) - soma),
            "gravidade": "alta",
            "observacao": (
                f"Depósito de {data_br(data_prevista)} veio diferente do previsto. "
                f"Envolve {len(lote)} {'venda' if len(lote) == 1 else 'vendas'}."
            ),
        })
        return True

    # Agrupa por maquininha + data prevista, que e como a adquirente paga.
    grupos = {}
    for r in para_conciliar:
        chave = (r.get("estabelecimento_id"), r["data_prevista"])
        grupos.setdefault(chave, []).append(r)

    sobraram = []

    for (_, data_prevista), grupo in grupos.items():
        # 1a tentativa: o lote inteiro caiu num credito so.
        movimento = achar_movimento(soma_de(grupo), data_prevista, p["tolerancia_valor"])
        if movimento is not None:
            registrar(grupo, movimento, "lote do dia", data_prevista)
            continue

        # 2a tentativa: o dia veio fatiado (debito separado de credito,
        # ou uma bandeira por deposito). Cada fatia procura o seu deposito.
        restantes = list(grupo)
        ja_tentado = {frozenset(id(r) for r in grupo)}
        for como, chave in FATIAS:
            if len(restantes) < 2:
                break
            for fatia in _fatiar(restantes, chave):
                marca = frozenset(id(r) for r in fatia)
                if marca in ja_tentado:
                    continue
                ja_tentado.add(marca)
                m = achar_movimento(soma_de(fatia), data_prevista, p["tolerancia_valor"])
                if m is not None:
                    registrar(fatia, m, como, data_prevista)
                    restantes = [r for r in restantes if id(r) not in marca]

        # 3a tentativa: parcela por parcela.
        nao_casados = []
        for r in restantes:
            m = achar_movimento(r["valor_liquido"], r["data_prevista"], p["tolerancia_valor"])
            if m is not None:
                registrar([r], m, "parcela", r["data_prevista"])
            else:
                nao_casados.append(r)

        if not nao_casados:
            continue

        # 4a tentativa: existe um deposito com a data certa mas valor errado?
        # Nao concilia, mas aponta o lugar exato pra pessoa olhar. Tenta o
        # que faltou inteiro e, se nao achar, debito e credito separados.
        if apontar_valor_divergente(nao_casados, data_prevista):
            continue
        por_modalidade = _fatiar(nao_casados, FATIAS[0][1])
        if len(por_modalidade) > 1:
            for lote in por_modalidade:
                if not apontar_valor_divergente(lote, data_prevista):
                    sobraram.extend(lote)
            continue
        sobraram.extend(nao_casados)

    # Recebivel que ja venceu e nao apareceu no banco.
    for r in sobraram:
        atraso = _dias_entre(r["data_prevista"], hoje)
        if atraso is None or atraso <= p["tolerancia_dias"]:
            continue  # ainda vai cair

        divergencias.append({
            "tipo": "nao_recebido",
            "referencia_tipo": "recebivel",
            "referencia_id": r.get("id"),
            "competencia": competencia_de(r["data_prevista"]),
            "valor_esperado": arredondar(r["valor_liquido"]),
            "valor_encontrado": ZERO,
            "diferenca": arredondar(-r["valor_liquido"]),
            "gravidade": "alta",
            "observacao": f"Previsto para {data_br(r['data_prevista'])}, {atraso} dias em atraso.",
        })

    # Dinheiro que entrou e ninguem sabe de onde veio.
    for m in disponiveis:
        if m["usado"]:
            continue
        descricao = m.get("descricao")
        if m["fora_da_maquininha"]:
            observacao = (f"Parece dinheiro de cliente (PIX, TED, transferência), não da "
                          f"maquininha: {descricao}. O sistema nunca casa esse tipo de "
                          "entrada com a agenda. Confira na mão.")
        elif descricao:
            observacao = f"Entrada sem recebível correspondente: {descricao}"
        else:
            observacao = "Entrada sem recebível correspondente."
        divergencias.append({
            "tipo": "nao_identificado",
            "referencia_tipo": "movimento",
            "referencia_id": m.get("id"),
            "competencia": competencia_de(m["data"]),
            "valor_esperado": None,
            "valor_encontrado": arredondar(m["valor"]),
            "diferenca": arredondar(m["valor"]),
            "gravidade": "media",
            "observacao": observacao,
        })

    return conciliacoes, divergencias


def para_numero_seguro(valor):
    """Converte pra Decimal pra comparar, sem explodir se vier vazio."""
    if valor is None:
        return ZERO
    if isinstance(valor, Decimal):
        return valor
    return Decimal(str(valor))


# ---------------------------------------------------------------------
# Roda tudo e devolve o resultado pronto
# ---------------------------------------------------------------------
def conciliar(recebiveis=None, movimentos=None, vendas=None, taxas=None,
              hoje=None, parametros=None):
    recebiveis = recebiveis or []
    movimentos = movimentos or []
    vendas = vendas or []
    taxas = taxas or []

    conciliacoes, divergencias = conciliar_recebiveis(
        recebiveis, movimentos, hoje=hoje, parametros=parametros
    )
    divergencias = divergencias + conferir_taxas(vendas, taxas, parametros)

    # Soma o dinheiro que esta em jogo, por tipo de problema.
    por_tipo = {}
    for d in divergencias:
        info = por_tipo.setdefault(d["tipo"], {"quantidade": 0, "valor": ZERO})
        info["quantidade"] += 1
        info["valor"] = arredondar(info["valor"] + abs(d.get("diferenca") or ZERO))

    return {
        "conciliacoes": conciliacoes,
        "divergencias": divergencias,
        "resumo": {
            "recebiveis_analisados": len(recebiveis),
            "movimentos_analisados": len(movimentos),
            "conciliados": len(conciliacoes),
            "divergencias": len(divergencias),
            "por_tipo": por_tipo,
        },
    }
