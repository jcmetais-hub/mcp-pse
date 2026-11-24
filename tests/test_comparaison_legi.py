import io
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
import unittest
from veille_legi import comparer_etats

C='JORFTEXT000041529241'

def etat(version, date='2026-02-19', **extra):
    return {'cid': C, 'id': version, 'etat': 'VIGUEUR', 'debut': date,
            'titre': 'Titre', 'fin': '2999-01-01', 'modifications': [], **extra}

class ComparaisonTest(unittest.TestCase):
    def test_cli_compare_deux_archives_et_signale_couverture(self):
        xml = '''<TEXTE_VERSION><META><META_COMMUN><ID>LEGITEXT1</ID></META_COMMUN><META_SPEC><META_TEXTE_CHRONICLE><CID>JORFTEXT000041529241</CID></META_TEXTE_CHRONICLE><META_TEXTE_VERSION><TITREFULL>Titre</TITREFULL><ETAT>VIGUEUR</ETAT><DATE_DEBUT>2026-02-19</DATE_DEBUT><DATE_FIN>2999-01-01</DATE_FIN><LIENS/></META_TEXTE_VERSION></META_SPEC></META></TEXTE_VERSION>'''
        with tempfile.TemporaryDirectory() as folder:
            paths=[Path(folder)/'a.tar.gz', Path(folder)/'b.tar.gz']
            for path in paths:
                with tarfile.open(path,'w:gz') as tar:
                    data=xml.encode('utf8'); entry=tarfile.TarInfo('x/'+C+'/texte/version/LEGITEXT1.xml'); entry.size=len(data); tar.addfile(entry,io.BytesIO(data))
            res=subprocess.run([sys.executable,'veille_legi.py','--comparer',str(paths[0]),str(paths[1])],capture_output=True,text=True,encoding='utf8',check=True)
            output=json.loads(res.stdout)
            self.assertEqual(output['resultats'][C]['statut'], 'aucune_difference_observee')
            self.assertFalse(output['couverture_complete'])

    def test_modification_de_version_detectee(self):
        r=comparer_etats([etat('LEGITEXT1')],[etat('LEGITEXT2')])
        self.assertEqual(r['resultats'][C]['statut'], 'changement_detecte')
        self.assertEqual(r['resultats'][C]['avant']['id'], 'LEGITEXT1')
        self.assertEqual(r['resultats'][C]['apres']['id'], 'LEGITEXT2')

    def test_absence_n_est_pas_une_confirmation(self):
        r=comparer_etats([etat('LEGITEXT1')],[])
        self.assertEqual(r['resultats'][C]['statut'], 'incomplet')
        self.assertFalse(r['couverture_complete'])

    def test_reemission_identique_pas_un_nouveau_changement(self):
        r=comparer_etats([etat('LEGITEXT1')],[etat('LEGITEXT1')])
        self.assertEqual(r['resultats'][C]['statut'], 'aucune_difference_observee')
        self.assertFalse(r['couverture_complete'])

    def test_deux_versions_actuelles_sont_ambigues(self):
        r=comparer_etats([etat('LEGITEXT1')],[etat('LEGITEXT1'),etat('LEGITEXT2')])
        self.assertEqual(r['resultats'][C]['statut'], 'incomplet')

    def test_metadata_manquante_ne_valide_pas(self):
        r=comparer_etats([etat('LEGITEXT1')],[{'cid':C, 'id':'LEGITEXT1','etat':'VIGUEUR'}])
        self.assertEqual(r['resultats'][C]['statut'], 'incomplet')
