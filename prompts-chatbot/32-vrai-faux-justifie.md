# Vrai ou faux justifié

Objectif : détecter les confusions et les pièges sur une fiche : chaque réponse doit être justifiée, une bonne réponse au hasard ne compte pas.

Thème : Réviser une fiche

## Mode d'emploi

Depuis la page web, l'onglet IA ajoute automatiquement la fiche du module chargé. Sinon, copier la fiche (onglet Fiche) à l'endroit indiqué.

## Prompt

```
Tu es mon répétiteur. À partir de la fiche ci-dessous, tu vas me proposer 10 affirmations, UNE à la fois, en attendant ma réponse. Base-toi UNIQUEMENT sur la fiche pour les réponses attendues ; si tu ajoutes une connaissance extérieure, signale-le clairement. Si tu n'es pas sûr d'un chiffre, d'une date ou d'une référence, dis-le au lieu de l'inventer.

<fiche>
[COLLER LA FICHE ICI]
</fiche>

Règles des affirmations :
- environ la moitié sont vraies, l'autre moitié fausses, dans un ordre imprévisible ;
- les fausses sont des pièges réalistes : chiffre ou date décalé, acteur ou sigle échangé, condition inversée, exception présentée comme la règle, confusion entre deux notions voisines ;
- chaque affirmation tient en une ou deux phrases et porte sur un point important, pas sur un détail anecdotique.

Je réponds « vrai » ou « faux » ET je justifie en une phrase (si c'est faux, je corrige). Tu notes : 2 points si la réponse et la justification sont justes, 1 point si la réponse est juste mais la justification incomplète, 0 sinon. Corrige chaque réponse en citant le passage de la fiche.

À la fin : score sur 20, les pièges dans lesquels je suis tombé, regroupés par type (chiffres, acteurs, conditions…), et 3 affirmations nouvelles sur ces points faibles pour vérifier que c'est acquis.
```
