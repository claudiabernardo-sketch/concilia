"""Roda todos os testes e mostra o resultado em portugues."""

import testes.teste_motor as suite
import testes.teste_fatias  # noqa: F401  (registra os testes na mesma lista)
import testes.teste_tela  # noqa: F401


def main():
    passou = falhou = 0
    grupo_atual = None

    for grupo, nome, fn in suite.TESTES:
        if grupo != grupo_atual:
            print("\n" + grupo)
            grupo_atual = grupo
        try:
            fn()
            print("  ok    " + nome)
            passou += 1
        except AssertionError as e:
            print("  FALHA " + nome)
            print("        " + str(e))
            falhou += 1
        except Exception as e:
            print("  ERRO  " + nome)
            print(f"        {type(e).__name__}: {e}")
            falhou += 1

    print()
    if falhou == 0:
        print(f"TODOS OS {passou} TESTES PASSARAM")
    else:
        print(f"{passou} passaram, {falhou} FALHARAM")
    print()
    return 0 if falhou == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
