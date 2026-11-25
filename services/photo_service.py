"""
SARL NOMADE AYRIS - Gestionnaire de Stock
Module: services/photo_service.py
Service de gestion et de traitement des photos de pièces de rechange.
- Normalisation EXIF, conversion RGB, redimensionnement max 800px, JPEG q=80
- Stockage externe dans photos_pieces/ à côté de l'exécutable
- Gestion des chemins relatifs et gestion d'erreurs sans crash.
"""

import os
import sys
import shutil
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageOps

FORMATS_ACCEPTES = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')


def get_base_dir() -> Path:
    """
    Retourne le répertoire racine de l'application :
    - Dossier de l'exécutable si packagé avec PyInstaller (sys.frozen)
    - Dossier racine du projet sinon.
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    # Sinon remonter depuis services/ vers la racine
    return Path(__file__).resolve().parent.parent


def get_photos_dir() -> Path:
    """
    Retourne le chemin absolu du dossier photos_pieces/ à côté de l'exécutable.
    Crée automatiquement le dossier s'il n'existe pas.
    """
    photos_dir = get_base_dir() / 'photos_pieces'
    photos_dir.mkdir(parents=True, exist_ok=True)
    return photos_dir


def resoudre_chemin_absolu(chemin_relatif_ou_absolu: str) -> Path | None:
    """
    Résout un chemin de photo en chemin absolu valide.
    Gère les chemins relatifs enregistrés en base.
    """
    if not chemin_relatif_ou_absolu:
        return None

    p = Path(chemin_relatif_ou_absolu)
    if p.is_absolute():
        return p if p.exists() else None

    # Si c'est un chemin relatif (ex: photos_pieces/PIECE_1_xxx.jpg ou PIECE_1_xxx.jpg)
    base = get_base_dir()
    candidat = base / p
    if candidat.exists():
        return candidat

    # Alternative : chercher directement dans photos_dir
    candidat2 = get_photos_dir() / p.name
    if candidat2.exists():
        return candidat2

    return candidat  # Retourner le chemin attendu même s'il n'existe pas encore


def traiter_et_enregistrer_photo(source_file_path: str, piece_id: int) -> tuple[bool, str]:
    """
    Prend en entrée une image du PC (explorateur), effectue :
    1. Validation du format
    2. Correction d'orientation EXIF
    3. Conversion RGB (suppression propre de la transparence PNG/WebP avec fond blanc)
    4. Redimensionnement avec conservation des proportions (max 800px sur le plus grand côté)
    5. Sauvegarde en JPEG qualité 80 dans photos_pieces/
    6. Retourne (succès: bool, chemin_relatif_ou_message_erreur: str)
    """
    if not source_file_path or not os.path.exists(source_file_path):
        return False, "Le fichier source sélectionné est introuvable."

    source_path = Path(source_file_path)
    ext = source_path.suffix.lower()
    if ext not in FORMATS_ACCEPTES:
        return False, f"Format non supporté ({ext}). Formats acceptés : JPG, JPEG, PNG, BMP, WEBP."

    try:
        photos_dir = get_photos_dir()
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        nom_fichier = f"PIECE_{piece_id}_{ts}.jpg"
        destination_path = photos_dir / nom_fichier

        with Image.open(source_path) as img:
            # 1. Correction d'orientation EXIF (smartphones / appareils photos)
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass

            # 2. Conversion en RGB
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                fond = Image.new('RGB', img.size, (255, 255, 255))
                # Extraire le masque alpha
                alpha = img.convert('RGBA').split()[-1]
                fond.paste(img.convert('RGB'), mask=alpha)
                img_rgb = fond
            else:
                img_rgb = img.convert('RGB')

            # 3. Redimensionnement proportionnel (max 800px)
            max_size = (800, 800)
            img_rgb.thumbnail(max_size, Image.Resampling.LANCZOS)

            # 4. Enregistrement en JPEG compressé (qualité 80, progressif pour fluidité)
            img_rgb.save(destination_path, format='JPEG', quality=80, optimize=True)

        # Chemin relatif propre et portable pour la base de données
        chemin_relatif = f"photos_pieces/{nom_fichier}"
        return True, chemin_relatif

    except Exception as e:
        return False, f"Impossible de traiter l'image :\n{e}"

