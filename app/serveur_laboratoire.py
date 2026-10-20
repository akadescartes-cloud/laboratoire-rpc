
import os
from concurrent import futures
import grpc

from app import laboratoire_pb2
from app import laboratoire_pb2_grpc


# Donnees fictives du laboratoire pour les tests
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
                f"Aucun resultat pour le patient {patient_id}"
            )

        resultat = RESULTATS[patient_id]

        return laboratoire_pb2.Resultat(
            patient_id=patient_id,
            analyse=resultat["analyse"],
            valeur=resultat["valeur"],
            statut=resultat["statut"],
        )


def demarrer_serveur():
    serveur = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10)
    )

    laboratoire_pb2_grpc.add_LaboratoireServicer_to_server(
        LaboratoireService(), serveur
    )

    # Render fournit PORT ; en local, on utilise 50051.
    port = int(os.environ.get("PORT", "50051"))

    port_ouvert = serveur.add_insecure_port(f"[::]:{port}")

    if port_ouvert == 0:
        raise RuntimeError(f"Impossible d'ouvrir le port {port}")

    serveur.start()
    print(f"Serveur Laboratoire demarre sur le port {port}")

    serveur.wait_for_termination()


if __name__ == "__main__":
    demarrer_serveur()
