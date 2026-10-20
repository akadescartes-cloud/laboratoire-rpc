
import os
import threading
from concurrent import futures

import grpc
from flask import Flask, jsonify, render_template_string

from app import laboratoire_pb2
from app import laboratoire_pb2_grpc


# Donnees fictives pour les tests
RESULTATS = {
    101: {
        "analyse": "Glycemie",
        "valeur": "0.95 g/L",
        "statut": "Disponible",
    },
    102: {
        "analyse": "Hemoglobine",
        "valeur": "13.5 g/dL",
        "statut": "Disponible",
    },
}


# =========================
# SERVICE gRPC
# =========================

class LaboratoireService(laboratoire_pb2_grpc.LaboratoireServicer):

    def ObtenirResultat(self, request, context):
        patient_id = request.patient_id

        if patient_id not in RESULTATS:
            context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Aucun resultat pour le patient {patient_id}",
            )

        resultat = RESULTATS[patient_id]

        return laboratoire_pb2.Resultat(
            patient_id=patient_id,
            analyse=resultat["analyse"],
            valeur=resultat["valeur"],
            statut=resultat["statut"],
        )


# =========================
# APPLICATION WEB ET REST
# =========================

app = Flask(__name__)


PAGE_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Laboratoire | Clinique Espoir</title>
    <style>
        * { box-sizing: border-box; }

        body {
            margin: 0;
            font-family: Arial, Helvetica, sans-serif;
            background: #f4f8fc;
            color: #18324b;
        }

        header {
            background: white;
            border-bottom: 1px solid #e4edf5;
            padding: 20px 7%;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
            font-weight: bold;
            font-size: 20px;
        }

        .logo {
            width: 42px;
            height: 42px;
            border-radius: 13px;
            background: #e2f3f5;
            display: grid;
            place-items: center;
            font-size: 23px;
        }

        .online {
            color: #16866f;
            background: #e6f7f1;
            padding: 9px 13px;
            border-radius: 30px;
            font-size: 13px;
        }

        main {
            max-width: 760px;
            margin: 65px auto;
            padding: 0 20px;
        }

        .intro { text-align: center; }

        .eyebrow {
            color: #168b9b;
            text-transform: uppercase;
            letter-spacing: 2px;
            font-size: 12px;
            font-weight: bold;
        }

        h1 {
            font-size: clamp(28px, 5vw, 40px);
            margin: 14px 0;
        }

        .subtitle {
            color: #718399;
            line-height: 1.7;
            margin-bottom: 35px;
        }

        .panel {
            background: white;
            padding: 28px;
            border-radius: 20px;
            box-shadow: 0 12px 40px rgba(36, 69, 100, 0.07);
            border: 1px solid #e8eff6;
        }

        label {
            display: block;
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 10px;
        }

        .search-row {
            display: flex;
            gap: 10px;
        }

        input {
            flex: 1;
            min-width: 0;
            padding: 15px;
            border: 1px solid #d8e3ed;
            border-radius: 10px;
            font-size: 16px;
            outline: none;
        }

        input:focus { border-color: #168b9b; }

        button {
            border: 0;
            border-radius: 10px;
            padding: 0 22px;
            background: #167e91;
            color: white;
            font-size: 15px;
            font-weight: bold;
            cursor: pointer;
        }

        button:hover { background: #106879; }
        button:disabled { opacity: 0.6; cursor: wait; }

        #message {
            margin-top: 18px;
            color: #b54747;
            font-size: 14px;
        }

        .result {
            display: none;
            margin-top: 25px;
            background: white;
            border: 1px solid #e0ebf2;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 12px 35px rgba(36, 69, 100, 0.06);
        }

        .result-head {
            padding: 20px 24px;
            border-bottom: 1px solid #edf2f7;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
        }

        .patient {
            font-size: 18px;
            font-weight: bold;
        }

        .badge {
            background: #e4f7ee;
            color: #16805e;
            padding: 8px 12px;
            border-radius: 30px;
            font-size: 12px;
            font-weight: bold;
        }

        .result-body { padding: 25px; }

        .analysis-label {
            color: #77899d;
            font-size: 13px;
        }

        .analysis {
            font-size: 23px;
            font-weight: bold;
            margin: 9px 0 20px;
        }

        .value-box {
            background: #f0f8fb;
            border-radius: 14px;
            padding: 20px;
        }

        .value {
            font-size: 32px;
            color: #167e91;
            font-weight: bold;
            margin-top: 8px;
        }

        footer {
            text-align: center;
            color: #8b9aab;
            font-size: 12px;
            padding: 30px 15px;
        }

        @media (max-width: 520px) {
            header { padding: 16px 5%; }
            main { margin-top: 38px; }
            .panel { padding: 20px; }
            .search-row { flex-direction: column; }
            button { padding: 15px; }
        }
    </style>
</head>
<body>
    <header>
        <div class="brand">
            <div class="logo">⚗</div>
            <div>Laboratoire</div>
        </div>
        <div class="online">● Service actif</div>
    </header>

    <main>
        <section class="intro">
            <div class="eyebrow">Clinique Espoir</div>
            <h1>Résultats d'analyses</h1>
            <p class="subtitle">
                Retrouvez rapidement un résultat de laboratoire
                à partir de l'identifiant du patient.
            </p>
        </section>

        <section class="panel">
            <label for="patientId">Identifiant du patient</label>
            <div class="search-row">
                <input
                    id="patientId"
                    type="number"
                    min="1"
                    placeholder="Ex. : 101"
                    value="101"
                >
                <button id="searchButton" onclick="rechercher()">
                    Rechercher
                </button>
            </div>
            <div id="message" role="status"></div>
        </section>

        <section id="result" class="result" aria-live="polite">
            <div class="result-head">
                <div class="patient" id="patient">Patient #101</div>
                <div class="badge" id="status">Disponible</div>
            </div>
            <div class="result-body">
                <div class="analysis-label">Analyse réalisée</div>
                <div class="analysis" id="analysis">Glycemie</div>
                <div class="value-box">
                    <div class="analysis-label">Résultat</div>
                    <div class="value" id="value">0.95 g/L</div>
                </div>
            </div>
        </section>
    </main>

    <footer>
        Laboratoire · API REST · Clinique Espoir
    </footer>

    <script>
        async function rechercher() {
            const input = document.getElementById("patientId");
            const button = document.getElementById("searchButton");
            const message = document.getElementById("message");
            const result = document.getElementById("result");
            const id = input.value.trim();

            message.textContent = "";
            result.style.display = "none";

            if (!id || !Number.isInteger(Number(id)) || Number(id) < 1) {
                message.textContent =
                    "Veuillez saisir un identifiant de patient valide.";
                return;
            }

            button.disabled = true;
            button.textContent = "Recherche...";
            
            try {
                const response = await fetch(
                    "/api/resultats/" + encodeURIComponent(id)
                );
                const data = await response.json();

                if (!response.ok) {
                    throw new Error(
                        data.erreur || "Résultat introuvable."
                    );
                }

                document.getElementById("patient").textContent =
                    "Patient #" + data.patient_id;
                document.getElementById("analysis").textContent =
                    data.analyse;
                document.getElementById("value").textContent =
                    data.valeur;
                document.getElementById("status").textContent =
                    data.statut;

                result.style.display = "block";
            } catch (error) {
                message.textContent =
                    error.message || "Impossible de contacter le service.";
            } finally {
                button.disabled = false;
                button.textContent = "Rechercher";
            }
        }

        document.getElementById("patientId").addEventListener(
            "keydown",
            function(event) {
                if (event.key === "Enter") rechercher();
            }
        );

        // Afficher le résultat initial du patient 101
        rechercher();
    </script>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def accueil():
    return render_template_string(PAGE_HTML)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "laboratoire",
    }), 200


