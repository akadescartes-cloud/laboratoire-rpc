
import os
import threading
from concurrent import futures

import grpc
import requests
from flask import Flask, jsonify, render_template_string, request

import laboratoire_pb2
import laboratoire_pb2_grpc


# =========================================================
# CONFIGURATION
# =========================================================

PORT = int(os.environ.get("PORT", "10000"))
GRPC_PORT = int(os.environ.get("GRPC_PORT", "50051"))

URL_CONSULTATION = (
    "https://serviceconsultation.onrender.com/api/notifs"
)

app = Flask(__name__)


# =========================================================
# DONNEES DE DEMONSTRATION DU LABORATOIRE
# =========================================================

RESULTATS = {
    101: {
        "patient_id": 101,
        "analyse": "Glycemie",
        "valeur": "0.95 g/L",
        "statut": "Disponible",
    },
    102: {
        "patient_id": 102,
        "analyse": "Hemoglobine",
        "valeur": "13.5 g/dL",
        "statut": "Disponible",
    },
}


def obtenir_resultat(patient_id):
    """Retourne le resultat d'un patient ou None."""
    return RESULTATS.get(patient_id)


# =========================================================
# SERVICE gRPC
# =========================================================

class LaboratoireService(
    laboratoire_pb2_grpc.LaboratoireServicer
):
    def ObtenirResultat(self, requete, contexte):
        resultat = obtenir_resultat(requete.patient_id)

        if resultat is None:
            contexte.abort(
                grpc.StatusCode.NOT_FOUND,
                "Aucun resultat pour ce patient."
            )

        return laboratoire_pb2.Resultat(
            patient_id=resultat["patient_id"],
            analyse=resultat["analyse"],
            valeur=resultat["valeur"],
            statut=resultat["statut"],
        )


def demarrer_grpc():
    """Demarre le serveur gRPC."""
    serveur = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10)
    )

    laboratoire_pb2_grpc.add_LaboratoireServicer_to_server(
        LaboratoireService(),
        serveur
    )

    serveur.add_insecure_port(f"[::]:{GRPC_PORT}")
    serveur.start()

    print(f"Serveur gRPC demarre sur le port {GRPC_PORT}")

    serveur.wait_for_termination()


# =========================================================
# INTERFACE WEB
# =========================================================

PAGE_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>Laboratoire médical</title>

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #f1f5f9;
            color: #1e293b;
        }

        header {
            background: #087f8c;
            color: white;
            padding: 25px 15px;
            text-align: center;
        }

        main {
            max-width: 750px;
            margin: 35px auto;
            padding: 0 15px;
        }

        .card {
            background: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 14px;
            box-shadow: 0 4px 15px #0000000d;
        }

        h2 {
            margin-top: 0;
            color: #087f8c;
        }

        label {
            display: block;
            margin: 15px 0 7px;
            font-weight: bold;
        }

        input {
            width: 100%;
            padding: 12px;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            font-size: 16px;
        }

        button {
            width: 100%;
            margin-top: 18px;
            padding: 13px;
            border: none;
            border-radius: 8px;
            background: #087f8c;
            color: white;
            font-size: 16px;
            cursor: pointer;
        }

        button:hover {
            background: #066874;
        }

        .resultat {
            margin-top: 20px;
            padding: 15px;
            background: #ecfeff;
            border-radius: 8px;
            white-space: pre-wrap;
        }

        .message {
            margin-top: 15px;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
        }

        footer {
            text-align: center;
            padding: 20px;
            color: #64748b;
        }
    </style>
</head>

