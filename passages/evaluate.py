"""Comparaison d'un run avec une annotation humaine (protocole E1 v2).

Les erreurs sont comptées séparément (manqués, ajouts, sens inversés) : un total juste peut masquer des erreurs
qui se compensent.
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

import passages
from passages.config import sha256_fichier
from passages.crossing import ANNULE_RETOUR, PASSAGE, appliquer_maintien, deriver_passages_machine
from passages.run import RACINE, charger_run, ecrire_json
from passages.versions import etat_git
from passages.video import format_temps

MAINTIENS_SENSIBILITE = [0, 500, 1000, 2000]


def charger_reference(chemin: str | Path) -> dict:
    with open(chemin, encoding="utf-8") as f:
        ref = json.load(f)
    if ref.get("format") != "annotation_passages" or ref.get("version_format") != 2:
        raise ValueError("annotation attendue : format annotation_passages, version_format 2")
    if ref.get("nature") != "verite_terrain_humaine" or ref.get("detecteur_affiche") is not False:
        raise ValueError("la référence doit être une annotation humaine faite sans affichage du détecteur")
    if ref.get("non_observable_ouvert"):
        raise ValueError("un intervalle non observable est resté ouvert dans l'annotation")
    return ref


def chaines_reference(franchissements: list[dict]) -> tuple[list[list[dict]], list[str]]:
    par_id = {f["id"]: f for f in franchissements}
    racine = {}
    for f in sorted(franchissements, key=lambda f: f["t_ms"]):
        r = f["id"]
        vus = set()
        while par_id.get(r, {}).get("retour_de") and r not in vus:
            vus.add(r)
            r = par_id[r]["retour_de"]
        racine[f["id"]] = r
    groupes = defaultdict(list)
    for f in franchissements:
        groupes[(f["ligne"], racine[f["id"]])].append(f)
    chaines, alertes = [], []
    for chaine in groupes.values():
        chaine.sort(key=lambda f: f["t_ms"])
        for a, b in zip(chaine, chaine[1:]):
            if a["direction"] == b["direction"]:
                alertes.append(f"chaîne de retour {a['id']} -> {b['id']} : deux franchissements de même sens")
        chaines.append(chaine)
    return chaines, alertes


def passages_reference(ref: dict, maintien_ms: int) -> list[dict]:
    chaines, _ = chaines_reference(ref["franchissements"])
    out = []
    for chaine in chaines:
        for f, st in zip(chaine, appliquer_maintien(chaine, maintien_ms, None, False)):
            out.append({"id": f["id"], "ligne": f["ligne"], "direction": f["direction"], "t_ms": f["t_ms"],
                        "statut": st, "incertain": f.get("incertain", False)})
    return sorted(out, key=lambda p: p["t_ms"])


def fenetres_valides(ref: dict, fin_analyse_ms: int, marge_ms: int) -> list[tuple[int, int]]:
    plages = [(p["debut_ms"], min(p["fin_ms"], fin_analyse_ms)) for p in ref["plages_couvertes"]]
    exclus = sorted((n["debut_ms"] - marge_ms, n["fin_ms"] + marge_ms) for n in ref["non_observables"])
    out = []
    for a, b in plages:
        a, b = a + marge_ms, b - marge_ms
        morceaux = [(a, b)]
        for xa, xb in exclus:
            nouveaux = []
            for ma, mb in morceaux:
                if xb <= ma or xa >= mb:
                    nouveaux.append((ma, mb))
                    continue
                if xa > ma:
                    nouveaux.append((ma, xa))
                if xb < mb:
                    nouveaux.append((xb, mb))
            morceaux = nouveaux
        out.extend((ma, mb) for ma, mb in morceaux if mb > ma)
    return out


def dans(t: int, fenetres: list[tuple[int, int]]) -> bool:
    return any(a <= t <= b for a, b in fenetres)


def apparier(ref: list[dict], mach: list[dict], tolerance_ms: int) -> list[tuple[int, int]]:
    """Appariement un pour un, même ligne et même sens, |Δt| ≤ tolérance, somme des |Δt| minimale."""
    paires = []
    cles = {(p["ligne"], p["direction"]) for p in ref} | {(p["ligne"], p["direction"]) for p in mach}
    for cle in cles:
        ir = [i for i, p in enumerate(ref) if (p["ligne"], p["direction"]) == cle]
        im = [j for j, p in enumerate(mach) if (p["ligne"], p["direction"]) == cle]
        if not ir or not im:
            continue
        cout = np.full((len(ir), len(im)), 1e9)
        for a, i in enumerate(ir):
            for b, j in enumerate(im):
                d = abs(mach[j]["t_ms"] - ref[i]["t_ms"])
                if d <= tolerance_ms:
                    cout[a, b] = d
        lignes, colonnes = linear_sum_assignment(cout)
        paires += [(ir[a], im[b]) for a, b in zip(lignes, colonnes) if cout[a, b] <= tolerance_ms]
    return sorted(paires)


def comparer_un_maintien(ref_doc: dict, ev: dict, maintien_ms: int, tolerance_ms: int, fin_analyse_ms: int,
                         pas_ms: float, marge_ms: int) -> dict:
    fin_pistes = {int(k): v["fin_ms"] for k, v in ev["pistes"].items()}
    tous_mach = deriver_passages_machine(ev["franchissements"], fin_pistes, fin_analyse_ms, pas_ms, maintien_ms)
    tous_ref = passages_reference(ref_doc, maintien_ms)
    fenetres = fenetres_valides(ref_doc, fin_analyse_ms, marge_ms)
    ref = [p for p in tous_ref if p["statut"] == PASSAGE and dans(p["t_ms"], fenetres)]
    mach = [p for p in tous_mach if p["statut"] == PASSAGE and dans(p["t_ms"], fenetres)]
    paires = apparier(ref, mach, tolerance_ms)
    ir_ok = {i for i, _ in paires}
    im_ok = {j for _, j in paires}
    manques = [i for i in range(len(ref)) if i not in ir_ok]
    ajouts = [j for j in range(len(mach)) if j not in im_ok]

    inversions = []
    for i in list(manques):
        for j in list(ajouts):
            if mach[j]["ligne"] == ref[i]["ligne"] and mach[j]["direction"] != ref[i]["direction"] \
                    and abs(mach[j]["t_ms"] - ref[i]["t_ms"]) <= tolerance_ms:
                inversions.append((i, j))
                manques.remove(i)
                ajouts.remove(j)
                break

    retenus_apparies = [mach[j] for j in im_ok]
    annules_ref = [p for p in tous_ref if p["statut"] == ANNULE_RETOUR]
    demi_tours = ref_doc.get("demi_tours", [])
    fenetre_doublon = ev["regle_passage"].get("fenetre_doublon_ms", 1500)
    detail_ajouts = []
    for j in ajouts:
        m = mach[j]
        if any(a["direction"] == m["direction"] and a["ligne"] == m["ligne"] and a["piste"] != m["piste"]
               and abs(a["t_ms"] - m["t_ms"]) <= fenetre_doublon for a in retenus_apparies):
            cause = "doublon_probable"
        elif any(abs(d["t_ms"] - m["t_ms"]) <= tolerance_ms for d in demi_tours) or \
                any(abs(a["t_ms"] - m["t_ms"]) <= tolerance_ms for a in annules_ref):
            cause = "demi_tour_ou_retour_compte"
        else:
            cause = "ajout_isole"
        detail_ajouts.append({**m, "cause_probable": cause})
    detail_manques = []
    for i in manques:
        r = ref[i]
        proches = [m for m in tous_mach if m["ligne"] == r["ligne"] and m["direction"] == r["direction"]
                   and abs(m["t_ms"] - r["t_ms"]) <= tolerance_ms and m["statut"] != PASSAGE]
        cause = f"franchissement_machine_{proches[0]['statut']}" if proches else "aucun_franchissement_machine"
        detail_manques.append({**r, "cause_probable": cause})

    ecarts = [mach[j]["t_ms"] - ref[i]["t_ms"] for i, j in paires]
    totaux = {}
    for sens in ("entree", "sortie"):
        nr = sum(p["direction"] == sens for p in ref)
        nm = sum(p["direction"] == sens for p in mach)
        totaux[sens] = {"reference": nr, "machine": nm, "ecart_net": nm - nr}
    return {
        "maintien_ms": maintien_ms,
        "fenetres_evaluees_ms": fenetres,
        "duree_evaluee_s": round(sum(b - a for a, b in fenetres) / 1000, 1),
        "reference_passages": len(ref),
        "machine_passages": len(mach),
        "apparies": len(paires),
        "manques": len(detail_manques),
        "ajouts": len(detail_ajouts),
        "sens_inverses": len(inversions),
        "totaux": totaux,
        "ecart_temporel_ms": {
            "n": len(ecarts),
            "median": statistics.median(ecarts) if ecarts else None,
            "min": min(ecarts) if ecarts else None,
            "max": max(ecarts) if ecarts else None,
            "moyenne_abs": round(sum(abs(e) for e in ecarts) / len(ecarts), 1) if ecarts else None,
        },
        "detail_apparies": [{"reference": ref[i]["id"], "machine": mach[j]["franchissement"], "piste": mach[j]["piste"],
                             "direction": ref[i]["direction"], "t_ref_ms": ref[i]["t_ms"], "t_machine_ms": mach[j]["t_ms"],
                             "reference_incertaine": ref[i]["incertain"]} for i, j in paires],
        "detail_manques": detail_manques,
        "detail_ajouts": detail_ajouts,
        "detail_sens_inverses": [{"reference": ref[i], "machine": mach[j]} for i, j in inversions],
        "_ref": ref, "_mach": mach,
    }


def par_minute(res: dict) -> list[dict]:
    lignes = defaultdict(lambda: {"reference": 0, "machine": 0, "manques": 0, "ajouts": 0, "sens_inverses": 0})
    for p in res["_ref"]:
        lignes[p["t_ms"] // 60000]["reference"] += 1
    for p in res["_mach"]:
        lignes[p["t_ms"] // 60000]["machine"] += 1
    for p in res["detail_manques"]:
        lignes[p["t_ms"] // 60000]["manques"] += 1
    for p in res["detail_ajouts"]:
        lignes[p["t_ms"] // 60000]["ajouts"] += 1
    for p in res["detail_sens_inverses"]:
        lignes[p["reference"]["t_ms"] // 60000]["sens_inverses"] += 1
    return [{"minute": m, **v, "ecart_net": v["machine"] - v["reference"],
             "erreurs_brutes": v["manques"] + v["ajouts"] + 2 * v["sens_inverses"]} for m, v in sorted(lignes.items())]


def comparer(dossier_run: str, chemin_reference: str, maintien_ms: int | None, tolerance_ms: int, afficher=print) -> Path:
    d, manifeste, ev = charger_run(dossier_run)
    ref_doc = charger_reference(chemin_reference)
    if ref_doc["video"]["sha256"].upper() != manifeste["video"]["sha256"].upper():
        raise ValueError("l'annotation et le run ne portent pas sur la même vidéo")
    _, alertes = chaines_reference(ref_doc["franchissements"])
    maintien = int(maintien_ms if maintien_ms is not None else ev["regle_passage"]["maintien_ms"])
    pas_ms = 1000 / float(manifeste["config"]["contenu"]["analyse"]["cadence_analyse"])
    fin = ev["temps"]["fin_analyse_ms"]
    maintiens = sorted(set(MAINTIENS_SENSIBILITE + [maintien]))
    marge = max(maintiens + [tolerance_ms])
    principal = comparer_un_maintien(ref_doc, ev, maintien, tolerance_ms, fin, pas_ms, marge)
    sensibilite = []
    for h in maintiens:
        r = comparer_un_maintien(ref_doc, ev, h, tolerance_ms, fin, pas_ms, marge)
        sensibilite.append({k: r[k] for k in ("maintien_ms", "duree_evaluee_s", "reference_passages", "machine_passages",
                                              "apparies", "manques", "ajouts", "sens_inverses")})
    minutes = par_minute(principal)
    for k in ("_ref", "_mach"):
        principal.pop(k)

    horodatage = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    dossier = d / "comparaisons"
    dossier.mkdir(exist_ok=True)
    base = dossier / f"{horodatage}_{Path(chemin_reference).stem}"
    resultat = {
        "format": "comparaison_passages",
        "version_format": 1,
        "cree_le_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": ev["run_id"],
        "outil": {"passages": passages.__version__, **etat_git(RACINE)},
        "reference": {"chemin": str(Path(chemin_reference).as_posix()), "sha256": sha256_fichier(chemin_reference).upper(),
                      "annotateur": ref_doc["annotateur"], "passe": ref_doc["passe"],
                      "role_echantillon": manifeste["config"]["contenu"]["video"].get("role_echantillon"),
                      "synthetique": bool(ref_doc.get("synthetique", False)),
                      "alertes": alertes},
        "parametres": {"maintien_ms": maintien, "tolerance_ms": tolerance_ms, "marge_bords_ms": marge,
                       "statut_maintien": "hypothese, appliquee identiquement a la reference et a la machine"},
        "resultat": principal,
        "par_minute": minutes,
        "sensibilite_maintien": sensibilite,
    }
    ecrire_json(base.with_suffix(".json"), resultat)
    base.with_suffix(".md").write_text(rapport_md(resultat), encoding="utf-8")
    afficher(rapport_md(resultat))
    return base.with_suffix(".md")


def rapport_md(c: dict) -> str:
    r = c["resultat"]
    role = c["reference"]["role_echantillon"]
    l = [f"# Comparaison run `{c['run_id']}` / annotation `{c['reference']['annotateur']}` passe {c['reference']['passe']}", ""]
    if c["reference"]["synthetique"]:
        l += ["> **Référence synthétique (test du logiciel).** Ces chiffres ne mesurent rien du système.", ""]
    if role != "evaluation":
        l += [f"> Extrait de rôle « {role} » : résultat mesuré sur un extrait qui peut servir au réglage. "
              "Ce n'est pas une évaluation sur données réservées.", ""]
    l += [f"- Maintien : {c['parametres']['maintien_ms']} ms (hypothèse, appliquée aux deux côtés) ; tolérance d'appariement : "
          f"{c['parametres']['tolerance_ms']} ms",
          f"- Durée évaluée : {r['duree_evaluee_s']} s (plages annotées, hors non observables et marges)",
          "", "## Erreurs séparées", "",
          "| Référence | Machine | Appariés | Manqués | Ajoutés | Sens inversés |", "|---|---|---|---|---|---|",
          f"| {r['reference_passages']} | {r['machine_passages']} | {r['apparies']} | {r['manques']} | {r['ajouts']} | {r['sens_inverses']} |",
          "", "| Sens | Référence | Machine | Écart net |", "|---|---|---|---|"]
    for sens, t in r["totaux"].items():
        l.append(f"| {sens} | {t['reference']} | {t['machine']} | {t['ecart_net']:+d} |")
    e = r["ecart_temporel_ms"]
    l += ["", f"Écart temporel machine − référence sur les appariés (ms) : n={e['n']}, médiane={e['median']}, "
              f"min={e['min']}, max={e['max']}, moyenne absolue={e['moyenne_abs']}", ""]
    if r["detail_manques"]:
        l += ["## Manqués", "", "| Réf. | t vidéo | Sens | Cause probable |", "|---|---|---|---|"]
        l += [f"| {m['id']} | {format_temps(m['t_ms'])} | {m['direction']} | {m['cause_probable']} |" for m in r["detail_manques"]]
        l.append("")
    if r["detail_ajouts"]:
        l += ["## Ajoutés", "", "| Franch. | Piste | t vidéo | Sens | Cause probable |", "|---|---|---|---|---|"]
        l += [f"| {a['franchissement']} | {a['piste']} | {format_temps(a['t_ms'])} | {a['direction']} | {a['cause_probable']} |"
              for a in r["detail_ajouts"]]
        l.append("")
    if r["detail_sens_inverses"]:
        l += ["## Sens inversés", ""]
        l += [f"- réf. {x['reference']['id']} {x['reference']['direction']} {format_temps(x['reference']['t_ms'])} / machine "
              f"{x['machine']['franchissement']} {x['machine']['direction']}" for x in r["detail_sens_inverses"]]
        l.append("")
    l += ["## Par minute (un total juste peut masquer des erreurs qui se compensent)", "",
          "| Minute | Réf. | Machine | Écart net | Manqués | Ajoutés | Inversés | Erreurs brutes |", "|---|---|---|---|---|---|---|---|"]
    l += [f"| {m['minute']} | {m['reference']} | {m['machine']} | {m['ecart_net']:+d} | {m['manques']} | {m['ajouts']} | "
          f"{m['sens_inverses']} | {m['erreurs_brutes']} |" for m in c["par_minute"]]
    l += ["", "## Sensibilité au maintien (hypothèse)", "",
          "| Maintien ms | Durée évaluée s | Réf. | Machine | Appariés | Manqués | Ajoutés | Inversés |", "|---|---|---|---|---|---|---|---|"]
    l += [f"| {s['maintien_ms']} | {s['duree_evaluee_s']} | {s['reference_passages']} | {s['machine_passages']} | {s['apparies']} | "
          f"{s['manques']} | {s['ajouts']} | {s['sens_inverses']} |" for s in c["sensibilite_maintien"]]
    if c["reference"]["alertes"]:
        l += ["", "## Alertes sur l'annotation", ""] + [f"- {a}" for a in c["reference"]["alertes"]]
    return "\n".join(l) + "\n"
