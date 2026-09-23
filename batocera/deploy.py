#!/usr/bin/env python3
"""Déploie le jeu Batocera de ce dépôt thématique vers une ou plusieurs
machines Batocera (partage SMB, via gio).

1. Assemble batocera/<dépôt>/data/ à partir des dossiers du dépôt (liens
   physiques : aucun espace disque en plus, rien de versionné en double) :
   modules.json, fiche/, quizz/, flashcard/, fiche_audio/, infographie/,
   chanson/*.mp3, et podcast/ converti en mp3 (SDL_mixer sur Batocera ne
   décode pas l'AAC/m4a de NotebookLM ; conversion faite une seule fois et
   conservée dans batocera/podcast_mp3/).
2. Copie le dossier du jeu vers smb://<hôte>/share/roms/pygame/<dépôt>/, en
   n'envoyant que les fichiers absents ou de taille différente côté distant.
3. Ajoute l'entrée du jeu (nom + vignette) dans le gamelist.xml pygame
   distant si elle n'y est pas encore (sauvegarde gamelist.xml.bak avant).

Usage : python3 deploy.py [hôte ...]      (défaut : HOSTS ci-dessous)
        python3 deploy.py --build-only    (assemble data/ sans rien envoyer)
"""
import json
import os
import shutil
import subprocess
import sys
from urllib.parse import quote

HOSTS = ['192.168.1.47', 'batocerasalon.local']

BATOCERA_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(BATOCERA_DIR)
REPO_NAME = os.path.basename(REPO_DIR)
GAME_DIR = os.path.join(BATOCERA_DIR, REPO_NAME)
DATA_DIR = os.path.join(GAME_DIR, 'data')
PODCAST_MP3_DIR = os.path.join(BATOCERA_DIR, 'podcast_mp3')
THUMB = os.path.join(BATOCERA_DIR, 'vignette.png')

# (dossier source dans le dépôt, extensions retenues)
DATA_SOURCES = [
    ('fiche', ('.txt',)), ('quizz', ('.csv',)), ('flashcard', ('.csv',)),
    ('fiche_audio', ('.mp3',)), ('infographie', ('.png',)), ('chanson', ('.mp3',)),
]


def link_or_copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        os.remove(dst)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def build_data():
    if os.path.isdir(DATA_DIR):
        shutil.rmtree(DATA_DIR)
    os.makedirs(DATA_DIR)
    link_or_copy(os.path.join(REPO_DIR, 'modules.json'), os.path.join(DATA_DIR, 'modules.json'))
    count = 0
    for folder, exts in DATA_SOURCES:
        src_dir = os.path.join(REPO_DIR, folder)
        if not os.path.isdir(src_dir):
            continue
        for name in os.listdir(src_dir):
            if name.endswith(exts):
                link_or_copy(os.path.join(src_dir, name), os.path.join(DATA_DIR, folder, name))
                count += 1
    podcast_dir = os.path.join(REPO_DIR, 'podcast')
    if os.path.isdir(podcast_dir):
        os.makedirs(PODCAST_MP3_DIR, exist_ok=True)
        for name in sorted(os.listdir(podcast_dir)):
            if not name.endswith('.m4a'):
                continue
            mp3 = os.path.join(PODCAST_MP3_DIR, name[:-4] + '.mp3')
            if not os.path.exists(mp3):
                print('conversion mp3 :', name, flush=True)
                tmp = mp3 + '.tmp.mp3'
                subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-i',
                                os.path.join(podcast_dir, name), '-codec:a', 'libmp3lame',
                                '-qscale:a', '4', tmp], check=True)
                os.replace(tmp, mp3)
            link_or_copy(mp3, os.path.join(DATA_DIR, 'podcast', name[:-4] + '.mp3'))
            count += 1
    print('data/ assemblé : {} fichiers'.format(count), flush=True)


def smb_url(host, rel=''):
    base = 'smb://{}/share/roms/pygame/'.format(host)
    return base + '/'.join(quote(p) for p in rel.split('/') if p)


def remote_sizes(url):
    """{nom: taille} des fichiers d'un dossier distant ({} s'il n'existe pas)."""
    # Format de sortie de gio list : « nom<TAB>taille<TAB>(type) ».
    proc = subprocess.run(['gio', 'list', '-l', url], capture_output=True, text=True)
    sizes = {}
    for line in proc.stdout.splitlines():
        parts = line.split('\t')
        if len(parts) >= 2 and parts[1].isdigit():
            sizes[parts[0]] = int(parts[1])
    return sizes


def deploy(host):
    print('=== {} → {} ==='.format(REPO_NAME, smb_url(host, REPO_NAME)), flush=True)
    sent = skipped = failed = 0
    for root, dirs, files in os.walk(GAME_DIR):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        rel_dir = os.path.relpath(root, BATOCERA_DIR)
        url_dir = smb_url(host, rel_dir)
        subprocess.run(['gio', 'mkdir', '-p', url_dir], capture_output=True)
        existing = remote_sizes(url_dir)
        for name in files:
            path = os.path.join(root, name)
            if existing.get(name) == os.path.getsize(path):
                skipped += 1
                continue
            proc = subprocess.run(['gio', 'copy', path, url_dir + '/' + quote(name)],
                                  capture_output=True, text=True)
            if proc.returncode == 0:
                sent += 1
            else:
                failed += 1
                print('ÉCHEC {} : {}'.format(os.path.join(rel_dir, name), proc.stderr.strip()), flush=True)
    print('envoyés {}, inchangés {}, échecs {}'.format(sent, skipped, failed), flush=True)
    register_gamelist(host)
    return failed == 0


def register_gamelist(host):
    config = json.load(open(os.path.join(GAME_DIR, 'jeu.json'), encoding='utf-8'))
    game_path = './{0}/{0}.pygame'.format(REPO_NAME)
    url = smb_url(host, 'gamelist.xml')
    proc = subprocess.run(['gio', 'cat', url], capture_output=True, text=True)
    if proc.returncode != 0:
        print('gamelist.xml illisible, entrée non ajoutée', flush=True)
        return
    xml = proc.stdout
    if game_path in xml:
        return
    if os.path.exists(THUMB):
        subprocess.run(['gio', 'copy', THUMB, smb_url(host, 'images/{}.png'.format(REPO_NAME))],
                       capture_output=True)
    entry = ('\t<game>\n\t\t<path>{}</path>\n\t\t<name>{}</name>\n\t\t<desc>{}</desc>\n'
             '\t\t<image>./images/{}.png</image>\n\t\t<developer>guiraudjb</developer>\n'
             '\t\t<genre>Quiz</genre>\n\t\t<players>1</players>\n\t\t<lang>fr</lang>\n\t</game>\n'
             ).format(game_path, config['titre'], config.get('description', ''), REPO_NAME)
    subprocess.run(['gio', 'save', smb_url(host, 'gamelist.xml.bak')], input=xml, text=True)
    new_xml = xml.replace('</gameList>', entry + '</gameList>')
    subprocess.run(['gio', 'save', url], input=new_xml, text=True, check=True)
    print('entrée ajoutée au gamelist.xml', flush=True)


def main():
    args = sys.argv[1:]
    build_data()
    if '--build-only' in args:
        return
    hosts = [a for a in args if not a.startswith('--')] or HOSTS
    ok = all([deploy(h) for h in hosts])
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
