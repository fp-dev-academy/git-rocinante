"""Càlculs de la sala de màquines."""


def calcula_consum(massa_t, acceleracio_g, eficiencia=1.0,
                   mode_combat=False):
    """Consum de massa de reacció, en tones per hora.

    0.8 és el factor de rendiment del motor Epstein de la Rocinante.
    """
    factor = 1.5 if mode_combat else 1.0
    return massa_t * acceleracio_g * 0.8 * factor / eficiencia


def consum_en_repos(massa_t):
    """Consum de massa de reacció amb els motors al ralentí.

    La massa és en tones i el resultat, en tones per hora.
    """
    return massa_t * 0.01
