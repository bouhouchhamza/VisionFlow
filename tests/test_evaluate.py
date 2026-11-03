"""Tests N0 (données synthétiques) de la comparaison avec une annotation humaine."""

from passages.evaluate import apparier, comparer_un_maintien, fenetres_valides, passages_reference


def ref_doc(franchissements, non_observables=(), demi_tours=(), fin_ms=60000):
    return {
        "franchissements": list(franchissements),
        "non_observables": list(non_observables),
        "demi_tours": list(demi_tours),
        "plages_couvertes": [{"debut_ms": 0, "fin_ms": fin_ms, "debut_image": 0, "fin_image": fin_ms // 33}],
    }


def fr_ref(id_, t, direction="entree", retour_de=None):
    return {"id": id_, "ligne": "l", "direction": direction, "t_ms": t, "retour_de": retour_de, "incertain": False}


def evenements(franchissements, pistes):
    return {"franchissements": franchissements, "pistes": pistes, "regle_passage": {"fenetre_doublon_ms": 1500}}


def fr_mach(id_, piste, t, direction="entree"):
    return {"id": id_, "ligne": "l", "piste": piste, "direction": direction, "t_ms": t}


def test_appariement_un_pour_un():
    ref = [{"ligne": "l", "direction": "entree", "t_ms": 1000}, {"ligne": "l", "direction": "entree", "t_ms": 1500}]
    mach = [{"ligne": "l", "direction": "entree", "t_ms": 1450}]
    assert apparier(ref, mach, 1000) == [(1, 0)]


def test_total_juste_mais_erreurs_compensees():
    ref = ref_doc([fr_ref("f1", 10000), fr_ref("f2", 30000)])
    ev = evenements([fr_mach("m1", 1, 10100), fr_mach("m2", 2, 45000)], {"1": {"fin_ms": 15000}, "2": {"fin_ms": 50000}})
    r = comparer_un_maintien(ref, ev, 1000, 1000, 60000, 100, 2000)
    assert r["totaux"]["entree"]["ecart_net"] == 0
    assert (r["apparies"], r["manques"], r["ajouts"]) == (1, 1, 1)


def test_sens_inverse_compte_a_part():
    ref = ref_doc([fr_ref("f1", 10000, "entree")])
    ev = evenements([fr_mach("m1", 1, 10200, "sortie")], {"1": {"fin_ms": 15000}})
    r = comparer_un_maintien(ref, ev, 1000, 1000, 60000, 100, 2000)
    assert (r["manques"], r["ajouts"], r["sens_inverses"]) == (0, 0, 1)


def test_doublon_probable():
    ref = ref_doc([fr_ref("f1", 10000)])
    ev = evenements([fr_mach("m1", 1, 10100), fr_mach("m2", 2, 10600)], {"1": {"fin_ms": 15000}, "2": {"fin_ms": 15000}})
    r = comparer_un_maintien(ref, ev, 1000, 1000, 60000, 100, 2000)
    assert r["ajouts"] == 1 and r["detail_ajouts"][0]["cause_probable"] == "doublon_probable"


def test_retour_reference_annule_avec_maintien():
    ref = ref_doc([fr_ref("f1", 10000, "entree"), fr_ref("f2", 10500, "sortie", retour_de="f1")])
    assert [p["statut"] for p in passages_reference(ref, 1000)] == ["annule_par_retour"] * 2
    assert [p["statut"] for p in passages_reference(ref, 0)] == ["passage"] * 2


def test_machine_compte_un_demi_tour():
    ref = ref_doc([], demi_tours=[{"id": "d1", "ligne": "l", "t_ms": 20000}])
    ev = evenements([fr_mach("m1", 1, 20100)], {"1": {"fin_ms": 30000}})
    r = comparer_un_maintien(ref, ev, 1000, 1000, 60000, 100, 2000)
    assert r["detail_ajouts"][0]["cause_probable"] == "demi_tour_ou_retour_compte"


def test_non_observable_exclu_des_deux_cotes():
    ref = ref_doc([fr_ref("f1", 20000)], non_observables=[{"debut_ms": 19000, "fin_ms": 22000}])
    ev = evenements([fr_mach("m1", 1, 40000)], {"1": {"fin_ms": 45000}})
    r = comparer_un_maintien(ref, ev, 1000, 1000, 60000, 100, 2000)
    assert (r["reference_passages"], r["machine_passages"], r["ajouts"]) == (0, 1, 1)


def test_fenetres_valides():
    ref = ref_doc([], non_observables=[{"debut_ms": 20000, "fin_ms": 25000}], fin_ms=60000)
    assert fenetres_valides(ref, 50000, 1000) == [(1000, 19000), (26000, 49000)]
