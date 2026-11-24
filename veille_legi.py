"""Analyse ponctuelle d'archives LEGI DILA, sans prétention d'exhaustivité."""
import argparse
import json
import re
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path

CIBLES = {
    'JORFTEXT000038349752': 'CAP',
    'JORFTEXT000038349745': 'seconde bac pro',
    'JORFTEXT000041529241': 'première et terminale bac pro',
}
MAX_FICHIER = 8 * 1024 * 1024
MAX_ENTREES = 300000


def analyser_archive(chemin):
    chemin = Path(chemin)
    result = {
        'archive': chemin.name,
        'source_repertoire': 'https://echanges.dila.gouv.fr/OPENDATA/LEGI/',
        'provenance': 'Fichier local fourni par l’utilisateur ; sa provenance et son intégrité ne sont pas vérifiées.',
        'versions': [], 'details_versions': [], 'erreurs': [], 'suppressions_a_verifier': [],
        'couverture_complete': False,
        'avertissement': "Analyse d'une archive incrémentale isolée : aucune conclusion sur l'actualité ou l'absence de changement ; historique, suppressions, annexes et continuité non reconstitués. Une réémission peut concerner une version ancienne.",
    }
    try:
        with tarfile.open(chemin, 'r:gz') as archive:
            for i, membre in enumerate(archive):
                if i >= MAX_ENTREES:
                    result['erreurs'].append('Nombre maximal de fichiers dépassé.')
                    break
                if not membre.isfile():
                    continue
                nom = membre.name
                suppression = Path(nom).name in ('liste_suppression_legi.dat', 'liste_suppression_legi_dossier.dat')
                cible = next((c for c in CIBLES if ('/' + c + '/') in nom), None)
                structure = cible and '/texte/struct/' in nom and nom.endswith('.xml')
                version = cible and '/texte/version/' in nom and nom.endswith('.xml')
                if not (structure or version or suppression):
                    continue
                if membre.size > MAX_FICHIER:
                    result['erreurs'].append('Fichier trop volumineux : ' + nom)
                    continue
                stream = archive.extractfile(membre)
                if stream is None:
                    result['erreurs'].append('Fichier inaccessible : ' + nom)
                    continue
                data = stream.read(MAX_FICHIER + 1)
                if suppression:
                    if data.strip():
                        result['suppressions_a_verifier'].append({'fichier': nom, 'octets': len(data)})
                    continue
                try:
                    if re.search(br'<!\s*(DOCTYPE|ENTITY)', data, re.I):
                        raise ValueError('DTD interdite')
                    xml = ET.fromstring(data)
                    cid = xml.findtext('./META/META_SPEC/META_TEXTE_CHRONICLE/CID')
                    if cid != cible:
                        raise ValueError('Identifiant XML incohérent')
                    chron = xml.find('./META/META_SPEC/META_TEXTE_CHRONICLE')
                    if version:
                        info = xml.find('./META/META_SPEC/META_TEXTE_VERSION')
                        if info is None:
                            raise ValueError('Métadonnées de version manquantes')
                        modifications = [
                            {'nor': lien.get('nortexte'), 'texte_id': lien.get('cidtexte'),
                             'article': lien.get('num'), 'date': lien.get('datesignatexte'),
                             'libelle': ''.join(lien.itertext()).strip()}
                            for lien in info.findall('./LIENS/LIEN')
                            if lien.get('typelien') == 'MODIFIE' and lien.get('sens') == 'cible'
                        ]
                        result['details_versions'].append({
                            'niveau': CIBLES[cible], 'cid': cid, 'fichier_xml': nom,
                            'id': xml.findtext('./META/META_COMMUN/ID'),
                            'titre': info.findtext('TITREFULL'), 'etat': info.findtext('ETAT'),
                            'debut': info.findtext('DATE_DEBUT'), 'fin': info.findtext('DATE_FIN'),
                            'modifications': modifications,
                        })
                        continue
                    versions = []
                    for ver in xml.findall('./VERSIONS/VERSION'):
                        lien = ver.find('LIEN_TXT')
                        if lien is not None:
                            versions.append({'etat': ver.get('etat'), 'debut': lien.get('debut'), 'fin': lien.get('fin'), 'id': lien.get('id')})
                    result['versions'].append({
                        'niveau': CIBLES[cible], 'cid': cid, 'fichier_xml': nom,
                        'nor': chron.findtext('NOR'), 'date_texte': chron.findtext('DATE_TEXTE'),
                        'derniere_modification': chron.findtext('DERNIERE_MODIFICATION'),
                        'versions': versions,
                    })
                except (ET.ParseError, ValueError, AttributeError) as error:
                    result['erreurs'].append('XML invalide ou incohérent : ' + nom + ' (' + type(error).__name__ + ')')
    except (OSError, tarfile.TarError, EOFError) as error:
        raise ValueError('Archive LEGI inaccessible ou invalide.') from error
    return result


def comparer_etats(avant, apres):
    """Compare uniquement des versions explicitement fournies, sans assurer leur exhaustivité."""
    champs = ('id', 'titre', 'etat', 'debut', 'fin', 'modifications')
    result = {
        'resultats': {}, 'couverture_complete': False,
        'avertissement': "Comparaison limitée aux métadonnées fournies : ne prouve ni la continuité des archives ni la présence des annexes ou l'absence d'autres changements.",
    }
    for cid in CIBLES:
        entrees = []
        for ensemble in (avant, apres):
            actifs = [v for v in ensemble if isinstance(v, dict) and v.get('cid') == cid and v.get('etat') == 'VIGUEUR']
            if len(actifs) != 1 or any(k not in actifs[0] or actifs[0][k] is None for k in champs):
                entrees.append(None)
            else:
                selection = {k: actifs[0][k] for k in champs}
                if not all(isinstance(selection[k], str) and selection[k] for k in ('id', 'titre', 'etat', 'debut', 'fin')) or not isinstance(selection['modifications'], list):
                    entrees.append(None)
                else:
                    selection['modifications'] = sorted(selection['modifications'], key=lambda x: json.dumps(x, sort_keys=True, ensure_ascii=False))
                    entrees.append(selection)
        ancienne, nouvelle = entrees
        statut = 'incomplet' if ancienne is None or nouvelle is None else ('aucune_difference_observee' if ancienne == nouvelle else 'changement_detecte')
        result['resultats'][cid] = {'niveau': CIBLES[cid], 'statut': statut, 'avant': ancienne, 'apres': nouvelle}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', nargs='?', help='Archive incrémentale LEGI officielle téléchargée')
    parser.add_argument('--comparer', nargs=2, metavar=('AVANT', 'APRES'), help='Comparer les métadonnées de deux archives locales')
    args = parser.parse_args()
    if bool(args.archive) == bool(args.comparer):
        parser.error('Indiquer une archive OU --comparer AVANT APRES.')
    if args.comparer:
        a, b = [analyser_archive(p) for p in args.comparer]
        result = comparer_etats(a['details_versions'] if not a['erreurs'] else [], b['details_versions'] if not b['erreurs'] else [])
        result['archives'] = [{'archive': v['archive'], 'erreurs': v['erreurs'], 'suppressions_a_verifier': v['suppressions_a_verifier']} for v in (a, b)]
    else:
        result = analyser_archive(args.archive)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
