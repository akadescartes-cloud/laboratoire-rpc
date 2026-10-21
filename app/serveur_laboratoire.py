import os
import threading
from concurrent import futures
import grpc
import requests
from flask import Flask, jsonify, render_template_string, request, send_file
from app import laboratoire_pb2
from app import laboratoire_pb2_grpc
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
# DONNEES DE DEMONSTRATION
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
RESULTAT_IDS = {
    "RES-42": 101,
    "RES-101": 101,
    "RES-102": 102,
}
def obtenir_resultat(patient_id):
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
                "Aucun résultat pour ce patient."
            )
        return laboratoire_pb2.Resultat(
            patient_id=resultat["patient_id"],
            analyse=resultat["analyse"],
            valeur=resultat["valeur"],
            statut=resultat["statut"],
        )
def demarrer_grpc():
    serveur = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10)
    )
    laboratoire_pb2_grpc.add_LaboratoireServicer_to_server(
        LaboratoireService(),
        serveur
    )
    serveur.add_insecure_port(f"[::]:{GRPC_PORT}")
    serveur.start()
    print(f"Serveur gRPC démarré sur le port {GRPC_PORT}")
    serveur.wait_for_termination()
# =========================================================
# INTERFACE WEB : COMPTE RENDU MEDICAL
# =========================================================
PAGE_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Laboratoire d'analyses médicales</title>
<style>
:root {
    --blue: #174a8b;
    --blue2: #2f75bd;
    --ink: #17243a;
    --muted: #65738a;
    --line: #d9e2ee;
    --bg: #eef3f8;
    --green: #16804a;
}
* {
    box-sizing: border-box;
}
body {
    margin: 0;
    background: var(--bg);
    font-family: Arial, Helvetica, sans-serif;
    color: var(--ink);
}
header {
    background: linear-gradient(120deg, #123c72, #2478b9);
    color: white;
    padding: 25px 18px;
    text-align: center;
}
header .brand {
    font-size: clamp(22px, 3vw, 32px);
    font-weight: 800;
}
header p {
    margin: 8px 0 0;
    color: #e4efff;
}
main {
    max-width: 1000px;
    margin: 28px auto;
    padding: 0 16px;
}
.panel {
    background: white;
    padding: 24px;
    border-radius: 16px;
    box-shadow: 0 8px 28px #17365b12;
    margin-bottom: 22px;
}
.panel h2 {
    margin-top: 0;
    color: var(--blue);
}
label {
    display: block;
    font-weight: 700;
    margin: 14px 0 7px;
}
input {
    width: 100%;
    padding: 12px 13px;
    border: 1px solid #cbd5e1;
    border-radius: 9px;
    font-size: 16px;
    background: white;
}
button {
    border: 0;
    border-radius: 9px;
    padding: 12px 17px;
    background: var(--blue2);
    color: white;
    font-weight: 700;
    font-size: 15px;
    cursor: pointer;
}
button:hover {
    filter: brightness(.94);
}
.actions {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 15px;
}
.secondary {
    background: #e7eef8;
    color: var(--blue);
}
.message {
    margin-top: 12px;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    color: var(--muted);
}
#resultat {
    margin-top: 24px;
}
.paper {
    background: white;
    border: 1px solid #dce3ec;
    box-shadow: 0 12px 34px #17365b18;
    padding: clamp(18px, 4vw, 42px);
    max-width: 900px;
    margin: 0 auto 24px;
    color: #202b3d;
}
.paper-head {
    display: flex;
    justify-content: space-between;
    gap: 20px;
    align-items: center;
    border-bottom: 4px solid var(--blue2);
    padding-bottom: 18px;
}
.brandmark {
    display: flex;
    gap: 14px;
    align-items: center;
}
.flask {
    width: 54px;
    height: 54px;
    border-radius: 13px;
    background: #e7f1fc;
    color: var(--blue);
    display: grid;
    place-items: center;
    font-size: 29px;
}
.labname {
    font-weight: 800;
    color: #143e79;
    font-size: clamp(17px, 2.5vw, 24px);
}
.labsub {
    color: var(--muted);
    margin-top: 5px;
}
.contact {
    font-size: 12px;
    color: var(--muted);
    line-height: 1.6;
    text-align: right;
}
.report-title {
    margin: 20px 0;
    background: #eaf2fb;
    border-radius: 12px;
    padding: 18px;
}
.report-title h2 {
    text-align: center;
    color: var(--blue);
    font-size: clamp(20px, 3vw, 30px);
    margin: 0 0 16px;
}
.meta {
    display: flex;
    flex-wrap: wrap;
    gap: 10px 25px;
    color: #475569;
}
.pill {
    display: inline-block;
    background: #d9f5e5;
    color: #126338;
    padding: 5px 11px;
    border-radius: 7px;
    font-weight: 700;
}
.patient-box {
    background: #f3f6fa;
    border-radius: 12px;
    padding: 18px;
    margin: 16px 0;
}
.patient-box h3,
.results-title,
.comments h3 {
    color: var(--blue);
    margin: 0 0 14px;
}
.patient-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px 24px;
}
.patient-grid p {
    margin: 4px 0;
    color: #4c5b70;
}
.results-title {
    margin: 22px 0 12px;
}
.table-wrap {
    overflow-x: auto;
}
table {
    width: 100%;
    border-collapse: collapse;
    min-width: 540px;
}
th {
    background: #2f70b9;
    color: white;
    padding: 12px 10px;
    text-align: center;
}
td {
    border: 1px solid #bdc9d8;
    padding: 14px 10px;
    text-align: center;
}
td:first-child {
    font-weight: 700;
}
.normal {
    color: #126338;
    background: #d9f5e5;
    border-radius: 7px;
    padding: 5px 10px;
    font-weight: 700;
}
.comments {
    background: #f1f5f9;
    padding: 16px;
    border-radius: 10px;
    margin-top: 18px;
}
.comments p {
    margin: 0;
    color: #344256;
}
.paper-foot {
    display: flex;
    justify-content: space-between;
    gap: 20px;
    align-items: end;
    margin-top: 24px;
    color: #64748b;
    font-size: 12px;
}
.signature {
    text-align: right;
    color: #43536a;
}
.signature strong {
    display: block;
    color: #1e3f75;
    font-size: 14px;
    margin-bottom: 8px;
}
.stamp {
    display: inline-grid;
    place-items: center;
    width: 78px;
    height: 78px;
    border: 3px double #2f70b9;
    color: #2f70b9;
    border-radius: 50%;
    font-weight: 800;
    font-size: 10px;
    text-align: center;
    margin-left: 12px;
    padding: 7px;
}
footer {
    text-align: center;
    padding: 18px;
    color: #738198;
    font-size: 13px;
}
@media(max-width: 650px) {
    .paper-head {
        align-items: flex-start;
        flex-direction: column;
    }
    .contact {
        text-align: left;
    }
    .patient-grid {
        grid-template-columns: 1fr;
    }
    .paper-foot {
        flex-direction: column;
        align-items: flex-start;
    }
    .signature {
        text-align: left;
    }
}
@media print {
    body {
        background: white;
    }
    .no-print,
    header,
    footer,
    .form-panel {
        display: none !important;
    }
    main {
        max-width: none;
        margin: 0;
        padding: 0;
    }
    .paper {
        box-shadow: none;
        border: 0;
        max-width: none;
        padding: 8mm;
    }
    .report-title,
    .patient-box,
    .comments,
    th,
    .normal {
        print-color-adjust: exact;
        -webkit-print-color-adjust: exact;
    }
}
</style>
</head>
<body>
<header>
    <div class="brand">⚕ Laboratoire d’analyses médicales</div>
    <p>Biologie médicale au service de votre santé</p>
