# Nara : Kagemane no Jutsu

La manipulation des ombres du clan Nara pour un serveur Garry's Mod Naruto RP. Le rendu de l'ombre reprend celui de la vidéo de présentation du clan Nara de Solve Community : une bande noire pleine aux bords nets, de largeur constante, à la pointe effilée, qui serpente au sol. L'addon est accompagné d'une preview 3D jouable dans le navigateur.

Fan-art non commercial. Naruto © Masashi Kishimoto / Shueisha / Studio Pierrot.

| Dossier | Contenu |
|---|---|
| `gmod/addon/nara_kage/` | L'addon à copier dans `garrysmod/addons/` (installation et commandes : `gmod/LISEZMOI.txt`) |
| `preview/index.html` | Preview jouable : double-clic, rien à installer |
| `tools/make_assets.py` | Génère les textures (VTF + PNG) et les sons (WAV) |
| `tools/build_preview.py` | Encode les sons de la preview et produit une version en un seul fichier |

## La technique

1. Le lanceur met un genou à terre et forme le sceau du Rat. Son ombre s'étale devant lui.
2. L'ombre part. La caméra plonge dans sa pointe, en vue première personne, et un compteur de 13 secondes s'affiche en bas au milieu de l'écran.
3. L'ombre prend la direction où regarde la caméra.
4. Si elle touche quelqu'un, la cible est prise : elle imite les mouvements et le sceau du lanceur pendant 10 s. Sinon l'ombre revient au bout des 13 secondes.

## Preview

- Souris / doigt : tourner la caméra. Pendant la technique, ce geste dirige l'ombre.
- `Espace` : lancer. Clic droit ou `Échap` : annuler.
- `Z` / `S` pendant la technique : accélérer / ralentir l'ombre.
- `Z` `Q` `S` `D` (ou flèches) : marcher. Pendant la possession, la cible imite tes pas.

La preview reprend les réglages, la pose, le tracé de l'ombre, les textures et les sons de l'addon.

## Régénérer les fichiers

```
cd tools
python3 make_assets.py        # textures + sons de l'addon, preview/textures.js
python3 build_preview.py      # preview/sounds.js (ffmpeg requis)
```
