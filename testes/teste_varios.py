"""Varias agendas e varios extratos de uma vez.

Caso real de aluna: o cliente recebe quase tudo na Stone, mas o vale-
alimentacao (Alelo, VR, Ticket) tem agenda propria e cai em outras contas
(BB, Itau, PJ Bank). Valores e nomes aqui sao ficticios.
"""

import base64
import io
import json
import tempfile
from pathlib import Path

from openpyxl import load_workbook

from concilia import relatorio
from concilia.servico import executar_varios
from testes.teste_motor import igual, teste
from testes.teste_tela import HOJE, _pedir, _subir

G14 = "VARIAS AGENDAS E VARIOS EXTRATOS (UMA CONTA POR ARQUIVO)"


def _csv(pasta, nome, linhas):
    caminho = Path(pasta) / nome
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return (caminho, nome)


def _cenario(pasta):
    agendas = [
        _csv(pasta, "agenda-stone.csv", ["Data prevista;Valor liquido",
                                         "01/10/2026;100,00", "01/10/2026;400,00"]),
        _csv(pasta, "agenda-alelo.csv", ["Data prevista;Valor liquido",
                                         "01/10/2026;250,00"]),
    ]
    extratos = [
        _csv(pasta, "extrato-itau.csv", ["Data;Historico;Valor",
                                         "01/10/2026;CRED STONE;500,00"]),
        _csv(pasta, "extrato-bb.csv", ["Data;Historico;Valor",
                                       "02/10/2026;CRED ALELO;250,00"]),
    ]
    return agendas, extratos


@teste(G14, "Stone e vale-alimentacao em agendas separadas, caindo em contas diferentes")
def _():
    with tempfile.TemporaryDirectory() as pasta:
        agendas, extratos = _cenario(pasta)
        d = executar_varios(agendas, extratos, hoje=HOJE)["dados"]
    igual(d["resumo"]["conciliados"], 3, "conciliados")
    igual(d["resumo"]["atencao"], 0, "precisam de atencao")
    contas = sorted({c["conta"] for c in d["conciliados"]})
    igual(contas, ["extrato-bb.csv", "extrato-itau.csv"], "contas onde caiu")
    agendas_usadas = sorted({c["agenda"] for c in d["conciliados"]})
    igual(agendas_usadas, ["agenda-alelo.csv", "agenda-stone.csv"], "agendas")


@teste(G14, "o lote do dia da Stone nao se mistura com o do vale-alimentacao")
def _():
    # Se as duas agendas fossem um lote so, o dia daria 750 e nada bateria
    # com o deposito de 500 da Stone.
    with tempfile.TemporaryDirectory() as pasta:
        agendas, extratos = _cenario(pasta)
        d = executar_varios(agendas, extratos, hoje=HOJE)["dados"]
    stone = [c for c in d["conciliados"] if c["agenda"] == "agenda-stone.csv"]
    igual(len(stone), 2, "vendas da Stone conciliadas")
    igual({c["como"] for c in stone}, {"Total do dia num depósito"}, "como casou")


@teste(G14, "a primeira linha de cada extrato nao se confunde com a do outro")
def _():
    with tempfile.TemporaryDirectory() as pasta:
        agendas = [_csv(pasta, "agenda.csv", ["Data prevista;Valor liquido",
                                              "01/10/2026;300,00", "01/10/2026;300,00"])]
        extratos = [
            _csv(pasta, "conta-a.csv", ["Data;Historico;Valor", "01/10/2026;CRED REDE;300,00"]),
            _csv(pasta, "conta-b.csv", ["Data;Historico;Valor", "01/10/2026;CRED REDE;300,00"]),
        ]
        d = executar_varios(agendas, extratos, hoje=HOJE)["dados"]
    igual(d["resumo"]["conciliados"], 2, "conciliados")
    igual(sorted(c["conta"] for c in d["conciliados"]), ["conta-a.csv", "conta-b.csv"],
          "cada deposito usado uma vez")


@teste(G14, "o Excel mostra a conta e a agenda de cada linha conciliada")
def _():
    with tempfile.TemporaryDirectory() as pasta:
        agendas, extratos = _cenario(pasta)
        d = executar_varios(agendas, extratos, hoje=HOJE)["dados"]
    memoria = io.BytesIO()
    relatorio.gravar(d, memoria)
    pasta = load_workbook(io.BytesIO(memoria.getvalue()))
    aba = pasta["Conciliados"]
    igual(aba["I1"].value, "Conta (extrato)", "coluna da conta")
    igual(aba["J1"].value, "Agenda", "coluna da agenda")
    igual("Extratos: extrato-itau.csv, extrato-bb.csv" in pasta["Resumo"]["B3"].value, True,
          "capa lista os extratos")


@teste(G14, "a tela recebe varios arquivos de cada lado")
def _():
    servidor, chave = _subir()
    try:
        with tempfile.TemporaryDirectory() as pasta:
            agendas, extratos = _cenario(pasta)

            def pacote(lista):
                return [{"nome": nome, "conteudo": base64.b64encode(Path(c).read_bytes()).decode()}
                        for c, nome in lista]

            status, corpo, _ = _pedir(servidor, "POST", "/conciliar",
                                      {"agendas": pacote(agendas), "extratos": pacote(extratos)},
                                      chave=chave)
        d = json.loads(corpo)
        igual(d["ok"], True, "ok")
        igual(len(d["arquivos"]["agendas"]), 2, "agendas lidas")
        igual(len(d["arquivos"]["extratos"]), 2, "extratos lidos")
        igual(d["resumo"]["conciliados"], 3, "conciliados")
    finally:
        servidor.shutdown()
        servidor.server_close()


@teste(G14, "um dos extratos sem coluna de valor: a tela diz qual arquivo")
def _():
    servidor, chave = _subir()
    try:
        with tempfile.TemporaryDirectory() as pasta:
            agendas, extratos = _cenario(pasta)
            ruim = _csv(pasta, "extrato-pjbank.csv", ["Dia;Descricao", "01/10/2026;PIX"])

            def pacote(lista):
                return [{"nome": nome, "conteudo": base64.b64encode(Path(c).read_bytes()).decode()}
                        for c, nome in lista]

            status, corpo, _ = _pedir(servidor, "POST", "/conciliar",
                                      {"agendas": pacote(agendas),
                                       "extratos": pacote(extratos + [ruim])}, chave=chave)
        d = json.loads(corpo)
        igual(d["ok"], False, "ok")
        igual(d["nome"], "extrato-pjbank.csv", "arquivo com problema")
        igual(d["arquivo"], "extrato", "lado")
    finally:
        servidor.shutdown()
        servidor.server_close()
