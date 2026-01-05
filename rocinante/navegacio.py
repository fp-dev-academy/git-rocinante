"""Càlculs de navegació."""

VELOCITAT_LLUM_KMS = 299_792.458


def temps_trajecte(distancia_km, velocitat_kms):
    """Temps de trajecte en hores, amb la velocitat en km/s."""
    return distancia_km / velocitat_kms / 3600


def rumb_emergencia(rumb_perill):
    """Rumb d'emergència (en graus): el sentit contrari al del perill."""
    return (rumb_perill + 180) % 360
