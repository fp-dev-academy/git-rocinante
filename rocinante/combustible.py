"""Càlculs de la sala de màquines."""


def calcula_consum(massa_t, acceleracio_g):
    """Consum de massa de reacció, en tones per hora.

    0.8 és el factor de rendiment del motor Epstein de la Rocinante.
    """
    return massa_t * acceleracio_g * 0.8


def consum_en_repos(massa_t):
    """Consum de massa de reacció amb els motors al ralentí, en tones per hora."""
    return massa_t * 0.01