</header>
<main>
<section class="panel form-panel">
    <h2>Consulter un résultat</h2>
    <label for="patient_id">Identifiant du patient</label>
    <input id="patient_id" type="number" min="1"
           placeholder="Exemple : 101">
    <div class="actions">
        <button onclick="consulterResultat()">
            Afficher le compte rendu
        </button>
    </div>
    <div id="lookup-message" class="message">
        Saisissez un identifiant pour générer la feuille de résultats.
    </div>
</section>
<div id="resultat"></div>
<section class="panel form-panel">
    <h2>Notifier le service Consultation</h2>
    <p>Envoyer une notification lorsqu’un résultat est disponible.</p>
    <label for="notif_patient_id">Identifiant du patient</label>
    <input id="notif_patient_id" type="number" min="1"
           placeholder="Exemple : 101">
    <label for="id_dossier">Identifiant du dossier Consultation</label>
    <input id="id_dossier" type="text" placeholder="Exemple : D001">
    <label for="id_resultat">Identifiant du résultat</label>
    <input id="id_resultat" type="text" placeholder="Exemple : RES-42">
    <div class="actions">
        <button onclick="envoyerNotification()">
            Envoyer la notification
        </button>
    </div>
    <div id="notification" class="message"></div>
</section>
</main>
<footer>
    Projet RPC — Service Laboratoire · Compte rendu de démonstration
