"""Le relevé du matin : relit tous les classeurs exploités. Lancé par planeo-releve.timer.

N'écrit que des nombres dans le journal, jamais un nom ni un numéro.
"""
import groupes

resultats = groupes.releve_tous()
print(f"Relevé : {sum(resultats)} classeur(s) lu(s), {len(resultats) - sum(resultats)} en échec.")
