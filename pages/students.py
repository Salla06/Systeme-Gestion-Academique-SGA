import dash
from dash import html, dcc, callback, Input, Output, State, ctx, no_update, ALL
import dash_bootstrap_components as dbc
from database import get_db
from datetime import datetime
from models import Student, Grade, Course, Session, Attendance
from sqlalchemy import func
import base64
import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

dash.register_page(__name__, path='/students', name='Etudiants', order=3)

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

# Add/Edit Student Modal
student_modal = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle(id="stu-modal-title")),
    dbc.ModalBody([
        dbc.Row([
            dbc.Col([dbc.Label("Nom *"), dbc.Input(id="stu-nom")], md=6),
            dbc.Col([dbc.Label("Prenom *"), dbc.Input(id="stu-prenom")], md=6),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([dbc.Label("Email"), dbc.Input(id="stu-email", type="email")], md=6),
            dbc.Col([dbc.Label("Date de naissance"),
                     dcc.DatePickerSingle(id="stu-dob", display_format="DD/MM/YYYY",
                                           style={"width": "100%"})], md=6),
        ]),
    ]),
    dbc.ModalFooter([
        dbc.Button("Annuler", id="stu-modal-cancel", color="secondary", outline=True, className="me-2"),
        dbc.Button("Enregistrer", id="stu-modal-save", color="primary"),
    ]),
], id="stu-modal", is_open=False, centered=True, size="lg")

# Student detail modal
detail_modal = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle(id="stu-detail-title")),
    dbc.ModalBody(id="stu-detail-body"),
    dbc.ModalFooter([
        dbc.Button([html.I(className="fas fa-file-pdf me-2"), "Bulletin PDF"],
                   id="stu-pdf-bulletin", color="primary", outline=True, className="me-2"),
        dbc.Button([html.I(className="fas fa-file-pdf me-2"), "Rapport Presence"],
                   id="stu-pdf-attendance", color="success", outline=True),
    ]),
], id="stu-detail-modal", is_open=False, centered=True, size="xl")

# Delete confirmation modal
delete_modal = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("Confirmer la suppression")),
    dbc.ModalBody(html.P("Cette action supprimera l'etudiant, ses notes et ses presences. Continuer ?")),
    dbc.ModalFooter([
        dbc.Button("Annuler", id="stu-del-cancel", color="secondary", outline=True, className="me-2"),
        dbc.Button("Supprimer", id="stu-del-confirm", color="danger"),
    ]),
], id="stu-del-modal", is_open=False, centered=True)

layout = html.Div([
    html.Div([
        html.Div([
            html.H2("Gestion des Etudiants"),
            html.P("Tableau de bord etudiants et evaluations", className="text-muted"),
        ]),
        html.Div([
            dbc.Input(id="stu-search", placeholder="Rechercher...", type="search",
                      className="me-2", style={"width": "220px"}),
            dbc.Button([html.I(className="fas fa-plus me-2"), "Nouvel Etudiant"],
                       id="stu-add-btn", color="primary"),
        ], className="d-flex"),
    ], className="d-flex justify-content-between align-items-start page-header"),

    html.Div(id="stu-alert"),
    html.Div(id="students-table-container"),
    student_modal,
    detail_modal,
    delete_modal,
    dcc.Store(id="stu-edit-store"),
    dcc.Store(id="stu-detail-store"),
    dcc.Store(id="stu-del-store"),
    dcc.Store(id="stu-trigger", data=0),
    dcc.Download(id="stu-download"),
])


