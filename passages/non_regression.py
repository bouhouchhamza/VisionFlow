"""Non-régression technique entre deux runs : même comportement, pas même justesse.

Compare un run candidat à un run de référence, en lecture seule sur les deux. Les rapports sont écrits ailleurs
(par défaut `runs/non_regression/comparaisons/`), jamais dans le dossier d'un des deux runs.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from passages import versions
from passages.run import RACINE, charger_run, ecrire_json

IDENTIQUE, ECARTS_D_ARRONDI, DIFFERENT, NON_COMPARABLE = "IDENTIQUE", "ECARTS_D_ARRONDI", "DIFFERENT", "NON_COMPARABLE"

# Pas d'arrondi des valeurs écrites par `run.py` et `crossing.py` ; un écart d'au plus un pas est classé à part.
PAS_PIXEL, PAS_SCORE, PAS_U = 0.1, 1e-4, 1e-4
EPS = 1e-9

CHAMPS_EXACTS_IMAGE = ("num_image", "t_ms", "pts", "temps_reconstruit", "detections_brutes")
CHAMPS_EXACTS_FRANCHISSEMENT = ("id", "ligne", "piste", "sens_geometrique", "direction", "t_ms", "num_image",
                                "t_ms_avant", "num_image_avant")
BLOCS_EVENEMENTS_EXACTS = ("format", "version_format", "nature", "regle_passage", "temps", "passages_derives",
                           "doublons_probables", "pistes")
BLOCS_EVENEMENTS_TRONQUE = ("format", "version_format", "nature", "regle_passage")
EXCLUS = ("manifeste.run_id", "manifeste.cree_le_utc", "manifeste.commande", "manifeste.config.chemin",
          "manifeste.config.sha256_fichier", "manifeste.versions.git_*", "manifeste.versions.plateforme",
          "manifeste.execution.duree_calcul_s", "manifeste.execution.chronometrage_s",
          "manifeste.execution.vitesse_s_video_par_s_calcul", "evenements.run_id")


def charger(dossier: str | Path) -> dict:
    d, manifeste, evenements = charger_run(dossier)
    with open(d / "pistes.jsonl", encoding="utf-8") as f:
        pistes = [json.loads(l) for l in f if l.strip()]
    return {"dossier": d, "manifeste": manifeste, "evenements": evenements, "pistes": pistes}


def prealables(manifeste: dict, tronque: bool) -> dict:
    """Conditions sans lesquelles deux runs ne sont pas comparables (entrées, environnement, étendue)."""
    v, ver, ex = manifeste["video"], manifeste["versions"], manifeste["execution"]
    p = {
        "video.sha256": v["sha256"].upper(),
        "modele.sha256": manifeste["modele"]["sha256"].upper(),
        "config.sha256_canonique": manifeste["config"]["sha256_canonique"],
        "temps.mode": v["bilan_temps"]["mode"],
        "versions.python": ver.get("python"),
        "versions.paquets": ver.get("paquets"),
        "versions.processeur": ver.get("processeur"),
        "versions.coeurs_logiques": ver.get("coeurs_logiques"),
        "execution.threads_onnxruntime": ex.get("threads_onnxruntime"),
    }
    if not tronque:
        p["video.bilan_temps"] = v["bilan_temps"]
        p["execution.limite_s"] = ex.get("limite_s")
        p["execution.images_decodees"] = ex.get("images_decodees")
        p["execution.images_analysees"] = ex.get("images_analysees")
    return p


def _metadonnees(m: dict) -> dict:
    ex = m["execution"]
    return {
        "run_id": m["run_id"], "cree_le_utc": m.get("cree_le_utc"), "commande": m.get("commande"),
        "git_commit": m["versions"].get("git_commit"),
        "git_dirty": m["versions"].get("git_dirty", m["versions"].get("git_modifications_locales")),
        "plateforme": m["versions"].get("plateforme"), "duree_calcul_s": ex.get("duree_calcul_s"),
    }


class Releve:
    """Accumule les écarts d'un bloc : stricts (divergence réelle) ou d'un pas d'arrondi."""

    def __init__(self):
        self.stricts = 0
        self.arrondis = 0
        self.premier_strict: dict | None = None
        self.premier_arrondi: dict | None = None

    def strict(self, **ou):
        self.stricts += 1
        if self.premier_strict is None:
            self.premier_strict = ou

    def arrondi(self, **ou):
        self.arrondis += 1
        if self.premier_arrondi is None:
            self.premier_arrondi = ou

    def proche(self, a, b, pas: float, **ou):
        if a == b:
            return
        if a is None or b is None or abs(float(a) - float(b)) > pas + EPS:
            self.strict(attendu=a, obtenu=b, **ou)
        else:
            self.arrondi(attendu=a, obtenu=b, **ou)

    def en_dict(self) -> dict:
        return {"ecarts_stricts": self.stricts, "ecarts_arrondi": self.arrondis,
                "premiere_divergence": self.premier_strict, "premier_ecart_arrondi": self.premier_arrondi}


