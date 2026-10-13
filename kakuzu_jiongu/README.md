# Les quatre cœurs de Kakuzu (Jiongu 地怨虞)

Modèles 3D riggés et animés des quatre monstres masqués de Kakuzu (Naruto Shippuden, épisodes 84 à 89). Ils sont prévus pour un serveur de jeu de rôle Naruto.

Fan-art non commercial. Naruto © Masashi Kishimoto / Shueisha / Studio Pierrot.

| Monstre | Élément | Technique | Hauteur (fourrure incluse) | Tris HQ | Tris LOW | Os |
|---|---|---|---|---|---|---|
| `Jiongu_Katon` | 火 Feu | Katon : Zukokku 頭刻苦 | ≈ 3,5 m | 97 600 | 16 440 | 15 |
| `Jiongu_Futon` | 風 Vent | Fūton : Atsugai 圧害 | ≈ 1,6 m (ailes : 2,9 m) | 85 904 | 19 688 | 21 |
| `Jiongu_Raiton` | 雷 Foudre | Raiton : Gian 偽暗 | ≈ 3,9 m (envergure : 4,7 m) | 109 200 | 18 904 | 17 |
| `Jiongu_Suiton` | 水 Eau | aucune (détruit avant d'attaquer) | ≈ 3,3 m | 75 816 | 12 888 | 15 |

Kakuzu mesure 1,85 m. Les monstres sont à l'échelle réelle : 1 unité = 1 mètre.

## Contenu

```
HQ/        version haute qualité (cinématique, Unreal Engine 5, Unity HDRP)
LOW/       version jeu, < 20 000 triangles par modèle (Roblox, GMod, mobile)
renders/   rendus Cycles des modèles HQ
sources/   scripts Python/Blender qui génèrent les modèles (modifiables)
```

Chaque monstre existe en trois formats :
- `.glb` : glTF 2.0 avec textures, squelette et animations intégrés. C'est le plus simple, il s'ouvre partout.
- `.fbx` : textures intégrées. Pour Unreal, Unity et Roblox.
- `.blend` : fichier Blender 5.2 avec textures empaquetées, pour retoucher les modèles.

## Ce que contient chaque modèle

**Un seul mesh, trois matériaux :**
- `KZ_Threads_Body` : le corps de fils noirs.
- `KZ_Threads_Fur` : les « hair cards » de fils. Matériau **masqué** (alpha clip à 0,5), **double face**.
- `KZ_Mask_<élément>` : le masque peint à la main.

**Squelette :** `root`, `hips`, `spine`, `chest`, `head` (le masque suit `head`), puis les bras, les jambes et les mains. S'y ajoutent :
- Foudre : les ailes d'épaules `crest.L/R`.
- Vent : les ailes en échelle `wing.L/R` et `wingtip.L/R`.

**Trois animations (30 images/s) :**

| Nom | Images | Boucle | Description |
|---|---|---|---|
| `<nom>_Idle` | 1 à 121 | oui | respiration, regard qui balaye, bras et ailes qui ondulent |
| `<nom>_Walk` | 1 à 41 | oui | marche lourde sur place (le Vent trotte à quatre pattes) |
| `<nom>_Attack` | 1 à 61 | non | recul, puis le masque est projeté en avant pour lancer la technique. L'impact est vers l'image 24. |

**Textures :** le corps et la fourrure ont une couleur et une normal map. Les masques HQ sont en 2048 px, les LOW en 1024 px.

## Importer dans ton moteur

### Unreal Engine 5
1. Glisse le `.fbx` HQ dans le Content Browser.
2. Coche **Skeletal Mesh** et **Import Animations**. Laisse **Import Uniform Scale** à 1 : le modèle est déjà en mètres, Unreal convertit tout seul.
3. Ouvre le matériau `KZ_Threads_Fur` : **Blend Mode = Masked**, **Two Sided = activé**, et branche l'alpha de la texture sur **Opacity Mask**.
4. Tu peux aussi importer le `.glb` directement (plugin Interchange glTF, actif par défaut depuis UE 5.1). Il garde l'alpha masqué tout seul.

### Unity
- **URP/HDRP :** importe le `.fbx`. Sur `KZ_Threads_Fur`, active **Alpha Clipping** (seuil 0,5) et **Render Face = Both**.
- **Avec le `.glb` :** installe le package **glTFast**, qui gère tout automatiquement.
- **Animations :** dans l'onglet Animation de l'import, coche **Loop Time** pour `Idle` et `Walk`.

### Roblox Studio
1. Utilise la version **LOW** : moins de 20 000 triangles, la limite d'un MeshPart.
2. Ouvre **Fichier > Importer 3D** et choisis le `.fbx` LOW. Le squelette et les animations sont détectés (rig personnalisé).
3. Sur la texture de fourrure, règle la transparence en mode découpe (**AlphaMode = Overlay/Transparency** selon ta version).

### Garry's Mod (Source)
1. Ouvre le `.blend` LOW dans Blender et installe l'add-on **Blender Source Tools**.
2. Exporte en SMD/DMX, écris un `.qc` (`$model`, `$sequence idle/walk/attack`), puis compile avec `studiomdl`.
3. Convertis les textures en VTF avec VTFEdit. Le matériau de fourrure a besoin de `$alphatest 1` et `$nocull 1`.

### FiveM / GTA RP
Ouvre le `.blend` dans Blender avec l'add-on **Sollumz** et exporte-le en YDR/YFT (prop animé). Pour en faire un vrai ped jouable, il faut d'abord le re-rigger sur le squelette GTA.

### Minecraft
Ces modèles ne sont pas compatibles avec le style cubique de Minecraft. Pour ce cas, il faut une version Blockbench dédiée.

## Fiche lore (d'après Narutopedia, épisode 84)

- **Feu (Katon) :**
  - **Masque :** ovale blanc, bandeau en forme de lunettes, bouche rectangulaire aux lèvres pourpres et aux dents carrées.
  - **Corps :** grand dôme poilu, bosse dorsale, longs bras griffus.
  - **Technique :** *Zukokku*. Une boule de feu explose en tempête de flammes.
  - **Destin :** détruit par le Rasenshuriken de Naruto (ép. 88).
- **Vent (Fūton) :**
  - **Masque :** grandes arcades, bouche en V comme un bec, larmes bleu marine.
  - **Corps :** quadrupède bas, fines ailes de fils en échelle.
  - **Technique :** *Atsugai*. Un souffle d'air comprimé.
  - **Destin :** détruit par le Rasenshuriken de Naruto (ép. 88).
- **Foudre (Raiton) :**
  - **Masque :** visage d'oni avec cornes en croissant, nez ocre et crocs.
  - **Corps :** le plus massif, épaules en ailes pointues, crête de pics.
  - **Technique :** *Gian*. Des lances d'éclairs.
  - **Destin :** son cœur est absorbé par Kakuzu, puis détruit par le Raikiri de Kakashi (ép. 89).
- **Eau (Suiton) :**
  - **Masque :** œuf blanc, croissants bleu acier près des yeux, ligne ondulée en bec.
  - **Corps :** grand bipède voûté.
  - **Destin :** transpercé par le premier Raikiri de Kakashi dès sa sortie (ép. 84). L'élément est déduit par élimination.

## Modifier ou régénérer

Le dossier `sources/` contient le pipeline complet. Il faut Python 3.13 avec `bpy==5.2.2`, `numpy`, `pillow` et `scikit-image`.

```
python tex_gen.py              # textures fourrure + corps
python masks.py                # peinture des 4 masques
python build.py katon hq       # katon | futon | raiton | suiton, hq | low
python render.py out.png 1080 1350 64 "x,y,z,tx,ty,tz,focale" "katon:0:0:0:Idle:1"
```

Les formes sont dans `creatures.py` : ellipsoïdes et cônes, avec un os par primitive. Les dessins des masques sont dans `masks.py`.
