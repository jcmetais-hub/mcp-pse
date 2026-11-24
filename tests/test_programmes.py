import unittest
from unittest.mock import patch

from pse_mcp import rechercher_programmes


class ProgrammesTest(unittest.TestCase):
    @patch('pse_mcp.fetch_records')
    def test_retourne_references_filtrees_et_signale_verification(self, fetch):
        fetch.return_value = {'total_count': 1, 'results': [{'niveau_d_enseignement': 'Seconde professionnelle', 'abroge_a_la_rentree': '-'}]}
        result = rechercher_programmes('seconde', inclure_archives=False)
        self.assertEqual(result['references'][0]['niveau_d_enseignement'], 'Seconde professionnelle')
        self.assertIn('vérifier', result['avertissement'].lower())
        self.assertFalse(result['inclut_archives'])
        self.assertIn('abroge_a_la_rentree', fetch.call_args.kwargs['where'])


    @patch('pse_mcp.fetch_records')
    def test_signale_resultats_tronques(self, fetch):
        fetch.return_value = {'total_count': 101, 'results': [{'descriptif': 'Exemple'}]}
        self.assertTrue(rechercher_programmes()['tronque'])

    def test_niveau_invalide(self):
        with self.assertRaises(ValueError):
            rechercher_programmes('niveau inconnu')

    @patch('pse_mcp.subprocess.run')
    def test_erreur_reseau_masquee(self, run):
        import subprocess
        run.side_effect = subprocess.TimeoutExpired('curl', 25)
        from pse_mcp import fetch_records
        with self.assertRaisesRegex(RuntimeError, 'Impossible de consulter'):
            fetch_records(where='x')


if __name__ == '__main__':
    unittest.main()
