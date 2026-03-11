import dash
from dash import html, dcc, callback, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import pandas as pd
from io import BytesIO
import base64
from database import get_db
from models import Student, Course, Grade

dash.register_page(__name__, path='/import', name='Import', order=5)

layout = html.Div([
    html.Div([
        html.H2("Import de Donnees"),
        html.P("Migration Excel vers la base de donnees SQL", className="text-muted"),
    ], className="page-header"),

    html.Div(id="import-alert"),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([html.I(className="fas fa-file-excel me-2"), "Charger un fichier Excel"]),
                dbc.CardBody([
                    dcc.Upload(
                        id="import-upload",
                        children=html.Div([
                            html.I(className="fas fa-cloud-upload-alt fa-3x text-muted mb-3"),
                            html.H5("Glisser-deposer ou cliquer", className="text-muted"),
                            html.P("Formats acceptes : .xlsx, .xls", className="text-muted small"),
                        ]),
                        className="upload-zone",
                        accept=".xlsx,.xls",
                    ),
                    html.Div(id="import-filename", className="mt-2"),
                ]),
            ]),
        ], md=5),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([html.I(className="fas fa-info-circle me-2"), "Format attendu"]),
                dbc.CardBody([
                    html.P("Le fichier Excel peut contenir les feuilles suivantes :", className="small"),
                    html.Ul([
                        html.Li([html.Strong("Etudiants"), " : Colonnes ID, Nom, Prenom, Email, Date_Naissance"]),
                        html.Li([html.Strong("Cours"), " : Colonnes Code, Libelle, Volume_Horaire, Enseignant"]),
                        html.Li([html.Strong("Notes"), " : Colonnes ID_Student, Code_Cours, Note, Coefficient"]),
                    ], className="small"),
                    html.Hr(),
                    html.P("Les noms de feuilles et colonnes sont flexibles (variations acceptees).", className="text-muted small"),
                ]),
            ]),
        ], md=7),
    ], className="g-3 mb-4"),

    # Preview
    dbc.Card([
        dbc.CardHeader([html.I(className="fas fa-eye me-2"), "Apercu des donnees"]),
        dbc.CardBody(id="import-preview"),
    ], className="mb-3"),

    dbc.Button([html.I(className="fas fa-database me-2"), "Importer dans la base de donnees"],
               id="import-confirm-btn", color="primary", size="lg", className="w-100",
               disabled=True),

    dcc.Store(id="import-store"),
])


@callback(
    [Output("import-preview", "children"), Output("import-store", "data"),
     Output("import-confirm-btn", "disabled"), Output("import-filename", "children")],
    Input("import-upload", "contents"),
    State("import-upload", "filename"),
    prevent_initial_call=True,
)
def preview_upload(contents, filename):
    if not contents:
        return html.P("Aucun fichier charge.", className="text-muted"), None, True, ""

    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        xls = pd.ExcelFile(BytesIO(decoded))

        preview_sections = []
        for sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet)
            preview_sections.append(html.Div([
                html.H6([
                    dbc.Badge(sheet, color="primary", className="me-2"),
                    f"{len(df)} lignes, {len(df.columns)} colonnes"
                ], className="mb-2"),
                dbc.Table.from_dataframe(
                    df.head(5), striped=True, bordered=False, hover=True, size="sm",
                    className="mb-3",
                ),
            ]))

        filename_badge = html.Div([
            html.I(className="fas fa-check-circle text-success me-2"),
            html.Span(filename, className="fw-bold"),
        ])

        return html.Div(preview_sections), contents, False, filename_badge
    except Exception as e:
        return html.P(f"Erreur de lecture: {e}", className="text-danger"), None, True, ""