</footer>
<script>
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
}[c]));
function afficherCompteRendu(donnees, idResultat) {
    const date = new Date().toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: 'long',
        year: 'numeric'
    });
    const nomAnalyse = String(donnees.analyse || 'Analyse')
        .replace(/glycemie/i, 'Glycémie')
        .replace(/hemoglobine/i, 'Hémoglobine');
    const valeur = String(donnees.valeur || 'Non renseignée');
    const unite = valeur.match(/\b(g\\/L|g\\/dL|mg\\/dL|mmol\\/L)\b/i);
    document.getElementById('resultat').innerHTML = `
    <article class="paper" id="compte-rendu">
        <div class="paper-head">
            <div class="brandmark">
                <div class="flask">⚗</div>
                <div>
                    <div class="labname">LABORATOIRE D’ANALYSES MÉDICALES</div>
                    <div class="labsub">Biologie médicale au service de votre santé</div>
                </div>
            </div>
            <div class="contact">
                Service de laboratoire<br>
                Compte rendu de démonstration<br>
                Document généré le ${esc(date)}
            </div>
        </div>
        <section class="report-title">
            <h2>RÉSULTAT D’ANALYSE MÉDICALE</h2>
            <div class="meta">
                <span>Référence :
                    <strong>${esc(idResultat || 'Non renseignée')}</strong>
                </span>
                <span>Date d’édition : <strong>${esc(date)}</strong></span>
                <span>Statut :
                    <span class="pill">${esc(donnees.statut || 'Non renseigné')}</span>
                </span>
            </div>
        </section>
        <section class="patient-box">
            <h3>INFORMATIONS PATIENT</h3>
            <div class="patient-grid">
                <div>
                    <p>Identifiant patient :
                        <strong>${esc(donnees.patient_id ?? 'Non renseigné')}</strong>
                    </p>
                    <p>Nom : Non renseigné</p>
                    <p>Prénom : Non renseigné</p>
                </div>
                <div>
                    <p>Médecin prescripteur : Non renseigné</p>
                    <p>Service : Consultation</p>
                    <p>Date de prélèvement : Non renseignée</p>
                </div>
            </div>
        </section>
        <h3 class="results-title">RÉSULTATS D’ANALYSES</h3>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Analyse</th>
                        <th>Résultat</th>
                        <th>Unité</th>
                        <th>Statut</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>${esc(nomAnalyse)}</td>
                        <td><strong>${esc(valeur)}</strong></td>
                        <td>${esc(unite ? unite[0] : '—')}</td>
                        <td><span class="normal">${esc(donnees.statut || 'Non renseigné')}</span></td>
                    </tr>
                </tbody>
            </table>
        </div>
        <section class="comments">
            <h3>COMMENTAIRES</h3>
            <p>
                Résultat affiché à partir des données transmises par le service
                laboratoire. Les valeurs de référence et l’interprétation médicale
                ne sont pas fournies par cette démonstration.
            </p>
        </section>
        <div class="paper-foot">
            <div>
                Document généré automatiquement à partir des données de démonstration.
                <br>
                Il ne remplace pas un compte rendu médical validé.
            </div>
            <div class="signature">
                <strong>Service de laboratoire</strong>
                Compte rendu informatique
                <span class="stamp">LABORATOIRE<br>ANALYSES<br>MÉDICALES</span>
            </div>
        </div>
        <div class="actions no-print">
            <button onclick="window.print()">
                Imprimer / Enregistrer en PDF
            </button>
        </div>
    </article>`;
}
async function consulterResultat() {
    const id = document.getElementById('patient_id').value;
    const message = document.getElementById('lookup-message');
    const affichage = document.getElementById('resultat');
    if (!id) {
        message.textContent = 'Entre un identifiant de patient.';
        return;
    }
    message.textContent = 'Recherche en cours…';
    affichage.innerHTML = '';
    try {
        const reponse = await fetch('/api/resultats/' + encodeURIComponent(id));
        const donnees = await reponse.json();
        if (!reponse.ok) {
            message.textContent = donnees.erreur || 'Résultat introuvable.';
            return;
        }
        const idResultat = Number(id) === 101
            ? 'RES-42'
            : 'RES-' + id;
        message.textContent = 'Compte rendu généré.';
        afficherCompteRendu(donnees, idResultat);
    } catch (erreur) {
        message.textContent =
            'Erreur réseau : impossible de récupérer le résultat.';
    }
}
async function envoyerNotification() {
    const patientId = document.getElementById('notif_patient_id').value;
    const idDossier = document.getElementById('id_dossier').value.trim();
    const idResultat = document.getElementById('id_resultat').value.trim();
    const affichage = document.getElementById('notification');
    if (!patientId || !idDossier || !idResultat) {
        affichage.textContent = 'Remplis les trois champs avant l’envoi.';
        return;
    }
    affichage.textContent = 'Envoi en cours…';
    try {
        const reponse = await fetch('/api/notifier-resultat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                patient_id: Number(patientId),
                id_dossier: idDossier,
                id_resultat: idResultat
            })
        });
        const donnees = await reponse.json();
        if (!reponse.ok) {
            affichage.textContent =
                'Échec : ' + (donnees.erreur || 'notification non envoyée.');
            return;
        }
        affichage.textContent =
            'Notification envoyée à Consultation. Identifiant : ' +
            (donnees.id_notif || 'non communiqué');
    } catch (erreur) {
        affichage.textContent =
            'Erreur réseau : impossible de contacter le service Consultation.';
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
            "erreur": "Aucun résultat pour ce patient."
        }), 404
    return jsonify(resultat), 200
