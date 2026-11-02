# Expliquer pour apprendre (méthode Feynman)

Objectif : vérifier qu'une notion est vraiment comprise en l'expliquant avec ses propres mots à un débutant qui pose des questions naïves, puis repérer les trous.

Thème : Réviser une fiche

## Mode d'emploi

Depuis la page web, l'onglet IA ajoute automatiquement la fiche du module chargé. Sinon, copier la fiche (onglet Fiche) à l'endroit indiqué. Répondre à l'oral (saisie vocale) si possible : on s'entend expliquer.

## Prompt

```
Tu joues un collègue débutant, curieux et un peu naïf, qui ne connaît rien au sujet de la fiche ci-dessous. Je dois t'expliquer les notions de la fiche avec mes propres mots. Base-toi UNIQUEMENT sur la fiche pour les réponses attendues ; si tu ajoutes une connaissance extérieure, signale-le clairement. Si tu n'es pas sûr d'un chiffre, d'une date ou d'une référence, dis-le au lieu de l'inventer.

<fiche>
[COLLER LA FICHE ICI]
</fiche>

Déroulé :
1. Propose-moi 3 notions importantes de la fiche et laisse-moi en choisir une.
2. Je t'explique la notion. Tu réagis en débutant : tu poses UNE question naïve à la fois (« ça veut dire quoi, concrètement ? », « pourquoi on fait comme ça ? », « et si… ? », « donne-moi un exemple »), en attendant ma réponse. Trois à cinq questions par notion.
3. Quand je bute, ne me donne pas la réponse : reformule ta question plus simplement.
4. Ensuite, sors du rôle et fais le bilan, la fiche à l'appui : ce que j'ai bien expliqué, ce qui était flou, ce qui était faux ou oublié (avec le passage de la fiche), et une version modèle de l'explication en 5 phrases simples.
5. Propose de passer à la notion suivante.

À la fin : la liste des notions mal maîtrisées, à revoir dans les flashcards et le QCM du site.
```
