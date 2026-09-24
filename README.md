# pse-securite-nationale

Révision des publications de l'ANSSI, du SGDSN, de Viginum et du COMCYBER-MI, et des stratégies nationales (cybersécurité, IA, manipulations de l'information).

56 modules, consultables depuis l'application de révision
https://guiraudjb.github.io/PSE25-27/ (ce dépôt en fournit les données via GitHub Pages).

## Séries

- **03** : ANSSI, SGDSN et stratégies nationales

## Organisation : un seul dossier pour le jeu et la page web

Tout est dans `batocera/pse-securite-nationale/`, le dossier du jeu Batocera, copié tel quel
sur la console. La page web lit les **mêmes** fichiers (via GitHub Pages).

- `batocera/pse-securite-nationale/data/` : `modules.json` (liste des modules) et, pour chaque
  module `<nom>` : `fiche/<nom>.txt`, `quizz/<nom>.csv`, `flashcard/<nom>.csv`,
  éventuellement `tp/<nom>.csv`, `icone/<nom>.png`, et les médias
  `podcast/<nom>.mp3`, `infographie/<nom>.png`, `chanson/<nom>.mp3` (+ paroles
  `.txt`), `fiche_audio/<nom>.mp3` (narration de la fiche).
- `batocera/pse-securite-nationale/tts_assets/cache/<module>/` : audio des QCM (`quiz_N_ask`,
  `quiz_N_feedback_correct|incorrect`) et des flashcards (`flash_N_recto|verso`),
  joué par le jeu ET par la page web.
- `batocera/pse-securite-nationale/*.py`, `pse-securite-nationale.pygame`, `jeu.json`, `assets/` : le jeu.

## Outils (`batocera/`)

- `deploy.py` : copie le dossier du jeu sur la Batocera (SMB).
- `generate_tts_voicestudio.py` / `generate_fiche_audio_voicestudio.py` :
  génèrent l'audio (VoiceStudio local) directement dans le dossier du jeu.

Le moteur du jeu est commun à tous les dépôts : il se modifie dans le modèle
de l'espace de travail puis se synchronise, jamais ici.