def comparer_pistes(ref: list[dict], cand: list[dict], jusqu_a_ms: int | None) -> dict:
    if jusqu_a_ms is not None:
        ref = [l for l in ref if l["t_ms"] <= jusqu_a_ms]
        cand = [l for l in cand if l["t_ms"] <= jusqu_a_ms]
    r = Releve()
    if len(ref) != len(cand):
        r.strict(champ="nombre_images_analysees", attendu=len(ref), obtenu=len(cand))
    for a, b in zip(ref, cand):
        lieu = {"num_image": a["num_image"], "t_ms": a["t_ms"]}
        for c in CHAMPS_EXACTS_IMAGE:
            if a[c] != b[c]:
                r.strict(champ=c, attendu=a[c], obtenu=b[c], **lieu)
        ids_a = [o["piste"] for o in a["objets"]]
        ids_b = [o["piste"] for o in b["objets"]]
        if ids_a != ids_b:
            r.strict(champ="pistes_de_l_image", attendu=ids_a, obtenu=ids_b, **lieu)
            continue
        for oa, ob in zip(a["objets"], b["objets"]):
            for k in range(4):
                r.proche(oa["boite"][k], ob["boite"][k], PAS_PIXEL, champ=f"boite[{k}]", piste=oa["piste"], **lieu)
            r.proche(oa["score"], ob["score"], PAS_SCORE, champ="score", piste=oa["piste"], **lieu)
    return {"images_comparees": min(len(ref), len(cand)), "images_reference": len(ref), "images_candidat": len(cand),
            **r.en_dict()}


def _cle(f: dict) -> tuple:
    return tuple(f[c] for c in CHAMPS_EXACTS_FRANCHISSEMENT if c != "id")


def comparer_franchissements(ref: list[dict], cand: list[dict], jusqu_a_ms: int | None) -> dict:
    if jusqu_a_ms is not None:
        ref = [f for f in ref if f["t_ms"] <= jusqu_a_ms]
        cand = [f for f in cand if f["t_ms"] <= jusqu_a_ms]
    r = Releve()
    if len(ref) != len(cand):
        r.strict(champ="nombre_franchissements", attendu=len(ref), obtenu=len(cand))
    for a, b in zip(ref, cand):
        lieu = {"franchissement": a["id"], "t_ms": a["t_ms"]}
        for c in CHAMPS_EXACTS_FRANCHISSEMENT:
            if a[c] != b[c]:
                r.strict(champ=c, attendu=a[c], obtenu=b[c], **lieu)
        r.proche(a["u"], b["u"], PAS_U, champ="u", **lieu)
        r.proche(a["confiance"], b["confiance"], PAS_SCORE, champ="confiance", **lieu)
        for k in range(2):
            r.proche(a["point"][k], b["point"][k], PAS_PIXEL, champ=f"point[{k}]", **lieu)
    cr, cc = Counter(map(_cle, ref)), Counter(map(_cle, cand))
    resume = lambda cles: [dict(zip(CHAMPS_EXACTS_FRANCHISSEMENT[1:], c)) for c in sorted(cles.elements())]
    return {"reference": len(ref), "candidat": len(cand), "manquants": resume(cr - cc),
            "supplementaires": resume(cc - cr), **r.en_dict()}


