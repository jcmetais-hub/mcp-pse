import unittest
from pse_mcp import rechercher_contenu_programme


class ContenuTest(unittest.TestCase):
    def test_retrouve_bruit_en_cap_avec_reference_et_page(self):
        result = rechercher_contenu_programme('cap', 'bruit')
        self.assertTrue(result['extraits'])
        self.assertTrue(all(e['page_pdf'] > 0 for e in result['extraits']))
        self.assertIn('education', result['source'])
        self.assertIn('vérifier', result['avertissement'].lower())

    def test_refuse_recherche_trop_courte(self):
        with self.assertRaises(ValueError):
            rechercher_contenu_programme('cap', 'ab')

    def test_refuse_recherche_composee_seulement_d_accents(self):
        with self.assertRaises(ValueError):
            rechercher_contenu_programme('cap', '\u0301\u0301\u0301')

    def test_refuse_niveau_inconnu(self):
        with self.assertRaises(ValueError):
            rechercher_contenu_programme('invalid', 'bruit')


if __name__ == '__main__':
    unittest.main()
