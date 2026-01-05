"""Càlculs de la sala de màquines."""


def calcula_consum(massa_t, acceleracio_g):
    """Consum de massa de reacció, en tones per hora.

    0.8 és el factor de rendiment del motor Epstein de la Rocinante.
    """
    return massa_t * acceleracio_g * 0.8
