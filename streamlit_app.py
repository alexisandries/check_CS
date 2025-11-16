import re
import pandas as pd
import streamlit as st

# =========================
# Helpers
# =========================

def normalize_digits(x: str) -> str:
    """Garde uniquement les chiffres."""
    if x is None:
        return ""
    return re.sub(r"\D", "", str(x))


def visual_format(d12: str) -> str:
    """Formate 12 chiffres en +++123/4567/89012+++."""
    if len(d12) != 12 or not d12.isdigit():
        return ""
    return f"+++{d12[:3]}/{d12[3:7]}/{d12[7:]}+++"


def compute_mod97_check(first10: str) -> str:
    """Calcule les 2 chiffres de contrôle (Mod97) à partir des 10 premiers chiffres."""
    if len(first10) != 10 or not first10.isdigit():
        return ""
    base = int(first10)
    r = base % 97
    chk = 97 if r == 0 else r
    return f"{chk:02d}"


def check_structured_comm(digits: str) -> dict:
    """
    Vérifie un code structuré (12 chiffres attendus).
    Retourne un dict avec valid (bool) et reason (str).
    """
    info = {
        "digits": digits,
        "is_12_digits": False,
        "valid_checksum": False,
        "reason": "",
        "first10": "",
        "given_check": "",
        "calc_check": "",
        "visual_suggested": visual_format(digits),
    }

    if len(digits) != 12 or not digits.isdigit():
        info["reason"] = "Longueur différente de 12 chiffres"
        return info

    info["is_12_digits"] = True
    info["first10"] = digits[:10]
    info["given_check"] = digits[-2:]
    info["calc_check"] = compute_mod97_check(info["first10"])

    if info["calc_check"] == info["given_check"]:
        info["valid_checksum"] = True
        info["reason"] = ""
    else:
        info["reason"] = f"Checksum incorrect (attendu {info['calc_check']})"

    return info


# =========================
# UI Streamlit
# =========================

st.set_page_config(
    page_title="Vérification des communications structurées",
    layout="wide",
)

st.title("Vérification des communications structurées")

st.write(
    """
Collez ci-dessous une **colonne Excel** contenant vos communications structurées  
(une valeur par ligne, avec ou sans `+++`, `/`, espaces, etc.).

L’app va :
- nettoyer les valeurs (garder uniquement les chiffres),
- dédupliquer sur la base des **numéros** (digits),
- vérifier la validité Mod97,
- indiquer si tout est correct ou non,
- lister les numéros **uniques** incorrects.
"""
)

input_text = st.text_area(
    "Collez ici votre colonne Excel de communications structurées :",
    height=300,
    placeholder="Exemple :\n+++123/4567/89012+++\n+++740/1234/56789+++\n..."
)

if st.button("Lancer la vérification"):
    if not input_text.strip():
        st.warning("Veuillez d’abord coller au moins une valeur.")
    else:
        # 1) On récupère les lignes non vides
        lines = [line.strip() for line in input_text.splitlines()]
        lines = [line for line in lines if line]  # supprime les lignes vides

        if not lines:
            st.warning("Aucune valeur non vide détectée.")
        else:
            # 2) Normalisation -> digits
            rows = []
            for original in lines:
                digits = normalize_digits(original)
                if digits:  # on ignore les lignes qui ne donnent aucun chiffre
                    rows.append({"original": original, "digits": digits})

            if not rows:
                st.error("Aucune ligne ne contient de chiffres utilisables.")
            else:
                df_all = pd.DataFrame(rows)

                # 3) On déduplique sur base des 'digits'
                #    (on garde un exemple 'original' par numéro)
                df_unique = (
                    df_all
                    .sort_values("original")          # pour avoir un original "stable"
                    .drop_duplicates(subset="digits") # unique par numéro
                    .reset_index(drop=True)
                )

                # 4) Vérification de chaque numéro unique
                check_results = []
                for _, row in df_unique.iterrows():
                    info = check_structured_comm(row["digits"])
                    info["original_example"] = row["original"]
                    check_results.append(info)

                df_checked = pd.DataFrame(check_results)

                # 5) Statistiques globales
                n_total = len(df_checked)
                n_valid = int(df_checked["valid_checksum"].sum())
                n_invalid = n_total - n_valid

                if n_total > 0:
                    invalid_ratio = n_invalid / n_total * 100
                else:
                    invalid_ratio = 0.0

                # 6) Affichage résumé
                if n_total == 0:
                    st.warning("Aucun numéro unique à vérifier.")
                elif n_invalid == 0:
                    st.success(
                        f"✅ Tous les {n_total} numéros uniques sont **corrects** "
                        f"selon le calcul Mod97."
                    )
                else:
                    st.error(
                        f"❌ Erreur : {invalid_ratio:.2f}% des numéros **uniques** sont inexacts.\n\n"
                        f"- Total de numéros uniques : **{n_total}**\n"
                        f"- Valides : **{n_valid}**\n"
                        f"- Invalides : **{n_invalid}**"
                    )

                    st.markdown("#### Détail des numéros uniques **invalides**")
                    df_invalid = df_checked[~df_checked["valid_checksum"]].copy()

                    # colonnes les plus utiles
                    cols_out = [
                        "original_example",
                        "digits",
                        "reason",
                        "first10",
                        "given_check",
                        "calc_check",
                        "visual_suggested",
                    ]
                    df_invalid = df_invalid[cols_out]

                    st.dataframe(df_invalid, use_container_width=True)

                    # Option : liste brute des digits invalides
                    st.write(
                        "Numéros (digits) invalides : " +
                        ", ".join(df_invalid["digits"].tolist())
                    )