def statistiques(evenements: dict, jusqu_a_ms: int | None = None) -> dict:
    """Comptes recalculés depuis les événements ; en mode tronqué, seulement ceux qui ne dépendent pas de la fin."""
    fr = [f for f in evenements["franchissements"] if jusqu_a_ms is None or f["t_ms"] <= jusqu_a_ms]
    s = {
        "franchissements": len(fr),
        "franchissements_par_ligne_et_direction": dict(sorted(Counter(f"{f['ligne']}|{f['direction']}" for f in fr).items())),
        "franchissements_par_minute": dict(sorted(Counter(f"{f['t_ms'] // 60000:03d}|{f['direction']}" for f in fr).items())),
    }
    if jusqu_a_ms is None:
        ps = evenements["passages_derives"]
        retenus = [p for p in ps if p["statut"] == "passage"]
        s.update({
            "pistes": len(evenements["pistes"]),
            "passages_par_statut_et_direction": dict(sorted(Counter(f"{p['statut']}|{p['direction']}" for p in ps).items())),
            "passages_retenus_par_minute": dict(sorted(Counter(f"{p['t_ms'] // 60000:03d}|{p['direction']}"
                                                               for p in retenus).items())),
            "doublons_probables": len(evenements["doublons_probables"]),
        })
    return s


