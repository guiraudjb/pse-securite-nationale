#!/usr/bin/env python3
"""Pré-génère la narration audio des fiches de révision via VoiceStudio local,
dans batocera/<dépôt>/data/fiche_audio/ (lue aussi par la page web), lue en jeu via dl.fiche_audio_path() (voir
data_loader.py) et pygame.mixer.music (streaming, pas pygame.mixer.Sound :
ces fichiers sont bien trop longs pour tenir chargés entièrement en mémoire
comme le quiz/flashcard).

Nécessite VoiceStudio démarré (http://127.0.0.1:3900) ET ffmpeg (conversion
WAV->MP3 après génération, pour une taille raisonnable : une narration de
20-30 min en PCM WAV brut pèserait ~150-300 Mo, contre ~5-15 Mo en mp3).

Même voix que generate_tts_voicestudio.py (PROFILE_ID, profil cloné à
référence audio fixe - jamais un archetype `instruct`, voir memory
voicestudio-tts-fiches-wavfiche.md et le skill ajoutfiche). num_step=32 :
c'est justement le réglage retenu à l'origine pour ce cas d'usage précis
(éviter l'artefact de fondu enchaîné entre les chunks internes de VoiceStudio
sur un texte long découpé, max_chunk_chars=800 par défaut côté API).

Débit mesuré sur le batch quiz/flashcard : ~61 caractères/s de génération.
Une fiche moyenne (~18 150 caractères) prend donc ~5 min, la plus longue
mesurée (~61 000 caractères) ~17 min. Pour les 166 fiches (~2,8M caractères
au total) : compter ~13h de génération séquentielle. À ne JAMAIS lancer en
même temps que generate_tts_voicestudio.py (même backend VoiceStudio/GPU,
risque de contention et de corruption du contexte CUDA documenté dans la
memory ci-dessus) - enchaîner après, pas en parallèle.

Usage:
    python3 generate_fiche_audio_voicestudio.py [--limit-modules N] [--only "<nom du module>"]
"""
import argparse
import json
import os
import subprocess
import sys
import time

import requests

BATOCERA_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(BATOCERA_DIR)          # racine du dépôt thématique
REPO_NAME = os.path.basename(REPO_DIR)
GAME_DIR = os.path.join(BATOCERA_DIR, REPO_NAME)  # dossier du jeu, nommé comme le dépôt
DATA_DIR = os.path.join(GAME_DIR, 'data')         # source unique (jeu ET page web)
FICHE_DIR = os.path.join(DATA_DIR, 'fiche')
OUT_DIR = os.path.join(DATA_DIR, 'fiche_audio')    # partagé avec la page web

VOICESTUDIO_URL = "http://127.0.0.1:3900/generate"
PROFILE_ID = "cc1ebb9c"  # NarrateurPSE_H1_clean : même voix que le quiz/flashcard
LANGUAGE = "fr"
NUM_STEP = 32
CROSSFADE_MS = 50  # défaut API : lissage entre chunks internes sur un texte long
EFFECT_PRESET = "raw"
REQUEST_TIMEOUT_S = 1800  # jusqu'à ~17 min mesurées pour la fiche la plus longue
# Au-delà, la fiche est découpée entre deux paragraphes et synthétisée par parties, puis
# assemblée : une requête unique de 126 000 caractères (synthèse 09-580) dépassait le délai.
PARTIE_MAX_CARACTERES = 30000


def decouper(text):
    """Parties de moins de PARTIE_MAX_CARACTERES, coupées uniquement entre deux paragraphes."""
    parties, courant = [], ''
    for bloc in text.split('\n\n'):
        if courant and len(courant) + len(bloc) + 2 > PARTIE_MAX_CARACTERES:
            parties.append(courant)
            courant = bloc
        else:
            courant = courant + '\n\n' + bloc if courant else bloc
    if courant.strip():
        parties.append(courant)
    return parties


def synth_wav(text, wav_path):
    """Synthèse d'un texte en WAV ; renvoie None si OK, sinon le message d'erreur."""
    try:
        r = requests.post(VOICESTUDIO_URL, data={
            "text": text, "profile_id": PROFILE_ID, "language": LANGUAGE,
            "num_step": NUM_STEP, "crossfade_ms": CROSSFADE_MS,
            "effect_preset": EFFECT_PRESET,
        }, timeout=REQUEST_TIMEOUT_S)
    except Exception as e:
        return 'réseau : {}'.format(e)
    if r.status_code != 200:
        return '{} : {}'.format(r.status_code, r.text[:200])
    with open(wav_path, 'wb') as f:
        f.write(r.content)
    return None


