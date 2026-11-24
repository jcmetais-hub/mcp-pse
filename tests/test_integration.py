import asyncio
import json
import sys
import unittest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class ProtocolTest(unittest.TestCase):
    def test_decouverte_et_requete_en_conditions_reelles(self):
        async def run():
            params = StdioServerParameters(command=sys.executable, args=['pse_mcp.py'])
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    self.assertIn('rechercher_programmes', [x.name for x in tools.tools])
                    response = await session.call_tool('rechercher_programmes', {'niveau': 'seconde'})
                    self.assertFalse(response.is_error)
                    text = ' '.join(getattr(x, 'text', '') for x in response.content)
                    self.assertIn('Seconde professionnelle', text)
                    self.assertIn('vérifier', text.lower())
                    self.assertIn('verifier_mises_a_jour', [x.name for x in tools.tools])
                    verification = await session.call_tool('verifier_mises_a_jour', {'niveau': 'premiere'})
                    self.assertFalse(verification.is_error)
                    bilan = json.loads(verification.content[0].text)
                    self.assertIn(bilan['statut'], ['aucun_changement_detecte_dans_index', 'changement_detecte'])
                    self.assertIn('ne garantit pas', bilan['avertissement'])
                    self.assertIn('rechercher_contenu_programme', [x.name for x in tools.tools])
                    for niveau, recherche in [('cap', 'bruit'), ('seconde', 'sommeil'), ('premiere', 'bruit'), ('terminale', 'physique')]:
                        with self.subTest(niveau=niveau):
                            result = await session.call_tool('rechercher_contenu_programme', {'niveau': niveau, 'recherche': recherche})
                            self.assertFalse(result.is_error)
                            body = json.loads(result.content[0].text)
                            self.assertGreater(body['nombre_pages_trouvees'], 0)
                            self.assertGreater(body['extraits'][0]['page_pdf'], 0)
        asyncio.run(run())


if __name__ == '__main__':
    unittest.main()