@callback(
    Output("students-table-container", "children"),
    [Input("stu-trigger", "data"), Input("stu-search", "value")],
)
def render_students(_, search):
    db = get_db()
    try:
        q = db.query(Student).order_by(Student.nom, Student.prenom)
        students = q.all()

        if search:
            search_lower = search.lower()
            students = [s for s in students if search_lower in s.nom.lower() or search_lower in s.prenom.lower()
                        or (s.email and search_lower in s.email.lower())]

        if not students:
            return dbc.Card(dbc.CardBody(html.Div([
                html.I(className="fas fa-users fa-3x text-muted"),
                html.H5("Aucun etudiant", className="text-muted mt-3"),
            ], className="empty-state")))

        rows = []
        for s in students:
            avg = db.query(func.avg(Grade.note)).filter(Grade.id_student == s.id).scalar()
            total_sessions = db.query(Session).count()
            absences = db.query(Attendance).filter(Attendance.id_student == s.id).count()
            att_rate = ((total_sessions - absences) / total_sessions * 100) if total_sessions > 0 else 100

            avg_badge_color = "success" if avg and avg >= 12 else ("warning" if avg and avg >= 10 else "danger")
            att_badge_color = "success" if att_rate >= 80 else ("warning" if att_rate >= 60 else "danger")

            rows.append(html.Tr([
                html.Td(html.Span(f"#{s.id}", className="text-muted fw-bold small")),
                html.Td(html.Span(f"{s.nom} {s.prenom}", className="fw-bold")),
                html.Td(s.email or "-", className="text-muted small"),
                html.Td(s.date_naissance.strftime("%d/%m/%Y") if s.date_naissance else "-"),
                html.Td(dbc.Badge(f"{avg:.1f}" if avg else "N/A", color=avg_badge_color if avg else "secondary")),
                html.Td(dbc.Badge(f"{att_rate:.0f}%", color=att_badge_color)),
                html.Td(html.Div([
                    dbc.Button(html.I(className="fas fa-eye"), id={"type": "stu-view-btn", "index": s.id},
                               color="primary", outline=True, size="sm", className="me-1"),
                    dbc.Button(html.I(className="fas fa-pen"), id={"type": "stu-edit-btn", "index": s.id},
                               color="info", outline=True, size="sm", className="me-1"),
                    dbc.Button(html.I(className="fas fa-trash"), id={"type": "stu-del-btn", "index": s.id},
                               color="danger", outline=True, size="sm"),
                ])),
            ]))

        return dbc.Table([
            html.Thead(html.Tr([
                html.Th("ID"), html.Th("Nom Complet"), html.Th("Email"),
                html.Th("Naissance"), html.Th("Moyenne"), html.Th("Presence"), html.Th("Actions"),
            ])),
            html.Tbody(rows)
        ], hover=True, borderless=True, responsive=True, className="mb-0")
    finally:
        db.close()


# Add/Edit modal
@callback(
    [Output("stu-modal", "is_open"), Output("stu-modal-title", "children"),
     Output("stu-nom", "value"), Output("stu-prenom", "value"),
     Output("stu-email", "value"), Output("stu-dob", "date"), Output("stu-edit-store", "data")],
    [Input("stu-add-btn", "n_clicks"),
     Input({"type": "stu-edit-btn", "index": ALL}, "n_clicks"),
     Input("stu-modal-cancel", "n_clicks")],
    prevent_initial_call=True,
)
def open_stu_modal(add_n, edit_ns, cancel):
    triggered = ctx.triggered_id
    if triggered == "stu-modal-cancel":
        return False, "", "", "", "", None, None
    if triggered == "stu-add-btn":
        return True, "Nouvel Etudiant", "", "", "", None, None
    if isinstance(triggered, dict) and triggered.get("type") == "stu-edit-btn":
        if not any(n for n in edit_ns if n):
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update
        sid = triggered["index"]
        db = get_db()
        try:
            s = db.query(Student).get(sid)
            if s:
                return True, f"Modifier {s.prenom} {s.nom}", s.nom, s.prenom, s.email or "", s.date_naissance, sid
        finally:
            db.close()
    return False, "", "", "", "", None, None


