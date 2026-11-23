"""Le os dois arquivos, roda o motor e monta o resultado pronto pra mostrar.

E o mesmo caminho pro comando (conciliar.py) e pra tela no navegador
(abrir_concilia.py), pra os dois darem sempre o mesmo resultado.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

from . import mapear, planilha
from .formato import arredondar, data_br, ZERO
from .motor import conciliar

NOMES_TIPO = {
    "taxa_maior":        "Taxa cobrada a maior",
    "taxa_menor":        "Taxa cobrada a menor",
    "nao_recebido":      "Previsto e não recebido",
    "valor_divergente":  "Valor diferente do previsto",
    "recebido_atrasado": "Recebido com atraso",
    "chargeback":        "Chargeback",
    "nao_identificado":  "Entrada sem origem identificada",
}

NOMES_GRAVIDADE = {"alta": "Alta", "media": "Média", "baixa": "Baixa"}

NOMES_COMO = {
    "lote do dia": "Total do dia num depósito",
    "lote do dia por modalidade": "Débito e crédito separados",
    "lote do dia por modalidade detalhada": "Separado por modalidade",
    "lote do dia por bandeira": "Separado por bandeira",
    "lote do dia por modalidade e bandeira": "Separado por modalidade e bandeira",
    "lote do dia por modalidade detalhada e bandeira": "Separado por modalidade e bandeira",
    "parcela": "Venda por venda",
}

ROTULOS = {
    "recebiveis": "Agenda de recebíveis",
    "extrato": "Extrato bancário",
}


# Os nomes dos campos no mapear.py ficam sem acento (o terminal do Windows
# as vezes quebra acento). Na tela e no Excel eles aparecem assim:
COM_ACENTO = {
    "Valor liquido": "Valor líquido",
    "Custo de antecipacao": "Custo de antecipação",
    "Parcela numero": "Número da parcela",
    "Situacao": "Situação",
    "Historico": "Histórico",
}


def acentuar(campo):
    return COM_ACENTO.get(campo, campo)


class ArquivoComProblema(Exception):
    """O arquivo nao pode ser usado. Leva a explicacao e, se for o caso,
    as colunas que o arquivo tem, pra pessoa saber o que renomear."""

    def __init__(self, mensagem, tipo, nome, faltando=None, colunas=None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.tipo = tipo
        self.nome = nome
        self.faltando = faltando or []
        self.colunas = colunas or []


def ler(caminho, tipo, nome=None):
    """Le uma planilha e devolve (registros, info).

    info traz o que o sistema entendeu: de qual coluna veio cada campo,
    quantas linhas leu e quantas ignorou.
    """
    nome = nome or Path(caminho).name
    try:
        linhas = planilha.ler(caminho)
    except FileNotFoundError:
        raise ArquivoComProblema(f"Não achei o arquivo {nome}.", tipo, nome)
    except ValueError as e:
        raise ArquivoComProblema(str(e), tipo, nome)
    except Exception:
        raise ArquivoComProblema(
            f"Não consegui abrir {nome}. Confira se é mesmo uma planilha Excel (.xlsx) ou CSV.",
            tipo, nome)

    if not linhas:
        raise ArquivoComProblema(f"O arquivo {nome} está vazio ou não tem cabeçalho.", tipo, nome)

    cabecalhos = list(linhas[0].keys())
    de_para = mapear.sugerir(cabecalhos, tipo)
    pendentes = mapear.faltando(de_para, tipo)
    if pendentes:
        raise ArquivoComProblema(
            f"Li {len(linhas)} {'linha' if len(linhas) == 1 else 'linhas'} de {nome}, mas não achei: "
            f"{', '.join(acentuar(c) for c in pendentes)}.",
            tipo, nome, faltando=pendentes, colunas=cabecalhos)

    por_chave = {c[0]: c[1] for c in mapear.CAMPOS[tipo]["campos"]}
    colunas = [(por_chave[chave], cabecalho)
               for cabecalho, chave in sorted(de_para.items(), key=lambda x: x[1])]

    registros, ignoradas = mapear.aplicar(linhas, de_para, tipo)
    return registros, {"nome": nome, "linhas": len(registros), "ignoradas": ignoradas,
                       "colunas": colunas,
                       "colunas_tela": [(acentuar(c), col) for c, col in colunas]}


def _dinheiro(valor):
    """Decimal vira texto com 2 casas (nao vira float, pra nao perder centavo)."""
    if valor is None:
        return None
    return str(arredondar(valor))


def montar(resultado, recebiveis, movimentos):
    """Transforma o resultado do motor em linhas prontas pra tela e pro Excel."""
    rec_por_id = {r["id"]: r for r in recebiveis}
    mov_por_id = {m["id"]: m for m in movimentos}

    def data_da(d):
        if d["referencia_tipo"] == "recebivel" and d["referencia_id"] in rec_por_id:
            return data_br(rec_por_id[d["referencia_id"]]["data_prevista"])
        if d["referencia_tipo"] == "movimento" and d["referencia_id"] in mov_por_id:
            return data_br(mov_por_id[d["referencia_id"]]["data"])
        return "-"

    ordem = {"alta": 0, "media": 1, "baixa": 2}
    divergencias = []
    for d in sorted(resultado["divergencias"],
                    key=lambda d: (ordem.get(d["gravidade"], 9), -abs(d.get("diferenca") or 0))):
        divergencias.append({
            "tipo": d["tipo"],
            "nome": NOMES_TIPO.get(d["tipo"], d["tipo"]),
            "gravidade": d["gravidade"],
            "gravidade_nome": NOMES_GRAVIDADE.get(d["gravidade"], d["gravidade"]),
            "data": data_da(d),
            "competencia": f"{d['competencia']:%m/%Y}",
            "esperado": _dinheiro(d["valor_esperado"]),
            "encontrado": _dinheiro(d["valor_encontrado"]),
            "diferenca": _dinheiro(d["diferenca"]),
            "observacao": d["observacao"],
        })

    conciliados = []
    valor_conciliado = ZERO
    for c in resultado["conciliacoes"]:
        r = rec_por_id.get(c["recebivel_id"], {})
        m = mov_por_id.get(c["movimento_banco_id"], {})
        if r.get("valor_liquido") is not None:
            valor_conciliado += Decimal(str(r["valor_liquido"]))
        conciliados.append({
            "data_prevista": data_br(r.get("data_prevista")),
            "modalidade": r.get("modalidade") or "",
            "bandeira": r.get("bandeira") or "",
            "valor_liquido": _dinheiro(r.get("valor_liquido")),
            "data_banco": data_br(m.get("data")),
            "valor_deposito": _dinheiro(m.get("valor")),
            "historico": m.get("descricao") or "",
            "como": NOMES_COMO.get(c.get("como", ""), c.get("como", "")),
        })

    por_tipo = [
        {"tipo": tipo, "nome": NOMES_TIPO.get(tipo, tipo),
         "quantidade": info["quantidade"], "valor": _dinheiro(info["valor"])}
        for tipo, info in sorted(resultado["resumo"]["por_tipo"].items(),
                                 key=lambda x: x[1]["valor"], reverse=True)
    ]
    em_jogo = sum((Decimal(t["valor"]) for t in por_tipo), ZERO)

    resumo = resultado["resumo"]
    return {
        "resumo": {
            "recebiveis": resumo["recebiveis_analisados"],
            "movimentos": resumo["movimentos_analisados"],
            "conciliados": resumo["conciliados"],
            "atencao": resumo["divergencias"],
            "valor_conciliado": _dinheiro(valor_conciliado),
            "valor_em_jogo": _dinheiro(em_jogo),
            "por_tipo": por_tipo,
        },
        "divergencias": divergencias,
        "conciliados": conciliados,
    }


def executar(caminho_agenda, caminho_extrato, nome_agenda=None, nome_extrato=None, hoje=None):
    """Le os dois arquivos, concilia e devolve tudo pronto.

    Devolve um dicionario com "dados" (pronto pra tela e pro Excel) e
    "resultado" (o que o motor devolveu, pro comando mostrar na tela).
    Levanta ArquivoComProblema se um dos arquivos nao servir.
    """
    recebiveis, info_agenda = ler(caminho_agenda, "recebiveis", nome_agenda)
    movimentos, info_extrato = ler(caminho_extrato, "extrato", nome_extrato)

    resultado = conciliar(recebiveis=recebiveis, movimentos=movimentos, hoje=hoje)
    dados = montar(resultado, recebiveis, movimentos)
    dados["arquivos"] = {"agenda": info_agenda, "extrato": info_extrato}
    dados["gerado_em"] = data_br(hoje or date.today())
    return {"dados": dados, "resultado": resultado,
            "recebiveis": recebiveis, "movimentos": movimentos}
