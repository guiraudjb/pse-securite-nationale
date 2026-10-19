# Mini-jeux bonus (récompense d'un QCM réussi à plus de 80 %).
#
# Tetromino, Pentomino, Wormy, Simulate, Memory Puzzle, Slide Puzzle, Ink Spill,
# Gemgem, Four in a Row et Flippy sont adaptés des jeux d'Al Sweigart (« Making Games with
# Python & Pygame », https://inventwithpython.com/pygame), publiés sous licence
# BSD simplifiée :
#
#   Copyright (c) Al Sweigart, al@inventwithpython.com
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions are met:
#   1. Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#   2. Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#   AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#   IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
#   ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
#   LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#   CONSEQUENTIAL DAMAGES ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE.
#
# Adaptation : logique reprise, rendu redessiné (aucune image ni son d'origine),
# commandes à la manette, session de 5 à 10 minutes (voir Session).
import math
import random
import pygame

SESSION_MIN_S = 5 * 60    # en dessous, une partie perdue est relancée
SESSION_MAX_S = 10 * 60   # au-delà, la session s'arrête d'elle-même

FOND_JEU = (16, 18, 40)
GRILLE = (34, 38, 70)
BLANC = (255, 255, 255)
GRIS = (170, 175, 200)
JAUNE = (255, 210, 60)


def _assombrir(c, f=0.6):
    return tuple(int(v * f) for v in c)


def _case(surface, couleur, rect):
    pygame.draw.rect(surface, _assombrir(couleur), rect)
    pygame.draw.rect(surface, couleur, rect.inflate(-4, -4))


def _grille(zone, cols, rows, panneau=6):
    """Taille de case et origine d'un plateau cols×rows centré dans zone,
    en gardant `panneau` cases libres à droite pour les scores."""
    case = min(zone.width // (cols + panneau + 1), zone.height // rows)
    ox = zone.x + (zone.width - case * (cols + panneau)) // 2
    oy = zone.y + (zone.height - case * rows) // 2
    return case, ox, oy


def _fond_plateau(surface, ox, oy, case, cols, rows, lignes=True):
    cadre = pygame.Rect(ox, oy, case * cols, case * rows)
    pygame.draw.rect(surface, FOND_JEU, cadre)
    if lignes:
        for x in range(1, cols):
            pygame.draw.line(surface, GRILLE, (ox + x * case, oy), (ox + x * case, cadre.bottom - 1))
        for y in range(1, rows):
            pygame.draw.line(surface, GRILLE, (ox, oy + y * case), (cadre.right - 1, oy + y * case))
    return cadre


def _panneau(cadre, case, zone):
    px = cadre.right + case
    return pygame.Rect(px, cadre.y, zone.right - px, zone.bottom - cadre.y)


def _curseur(surface, rect, t=None):
    pygame.draw.rect(surface, JAUNE, rect.inflate(2, 2), 4, border_radius=6)


DIRS = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}


class Jeu:
    """Interface commune : action(a), update(dt), draw(surface, zone, fonts)
    -> rectangle libre pour le panneau de scores, infos(), score, over.
    `annonce` = (titre, sous-titre) affiché par-dessus le jeu entre deux
    manches ; A passe à la manche suivante (voir continuer())."""
    titre = ''
    aide_jeu = []
    over = False
    score = 0
    annonce = None
    tenu = (0, 0, frozenset())   # (dx, dy, boutons) maintenus, fourni par la session

    @property
    def aide(self):
        if self.annonce:
            return [('A', 'Continuer'), ('Start', 'Pause')]
        return self.aide_jeu

    def update(self, dt):
        pass

    def infos(self):
        return [('Score', self.score)]

    def continuer(self):
        self.annonce = None

    def _deplacer(self, cur, a, larg, haut):
        dx, dy = DIRS[a]
        cur[0] = (cur[0] + dx) % larg
        cur[1] = (cur[1] + dy) % haut


# ----------------------------------------------------------------------
# TETROMINO
VIDE = '.'
T_LARG, T_HAUT = 5, 5
PIECES = {
    'S': [['.....', '.....', '..OO.', '.OO..', '.....'],
          ['.....', '..O..', '..OO.', '...O.', '.....']],
    'Z': [['.....', '.....', '.OO..', '..OO.', '.....'],
          ['.....', '..O..', '.OO..', '.O...', '.....']],
    'I': [['..O..', '..O..', '..O..', '..O..', '.....'],
          ['.....', '.....', 'OOOO.', '.....', '.....']],
    'O': [['.....', '.....', '.OO..', '.OO..', '.....']],
    'J': [['.....', '.O...', '.OOO.', '.....', '.....'],
          ['.....', '..OO.', '..O..', '..O..', '.....'],
          ['.....', '.....', '.OOO.', '...O.', '.....'],
          ['.....', '..O..', '..O..', '.OO..', '.....']],
    'L': [['.....', '...O.', '.OOO.', '.....', '.....'],
          ['.....', '..O..', '..O..', '..OO.', '.....'],
          ['.....', '.....', '.OOO.', '.O...', '.....'],
          ['.....', '.OO..', '..O..', '..O..', '.....']],
    'T': [['.....', '..O..', '.OOO.', '.....', '.....'],
          ['.....', '..O..', '..OO.', '..O..', '.....'],
          ['.....', '.....', '.OOO.', '..O..', '.....'],
          ['.....', '..O..', '.OO..', '..O..', '.....']],
}
COULEURS_PIECES = {
    'S': (40, 200, 90), 'Z': (230, 60, 60), 'I': (60, 200, 230), 'O': (240, 210, 50),
    'J': (70, 110, 240), 'L': (245, 150, 40), 'T': (180, 80, 220),
}