# Save student
@callback(
    [Output("stu-trigger", "data"), Output("stu-modal", "is_open", allow_duplicate=True),
     Output("stu-alert", "children")],
    Input("stu-modal-save", "n_clicks"),
    [State("stu-nom", "value"), State("stu-prenom", "value"),
     State("stu-email", "value"), State("stu-dob", "date"),
     State("stu-edit-store", "data"), State("stu-trigger", "data")],
    prevent_initial_call=True,
)
def save_student(n, nom, prenom, email, dob, edit_id, trigger):
    if not nom or not prenom:
        return no_update, no_update, dbc.Alert("Nom et prenom obligatoires.", color="warning", dismissable=True, duration=4000)
    
    # Validation email
    if email and not EMAIL_REGEX.match(email):
        return no_update, no_update, dbc.Alert("Format email invalide.", color="warning", dismissable=True, duration=4000)
    # Conversion de la date si necessaire
    if dob and isinstance(dob, str):
        dob = datetime.strptime(dob, '%Y-%m-%d').date()
        
    db = get_db()
    try:
        if edit_id:
            s = db.query(Student).get(edit_id)
            if s:
                # Verification doublon email si modification
                if email and email != s.email:
                    existing = db.query(Student).filter(Student.email == email).first()
                    if existing:
                        return no_update, no_update, dbc.Alert("Cet email existe deja.", color="danger", dismissable=True, duration=4000)
                s.nom = nom
                s.prenom = prenom
                s.email = email or None
                s.date_naissance = dob
                db.commit()
                return (trigger or 0) + 1, False, dbc.Alert("Etudiant modifie !", color="success", dismissable=True, duration=3000)
        else:
            if email and db.query(Student).filter(Student.email == email).first():
                return no_update, no_update, dbc.Alert("Cet email existe deja.", color="danger", dismissable=True, duration=4000)
            s = Student(nom=nom, prenom=prenom, email=email or None, date_naissance=dob)
            db.add(s)
            db.commit()
            return (trigger or 0) + 1, False, dbc.Alert("Etudiant ajoute !", color="success", dismissable=True, duration=3000)
    except Exception as e:
        db.rollback()
        return no_update, no_update, dbc.Alert(f"Erreur: {e}", color="danger", dismissable=True, duration=5000)
    finally:
        db.close()
    return no_update, no_update, no_update


# Open delete confirmation modal
@callback(
    [Output("stu-del-modal", "is_open"), Output("stu-del-store", "data")],
    [Input({"type": "stu-del-btn", "index": ALL}, "n_clicks"),
     Input("stu-del-cancel", "n_clicks")],
    prevent_initial_call=True,
)
def open_del_modal(del_ns, cancel):
    triggered = ctx.triggered_id
    if triggered == "stu-del-cancel":
        return False, None
    if isinstance(triggered, dict) and triggered.get("type") == "stu-del-btn":
        if any(n for n in del_ns if n):
            return True, triggered["index"]
    return False, None


# Confirm delete student
@callback(
    [Output("stu-trigger", "data", allow_duplicate=True),
     Output("stu-del-modal", "is_open", allow_duplicate=True),
     Output("stu-alert", "children", allow_duplicate=True)],
    Input("stu-del-confirm", "n_clicks"),
    [State("stu-del-store", "data"), State("stu-trigger", "data")],
    prevent_initial_call=True,
)
def delete_student(n, sid, trigger):
    if not sid:
        return no_update, False, no_update
    db = get_db()
    try:
        s = db.query(Student).get(sid)
        if s:
            nom_complet = f"{s.prenom} {s.nom}"
            db.delete(s)
            db.commit()
            return (trigger or 0) + 1, False, dbc.Alert(f"Etudiant {nom_complet} supprime.", color="info", dismissable=True, duration=3000)
    except Exception as e:
        db.rollback()
        return no_update, False, dbc.Alert(f"Erreur: {e}", color="danger", dismissable=True, duration=5000)
    finally:
        db.close()
    return no_update, False, no_update


