"""
Utils for interacting with the transport.data.gouv.fr API :
- get_gtfs_datasets_info()
"""

import logging
import polars as pl
import requests

log = logging.getLogger(__name__)

def get_gtfs_datasets_info() -> pl.DataFrame:
    """Interrogates the transport.data.gouv.fr API and returns GTFS metadata.

    Replicates territoRy::get_dataset_info(format = "gtfs") :
    - Single call to /api/datasets (flat list, no pagination)
    - Filter resources_is_available == True
    - Filter resources_format == "GTFS" (case-insensitive)
    - Detection of duplicates in resources_datagouv_id
    """
    log.info("Getting dataset information from transport.data.gouv.fr")

    resp = requests.get("https://transport.data.gouv.fr/api/datasets", timeout=60)
    resp.raise_for_status()
    datasets_raw: list[dict] = resp.json()

    rows = []
    seen_datagouv_ids: list[str] = []
    duplicates: list[str] = []

    for item in datasets_raw:
        publisher = item.get("publisher") or {}
        covered_area = item.get("covered_area") or []
        sub_types = item.get("sub_types") or []
        tags_list = item.get("tags") or []
        categorie_geo = covered_area[0].get("type") if covered_area else None

        # get aggregate containing this dataset
        offers_raw = item.get("offers") or []
        offer_ids = [
            o.get("identifiant_offre") for o in offers_raw if o.get("identifiant_offre") is not None
        ]
        offer_names = [
            o.get("nom_commercial", "").strip() for o in offers_raw if o.get("nom_commercial")
        ]

        for _, res in enumerate(item.get("resources") or []):
            if not res.get("is_available", True):
                continue
            fmt = (res.get("format") or "").strip()
            if fmt.upper() != "GTFS":
                continue

            metadata = res.get("metadata") or {}
            datagouv_id = res.get("datagouv_id")

            if datagouv_id in seen_datagouv_ids:
                duplicates.append(datagouv_id)
            else:
                seen_datagouv_ids.append(datagouv_id)

            rows.append({
                "id": item.get("id"),
                "datagouv_id": item.get("datagouv_id"),
                "title": item.get("title"),
                "slug": item.get("slug"),
                "page_url": item.get("page_url"),
                "publisher_name": publisher.get("name"),
                "resources_id": res.get("id"),
                "resources_datagouv_id": datagouv_id,
                "resources_title": res.get("title"),
                "resources_type": res.get("type"),
                "resources_updated": res.get("updated"),
                "resources_url": res.get("url"),
                "resources_original_url": res.get("original_url"),
                "resources_page_url": res.get("page_url"),
                "resources_community_resource_publisher": res.get("community_resource_publisher"),
                "resources_features": res.get("features"),
                "resources_modes": res.get("modes"),
                "start_date": metadata.get("start_date"),
                "end_date": metadata.get("end_date"),
                "stops_count": metadata.get("stops_count"),
                "categorie_geo": categorie_geo,
                "covered_area": covered_area,
                "is_scolaire": any(st == "school" for st in sub_types),
                "is_saisonnier": any(st == "seasonal" for st in sub_types),
                "is_agregat": any(t == "agrégat_region" for t in tags_list),
                "offer_ids": offer_ids,
                "offer_names": offer_names,
                "legal_owners": item.get("legal_owners"),
                "created_at": item.get("created_at"),
                "updated": item.get("updated"),
            })
            # TODO : mettre resources au singulier, traduire en anglais

    if duplicates:
        log.warning(
            "Found duplicates in resources_datagouv_id : %s",
            ", ".join(str(d) for d in set(duplicates)),
        )

    log.info("%d available resources GTFS after filtering.", len(rows))
    return pl.DataFrame(rows)
