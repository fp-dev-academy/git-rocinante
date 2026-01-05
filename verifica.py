"""Verificador del curs de Git de la Rocinante.

Ús (des de la carpeta del repositori):

    python verifica.py NN

Comprova l'estat del repositori per al pas NN i mostra cada criteri com a
[OK] o [FALLA]. No modifica mai el repositori: només el llegeix.

Codis de sortida: 0 si se superen tots els criteris, 1 si en falla algun,
2 si no es pot fer la verificació (no hi ha git, no és un repositori o el
pas no existeix).
"""

import ast
import hashlib
import io
import re
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPOSITORI_GUIA = "github.com/fp-dev-academy/git-rocinante"
URL_GUIA_SSH = "git@github.com:fp-dev-academy/git-rocinante.git"

# L'omple el generador amb tots els tags del curs.
TAGS_DEL_CURS: tuple[str, ...] = ('pas-00', 'pas-01', 'pas-02', 'pas-03', 'pas-04', 'pas-05', 'v1.0', 'pas-06', 'pas-07')

# L'omple el generador: SHA-256 de les respostes esperades, ja normalitzades,
# per a cada "pas.clau". No hi ha cap resposta en clar.
RESPOSTES: dict[str, tuple[str, ...]] = {}


class ErrorEntorn(Exception):
    """No es pot fer la verificació (codi de sortida 2)."""


@dataclass
class Resultat:
    ok: bool
    criteri: str
    pista: str = ""


def criteri(ok: bool, text: str, pista: str) -> Resultat:
    return Resultat(ok, text, "" if ok else pista)


# --- Accés a git (només lectura) ---------------------------------------

def git(*args: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["git", "-c", "core.quotepath=off", *args],
            capture_output=True, encoding="utf-8",
        )
    except FileNotFoundError:
        raise ErrorEntorn("No es troba git. Comprova que Git for Windows està instal·lat.")


def sortida(*args: str) -> str:
    """Sortida d'una ordre de git, o "" si falla."""
    resultat = git(*args)
    return resultat.stdout.strip() if resultat.returncode == 0 else ""


def config(clau: str) -> str:
    return sortida("config", "--get", clau)


def normalitza_url(url: str) -> str:
    """Converteix una URL SSH o HTTPS en 'host/ruta', sense '.git' final."""
    url = url.strip().lower()
    coincidencia = (re.match(r"^(?:ssh://)?git@([^:/]+)[:/](.+)$", url)
                    or re.match(r"^https?://([^/]+)/(.+)$", url))
    if coincidencia is None:
        return url
    host, ruta = coincidencia.groups()
    ruta = ruta.rstrip("/")
    if ruta.endswith(".git"):
        ruta = ruta[:-4]
    return f"{host}/{ruta}"


def es_ssh(url: str) -> bool:
    return url.startswith(("git@", "ssh://"))


def es_avantpassat(avantpassat: str, descendent: str = "HEAD") -> bool:
    return git("merge-base", "--is-ancestor", avantpassat, descendent).returncode == 0


def commits_nous(des_de: str) -> list[str]:
    """Hashos dels commits de des_de..HEAD, del més antic al més nou."""
    return sortida("rev-list", "--reverse", f"{des_de}..HEAD").splitlines()


def fitxers_a_head() -> list[str]:
    return sortida("ls-tree", "-r", "--name-only", "HEAD").splitlines()


def directori_net() -> bool:
    return git("status", "--porcelain").stdout.strip() == ""


PATRO_CONVENTIONAL = re.compile(
    r"^(feat|fix|docs|refactor|test|chore)(\([a-z0-9-]+\))?!?: \S.*$")


def missatges_no_convencionals(des_de: str) -> list[str]:
    """Primeres línies de des_de..HEAD que no segueixen Conventional Commits.

    No es comproven els missatges que genera git (merges i reverts).
    """
    assumptes = sortida("log", "--no-merges", "--format=%s", f"{des_de}..HEAD").splitlines()
    return [a for a in assumptes
            if not a.startswith(('Revert "', "Merge "))
            and (PATRO_CONVENTIONAL.match(a) is None or len(a) > 72)]