def synth_fiche(base):
    txt_path = os.path.join(FICHE_DIR, base + '.txt')
    if not os.path.exists(txt_path):
        return 'skip'
    out_path = os.path.join(OUT_DIR, base + '.mp3')
    if os.path.exists(out_path):
        return 'skip'
    with open(txt_path, encoding='utf-8') as f:
        text = f.read()
    if not text.strip():
        return 'skip'

    os.makedirs(OUT_DIR, exist_ok=True)
    t0 = time.time()
    tmp_wav = out_path + '.tmp.wav'
    parties = decouper(text) if len(text) > PARTIE_MAX_CARACTERES else [text]
    wavs = []
    for k, partie in enumerate(parties):
        w = tmp_wav if len(parties) == 1 else '{}.partie{:02d}.wav'.format(out_path, k)
        err = synth_wav(partie, w)
        if err:
            print('[ERREUR {}] {} (partie {}/{})'.format(err, base, k + 1, len(parties)), flush=True)
            for x in wavs:
                os.remove(x)
            return 'error'
        wavs.append(w)
        if len(parties) > 1:
            print('  partie {}/{} ({} caractères, {:.0f}s)'.format(k + 1, len(parties), len(partie), time.time() - t0), flush=True)
    if len(parties) > 1:
        liste = out_path + '.parties.txt'
        with open(liste, 'w', encoding='utf-8') as f:
            f.writelines("file '{}'\n".format(w.replace("'", "'\\''")) for w in wavs)
        subprocess.run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', liste, '-c', 'copy', tmp_wav],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        os.remove(liste)
        for w in wavs:
            os.remove(w)

    tmp_mp3 = out_path + '.tmp.mp3'
    try:
        proc = subprocess.run(
            ['ffmpeg', '-y', '-i', tmp_wav, '-codec:a', 'libmp3lame', '-qscale:a', '4', tmp_mp3],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
    finally:
        os.remove(tmp_wav)
    if proc.returncode != 0 or not os.path.exists(tmp_mp3):
        print('[ERREUR ffmpeg] {} : conversion mp3 échouée (code {})'.format(base, proc.returncode), flush=True)
        return 'error'
    os.replace(tmp_mp3, out_path)

    print('[ok] {} ({:.0f}s de génération, {} caractères, {} octets mp3)'.format(
        base, time.time() - t0, len(text), os.path.getsize(out_path)), flush=True)
    return 'ok'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit-modules', type=int, default=None)
    ap.add_argument('--only', action='append', default=[],
                    help='ne traiter que ce module (nom exact, répétable)')
    args = ap.parse_args()

    modules = json.load(open(os.path.join(DATA_DIR, 'modules.json'), encoding='utf-8'))
    bases = [m[:-4] for m in modules]
    if args.limit_modules:
        bases = bases[:args.limit_modules]
    if args.only:
        bases = [b for b in bases if b in args.only]

    # Garde GPU commune de l'espace de travail (un seul outil IA lourd à la fois), si disponible
    if os.path.isdir('/home/adm1/RefonteRévisions/scripts/outils'):
        sys.path.insert(0, '/home/adm1/RefonteRévisions/scripts/outils')
        from gpu import reserver_pour_le_script
        reserver_pour_le_script('narration des fiches (VoiceStudio)', 'voicestudio', service='VoiceStudio')
    stats = {'ok': 0, 'skip': 0, 'error': 0}
    t_start = time.time()

    for i, base in enumerate(bases):
        result = synth_fiche(base)
        stats[result] += 1
        elapsed = time.time() - t_start
        print('=== {}/{} : {} [{}] -- cumul ok={} skip={} error={} -- {:.0f} min écoulées ==='.format(
            i + 1, len(bases), base, result, stats['ok'], stats['skip'], stats['error'], elapsed / 60), flush=True)

    print('TERMINÉ.', stats, flush=True)


if __name__ == '__main__':
    main()
