# Mini-jeux d'action : plateforme 2D, course (run and jump), bagarre (beat them all).
#
# Code original. Graphismes : packs « Pixel Platformer » et « Toon Characters » de
# Kenney (www.kenney.nl), licence CC0 (domaine public) : voir
# assets/minijeux/*/LICENCE.txt.
#
# Les jeux d'action lisent l'état maintenu de la manette (self.tenu = (dx, dy,
# boutons), fourni à chaque image par la session) en plus des appuis ponctuels
# reçus par action().
import math
import os
import random
import pygame

from minijeux import Jeu, BLANC, JAUNE

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'minijeux')
SOUS_PAS = 1 / 120.0   # pas de simulation physique maximal (s)


# ----------------------------------------------------------------------
# Images
_FEUILLES = {}
_MIROIRS = {}


def _feuille(nom, t, cols, rows, taille):
    """Découpe une planche Kenney (tuiles de t px, sans marge) et met chaque tuile
    à `taille` px, sans lissage (pixel art)."""
    cle = (nom, taille)
    if cle not in _FEUILLES:
        img = pygame.image.load(os.path.join(ASSETS, 'pixel-platformer', nom)).convert_alpha()
        _FEUILLES[cle] = [pygame.transform.scale(img.subsurface(((i % cols) * t, (i // cols) * t, t, t)),
                                                 (taille, taille)) for i in range(cols * rows)]
    return _FEUILLES[cle]


def tuile(i, taille):
    return _feuille('tuiles.png', 18, 20, 9, taille)[i]


def perso_pixel(i, taille, miroir=False):
    img = _feuille('personnages.png', 24, 9, 3, taille)[i]
    return _miroir(img) if miroir else img


def fond(i, taille):
    return _feuille('fonds.png', 24, 8, 3, taille)[i]


def _miroir(img):
    if img not in _MIROIRS:
        _MIROIRS[img] = pygame.transform.flip(img, True, False)
    return _MIROIRS[img]


_TOON = {}


def toon(perso, pose, echelle, miroir=False):
    cle = (perso, pose, round(echelle, 3))
    if cle not in _TOON:
        img = pygame.image.load(os.path.join(ASSETS, 'toon', perso, pose + '.png')).convert_alpha()
        w, h = img.get_size()
        _TOON[cle] = pygame.transform.smoothscale(img, (max(1, int(w * echelle)), max(1, int(h * echelle))))
    img = _TOON[cle]
    return _miroir(img) if miroir else img


# ----------------------------------------------------------------------
# Physique en unités de tuiles (indépendante de la résolution)
class Corps:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.vx = self.vy = 0.0
        self.au_sol = False
        self.mur = 0
        self.plafond = None

    def rect(self):
        return (self.x, self.y, self.x + self.w, self.y + self.h)

    def touche(self, autre, marge=0.0):
        a, b = self.rect(), autre.rect()
        return a[0] + marge < b[2] and b[0] + marge < a[2] and a[1] + marge < b[3] and b[1] + marge < a[3]


def deplacer(e, dt, solide, planche):
    """Déplace e de (vx, vy)·dt, axe par axe, contre les cases solides ;
    une planche ne bloque que par le dessus."""
    e.x += e.vx * dt
    haut, bas = int(math.floor(e.y + 0.02)), int(math.floor(e.y + e.h - 0.02))
    e.mur = 0
    if e.vx > 0:
        c = int(math.floor(e.x + e.w))
        if any(solide(c, r) for r in range(haut, bas + 1)):
            e.x = c - e.w - 0.001
            e.mur = 1
    elif e.vx < 0:
        c = int(math.floor(e.x))
        if any(solide(c, r) for r in range(haut, bas + 1)):
            e.x = c + 1.001
            e.mur = -1
    ancien_bas = e.y + e.h
    e.y += e.vy * dt
    g, d = int(math.floor(e.x + 0.02)), int(math.floor(e.x + e.w - 0.02))
    e.au_sol = False
    e.plafond = None
    if e.vy > 0:
        r = int(math.floor(e.y + e.h))
        for c in range(g, d + 1):
            if solide(c, r) or (planche(c, r) and ancien_bas <= r + 0.02):
                e.y = r - e.h
                e.vy = 0.0
                e.au_sol = True
                break
    elif e.vy < 0:
        r = int(math.floor(e.y))
        for c in range(g, d + 1):
            if solide(c, r):
                e.y = r + 1.0
                e.vy = 0.0
                e.plafond = (c, r)
                break


GRAVITE = 42.0        # tuiles/s²
SAUT = 17.5           # vitesse initiale du saut (≈ 3,6 tuiles de haut)
REBOND = 13.0         # après avoir écrasé un ennemi
RESSORT = 26.0
MARCHE, COURSE = 6.5, 9.5
CHUTE_MAX = 22.0


# ----------------------------------------------------------------------
# PLATEFORME 2D
#
# Un niveau = blocs juxtaposés. Bloc : (largeur, sol, objets)
#   sol : un caractère par colonne, chiffre k = sol de k cases de haut, ' ' = trou ;
#   objets : {ligne: texte} posé par-dessus (les espaces ne remplacent rien).
# Codes : B caisse, ? bloc bonus, = planche, o pièce, ^ pics, S ressort, H cœur,
# K drapeau d'étape, D porte de sortie, P départ, E ennemi, Z ennemi à pointes
# (ne s'écrase pas), F chauve-souris ; décor : g herbe, t sapin, c cactus,
# m champignon, n bonhomme de neige, p panneau.
LIGNES = 15

NIVEAUX = [
    ('Prairie', 'herbe', [
        (16, '3' * 16, {7: '      ?   ?', 11: ' P  p   g   t'}),
        (18, '3333333   33333333', {7: '     ooo', 9: '    ====', 11: '            E'}),
        (20, '33333444555544433333', {7: '         ooo', 11: ' E               g'}),
        (16, '3333    33333333', {8: '    oooo', 11: '          ^^   m'}),
        (18, '3' * 18, {11: ' K      E     E  '}),
        (22, '3' * 22, {4: '        oo', 6: '       ====', 9: '  ====', 8: '               F'}),
        (14, '33  33  33  333', {9: '  o   o   o'}),
        (18, '3' * 18, {7: '    ???', 11: '    E   g     t'}),
        (16, '3' * 16, {11: '   H      D  g'}),
    ]),
    ('Neige', 'neige', [
        (14, '3' * 14, {11: ' P   n    p'}),
        (20, '333333    4444  3333', {6: '       oo', 8: '      ==', 10: '          E'}),
        (18, '33333333     33333', {8: '   ?  ?', 11: '      E        S'}),
        (20, '3' * 20, {3: '          ooo', 5: '         =====', 9: '   F', 11: '      ^^^      E'}),
        (16, '3333333333333333', {11: '  K    n     E'}),
        (22, '333   33   33   3333333', {7: '   o    o    o', 11: '                  E'}),
        (18, '334455   5544333', {6: '      oo', 8: '     ', 11: '               '}),
        (20, '3' * 20, {6: '    ??B??', 9: '            F', 11: ' E      E      Z'}),
        (16, '3' * 16, {11: '  H    n   D'}),
    ]),
    ('Désert', 'desert', [
        (14, '3' * 14, {11: ' P   c   p'}),
        (20, '3333333333333333333', {11: '    ^    ^    ^  Z'}),
        (18, '3333    33333  3333', {7: '     oo     oo', 10: '     ==', 11: '               '}),
        (20, '33333333333333333333', {3: '           ooo', 5: '          =====', 11: '      S   E    c'}),
        (16, '3' * 16, {11: '  K    Z     E'}),
        (22, '3335555553333  33333333', {7: '    ?? ?', 9: '', 11: '               F  E'}),
        (22, '333  33  33  33  33333', {8: '     o   o   o   o'}),
        (18, '3' * 18, {8: '      F', 11: '  Z   ^^^   E    '}),
        (16, '3' * 16, {11: '  H  c    D'}),
    ]),
]

THEMES = {
    # (bordure gauche, haut, bordure droite, isolé), fond : (ciel, collines, bas)
    'herbe': {'haut': (1, 2, 3, 0), 'fond': (6, (14, 15), 22)},
    'neige': {'haut': (81, 82, 83, 80), 'fond': (0, (8, 9, 10, 11), 16)},
    'desert': {'haut': (41, 42, 43, 40), 'fond': (4, (12, 13), 20)},
}
DEDANS = (4, 5, 24, 25)
DECOR = {'g': 124, 't': 126, 'c': 127, 'm': 128, 'n': 145, 'p': 85}
SOLIDES = 'B?u#'


def construire_niveau(blocs):
    grille = []
    for largeur, sol, objets in blocs:
        bloc = [[' '] * largeur for _ in range(LIGNES)]
        for c in range(largeur):
            k = sol[c] if c < len(sol) else ' '
            if k.isdigit():
                for r in range(LIGNES - int(k), LIGNES):
                    bloc[r][c] = '#'
        for r, texte in objets.items():
            for c, ch in enumerate(texte[:largeur]):
                if ch != ' ':
                    bloc[r][c] = ch
        if not grille:
            grille = bloc
        else:
            for r in range(LIGNES):
                grille[r] += bloc[r]
    return grille


class Plateforme(Jeu):
    titre = 'Plateforme'
    aide_jeu = [('◄►', 'Marcher'), ('A/C', 'Sauter'), ('B (tenu)', 'Courir'), ('Start', 'Pause')]

    def __init__(self):
        self.score = 0
        self.pieces = 0
        self.vies = 3
        self.niveau = 0
        self.tour = 1          # augmente quand les 3 niveaux sont finis
        self.t = 0.0
        self._charger()

    # -- niveau
    def _charger(self):
        nom, theme, blocs = NIVEAUX[self.niveau]
        self.nom, self.theme = nom, THEMES[theme]
        self.grille = construire_niveau(blocs)
        self.larg = len(self.grille[0])
        self.ennemis = []
        self.depart = (1.0, 10.0)
        for r in range(LIGNES):
            for c in range(self.larg):
                ch = self.grille[r][c]
                if ch == 'P':
                    self.depart = (c + 0.1, r - 0.15)
                    self.grille[r][c] = ' '
                elif ch in 'EZF':
                    e = Corps(c + 0.1, r + 0.2, 0.8, 0.8)
                    e.genre = ch
                    vit = (1.6 if ch != 'F' else 2.2) * (1 + 0.15 * (self.tour - 1))
                    e.vx = -vit
                    e.base_y, e.x0 = r + 0.1, c
                    e.mort = 0.0
                    self.ennemis.append(e)
                    self.grille[r][c] = ' '
        self.etape = self.depart
        self.bulles = []   # pièces qui sortent d'un bloc bonus : [x, y, durée]
        self._respawn()

    def _respawn(self):
        self.j = Corps(self.etape[0], self.etape[1], 0.75, 1.05)
        self.face = 1
        self.coyote = 0.0
        self.tampon = 0.0
        self.invincible = 1.0
        self.cam = 0.0

    def continuer(self):
        self.annonce = None
        self.niveau += 1
        if self.niveau >= len(NIVEAUX):
            self.niveau = 0
            self.tour += 1
        self._charger()

    # -- cases
    def case(self, c, r):
        if c < 0:
            return '#'
        if 0 <= r < LIGNES and c < self.larg:
            return self.grille[r][c]
        return ' '

    def solide(self, c, r):
        return self.case(c, r) in SOLIDES

    def planche(self, c, r):
        return self.case(c, r) == '='

    # -- jeu
    def action(self, a):
        if a in ('face_a', 'face_x', 'face_y'):
            self.tampon = 0.15

    def _perdre_vie(self):
        self.vies -= 1
        if self.vies <= 0:
            self.over = True
        else:
            self._respawn()

    def update(self, dt):
        if self.over or self.annonce:
            return
        self.t += dt
        while dt > 0:
            pas = min(dt, SOUS_PAS)
            dt -= pas
            self._pas(pas)
            if self.over or self.annonce:
                return

    def _pas(self, dt):
        dx, _dy, boutons = self.tenu
        j = self.j
        vmax = COURSE if 'face_b' in boutons else MARCHE
        if dx:
            j.vx += dx * 40.0 * dt
            j.vx = max(-vmax, min(vmax, j.vx))
            self.face = dx
        else:
            j.vx *= max(0.0, 1 - 12 * dt)
            if abs(j.vx) < 0.1:
                j.vx = 0.0
        self.coyote = 0.1 if j.au_sol else max(0.0, self.coyote - dt)
        self.tampon = max(0.0, self.tampon - dt)
        if self.tampon > 0 and self.coyote > 0:
            j.vy = -SAUT
            self.tampon = self.coyote = 0.0
        saut_tenu = boutons & {'face_a', 'face_x', 'face_y'}
        if j.vy < -6 and not saut_tenu:
            j.vy = -6.0   # saut court si le bouton est relâché tôt
        j.vy = min(CHUTE_MAX, j.vy + GRAVITE * dt)
        deplacer(j, dt, self.solide, self.planche)
        if j.plafond:
            c, r = j.plafond
            if self.grille[r][c] == '?':
                self.grille[r][c] = 'u'
                self.pieces += 1
                self.score += 10
                self.bulles.append([c, r - 1, 0.5])
        self.bulles = [[x, y - 3 * dt, t - dt] for x, y, t in self.bulles if t - dt > 0]
        self.invincible = max(0.0, self.invincible - dt)

        # objets touchés
        for r in range(int(j.y), int(j.y + j.h) + 1):
            for c in range(int(j.x), int(j.x + j.w) + 1):
                ch = self.case(c, r)
                if ch == 'o':
                    self.grille[r][c] = ' '
                    self.pieces += 1
                    self.score += 10
                elif ch == 'H':
                    self.grille[r][c] = ' '
                    self.vies = min(5, self.vies + 1)
                elif ch == 'K':
                    self.grille[r][c] = 'k'
                    self.etape = (c + 0.1, r - 0.15)
                elif ch == 'D':
                    self.score += 100
                    self.annonce = ('{} terminé !'.format(self.nom), 'A : niveau suivant')
                    return
                elif ch == 'S' and j.vy > 0 and j.y + j.h > r + 0.4:
                    j.vy = -RESSORT
                elif ch == '^' and j.y + j.h > r + 0.55 and j.x + j.w - 0.2 > c and j.x + 0.2 < c + 1 \
                        and not self.invincible:
                    self._perdre_vie()   # les pics n'occupent que le bas de la case
                    return
        if j.y > LIGNES + 1:
            self._perdre_vie()
            return

        # ennemis
        for e in self.ennemis:
            if e.mort:
                e.mort -= dt
                e.fini = e.mort <= 0
                continue
            if e.genre == 'F':
                e.x += e.vx * dt
                if abs(e.x - e.x0) > 3:
                    e.vx = -e.vx
                    e.x = e.x0 + math.copysign(3, e.x - e.x0)
                e.y = e.base_y + 0.6 * math.sin(self.t * 3 + e.x0)
            else:
                e.vy = min(CHUTE_MAX, e.vy + GRAVITE * dt)
                deplacer(e, dt, self.solide, self.planche)
                if e.mur:
                    e.vx = -e.vx
                elif e.au_sol:
                    devant = int(e.x + (e.w + 0.05 if e.vx > 0 else -0.05))
                    if not (self.solide(devant, int(e.y + e.h + 0.1)) or self.planche(devant, int(e.y + e.h + 0.1))):
                        e.vx = -e.vx   # ne tombe pas des bords
                if e.vx == 0:
                    e.vx = 1.6
                if e.y > LIGNES + 1:
                    e.mort = 0.01
            if j.touche(e, 0.08):
                if j.vy > 0 and j.y + j.h - e.y < 0.55 and e.genre != 'Z':
                    e.mort = 0.4
                    e.ecrase = True
                    self.score += 20
                    saut_tenu = self.tenu[2] & {'face_a', 'face_x', 'face_y'}
                    j.vy = -(SAUT if saut_tenu else REBOND)
                elif not self.invincible:
                    self._perdre_vie()
                    return
        self.ennemis = [e for e in self.ennemis if not getattr(e, 'fini', False)]

    def infos(self):
        return [('Score', self.score), ('Pièces', self.pieces), ('Vies', self.vies),
                ('Niveau', '{} {}'.format(self.niveau + 1, self.nom))]

    # -- dessin
    def _fond(self, surface, zone, T):
        ciel, collines, bas = self.theme['fond']
        B = T * 3
        surface.fill(fond(ciel, 8).get_at((4, 4)), zone)
        y_band = zone.y + int(zone.height * 0.62) - B
        surface.fill(fond(bas, 8).get_at((4, 4)), (zone.x, y_band + B, zone.width, zone.bottom - y_band - B))
        decal = int(self.cam * T * 0.35) % (B * len(collines))
        x = zone.x - decal
        i = 0
        while x < zone.right:
            surface.blit(fond(collines[i % len(collines)], B), (x, y_band))
            x += B
            i += 1

    def draw(self, surface, zone, fonts):
        T = max(18, zone.height // LIGNES)
        vue = zone.width / T
        cible = self.j.x - vue * 0.4
        self.cam = max(0.0, min(self.larg - vue, cible))
        ox = zone.x - int(self.cam * T)
        oy = zone.y + (zone.height - T * LIGNES)
        ancien_clip = surface.get_clip()
        surface.set_clip(zone)
        self._fond(surface, zone, T)
        g = int(self.cam)
        haut = self.theme['haut']
        anim = int(self.t * 4) % 2
        for r in range(LIGNES):
            for c in range(g, min(self.larg, g + int(vue) + 2)):
                ch = self.grille[r][c]
                if ch == ' ':
                    continue
                pos = (ox + c * T, oy + r * T)
                if ch == '#':
                    if self.case(c, r - 1) != '#':
                        gauche, droite = self.case(c - 1, r) == '#', self.case(c + 1, r) == '#'
                        i = haut[1] if gauche and droite else haut[0] if droite else haut[2] if gauche else haut[3]
                    else:
                        i = DEDANS[(c * 7 + r * 3) % 4]
                    surface.blit(tuile(i, T), pos)
                elif ch == '=':
                    gauche, droite = self.case(c - 1, r) == '=', self.case(c + 1, r) == '='
                    surface.blit(tuile(49 if gauche and droite else 48 if droite else 50 if gauche else 49, T), pos)
                elif ch in 'B?u':
                    surface.blit(tuile({'B': 26, '?': 10, 'u': 9}[ch], T), pos)
                elif ch == 'o':
                    surface.blit(tuile(151 + anim, T), pos)
                elif ch == '^':
                    surface.blit(tuile(68, T), pos)
                elif ch == 'S':
                    surface.blit(tuile(108, T), pos)
                elif ch == 'H':
                    surface.blit(tuile(44, T), pos)
                elif ch in 'Kk':
                    surface.blit(tuile(131, T), pos)
                    if ch == 'k':
                        surface.blit(tuile(111 + anim, T), (pos[0], pos[1] - T))
                elif ch == 'D':
                    surface.blit(tuile(150, T), pos)
                    surface.blit(tuile(130, T), (pos[0], pos[1] - T))
                elif ch in DECOR:
                    surface.blit(tuile(DECOR[ch], T), pos)
        for x, y, _t in self.bulles:
            surface.blit(tuile(151, T), (ox + int(x * T), oy + int(y * T)))
        P = T * 24 // 18
        for e in self.ennemis:
            if e.genre == 'F':
                i = 24 + anim
            elif e.genre == 'Z':
                i = 15 + anim
            else:
                i = 20 if e.mort else 18 + anim
            surface.blit(perso_pixel(i, P, e.vx > 0), (ox + int((e.x + e.w / 2) * T) - P // 2,
                                                   oy + int((e.y + e.h) * T) - P))
        j = self.j
        if not (self.invincible and int(self.t * 12) % 2):
            pose = 1 if (not j.au_sol or (abs(j.vx) > 0.5 and int(self.t * 8) % 2)) else 0
            surface.blit(perso_pixel(pose, P, self.face < 0), (ox + int((j.x + j.w / 2) * T) - P // 2,
                                                            oy + int((j.y + j.h) * T) - P + T // 9))
        # cœurs
        for i in range(self.vies):
            surface.blit(tuile(44, T), (zone.right - (i + 1) * (T + 2) - 8, zone.y + 40))
        surface.set_clip(ancien_clip)
        return None


# ----------------------------------------------------------------------
# COURSE (run and jump) : le personnage court tout seul, on saute.
class Course(Jeu):
    titre = 'Course'
    aide_jeu = [('A/C', 'Sauter (double saut en l\'air)'), ('Start', 'Pause')]
    THEMES = ('herbe', 'neige', 'desert')

    def __init__(self):
        self.score = 0
        self.pieces = 0
        self.ecrases = 0
        self.t = 0.0
        self.vitesse = 7.0
        self.sol = {}        # colonne -> hauteur du sol (0 = trou)
        self.objets = {}     # (colonne, ligne) -> code
        self.ennemis = []
        self.fin_generee = 0
        self.theme = THEMES['herbe']
        self._generer(0, 'depart')
        self.j = Corps(3.0, LIGNES - 3 - 1.1, 0.75, 1.05)
        self.cam = 0.0
        self.sauts = 0
        self.tampon = 0.0
        self.coyote = 0.0
        self.distance = 0.0

    # -- génération procédurale par tronçons
    def _generer(self, c0, genre=None):
        h = self.sol.get(c0 - 1, 3) or 3
        if genre is None:
            genre = random.choice(('plat', 'trou', 'trou', 'marche', 'pics', 'planches', 'ennemi', 'chauve'))
        difficulte = min(1.0, (self.vitesse - 7.0) / 6.0)

        def plat(n, hh):
            for i in range(n):
                self.sol[self.fin_generee + i] = hh
            self.fin_generee += n

        if genre == 'depart':
            plat(20, 3)
        elif genre == 'plat':
            n = random.randint(6, 12)
            debut = self.fin_generee
            plat(n, h)
            if random.random() < 0.6:
                for i in range(2, n - 2):
                    self.objets[(debut + i, LIGNES - h - 1)] = 'o'
        elif genre == 'trou':
            plat(4, h)
            n = random.randint(2, 3 + int(2 * difficulte))
            debut = self.fin_generee
            plat(n, 0)
            for i in range(n):
                self.objets[(debut + i, LIGNES - h - 3)] = 'o'
            h2 = max(2, min(5, h + random.choice((-1, 0, 0, 1))))
            plat(4, h2)
        elif genre == 'marche':
            h2 = max(2, min(6, h + random.choice((-2, -1, 1, 2))))
            plat(3, h)
            plat(random.randint(5, 9), h2)
        elif genre == 'pics':
            plat(5, h)
            n = random.randint(1, 2 + int(difficulte))
            for i in range(n):
                self.objets[(self.fin_generee + i, LIGNES - h - 1)] = '^'
            plat(n, h)
            plat(5, h)
        elif genre == 'planches':
            plat(3, h)
            n = random.randint(7, 9)
            debut = self.fin_generee
            plat(n, 0)
            for i in range(2, n - 2):
                self.objets[(debut + i, LIGNES - h - 2)] = '='
                self.objets[(debut + i, LIGNES - h - 3)] = 'o'
            plat(4, h)
        elif genre == 'ennemi':
            debut = self.fin_generee
            plat(10, h)
            e = Corps(debut + 7.1, LIGNES - h - 0.8, 0.8, 0.8)
            e.genre, e.vx, e.mort = 'E', -1.5, 0.0
            self.ennemis.append(e)
        elif genre == 'chauve':
            debut = self.fin_generee
            plat(10, h)
            e = Corps(debut + 7.1, LIGNES - h - 1.9, 0.8, 0.8)
            e.genre, e.vx, e.mort = 'F', -1.0, 0.0
            e.base_y = e.y
            self.ennemis.append(e)
            for i in range(3, 6):
                self.objets[(debut + i, LIGNES - h - 1)] = 'o'

    def solide(self, c, r):
        h = self.sol.get(c, 3)
        return bool(h) and r >= LIGNES - h

    def planche(self, c, r):
        return self.objets.get((c, r)) == '='

    def action(self, a):
        if a in ('face_a', 'face_x', 'face_y', 'up'):
            self.tampon = 0.15

    def update(self, dt):
        if self.over:
            return
        self.t += dt
        self.vitesse = min(13.0, 7.0 + self.t * 0.03)
        idx = int(self.t // 40) % len(self.THEMES)
        self.theme = THEMES[self.THEMES[idx]]
        while self.fin_generee < self.cam + 60:
            self._generer(self.fin_generee)
        while dt > 0 and not self.over:
            pas = min(dt, SOUS_PAS)
            dt -= pas
            self._pas(pas)
        self.score = int(self.distance) + self.pieces * 5 + self.ecrases * 10

    def _pas(self, dt):
        j = self.j
        self.cam += self.vitesse * dt
        # le coureur garde sa place (40 % de l'écran) ; bloqué par un mur, il recule à l'écran
        cible = self.cam + 6.0
        j.vx = self.vitesse + max(-2.0, min(2.0, (cible - j.x) * 2))
        self.coyote = 0.1 if j.au_sol else max(0.0, self.coyote - dt)
        if j.au_sol:
            self.sauts = 0
        self.tampon = max(0.0, self.tampon - dt)
        if self.tampon > 0 and (self.coyote > 0 or self.sauts < 2):
            j.vy = -SAUT if self.coyote > 0 else -SAUT * 0.85
            self.sauts = 1 if self.coyote > 0 else 2
            self.tampon = self.coyote = 0.0
        if j.vy < -6 and not (self.tenu[2] & {'face_a', 'face_x', 'face_y'}):
            j.vy = -6.0
        j.vy = min(CHUTE_MAX, j.vy + GRAVITE * dt)
        deplacer(j, dt, self.solide, self.planche)
        self.distance = max(self.distance, j.x)
        if j.y > LIGNES + 1 or j.x < self.cam - 0.5:
            self.over = True
            return
        for r in range(int(j.y), int(j.y + j.h) + 1):
            for c in range(int(j.x), int(j.x + j.w) + 1):
                ch = self.objets.get((c, r))
                if ch == 'o':
                    del self.objets[(c, r)]
                    self.pieces += 1
                elif ch == '^' and j.y + j.h > r + 0.55 and j.x + j.w - 0.2 > c and j.x + 0.2 < c + 1:
                    self.over = True
                    return
        for e in self.ennemis:
            if e.mort:
                e.mort -= dt
                e.fini = e.mort <= 0
                continue
            e.x += e.vx * dt
            if e.genre == 'F':
                e.y = e.base_y + 0.7 * math.sin(self.t * 3 + e.x)
            if j.touche(e, 0.08):
                if j.vy > 0 and j.y + j.h - e.y < 0.55:
                    e.mort = 0.4
                    self.ecrases += 1
                    j.vy = -REBOND
                    self.sauts = 1
                else:
                    self.over = True
                    return
        self.ennemis = [e for e in self.ennemis if e.x > self.cam - 5 and not getattr(e, 'fini', False)]
        if len(self.objets) > 400:
            self.objets = {k: v for k, v in self.objets.items() if k[0] > self.cam - 5}

    def infos(self):
        return [('Score', self.score), ('Distance', '{} m'.format(int(self.distance))), ('Pièces', self.pieces)]

    def draw(self, surface, zone, fonts):
        T = max(18, zone.height // LIGNES)
        vue = zone.width / T
        ox = zone.x - int(self.cam * T)
        oy = zone.y + (zone.height - T * LIGNES)
        ancien_clip = surface.get_clip()
        surface.set_clip(zone)
        Plateforme._fond(self, surface, zone, T)
        haut = self.theme['haut']
        anim = int(self.t * 4) % 2
        g = int(self.cam)
        for c in range(g, g + int(vue) + 2):
            h = self.sol.get(c, 3)
            for r in range(LIGNES - h, LIGNES) if h else ():
                if r == LIGNES - h:
                    hg, hd = self.sol.get(c - 1, 3), self.sol.get(c + 1, 3)
                    gauche, droite = hg >= h, hd >= h
                    i = haut[1] if gauche and droite else haut[0] if droite else haut[2] if gauche else haut[3]
                else:
                    i = DEDANS[(c * 7 + r * 3) % 4]
                surface.blit(tuile(i, T), (ox + c * T, oy + r * T))
        for (c, r), ch in self.objets.items():
            if g - 1 <= c <= g + vue + 1:
                i = {'o': 151 + anim, '^': 68, '=': 49}[ch]
                surface.blit(tuile(i, T), (ox + c * T, oy + r * T))
        P = T * 24 // 18
        for e in self.ennemis:
            i = (24 + anim) if e.genre == 'F' else (20 if e.mort else 18 + anim)
            surface.blit(perso_pixel(i, P), (ox + int((e.x + e.w / 2) * T) - P // 2, oy + int((e.y + e.h) * T) - P))
        j = self.j
        pose = 1 if (not j.au_sol or int(self.t * 10) % 2) else 0
        surface.blit(perso_pixel(pose, P), (ox + int((j.x + j.w / 2) * T) - P // 2, oy + int((j.y + j.h) * T) - P + T // 9))
        surface.set_clip(ancien_clip)
        return None


# ----------------------------------------------------------------------
# BAGARRE (beat them all) : vagues d'adversaires dans une rue qui défile.
# Coordonnées « monde » en pixels de référence (hauteur de zone 560), mises à
# l'échelle au dessin. y = profondeur (position des pieds sur le trottoir).
REF_H = 560.0
SOL_HAUT, SOL_BAS = 330.0, 540.0     # bande où l'on peut marcher


class Combattant:
    def __init__(self, perso, x, y, pv, vitesse, degats):
        self.perso = perso
        self.x, self.y, self.z = x, y, 0.0   # z = hauteur du saut
        self.vz = 0.0
        self.pv = self.pv_max = pv
        self.vitesse = vitesse
        self.degats = degats
        self.face = 1
        self.etat = 'idle'   # idle, marche, attaque, touche, sol, ko, saut
        self.minuteur = 0.0
        self.pose = 'idle'
        self.recul = 0.0
        self.combo = 0
        self.coup_porte = False
        self.attente = random.uniform(0.6, 1.4)
        self.t = 0.0

    def libre(self):
        return self.etat in ('idle', 'marche')


ENNEMIS_BAGARRE = {
    'zombie': dict(pv=40, vitesse=70, degats=7, points=10),
    'passant': dict(pv=30, vitesse=120, degats=5, points=10),
    'robot': dict(pv=70, vitesse=60, degats=11, points=20),
}


class Bagarre(Jeu):
    titre = 'Bagarre'
    aide_jeu = [('◄►▲▼', 'Se déplacer'), ('A', 'Coup de poing'), ('B', 'Coup de pied'),
                ('C', 'Sauter'), ('Start', 'Pause')]
    ECRAN_W = 900.0   # largeur de référence ajustée au dessin

    def __init__(self):
        self.score = 0
        self.ko = 0
        self.vague = 0
        self.t = 0.0
        self.j = Combattant('aventuriere', 150, 440, 100, 210, 0)
        self.ennemis = []
        self.cam = 0.0
        self.arene = 0.0          # x gauche de l'arène verrouillée
        self.a_venir = []         # ennemis de la vague pas encore entrés
        self.go = 0.0             # affichage « GO → »
        self.etat_vague = 'combat'
        self._vague_suivante()

    def _vague_suivante(self):
        self.vague += 1
        n = 2 + self.vague
        types = ['zombie', 'passant'] + (['robot'] if self.vague >= 3 else [])
        self.a_venir = [random.choice(types) for _ in range(n)]
        self.etat_vague = 'combat'
        self.arene = self.cam

    def _entrer(self, perso):
        c = ENNEMIS_BAGARRE[perso]
        bonus = 1 + 0.08 * (self.vague - 1)
        cote = random.choice((-1, 1))
        x = self.arene + (self.ECRAN_W + 80 if cote > 0 else -80)
        e = Combattant(perso, x, random.uniform(SOL_HAUT + 20, SOL_BAS - 10),
                       int(c['pv'] * bonus), c['vitesse'] * min(1.5, bonus), int(c['degats'] * bonus))
        e.points = c['points']
        self.ennemis.append(e)

    # -- commandes
    def action(self, a):
        j = self.j
        if j.etat in ('ko', 'sol', 'touche'):
            return
        if a == 'face_a':
            if j.etat == 'saut':
                self._attaque(j, 'kick', 0.35, 16, renverse=True)
            elif j.etat == 'attaque' and j.pose.startswith('attack') and j.minuteur < 0.12 and j.combo < 3:
                j.combo += 1
                self._attaque(j, 'attack{}'.format(j.combo - 1), 0.25, 14 if j.combo == 3 else 8,
                              renverse=j.combo == 3, combo=j.combo)
            elif j.libre():
                self._attaque(j, 'attack0', 0.25, 8, combo=1)
        elif a == 'face_b':
            if j.etat == 'saut':
                self._attaque(j, 'kick', 0.35, 18, renverse=True)
            elif j.libre():
                self._attaque(j, 'attackKick', 0.4, 15, renverse=True)
        elif a in ('face_x', 'face_y') and j.libre():
            j.etat = 'saut'
            j.vz = 520.0

    def _attaque(self, c, pose, duree, degats, renverse=False, combo=0):
        if c.etat != 'saut':
            c.etat = 'attaque'
        c.pose = pose
        c.minuteur = duree
        c.coup_porte = False
        c.degats_coup = degats
        c.renverse = renverse
        if combo:
            c.combo = combo

    def _toucher(self, attaquant, cibles):
        """Applique le coup d'attaquant aux cibles à portée (devant lui, même profondeur)."""
        for c in cibles:
            if c.etat in ('ko', 'sol'):
                continue
            dx = (c.x - attaquant.x) * attaquant.face
            if 20 < dx < 115 and abs(c.y - attaquant.y) < 34 and abs(c.z - attaquant.z) < 90:
                c.pv -= attaquant.degats_coup
                c.face = -attaquant.face
                if c.pv <= 0:
                    c.etat, c.pose, c.minuteur = 'ko', 'down', 1.4
                    c.recul = 260.0 * attaquant.face
                    if c is not self.j:
                        self.score += c.points
                        self.ko += 1
                elif attaquant.renverse:
                    c.etat, c.pose, c.minuteur = 'sol', 'down', 1.0
                    c.recul = 240.0 * attaquant.face
                else:
                    c.etat, c.pose, c.minuteur = 'touche', 'hit', 0.3
                    c.recul = 90.0 * attaquant.face
                attaquant.coup_porte = True

    # -- simulation
    def update(self, dt):
        if self.over:
            return
        self.t += dt
        self.go = max(0.0, self.go - dt)
        self._joueur(dt)
        for e in self.ennemis:
            self._ennemi(e, dt)
        self.ennemis = [e for e in self.ennemis if not (e.etat == 'ko' and e.minuteur <= 0)]
        if self.etat_vague == 'combat':
            actifs = [e for e in self.ennemis if e.etat != 'ko']
            if self.a_venir and len(actifs) < min(3, 1 + self.vague // 2 + 1):
                self._entrer(self.a_venir.pop())
            elif not self.a_venir and not self.ennemis:
                self.etat_vague = 'avance'
                self.score += 25 * self.vague
                self.j.pv = min(self.j.pv_max, self.j.pv + 25)
                self.go = 3.0
        else:
            # avancer : la caméra suit le joueur jusqu'à la zone suivante
            self.cam = max(self.cam, min(self.j.x - self.ECRAN_W * 0.4, self.arene + 700))
            if self.cam >= self.arene + 700:
                self._vague_suivante()

    def _bornes(self, c, marge=40):
        """Le joueur reste à l'écran (la caméra est fixe pendant une vague)."""
        c.y = max(SOL_HAUT, min(SOL_BAS, c.y))
        c.x = max(self.cam + marge, min(self.cam + self.ECRAN_W - marge, c.x))

    def _commun(self, c, dt):
        c.t += dt
        if c.recul:
            c.x += c.recul * dt
            c.recul *= max(0.0, 1 - 6 * dt)
            if abs(c.recul) < 5:
                c.recul = 0.0
        if c.etat == 'saut' or c.z > 0:
            c.vz -= 1500.0 * dt
            c.z = max(0.0, c.z + c.vz * dt)
            if c.z == 0 and c.vz < 0:
                c.vz = 0.0
                if c.etat == 'saut' or (c.etat == 'attaque' and c.pose == 'kick'):
                    c.etat, c.pose = 'idle', 'idle'
        if c.minuteur > 0:
            c.minuteur -= dt
            if c.minuteur <= 0:
                if c.etat in ('attaque', 'touche'):
                    c.etat, c.pose = ('saut', 'fall') if c.z > 0 else ('idle', 'idle')
                elif c.etat == 'sol':
                    c.etat, c.pose = 'idle', 'idle'

    def _joueur(self, dt):
        j = self.j
        self._commun(j, dt)
        if j.etat == 'ko':
            if j.minuteur <= 0.3:
                self.over = True
            return
        dx, dy, _b = self.tenu
        if j.libre() or j.etat == 'saut':
            j.x += dx * j.vitesse * dt
            if j.etat != 'saut':
                j.y += dy * j.vitesse * 0.6 * dt
            if dx:
                j.face = dx
            if j.etat != 'saut':
                j.etat = 'marche' if (dx or dy) else 'idle'
                j.pose = 'walk{}'.format(int(j.t * 12) % 8) if (dx or dy) else 'idle'
            elif j.pose != 'kick':
                j.pose = 'jump' if j.vz > 0 else 'fall'
        if (j.etat == 'attaque' or (j.etat == 'saut' and j.pose == 'kick')) and not j.coup_porte:
            self._toucher(j, self.ennemis)
        self._bornes(j)

    def _ennemi(self, e, dt):
        self._commun(e, dt)
        if e.etat == 'ko':
            return
        j = self.j
        if e.etat == 'attaque' and not e.coup_porte and e.minuteur < 0.2 and j.etat != 'ko':
            e.degats_coup, e.renverse = e.degats, False
            self._toucher(e, [j])
            if j.etat == 'ko':
                j.minuteur = 1.8
        if not e.libre():
            return
        # se placer à côté du joueur, à sa profondeur, puis frapper
        cote = 1 if e.x > j.x else -1
        cible_x, cible_y = j.x + cote * 85, j.y
        ddx, ddy = cible_x - e.x, cible_y - e.y
        e.attente -= dt
        if abs(ddx) < 14 and abs(ddy) < 12:
            e.face = -cote
            e.etat, e.pose = 'idle', 'idle'
            if e.attente <= 0 and j.etat not in ('ko',) and j.z < 40:
                self._attaque(e, 'attack0' if e.perso != 'robot' else 'attack1', 0.45, e.degats)
                e.attente = random.uniform(0.9, 1.8) / (1 + 0.05 * self.vague)
        else:
            n = math.hypot(ddx, ddy) or 1
            e.x += ddx / n * e.vitesse * dt
            e.y += ddy / n * e.vitesse * 0.7 * dt
            e.face = 1 if ddx > 0 else -1
            e.etat = 'marche'
            e.pose = 'walk{}'.format(int(e.t * 10) % 8)
        e.y = max(SOL_HAUT, min(SOL_BAS, e.y))

    def infos(self):
        return [('Score', self.score), ('Adversaires KO', self.ko), ('Vague', self.vague)]

    # -- dessin
    def _decor(self, surface, zone, k):
        ciel_h = int(SOL_HAUT * k) - int(70 * k)
        for i in range(0, ciel_h, 6):
            f = i / max(1, ciel_h)
            pygame.draw.rect(surface, (int(40 + 120 * f), int(60 + 100 * f), int(130 + 80 * f)),
                             (zone.x, zone.y + i, zone.width, 6))
        # immeubles (parallaxe), générés de façon stable par leur index
        dec = self.cam * 0.5
        larg = 160
        premier = int(dec // larg) - 1
        for n in range(premier, premier + int(zone.width / (larg * k)) + 3):
            rnd = random.Random(n * 7919)
            h = rnd.randint(140, 300)
            coul = rnd.choice(((70, 80, 110), (90, 70, 90), (60, 90, 100), (100, 90, 80)))
            x = zone.x + int((n * larg - dec) * k)
            r = pygame.Rect(x, zone.y + ciel_h - int(h * k), int((larg - 12) * k), int(h * k))
            pygame.draw.rect(surface, coul, r)
            for wy in range(r.y + int(14 * k), r.bottom - int(20 * k), int(30 * k)):
                for wx in range(r.x + int(12 * k), r.right - int(20 * k), int(30 * k)):
                    allume = rnd.random() < 0.35
                    pygame.draw.rect(surface, (250, 220, 120) if allume else (40, 45, 60), (wx, wy, int(14 * k), int(18 * k)))
        # trottoir et chaussée
        y_trott = zone.y + ciel_h
        pygame.draw.rect(surface, (150, 150, 160), (zone.x, y_trott, zone.width, int(70 * k)))
        pygame.draw.rect(surface, (70, 72, 80), (zone.x, y_trott + int(70 * k), zone.width, zone.bottom - y_trott))
        dec2 = int(self.cam * k) % int(120 * k)
        for x in range(zone.x - dec2, zone.right, int(120 * k)):
            pygame.draw.line(surface, (120, 120, 130), (x, y_trott), (x, y_trott + int(70 * k)), 2)
            pygame.draw.rect(surface, (220, 220, 220), (x, zone.y + int(470 * k), int(60 * k), int(8 * k)))

    def draw(self, surface, zone, fonts):
        k = zone.height / REF_H
        self.ECRAN_W = zone.width / k
        ancien_clip = surface.get_clip()
        surface.set_clip(zone)
        self._decor(surface, zone, k)
        tous = sorted(self.ennemis + [self.j], key=lambda c: c.y)
        echelle = 1.1 * k
        for c in tous:
            sx = zone.x + int((c.x - self.cam) * k)
            sy = zone.y + int(c.y * k)
            pygame.draw.ellipse(surface, (40, 40, 45), (sx - int(32 * k), sy - int(8 * k), int(64 * k), int(16 * k)))
            if c.etat == 'ko' and c.minuteur < 0.8 and int(c.minuteur * 10) % 2:
                continue
            img = toon(c.perso, c.pose, echelle, c.face < 0)
            surface.blit(img, (sx - img.get_width() // 2, sy - img.get_height() + int(6 * k) - int(c.z * k)))
            if c is not self.j and c.etat != 'ko':
                w = int(60 * k)
                pygame.draw.rect(surface, (60, 0, 0), (sx - w // 2, sy - int(155 * k) - int(c.z * k), w, 6))
                pygame.draw.rect(surface, (230, 60, 60), (sx - w // 2, sy - int(155 * k) - int(c.z * k),
                                                          int(w * max(0, c.pv) / c.pv_max), 6))
        # vie du joueur
        w = int(260 * k)
        x, y = zone.x + 14, zone.y + 44
        pygame.draw.rect(surface, (30, 30, 30), (x - 2, y - 2, w + 4, 18))
        pygame.draw.rect(surface, (40, 200, 90), (x, y, int(w * max(0, self.j.pv) / self.j.pv_max), 14))
        if self.go and int(self.t * 3) % 2:
            txt = 'EN AVANT  →'
            r = fonts.large.get_rect(txt)
            fonts.large.render_to(surface, (zone.right - r.width - 30, zone.y + 90), txt, JAUNE)
        surface.set_clip(ancien_clip)
        return None