def llista_literal(referencia: str, fitxer: str, nom: str):
    """Valor literal d'una assignació `nom = [...]` d'un fitxer a una referència.

    Fa servir ast: no s'executa mai el codi de l'alumne. Retorna None si el
    fitxer no existeix, té errors de sintaxi o no hi ha l'assignació.
    """
    font = sortida("show", f"{referencia}:{fitxer}")
    try:
        arbre = ast.parse(font)
    except SyntaxError:
        return None
    for node in arbre.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name) and node.targets[0].id == nom):
            try:
                return ast.literal_eval(node.value)
            except ValueError:
                return None
    return None


def funcions_definides(referencia: str, fitxer: str) -> set[str] | None:
    """Noms de les funcions d'un fitxer a una referència, o None si no compila."""
    try:
        arbre = ast.parse(sortida("show", f"{referencia}:{fitxer}"))
    except SyntaxError:
        return None
    return {n.name for n in arbre.body if isinstance(n, ast.FunctionDef)}


def en_detached_head() -> bool:
    return git("symbolic-ref", "--quiet", "HEAD").returncode != 0


def referencia_de_branca(nom: str) -> str:
    """Hash de la punta d'una branca de la tripulació: remota d'origin, local o d'upstream."""
    for ref in (f"refs/remotes/origin/{nom}", f"refs/heads/{nom}", f"refs/remotes/upstream/{nom}"):
        hash_ = sortida("rev-parse", "--verify", "--quiet", ref)
        if hash_:
            return hash_
    return ""


def executa_test_a_head(test: str) -> subprocess.CompletedProcess | None:
    """Executa un fitxer de tests sobre una còpia de HEAD en una carpeta temporal.

    No toca el directori de treball (ni hi crea __pycache__). Retorna None si
    no s'ha pogut fer la còpia.
    """
    arxiu = subprocess.run(["git", "archive", "--format=tar", "HEAD"], capture_output=True)
    if arxiu.returncode != 0:
        return None
    with tempfile.TemporaryDirectory() as directori:
        with tarfile.open(fileobj=io.BytesIO(arxiu.stdout)) as tar:
            tar.extractall(directori, filter="data")
        try:
            return subprocess.run([sys.executable, test], cwd=directori, capture_output=True,
                                  encoding="utf-8", timeout=60)
        except subprocess.TimeoutExpired:
            return None


# --- Fitxers de respostes ----------------------------------------------

def normalitza_nom(valor: str) -> str:
    return " ".join(valor.lower().split())


def normalitza_hash(valor: str) -> str:
    valor = valor.strip().lower()
    return valor[:7] if re.fullmatch(r"[0-9a-f]{7,40}", valor) else ""


def sha256(valor: str) -> str:
    return hashlib.sha256(valor.encode("utf-8")).hexdigest()


def llegeix_respostes(text: str) -> tuple[dict[str, str], list[str]]:
    """Parelles clau=valor d'un fitxer de respostes, i les línies mal formades."""
    respostes, errors = {}, []
    for linia in text.lstrip("\ufeff").splitlines():
        linia = linia.strip()
        if not linia or linia.startswith("#"):
            continue
        clau, igual, valor = linia.partition("=")
        if not igual or not clau.strip():
            errors.append(linia)
            continue
        respostes[clau.strip()] = valor.strip()
    return respostes, errors


def criteris_de_respostes(numero: str, normalitzadors: dict, pistes: dict) -> list[Resultat]:
    """Un criteri per a la versió del fitxer i un per a cada clau esperada."""
    ruta = f"respostes/pas-{numero}.txt"
    if ruta not in fitxers_a_head():
        return [criteri(False, f"{ruta} versionat",
                        f"Crea {ruta} i fes-ne commit (git add {ruta}).")]
    respostes, errors = llegeix_respostes(sortida("show", f"HEAD:{ruta}"))
    resultats = [criteri(not errors, f"{ruta} versionat i amb format clau=valor",
                         f"Línia no vàlida: «{errors[0]}». Exemple: "
                         f"{next(iter(normalitzadors))}=valor" if errors else "")]
    for clau, normalitza in normalitzadors.items():
        if clau not in respostes:
            resultats.append(criteri(False, f"{clau} correcte",
                                     f"Falta la clau {clau} a {ruta}."))
            continue
        valor = normalitza(respostes[clau])
        esperats = RESPOSTES.get(f"{numero}.{clau}", ())
        resultats.append(criteri(bool(valor) and sha256(valor) in esperats,
                                 f"{clau} correcte", pistes[clau]))
    return resultats