@callback(
    [Output("import-alert", "children"), Output("import-confirm-btn", "disabled", allow_duplicate=True)],
    Input("import-confirm-btn", "n_clicks"),
    State("import-store", "data"),
    prevent_initial_call=True,
)
def do_import(n, contents):
    if not contents:
        return dbc.Alert("Aucun fichier.", color="warning", dismissable=True, duration=4000), True

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    xls = pd.ExcelFile(BytesIO(decoded))

    db = get_db()
    counts = {"etudiants": 0, "cours": 0, "notes": 0}
    skipped = {"etudiants": 0, "cours": 0, "notes": 0, "notes_invalid": 0}

    try:
        for sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet)
            cols_lower = {c.lower().strip(): c for c in df.columns}
            sheet_lower = sheet.lower().strip()

            # Detect students sheet
            if sheet_lower in ('etudiants', 'students', 'eleves') or 'nom' in cols_lower:
                has_prenom = any(k in cols_lower for k in ('prenom', 'prénom', 'firstname'))
                if has_prenom:
                    for _, row in df.iterrows():
                        nom = str(row.get(cols_lower.get('nom', ''), '')).strip()
                        prenom_key = next((cols_lower[k] for k in ('prenom', 'prénom', 'firstname') if k in cols_lower), None)
                        prenom = str(row.get(prenom_key, '')).strip() if prenom_key else ''
                        email_key = next((cols_lower[k] for k in ('email', 'mail', 'e-mail') if k in cols_lower), None)
                        email = str(row.get(email_key, '')).strip() if email_key else None
                        if email == 'nan':
                            email = None

                        if not nom or nom == 'nan':
                            continue

                        # Check duplicate
                        if email and db.query(Student).filter(Student.email == email).first():
                            skipped["etudiants"] += 1
                            continue

                        dob = None
                        dob_key = next((cols_lower[k] for k in ('date_naissance', 'date de naissance', 'dob', 'naissance') if k in cols_lower), None)
                        if dob_key:
                            try:
                                dob = pd.to_datetime(row.get(dob_key), errors='coerce')
                                if pd.isna(dob):
                                    dob = None
                                else:
                                    dob = dob.date()
                            except:
                                dob = None

                        db.add(Student(nom=nom, prenom=prenom, email=email, date_naissance=dob))
                        counts["etudiants"] += 1

            # Detect courses sheet
            elif sheet_lower in ('cours', 'courses', 'matieres') or 'code' in cols_lower:
                code_key = cols_lower.get('code', None)
                if code_key:
                    for _, row in df.iterrows():
                        code = str(row.get(code_key, '')).strip()
                        if not code or code == 'nan':
                            continue
                        if db.query(Course).get(code):
                            skipped["cours"] += 1
                            continue

                        lib_key = next((cols_lower[k] for k in ('libelle', 'libellé', 'label', 'nom') if k in cols_lower), None)
                        vol_key = next((cols_lower[k] for k in ('volume_horaire', 'volume horaire', 'heures', 'hours') if k in cols_lower), None)
                        ens_key = next((cols_lower[k] for k in ('enseignant', 'professeur', 'teacher', 'prof') if k in cols_lower), None)

                        libelle = str(row.get(lib_key, code)).strip() if lib_key else code
                        volume = float(row.get(vol_key, 0)) if vol_key else 0
                        enseignant = str(row.get(ens_key, '')).strip() if ens_key else None
                        if enseignant == 'nan':
                            enseignant = None

                        db.add(Course(code=code, libelle=libelle, volume_horaire=volume, enseignant=enseignant))
                        counts["cours"] += 1

            # Detect grades sheet
            elif sheet_lower in ('notes', 'grades', 'evaluations'):
                for _, row in df.iterrows():
                    sid_key = next((cols_lower[k] for k in ('id_student', 'id_etudiant', 'student_id', 'id') if k in cols_lower), None)
                    course_key = next((cols_lower[k] for k in ('id_course', 'code_cours', 'code', 'cours', 'course') if k in cols_lower), None)
                    note_key = next((cols_lower[k] for k in ('note', 'grade', 'score') if k in cols_lower), None)
                    coeff_key = next((cols_lower[k] for k in ('coefficient', 'coeff', 'coef') if k in cols_lower), None)

                    if not sid_key or not note_key:
                        continue

                    try:
                        sid = int(row.get(sid_key))
                        note = float(row.get(note_key))
                    except (ValueError, TypeError):
                        continue

                    # Validation note entre 0 et 20
                    if note < 0 or note > 20:
                        skipped["notes_invalid"] += 1
                        continue

                    course_code = str(row.get(course_key, 'UNKNOWN')).strip() if course_key else 'UNKNOWN'
                    coeff = float(row.get(coeff_key, 1.0)) if coeff_key else 1.0

                    if db.query(Student).get(sid):
                        db.add(Grade(id_student=sid, id_course=course_code, note=note, coefficient=coeff))
                        counts["notes"] += 1
                    else:
                        skipped["notes"] += 1

        db.commit()

        # Message detaille
        msg_parts = [f"{counts['etudiants']} etudiants", f"{counts['cours']} cours", f"{counts['notes']} notes"]
        msg = f"Import termine : {', '.join(msg_parts)}"
        
        skip_parts = []
        if skipped["etudiants"] > 0:
            skip_parts.append(f"{skipped['etudiants']} etudiants (doublons)")
        if skipped["cours"] > 0:
            skip_parts.append(f"{skipped['cours']} cours (doublons)")
        if skipped["notes"] > 0:
            skip_parts.append(f"{skipped['notes']} notes (etudiant inconnu)")
        if skipped["notes_invalid"] > 0:
            skip_parts.append(f"{skipped['notes_invalid']} notes (hors [0-20])")
        
        if skip_parts:
            msg += f". Ignores : {', '.join(skip_parts)}"
            return dbc.Alert([html.I(className="fas fa-exclamation-triangle me-2"), msg], color="warning", dismissable=True, duration=10000), True
        
        return dbc.Alert([html.I(className="fas fa-check-circle me-2"), msg], color="success", dismissable=True, duration=8000), True
    except Exception as e:
        db.rollback()
        return dbc.Alert(f"Erreur lors de l'import: {e}", color="danger", dismissable=True, duration=8000), False
    finally:
        db.close()
