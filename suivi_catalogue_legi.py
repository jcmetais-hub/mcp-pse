"""Inventaire expérimental du catalogue public LEGI : aucune garantie de continuité."""
import argparse
from datetime import datetime
from html.parser import HTMLParser
import json
from pathlib import Path
import re

INCREMENT = re.compile(r'LEGI_(\d{8}-\d{6})\.tar\.gz\Z')
STOCK = re.compile(r'Freemium_legi_global_(\d{8}-\d{6})\.tar\.gz\Z')

class LecteurLiens(HTMLParser):
    def __init__(self):
        super().__init__(); self.liens = []; self.titre = ''; self._titre = False
    def handle_starttag(self, tag, attrs):
        if tag == 'title': self._titre = True
        if tag == 'a':
            href = dict(attrs).get('href')
            if href is not None: self.liens.append(href)
    def handle_endtag(self, tag):
        if tag == 'title': self._titre = False
    def handle_data(self, data):
        if self._titre: self.titre += data


def lire_catalogue(html):
    parser=LecteurLiens(); parser.feed(html)
    if parser.titre.strip() != 'Index of /OPENDATA/LEGI':
        raise ValueError('Catalogue non reconnu ou réponse de blocage.')
    stocks=[]; increments=[]
    for nom in parser.liens:
        match=STOCK.fullmatch(nom) or INCREMENT.fullmatch(nom)
        if not match: continue
        try: datetime.strptime(match.group(1), '%Y%m%d-%H%M%S')
        except ValueError as exc: raise ValueError('Horodatage invalide : '+nom) from exc
        (stocks if STOCK.fullmatch(nom) else increments).append(nom)
    if not stocks or not increments:
        raise ValueError('Catalogue sans stock ou incréments : vérification impossible.')
    if len(set(stocks)) != len(stocks) or len(set(increments)) != len(increments):
        raise ValueError('Archive en double dans le catalogue.')
    return {'source': 'https://echanges.dila.gouv.fr/OPENDATA/LEGI/',
            'stocks': sorted(stocks), 'increments': sorted(increments),
            'continuite_garantie': False,
            'avertissement': 'Un catalogue seul ne prouve pas que toutes les archives ont été conservées ; conserver les catalogues successifs et vérifier les lacunes.'}


def comparer_catalogues(avant, apres):
    a=set(avant['stocks']+avant['increments']); b=set(apres['stocks']+apres['increments'])
    return {'nouvelles': sorted(b-a), 'disparues': sorted(a-b),
            'continuite_garantie': False,
            'avertissement': 'Une disparition observée impose une vérification ; une absence de disparition ne prouve pas la continuité. Le contenu des archives n’est pas comparé.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('catalogue', help='Catalogue HTML récupéré depuis DILA')
    p.add_argument('--avant', help='Catalogue HTML antérieurement conservé')
    args=p.parse_args(); current=lire_catalogue(Path(args.catalogue).read_text(encoding='utf8'))
    if args.avant:
        current={'actuel':current,'comparaison':comparer_catalogues(lire_catalogue(Path(args.avant).read_text(encoding='utf8')),current)}
    print(json.dumps(current, ensure_ascii=True, indent=2))

if __name__ == '__main__': main()
