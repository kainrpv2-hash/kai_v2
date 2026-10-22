# Nara : manipulation des ombres

Techniques d'ombre du clan Nara pour un serveur Garry's Mod Naruto RP, refaites de zéro. L'addon est accompagné d'une preview 3D jouable dans le navigateur.

Fan-art non commercial. Naruto © Masashi Kishimoto / Shueisha / Studio Pierrot.

| Dossier | Contenu |
|---|---|
| `gmod/addon/nara_kage/` | L'addon à copier dans `garrysmod/addons/` (installation et commandes : `gmod/LISEZMOI.txt`) |
| `preview/index.html` | Preview jouable : double-clic, rien à installer |
| `tools/make_assets.py` | Génère les textures (VTF + PNG) et les sons (WAV) |
| `tools/build_preview.py` | Encode les sons de la preview et produit une version en un seul fichier |

## Les techniques

1. **Kagemane no Jutsu** : genou à terre et sceau du Rat. La caméra plonge ensuite dans la pointe de l'ombre, en vue première personne. Un compteur de 13 s s'affiche en bas au milieu de l'écran et la souris dirige l'ombre. Une fois prise, la cible imite les mouvements du lanceur pendant 10 s.
2. **Kage Kubishibari no Jutsu** : des bras d'ombre montent en spirale jusqu'au cou de la cible et serrent.
3. **Kage Nui no Jutsu** : des aiguilles d'ombre jaillissent du sol et transpercent la cible.

Les techniques 2 et 3 s'enchaînent sur une cible déjà prise par Kagemane, ou partent directement sur la cible visée.

## Preview

- Souris / doigt : tourner la caméra. Pendant Kagemane, ce geste dirige l'ombre.
- `1` `2` `3` ou `R` : choisir la technique. `Espace` : lancer. Clic droit ou `Échap` : annuler.
- `Z` `Q` `S` `D` (ou flèches) : marcher. Pendant la possession, la cible imite tes pas.
- Pendant Kagemane : `Z` accélère l'ombre, `S` la ralentit.

La preview reprend les réglages, la cinématique inverse de la pose, le tracé de l'ombre, les textures et les sons de l'addon.

## Régénérer les fichiers

```
cd tools
python3 make_assets.py        # textures + sons de l'addon, preview/textures.js
python3 build_preview.py      # preview/sounds.js (ffmpeg requis)
```
