# MCP PSE

Serveur MCP en lecture seule pour retrouver les **références officielles** des programmes de prévention-santé-environnement et rechercher dans quatre PDF locaux : CAP, seconde, première et terminale professionnelles.

## Fonction disponible

`rechercher_programmes` interroge l’API publique de data.education.gouv.fr, sans clé API. Le paramètre `niveau` accepte `tous`, `cap-1`, `cap-2`, `seconde`, `premiere` ou `terminale`. Les références ayant une année d’abrogation renseignée sont exclues par défaut ; `inclure_archives=true` les inclut.

`rechercher_contenu_programme` cherche une expression dans les PDF locaux : `niveau` accepte `cap`, `seconde`, `premiere` ou `terminale`, et `recherche` contient le terme recherché. Il renvoie les pages PDF et leur texte extrait, ainsi qu'un lien source. La recherche textuelle est sensible à la formulation : si elle ne trouve rien, essayer un autre terme. Le numéro renvoyé est le numéro de page du PDF, pas forcément le numéro imprimé.

`verifier_mises_a_jour` compare, à la demande, l’intitulé de l’arrêté présent dans l’index ministériel à la référence de base du niveau (`cap-1`, `cap-2`, `seconde`, `premiere`, `terminale`). Il indique la date UTC et signale une référence différente ou une vérification incomplète. Il ne surveille pas automatiquement, ne compare pas les textes consolidés ni les PDF, et ne télécharge ni ne remplace aucun fichier. Même sans changement détecté, une modification de l’arrêté ou du programme peut échapper au contrôle ; l’index peut être incomplet ou obsolète. Une vérification humaine des sources officielles reste indispensable.

**Attention :** la recherche de références est un index, pas une garantie d’actualité. La recherche de contenu utilise des copies statiques, sans contrôle automatique des mises à jour, et l'extraction peut déformer les tableaux. Vérifier la version applicable et l'extrait dans le PDF ou au Bulletin officiel. Certaines métadonnées du jeu indiquent une couverture historique limitée ; un champ d’abrogation vide ne prouve pas l’absence de changements. Ce serveur ne génère pas lui-même de cours, ne parcourt pas les pages Éduscol et ne remplace pas la validation du professeur.

Source : https://data.education.gouv.fr/explore/dataset/fr-en-programmes-enseignement-2nd-degre/

Les PDF sous `documents/` proviennent des annexes officielles : CAP et seconde, BO spécial n° 5 du 11 avril 2019 ; première et terminale, BO spécial n° 1 du 6 février 2020. Les copies sont à actualiser après vérification des sources officielles. Pour un exemple d’utilisation pédagogique, voir `docs/consignes-assistant.md`.

## Installation

Prérequis : Python 3.10 ou supérieur compatible avec le SDK MCP 2.x, `curl` et accès réseau à l’API officielle. Installer les dépendances dans un environnement virtuel :

```bash
python -m venv .venv
# macOS/Linux
. .venv/bin/activate
python -m pip install -r requirements.txt
python pse_mcp.py
```

Le serveur utilise le transport MCP **stdio** ; la commande attend des messages d’un client MCP et ne présente pas d’interface interactive. Configurez votre client pour lancer le Python de l’environnement virtuel avec le chemin absolu de `pse_mcp.py`. Le processus a accès au réseau, mais n’a besoin d’aucune clé API.

## Analyse expérimentale d'une archive LEGI

`python veille_legi.py chemin/LEGI_AAAAMMJJ-HHMMSS.tar.gz` inspecte, sans extraction sur disque, les fichiers XML de structure des arrêtés CAP, seconde et première/terminale dans une archive locale. Les dates et identifiants sont ceux publiés dans les XML ; une ancienne version peut être réémise dans une archive récente. Les suppressions non vides et les erreurs sont signalées. La provenance du fichier local n'est pas certifiée : obtenir l'archive depuis https://echanges.dila.gouv.fr/OPENDATA/LEGI/ et noter son URL et sa date.

`python veille_legi.py --comparer avant.tar.gz apres.tar.gz` compare les métadonnées des versions présentes dans deux archives locales. La réémission d'une version identique ne constitue pas automatiquement une nouveauté ; une absence, des versions ambiguës ou des métadonnées incomplètes sont signalées comme vérification incomplète. Comme un incrément contient uniquement des modifications, l’absence d’un texte ne permet pas de le considérer inchangé. Les listes de suppression non traitées restent signalées pour vérification.

`python suivi_catalogue_legi.py catalogue.html` lit un index HTML DILA préalablement téléchargé et liste tous les stocks et incréments, y compris plusieurs le même jour. Avec `--avant ancien.html`, il signale les archives apparues ou disparues entre les deux catalogues. Il ne surveille pas automatiquement et ne vérifie ni les contenus ni les empreintes ; une archive absente un jour donné n'est pas forcément une lacune. Un catalogue sans disparition ne prouve pas la continuité.

`python suivi_journal_legi.py catalogue.html dossier_archives journal.json` produit un journal local expérimental des incréments listés dans un catalogue HTML préalablement récupéré et déjà présents dans le dossier. Il calcule une empreinte locale, contrôle la lecture gzip et l’analyse des archives, signale les suppressions à vérifier et refuse d'avancer en cas de fichier absent, modifié, illisible, disparu du catalogue ou apparu hors ordre. L’écriture du fichier final est atomique ; ne pas lancer deux instances simultanées. La première exécution nécessite toutes les archives incrémentales listées. Une empreinte locale ne prouve pas la provenance de l'archive. Le journal ne contient pas un état consolidé : aucun stock n'est intégré et les suppressions ne sont pas appliquées ; il n'est pas relié à la veille planifiée.

Ceci est un outil d'inspection ponctuelle, **pas une surveillance complète ni un remplacement des textes consolidés** : il ne télécharge pas le stock et les incréments, ne vérifie pas la continuité, ne reconstitue pas les suppressions, ne compare pas les annexes et ne détecte pas nécessairement une modification publiée uniquement ailleurs. Il n'est pas encore branché à la veille planifiée. Une archive sans résultat ne signifie pas l'absence de changement.

## Tests

```bash
python -m unittest discover -s tests -v
```

Le test d’intégration lance un vrai client et serveur MCP et effectue une requête réelle au portail : il nécessite le réseau. Les résultats du portail peuvent évoluer.

## Confidentialité et sécurité

Aucun compte élève ni donnée personnelle n’est nécessaire. Ne jamais enregistrer de clé API ou de mot de passe dans le dépôt. L’API publique reçoit les requêtes de programme et peut consigner des informations techniques telles que l’adresse IP.
