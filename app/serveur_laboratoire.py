
import os
import threading
from concurrent import futures

import grpc
from flask import Flask

from app import laboratoire_pb2
from app import laboratoire_pb2_grpc


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


app = Flask(__name__)


@app.route("/")
def accueil():
    return "Service Laboratoire OK", 200


@app.route("/health")
def health():
    return {"status": "ok", "service": "laboratoire"}, 200


def demarrer_serveur():
    # Serveur HTTP pour Render
    port_http = int(os.environ.get("PORT", "10000"))
    threading.Thread(
        target=lambda: app.run(
            host="0.0.0.0",
            port=port_http,
            use_reloader=False,
        ),
        daemon=True,
    ).start()

    # Serveur gRPC sur un port distinct
    serveur = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10)
    )

    laboratoire_pb2_grpc.add_LaboratoireServicer_to_server(
        LaboratoireService(), serveur
    )

    port_grpc = int(os.environ.get("GRPC_PORT", "50051"))
    port_ouvert = serveur.add_insecure_port(f"[::]:{port_grpc}")

    if port_ouvert == 0:
        raise RuntimeError(
            f"Impossible d'ouvrir le port gRPC {port_grpc}"
        )

    serveur.start()
    print(f"Serveur HTTP demarre sur le port {port_http}")
    print(f"Serveur gRPC demarre sur le port {port_grpc}")

    serveur.wait_for_termination()


if __name__ == "__main__":
    demarrer_serveur()
