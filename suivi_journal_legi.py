"""Journal expérimental d'incréments LEGI locaux ; ne constitue pas un état juridique."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import tempfile
from datetime import datetime, timezone

from suivi_catalogue_legi import lire_catalogue
from veille_legi import analyser_archive

MAX_DECOMPRESSE = 1024 * 1024 * 1024


def empreinte(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def verifier_gzip(path):
    total=0
    with gzip.open(path,'rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            total+=len(block)
            if total > MAX_DECOMPRESSE:
                raise ValueError('Archive décompressée trop volumineuse.')


def actualiser(html, dossier, journal):
    catalogue=lire_catalogue(html); dossier=Path(dossier); journal=Path(journal)
    result={'statut':'incomplet', 'absentes':[], 'alterees':[], 'disparues':[],
            'hors_ordre':[], 'erreurs':[], 'nouvelles':[], 'continuite_garantie':False,
            'avertissement':'Journal local expérimental : sans stock initial ni traitement des suppressions, il ne reconstitue pas le droit ni ne prouve la continuité ou l’actualité des programmes.'}
    if journal.exists():
        try:
            ancien=json.loads(journal.read_text(encoding='utf8'))
            if ancien.get('schema') != 1 or not isinstance(ancien.get('archives'),dict): raise ValueError('Format invalide')
            for nom, info in ancien['archives'].items():
                if not isinstance(nom,str) or not isinstance(info,dict) or not isinstance(info.get('sha256'),str): raise ValueError('Entrée invalide')
        except (OSError, ValueError, AttributeError) as exc:
            result['erreurs'].append('Journal illisible ou invalide : '+type(exc).__name__)
            return result
    else:
        ancien={'schema':1,'archives':{}}
    archives=ancien['archives']; visibles=catalogue['increments']
    result['disparues']=sorted(set(archives)-set(visibles))
    nouvelles=[n for n in visibles if n not in archives]
    if archives:
        derniere=max(archives)
        result['hors_ordre']=[n for n in nouvelles if n < derniere]
    result['nouvelles']=nouvelles
    for nom in visibles:
        path=dossier/nom
        if not path.is_file():
            result['absentes'].append(nom); continue
        try:
            h=empreinte(path)
            if nom in archives and h != archives[nom]['sha256']:
                result['alterees'].append(nom)
        except OSError:
            result['erreurs'].append('Lecture impossible : '+nom)
    if any(result[k] for k in ('absentes','alterees','disparues','hors_ordre','erreurs')):
        return result
    nouveau=dict(archives)
    for nom in nouvelles:
        path=dossier/nom
        try:
            h1=empreinte(path); verifier_gzip(path); analyse=analyser_archive(path); h2=empreinte(path)
            if h1 != h2: raise ValueError('Archive modifiée pendant la lecture')
            if analyse['erreurs']: raise ValueError('Analyse partielle : '+str(analyse['erreurs']))
            nouveau[nom]={'sha256':h2, 'taille':path.stat().st_size,
                          'versions':analyse['versions'], 'details_versions':analyse['details_versions'],
                          'suppressions_a_verifier':analyse['suppressions_a_verifier']}
        except (OSError, ValueError, EOFError) as exc:
            result['erreurs'].append(nom+' : '+str(exc))
            return result
    if not nouvelles:
        result['statut']='aucune_nouvelle_archive'; return result
    payload={'schema':1,'cree_ou_actualise_utc':datetime.now(timezone.utc).isoformat(),
             'source_catalogue':catalogue['source'], 'archives':nouveau,
             'avertissement':result['avertissement']}
    journal.parent.mkdir(parents=True,exist_ok=True)
    temp=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf8',dir=journal.parent,prefix='.journal-',suffix='.tmp',delete=False) as f:
            temp=Path(f.name); json.dump(payload,f,ensure_ascii=False,indent=2); f.flush(); os.fsync(f.fileno())
        os.replace(temp,journal)
    finally:
        if temp and temp.exists(): temp.unlink()
    result['statut']='enregistre'
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('catalogue'); p.add_argument('dossier'); p.add_argument('journal')
    args=p.parse_args(); html=Path(args.catalogue).read_text(encoding='utf8')
    r=actualiser(html,args.dossier,args.journal)
    print(json.dumps(r,ensure_ascii=True,indent=2))
    if r['statut']=='incomplet': raise SystemExit(1)

if __name__=='__main__': main()
