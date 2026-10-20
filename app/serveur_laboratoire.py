
import os
import threading
from concurrent import futures

import grpc
from flask import Flask

from app import laboratoire_pb2
from app import laboratoire_pb2_grpc


# Données fictives du laboratoire pour les tests
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
# API REST avec Flask
# =========================

app = Flask(__name__)


@app.route("/", methods=["GET"])
def accueil():
    return {
        "message": "Service Laboratoire OK",
        "endpoints": {
            "health": "/health",
            "resultat_patient_101": "/api/resultats/101",
            "resultat_patient_102": "/api/resultats/102",
        },
    }, 200


@app.route("/health", methods=["GET"])
def health():
    return {
        "status": "ok",
        "service": "laboratoire",
    }, 200


@app.route("/api/resultats/<int:patient_id>", methods=["GET"])
def obtenir_resultat_rest(patient_id):
    if patient_id not in RESULTATS:
        return {
            "erreur": f"Aucun resultat pour le patient {patient_id}"
        }, 404

    resultat = RESULTATS[patient_id]

    return {
        "patient_id": patient_id,
        "analyse": resultat["analyse"],
        "valeur": resultat["valeur"],
        "statut": resultat["statut"],
    }, 200


# =========================
# Démarrage des deux services
# =========================

def demarrer_serveur():

    # Serveur HTTP/REST pour Render
    port_http = int(os.environ.get("PORT", "10000"))

    serveur_http = threading.Thread(
        target=lambda: app.run(
            host="0.0.0.0",
            port=port_http,
            use_reloader=False,
        ),
        daemon=True,
    )
    serveur_http.start()

    # Serveur gRPC
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
