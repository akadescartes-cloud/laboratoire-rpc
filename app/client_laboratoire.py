
import grpc

from app import laboratoire_pb2
from app import laboratoire_pb2_grpc


def tester_laboratoire():
    with grpc.insecure_channel("localhost:50051") as canal:
        client = laboratoire_pb2_grpc.LaboratoireStub(canal)

        requete = laboratoire_pb2.RequeteResultat(
            patient_id=101
            
        )

        try:
            resultat = client.ObtenirResultat(
                requete,
                timeout=3
            )

            print("Résultat reçu du laboratoire :")
            print("Patient :", resultat.patient_id)
            print("Analyse :", resultat.analyse)
            print("Valeur :", resultat.valeur)
            print("Statut :", resultat.statut)

        except grpc.RpcError as erreur:
            print("Erreur gRPC :", erreur.code())
            print(erreur.details())


if __name__ == "__main__":
    tester_laboratoire()