<body>
    <header>
        <h1>Laboratoire médical</h1>
        <p>Consultation des résultats d'analyses</p>
    </header>

    <main>
        <section class="card">
            <h2>Consulter un résultat</h2>

            <label for="patient_id">Identifiant du patient</label>
            <input
                id="patient_id"
                type="number"
                min="1"
                placeholder="Exemple : 101"
            >

            <button onclick="consulterResultat()">
                Consulter
            </button>

            <div id="resultat" class="resultat">
                Entre un identifiant pour afficher le résultat.
            </div>
        </section>

        <section class="card">
            <h2>Notifier le service Consultation</h2>

            <p>
                Envoie une notification quand un résultat est disponible.
            </p>

            <label for="notif_patient_id">
                Identifiant du patient
            </label>
            <input
                id="notif_patient_id"
                type="number"
                min="1"
                placeholder="Exemple : 101"
            >

            <label for="id_dossier">
                Identifiant du dossier Consultation
            </label>
            <input
                id="id_dossier"
                type="text"
                placeholder="Exemple : D001"
            >

            <label for="id_resultat">
                Identifiant du résultat
            </label>
            <input
                id="id_resultat"
                type="text"
                placeholder="Exemple : RES-42"
            >

            <button onclick="envoyerNotification()">
                Envoyer la notification
            </button>

            <div id="notification" class="message"></div>
        </section>
    </main>

    <footer>
        Projet RPC — Service Laboratoire
    </footer>

    <script>
        async function consulterResultat() {
            const id = document.getElementById("patient_id").value;
            const affichage = document.getElementById("resultat");

            if (!id) {
                affichage.textContent = "Entre un identifiant de patient.";
                return;
            }

            affichage.textContent = "Recherche en cours...";

            try {
                const reponse = await fetch("/api/resultats/" + id);
                const donnees = await reponse.json();

                if (!reponse.ok) {
                    affichage.textContent =
                        donnees.erreur || "Résultat introuvable.";
                    return;
                }

                affichage.textContent =
                    "Patient : " + donnees.patient_id + "\\n" +
                    "Analyse : " + donnees.analyse + "\\n" +
                    "Valeur : " + donnees.valeur + "\\n" +
                    "Statut : " + donnees.statut;
            } catch (erreur) {
                affichage.textContent =
                    "Erreur réseau : impossible de contacter le laboratoire.";
            }
        }

        async function envoyerNotification() {
            const patientId =
                document.getElementById("notif_patient_id").value;

            const idDossier =
                document.getElementById("id_dossier").value.trim();

            const idResultat =
                document.getElementById("id_resultat").value.trim();

            const affichage =
                document.getElementById("notification");

            if (!patientId || !idDossier || !idResultat) {
                affichage.textContent =
                    "Remplis les trois champs avant l'envoi.";
                return;
            }

            affichage.textContent = "Envoi en cours...";

            try {
                const reponse = await fetch("/api/notifier-resultat", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        patient_id: Number(patientId),
                        id_dossier: idDossier,
                        id_resultat: idResultat
                    })
                });

                const donnees = await reponse.json();

                if (!reponse.ok) {
                    affichage.textContent =
                        "Échec : " +
                        (donnees.erreur || "notification non envoyée.");
                    return;
                }

                affichage.textContent =
                    "Notification envoyée à Consultation.\\n" +
                    "Identifiant : " +
                    (donnees.id_notif || "non communiqué");
            } catch (erreur) {
                affichage.textContent =
                    "Erreur réseau : impossible de contacter le laboratoire.";
            }
        }
    </script>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def accueil():
    return render_template_string(PAGE_HTML)


# =========================================================
# API REST DU LABORATOIRE
# =========================================================

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "laboratoire"
    }), 200


@app.route("/api/resultats/<int:patient_id>", methods=["GET"])
def api_obtenir_resultat(patient_id):
    resultat = obtenir_resultat(patient_id)

    if resultat is None:
        return jsonify({
            "erreur": "Aucun resultat pour ce patient."
        }), 404

    return jsonify(resultat), 200


# =========================================================
# NOTIFICATION DU SERVICE CONSULTATION
# =========================================================

def notifier_consultation(id_dossier, id_resultat):
    """
    Envoie le résultat au service Consultation par REST.
    Le type L signifie Laboratoire.
    """

    donnees = {
        "id_dossier": id_dossier,
        "id_resultat": id_resultat,
        "type": "L"
    }

    try:
        reponse = requests.post(
            URL_CONSULTATION,
            json=donnees,
            timeout=5
        )

        if not reponse.ok:
            return {
                "succes": False,
                "erreur": (
                    f"Consultation a répondu avec le code "
                    f"{reponse.status_code}."
                )
            }

        try:
            resultat = reponse.json()
        except ValueError:
            resultat = {}

        return {
            "succes": True,
            "donnees": resultat
        }

    except requests.Timeout:
        return {
            "succes": False,
            "erreur": "Délai dépassé : Consultation n'a pas répondu à temps."
        }

    except requests.RequestException as erreur:
        return {
            "succes": False,
            "erreur": f"Erreur réseau vers Consultation : {erreur}"
        }


@app.route("/api/notifier-resultat", methods=["POST"])
def api_notifier_resultat():
    donnees = request.get_json(silent=True)

    if not isinstance(donnees, dict):
        return jsonify({
            "erreur": "Le corps de la requête doit être un JSON valide."
        }), 400

    patient_id = donnees.get("patient_id")
    id_dossier = donnees.get("id_dossier")
    id_resultat = donnees.get("id_resultat")

    if patient_id is None or not id_dossier or not id_resultat:
        return jsonify({
            "erreur": (
                "Les champs patient_id, id_dossier et id_resultat "
                "sont obligatoires."
            )
        }), 400

    try:
        patient_id = int(patient_id)
    except (TypeError, ValueError):
        return jsonify({
            "erreur": "patient_id doit être un nombre entier."
        }), 400

    resultat = obtenir_resultat(patient_id)

    if resultat is None:
        return jsonify({
            "erreur": "Impossible de notifier : patient inconnu."
        }), 404

    notification = notifier_consultation(
        str(id_dossier),
        str(id_resultat)
    )

    if not notification["succes"]:
        return jsonify({
            "erreur": notification["erreur"]
        }), 502

    reponse_consultation = notification["donnees"]

    return jsonify({
        "message": "Notification envoyée au service Consultation.",
        "patient_id": patient_id,
        "id_dossier": str(id_dossier),
        "id_resultat": str(id_resultat),
        "type": "L",
        "id_notif": reponse_consultation.get("id_notif")
    }), 200


# =========================================================
# DEMARRAGE DES SERVICES
# =========================================================

if __name__ == "__main__":
    thread_grpc = threading.Thread(
        target=demarrer_grpc,
        daemon=True
    )
    thread_grpc.start()

    print(f"Interface web et API REST sur le port {PORT}")

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False
    )
