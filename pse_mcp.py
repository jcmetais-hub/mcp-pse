"""MCP de consultation des références officielles PSE (lecture seule)."""
import json
import subprocess
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from mcp.server.mcpserver import MCPServer
from pypdf import PdfReader

mcp = MCPServer('PSE - références officielles')
SOURCE = 'https://data.education.gouv.fr/explore/dataset/fr-en-programmes-enseignement-2nd-degre/'
API = 'https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/fr-en-programmes-enseignement-2nd-degre/records'
NIVEAUX = {
    'cap-1': 'Première année de CAP',
    'cap-2': 'Deuxième année de CAP',
    'seconde': 'Seconde professionnelle',
    'premiere': 'Première professionnelle',
    'terminale': 'Terminale professionnelle',
}
DOCUMENTS = {
    'cap': ('cap.pdf', 'https://eduscol.education.gouv.fr/sites/default/files/document/spe641annexe1105406pdf-85401.pdf'),
    'seconde': ('seconde.pdf', 'https://www.education.gouv.fr/bo/19/Special5/MENE1908632A.htm'),
    'premiere': ('premiere.pdf', 'https://www.education.gouv.fr/bo/20/Special1/MENE2003005A.htm'),
    'terminale': ('terminale.pdf', 'https://www.education.gouv.fr/bo/20/Special1/MENE2003005A.htm'),
}


def fetch_records(*, where):
    url = API + '?' + urlencode({'where': where, 'limit': 100})
    try:
        p = subprocess.run(['curl', '--disable', '--fail', '--silent', '--show-error', '--max-time', '20', url], capture_output=True, text=True, encoding='utf-8', timeout=25, check=True)
        data = json.loads(p.stdout)
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        raise RuntimeError('Impossible de consulter les données officielles. Réessayez ou consultez la source.') from error
    if not isinstance(data, dict) or not isinstance(data.get('results'), list):
        raise RuntimeError('Réponse inattendue du portail officiel.')
    return data


@mcp.tool()
def rechercher_programmes(niveau: str = 'tous', inclure_archives: bool = False) -> dict:
    """Cherche les références PSE CAP/bac pro. Niveaux : tous, cap-1, cap-2, seconde, premiere, terminale. Vérifier les textes en vigueur : index seulement."""
    if niveau != 'tous' and niveau not in NIVEAUX:
        raise ValueError('Niveau inconnu. Choisir : tous, cap-1, cap-2, seconde, premiere, terminale.')
    where = 'discipline="Prévention Santé Environnement"'
    if niveau != 'tous':
        where += ' AND niveau_d_enseignement="' + NIVEAUX[niveau] + '"'
    if not inclure_archives:
        where += ' AND abroge_a_la_rentree="-"'
    data = fetch_records(where=where)
    return {
        'source': SOURCE,
        'inclut_archives': inclure_archives,
        'nombre_total': data.get('total_count'),
        'tronque': isinstance(data.get('total_count'), int) and data['total_count'] > len(data['results']),
        'references': data['results'],
        'avertissement': "Index de références, pas le texte intégral. Une absence d'année d'abrogation ne garantit pas l'actualité : vérifier le texte officiel, sa version et la session applicables.",
    }


def normaliser(texte):
    return ''.join(c for c in unicodedata.normalize('NFD', texte.casefold()) if not unicodedata.combining(c))


@mcp.tool()
def rechercher_contenu_programme(niveau: str, recherche: str) -> dict:
    """Recherche une expression dans les PDF officiels locaux. Niveaux : cap, seconde, premiere, terminale. Pages PDF et extraits à vérifier dans la source."""
    if niveau not in DOCUMENTS:
        raise ValueError('Niveau inconnu : cap, seconde, premiere ou terminale.')
    recherche = recherche.strip()
    if not 3 <= len(recherche) <= 100 or len(normaliser(recherche).strip()) < 3:
        raise ValueError('La recherche doit contenir entre 3 et 100 caractères.')
    fichier, source = DOCUMENTS[niveau]
    chemin = Path(__file__).resolve().parent / 'documents' / fichier
    try:
        reader = PdfReader(str(chemin))
        resultats = []
        for numero, page in enumerate(reader.pages, 1):
            texte = ' '.join((page.extract_text() or '').split())
            if normaliser(recherche) in normaliser(texte):
                resultats.append({'page_pdf': numero, 'texte_page': texte[:6000], 'page_tronquee': len(texte) > 6000})
    except (OSError, ValueError) as error:
        raise RuntimeError('Impossible de lire le programme local.') from error
    return {
        'niveau': niveau, 'source': source, 'fichier': fichier,
        'nombre_pages_trouvees': len(resultats), 'tronque': len(resultats) > 6,
        'extraits': resultats[:6],
        'avertissement': 'Extraction automatique : vérifier les passages dans le PDF original, les numéros de page et la version applicable ; ne transmettez pas de données personnelles.',
    }


REFERENCES_ATTENDUES = {
    'cap-1': 'arrêté du 3-4-2019 - J.O. du 9-4-2019',
    'cap-2': 'arrêté du 3-4-2019 - J.O. du 9-4-2019',
    'seconde': 'arrêté du 3-4-2019 - J.O. du 9-4-2019',
    'premiere': 'Arrêté du 3-2-2020 - J.O. du 5-2-2020',
    'terminale': 'Arrêté du 3-2-2020 - J.O. du 5-2-2020',
}


@mcp.tool()
def verifier_mises_a_jour(niveau: str) -> dict:
    """Compare la référence d'un niveau à l'index ministériel, sans certifier la validité juridique ou surveiller automatiquement."""
    if niveau not in NIVEAUX:
        raise ValueError('Niveau inconnu. Choisir : cap-1, cap-2, seconde, premiere, terminale.')
    result = {
        'niveau': niveau,
        'verifie_le_utc': datetime.now(timezone.utc).isoformat(),
        'source': SOURCE,
        'reference_attendue': REFERENCES_ATTENDUES[niveau],
        'references_observees': [],
        'statut': 'verification_incomplete',
        'avertissement': "Comparaison de l'index uniquement : elle ne garantit pas que le texte ou le PDF soit à jour. Des modifications peuvent ne pas figurer dans l'index. Vérifier la version consolidée et les annexes officielles. Aucun contrôle automatique ni remplacement de PDF.",
    }
    try:
        data = fetch_records(where='discipline="Prévention Santé Environnement" AND niveau_d_enseignement="' + NIVEAUX[niveau] + '"')
    except RuntimeError:
        result['motif'] = 'Index officiel inaccessible.'
        return result
    records = data['results']
    if (not isinstance(data.get('total_count'), int)
            or data['total_count'] != len(records)
            or not records
            or any(not isinstance(r, dict) or not isinstance(r.get('texte_officiel'), str)
                   or not isinstance(r.get('abroge_a_la_rentree'), str)
                   or r.get('niveau_d_enseignement') != NIVEAUX[niveau] for r in records)):
        result['motif'] = 'Réponse vide, tronquée ou incomplète.'
        return result
    actifs = [r for r in records if r['abroge_a_la_rentree'] == '-']
    result['references_observees'] = actifs
    if not actifs:
        result['motif'] = 'Aucune référence active dans l’index.'
        return result
    observes = {r['texte_officiel'].strip().casefold() for r in actifs}
    if observes == {REFERENCES_ATTENDUES[niveau].strip().casefold()}:
        result['statut'] = 'aucun_changement_detecte_dans_index'
    else:
        result['statut'] = 'changement_detecte'
    return result


if __name__ == '__main__':
    mcp.run(transport='stdio')
