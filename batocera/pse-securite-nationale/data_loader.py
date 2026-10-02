"""Chargement des données de révision (modules.json, quizz/, flashcard/) et de la
configuration propre à chaque jeu (jeu.json : titre, libellés des séries)."""
import csv
import json
import os

GAME_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(GAME_DIR, 'data')


def load_config():
    """Configuration du jeu (jeu.json à côté du .pygame) : un même moteur est
    déployé une fois par dépôt thématique, seul ce fichier les distingue.
    Valeurs par défaut si le fichier est absent ou illisible."""
    config = {'titre': 'Révision', 'series': {}}
    try:
        with open(os.path.join(GAME_DIR, 'jeu.json'), encoding='utf-8') as f:
            config.update(json.load(f))
    except (OSError, ValueError):
        pass
    return config


def base_name(csv_filename):
    """'09-570 PSE-ER F6-7 ToIP et convergence....csv' -> '09-570 PSE-ER F6-7 ToIP et convergence....'"""
    return csv_filename[:-4] if csv_filename.lower().endswith('.csv') else csv_filename


def load_series():
    """Retourne une liste de séries triées : [(code_serie, [modules...]), ...]
    Chaque module est un dict {code, numero, titre, base}.
    """
    with open(os.path.join(DATA_DIR, 'modules.json'), encoding='utf-8') as f:
        entries = json.load(f)

    series = {}
    for entry in entries:
        base = base_name(entry)
        numero, _, titre = base.partition(' ')
        code = numero.split('-')[0]
        titre = titre.strip()
        series.setdefault(code, []).append({
            'code': code,
            'numero': numero,
            'titre': titre,
            'base': base,
        })

    def sort_key(m):
        parts = m['numero'].split('-')
        try:
            return (parts[0], int(parts[1]))
        except (IndexError, ValueError):
            return (parts[0], 0)

    for code in series:
        series[code].sort(key=sort_key)

    return sorted(series.items(), key=lambda kv: kv[0])


def load_quiz(base, max_questions=15):
    """Charge et renvoie une liste de questions mélangées pour le module `base`.
    Chaque question : {question, choix:[4], index_correct(0-3), explication}.
    """
    path = os.path.join(DATA_DIR, 'quizz', base + '.csv')
    questions = []
    if not os.path.exists(path):
        return questions
    with open(path, encoding='utf-8') as f:
        for row_index, row in enumerate(csv.reader(f, delimiter=';')):
            if len(row) < 7:
                continue
            question, c1, c2, c3, c4, idx, expl = row[0], row[1], row[2], row[3], row[4], row[5], row[6]
            try:
                correct = int(idx) - 2  # colonne 2..5 -> index 0..3
            except ValueError:
                continue
            questions.append({
                'id': row_index,  # stable (position dans le CSV, avant mélange) : sert de clé de cache TTS
                'question': question,
                'choix': [c1, c2, c3, c4],
                'correct': correct,
                'explication': expl,
            })
    import random
    random.shuffle(questions)
    return questions[:max_questions]


def load_flashcards(base):
    """Charge les flashcards du module `base` : liste de {recto, verso}."""
    path = os.path.join(DATA_DIR, 'flashcard', base + '.csv')
    cards = []
    if not os.path.exists(path):
        return cards
    with open(path, encoding='utf-8') as f:
        for row in csv.reader(f):
            if len(row) < 2:
                continue
            cards.append({'recto': row[0], 'verso': row[1]})
    return cards


def chanson_path(base):
    """Chemin du fichier chanson (mp3) du module, ou None si absent."""
    path = os.path.join(DATA_DIR, 'chanson', base + '.mp3')
    return path if os.path.exists(path) else None


# Deux sources par module pour le podcast et l'infographie, comme le sélecteur
# « Pipeline local / NotebookLM » de la page web : la source préférée (réglages)
# est lue en priorité, l'autre sert de repli si la première manque.
SOURCES = ('local', 'nlm')
SOURCE_LIBELLES = {'local': 'Pipeline local', 'nlm': 'NotebookLM'}
DOSSIERS_SOURCE = {
    'podcast': {'local': 'podcast', 'nlm': 'podcast_nlm'},
    'infographie': {'local': 'infographie', 'nlm': 'infographie_nlm'},
}
EXTENSIONS = {'podcast': '.mp3', 'infographie': '.png'}
source_preferee = 'local'


def autre_source(source):
    return 'nlm' if source == 'local' else 'local'


def media_source(kind, base, source=None):
    """(chemin, source effective) du podcast ou de l'infographie : la source
    demandée (par défaut la préférée), sinon l'autre, ou (None, None)."""
    voulue = source or source_preferee
    for src in (voulue, autre_source(voulue)):
        path = os.path.join(DATA_DIR, DOSSIERS_SOURCE[kind][src], base + EXTENSIONS[kind])
        if os.path.exists(path):
            return path, src
    return None, None