# --- Passos --------------------------------------------------------------
# Cada pas va entre les marques `# >>> pas NN` i `# <<< pas NN`: el generador
# esborra els passos posteriors al tag on es publica verifica.py.

PASSOS = {}


def pas(numero: str, titol: str):
    def registra(funcio):
        PASSOS[numero] = (titol, funcio)
        return funcio
    return registra


# >>> pas 00
@pas("00", "Embarcament")
def verifica_pas_00(repo: Path) -> list[Resultat]:
    nom = config("user.name")
    correu = config("user.email")
    origin = config("remote.origin.url")
    upstream = config("remote.upstream.url")
    tags = set(sortida("tag", "--list").splitlines())
    falten = [t for t in TAGS_DEL_CURS if t not in tags]
    return [
        criteri(bool(nom), "user.name definit",
                'git config --global user.name "El teu nom i cognom"'),
        criteri(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correu) is not None,
                "user.email definit amb format de correu",
                'git config --global user.email "el-teu-correu@exemple.cat"'),
        criteri(bool(config("core.editor")), "core.editor definit",
                "git config --global core.editor notepad"),
        criteri(bool(origin) and normalitza_url(origin) != REPOSITORI_GUIA,
                "origin apunta al teu fork, no al repositori guia",
                "Has clonat el repositori guia? Vegeu PISTES.md: git remote set-url origin ..."),
        criteri(es_ssh(origin), "origin fa servir SSH (git@...)",
                "git remote set-url origin git@github.com:<usuari>/git-rocinante.git"),
        criteri(normalitza_url(upstream) == REPOSITORI_GUIA,
                "upstream apunta al repositori guia",
                f"git remote add upstream {URL_GUIA_SSH}"),
        criteri(not falten, "hi ha tots els tags del curs en local",
                f"Falten {', '.join(falten)}. Prova: git fetch upstream --tags"),
        criteri(sys.version_info >= (3, 12),
                f"Python 3.12 o superior (tens {sys.version.split()[0]})",
                "Instal·la una versió de Python més recent."),
    ]
# <<< pas 00
















# --- Programa principal ----------------------------------------------------

def arrel_del_repositori() -> Path:
    resultat = git("rev-parse", "--show-toplevel")
    if resultat.returncode != 0:
        raise ErrorEntorn("Aquesta carpeta no és un repositori de Git. "
                          "Executa verifica.py des de la carpeta git-rocinante.")
    return Path(resultat.stdout.strip())


def main(arguments: list[str]) -> int:
    if len(arguments) != 1:
        raise ErrorEntorn("Ús: python verifica.py NN   (per exemple: python verifica.py 00)")
    numero = arguments[0].zfill(2)
    if numero not in PASSOS:
        disponibles = ", ".join(sorted(PASSOS))
        bisect_log = git("rev-parse", "--git-path", "BISECT_LOG")
        if bisect_log.returncode == 0 and Path(bisect_log.stdout.strip()).exists():
            raise ErrorEntorn(f"El pas {arguments[0]} no existeix en aquesta versió de "
                              f"verifica.py: hi ha un git bisect en curs, i HEAD és en un "
                              f"commit antic, amb un verifica.py antic.\n"
                              f"Acaba primer el bisect i torna a la teva branca:\n"
                              f"  git bisect reset")
        raise ErrorEntorn(f"El pas {arguments[0]} no existeix en aquesta versió de "
                          f"verifica.py. Passos disponibles: {disponibles}.\n"
                          f"Si has fet un reset a un commit anterior al pas, verifica.py "
                          f"també ha tornat enrere. Torna a començar el pas:\n"
                          f"  git switch -C treball/pas-{numero} pas-{numero}")
    repo = arrel_del_repositori()
    titol, funcio = PASSOS[numero]
    print(f"Pas {numero} - {titol}\n")
    resultats = funcio(repo)
    for resultat in resultats:
        print(f"[{'OK' if resultat.ok else 'FALLA'}] {resultat.criteri}")
        if resultat.pista:
            print(f"        Pista: {resultat.pista}")
    superats = sum(r.ok for r in resultats)
    print(f"\n{superats} de {len(resultats)} criteris superats.")
    if superats == len(resultats):
        print("Pas superat. Bona feina, tripulant.")
        return 0
    print("Encara no. Revisa les pistes o llegeix PISTES.md.")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except ErrorEntorn as error:
        print(error)
        sys.exit(2)
