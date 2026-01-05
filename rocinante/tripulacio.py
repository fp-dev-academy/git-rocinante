"""Tripulació de la Rocinante."""

TRIPULACIO = [
    {"nom": "James Holden", "rol": "capità"},
    {"nom": "Naomi Nagata", "rol": "enginyera"},
    {"nom": "Amos Burton", "rol": "mecànic en cap"},
    {"nom": "Alex Kamal", "rol": "pilot"},
]


def noms():
    """Retorna els noms de tota la tripulació."""
    return [tripulant["nom"] for tripulant in TRIPULACIO]


def es_a_bord(nom):
    """Diu si hi ha algú amb aquest nom a la tripulació."""
    return nom in noms()


def capita():
    """Retorna el tripulant que té el rol de capità."""
    return next(t for t in TRIPULACIO if t["rol"] == "capità")


def alta(nom, rol):
    """Dona d'alta un tripulant nou (només durant l'execució)."""
    tripulant = {"nom": nom.strip(), "rol": rol.strip()}
    TRIPULACIO.append(tripulant)
    return tripulant
