"""A tela do Concilia, que abre no navegador.

Roda so neste computador (endereco 127.0.0.1). Nada vai pra internet: o
navegador manda as planilhas pra este programa, que concilia aqui mesmo e
devolve o resultado. Usa so o que ja vem com o Python.

Protecoes:
- so atende quem chama por 127.0.0.1 ou localhost (outro site nao consegue
  se passar por ele);
- toda acao exige uma chave que muda a cada vez que o Concilia abre e que
  so a pagina dele conhece.
"""

import base64
import binascii
import io
import json
import secrets
import tempfile
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from . import relatorio
from .servico import ROTULOS, ArquivoComProblema, acentuar, executar

PASTA = Path(__file__).resolve().parent
PAGINA = PASTA / "tela" / "index.html"
EXEMPLOS = PASTA.parent / "exemplos"

LIMITE_BYTES = 40 * 1024 * 1024  # 40 MB, bem mais que uma agenda de mes inteiro
EXTENSOES = {".xlsx", ".xlsm", ".csv", ".txt"}


def _nome_seguro(nome, padrao):
    nome = Path(str(nome or padrao)).name
    return nome[:120] or padrao


def _apelido(nome):
    base = Path(nome).stem.lower()
    for tirar in ("agenda-", "agenda_", "agenda", "recebiveis-", "recebimentos_"):
        if base.startswith(tirar):
            base = base[len(tirar):]
    base = "".join(c if c.isalnum() or c in "-_" else "-" for c in base).strip("-_")
    return base[:40]


def criar_servidor(porta=0, hoje=None):
    """Cria o servidor (sem comecar a rodar). Devolve (servidor, chave)."""
    chave = secrets.token_urlsafe(18)
    relatorios = {}

    class Atendente(BaseHTTPRequestHandler):
        server_version = "Concilia"
        sys_version = ""

        def log_message(self, *args):
            pass  # nao enche a janela de mensagens tecnicas

        # ---------------------------------------------------------------
        def _endereco_ok(self):
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]").lower()
            return host in ("127.0.0.1", "localhost")

        def _enviar(self, codigo, corpo, tipo, extra=None):
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(corpo)

        def _json(self, codigo, dados):
            corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
            self._enviar(codigo, corpo, "application/json; charset=utf-8")

        # ---------------------------------------------------------------
        def do_GET(self):
            if not self._endereco_ok():
                return self._enviar(403, b"Proibido", "text/plain")
            url = urlsplit(self.path)

            if url.path in ("/", "/index.html"):
                html = PAGINA.read_text(encoding="utf-8").replace("__CHAVE__", chave)
                return self._enviar(200, html.encode("utf-8"), "text/html; charset=utf-8", {
                    "Content-Security-Policy":
                        "default-src 'self'; img-src 'self' data:; "
                        "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
                        "connect-src 'self'; frame-ancestors 'none'",
                })

            if url.path == "/relatorio":
                q = parse_qs(url.query)
                if q.get("chave", [""])[0] != chave:
                    return self._enviar(403, b"Proibido", "text/plain")
                item = relatorios.get(q.get("id", [""])[0])
                if item is None:
                    return self._enviar(404, "Relatório não encontrado. Concilie de novo.".encode(),
                                        "text/plain; charset=utf-8")
                nome, conteudo = item
                return self._enviar(200, conteudo,
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    {"Content-Disposition": f'attachment; filename="{nome}"'})

            return self._enviar(404, b"Nao encontrado", "text/plain")

        def do_POST(self):
            if not self._endereco_ok() or self.headers.get("X-Concilia-Chave") != chave:
                return self._json(403, {"ok": False, "erro": "Acesso negado."})
            url = urlsplit(self.path)
            try:
                tamanho = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                tamanho = 0
            if tamanho <= 0 or tamanho > LIMITE_BYTES:
                return self._json(413, {"ok": False,
                                        "erro": "Arquivo grande demais (o limite é 40 MB)."})
            try:
                pedido = json.loads(self.rfile.read(tamanho))
            except ValueError:
                return self._json(400, {"ok": False, "erro": "Pedido inválido."})

            if url.path == "/exemplo":
                return self._conciliar(EXEMPLOS / "agenda-exemplo.xlsx",
                                       EXEMPLOS / "extrato-exemplo.xlsx",
                                       "agenda-exemplo.xlsx", "extrato-exemplo.xlsx")

            if url.path == "/conciliar":
                with tempfile.TemporaryDirectory(prefix="concilia-") as pasta:
                    caminhos = []
                    nomes = []
                    for campo, padrao in (("agenda", "agenda.xlsx"), ("extrato", "extrato.xlsx")):
                        item = pedido.get(campo) or {}
                        nome = _nome_seguro(item.get("nome"), padrao)
                        if Path(nome).suffix.lower() not in EXTENSOES:
                            tipo = "recebiveis" if campo == "agenda" else "extrato"
                            return self._json(200, {
                                "ok": False, "arquivo": tipo, "rotulo": ROTULOS[tipo],
                                "erro": f"{nome} não é Excel (.xlsx) nem CSV. Se for .xls antigo, "
                                        "abra no Excel e salve como .xlsx. PDF ainda não é lido."})
                        try:
                            conteudo = base64.b64decode(item.get("conteudo") or "", validate=True)
                        except (binascii.Error, ValueError):
                            return self._json(400, {"ok": False, "erro": "Arquivo corrompido."})
                        caminho = Path(pasta) / f"{campo}{Path(nome).suffix.lower()}"
                        caminho.write_bytes(conteudo)
                        caminhos.append(caminho)
                        nomes.append(nome)
                    return self._conciliar(caminhos[0], caminhos[1], nomes[0], nomes[1])

            return self._json(404, {"ok": False, "erro": "Não encontrado."})

        def _conciliar(self, agenda, extrato, nome_agenda, nome_extrato):
            try:
                tudo = executar(agenda, extrato, nome_agenda, nome_extrato, hoje=hoje)
            except ArquivoComProblema as e:
                return self._json(200, {
                    "ok": False, "arquivo": e.tipo, "rotulo": ROTULOS[e.tipo], "erro": e.mensagem,
                    "faltando": [acentuar(c) for c in e.faltando], "colunas": e.colunas})
            except Exception as e:  # nunca deixa a tela travada sem explicacao
                return self._json(200, {"ok": False, "erro": f"Algo deu errado: {e}"})

            dados = tudo["dados"]
            memoria = io.BytesIO()
            relatorio.gravar(dados, memoria)
            ident = secrets.token_urlsafe(9)
            apelido = _apelido(nome_agenda)
            nome = f"relatorio-{apelido + '-' if apelido else ''}{date.today():%Y-%m-%d}.xlsx"
            relatorios.clear()  # so guarda o ultimo, pra nao acumular memoria
            relatorios[ident] = (nome, memoria.getvalue())
            dados["relatorio"] = {"url": f"/relatorio?id={ident}&chave={chave}", "nome": nome}
            dados["ok"] = True
            return self._json(200, dados)

    servidor = ThreadingHTTPServer(("127.0.0.1", porta), Atendente)
    servidor.daemon_threads = True
    return servidor, chave
