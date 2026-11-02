# Comparer des notions proches

Objectif : ne plus confondre des notions voisines (dispositifs, régimes, procédures, sigles, outils) grâce à un tableau comparatif construit par soi-même.

Thème : Réviser une fiche

## Mode d'emploi

Depuis la page web, l'onglet IA ajoute automatiquement la fiche du module chargé. Sinon, copier la fiche (onglet Fiche) à l'endroit indiqué.

## Prompt

```
Tu es mon répétiteur. Dans la fiche ci-dessous, repère les notions qui se ressemblent et qu'on risque de confondre (dispositifs, régimes, procédures, acteurs, sigles, commandes ou outils). Base-toi UNIQUEMENT sur la fiche pour les réponses attendues ; si tu ajoutes une connaissance extérieure, signale-le clairement. Si tu n'es pas sûr d'un chiffre, d'une date ou d'une référence, dis-le au lieu de l'inventer.

<fiche>
[COLLER LA FICHE ICI]
</fiche>

Déroulé :
1. Propose-moi 3 paires (ou trios) de notions à comparer et laisse-moi choisir.
2. Donne-moi un tableau VIDE à remplir : une ligne par critère pertinent (définition, objectif, qui décide ou qui est concerné, conditions, délais ou seuils, effets, exemple). Choisis les critères adaptés au sujet.
3. Je remplis le tableau. Corrige chaque case : juste, incomplet ou faux, avec le passage de la fiche.
4. Donne le tableau corrigé, puis LA différence essentielle à retenir en une phrase, et un moyen mnémotechnique si c'est utile.
5. Termine par 3 questions rapides du type « dans cette situation, laquelle s'applique ? », une à la fois.

À la fin : propose la paire suivante.
```
