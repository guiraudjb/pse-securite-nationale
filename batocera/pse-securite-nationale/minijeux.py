# Mini-jeux bonus (récompense d'un QCM réussi à plus de 80 %).
#
# Tetromino et Wormy sont adaptés des jeux d'Al Sweigart (« Making Games with
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


class Tetromino:
    titre = 'Tetromino'
    LARG, HAUT = 10, 20
    aide = [('◄►', 'Déplacer'), ('▼', 'Descendre'), ('A/▲', 'Tourner'), ('B', 'Tourner ↺'),
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
        forme = random.choice(list(PIECES))
        return {'forme': forme, 'rot': random.randint(0, len(PIECES[forme]) - 1),
                'x': self.LARG // 2 - T_LARG // 2, 'y': -2}

    @staticmethod
    def _cases(piece):
        modele = PIECES[piece['forme']][piece['rot']]
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
        n = len(PIECES[self.piece['forme']])
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
                    _case(surface, COULEURS_PIECES[self.plateau[x][y]],
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
                    _case(surface, COULEURS_PIECES[self.piece['forme']],
                          pygame.Rect(ox + x * case, oy + y * case, case, case))
        pygame.draw.rect(surface, BLANC, cadre.inflate(4, 4), 2)
        # pièce suivante
        px = cadre.right + case
        fonts.small.render_to(surface, (px, oy), 'Suivante', BLANC)
        p = dict(self.suivante, x=0, y=0)
        for x, y in self._cases(p):
            _case(surface, COULEURS_PIECES[p['forme']],
                  pygame.Rect(px + x * case, oy + 20 + y * case, case, case))
        return pygame.Rect(px, oy + 20 + 5 * case + 10, zone.right - px, zone.bottom - oy)


# ----------------------------------------------------------------------
# WORMY
class Wormy:
    titre = 'Wormy'
    LARG, HAUT = 28, 21
    aide = [('◄►▲▼', 'Diriger le ver'), ('Start', 'Pause')]
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


JEUX = {'tetromino': Tetromino, 'wormy': Wormy}
ORDRE = ['tetromino', 'wormy']


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
        x, y = panneau.x, panneau.y + 10
        restant = int(self.restant())
        lignes = list(self.jeu.infos()) + [
            ('Record', max(self.record_avant, self.meilleur, self.jeu.score)),
            ('Temps', '{}:{:02d}'.format(restant // 60, restant % 60)),
        ]
        for nom, val in lignes:
            fonts.small.render_to(surface, (x, y), nom, GRIS)
            fonts.medium.render_to(surface, (x, y + 24), str(val), BLANC)
            y += 64
        if self.parties > 1:
            fonts.small.render_to(surface, (x, y), 'Partie {}'.format(self.parties), GRIS)

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
