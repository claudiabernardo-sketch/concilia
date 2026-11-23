"""Testes da tela no navegador e do relatorio em Excel.

Sobem o Concilia de verdade (so neste computador), mandam os arquivos de
exemplo como o navegador manda, e conferem a resposta e o Excel.
"""

import base64
import http.client
import io
import json
import threading
from datetime import date
from pathlib import Path

from openpyxl import load_workbook

from concilia import relatorio
from concilia.servico import executar
from concilia.servidor import criar_servidor
from testes.teste_motor import igual, teste

EXEMPLOS = Path(__file__).resolve().parent.parent / "exemplos"
AGENDA = EXEMPLOS / "agenda-exemplo.xlsx"
EXTRATO = EXEMPLOS / "extrato-exemplo.xlsx"
HOJE = date(2026, 11, 23)

G12 = "RELATORIO EM EXCEL"
G13 = "TELA NO NAVEGADOR"


@teste(G12, "o exemplo da 6 conciliados e 4 que precisam de atencao")
def _():
    d = executar(AGENDA, EXTRATO, hoje=HOJE)["dados"]
    igual(d["resumo"]["conciliados"], 6, "conciliados")
    igual(d["resumo"]["atencao"], 4, "precisam de atencao")
    igual(d["resumo"]["valor_em_jogo"], "1766.60", "dinheiro em jogo")
    igual(d["resumo"]["valor_conciliado"], "3831.00", "valor conciliado")


@teste(G12, "o Excel tem Resumo, Divergencias e Conciliados, nessa ordem")
def _():
    d = executar(AGENDA, EXTRATO, hoje=HOJE)["dados"]
    memoria = io.BytesIO()
    relatorio.gravar(d, memoria)
    pasta = load_workbook(io.BytesIO(memoria.getvalue()))
    igual(pasta.sheetnames, ["Resumo", "Divergências", "Conciliados"], "abas")
    igual(pasta["Divergências"].max_row, 5, "linhas de divergencia (com cabecalho)")
    igual(pasta["Conciliados"].max_row, 7, "linhas conciliadas (com cabecalho)")
    igual(pasta["Divergências"]["A2"].value, "Previsto e não recebido", "primeiro problema")


@teste(G12, "tudo batendo, o Excel diz que nao ha divergencia")
def _():
    d = executar(AGENDA, EXTRATO, hoje=HOJE)["dados"]
    d = {**d, "divergencias": [], "resumo": {**d["resumo"], "atencao": 0, "por_tipo": [],
                                              "valor_em_jogo": "0.00"}}
    memoria = io.BytesIO()
    relatorio.gravar(d, memoria)
    pasta = load_workbook(io.BytesIO(memoria.getvalue()))
    igual(pasta["Divergências"]["A2"].value, "Nenhuma divergência. Tudo bateu.", "mensagem")


# ---------------------------------------------------------------------
def _subir():
    servidor, chave = criar_servidor(0, hoje=HOJE)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor, chave


def _pedir(servidor, metodo, caminho, corpo=None, chave=None, host="127.0.0.1"):
    conexao = http.client.HTTPConnection("127.0.0.1", servidor.server_port, timeout=20)
    cab = {"Host": host}
    dados = None
    if corpo is not None:
        dados = json.dumps(corpo).encode()
        cab["Content-Type"] = "application/json"
    if chave:
        cab["X-Concilia-Chave"] = chave
    conexao.request(metodo, caminho, body=dados, headers=cab)
    resposta = conexao.getresponse()
    conteudo = resposta.read()
    conexao.close()
    return resposta.status, conteudo, resposta


def _arquivo(caminho, nome=None):
    return {"nome": nome or caminho.name, "conteudo": base64.b64encode(caminho.read_bytes()).decode()}


@teste(G13, "a pagina abre e traz a chave de seguranca")
def _():
    servidor, chave = _subir()
    try:
        status, corpo, _ = _pedir(servidor, "GET", "/")
        igual(status, 200, "status")
        igual(chave in corpo.decode("utf-8"), True, "chave na pagina")
        igual("__CHAVE__" in corpo.decode("utf-8"), False, "marcador trocado")
    finally:
        servidor.shutdown()
        servidor.server_close()


