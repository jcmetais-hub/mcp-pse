import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from suivi_journal_legi import actualiser

N1='LEGI_20261116-104909.tar.gz'
N2='LEGI_20261116-212357.tar.gz'
STOCK='Freemium_legi_global_20261108-140000.tar.gz'

def catalogue(names):
    return '<title>Index of /OPENDATA/LEGI</title>' + ''.join('<a href="'+n+'">x</a>' for n in [STOCK]+names)
def archive(path):
    with tarfile.open(path,'w:gz') as t:
        b=b'hello'; i=tarfile.TarInfo('x/other.txt'); i.size=len(b); t.addfile(i,io.BytesIO(b))

class JournalTest(unittest.TestCase):
    def test_premiere_execution_et_rejeu_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); archive(root/N1); archive(root/N2); journal=root/'journal.json'
            result=actualiser(catalogue([N2,N1]),root,journal)
            self.assertEqual(result['statut'],'enregistre')
            self.assertEqual(list(json.loads(journal.read_text(encoding='utf8'))['archives']),[N1,N2])
            self.assertFalse(result['continuite_garantie'])
            avant=journal.read_bytes(); r2=actualiser(catalogue([N1,N2]),root,journal)
            self.assertEqual(r2['statut'],'aucune_nouvelle_archive'); self.assertEqual(journal.read_bytes(),avant)

    def test_archive_absente_interdit_avancee(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); archive(root/N1); j=root/'journal.json'
            r=actualiser(catalogue([N1,N2]),root,j)
            self.assertEqual(r['statut'],'incomplet'); self.assertIn(N2,r['absentes']); self.assertFalse(j.exists())

    def test_archive_alteree_interdit_modification_du_journal(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); archive(root/N1); j=root/'journal.json'
            actualiser(catalogue([N1]),root,j); old=j.read_bytes(); (root/N1).write_bytes(b'modifie')
            r=actualiser(catalogue([N1]),root,j)
            self.assertEqual(r['statut'],'incomplet'); self.assertIn(N1,r['alterees']); self.assertEqual(j.read_bytes(),old)

    def test_gzip_tronque_interdit_avancee(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); p=root/N1; archive(p); p.write_bytes(p.read_bytes()[:-6]); j=root/'journal.json'
            r=actualiser(catalogue([N1]),root,j)
            self.assertEqual(r['statut'],'incomplet'); self.assertTrue(r['erreurs']); self.assertFalse(j.exists())

    def test_archive_corrompue_interdit_avancee(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/N1).write_bytes(b'not gz'); j=root/'journal.json'
            r=actualiser(catalogue([N1]),root,j)
            self.assertEqual(r['statut'],'incomplet'); self.assertTrue(r['erreurs']); self.assertFalse(j.exists())

    def test_disparition_signalee_et_conserve_etat(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); archive(root/N1); archive(root/N2); j=root/'journal.json'
            actualiser(catalogue([N1,N2]),root,j); old=j.read_bytes()
            r=actualiser(catalogue([N2]),root,j)
            self.assertEqual(r['statut'],'incomplet'); self.assertIn(N1,r['disparues']); self.assertEqual(old,j.read_bytes())

    def test_retour_en_arriere_refuse(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); archive(root/N2); j=root/'journal.json'; actualiser(catalogue([N2]),root,j)
            old=j.read_bytes(); archive(root/N1)
            r=actualiser(catalogue([N1,N2]),root,j)
            self.assertEqual(r['statut'],'incomplet'); self.assertIn(N1,r['hors_ordre']); self.assertEqual(old,j.read_bytes())
