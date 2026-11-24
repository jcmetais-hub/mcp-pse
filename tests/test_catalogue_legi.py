import unittest
from suivi_catalogue_legi import lire_catalogue, comparer_catalogues

INDEX='''<html><title>Index of /OPENDATA/LEGI</title><pre>
<a href="Freemium_legi_global_20261108-140000.tar.gz">global</a>
<a href="LEGI_20261116-104909.tar.gz">a</a>
<a href="LEGI_20261116-212357.tar.gz">b</a>
</pre></html>'''

class CatalogueTest(unittest.TestCase):
    def test_deux_archives_meme_jour_conservees_et_triees(self):
        c=lire_catalogue(INDEX)
        self.assertEqual(c['increments'], ['LEGI_20261116-104909.tar.gz','LEGI_20261116-212357.tar.gz'])
        self.assertEqual(c['stocks'], ['Freemium_legi_global_20261108-140000.tar.gz'])
        self.assertFalse(c['continuite_garantie'])

    def test_page_blocage_refusee(self):
        with self.assertRaises(ValueError): lire_catalogue('<title>Access denied</title>')

    def test_lien_non_dila_refuse(self):
        result=lire_catalogue(INDEX.replace('LEGI_20261116-104909.tar.gz','https://exemple.fr/LEGI_20261116-104909.tar.gz'))
        self.assertEqual(len(result['increments']),1)

    def test_disparition_d_archive_est_un_signal(self):
        old=lire_catalogue(INDEX)
        new=lire_catalogue(INDEX.replace('<a href="LEGI_20261116-104909.tar.gz">a</a>',''))
        diff=comparer_catalogues(old,new)
        self.assertEqual(diff['disparues'], ['LEGI_20261116-104909.tar.gz'])
        self.assertFalse(diff['continuite_garantie'])

    def test_jour_absent_ne_prouve_pas_une_lacune(self):
        c=lire_catalogue(INDEX)
        diff=comparer_catalogues(c,c)
        self.assertEqual(diff['disparues'],[])
        self.assertFalse(diff['continuite_garantie'])

    def test_refuse_doublons(self):
        with self.assertRaises(ValueError): lire_catalogue(INDEX.replace('</pre>','<a href="LEGI_20261116-104909.tar.gz">a</a></pre>'))
