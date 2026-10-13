# Rouleau des Jutsu : preview des particules

Preview 3D de 39 techniques de Naruto, du rang C au rang S, chacune avec son effet de particules de base. Elle sert à valider l'apparence des techniques avant de les intégrer au serveur de jeu de rôle.

Fan-art non commercial. Naruto © Masashi Kishimoto / Shueisha / Studio Pierrot.

## Lancer la preview

Double-clique sur `index.html`. La page s'ouvre dans le navigateur, sans rien à installer.

- Avec internet, three.js est chargé depuis un CDN.
- Sans internet, la page prend la copie locale dans `vendor/`. Seules les polices changent : le navigateur utilise ses polices système.

**Commandes :**
- Clic sur une technique : la lance.
- `Espace` : rejoue la technique.
- `↑` / `↓` : technique précédente / suivante.
- Souris ou doigt : tourner autour de la scène. Molette ou pincement : zoomer.
- **Boucle** : rejoue la technique en continu.
- **Vitesse** : ralenti à 0,25× ou 0,5× pour examiner les particules.

## Les techniques

| Rang | Feu 火 | Vent 風 | Foudre 雷 | Eau 水 | Terre 土 | Autre |
|---|---|---|---|---|---|---|
| **C** | Gōkakyū, Hōsenka, Ryūka | Reppūshō, Daitoppa | Jibashi | Teppōdama, Suirō | Doryū Taiga | Kuchiyose |
| **B** | Karyū Endan, Haisekishō | Kamaitachi | Gian | Suijinheki, Suiryūdan, Suikōdan | Doryūheki, Doryūdan, Yomi Numa, Domu | Kage Bunshin |
| **A** | Gōka Mekkyaku, Gōryūka, Zukokku | Atsugai | Chidori, Raikiri, Raiton Kage Bunshin | Daibakufu, Bakusui Shōha | | Rasengan, Ōdama Rasengan, Tajū Kage Bunshin |
| **S** | | Rasenshuriken | Kirin | | | Hiraishin, Shiki Fūjin, Jiongu |

Les rangs suivent les databooks et Narutopedia. Pour quelques techniques, le rang n'y est pas clairement indiqué (Zukokku, Domu, Jiongu, Shiki Fūjin notamment). Vérifie-les par rapport aux règles de ton serveur.

## Ajouter ou modifier une technique

Tout est dans `index.html`, section **1. LES TECHNIQUES**, en haut du script. Chaque technique tient sur un objet :

```js
{ rank:"C", el:"fire", name:"Katon : Gōkakyū no Jutsu", jp:"火遁・豪火球の術", fr:"Boule de feu suprême", type:"Ninjutsu",
  desc:"…",
  fx:"projectile", o:{ pal:"fire", from:"mouth", r:1.3, speed:11, charge:.7, impact:"explode", impactR:2.6 } },
```

- `rank` : `C`, `B`, `A` ou `S`.
- `el` : `fire`, `wind`, `lightning`, `water`, `earth` ou `other`.
- `fx` : le preset de particules. `o` : ses réglages.

Les presets réutilisables avec leurs réglages principaux :

| Preset | Effet | Réglages utiles |
|---|---|---|
| `projectile` | charge, boule qui vole, impact | `pal`, `from` (`mouth`/`hand`), `r` (rayon), `n` (nombre), `spread`, `curve`, `speed`, `impact`, `impactR` |
| `stream` | souffle continu en cône | `pal`, `len`, `cone` (ouverture), `dur`, `rate`, `size`, `life`, `heavy` |
| `dragon` | tête qui suit une courbe, corps en traînée | `pal`, `path` (`arc`, `rise`, `sky`, `low`), `n`, `head`, `dur`, `body`, `impact` |
| `orb` | orbe en main, charge, impact | `pal`, `kind` (`rasengan`/`chidori`), `r` |
| `wall` | mur défensif | `pal`, `kind` (`spiral`/`front`) |
| `wave` | vague ou coulée | `pal`, `kind` (`water`/`mud`) |
| `blades` | lames en croissant | `pal`, `n` |
| `clones` | apparition de clones dans la fumée | `n` (jusqu'à 30) |

**Palettes (`pal`) :** `fire`, `wind`, `lightning`, `water`, `earth`, `chakra`, `yin`, `flash`, `ash`, `thread`, `smoke`.

**Impacts (`impact`) :** `explode`, `splash`, `shock`, `spark`, `mud`.

Les autres presets (`kirin`, `rasenshuriken`, `hiraishin`, `reaper`, `threads`, `summon`, etc.) sont propres à une technique. Ils sont écrits dans la section **5. PRESETS D'EFFETS**.

## Passer au moteur du serveur

Cette preview ne s'exporte pas telle quelle vers un moteur de jeu. Elle sert de référence visuelle : pour chaque technique, elle fixe les couleurs (dégradé début → milieu → fin), les tailles, les durées de vie, la vitesse et le nombre de particules. Ces valeurs se recopient directement dans un `ParticleEmitter` Roblox, un système Niagara (Unreal), un Particle System Unity ou un effet Lua GMod.