@teste(G13, "sem a chave, ou vindo de outro endereco, o Concilia recusa")
def _():
    servidor, chave = _subir()
    try:
        status, _, _ = _pedir(servidor, "POST", "/exemplo", {})
        igual(status, 403, "sem chave")
        status, _, _ = _pedir(servidor, "POST", "/exemplo", {}, chave="errada")
        igual(status, 403, "chave errada")
        status, _, _ = _pedir(servidor, "GET", "/", host="site-malicioso.com")
        igual(status, 403, "outro endereco")
    finally:
        servidor.shutdown()
        servidor.server_close()


@teste(G13, "manda a agenda e o extrato como o navegador manda, e baixa o Excel")
def _():
    servidor, chave = _subir()
    try:
        status, corpo, _ = _pedir(servidor, "POST", "/conciliar",
                                  {"agenda": _arquivo(AGENDA, "agenda-padaria.xlsx"),
                                   "extrato": _arquivo(EXTRATO, "extrato-padaria.xlsx")}, chave=chave)
        igual(status, 200, "status")
        d = json.loads(corpo)
        igual(d["ok"], True, "ok")
        igual(d["resumo"]["conciliados"], 6, "conciliados")
        igual(len(d["divergencias"]), 4, "divergencias")
        igual(d["relatorio"]["nome"].startswith("relatorio-padaria-"), True, "nome do relatorio")

        status, xlsx, resp = _pedir(servidor, "GET", d["relatorio"]["url"])
        igual(status, 200, "baixar relatorio")
        igual(xlsx[:2], b"PK", "e um Excel de verdade")
        igual("attachment" in (resp.getheader("Content-Disposition") or ""), True, "vem como download")

        status, _, _ = _pedir(servidor, "GET", d["relatorio"]["url"].replace(chave, "errada"))
        igual(status, 403, "relatorio sem a chave certa")
    finally:
        servidor.shutdown()
        servidor.server_close()


@teste(G13, "o botao de exemplo funciona sem arquivo nenhum")
def _():
    servidor, chave = _subir()
    try:
        status, corpo, _ = _pedir(servidor, "POST", "/exemplo", {}, chave=chave)
        d = json.loads(corpo)
        igual(d["ok"], True, "ok")
        igual(d["resumo"]["atencao"], 4, "precisam de atencao")
    finally:
        servidor.shutdown()
        servidor.server_close()


@teste(G13, "coluna faltando: a tela mostra as colunas que o arquivo tem")
def _():
    servidor, chave = _subir()
    try:
        csv = "Dia;Quanto\n01/10/2026;10,00\n".encode("utf-8")
        status, corpo, _ = _pedir(servidor, "POST", "/conciliar", {
            "agenda": {"nome": "agenda.csv", "conteudo": base64.b64encode(csv).decode()},
            "extrato": _arquivo(EXTRATO)}, chave=chave)
        d = json.loads(corpo)
        igual(d["ok"], False, "ok")
        igual(d["arquivo"], "recebiveis", "qual arquivo")
        igual(d["colunas"], ["Dia", "Quanto"], "colunas do arquivo")
        igual(d["faltando"], ["Data prevista", "Valor líquido"], "o que faltou")
    finally:
        servidor.shutdown()
        servidor.server_close()


@teste(G13, "PDF ou .xls antigo: explica em vez de travar")
def _():
    servidor, chave = _subir()
    try:
        status, corpo, _ = _pedir(servidor, "POST", "/conciliar", {
            "agenda": {"nome": "agenda.pdf", "conteudo": base64.b64encode(b"%PDF").decode()},
            "extrato": _arquivo(EXTRATO)}, chave=chave)
        d = json.loads(corpo)
        igual(d["ok"], False, "ok")
        igual("PDF" in d["erro"], True, "explica o PDF")
    finally:
        servidor.shutdown()
        servidor.server_close()