def comparer_runs(reference: str | Path, candidat: str | Path, jusqu_a_ms: int | None = None) -> dict:
    ref, cand = charger(reference), charger(candidat)
    tronque = jusqu_a_ms is not None
    pr, pc = prealables(ref["manifeste"], tronque), prealables(cand["manifeste"], tronque)
    prealables_differents = {k: {"reference": pr[k], "candidat": pc[k]} for k in pr if pr[k] != pc[k]}

    pistes = comparer_pistes(ref["pistes"], cand["pistes"], jusqu_a_ms)
    franchissements = comparer_franchissements(ref["evenements"]["franchissements"],
                                               cand["evenements"]["franchissements"], jusqu_a_ms)
    blocs = BLOCS_EVENEMENTS_TRONQUE if tronque else BLOCS_EVENEMENTS_EXACTS
    blocs_differents = [b for b in blocs if ref["evenements"].get(b) != cand["evenements"].get(b)]
    sr, sc = statistiques(ref["evenements"], jusqu_a_ms), statistiques(cand["evenements"], jusqu_a_ms)
    stats_differentes = {k: {"reference": sr[k], "candidat": sc[k]} for k in sr if sr[k] != sc[k]}

    stricts = pistes["ecarts_stricts"] + franchissements["ecarts_stricts"] + len(blocs_differents) + len(stats_differentes)
    arrondis = pistes["ecarts_arrondi"] + franchissements["ecarts_arrondi"]
    if prealables_differents:
        verdict = NON_COMPARABLE
    elif stricts:
        verdict = DIFFERENT
    elif arrondis:
        verdict = ECARTS_D_ARRONDI
    else:
        verdict = IDENTIQUE
    mr, mc = _metadonnees(ref["manifeste"]), _metadonnees(cand["manifeste"])
    return {
        "format": "non_regression_runs",
        "version_format": 1,
        "nature": "equivalence_de_comportement_pas_mesure_de_justesse",
        "verdict": verdict,
        "mode": "tronque" if tronque else "complet",
        "jusqu_a_ms": jusqu_a_ms,
        "reference": {"dossier": str(ref["dossier"]), **mr},
        "candidat": {"dossier": str(cand["dossier"]), **mc},
        "prealables_differents": prealables_differents,
        "pistes": pistes,
        "franchissements": franchissements,
        "blocs_evenements_compares": list(blocs),
        "blocs_evenements_differents": blocs_differents,
        "statistiques_reference": sr,
        "statistiques_differentes": stats_differentes,
        "metadonnees_differentes": sorted(k for k in mr if mr[k] != mc[k]),
        "exclus_de_la_comparaison": list(EXCLUS),
        "pas_arrondi": {"pixel": PAS_PIXEL, "score": PAS_SCORE, "u": PAS_U},
        "outil": {"cree_le_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), **versions.etat_git(RACINE)},
    }


def rapport_md(res: dict) -> str:
    l = [f"# Non-régression : {res['verdict']}", "",
         "Équivalence de comportement entre deux runs, **pas une mesure de justesse**.", "",
         f"- Référence : `{res['reference']['run_id']}` (commit `{res['reference']['git_commit']}`)",
         f"- Candidat : `{res['candidat']['run_id']}` (commit `{res['candidat']['git_commit']}`, "
         f"modifications locales : {res['candidat']['git_dirty']})",
         f"- Mode : {res['mode']}" + (f" (t_ms ≤ {res['jusqu_a_ms']})" if res["jusqu_a_ms"] is not None else ""), ""]
    if res["prealables_differents"]:
        l += ["## Préalables différents (runs non comparables)", ""]
        l += [f"- `{k}` : référence `{v['reference']}`, candidat `{v['candidat']}`"
              for k, v in res["prealables_differents"].items()] + [""]
    p, f = res["pistes"], res["franchissements"]
    l += ["## Écarts", "", "| Bloc | Stricts | Arrondi | Première divergence |", "|---|---|---|---|",
          f"| Pistes ({p['images_reference']} / {p['images_candidat']} images) | {p['ecarts_stricts']} | "
          f"{p['ecarts_arrondi']} | {p['premiere_divergence'] or ''} |",
          f"| Franchissements ({f['reference']} / {f['candidat']}) | {f['ecarts_stricts']} | {f['ecarts_arrondi']} | "
          f"{f['premiere_divergence'] or ''} |",
          f"| Blocs d'événements | {len(res['blocs_evenements_differents'])} | — | "
          f"{', '.join(res['blocs_evenements_differents'])} |",
          f"| Statistiques | {len(res['statistiques_differentes'])} | — | "
          f"{', '.join(res['statistiques_differentes'])} |", ""]
    if f["manquants"] or f["supplementaires"]:
        l += [f"Franchissements manquants : {f['manquants']}", "", f"Franchissements supplémentaires : {f['supplementaires']}", ""]
    l += [f"Métadonnées différentes (attendu, non comparées) : {', '.join(res['metadonnees_differentes']) or 'aucune'}", ""]
    return "\n".join(l)


def comparer_et_ecrire(reference: str, candidat: str, jusqu_a_ms: int | None = None, sortie: str | None = None,
                       afficher=print) -> dict:
    res = comparer_runs(reference, candidat, jusqu_a_ms)
    nom = f"{Path(candidat).name}__vs__{Path(reference).name}" + (f"__jusqu_a_{jusqu_a_ms}" if jusqu_a_ms is not None else "")
    dossier = Path(sortie) if sortie else RACINE / "runs" / "non_regression" / "comparaisons"
    dossier = dossier.resolve()
    for run in (reference, candidat):
        if dossier == Path(run).resolve() or Path(run).resolve() in dossier.parents:
            raise ValueError(f"refus d'écrire dans le dossier d'un run comparé : {run}")
    dossier.mkdir(parents=True, exist_ok=True)
    ecrire_json(dossier / f"{nom}.json", res)
    (dossier / f"{nom}.md").write_text(rapport_md(res), encoding="utf-8")
    afficher(f"verdict : {res['verdict']}  (rapport : {dossier / nom}.md)")
    return res