@app.route("/api/resultats/id/<string:id_resultat>", methods=["GET"])
def api_obtenir_resultat_par_id(id_resultat):
    patient_id = RESULTAT_IDS.get(id_resultat)
    if patient_id is None:
        return jsonify({
            "erreur": "Identifiant de résultat introuvable."
        }), 404
    resultat = obtenir_resultat(patient_id)
    if resultat is None:
        return jsonify({"erreur": "Résultat introuvable."}), 404
    return jsonify({
        **resultat,
        "id_resultat": id_resultat,
        "image_url": None
    }), 200
# =========================================================
# ROUTE IMAGE PNG DU COMPTE RENDU
# =========================================================
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
def generer_image_compte_rendu(id_resultat, resultat):
    """Génère une image PNG professionnelle du compte rendu."""
    import os
    import re
    largeur, hauteur = 1240, 1754  # A4 vertical en haute résolution
    image = Image.new("RGB", (largeur, hauteur), "#edf2f8")
    draw = ImageDraw.Draw(image)
    # Polices disponibles sur Render (Linux) et Windows.
    chemins = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        (r"C:\Window&#x73;**\F**ont&#x73;**\a**rial.ttf",
         r"C:\Window&#x73;**\F**ont&#x73;**\a**rialbd.ttf"),
    ]
    regular_path = bold_path = None
    for regular, bold in chemins:
        if os.path.exists(regular) and os.path.exists(bold):
            regular_path, bold_path = regular, bold
            break
    def font(size, bold=False):
        path = bold_path if bold else regular_path
        try:
            return ImageFont.truetype(path, size) if path else ImageFont.load_default()
        except OSError:
            return ImageFont.load_default()
    f_small = font(19)
    f_body = font(23)
    f_body_bold = font(23, True)
    f_section = font(27, True)
    f_title = font(39, True)
    f_brand = font(34, True)
    f_footer = font(16)
    navy = "#174a8b"
    blue = "#3274bd"
    pale = "#eaf2fc"
    ink = "#243247"
    muted = "#65738a"
    line = "#cbd7e6"
    green = "#137547"
    # Feuille blanche
    draw.rounded_rectangle((42, 35, 1198, 1718), radius=22,
                           fill="white", outline="#d7e0ec", width=3)
    # En-tête bleu
    draw.rounded_rectangle((43, 36, 1197, 255), radius=21, fill=navy)
    draw.rectangle((43, 215, 1197, 255), fill=navy)
    draw.text((88, 77), "LABORATOIRE D'ANALYSES", font=f_brand, fill="white")
    draw.text((88, 121), "MEDICALES", font=f_brand, fill="white")
    draw.text((90, 184), "Biologie medicale au service de votre sante",
              font=f_body, fill="#e4efff")
    draw.text((875, 88), "SERVICE DE LABORATOIRE", font=f_small, fill="white")
    draw.text((875, 122), "COMPTE RENDU DE DEMONSTRATION",
              font=f_footer, fill="#dceaff")
    # Bandeau de référence
    draw.rounded_rectangle((85, 292, 1155, 480), radius=18, fill=pale)
    label = "RESULTAT D'ANALYSE MEDICALE"
    bbox = draw.textbbox((0, 0), label, font=f_title)
    draw.text(((largeur - (bbox[2] - bbox[0])) / 2, 323), label,
              font=f_title, fill=navy)
    draw.text((120, 405), f"Reference : {id_resultat}", font=f_body, fill=ink)
    draw.text((700, 405), "Statut :", font=f_body, fill=ink)
    draw.rounded_rectangle((790, 397, 1090, 443), radius=12, fill="#d9f5e5")
    draw.text((810, 407), str(resultat.get("statut", "Non renseigne")),
              font=f_body_bold, fill=green)
    # Informations patient
    draw.text((90, 535), "INFORMATIONS PATIENT", font=f_section, fill=navy)
    draw.rounded_rectangle((85, 585, 1155, 785), radius=15, fill="#f3f6fa")
    draw.text((120, 620), f"Identifiant patient : {resultat.get('patient_id', 'Non renseigne')}",
              font=f_body, fill=ink)
    draw.text((120, 670), "Nom : Non renseigne", font=f_body, fill=ink)
    draw.text((120, 720), "Prenom : Non renseigne", font=f_body, fill=ink)
    draw.text((650, 620), "Service : Consultation", font=f_body, fill=ink)
    draw.text((650, 670), "Medecin prescripteur : Non renseigne",
              font=f_small, fill=ink)
    draw.text((650, 720), "Date de prelevement : Non renseignee",
              font=f_small, fill=ink)
    # Tableau de résultats
    draw.text((90, 835), "RESULTATS D'ANALYSES", font=f_section, fill=navy)
    x0, y0, x1 = 85, 895, 1155
    header_bottom = 970
    row_bottom = 1075
    cols = [85, 410, 680, 900, 1155]
    draw.rounded_rectangle((x0, y0, x1, header_bottom), radius=8, fill=blue)
    draw.rectangle((x0, y0 + 35, x1, header_bottom), fill=blue)
    headers = ["Analyse", "Resultat", "Unite", "Statut"]
    for i, text_value in enumerate(headers):
        draw.text((cols[i] + 20, y0 + 25), text_value, font=f_body_bold, fill="white")
    valeur = str(resultat.get("valeur", "Non renseignee"))
    analyse = str(resultat.get("analyse", "Non renseignee"))
    statut = str(resultat.get("statut", "Non renseigne"))
    match = re.search(r"(g/L|g/dL|mg/dL|mmol/L)\b", valeur, re.I)
    unite = match.group(1) if match else "—"
    draw.rectangle((x0, header_bottom, x1, row_bottom),
                   fill="white", outline=line, width=2)
    for x in cols[1:-1]:
        draw.line((x, header_bottom, x, row_bottom), fill=line, width=2)
    cells = [analyse, valeur, unite, statut]
    for i, value in enumerate(cells):
        draw.text((cols[i] + 20, header_bottom + 37), value,
                  font=f_body_bold if i == 1 else f_body,
                  fill=green if i == 3 else ink)
    # Commentaires
    draw.rounded_rectangle((85, 1125, 1155, 1320), radius=15, fill="#f1f5f9")
    draw.text((120, 1160), "COMMENTAIRES", font=f_section, fill=navy)
    draw.text((120, 1215), "Resultat transmis par le service laboratoire.",
              font=f_body, fill=ink)
    draw.text((120, 1260), "Les valeurs de reference et l'interpretation medicale",
              font=f_small, fill=ink)
    draw.text((120, 1290), "ne sont pas fournies dans cette demonstration.",
              font=f_small, fill=ink)
    # Pied de page et cachet graphique
    draw.line((85, 1575, 1155, 1575), fill=line, width=3)
    draw.text((90, 1605), "Document genere automatiquement a partir des donnees de demonstration.",
              font=f_footer, fill=muted)
    draw.text((90, 1638), "Ne remplace pas un compte rendu medical valide.",
              font=f_footer, fill=muted)
    draw.text((850, 1605), "SERVICE DE LABORATOIRE", font=f_small, fill=navy)
    draw.text((850, 1640), "Compte rendu informatique", font=f_footer, fill=muted)
    draw.ellipse((1045, 1585, 1135, 1675), outline=blue, width=3)
    draw.text((1060, 1610), "LABO", font=f_footer, fill=blue)
    draw.text((1057, 1635), "MEDICAL", font=f_footer, fill=blue)
    sortie = BytesIO()
    image.save(sortie, format="PNG", optimize=True)
    sortie.seek(0)
    return sortie
@app.route("/api/resultats/id/<string:id_resultat>/image", methods=["GET"])
def api_image_resultat(id_resultat):
    patient_id = RESULTAT_IDS.get(id_resultat)
    if patient_id is None:
        return jsonify({"erreur": "Identifiant de résultat introuvable."}), 404
    resultat = obtenir_resultat(patient_id)
    if resultat is None:
        return jsonify({"erreur": "Résultat introuvable."}), 404
    image_png = generer_image_compte_rendu(id_resultat, resultat)
    return send_file(
        image_png,
        mimetype="image/png",
        download_name=f"{id_resultat}.png"
    )
# =========================================================
# NOTIFICATION DU SERVICE CONSULTATION
# =========================================================
def notifier_consultation(id_dossier, id_resultat):
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
    id_resultat = str(id_resultat).strip()
    if RESULTAT_IDS.get(id_resultat) != patient_id:
        return jsonify({
            "erreur": "L'identifiant du résultat ne correspond pas au patient."
        }), 400
    notification = notifier_consultation(
        str(id_dossier),
        id_resultat
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
        "id_resultat": id_resultat,
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
