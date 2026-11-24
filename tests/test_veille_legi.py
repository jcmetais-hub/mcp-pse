import io
import tarfile
import tempfile
import unittest
from pathlib import Path
from veille_legi import analyser_archive


def add(tar, name, content):
    data = content.encode('utf-8')
    entry = tarfile.TarInfo(name); entry.size = len(data)
    tar.addfile(entry, io.BytesIO(data))


class VeilleLegiTest(unittest.TestCase):
    def test_version_pse_dans_archive_reste_une_modification_ancienne(self):
        xml = '''<TEXTELR><META><META_COMMUN><ID>LEGITEXT2</ID></META_COMMUN><META_SPEC><META_TEXTE_CHRONICLE><CID>JORFTEXT000041529241</CID><NOR>MENE2003005A</NOR><DATE_TEXTE>2020-02-03</DATE_TEXTE><DERNIERE_MODIFICATION>2026-02-19</DERNIERE_MODIFICATION></META_TEXTE_CHRONICLE></META_SPEC></META><VERSIONS><VERSION etat="VIGUEUR"><LIEN_TXT debut="2026-02-19" fin="2999-01-01" id="LEGITEXT2"/></VERSION></VERSIONS></TEXTELR>'''
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'LEGI_20261120-222218.tar.gz'
            with tarfile.open(path,'w:gz') as tar:
                add(tar,'x/jorf/JORFTEXT000041529241/texte/struct/a.xml',xml)
                add(tar,'x/liste_suppression_legi.dat','')
            result=analyser_archive(path)
            self.assertEqual(len(result['versions']),1)
            self.assertEqual(result['versions'][0]['derniere_modification'],'2026-02-19')
            self.assertEqual(result['versions'][0]['versions'][0]['debut'],'2026-02-19')
            self.assertFalse(result['couverture_complete'])

    def test_corruption_refusee_sans_fausse_confirmation(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'invalid.tar.gz'; path.write_bytes(b'pas une archive')
            with self.assertRaises(ValueError): analyser_archive(path)

    def test_xml_invalide_signale_incomplet(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'LEGI_20261120-222218.tar.gz'
            with tarfile.open(path,'w:gz') as tar:
                add(tar,'x/JORFTEXT000041529241/texte/struct/a.xml','<cassé')
            result=analyser_archive(path)
            self.assertTrue(result['erreurs'])
            self.assertEqual(result['versions'],[])
            self.assertFalse(result['couverture_complete'])

    def test_version_identifie_arrete_modificatif(self):
        xml = '''<TEXTE_VERSION><META><META_COMMUN><ID>LEGITEXT2</ID></META_COMMUN><META_SPEC><META_TEXTE_CHRONICLE><CID>JORFTEXT000041529241</CID><NOR>MENE2003005A</NOR></META_TEXTE_CHRONICLE><META_TEXTE_VERSION><TITREFULL>Un titre</TITREFULL><ETAT>VIGUEUR</ETAT><DATE_DEBUT>2026-02-19</DATE_DEBUT><LIENS><LIEN typelien="MODIFIE" sens="cible" nortexte="MENE2602913A" num="13">Arrêté</LIEN><LIEN typelien="CITATION" sens="source" nortexte="" /></LIENS></META_TEXTE_VERSION></META_SPEC></META></TEXTE_VERSION>'''
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'LEGI_20261120-222218.tar.gz'
            with tarfile.open(path,'w:gz') as tar:
                add(tar,'x/JORFTEXT000041529241/texte/version/LEGITEXT2.xml',xml)
            result=analyser_archive(path)
            version=result['details_versions'][0]
            self.assertEqual(version['id'], 'LEGITEXT2')
            self.assertEqual(version['modifications'][0]['nor'], 'MENE2602913A')
            self.assertEqual(version['modifications'][0]['article'], '13')
            self.assertEqual(len(version['modifications']), 1)

    def test_liste_de_suppression_non_interpretee_signalee(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'LEGI_20261120-222218.tar.gz'
            with tarfile.open(path,'w:gz') as tar:
                add(tar,'x/liste_suppression_legi.dat','LEGIARTI000000000001\n')
            result=analyser_archive(path)
            self.assertTrue(result['suppressions_a_verifier'])
            self.assertFalse(result['couverture_complete'])
