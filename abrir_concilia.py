"""Abre a tela do Concilia no navegador.

    python abrir_concilia.py

Deixe a janela aberta enquanto usa. Para fechar, feche a janela ou aperte
Ctrl+C. Tudo roda neste computador: nada vai para a internet.
"""

import sys
import threading
import webbrowser

from concilia.servidor import criar_servidor

PORTA_PREFERIDA = 8765


def main():
    try:
        servidor, _ = criar_servidor(PORTA_PREFERIDA)
    except OSError:
        servidor, _ = criar_servidor(0)  # a 8765 esta ocupada, usa qualquer uma livre

    endereco = f"http://127.0.0.1:{servidor.server_port}/"
    print("=" * 60)
    print("CONCILIA esta aberto")
    print("=" * 60)
    print(f"  Endereco: {endereco}")
    print("  Se o navegador nao abrir sozinho, copie o endereco acima.")
    print()
    print("  Deixe esta janela aberta enquanto usa o Concilia.")
    print("  Para fechar: feche esta janela ou aperte Ctrl+C.")
    print("  Nada sai deste computador.")
    print("=" * 60)
    sys.stdout.flush()

    if "--sem-navegador" not in sys.argv:
        threading.Timer(0.8, webbrowser.open, [endereco]).start()

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nConcilia fechado.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
