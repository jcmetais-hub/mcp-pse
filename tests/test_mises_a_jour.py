import unittest
from unittest.mock import patch
import pse_mcp


class MiseAJourTest(unittest.TestCase):
    @patch('pse_mcp.fetch_records')
    def test_signale_une_modification_de_reference(self, fetch):
        fetch.return_value = {'total_count': 1, 'results': [{'niveau_d_enseignement': 'Première année de CAP', 'texte_officiel': 'Nouvel arrêté', 'abroge_a_la_rentree': '-'}]}
        result = pse_mcp.verifier_mises_a_jour('cap-1')
        self.assertEqual(result['statut'], 'changement_detecte')
        self.assertIn('Nouvel arrêté', str(result['references_observees']))
        self.assertIn('ne garantit pas', result['avertissement'])

    @patch('pse_mcp.fetch_records')
    def test_absence_de_donnee_ne_signifie_pas_a_jour(self, fetch):
        fetch.return_value = {'total_count': 0, 'results': []}
        self.assertEqual(pse_mcp.verifier_mises_a_jour('cap-1')['statut'], 'verification_incomplete')

    @patch('pse_mcp.fetch_records')
    def test_reference_identique_ne_garantit_pas_la_validite(self, fetch):
        fetch.return_value = {'total_count': 1, 'results': [{'niveau_d_enseignement': 'Première année de CAP', 'texte_officiel': 'arrêté du 3-4-2019 - J.O. du 9-4-2019', 'abroge_a_la_rentree': '-'}]}
        result = pse_mcp.verifier_mises_a_jour('cap-1')
        self.assertEqual(result['statut'], 'aucun_changement_detecte_dans_index')
        self.assertIn('ne garantit pas', result['avertissement'])

    @patch('pse_mcp.fetch_records')
    def test_reponse_tronquee_incomplete(self, fetch):
        fetch.return_value = {'total_count': 2, 'results': [{'niveau_d_enseignement': 'Première année de CAP', 'texte_officiel': 'arrêté du 3-4-2019 - J.O. du 9-4-2019', 'abroge_a_la_rentree': '-'}]}
        self.assertEqual(pse_mcp.verifier_mises_a_jour('cap-1')['statut'], 'verification_incomplete')

    @patch('pse_mcp.fetch_records')
    def test_reseau_indisponible_signale(self, fetch):
        fetch.side_effect = RuntimeError('indisponible')
        self.assertEqual(pse_mcp.verifier_mises_a_jour('cap-1')['statut'], 'verification_incomplete')

    def test_refuse_niveau_inconnu(self):
        with self.assertRaises(ValueError):
            pse_mcp.verifier_mises_a_jour('inconnu')


if __name__ == '__main__':
    unittest.main()
