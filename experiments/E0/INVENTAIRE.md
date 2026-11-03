# E0 — Inventaire des vidéos et sources candidates

Statut : **en cours**. Rédigé le 2026-11-03. Conditions d'utilisation consultées le 2026-11-03 ;
elles peuvent changer : les relire et noter la date avant tout téléchargement massif ou toute démonstration.

Ce document ne constitue pas un avis juridique. « Usage » désigne ici l'usage permis par le texte de la licence
tel que lu ; les points marqués **à clarifier** doivent l'être avant l'usage concerné.

## 1. Vidéos existantes

- Dossier du projet : **aucune vidéo** (constaté le 2026-11-03).
- `C:\Users\pc\Videos` contient seulement des enregistrements d'écran (`Enregistrements d'écran\*.mp4`),
  sans rapport avec le sujet. Ils ne sont pas retenus.
- Aucune vidéo « autorisée » fournie par le porteur à ce jour. **À fournir si elle existe** : sinon, on démarre
  avec les sources publiques ci-dessous.

## 2. Sources candidates vérifiées

| Source | URL | Licence (texte lu) | Attribution | Restrictions pertinentes |
|---|---|---|---|---|
| **MEVA KF1** (Kitware / IARPA) | https://mevadata.org/ · licence : https://mevadata.org/resources/MEVA-data-license.txt · vidéos : bucket S3 public `mevadata-public-01` | CC BY 4.0 (texte complet lu) | Obligatoire : « "Multiview Extended Video with Activities" (MEVA) dataset by Kitware Inc. and IARPA », lien vers la licence, mention des modifications | Acteurs dans un centre d'entraînement (école, hôpital, bâtiments administratifs) : scènes réalistes mais pas un commerce |
| **CAVIAR** (projet CE IST 2001 37540) | https://homepages.inf.ed.ac.uk/rbf/CAVIARDATA1/ (clips Lisbonne sous `../CAVIARDATA2/`) | « Creative Commons BY-SA », **version non précisée** sur la page | Demandée : « EC Funded CAVIAR project/IST 2001 37540 » + URL du projet | Partage à l'identique pour les adaptations ; version de licence **à clarifier** avant redistribution ; vidéos de 2003–2004, 384×288 |
| **Pexels** | https://www.pexels.com/license/ | Licence Pexels (propre, pas Creative Commons) | Non requise (appréciée) | Pas de personne identifiable « sous un jour défavorable » ; pas de vente de copies non modifiées ; pas de redistribution sur d'autres plateformes de banque d'images ; ne pas suggérer l'aval des personnes ou marques visibles |
| **Pixabay** | https://pixabay.com/service/license-summary/ | Licence de contenu Pixabay | Non requise | Pas de distribution « autonome » sans apport créatif ; pas d'usage trompeur ou immoral, « en particulier avec des personnes reconnaissables » ; marques visibles : pas d'usage commercial lié à des produits |

Sources examinées et **non retenues** pour l'instant :

- **MOT17** (https://motchallenge.net/data/MOT17/) : la page actuelle (archive) n'affiche pas de licence explicite et
  précise que les conditions des sources d'origine peuvent s'appliquer ; la plupart des séquences sont des caméras
  mobiles ou des rues, loin du cas d'usage.
- **Wikimedia Commons** : licences claires par fichier, mais les vidéos trouvées sont filmées à la main, sans vue fixe
  exploitable.

### Conséquence pour notre usage

Point important pour le produit : **la licence Pexels interdit de montrer une personne identifiable sous un jour
défavorable**. Un clip Pexels ne doit donc jamais illustrer un « écart à examiner » qui pourrait être lu comme
une suspicion envers la personne filmée. Il en va de même, par prudence, pour toutes les sources (D-003).

| Source | Essais internes | Démonstration (montrée à un tiers) | Redistribution (clips publiés ou fournis) |
|---|---|---|---|
| MEVA | Oui | Oui, avec attribution | Oui, avec attribution et mention des modifications |
| CAVIAR | Oui | Oui, avec attribution | **À clarifier** (version BY-SA ; partage à l'identique des clips dérivés) |
| Pexels | Oui | Oui, sans associer les personnes à un écart ou à un soupçon | **Non** pour les clips bruts ; ne pas publier le jeu d'origine |
| Pixabay | Oui | Oui, mêmes précautions que Pexels | **Non** pour les clips bruts |

Dans tous les cas : les vidéos restent hors de git (`.gitignore`), et le registre (EF-01) stocke l'URL, la licence,
l'attribution et la date de consultation comme « référence d'autorisation ».

## 3. Observations déjà faites (2026-11-03)

Accès vérifié en lisant quelques images à distance avec ffmpeg et en téléchargeant un clip :

- **MEVA** : clips de 5 min en AVI ; exemple mesuré : H.264, 1920×1080, 30 i/s, durée 300,3 s
  (`school.G299`, 2018-03-07 16:50). Taille de 2 à 170 Mo par clip. Le nom de fichier code la date, l'heure de début
  et de fin, le lieu et la caméra.
- Une image par caméra intérieure du créneau 2018-03-07 16:50 a été examinée (planche dans
  `experiments/E0/out/`, non versionnée). Vues de passage identifiées : `school.G420` (double porte d'entrée vue
  d'en haut), `school.G638` (entrée extérieure d'un bâtiment, personnes petites), `school.G423` (couloir),
  `admin.G326` (porte de cage d'escalier), `school.G421` (hall animé avec tables).
- Activité échantillonnée (10 images sur 5 min, **pas un comptage**) : `G420` montre plusieurs personnes à la porte ;
  `G638` des passages lointains ; `G421` une forte densité et une table où des personnes prennent des objets ;
  `G326` **aucune personne visible** sur ce créneau (écarté pour ce créneau).
- **CAVIAR** `OneStopEnter2front.mpg` téléchargé dans `data/videos/caviar/` (non versionné),
  SHA-256 `A296AC0B4300A344F7399DE19F049CECB1E90F407B0505F9289D6F1E6B08B80F`, 15 Mo :
  - flux MPEG-1 **brut sans conteneur** : `start_time` absent, durée annoncée **1,2 s** alors que le fichier contient
    **2 725 images** (soit 109 s à 25 i/s) ; `r_frame_rate` = 50/1 et `avg_frame_rate` = 25/1 ;
  - certaines images n'ont pas de PTS (`N/A`) ; ffprobe fournit alors un temps estimé (`best_effort_timestamp`) ;
  - une **horloge est incrustée** dans l'image (`10:19:05.477 20-01-2004`) : référence indépendante pour E3 ;
  - la page CAVIAR signale des images dupliquées dues à une erreur de numérisation.
  → Ce fichier est un **cas limite utile pour E3**, pas un cas nominal.

## 4. Échantillon proposé

Rôles : **réglage** = on peut régler des paramètres dessus ; **réserve** = évaluation seulement, jamais de réglage.

| ID | Fichier | Scénario | Rôle | Pourquoi |
|---|---|---|---|---|
| S1 | MEVA `2018-03-07.16-50-01.16-55-01.school.G420.r13.avi` | A | Réglage | Porte d'entrée intérieure, vue plongeante, passages espacés : cas simple |
| S2 | CAVIAR `OneStopEnter2front.mpg` + `OneStopEnter2cor.mpg` | A + E3 | Réglage | Entrée de boutique en galerie ; basse résolution ; horloge incrustée ; flux sans conteneur |
| S3 | MEVA `2018-03-07.16-50-00.16-55-00.school.G638.r13.avi` | A | Réglage | Extérieur, personnes petites et lointaines : difficulté de taille |
| S4 | MEVA `2018-03-07.16-50-00.16-55-00.school.G421.r13.avi` | A (stress) + B (E4) | Réglage | Densité, occultations ; table de retrait d'objets comparable à une zone de transfert |
| **R1** | MEVA `2018-03-13.16-00-01.16-05-01.school.G420.r13.avi` | A | **Réserve** | Même caméra que S1, autre jour : mesure la généralisation dans le temps |
| **R2** | CAVIAR `TwoEnterShop2front.mpg` + `TwoEnterShop2cor.mpg` | A | **Réserve** | Même lieu que S2, autre séquence |

Règles de la réserve (fixées le 2026-11-03, avant tout réglage) :

1. R1 et R2 sont choisis par règle (autre jour ou autre séquence, même point de vue), **sans visionnage préalable**
   du contenu.
2. Ils sont annotés selon le protocole E1, puis ne sont plus regardés pendant les réglages.
3. Ils ne servent qu'à évaluer une configuration **gelée** (empreinte notée). Toute évaluation sur la réserve est
   consignée, même mauvaise. Après plus de trois évaluations sur la réserve, elle est considérée comme usée et
   une nouvelle réserve est tirée selon la même règle.
4. Si l'annotation de R1 compte moins de 10 passages, on ajoute le créneau suivant de la même caméra
   (`16-05-01`), décidé ici et non après coup.

**Prototype (2026-11-03)** : **S1 est le seul extrait de réglage utilisé** ; S2 à S4 ne servent pas encore. Téléchargé le
2026-11-03T17:07:31Z depuis la base S3 MEVA indiquée au §2. Empreinte sha256
`19A8159AAE2423E4A0221BED3735BD2C61B158B02E4DFCF8A21D007796816CE4`, 69 804 664 octets, 1920×1072, 30 images/s,
9 000 images. Fichier original conservé tel quel. Les pistes du premier run et deux images de son rendu nuancent la description
ci-dessus : l'extrait commence par une sortie de groupe dense (≈ 17 s), puis seules deux personnes sont suivies
(observation machine, non vérifiée). Il n'est donc pas un « cas simple »
sur toute sa durée. R1 et R2 ne sont ni téléchargés ni regardés.

Clips d'appoint, non retenus dans l'échantillon principal (vues de banque d'images, souvent mobiles ou en gros plan ;
métadonnées lues sur la page du clip, **à confirmer au téléchargement**) :

| Clip | URL | Auteur | Usage envisagé |
|---|---|---|---|
| People Going inside a Store with Automatic Sliding Doors | https://www.pexels.com/video/people-going-inside-a-store-with-automatic-sliding-doors-6641527/ | Casey Whalen | Démonstration scénario A (entrée de commerce), si la caméra est fixe |
| Packages Moving on a Conveyor Belt | https://www.pexels.com/video/packages-moving-on-a-conveyor-belt-4156510/ | Erkan Avanoğlu | E4 : objets traversant une zone (entrepôt) |
| A Salesperson Handing Shopping Bags to a Customer | https://www.pexels.com/video/a-salesperson-handing-shopping-bags-to-a-customer-9595330/ | Ron Lach | E4 : remise d'objet en gros plan (pas un angle de caméra fixe) |

## 5. Étapes restantes d'E0

- [x] S1 téléchargé, empreinte et métadonnées relevées (ci-dessus).
- [ ] Télécharger S3, S4, R1 (MEVA) et R2 (CAVIAR) dans `data/videos/` ; calculer SHA-256 et métadonnées.
- [ ] Remplir le manifeste (une ligne par fichier : ID, URL, licence, attribution, date de consultation, empreinte,
      rôle, métadonnées techniques).
- [ ] Vérifier sur S1 à S4 la présence effective de passages (visionnage rapide, sans compter) ; **ne pas visionner R1 et R2**.
- [ ] Le porteur indique s'il dispose de vidéos autorisées propres (commerce, café, entrepôt) : elles seraient
      prioritaires sur les sources publiques.
