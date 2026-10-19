# PSE25-27 Révision

Jeu de révision (Quiz + Flashcards) pour réviser les modules PSE 25-27 / PSE Expert Réseau
et les autres fascicules du dépôt, jouable entièrement à la manette sur Batocera.

## Contenu

165+ modules répartis en 9 séries thématiques (cybersécurité, numérique de l'État,
Bercy/finances publiques, PSE 25-27, PSE Expert Réseau...), chacun avec :

- un mode **Quiz** : QCM chronométré, 15 questions tirées aléatoirement parmi celles du module
- un mode **Flashcards** : cartes recto/verso navigables, à retourner pour vérifier la réponse
- **Synthèse vocale française** (bouton R1) sur les questions/choix/explications du quiz et
  sur chaque face des flashcards, voir la section dédiée ci-dessous

## Contrôles manette

- D-pad / stick analogique / Select-Start : naviguer dans les menus et les listes
- **A** : valider / retourner une flashcard
- **B** : retour à l'écran précédent
- Gauche/Droite : carte précédente/suivante (en mode Flashcards)
- En quiz : **A/B/C/D** (esprit manette NeoGeo) répondent directement au choix correspondant ; **L1** abandonne la question
- **R1** : lire à voix haute (flashcard affichée, ou question + choix en quiz/explication en feedback)
- Podcast en lecture : **L1** (ou R1) passe à l'autre version du podcast (pipeline local / NotebookLM) ;
  **R2** passe à l'autre version de l'infographie affichée en fond, sans couper la lecture
- Infographie : **L1/R1/R2** passent à l'autre version (pipeline local / NotebookLM)
- Jukebox podcast : **L1** autre version du podcast (la piste repart du début), **R2** autre version de
  l'infographie de fond ; le choix est gardé pour les pistes suivantes (repli sur l'autre version si absente) ;
  **R1** active/désactive l'aléatoire. Jukebox musique et micro-chroniques : **L1/R1** aléatoire, **R2** infographie
- L2/R2 sont lus en bouton (manette DragonRise) ou en gâchette analogique (manettes Xbox, axes 2 et 5
  d'après es_input.cfg)

## Synthèse vocale (R1)

Voix française neuronale locale ([Piper](https://github.com/rhasspy/piper), voix
`fr_FR-siwis-medium`), embarquée dans `tts_assets/` (binaire + modèle, ~112 Mo, aucune
dépendance réseau). Mesuré sur le CPU de la machine Batocera cible : la synthèse est
~1,5× plus lente que le temps réel (une phrase de 20 mots prend environ 10 à 15
secondes à générer, contre une fraction de seconde sur une machine de développement
plus puissante). Une lecture à la volée bloquerait donc le jeu de façon inacceptable.

Solution retenue : chaque contenu (recto/verso d'une carte, question+choix d'un quiz,
explication) est synthétisé **une seule fois**, dans un thread d'arrière-plan, et mis en
cache sous forme de fichier `.wav` dans `tts_assets/cache/` (persistant sur le disque de
la machine). Un badge « VOIX : préparation… » puis « VOIX : lecture… » s'affiche en
haut à droite de l'écran pendant ce délai. Toute lecture suivante du même contenu est
instantanée. Le cache se remplit donc progressivement à l'usage ; il peut être vidé
(dossier `tts_assets/cache/`) sans risque, il se regénère à la demande.

## Origine des données

Les fichiers `data/quizz/*.csv` et `data/flashcard/*.csv` proviennent du dépôt de révision
PSE25-27 (généré à partir des fascicules officiels du parcours). `data/modules.json` liste
les modules disponibles par série.

## Licence

Code du jeu : usage personnel. Police intégrée : DejaVu Sans (licence Bitstream Vera /
DejaVu, libre de redistribution).

## Mini-jeu bonus

Proposé à la fin d'un QCM réussi à **plus de 80 %**, une seule fois par QCM.
Une session dure de 5 à 10 minutes : une partie perdue avant 5 min peut être rejouée,
et le jeu s'arrête de lui-même à 10 min. La pause (Start ou Select) arrête le chronomètre.
Les records sont gardés dans `preferences.json`.

Dix jeux, choisis à la croix dans une grille de deux colonnes :

- **Tetromino** / **Pentomino** (pièces de 5 cases) : ◄► déplacer, ▼ descendre, A ou ▲ tourner, B tourner dans l'autre sens, C (ou D/R1) faire tomber.
- **Wormy** : la croix dirige le ver.
- **Gemgem** : la croix déplace le curseur, A sélectionne une gemme, puis une direction l'échange avec sa voisine (alignez-en 3).
- **Simulate** : répéter la séquence de couleurs avec A, B, C, D (4 s maximum entre deux appuis).
- **Memory Puzzle** : la croix choisit une case, A la retourne. Les paires sont les icônes des modules du dépôt (jusqu'à 35 paires, grille réduite s'il y en a moins) ; le module de chaque paire trouvée s'affiche sous la grille.
- **Slide Puzzle** : taquin 4×4, la croix fait glisser une tuile vers le trou.
- **Ink Spill** : ◄► choisir une couleur, A la verser depuis le coin ; remplir la grille en 30 coups.
- **Four in a Row** : puissance 4 contre l'ordinateur, ◄► colonne, A ou ▼ jouer.
- **Flippy** : Othello contre l'ordinateur, la croix choisit la case, A pose (les coups possibles sont marqués d'un point).

Entre deux manches (taquin résolu, partie de puissance 4 finie…), A passe à la suivante.
Ces jeux sont adaptés d'Al Sweigart (« Making Games with Python & Pygame »,
licence BSD simplifiée, texte dans `minijeux.py`). Les images et sons d'origine ne sont pas repris.
