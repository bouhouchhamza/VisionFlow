# Instructions permanentes

Documentation détaillée : `docs/`. Lire `docs/DECISIONS.md` avant toute proposition technique.

- Statuts à respecter : Confirmé / Proposition / Hypothèse / Ouvert. Une proposition n'est pas une décision.
- Dater un événement observé par le temps de la vidéo (PTS, ms), jamais par l'horloge système.
- Ne jamais modifier une observation brute ; les corrections humaines s'ajoutent ; les indicateurs se recalculent.
- Toute observation, preuve et correction porte un `run_id` ; ne jamais mélanger deux runs d'une même vidéo.
- Marquer toute donnée synthétique à la source ; ne jamais présenter une simulation comme une validation réelle.
- Une observation vidéo ne prouve ni vente, ni paiement, ni fraude : écrire « écart à examiner ».
- Ne jamais affirmer une commande exécutée, un test réussi ou une performance sans l'avoir réellement obtenu.
- Aucune dépendance ajoutée sans décision consignée dans `docs/DECISIONS.md`.
- Vidéos et données hors de git. Git uniquement dans ce dossier : jamais le dépôt de `C:\`, jamais d'ajout global, jamais de push sans demande.
- Ne jamais régler un paramètre sur un extrait de réserve (`experiments/E0/INVENTAIRE.md`).
- Prototype : `.\.venv\Scripts\python -m passages …` et `python -m pytest -q tests` (commandes : `experiments/E2/RESULTATS_S1.md`).
