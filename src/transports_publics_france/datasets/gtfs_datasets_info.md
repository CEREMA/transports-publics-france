# Rapport par réseau (`gtfs_datasets_info`)

## Objectif

Le rapport par réseau liste l'ensemble des jeux de données GTFS référencés sur
[transport.data.gouv.fr](https://transport.data.gouv.fr), en croisant :

- les **métadonnées déclaratives** de l'API transport.data.gouv.fr (titre, éditeur, zone géographique couverte, offres de transport, etc.) ;
- les **métadonnées observées** directement dans les fichiers GTFS téléchargés (agences, dates de validité du calendrier) ;
- un **rapprochement automatique** entre chaque GTFS individuel et l'agrégat régional qui le contient éventuellement (par exemple un réseau urbain intégré dans le GTFS agrégé de sa région), à partir des identifiants d'offres de transport de l'API (`offer_ids`).

Il est produit par `build_network_report(run_date, data_dir)`, à lancer **après** `run_gtfs_pipeline` pour la même date et dans le même dossier. La fonction écrit `AAAAMMJJ_gtfs_datasets_info.csv` dans `data_dir` et renvoie également le tableau sous forme de DataFrame.

```python
from datetime import date
from pathlib import Path
import polars as pl

from transports_publics_france import run_gtfs_pipeline, build_network_report

RUN_DATE = date.today()
DATA_DIR = Path("data")

run_gtfs_pipeline(out_dir=DATA_DIR, run_date=RUN_DATE, redownload=True)
report = build_network_report(RUN_DATE, DATA_DIR)
report.head()
```

## Une ligne = une ressource GTFS

Une ligne correspond à **une ressource GTFS** (`resource_transport_id`), c'est-à-dire un fichier GTFS précis.
Un même jeu de données (`dataset_id`) peut contenir plusieurs ressources.

> **Champs vides.** Les champs *observés dans le GTFS* (`agency_name`, `start_date`, `end_date`, `service_dates_valid`) sont vides pour un GTFS qui n'a pas pu être téléchargé ou qui a été écarté à la validation.

## Dictionnaire des champs

**Colonne « Source »** :

- `API` : métadonnée déclarative de transport.data.gouv.fr ;
- `GTFS` : valeur recalculée à partir du fichier GTFS réellement téléchargé et lu ;
- `Pipeline` : valeur générée par le package lui-même.

### Identifiants

| Colonne | Type | Source | Description |
|---|---|---|---|
| `dataset_id` | texte | API | Identifiant data.gouv.fr du **jeu de données** (peut regrouper plusieurs ressources GTFS). |
| `resource_transport_id` | entier | API | Identifiant interne transport.data.gouv.fr de la **ressource GTFS** (le fichier lui-même). |
| `resource_datagouv_id` | texte | API | Identifiant data.gouv.fr de la ressource GTFS. |

### Titres et liens

| Colonne | Type | Source | Description |
|---|---|---|---|
| `dataset_title` | texte | API | Titre du jeu de données tel qu'affiché sur transport.data.gouv.fr. |
| `resource_title` | texte | API | Titre de la ressource GTFS. |
| `page_url` | texte (url) | API | Page du jeu de données sur transport.data.gouv.fr. |
| `resource_url` | texte (url) | API | URL de téléchargement du fichier GTFS (zip), hébergée par transport.data.gouv.fr. |
| `resource_original_url` | texte (url) | API | URL de téléchargement d'origine, chez l'émetteur des données (à utiliser si `resource_url` échoue). |
| `resource_page_url` | texte (url) | API | Page dédiée à la ressource sur transport.data.gouv.fr. |

### Éditeur et contenu

| Colonne | Type | Source | Description |
|---|---|---|---|
| `publisher_name` | texte | API | Nom de l'organisme éditeur du jeu de données (AOM, région, opérateur...). |
| `resource_community_resource_publisher` | texte | API | Si la ressource a été ajoutée par un tiers (et non par l'éditeur officiel), nom de ce contributeur communautaire. Vide sinon. |
| `resource_features` | texte (valeurs séparées par des virgules) | API | Fonctionnalités GTFS détectées par la plateforme (ex. `tarification`, `couleur de ligne`...). |
| `resource_modes` | texte (valeurs séparées par des virgules) | API | Modes de transport détectés dans le GTFS (ex. `bus`, `tram`...), déduits par transport.data.gouv.fr. |
| `stops_count` | entier | API | Nombre d'arrêts (`stops.txt`) déclaré par la plateforme pour ce GTFS. |

### Couverture géographique et type de jeu de données

| Colonne | Type | Source | Description |
|---|---|---|---|
| `categorie_geo` | texte | API | Type de zone géographique couverte (`commune`, `epci`, `departement`, `region`, `pays`), déduit de `covered_area`. Sert de filtre dans le rapprochement avec un agrégat (voir plus bas). |
| `covered_area` | texte (JSON) | API | Détail brut de la ou des zones géographiques couvertes par le jeu de données, tel que renvoyé par l'API. |
| `is_scolaire` | booléen | API | `True` si le jeu de données est tagué comme transport scolaire (`sub_types` contient `school`). |
| `is_saisonnier` | booléen | API | `True` si le jeu de données est tagué comme saisonnier (`sub_types` contient `seasonal`). |
| `is_agregat` | booléen | API | `True` si le jeu de données est un **agrégat régional** (tag `agrégat_region`). |

### Offres de transport et propriétaires

| Colonne | Type | Source | Description |
|---|---|---|---|
| `offer_ids` | texte (identifiants séparés par des virgules) | API | Identifiants des offres de transport (réseaux) couvertes par le jeu de données, tels que renvoyés par l'API (`identifiant_offre`). |
| `offer_names` | texte (valeurs séparées par des virgules) | API | Noms commerciaux correspondant à `offer_ids` (ex. `Ilévia`, `Star`...), pour lecture humaine. |
| `legal_owners` | texte (JSON) | API | Détail des propriétaires légaux des données, tel que renvoyé par l'API. |

### Dates du jeu de données et de l'extraction

| Colonne | Type | Source | Description |
|---|---|---|---|
| `created_at` | texte | API | Date de création du jeu de données sur la plateforme, telle que renvoyée par l'API. |
| `updated` | texte | API | Date de dernière mise à jour du jeu de données sur la plateforme, telle que renvoyée par l'API. |
| `resource_extract_date` | date (`AAAA-MM-JJ`) | Pipeline | Date d'extraction (`run_date`) à laquelle le pipeline a tourné : elle permet de dater chaque export et de suivre l'évolution d'un GTFS dans le temps entre deux exécutions. |

### Observé dans le GTFS

Ces champs sont vides si le GTFS n'a pas pu être traité.

| Colonne | Type | Source | Description |
|---|---|---|---|
| `agency_name` | texte | GTFS | Nom(s) d'agence (`agency.txt`, champ `agency_name`) observé(s) directement dans le fichier téléchargé. |
| `start_date` | date (`JJ/MM/AAAA`) | GTFS | Première date de validité du service, calculée à partir de `calendar.txt` et `calendar_dates.txt` du GTFS. |
| `end_date` | date (`JJ/MM/AAAA`) | GTFS | Dernière date de validité du service, même calcul que `start_date`. |
| `service_dates_valid` | booléen | GTFS | `True` si la date d'extraction (`run_date`) est comprise entre `start_date` et `end_date` (le GTFS est donc à jour) ; `False` si elle est en dehors de cette période (GTFS périmé ou pas encore actif). |

### Rattachement à un agrégat régional

| Colonne | Type | Source | Description |
|---|---|---|---|
| `agregat_resources_id` | entier | Pipeline | `resource_transport_id` de l'agrégat régional dans lequel ce GTFS est intégré, s'il existe ; `null` si ce GTFS est lui-même un agrégat (`is_agregat = True`) ou si aucun agrégat correspondant n'a été trouvé. |

## Rapprochement entre un GTFS individuel et un agrégat régional

Certaines régions publient, en plus des GTFS de chaque réseau de transport, un GTFS « agrégat » qui les compile tous. Pour associer un GTFS individuel à l'agrégat qui le contient (utile pour éviter de traiter deux fois les mêmes données, ou pour choisir la source à privilégier), le package :

1. repère tous les jeux de données `is_agregat = True` et construit, pour chacun, l'ensemble de ses `offer_ids` ;
2. pour chaque GTFS individuel, cherche un agrégat dont les `offer_ids` recoupent les siens, en écartant les agrégats dont la couverture géographique (`categorie_geo`) serait plus étroite que celle du GTFS individuel (un agrégat régional ne peut pas contenir un GTFS couvrant tout le pays) ;
3. enregistre le premier agrégat correspondant trouvé dans `agregat_resources_id`.

## Colonnes imbriquées et format CSV

Le rapport est écrit en CSV, format qui ne supporte pas les champs imbriqués. Les colonnes qui contiennent des listes ou des structures dans l'API (`resource_features`, `resource_modes`, `covered_area`, `offer_ids`, `offer_names`, `legal_owners`) sont donc aplaties avant l'écriture, et le DataFrame renvoyé par `build_network_report` contient déjà ces versions aplaties :

- liste de valeurs simples (par exemple `offer_ids`) : valeurs jointes par une virgule ;
- liste de structures ou structure simple (par exemple `covered_area`, `legal_owners`) : encodée en JSON dans une seule cellule de texte.