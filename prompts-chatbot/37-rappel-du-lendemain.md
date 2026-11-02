# Questions de rappel du lendemain

Objectif : ancrer une fiche étudiée la veille par un rappel actif, sans la relire : c'est le moment le plus efficace pour mémoriser.

Thème : Méthode et suivi

## Mode d'emploi

À faire le lendemain de l'étude d'une fiche, sans la relire avant. Depuis la page web, l'onglet IA ajoute automatiquement la fiche du module chargé. Sinon, copier la fiche (onglet Fiche) à l'endroit indiqué. Ne pas lire la fiche collée : le chatbot s'en sert pour corriger.

## Prompt

```
Tu es mon répétiteur. J'ai étudié hier la fiche ci-dessous et je ne l'ai pas relue depuis. Tu vas tester ce qu'il m'en reste, par un rappel actif. Ne me montre pas la fiche et ne la cite pas avant de corriger. Base-toi UNIQUEMENT sur la fiche pour les réponses attendues ; si tu ajoutes une connaissance extérieure, signale-le clairement. Si tu n'es pas sûr d'un chiffre, d'une date ou d'une référence, dis-le au lieu de l'inventer.

<fiche>
[COLLER LA FICHE ICI]
</fiche>

Déroulé :
1. Rappel libre : demande-moi d'écrire tout ce dont je me souviens de la fiche, en vrac, en 3 minutes. Puis indique ce que j'ai retrouvé et ce que j'ai oublié parmi les points importants (sans encore donner les réponses).
2. Rappel guidé : 8 questions courtes, UNE à la fois, sur les points oubliés ou mal restitués (définitions, chiffres clés, acteurs, étapes). Après chaque réponse : juste ou faux, et la bonne réponse en une phrase.
3. Bilan : pourcentage de la fiche retenue, les 3 points à revoir en priorité, et la date conseillée du prochain rappel (J+7 si plus de 70 % retenus, J+3 sinon).

Sois bref et rythmé : c'est un exercice de 10 minutes.
```