def sources_disponibles(kind, base):
    """Sources présentes pour ce module (0, 1 ou 2), dans l'ordre local, NotebookLM."""
    return [src for src in SOURCES
            if os.path.exists(os.path.join(DATA_DIR, DOSSIERS_SOURCE[kind][src], base + EXTENSIONS[kind]))]


def podcast_path(base):
    """Chemin du podcast (mp3 ; SDL_mixer sur Batocera ne décode pas l'AAC/m4a) dans
    la source préférée (podcast/ ou podcast_nlm/), sinon dans l'autre, ou None."""
    return media_source('podcast', base)[0]


def podcast_court_path(base):
    """Chemin de la micro-chronique « l'essentiel en 3 min » (mp3), ou None si absente."""
    path = os.path.join(DATA_DIR, 'podcast_court', base + '.mp3')
    return path if os.path.exists(path) else None


def icone_path(base):
    """Chemin de l'icône pixel art (png 512x512) du module, ou None si absente."""
    path = os.path.join(DATA_DIR, 'icone', base + '.png')
    return path if os.path.exists(path) else None


def infographie_path(base):
    """Chemin de l'infographie (png) dans la source préférée (infographie/ ou
    infographie_nlm/), sinon dans l'autre, ou None si absente."""
    return media_source('infographie', base)[0]


def paroles_chanson(base):
    """Paroles de la chanson du module (chanson/<module>.txt), ou None."""
    path = os.path.join(DATA_DIR, 'chanson', base + '.txt')
    try:
        with open(path, encoding='utf-8') as f:
            return f.read().strip() or None
    except OSError:
        return None


def load_lexique():
    """Lexique du dépôt (data/lexique.json, produit par scripts/lexique.py, le même
    que l'onglet Lexique de la page web) : {'modules': [base...], 'entrees': [...]},
    chaque entrée {t: terme, s: sigle, x: forme développée, d: [[définition, index module]]}.
    None si absent ou illisible."""
    try:
        with open(os.path.join(DATA_DIR, 'lexique.json'), encoding='utf-8') as f:
            lex = json.load(f)
    except (OSError, ValueError):
        return None
    lex['modules'] = [base_name(m) for m in lex.get('modules', [])]
    lex['entrees'] = [e for e in lex.get('entrees', []) if e.get('t') and e.get('d')]
    return lex if lex['entrees'] else None


PREFS_PATH = os.path.join(GAME_DIR, 'preferences.json')


def load_prefs():
    """Réglages mémorisés entre deux parties (temps de réflexion, source des médias)."""
    try:
        with open(PREFS_PATH, encoding='utf-8') as f:
            prefs = json.load(f)
            return prefs if isinstance(prefs, dict) else {}
    except (OSError, ValueError):
        return {}


def save_prefs(prefs):
    try:
        with open(PREFS_PATH, 'w', encoding='utf-8') as f:
            json.dump(prefs, f)
    except OSError:
        pass


def fiche_path(base):
    """Chemin de la fiche de révision (txt) du module, ou None si absente."""
    path = os.path.join(DATA_DIR, 'fiche', base + '.txt')
    return path if os.path.exists(path) else None


def tp_path(base):
    """Chemin du fichier de TP (csv « titre;énoncé;corrigé ») du module, ou None si absent."""
    path = os.path.join(DATA_DIR, 'tp', base + '.csv')
    return path if os.path.exists(path) else None


def load_tp(base):
    """Exercices de TP du module : liste de {titre, enonce, solution}, dans l'ordre du fichier."""
    path = tp_path(base)
    if path is None:
        return []
    exercices = []
    with open(path, encoding='utf-8') as f:
        for row in csv.reader(f, delimiter=';'):
            if len(row) >= 3 and row[0].strip() and row[1].strip():
                exercices.append({'titre': row[0].strip(), 'enonce': row[1].strip(), 'solution': row[2].strip()})
    return exercices


def load_fiche(base):
    """Charge le texte complet de la fiche de révision du module, ou None si absente."""
    path = fiche_path(base)
    if path is None:
        return None
    with open(path, encoding='utf-8') as f:
        return f.read()


def fiche_audio_path(base):
    """Chemin de la narration audio (mp3) de la fiche de révision du module,
    ou None si absente. Fichier long (plusieurs dizaines de minutes possible)
    pré-généré à l'avance et streamé via pygame.mixer.music - jamais généré à
    la volée (bien trop long pour ça)."""
    path = os.path.join(DATA_DIR, 'fiche_audio', base + '.mp3')
    return path if os.path.exists(path) else None