class Tetromino(Jeu):
    titre = 'Tetromino'
    LARG, HAUT = 10, 20
    PIECES = PIECES
    COULEURS = COULEURS_PIECES
    aide_jeu = [('◄►', 'Déplacer'), ('▼', 'Descendre'), ('A/▲', 'Tourner'), ('B', 'Tourner ↺'),
            ('C', 'Chute'), ('Start', 'Pause')]

    def __init__(self):
        self.plateau = [[VIDE] * self.HAUT for _ in range(self.LARG)]
        self.score = 0
        self.lignes = 0
        self.niveau = 1
        self.over = False
        self.piece = self._nouvelle()
        self.suivante = self._nouvelle()
        self.chrono_chute = 0.0

    # -- logique d'origine (calculateLevelAndFallFreq, isValidPosition, ...)
    def delai_chute(self):
        return max(0.05, 0.27 - self.niveau * 0.02)

    def _nouvelle(self):
        forme = random.choice(list(self.PIECES))
        return {'forme': forme, 'rot': random.randint(0, len(self.PIECES[forme]) - 1),
                'x': self.LARG // 2 - T_LARG // 2, 'y': -2}

    def _cases(self, piece):
        modele = self.PIECES[piece['forme']][piece['rot']]
        for x in range(T_LARG):
            for y in range(T_HAUT):
                if modele[y][x] != VIDE:
                    yield piece['x'] + x, piece['y'] + y

    def valide(self, piece, dx=0, dy=0):
        for x, y in self._cases(piece):
            x, y = x + dx, y + dy
            if y < 0:
                continue
            if not (0 <= x < self.LARG and y < self.HAUT):
                return False
            if self.plateau[x][y] != VIDE:
                return False
        return True

    def _poser(self):
        for x, y in self._cases(self.piece):
            if 0 <= y < self.HAUT:
                self.plateau[x][y] = self.piece['forme']
        faites = 0
        y = self.HAUT - 1
        while y >= 0:
            if all(self.plateau[x][y] != VIDE for x in range(self.LARG)):
                for yy in range(y, 0, -1):
                    for x in range(self.LARG):
                        self.plateau[x][yy] = self.plateau[x][yy - 1]
                for x in range(self.LARG):
                    self.plateau[x][0] = VIDE
                faites += 1
            else:
                y -= 1
        if faites:
            self.lignes += faites
            self.score += (0, 1, 3, 5, 8)[faites] * self.niveau
            self.niveau = self.lignes // 10 + 1
        self.piece = self.suivante
        self.suivante = self._nouvelle()
        self.chrono_chute = 0.0
        if not self.valide(self.piece):
            self.over = True

    def _descendre(self):
        if self.valide(self.piece, dy=1):
            self.piece['y'] += 1
            return True
        self._poser()
        return False

    def _tourner(self, sens):
        n = len(self.PIECES[self.piece['forme']])
        ancienne = self.piece['rot']
        self.piece['rot'] = (ancienne + sens) % n
        if self.valide(self.piece):
            return
        # petit décalage latéral si la rotation touche un bord
        for dx in (-1, 1, -2, 2):
            if self.valide(self.piece, dx=dx):
                self.piece['x'] += dx
                return
        self.piece['rot'] = ancienne

    def action(self, a):
        if self.over:
            return
        if a == 'left' and self.valide(self.piece, dx=-1):
            self.piece['x'] -= 1
        elif a == 'right' and self.valide(self.piece, dx=1):
            self.piece['x'] += 1
        elif a == 'down':
            self._descendre()
            self.chrono_chute = 0.0
        elif a in ('up', 'face_a'):
            self._tourner(1)
        elif a == 'face_b':
            self._tourner(-1)
        elif a in ('face_x', 'face_y', 'shoulder_r'):
            while self._descendre():
                pass
            self.chrono_chute = 0.0

    def update(self, dt):
        if self.over:
            return
        self.chrono_chute += dt
        if self.chrono_chute >= self.delai_chute():
            self.chrono_chute = 0.0
            self._descendre()

    def infos(self):
        return [('Score', self.score), ('Lignes', self.lignes), ('Niveau', self.niveau)]

    def draw(self, surface, zone, fonts):
        case = min(zone.width // (self.LARG + 7), zone.height // self.HAUT)
        larg, haut = case * self.LARG, case * self.HAUT
        ox = zone.x + (zone.width - larg - 6 * case) // 2
        oy = zone.y + (zone.height - haut) // 2
        cadre = pygame.Rect(ox, oy, larg, haut)
        pygame.draw.rect(surface, FOND_JEU, cadre)
        for x in range(1, self.LARG):
            pygame.draw.line(surface, GRILLE, (ox + x * case, oy), (ox + x * case, oy + haut - 1))
        for x in range(self.LARG):
            for y in range(self.HAUT):
                if self.plateau[x][y] != VIDE:
                    _case(surface, self.COULEURS[self.plateau[x][y]],
                          pygame.Rect(ox + x * case, oy + y * case, case, case))
        if not self.over:
            # ombre de la position d'arrivée
            dy = 0
            while self.valide(self.piece, dy=dy + 1):
                dy += 1
            for x, y in self._cases(self.piece):
                if y + dy >= 0:
                    pygame.draw.rect(surface, GRIS, (ox + x * case, oy + (y + dy) * case, case, case), 1)
            for x, y in self._cases(self.piece):
                if y >= 0:
                    _case(surface, self.COULEURS[self.piece['forme']],
                          pygame.Rect(ox + x * case, oy + y * case, case, case))
        pygame.draw.rect(surface, BLANC, cadre.inflate(4, 4), 2)
        # pièce suivante
        px = cadre.right + case
        fonts.small.render_to(surface, (px, oy), 'Suivante', BLANC)
        p = dict(self.suivante, x=0, y=0)
        for x, y in self._cases(p):
            _case(surface, self.COULEURS[p['forme']],
                  pygame.Rect(px + x * case, oy + 20 + y * case, case, case))
        return pygame.Rect(px, oy + 20 + 5 * case + 10, zone.right - px, zone.bottom - oy)


# ----------------------------------------------------------------------
# WORMY
class Wormy(Jeu):
    titre = 'Wormy'
    LARG, HAUT = 28, 21
    aide_jeu = [('◄►▲▼', 'Diriger le ver'), ('Start', 'Pause')]
    OPPOSES = {'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left'}
    PAS = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}

    def __init__(self):
        x = random.randint(5, self.LARG - 6)
        y = random.randint(5, self.HAUT - 6)
        self.ver = [(x, y), (x - 1, y), (x - 2, y)]
        self.direction = 'right'
        self.file = []   # virages demandés entre deux pas (au plus 2)
        self.pomme = self._place_libre()
        self.score = 0
        self.over = False
        self.chrono = 0.0

    def _place_libre(self):
        libres = [(x, y) for x in range(self.LARG) for y in range(self.HAUT) if (x, y) not in self.ver]
        return random.choice(libres) if libres else None

    def delai_pas(self):
        return max(0.065, 0.14 - self.score * 0.003)

    def action(self, a):
        if self.over or a not in self.PAS:
            return
        derniere = self.file[-1] if self.file else self.direction
        if a != derniere and a != self.OPPOSES[derniere] and len(self.file) < 2:
            self.file.append(a)

    def _pas(self):
        if self.file:
            self.direction = self.file.pop(0)
        dx, dy = self.PAS[self.direction]
        tete = (self.ver[0][0] + dx, self.ver[0][1] + dy)
        mange = tete == self.pomme
        corps = self.ver if mange else self.ver[:-1]
        if not (0 <= tete[0] < self.LARG and 0 <= tete[1] < self.HAUT) or tete in corps:
            self.over = True
            return
        self.ver.insert(0, tete)
        if mange:
            self.score += 1
            self.pomme = self._place_libre()
            if self.pomme is None:
                self.over = True
        else:
            self.ver.pop()

    def update(self, dt):
        if self.over:
            return
        self.chrono += dt
        while self.chrono >= self.delai_pas() and not self.over:
            self.chrono -= self.delai_pas()
            self._pas()

    def infos(self):
        return [('Score', self.score), ('Longueur', len(self.ver))]

    def draw(self, surface, zone, fonts):
        case = min(zone.width // (self.LARG + 6), zone.height // self.HAUT)
        larg, haut = case * self.LARG, case * self.HAUT
        ox = zone.x + (zone.width - larg - 5 * case) // 2
        oy = zone.y + (zone.height - haut) // 2
        cadre = pygame.Rect(ox, oy, larg, haut)
        pygame.draw.rect(surface, FOND_JEU, cadre)
        for x in range(1, self.LARG):
            pygame.draw.line(surface, GRILLE, (ox + x * case, oy), (ox + x * case, oy + haut - 1))
        for y in range(1, self.HAUT):
            pygame.draw.line(surface, GRILLE, (ox, oy + y * case), (ox + larg - 1, oy + y * case))
        if self.pomme:
            pygame.draw.circle(surface, (230, 40, 40),
                               (ox + self.pomme[0] * case + case // 2, oy + self.pomme[1] * case + case // 2),
                               case // 2 - 2)
        for i, (x, y) in enumerate(self.ver):
            couleur = (120, 240, 120) if i == 0 else (40, 190, 80)
            _case(surface, couleur, pygame.Rect(ox + x * case, oy + y * case, case, case))
        pygame.draw.rect(surface, BLANC, cadre.inflate(4, 4), 2)
        px = cadre.right + case
        return pygame.Rect(px, oy, zone.right - px, zone.bottom - oy)


# ----------------------------------------------------------------------
# PENTOMINO : Tetromino avec des pièces de 5 cases
_PENTO_BASES = {
    'F': ['.....', '..OO.', '.OO..', '..O..', '.....'],
    'RF': ['.....', '.OO..', '..OO.', '..O..', '.....'],
    'I': ['..O..', '..O..', '..O..', '..O..', '..O..'],
    'L': ['..O..', '..O..', '..O..', '..OO.', '.....'],
    'J': ['..O..', '..O..', '..O..', '.OO..', '.....'],
    'N': ['.....', '.OO..', '..OOO', '.....', '.....'],
    'RN': ['.....', '..OO.', 'OOO..', '.....', '.....'],
    'P': ['.....', '..OO.', '..OO.', '..O..', '.....'],
    'RP': ['.....', '.OO..', '.OO..', '..O..', '.....'],
    'T': ['.....', '.OOO.', '..O..', '..O..', '.....'],
    'U': ['.....', '.O.O.', '.OOO.', '.....', '.....'],
    'V': ['..O..', '..O..', '..OOO', '.....', '.....'],
    'W': ['.....', '.O...', '.OO..', '..OO.', '.....'],
    'X': ['.....', '..O..', '.OOO.', '..O..', '.....'],
    'Y': ['.....', '..O..', 'OOOO.', '.....', '.....'],
    'RY': ['.....', '.....', 'OOOO.', '..O..', '.....'],
    'Z': ['.....', '.OO..', '..O..', '..OO.', '.....'],
    'RZ': ['.....', '..OO.', '..O..', '.OO..', '.....'],
}


def _rotations(modele):
    """Les rotations distinctes d'un modèle 5×5 (quart de tour autour du centre)."""
    vues = [modele]
    while True:
        m = vues[-1]
        tourne = [''.join(m[4 - x][y] for x in range(5)) for y in range(5)]
        if tourne in vues:
            return vues
        vues.append(tourne)


_TEINTES = [(230, 60, 60), (245, 150, 40), (240, 210, 50), (40, 200, 90), (60, 200, 230),
            (70, 110, 240), (180, 80, 220), (240, 110, 180), (150, 220, 80)]


class Pentomino(Tetromino):
    titre = 'Pentomino'
    PIECES = {k: _rotations(v) for k, v in _PENTO_BASES.items()}
    COULEURS = {k: _TEINTES[i % len(_TEINTES)] for i, k in enumerate(_PENTO_BASES)}


# ----------------------------------------------------------------------
# SIMULATE (jeu de mémoire « Simon »)
class Simulate(Jeu):
    titre = 'Simulate'
    BOUTONS = ['face_a', 'face_b', 'face_x', 'face_y']
    LETTRES = ['A', 'B', 'C', 'D']
    COULEURS = [(235, 200, 30), (40, 90, 230), (220, 40, 40), (30, 180, 70)]
    ECLAIR, ECART = 0.5, 0.2   # FLASHSPEED / FLASHDELAY d'origine
    DELAI_MAX = 4.0            # TIMEOUT d'origine : 4 s sans réponse = perdu
    aide_jeu = [('A B C D', 'Répéter la séquence'), ('Start', 'Pause')]

    def __init__(self):
        self.sequence = []
        self.score = 0
        self.eclair = None   # (bouton, durée restante) appui du joueur
        self._ajout()

    def _ajout(self):
        self.sequence.append(random.randrange(4))
        self.phase = 'montre'
        self.t = -0.8
        self.pos = 0

    def allume_auto(self):
        if self.phase != 'montre' or self.t < 0:
            return None
        pas = self.ECLAIR + self.ECART
        i = int(self.t // pas)
        if i < len(self.sequence) and self.t - i * pas < self.ECLAIR:
            return self.sequence[i]
        return None

    def update(self, dt):
        if self.eclair:
            b, r = self.eclair
            self.eclair = (b, r - dt) if r - dt > 0 else None
        if self.over:
            return
        self.t += dt
        if self.phase == 'montre':
            if self.t >= len(self.sequence) * (self.ECLAIR + self.ECART):
                self.phase = 'saisie'
                self.t = 0.0
        elif self.t > self.DELAI_MAX:
            self.over = True

    def action(self, a):
        if self.over or self.phase != 'saisie' or a not in self.BOUTONS:
            return
        b = self.BOUTONS.index(a)
        self.eclair = (b, 0.25)
        if b != self.sequence[self.pos]:
            self.over = True
            return
        self.pos += 1
        self.t = 0.0
        if self.pos == len(self.sequence):
            self.score += 1
            self._ajout()

    def infos(self):
        return [('Score', self.score), ('Séquence', len(self.sequence))]

    def draw(self, surface, zone, fonts):
        case, ox, oy = _grille(zone, 2, 2, panneau=1)
        gap = case // 12
        allume = self.allume_auto()
        if self.eclair:
            allume = self.eclair[0]
        for b in range(4):
            r = pygame.Rect(ox + (b % 2) * case + gap, oy + (b // 2) * case + gap, case - 2 * gap, case - 2 * gap)
            coul = self.COULEURS[b] if b == allume else _assombrir(self.COULEURS[b], 0.45)
            pygame.draw.rect(surface, coul, r, border_radius=24)
            lettre = self.LETTRES[b]
            g = fonts.large.get_rect(lettre)
            fonts.large.render_to(surface, (r.centerx - g.width // 2, r.centery - g.height // 2), lettre, BLANC)
        cadre = pygame.Rect(ox, oy, 2 * case, 2 * case)
        msg = 'Regardez…' if self.phase == 'montre' else 'À vous !'
        fonts.medium.render_to(surface, (cadre.right + 20, cadre.bottom - 40), msg, JAUNE)
        return _panneau(cadre, 20, zone)


# ----------------------------------------------------------------------
# MEMORY PUZZLE (paires cachées : icônes des modules, sinon formes de couleur)
ICONES = []   # [{'path', 'numero', 'titre'}], rempli par le moteur (dl.icones_distinctes)
_IMAGES = {}
# grilles possibles selon le nombre de paires disponibles (paires: colonnes, lignes)
GRILLES_MEMORY = [(35, 10, 7), (30, 10, 6), (28, 8, 7), (24, 8, 6), (20, 8, 5),
                  (18, 6, 6), (15, 6, 5), (12, 6, 4), (10, 5, 4), (8, 4, 4)]


def _image(path, taille):
    cle = (path, taille)
    if cle not in _IMAGES:
        try:
            _IMAGES[cle] = pygame.transform.smoothscale(pygame.image.load(path).convert_alpha(), (taille, taille))
        except (pygame.error, OSError):
            _IMAGES[cle] = None
    return _IMAGES[cle]


class MemoryPuzzle(Jeu):
    titre = 'Memory Puzzle'
    FORMES = ('donut', 'carre', 'losange', 'lignes', 'ovale')
    COULEURS = ((230, 50, 50), (40, 190, 80), (60, 110, 240), (240, 210, 50),
                (245, 140, 30), (170, 70, 210), (40, 210, 220))
    aide_jeu = [('◄►▲▼', 'Choisir'), ('A', 'Retourner'), ('Start', 'Pause')]

    def __init__(self):
        self.score = 0   # paires trouvées, toutes grilles confondues
        self.coups = 0
        self.grilles = 0
        self.cur = [0, 0]
        self._nouvelle()

    def _nouvelle(self):
        grille = next((g for g in GRILLES_MEMORY if g[0] <= len(ICONES)), None)
        if grille:
            paires, self.LARG, self.HAUT = grille
            icones = random.sample(range(len(ICONES)), paires) * 2
        else:
            self.LARG, self.HAUT = 10, 7
            icones = [(f, c) for f in self.FORMES for c in self.COULEURS] * 2
        self.avec_icones = bool(grille)
        self.trouvee = None   # dernière paire trouvée (index dans ICONES)
        random.shuffle(icones)
        self.plateau = [[icones[x * self.HAUT + y] for y in range(self.HAUT)] for x in range(self.LARG)]
        self.visible = [[False] * self.HAUT for _ in range(self.LARG)]
        self.premier = None
        self.a_cacher = None
        self.attente = 0.0

    def continuer(self):
        self.annonce = None
        self._nouvelle()

    def action(self, a):
        if a in DIRS:
            self._deplacer(self.cur, a, self.LARG, self.HAUT)
            return
        if a != 'face_a' or self.a_cacher:
            return
        x, y = self.cur
        if self.visible[x][y]:
            return
        self.visible[x][y] = True
        if self.premier is None:
            self.premier = (x, y)
            return
        self.coups += 1
        px, py = self.premier
        self.premier = None
        if self.plateau[px][py] == self.plateau[x][y]:
            self.score += 1
            if self.avec_icones:
                self.trouvee = self.plateau[x][y]
            if all(all(c) for c in self.visible):
                self.grilles += 1
                self.annonce = ('Grille terminée en {} coups !'.format(self.coups), 'A : nouvelle grille')
                self.coups = 0
        else:
            self.a_cacher = ((px, py), (x, y))
            self.attente = 1.0

    def update(self, dt):
        if self.a_cacher:
            self.attente -= dt
            if self.attente <= 0:
                for x, y in self.a_cacher:
                    self.visible[x][y] = False
                self.a_cacher = None

    def infos(self):
        return [('Paires', self.score), ('Coups', self.coups), ('Grilles', self.grilles)]

    @staticmethod
    def _icone(surface, forme, coul, r):
        q, h = r.width // 4, r.width // 2
        if forme == 'donut':
            pygame.draw.circle(surface, coul, r.center, h - 4)
            pygame.draw.circle(surface, FOND_JEU, r.center, q - 3)
        elif forme == 'carre':
            pygame.draw.rect(surface, coul, r.inflate(-q, -q))
        elif forme == 'losange':
            pygame.draw.polygon(surface, coul, [(r.centerx, r.y + 3), (r.right - 3, r.centery),
                                                (r.centerx, r.bottom - 3), (r.x + 3, r.centery)])
        elif forme == 'lignes':
            for i in range(0, r.width, 6):
                pygame.draw.line(surface, coul, (r.x, r.y + i), (r.x + i, r.y), 2)
                pygame.draw.line(surface, coul, (r.x + i, r.bottom - 1), (r.right - 1, r.y + i), 2)
        else:
            pygame.draw.ellipse(surface, coul, (r.x + 2, r.y + q, r.width - 4, h))

    def draw(self, surface, zone, fonts):
        bas = 44 if self.avec_icones else 0   # ligne du module de la dernière paire
        case, ox, oy = _grille(pygame.Rect(zone.x, zone.y, zone.width, zone.height - bas),
                               self.LARG, self.HAUT, panneau=4)
        cadre = pygame.Rect(ox, oy, case * self.LARG, case * self.HAUT)
        for x in range(self.LARG):
            for y in range(self.HAUT):
                r = pygame.Rect(ox + x * case + 3, oy + y * case + 3, case - 6, case - 6)
                if self.visible[x][y] and self.avec_icones:
                    pygame.draw.rect(surface, (235, 235, 245), r, border_radius=4)
                    img = _image(ICONES[self.plateau[x][y]]['path'], r.width - 4)
                    if img:
                        surface.blit(img, (r.x + 2, r.y + 2))
                elif self.visible[x][y]:
                    pygame.draw.rect(surface, FOND_JEU, r)
                    self._icone(surface, *self.plateau[x][y], r.inflate(-6, -6))
                else:
                    pygame.draw.rect(surface, (60, 70, 130), r, border_radius=4)
                    pygame.draw.rect(surface, (90, 100, 170), r.inflate(-8, -8), 2, border_radius=3)
        if self.trouvee is not None:
            m = ICONES[self.trouvee]
            texte = '✓ {}  {}'.format(m['numero'], m['titre'])
            if fonts.small.get_rect(texte).width > zone.width - 20:
                while len(texte) > 10 and fonts.small.get_rect(texte + '…').width > zone.width - 20:
                    texte = texte[:-1]
                texte = texte.rstrip() + '…'
            fonts.small.render_to(surface, (cadre.x, cadre.bottom + 16), texte, JAUNE)
        x, y = self.cur
        _curseur(surface, pygame.Rect(ox + x * case + 1, oy + y * case + 1, case - 2, case - 2))
        return _panneau(cadre, case // 2, zone)


# ----------------------------------------------------------------------
# SLIDE PUZZLE (taquin 4×4)
class SlidePuzzle(Jeu):
    titre = 'Slide Puzzle'
    N = 4
    MELANGE = 80   # generateNewPuzzle(80) d'origine
    aide_jeu = [('◄►▲▼', 'Glisser une tuile vers le trou'), ('Start', 'Pause')]

    def __init__(self):
        self.score = 0   # taquins résolus
        self.coups = 0
        self._nouveau()

    def _resolu(self):
        return [[(y * self.N + x + 1) if (x, y) != (self.N - 1, self.N - 1) else None
                 for y in range(self.N)] for x in range(self.N)]

    def _trou(self):
        for x in range(self.N):
            for y in range(self.N):
                if self.plateau[x][y] is None:
                    return x, y

    def _glisser(self, a):
        """Comme makeMove d'origine : ▲ fait monter la tuile située sous le trou."""
        bx, by = self._trou()
        dx, dy = DIRS[a]
        tx, ty = bx - dx, by - dy
        if not (0 <= tx < self.N and 0 <= ty < self.N):
            return False
        self.plateau[bx][by], self.plateau[tx][ty] = self.plateau[tx][ty], None
        return True

    def _nouveau(self):
        self.plateau = self._resolu()
        derniere = None
        opp = {'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left'}
        n = 0
        while n < self.MELANGE:
            a = random.choice([d for d in DIRS if d != opp.get(derniere)])
            if self._glisser(a):
                derniere = a
                n += 1
        if self.plateau == self._resolu():
            self._nouveau()
        self.coups = 0

    def continuer(self):
        self.annonce = None
        self._nouveau()

    def action(self, a):
        if a in DIRS and self._glisser(a):
            self.coups += 1
            if self.plateau == self._resolu():
                self.score += 1
                self.annonce = ('Résolu en {} coup{} !'.format(self.coups, 's' if self.coups > 1 else ''), 'A : nouveau taquin')

    def infos(self):
        return [('Résolus', self.score), ('Coups', self.coups)]

    def draw(self, surface, zone, fonts):
        case, ox, oy = _grille(zone, self.N, self.N, panneau=3)
        cadre = _fond_plateau(surface, ox, oy, case, self.N, self.N, lignes=False)
        for x in range(self.N):
            for y in range(self.N):
                v = self.plateau[x][y]
                if v is None:
                    continue
                r = pygame.Rect(ox + x * case + 3, oy + y * case + 3, case - 6, case - 6)
                bien = v == y * self.N + x + 1
                pygame.draw.rect(surface, (40, 170, 90) if bien else (40, 120, 200), r, border_radius=10)
                t = str(v)
                g = fonts.large.get_rect(t)
                fonts.large.render_to(surface, (r.centerx - g.width // 2, r.centery - g.height // 2), t, BLANC)
        pygame.draw.rect(surface, BLANC, cadre.inflate(4, 4), 2)
        return _panneau(cadre, case // 2, zone)


# ----------------------------------------------------------------------
# INK SPILL (inonder la grille d'une seule couleur)
class InkSpill(Jeu):
    titre = 'Ink Spill'
    N = 17          # MEDIUMBOARDSIZE
    VIE = 30        # MEDIUMMAXLIFE
    A_LISSER = 200  # cases recopiées sur un voisin (difficulté moyenne)
    PALETTE = [(230, 50, 50), (40, 190, 80), (50, 100, 240), (240, 210, 50), (245, 140, 30), (170, 70, 210)]
    aide_jeu = [('◄►', 'Couleur'), ('A', 'Verser'), ('Start', 'Pause')]

    def __init__(self):
        self.score = 0   # grilles gagnées
        self.choix = 0
        self._nouvelle()

    def _nouvelle(self):
        n = self.N
        self.plateau = [[random.randrange(len(self.PALETTE)) for _ in range(n)] for _ in range(n)]
        # L'original voulait recopier des couleurs sur des voisins (mais une
        # faute de frappe « == » l'en empêchait) : on le fait vraiment ici.
        for _ in range(self.A_LISSER):
            x, y = random.randint(1, n - 2), random.randint(1, n - 2)
            c = self.plateau[x][y]
            for dx, dy in random.choice((((-1, 0), (0, -1)), ((1, 0), (0, 1)), ((1, 0), (0, -1)), ((-1, 0), (0, 1)))):
                self.plateau[x + dx][y + dy] = c
        self.vie = self.VIE

    def continuer(self):
        self.annonce = None
        self._nouvelle()

    def _inonder(self, nouvelle):
        ancienne = self.plateau[0][0]
        pile = [(0, 0)]
        while pile:
            x, y = pile.pop()
            if 0 <= x < self.N and 0 <= y < self.N and self.plateau[x][y] == ancienne:
                self.plateau[x][y] = nouvelle
                pile += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]

    def action(self, a):
        if self.over:
            return
        if a in ('left', 'up'):
            self.choix = (self.choix - 1) % len(self.PALETTE)
        elif a in ('right', 'down'):
            self.choix = (self.choix + 1) % len(self.PALETTE)
        elif a == 'face_a' and self.choix != self.plateau[0][0]:
            self._inonder(self.choix)
            self.vie -= 1
            if all(c == self.choix for col in self.plateau for c in col):
                self.score += 1
                self.annonce = ('Grille remplie avec {} coups d\'avance !'.format(self.vie), 'A : grille suivante')
            elif self.vie == 0:
                self.over = True

    def infos(self):
        return [('Grilles', self.score), ('Coups restants', self.vie)]

    def draw(self, surface, zone, fonts):
        hp = 70   # bande de la palette sous la grille
        sous = pygame.Rect(zone.x, zone.y, zone.width, zone.height - hp)
        case, ox, oy = _grille(sous, self.N, self.N, panneau=8)
        cadre = pygame.Rect(ox, oy, case * self.N, case * self.N)
        for x in range(self.N):
            for y in range(self.N):
                pygame.draw.rect(surface, self.PALETTE[self.plateau[x][y]], (ox + x * case, oy + y * case, case, case))
        pygame.draw.rect(surface, BLANC, cadre.inflate(4, 4), 2)
        t = 48
        px = cadre.centerx - (len(self.PALETTE) * (t + 12)) // 2
        for i, c in enumerate(self.PALETTE):
            r = pygame.Rect(px + i * (t + 12), cadre.bottom + 14, t, t)
            pygame.draw.rect(surface, c, r, border_radius=8)
            if i == self.choix:
                _curseur(surface, r.inflate(6, 6))
        # jauge de vie
        jx = cadre.right + case
        for i in range(self.VIE):
            h = cadre.height // self.VIE
            r = pygame.Rect(jx, cadre.bottom - (i + 1) * h, 14, h - 2)
            pygame.draw.rect(surface, (220, 40, 40) if i < self.vie else GRILLE, r)
        return pygame.Rect(jx + 30, cadre.y, zone.right - jx - 30, zone.bottom - cadre.y)


# ----------------------------------------------------------------------
# GEMGEM (alignez trois gemmes identiques)
class Gemgem(Jeu):
    titre = 'Gemgem'
    N = 8
    TYPES = 7
    COULEURS = [(230, 50, 50), (40, 190, 80), (60, 120, 245), (245, 215, 50),
                (190, 80, 230), (245, 140, 30), (230, 230, 240)]
    PERTE = 0.8   # DEDUCTSPEED : 1 point perdu toutes les 0,8 s
    aide_jeu = [('◄►▲▼', 'Curseur'), ('A puis ◄►▲▼', 'Échanger'), ('Start', 'Pause')]

    def __init__(self):
        self.score = 0
        self.cur = [3, 3]
        self.choisie = None
        self.phase = None   # None = au joueur ; 'casse' ; 'chute'
        self.attente = 0.0
        self.a_casser = set()
        self.perte = 0.0
        self.refus = 0.0
        self.plateau = [[None] * self.N for _ in range(self.N)]
        self._remplir()
        while self._alignements() or not self._coup_possible():
            self.plateau = [[None] * self.N for _ in range(self.N)]
            self._remplir()

    def _gemme(self, x, y):
        if 0 <= x < self.N and 0 <= y < self.N:
            return self.plateau[x][y]
        return None

    def _remplir(self):
        """Comme getDropSlots : une nouvelle gemme évite la couleur de ses voisines."""
        for x in range(self.N):
            for y in range(self.N - 1, -1, -1):
                if self.plateau[x][y] is None:
                    possibles = set(range(self.TYPES)) - {self._gemme(x + dx, y + dy) for dx, dy in DIRS.values()}
                    self.plateau[x][y] = random.choice(sorted(possibles) or list(range(self.TYPES)))

    def _tomber(self):
        for x in range(self.N):
            col = [g for g in self.plateau[x] if g is not None]
            self.plateau[x] = [None] * (self.N - len(col)) + col

    def _alignements(self):
        """Liste des alignements de 3 et plus (chacun = ensemble de cases)."""
        res = []
        for x in range(self.N):
            for y in range(self.N):
                g = self.plateau[x][y]
                if g is None:
                    continue
                for dx, dy in ((1, 0), (0, 1)):
                    if self._gemme(x - dx, y - dy) == g:
                        continue   # pas le début de la série
                    serie = [(x, y)]
                    while self._gemme(serie[-1][0] + dx, serie[-1][1] + dy) == g:
                        serie.append((serie[-1][0] + dx, serie[-1][1] + dy))
                    if len(serie) >= 3:
                        res.append(serie)
        return res

    def _echanger(self, a, b):
        (ax, ay), (bx, by) = a, b
        self.plateau[ax][ay], self.plateau[bx][by] = self.plateau[bx][by], self.plateau[ax][ay]

    def _coup_possible(self):
        for x in range(self.N):
            for y in range(self.N):
                for dx, dy in ((1, 0), (0, 1)):
                    if x + dx < self.N and y + dy < self.N:
                        self._echanger((x, y), (x + dx, y + dy))
                        ok = bool(self._alignements())
                        self._echanger((x, y), (x + dx, y + dy))
                        if ok:
                            return True
        return False

    def _casser(self):
        series = self._alignements()
        if not series:
            self.phase = None
            if not self._coup_possible():
                self.over = True
            return
        for serie in series:
            self.score += 10 + (len(serie) - 3) * 10
        self.a_casser = {c for serie in series for c in serie}
        self.phase = 'casse'
        self.attente = 0.3

    def action(self, a):
        if self.over or self.phase:
            return
        if a == 'face_a':
            self.choisie = None if self.choisie else tuple(self.cur)
        elif a == 'face_b':
            self.choisie = None
        elif a in DIRS and self.choisie:
            dx, dy = DIRS[a]
            x, y = self.choisie
            cible = (x + dx, y + dy)
            self.choisie = None
            if not (0 <= cible[0] < self.N and 0 <= cible[1] < self.N):
                return
            self._echanger((x, y), cible)
            if self._alignements():
                self.cur = list(cible)
                self._casser()
            else:
                self._echanger((x, y), cible)
                self.refus = 0.3
        elif a in DIRS:
            dx, dy = DIRS[a]
            self.cur = [max(0, min(self.N - 1, self.cur[0] + dx)), max(0, min(self.N - 1, self.cur[1] + dy))]

    def update(self, dt):
        if self.over:
            return
        self.refus = max(0.0, self.refus - dt)
        if self.phase:
            self.attente -= dt
            if self.attente > 0:
                return
            if self.phase == 'casse':
                for x, y in self.a_casser:
                    self.plateau[x][y] = None
                self.a_casser = set()
                self._tomber()
                self._remplir()
                self.phase = 'chute'
                self.attente = 0.2
            else:
                self._casser()
            return
        if self.score > 0:
            self.perte += dt
            if self.perte >= self.PERTE:
                self.perte -= self.PERTE
                self.score -= 1

    def _dessin_gemme(self, surface, g, r):
        c, ctr, m = self.COULEURS[g], r.center, r.width // 2
        if g == 0:
            pygame.draw.circle(surface, c, ctr, m)
        elif g == 1:
            pygame.draw.rect(surface, c, r.inflate(-4, -4), border_radius=4)
        else:
            cotes = (3, 4, 5, 6, 8)[(g - 2) % 5]
            dep = -math.pi / 2   # le 4 côtés devient un losange (le carré est déjà pris)
            pts = [(ctr[0] + m * math.cos(dep + 2 * math.pi * i / cotes),
                    ctr[1] + m * math.sin(dep + 2 * math.pi * i / cotes)) for i in range(cotes)]
            pygame.draw.polygon(surface, c, pts)
        pygame.draw.circle(surface, BLANC, (ctr[0] - m // 3, ctr[1] - m // 3), max(2, m // 6))

    def draw(self, surface, zone, fonts):
        case, ox, oy = _grille(zone, self.N, self.N, panneau=5)
        cadre = _fond_plateau(surface, ox, oy, case, self.N, self.N)
        for x in range(self.N):
            for y in range(self.N):
                g = self.plateau[x][y]
                if g is None:
                    continue
                r = pygame.Rect(ox + x * case, oy + y * case, case, case)
                if (x, y) in self.a_casser:
                    pygame.draw.rect(surface, BLANC, r)
                self._dessin_gemme(surface, g, r.inflate(-case // 4, -case // 4))
        if self.choisie:
            x, y = self.choisie
            pygame.draw.rect(surface, (255, 80, 200), (ox + x * case, oy + y * case, case, case), 4)
        if not self.over:
            x, y = self.cur
            r = pygame.Rect(ox + x * case, oy + y * case, case, case)
            pygame.draw.rect(surface, (230, 40, 40) if self.refus else JAUNE, r, 3)
        pygame.draw.rect(surface, BLANC, cadre.inflate(4, 4), 2)
        return _panneau(cadre, case // 2, zone)


# ----------------------------------------------------------------------
# FOUR IN A ROW (puissance 4 contre l'ordinateur)
class FourInARow(Jeu):
    titre = 'Four in a Row'
    LARG, HAUT = 7, 6
    PROFONDEUR = 2   # DIFFICULTY d'origine
    JOUEUR, ORDI = 'J', 'O'
    COUL = {'J': (230, 50, 50), 'O': (245, 215, 50)}
    aide_jeu = [('◄►', 'Colonne'), ('A/▼', 'Jouer'), ('Start', 'Pause')]

    def __init__(self):
        self.score = 0   # victoires
        self.defaites = 0
        self.nuls = 0
        self.col = 3
        self._manche()

    def _manche(self):
        self.plateau = [[None] * self.HAUT for _ in range(self.LARG)]
        self.tour = random.choice((self.JOUEUR, self.ORDI))
        self.attente = 0.8

    def continuer(self):
        self.annonce = None
        self._manche()

    @staticmethod
    def _bas(plateau, col):
        for y in range(len(plateau[col]) - 1, -1, -1):
            if plateau[col][y] is None:
                return y
        return -1

    @classmethod
    def _valide(cls, plateau, col):
        return 0 <= col < cls.LARG and plateau[col][0] is None

    @classmethod
    def _jouer(cls, plateau, qui, col):
        plateau[col][cls._bas(plateau, col)] = qui

    @staticmethod
    def _plein(plateau):
        return all(c is not None for col in plateau for c in col)

    @classmethod
    def _gagne(cls, p, t):
        L, H = cls.LARG, cls.HAUT
        for x in range(L):
            col = p[x]
            for y in range(H):
                if col[y] != t:
                    continue
                if y + 3 < H and col[y + 1] == t and col[y + 2] == t and col[y + 3] == t:
                    return True
                if x + 3 < L:
                    if p[x + 1][y] == t and p[x + 2][y] == t and p[x + 3][y] == t:
                        return True
                    if y + 3 < H and p[x + 1][y + 1] == t and p[x + 2][y + 2] == t and p[x + 3][y + 3] == t:
                        return True
                    if y >= 3 and p[x + 1][y - 1] == t and p[x + 2][y - 2] == t and p[x + 3][y - 3] == t:
                        return True
        return False

    @classmethod
    def _potentiels(cls, plateau, tuile, prof):
        """getPotentialMoves d'origine (anticipation sur `prof` coups)."""
        if prof == 0 or cls._plein(plateau):
            return [0] * cls.LARG
        autre = cls.JOUEUR if tuile == cls.ORDI else cls.ORDI
        pot = [0] * cls.LARG
        for c1 in range(cls.LARG):
            p1 = [c[:] for c in plateau]
            if not cls._valide(p1, c1):
                continue
            cls._jouer(p1, tuile, c1)
            if cls._gagne(p1, tuile):
                pot[c1] = 1
                break
            if cls._plein(p1):
                continue
            for c2 in range(cls.LARG):
                p2 = [c[:] for c in p1]
                if not cls._valide(p2, c2):
                    continue
                cls._jouer(p2, autre, c2)
                if cls._gagne(p2, autre):
                    pot[c1] = -1
                    break
                res = cls._potentiels(p2, tuile, prof - 1)
                pot[c1] += (sum(res) / cls.LARG) / cls.LARG
        return pot

    def _coup_ordi(self):
        pot = self._potentiels(self.plateau, self.ORDI, self.PROFONDEUR)
        valides = [c for c in range(self.LARG) if self._valide(self.plateau, c)]
        meilleur = max(pot[c] for c in valides)
        return random.choice([c for c in valides if pot[c] == meilleur])

    def _apres_coup(self, qui):
        if self._gagne(self.plateau, qui):
            if qui == self.JOUEUR:
                self.score += 1
                self.annonce = ('Gagné !', 'A : manche suivante')
            else:
                self.defaites += 1
                self.annonce = ("L'ordinateur gagne.", 'A : revanche')
        elif self._plein(self.plateau):
            self.nuls += 1
            self.annonce = ('Match nul.', 'A : manche suivante')
        else:
            self.tour = self.ORDI if qui == self.JOUEUR else self.JOUEUR
            self.attente = 0.6

    def action(self, a):
        if self.annonce or self.tour != self.JOUEUR:
            return
        if a == 'left':
            self.col = max(0, self.col - 1)
        elif a == 'right':
            self.col = min(self.LARG - 1, self.col + 1)
        elif a in ('face_a', 'down') and self._valide(self.plateau, self.col):
            self._jouer(self.plateau, self.JOUEUR, self.col)
            self._apres_coup(self.JOUEUR)

    def update(self, dt):
        if self.annonce or self.tour != self.ORDI:
            return
        self.attente -= dt
        if self.attente <= 0:
            self._jouer(self.plateau, self.ORDI, self._coup_ordi())
            self._apres_coup(self.ORDI)

    def infos(self):
        return [('Victoires', self.score), ('Défaites', self.defaites), ('Nuls', self.nuls)]

    def draw(self, surface, zone, fonts):
        case, ox, oy = _grille(zone, self.LARG, self.HAUT + 1, panneau=4)
        oy += case
        cadre = pygame.Rect(ox, oy, case * self.LARG, case * self.HAUT)
        pygame.draw.rect(surface, (30, 60, 170), cadre, border_radius=10)
        for x in range(self.LARG):
            for y in range(self.HAUT):
                c = self.plateau[x][y]
                pygame.draw.circle(surface, self.COUL[c] if c else FOND_JEU,
                                   (ox + x * case + case // 2, oy + y * case + case // 2), case // 2 - 6)
        if not self.annonce and self.tour == self.JOUEUR:
            pygame.draw.circle(surface, self.COUL[self.JOUEUR],
                               (ox + self.col * case + case // 2, oy - case // 2), case // 2 - 6)
        elif not self.annonce:
            fonts.medium.render_to(surface, (ox, oy - case // 2 - 10), "L'ordinateur réfléchit…", JAUNE)
        return _panneau(cadre, case // 2, zone)


# ----------------------------------------------------------------------
# FLIPPY (Othello contre l'ordinateur)
class Flippy(Jeu):
    titre = 'Flippy'
    N = 8
    JOUEUR, ORDI = 'N', 'B'
    COUL = {'N': (25, 25, 30), 'B': (245, 245, 250)}
    aide_jeu = [('◄►▲▼', 'Case'), ('A', 'Poser'), ('Start', 'Pause')]
    VOISINS = [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]

    def __init__(self):
        self.score = 0   # victoires
        self.defaites = 0
        self.nuls = 0
        self.cur = [2, 3]
        self._manche()

    def _manche(self):
        p = [[None] * self.N for _ in range(self.N)]
        p[3][3] = p[4][4] = self.ORDI
        p[3][4] = p[4][3] = self.JOUEUR
        self.plateau = p
        self.tour = random.choice((self.JOUEUR, self.ORDI))
        self.attente = 0.8
        self.message = ''

    def continuer(self):
        self.annonce = None
        self._manche()

    def _sur(self, x, y):
        return 0 <= x < self.N and 0 <= y < self.N

    def _a_retourner(self, p, t, x0, y0):
        """isValidMove d'origine : liste des pions retournés, vide si coup interdit."""
        if not self._sur(x0, y0) or p[x0][y0] is not None:
            return []
        autre = self.ORDI if t == self.JOUEUR else self.JOUEUR
        res = []
        for dx, dy in self.VOISINS:
            x, y, ligne = x0 + dx, y0 + dy, []
            while self._sur(x, y) and p[x][y] == autre:
                ligne.append((x, y))
                x, y = x + dx, y + dy
            if ligne and self._sur(x, y) and p[x][y] == t:
                res += ligne
        return res

    def _coups(self, p, t):
        return [(x, y) for x in range(self.N) for y in range(self.N) if self._a_retourner(p, t, x, y)]

    def _poser(self, p, t, x, y):
        for a, b in self._a_retourner(p, t, x, y):
            p[a][b] = t
        p[x][y] = t

    def _compte(self, t):
        return sum(c == t for col in self.plateau for c in col)

    def _coup_ordi(self):
        """getComputerMove d'origine : un coin d'abord, sinon le coup qui
        retourne le plus de pions (le test de coin d'origine, décalé d'une case,
        est corrigé ici)."""
        coups = self._coups(self.plateau, self.ORDI)
        random.shuffle(coups)
        coins = [c for c in coups if c[0] in (0, self.N - 1) and c[1] in (0, self.N - 1)]
        if coins:
            return coins[0]
        return max(coups, key=lambda c: len(self._a_retourner(self.plateau, self.ORDI, *c)))

    def _tour_suivant(self, qui):
        autre = self.ORDI if qui == self.JOUEUR else self.JOUEUR
        self.message = ''
        if self._coups(self.plateau, autre):
            self.tour = autre
        elif self._coups(self.plateau, qui):
            self.tour = qui
            self.message = ('Vous passez votre tour.' if autre == self.JOUEUR
                            else "L'ordinateur passe son tour.")
        else:
            j, o = self._compte(self.JOUEUR), self._compte(self.ORDI)
            if j > o:
                self.score += 1
                self.annonce = ('Gagné {} à {} !'.format(j, o), 'A : manche suivante')
            elif j < o:
                self.defaites += 1
                self.annonce = ("L'ordinateur gagne {} à {}.".format(o, j), 'A : revanche')
            else:
                self.nuls += 1
                self.annonce = ('Égalité {} partout.'.format(j), 'A : manche suivante')
            return
        self.attente = 0.7

    def action(self, a):
        if self.annonce or self.tour != self.JOUEUR:
            return
        if a in DIRS:
            self._deplacer(self.cur, a, self.N, self.N)
        elif a == 'face_a' and self._a_retourner(self.plateau, self.JOUEUR, *self.cur):
            self._poser(self.plateau, self.JOUEUR, *self.cur)
            self._tour_suivant(self.JOUEUR)

    def update(self, dt):
        if self.annonce or self.tour != self.ORDI:
            return
        self.attente -= dt
        if self.attente <= 0:
            self._poser(self.plateau, self.ORDI, *self._coup_ordi())
            self._tour_suivant(self.ORDI)

    def infos(self):
        return [('Vous (noirs)', self._compte(self.JOUEUR)), ('Ordinateur', self._compte(self.ORDI)),
                ('Victoires', self.score), ('Défaites', self.defaites)]

    def draw(self, surface, zone, fonts):
        case, ox, oy = _grille(zone, self.N, self.N, panneau=6)
        cadre = pygame.Rect(ox, oy, case * self.N, case * self.N)
        pygame.draw.rect(surface, (20, 120, 60), cadre)
        for i in range(self.N + 1):
            pygame.draw.line(surface, (10, 70, 35), (ox + i * case, oy), (ox + i * case, cadre.bottom), 2)
            pygame.draw.line(surface, (10, 70, 35), (ox, oy + i * case), (cadre.right, oy + i * case), 2)
        aides = self._coups(self.plateau, self.JOUEUR) if self.tour == self.JOUEUR and not self.annonce else []
        for x in range(self.N):
            for y in range(self.N):
                c = (ox + x * case + case // 2, oy + y * case + case // 2)
                if self.plateau[x][y]:
                    pygame.draw.circle(surface, self.COUL[self.plateau[x][y]], c, case // 2 - 5)
                elif (x, y) in aides:
                    pygame.draw.circle(surface, (90, 190, 120), c, case // 8)
        if self.tour == self.JOUEUR and not self.annonce:
            x, y = self.cur
            _curseur(surface, pygame.Rect(ox + x * case + 2, oy + y * case + 2, case - 4, case - 4))
        panneau = _panneau(cadre, case // 2, zone)
        msg = self.message or ("L'ordinateur réfléchit…" if self.tour == self.ORDI and not self.annonce else '')
        if msg:
            fonts.small.render_to(surface, (panneau.x, cadre.bottom - 24), msg, JAUNE)
        return panneau


JEUX = {'tetromino': Tetromino, 'pentomino': Pentomino, 'wormy': Wormy, 'simulate': Simulate,
        'memory': MemoryPuzzle, 'slide': SlidePuzzle, 'inkspill': InkSpill, 'gemgem': Gemgem,
        'fourinarow': FourInARow, 'flippy': Flippy}
from minijeux_action import Plateforme, Course, Bagarre  # noqa: E402 (utilise Jeu ci-dessus)
JEUX.update({'plateforme': Plateforme, 'course': Course, 'bagarre': Bagarre})
ORDRE = ['plateforme', 'course', 'bagarre', 'tetromino', 'pentomino', 'wormy', 'gemgem', 'simulate',
         'memory', 'slide', 'inkspill', 'fourinarow', 'flippy']


# ----------------------------------------------------------------------
class Session:
    """Une session bonus : une ou plusieurs parties du même jeu, de 5 à 10 min.

    Une partie perdue avant 5 min est relancée (le meilleur score est gardé) ;
    à 10 min la partie en cours s'arrête. La pause gèle le chronomètre.
    États : 'jeu', 'pause', 'perdu' (avant 5 min, A pour rejouer), 'fin'."""

    def __init__(self, jeu_id, record=0):
        self.jeu_id = jeu_id
        self.record_avant = record
        self.jeu = JEUX[jeu_id]()
        self.etat = 'jeu'
        self.ecoule = 0.0
        self.meilleur = 0
        self.parties = 1
        self.quitter = False   # passe à True quand le joueur referme le résumé
        self.tenu = (0, 0, frozenset())

    @property
    def titre(self):
        return self.jeu.titre

    def restant(self):
        return max(0.0, SESSION_MAX_S - self.ecoule)

    def _fin_partie(self):
        self.meilleur = max(self.meilleur, self.jeu.score)
        self.etat = 'perdu' if self.ecoule < SESSION_MIN_S else 'fin'

    def update(self, dt):
        if self.etat != 'jeu':
            return
        self.ecoule += dt
        self.jeu.tenu = self.tenu
        self.jeu.update(dt)
        if self.jeu.over:
            self._fin_partie()
        elif self.ecoule >= SESSION_MAX_S:
            self.meilleur = max(self.meilleur, self.jeu.score)
            self.etat = 'fin'

    def action(self, a):
        """a : action brute du moteur (face_a/b/x/y, action = Start, back = Select,
        directions, gâchettes)."""
        if self.etat == 'jeu':
            if a in ('action', 'back'):
                self.etat = 'pause'
            elif self.jeu.annonce:
                if a == 'face_a':
                    self.jeu.continuer()
            else:
                self.jeu.action(a)
        elif self.etat == 'pause':
            if a in ('action', 'face_a'):
                self.etat = 'jeu'
            elif a in ('back', 'face_b'):
                self.meilleur = max(self.meilleur, self.jeu.score)
                self.etat = 'fin'
        elif self.etat == 'perdu':
            if a in ('action', 'face_a'):
                self.jeu = JEUX[self.jeu_id]()
                self.parties += 1
                self.etat = 'jeu'
            elif a in ('back', 'face_b'):
                self.etat = 'fin'
        elif self.etat == 'fin':
            if a in ('action', 'back', 'face_a', 'face_b'):
                self.quitter = True

    def aide(self):
        if self.etat == 'jeu':
            return self.jeu.aide
        if self.etat == 'pause':
            return [('A/Start', 'Reprendre'), ('B/Select', 'Terminer')]
        if self.etat == 'perdu':
            return [('A/Start', 'Rejouer'), ('B/Select', 'Terminer')]
        return [('A/Start', 'Continuer')]

    def draw(self, surface, zone, fonts):
        panneau = self.jeu.draw(surface, zone, fonts)
        restant = int(self.restant())
        lignes = list(self.jeu.infos()) + [
            ('Record', max(self.record_avant, self.meilleur, self.jeu.score)),
            ('Temps', '{}:{:02d}'.format(restant // 60, restant % 60)),
        ]
        if panneau is None:
            # jeu en plein écran (défilement) : bandeau de scores en haut
            bande = pygame.Rect(zone.x, zone.y, zone.width, 34)
            voile = pygame.Surface(bande.size, pygame.SRCALPHA)
            voile.fill((0, 0, 0, 150))
            surface.blit(voile, bande.topleft)
            x = bande.x + 12
            for nom, val in lignes:
                fonts.small.render_to(surface, (x, bande.y + 8), nom, GRIS)
                x += fonts.small.get_rect(nom).width + 8
                fonts.small.render_to(surface, (x, bande.y + 8), str(val), BLANC)
                x += fonts.small.get_rect(str(val)).width + 26
        else:
            x, y = panneau.x, panneau.y + 10
            for nom, val in lignes:
                fonts.small.render_to(surface, (x, y), nom, GRIS)
                fonts.medium.render_to(surface, (x, y + 24), str(val), BLANC)
                y += 64
            if self.parties > 1:
                fonts.small.render_to(surface, (x, y), 'Partie {}'.format(self.parties), GRIS)

        if self.etat == 'jeu' and self.jeu.annonce:
            titre, sous = self.jeu.annonce
            bande = pygame.Rect(zone.x, zone.centery - 70, zone.width, 140)
            voile = pygame.Surface(bande.size, pygame.SRCALPHA)
            voile.fill((0, 0, 0, 200))
            surface.blit(voile, bande.topleft)
            for i, (txt, font, coul) in enumerate(((titre, fonts.large, JAUNE), (sous, fonts.medium, BLANC))):
                r = font.get_rect(txt)
                font.render_to(surface, (zone.centerx - r.width // 2, bande.y + 28 + i * 56), txt, coul)
        if self.etat != 'jeu':
            voile = pygame.Surface(zone.size, pygame.SRCALPHA)
            voile.fill((0, 0, 0, 170))
            surface.blit(voile, zone.topleft)
            if self.etat == 'pause':
                titre, sous = 'PAUSE', 'Le chronomètre est arrêté.'
            elif self.etat == 'perdu':
                titre = 'Partie terminée : {} points'.format(self.jeu.score)
                sous = 'Encore {} min de jeu bonus : A pour rejouer.'.format(
                    max(1, int((SESSION_MIN_S - self.ecoule) // 60) + 1))
            else:
                titre = 'Fin du bonus : meilleur score {}'.format(self.meilleur)
                if self.meilleur > self.record_avant:
                    sous = 'Nouveau record !'
                else:
                    sous = 'Record à battre : {}'.format(self.record_avant)
            for i, (txt, font, coul) in enumerate(((titre, fonts.large, JAUNE), (sous, fonts.medium, BLANC))):
                r = font.get_rect(txt)
                font.render_to(surface, (zone.centerx - r.width // 2, zone.centery - 40 + i * 60), txt, coul)
