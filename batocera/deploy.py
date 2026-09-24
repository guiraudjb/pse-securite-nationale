#!/usr/bin/env python3
"""Déploie le jeu Batocera de ce dépôt thématique vers une ou plusieurs
machines Batocera (partage SMB, via gio).

Le dossier batocera/<dépôt>/ contient DÉJÀ tout ce dont le jeu a besoin
(code, data/ = contenus des modules, tts_assets/cache/ = audio des QCM et
flashcards) : c'est aussi la source unique lue par la page web. Rien n'est
assemblé ni copié localement.

1. Vérifie data/podcast/ : un podcast NotebookLM déposé en .m4a est converti
   en .mp3 (SDL_mixer sur Batocera ne décode pas l'AAC) puis le .m4a est
   supprimé — un seul format, lu par le jeu et par la page web.
2. Copie le dossier du jeu vers smb://<hôte>/share/roms/pygame/<dépôt>/, en
   n'envoyant que les fichiers absents ou de taille différente côté distant.
3. Ajoute l'entrée du jeu (nom + vignette) dans le gamelist.xml pygame
   distant si elle n'y est pas encore (sauvegarde gamelist.xml.bak avant).

Usage : python3 deploy.py [hôte ...]      (défaut : HOSTS ci-dessous)
        python3 deploy.py --build-only    (conversion des podcasts seulement)
"""
import json
import os
import subprocess
import sys
from urllib.parse import quote

HOSTS = ['192.168.1.47', 'batocerasalon.local']

BATOCERA_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(BATOCERA_DIR)
REPO_NAME = os.path.basename(REPO_DIR)
GAME_DIR = os.path.join(BATOCERA_DIR, REPO_NAME)
DATA_DIR = os.path.join(GAME_DIR, 'data')
THUMB = os.path.join(BATOCERA_DIR, 'vignette.png')


def convert_podcasts():
    """Convertit en mp3 les podcasts restés en .m4a dans data/podcast/."""
    podcast_dir = os.path.join(DATA_DIR, 'podcast')
    if not os.path.isdir(podcast_dir):
        return
    for name in sorted(os.listdir(podcast_dir)):
        if not name.endswith('.m4a'):
            continue
        src = os.path.join(podcast_dir, name)
        mp3 = src[:-4] + '.mp3'
        print('conversion mp3 :', name, flush=True)
        tmp = mp3 + '.tmp.mp3'
        subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-i', src,
                        '-codec:a', 'libmp3lame', '-qscale:a', '4', tmp], check=True)
        os.replace(tmp, mp3)
        os.remove(src)


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
    convert_podcasts()
    if '--build-only' in args:
        return
    hosts = [a for a in args if not a.startswith('--')] or HOSTS
    ok = all([deploy(h) for h in hosts])
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
