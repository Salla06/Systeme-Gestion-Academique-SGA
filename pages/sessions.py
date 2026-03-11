import dash
from dash import html, dcc, callback, Input, Output, State, ctx, no_update
import dash_bootstrap_components as dbc
from datetime import datetime
from datetime import date as dt_date
from database import get_db
from models import Course, Session, Student, Attendance

dash.register_page(__name__, path='/sessions', name='Seances', order=2)

layout = html.Div([
    html.Div([
        html.H2("Cahier de Texte & Presences"),
        html.P("Enregistrement des seances et appel numerique", className="text-muted"),
    ], className="page-header"),

    html.Div(id="session-alert"),

    dbc.Tabs([
        dbc.Tab(label="Nouvelle Seance", tab_id="tab-new", children=[
            html.Div([
                dbc.Card([
                    dbc.CardHeader("Details de la Seance"),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Cours *"),
                                dcc.Dropdown(id="session-course-dd", placeholder="Selectionner un cours..."),
                            ], md=4),
                            dbc.Col([
                                dbc.Label("Date *"),
                                dcc.DatePickerSingle(id="session-date", date=dt_date.today(),
                                                      display_format="DD/MM/YYYY",
                                                      style={"width": "100%"}),
                            ], md=3),
                            dbc.Col([
                                dbc.Label("Duree (h) *"),
                                dbc.Input(id="session-duree", type="number", value=3, min=0.5, step=0.5),
                            ], md=2),
                            dbc.Col([
                                dbc.Label("Theme aborde"),
                                dbc.Input(id="session-theme", placeholder="Sujet de la seance"),
                            ], md=3),
                        ]),
                    ]),
                ], className="mb-3"),

                dbc.Card([
                    dbc.CardHeader([
                        html.Div([
                            html.Span("Appel Numerique"),
                            dbc.Badge(id="session-absent-count", color="danger", className="ms-2"),
                        ], className="d-flex align-items-center"),
                    ]),
                    dbc.CardBody([
                        html.P("Cochez les etudiants ABSENTS :", className="text-muted small mb-3"),
                        html.Div(id="session-checklist-container"),
                    ]),
                ], className="mb-3"),

                dbc.Button([html.I(className="fas fa-save me-2"), "Enregistrer la Seance"],
                           id="session-save-btn", color="primary", size="lg", className="w-100"),
            ], className="pt-3"),
        ]),

        dbc.Tab(label="Historique", tab_id="tab-history", children=[
            html.Div([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Filtrer par cours"),
                        dcc.Dropdown(id="history-course-filter", placeholder="Tous les cours",
                                     clearable=True),
                    ], md=4),
                    dbc.Col([
                        dbc.Label("Trier par"),
                        dcc.Dropdown(id="history-sort", value="date_desc",
                                     options=[
                                         {"label": "Date (recent)", "value": "date_desc"},
                                         {"label": "Date (ancien)", "value": "date_asc"},
                                         {"label": "Cours", "value": "course"},
                                     ]),
                    ], md=3),
                ], className="mb-3"),
                html.Div(id="history-container"),
            ], className="pt-3"),
        ]),
    ], id="session-tabs", active_tab="tab-new"),

    dcc.Store(id="session-trigger", data=0),
])


# Populate course dropdowns
@callback(
    [Output("session-course-dd", "options"), Output("history-course-filter", "options")],
    Input("session-trigger", "data"),
)
def load_courses(_):
    db = get_db()
    try:
        courses = db.query(Course).order_by(Course.code).all()
        opts = [{"label": f"{c.code} - {c.libelle}", "value": c.code} for c in courses]
        return opts, opts
    finally:
        db.close()


# Populate student checklist
@callback(
    Output("session-checklist-container", "children"),
    Input("session-course-dd", "value"),
)
def load_checklist(course_code):
    db = get_db()
    try:
        students = db.query(Student).order_by(Student.nom, Student.prenom).all()
        if not students:
            return html.P("Aucun etudiant enregistre.", className="text-muted")
        checks = []
        for s in students:
            checks.append(
                dbc.Checkbox(
                    id={"type": "absence-check", "index": s.id},
                    label=f"{s.nom} {s.prenom}",
                    value=False,
                    className="py-1",
                )
            )
        return html.Div(checks, style={"maxHeight": "350px", "overflowY": "auto"})
    finally:
        db.close()