# View student detail
@callback(
    [Output("stu-detail-modal", "is_open"), Output("stu-detail-title", "children"),
     Output("stu-detail-body", "children"), Output("stu-detail-store", "data")],
    Input({"type": "stu-view-btn", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def view_student(view_ns):
    triggered = ctx.triggered_id
    if not isinstance(triggered, dict) or not any(n for n in view_ns if n):
        return False, "", "", None
    sid = triggered["index"]
    db = get_db()
    try:
        s = db.query(Student).get(sid)
        if not s:
            return False, "", "", None

        avg = db.query(func.avg(Grade.note)).filter(Grade.id_student == sid).scalar()
        total_sessions = db.query(Session).count()
        absences = db.query(Attendance).filter(Attendance.id_student == sid).count()
        att_rate = ((total_sessions - absences) / total_sessions * 100) if total_sessions > 0 else 100
        n_grades = db.query(Grade).filter(Grade.id_student == sid).count()

        # Student info card
        info_card = html.Div([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Div("NOM", className="detail-label"),
                        html.Div(s.nom, className="detail-value"),
                    ], className="mb-3"),
                    html.Div([
                        html.Div("PRENOM", className="detail-label"),
                        html.Div(s.prenom, className="detail-value"),
                    ], className="mb-3"),
                ], md=3),
                dbc.Col([
                    html.Div([
                        html.Div("EMAIL", className="detail-label"),
                        html.Div(s.email or "N/A", className="detail-value"),
                    ], className="mb-3"),
                    html.Div([
                        html.Div("DATE DE NAISSANCE", className="detail-label"),
                        html.Div(s.date_naissance.strftime("%d/%m/%Y") if s.date_naissance else "N/A", className="detail-value"),
                    ], className="mb-3"),
                ], md=3),
                dbc.Col([
                    html.Div([
                        html.Div("MOYENNE", className="detail-label"),
                        html.Div(f"{avg:.2f}/20" if avg else "N/A",
                                 className="detail-value",
                                 style={"color": "#06d6a0" if avg and avg >= 12 else "#ef476f"}),
                    ], className="mb-3"),
                ], md=3),
                dbc.Col([
                    html.Div([
                        html.Div("PRESENCE", className="detail-label"),
                        html.Div(f"{att_rate:.0f}%",
                                 className="detail-value",
                                 style={"color": "#06d6a0" if att_rate >= 80 else "#ef476f"}),
                    ], className="mb-3"),
                    html.Div([
                        html.Div("ABSENCES", className="detail-label"),
                        html.Div(str(absences), className="detail-value"),
                    ]),
                ], md=3),
            ]),
        ], className="student-detail-card mb-3")

        # Grades table
        grades = db.query(Grade).filter(Grade.id_student == sid).all()
        if grades:
            grade_rows = []
            for g in grades:
                c = db.query(Course).get(g.id_course)
                color_style = {"color": "#06d6a0"} if g.note >= 12 else ({"color": "#fd7e14"} if g.note >= 10 else {"color": "#ef476f"})
                grade_rows.append(html.Tr([
                    html.Td(dbc.Badge(g.id_course, color="primary")),
                    html.Td(c.libelle if c else "-"),
                    html.Td(html.Span(f"{g.note:.2f}", style=color_style, className="fw-bold")),
                    html.Td(f"{g.coefficient}"),
                ]))
            grades_section = dbc.Table([
                html.Thead(html.Tr([html.Th("Cours"), html.Th("Matiere"), html.Th("Note /20"), html.Th("Coeff")])),
                html.Tbody(grade_rows)
            ], hover=True, borderless=True, size="sm")
        else:
            grades_section = html.P("Aucune note.", className="text-muted")

        body = html.Div([
            info_card,
            html.H6("Notes", className="fw-bold mt-4 mb-3"),
            grades_section,
        ])

        return True, f"{s.prenom} {s.nom}", body, sid
    finally:
        db.close()


# PDF Download
@callback(
    Output("stu-download", "data"),
    [Input("stu-pdf-bulletin", "n_clicks"), Input("stu-pdf-attendance", "n_clicks")],
    State("stu-detail-store", "data"),
    prevent_initial_call=True,
)
def download_pdf(bull_n, att_n, sid):
    if not sid:
        return no_update
    
    triggered = ctx.triggered_id
    
    if triggered == "stu-pdf-bulletin" and bull_n:
        from utils.pdf_generator import generate_student_bulletin
        data = generate_student_bulletin(sid)
        if data:
            return dcc.send_bytes(data, f"bulletin_etudiant_{sid}.pdf")
    
    if triggered == "stu-pdf-attendance" and att_n:
        from utils.pdf_generator import generate_attendance_report
        data = generate_attendance_report(sid)
        if data:
            return dcc.send_bytes(data, f"presence_etudiant_{sid}.pdf")
    
    return no_update