@app.route("/api/resultats/<int:patient_id>", methods=["GET"])
def obtenir_resultat_rest(patient_id):
    if patient_id not in RESULTATS:
        return jsonify({
            "erreur": f"Aucun resultat pour le patient {patient_id}"
        }), 404

    resultat = RESULTATS[patient_id]

    return jsonify({
        "patient_id": patient_id,
        "analyse": resultat["analyse"],
        "valeur": resultat["valeur"],
        "statut": resultat["statut"],
    }), 200


# =========================
# DEMARRAGE DES SERVICES
# =========================

def demarrer_serveur():
    port_http = int(os.environ.get("PORT", "10000"))

    serveur_http = threading.Thread(
        target=lambda: app.run(
            host="0.0.0.0",
            port=port_http,
            use_reloader=False,
            threaded=True,
        ),
        daemon=True,
    )
    serveur_http.start()

    serveur_grpc = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10)
    )

    laboratoire_pb2_grpc.add_LaboratoireServicer_to_server(
        LaboratoireService(),
        serveur_grpc,
    )

    port_grpc = int(os.environ.get("GRPC_PORT", "50051"))
    port_ouvert = serveur_grpc.add_insecure_port(
        f"[::]:{port_grpc}"
    )

    if port_ouvert == 0:
        raise RuntimeError(
            f"Impossible d'ouvrir le port gRPC {port_grpc}"
        )

    serveur_grpc.start()

    print(f"Serveur REST demarre sur le port {port_http}")
    print(f"Serveur gRPC demarre sur le port {port_grpc}")

    serveur_grpc.wait_for_termination()


if __name__ == "__main__":
    demarrer_serveur()