# Count absents
@callback(
    Output("session-absent-count", "children"),
    Input({"type": "absence-check", "index": dash.ALL}, "value"),
)
def count_absents(values):
    if not values:
        return "0 absent(s)"
    n = sum(1 for v in values if v)
    return f"{n} absent(s)"


# Save session + attendance
@callback(
    [Output("session-trigger", "data", allow_duplicate=True),
     Output("session-alert", "children"),
     Output("session-course-dd", "value"),
     Output("session-theme", "value")],
    Input("session-save-btn", "n_clicks"),
    [State("session-course-dd", "value"), State("session-date", "date"),
     State("session-duree", "value"), State("session-theme", "value"),
     State({"type": "absence-check", "index": dash.ALL}, "value"),
     State({"type": "absence-check", "index": dash.ALL}, "id"),
     State("session-trigger", "data")],
    prevent_initial_call=True,
)
def save_session(n, course, date_val, duree, theme, check_values, check_ids, trigger):
    if not course or not date_val or not duree:
        return no_update, dbc.Alert("Remplissez cours, date et duree.", color="warning", dismissable=True, duration=4000), no_update, no_update

    db = get_db()
    try:
        # Convertir la date string en objet date
        if isinstance(date_val, str):
            date_val = datetime.strptime(date_val, '%Y-%m-%d').date()
        session = Session(id_course=course, date=date_val, duree=float(duree), theme=theme)
        db.add(session)
        db.flush()

        # Save absences
        absent_count = 0
        if check_values and check_ids:
            for check_id, is_absent in zip(check_ids, check_values):
                if is_absent:
                    db.add(Attendance(id_session=session.id, id_student=check_id["index"]))
                    absent_count += 1

        db.commit()
        msg = f"Seance enregistree ! ({absent_count} absent(s) marque(s))"
        return (trigger or 0) + 1, dbc.Alert(msg, color="success", dismissable=True, duration=4000), None, ""
    except Exception as e:
        db.rollback()
        return no_update, dbc.Alert(f"Erreur: {e}", color="danger", dismissable=True, duration=5000), no_update, no_update
    finally:
        db.close()


# History
@callback(
    Output("history-container", "children"),
    [Input("session-trigger", "data"), Input("history-course-filter", "value"),
     Input("history-sort", "value")],
)
def load_history(_, course_filter, sort_by):
    db = get_db()
    try:
        q = db.query(Session)
        if course_filter:
            q = q.filter(Session.id_course == course_filter)
        if sort_by == "date_desc":
            q = q.order_by(Session.date.desc())
        elif sort_by == "date_asc":
            q = q.order_by(Session.date.asc())
        elif sort_by == "course":
            q = q.order_by(Session.id_course, Session.date.desc())

        sessions = q.all()
        if not sessions:
            return html.Div([
                html.I(className="fas fa-calendar-times fa-3x text-muted"),
                html.H5("Aucune seance enregistree", className="text-muted mt-3"),
            ], className="empty-state")

        n_students = db.query(Student).count()
        rows = []
        for s in sessions:
            n_abs = db.query(Attendance).filter(Attendance.id_session == s.id).count()
            present_rate = ((n_students - n_abs) / n_students * 100) if n_students > 0 else 0

            absent_names = []
            if n_abs > 0:
                absents = db.query(Attendance).filter(Attendance.id_session == s.id).all()
                for a in absents:
                    st = db.query(Student).get(a.id_student)
                    if st:
                        absent_names.append(f"{st.nom} {st.prenom}")

            rate_color = "success" if present_rate >= 80 else ("warning" if present_rate >= 60 else "danger")

            rows.append(html.Tr([
                html.Td(dbc.Badge(s.id_course, color="primary")),
                html.Td(s.date.strftime("%d/%m/%Y") if s.date else "-"),
                html.Td(f"{s.duree}h"),
                html.Td(s.theme or "-"),
                html.Td(dbc.Badge(f"{present_rate:.0f}%", color=rate_color)),
                html.Td(
                    dbc.Badge(f"{n_abs}", color="danger" if n_abs > 0 else "success"),
                    title=", ".join(absent_names) if absent_names else "Aucun absent",
                ),
            ]))

        return dbc.Table([
            html.Thead(html.Tr([
                html.Th("Cours"), html.Th("Date"), html.Th("Duree"),
                html.Th("Theme"), html.Th("Presence"), html.Th("Absents"),
            ])),
            html.Tbody(rows)
        ], hover=True, borderless=True, responsive=True)
    finally:
        db.close()
