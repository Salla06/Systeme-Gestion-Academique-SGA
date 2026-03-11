import dash
from dash import html, dcc, callback, Input, Output, State, ctx, no_update
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from database import get_db
from models import Student, Grade, Course
from sqlalchemy import func
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

dash.register_page(__name__, path='/grades', name='Notes', order=4)

layout = html.Div([
    html.Div([
        html.Div([
            html.H2("Notes & Evaluations"),
            html.P("Gestion des notes et workflow Excel", className="text-muted"),
        ]),
        html.Div([
            dbc.Button([html.I(className="fas fa-download me-2"), "Template Excel"],
                       id="grade-dl-template", color="primary", outline=True, className="me-2"),
            dbc.Button([html.I(className="fas fa-upload me-2"), "Importer Notes"],
                       id="grade-upload-toggle", color="success"),
        ], className="d-flex"),
    ], className="d-flex justify-content-between align-items-start page-header"),

    html.Div(id="grade-alert"),

    # Upload section (collapsible)
    dbc.Collapse([
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Cours cible *"),
                        dcc.Dropdown(id="grade-upload-course", placeholder="Selectionner le cours..."),
                    ], md=4),
                    dbc.Col([
                        dbc.Label("Fichier Excel"),
                        dcc.Upload(
                            id="grade-upload-file",
                            children=html.Div([
                                html.I(className="fas fa-cloud-upload-alt me-2"),
                                "Glisser ou cliquer pour uploader"
                            ]),
                            className="upload-zone",
                            style={"padding": "1.5rem"},
                        ),
                    ], md=8),
                ]),
                dbc.Button([html.I(className="fas fa-check me-2"), "Valider l'import"],
                           id="grade-import-btn", color="success", className="mt-3"),
            ])
        ], className="mb-3"),
    ], id="grade-upload-section", is_open=False),

    # Filters
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Filtrer par cours"),
                    dcc.Dropdown(id="grade-filter-course", placeholder="Tous les cours", clearable=True),
                ], md=4),
                dbc.Col([
                    dbc.Label("Filtrer par etudiant"),
                    dcc.Dropdown(id="grade-filter-student", placeholder="Tous les etudiants", clearable=True),
                ], md=4),
            ]),
        ])
    ], className="mb-3"),

    # Content
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Liste des Notes"),
                dbc.CardBody(id="grade-table-container",
                             style={"maxHeight": "500px", "overflowY": "auto"}),
            ])
        ], md=7),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Distribution"),
                dbc.CardBody(dcc.Graph(id="grade-dist-chart", config={"displayModeBar": False},
                                       style={"height": "280px"})),
            ], className="mb-3"),
            dbc.Card([
                dbc.CardHeader("Statistiques"),
                dbc.CardBody(id="grade-stats"),
            ]),
        ], md=5),
    ]),

    dcc.Store(id="grade-trigger", data=0),
    dcc.Store(id="grade-upload-contents"),
    dcc.Download(id="grade-download"),
])


# Load filter options
@callback(
    [Output("grade-filter-course", "options"), Output("grade-filter-student", "options"),
     Output("grade-upload-course", "options")],
    Input("grade-trigger", "data"),
)
def load_options(_):
    db = get_db()
    try:
        courses = [{"label": f"{c.code} - {c.libelle}", "value": c.code}
                   for c in db.query(Course).order_by(Course.code).all()]
        students = [{"label": f"{s.nom} {s.prenom}", "value": s.id}
                    for s in db.query(Student).order_by(Student.nom).all()]
        return courses, students, courses
    finally:
        db.close()


# Toggle upload section
@callback(
    Output("grade-upload-section", "is_open"),
    Input("grade-upload-toggle", "n_clicks"),
    State("grade-upload-section", "is_open"),
    prevent_initial_call=True,
)
def toggle_upload(n, is_open):
    return not is_open


# Store upload contents
@callback(
    Output("grade-upload-contents", "data"),
    Input("grade-upload-file", "contents"),
    prevent_initial_call=True,
)
def store_upload(contents):
    return contents


# Download template
@callback(
    Output("grade-download", "data"),
    Input("grade-dl-template", "n_clicks"),
    State("grade-filter-course", "value"),
    prevent_initial_call=True,
)
def download_template(n, course):
    from utils.excel_utils import generate_grade_template
    code = course or "NOTES"
    data = generate_grade_template(code)
    return dcc.send_bytes(data, f"template_notes_{code}.xlsx")


# Import grades from Excel
@callback(
    [Output("grade-trigger", "data", allow_duplicate=True),
     Output("grade-alert", "children")],
    Input("grade-import-btn", "n_clicks"),
    [State("grade-upload-contents", "data"), State("grade-upload-course", "value"),
     State("grade-trigger", "data")],
    prevent_initial_call=True,
)
def import_grades(n, contents, course_code, trigger):
    if not contents or not course_code:
        return no_update, dbc.Alert("Selectionnez un cours et un fichier.", color="warning", dismissable=True, duration=4000)

    from utils.excel_utils import parse_grade_excel
    db = get_db()
    try:
        grades_data = parse_grade_excel(contents)
        count = 0
        skipped = 0
        invalid_notes = []
        for g in grades_data:
            # Validation note entre 0 et 20
            if g['note'] < 0 or g['note'] > 20:
                invalid_notes.append(f"ID {g['id_student']}: {g['note']}")
                skipped += 1
                continue
            # Check if student exists
            student = db.query(Student).get(g['id_student'])
            if not student:
                skipped += 1
                continue
            # Update or insert
            existing = db.query(Grade).filter(
                Grade.id_student == g['id_student'],
                Grade.id_course == course_code
            ).first()
            if existing:
                existing.note = g['note']
                existing.coefficient = g['coefficient']
            else:
                db.add(Grade(id_student=g['id_student'], id_course=course_code,
                             note=g['note'], coefficient=g['coefficient']))
            count += 1
        db.commit()
        
        if invalid_notes:
            return (trigger or 0) + 1, dbc.Alert(
                f"{count} notes importees. {skipped} ignorees (notes hors [0-20]: {', '.join(invalid_notes[:3])}{'...' if len(invalid_notes) > 3 else ''})",
                color="warning", dismissable=True, duration=6000)
        return (trigger or 0) + 1, dbc.Alert(f"{count} notes importees avec succes !", color="success", dismissable=True, duration=4000)
    except Exception as e:
        db.rollback()
        return no_update, dbc.Alert(f"Erreur: {e}", color="danger", dismissable=True, duration=5000)
    finally:
        db.close()


# Render grades table + chart + stats
@callback(
    [Output("grade-table-container", "children"),
     Output("grade-dist-chart", "figure"),
     Output("grade-stats", "children")],
    [Input("grade-trigger", "data"), Input("grade-filter-course", "value"),
     Input("grade-filter-student", "value")],
)
def render_grades(_, course_filter, student_filter):
    db = get_db()
    try:
        q = db.query(Grade)
        if course_filter:
            q = q.filter(Grade.id_course == course_filter)
        if student_filter:
            q = q.filter(Grade.id_student == student_filter)
        grades = q.all()

        if not grades:
            empty = html.Div([
                html.I(className="fas fa-clipboard fa-2x text-muted"),
                html.P("Aucune note", className="text-muted mt-2"),
            ], className="empty-state")
            empty_fig = go.Figure()
            empty_fig.update_layout(
                annotations=[dict(text="Pas de donnees", showarrow=False, font=dict(color="#aaa"))],
                margin=dict(l=20, r=20, t=20, b=20),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(visible=False), yaxis=dict(visible=False),
            )
            return empty, empty_fig, html.P("Aucune donnee.", className="text-muted")

        # Table
        rows = []
        notes_list = []
        for g in grades:
            s = db.query(Student).get(g.id_student)
            color = "#06d6a0" if g.note >= 12 else ("#fd7e14" if g.note >= 10 else "#ef476f")
            rows.append(html.Tr([
                html.Td(f"{s.nom} {s.prenom}" if s else "?"),
                html.Td(dbc.Badge(g.id_course, color="primary")),
                html.Td(html.Span(f"{g.note:.2f}", style={"color": color}, className="fw-bold")),
                html.Td(f"{g.coefficient}"),
            ]))
            notes_list.append(g.note)

        table = dbc.Table([
            html.Thead(html.Tr([html.Th("Etudiant"), html.Th("Cours"), html.Th("Note"), html.Th("Coeff")])),
            html.Tbody(rows)
        ], hover=True, borderless=True, size="sm")

        # Chart
        fig = px.histogram(x=notes_list, nbins=15, color_discrete_sequence=["#4361ee"],
                           labels={"x": "Note", "count": "Effectif"})
        fig.update_layout(
            margin=dict(l=30, r=10, t=10, b=30),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="#f0f0f0"), yaxis=dict(gridcolor="#f0f0f0"),
            bargap=0.08,
        )

        # Stats
        avg = sum(notes_list) / len(notes_list)
        min_n, max_n = min(notes_list), max(notes_list)
        passed = sum(1 for n in notes_list if n >= 10)
        stats = html.Div([
            dbc.Row([
                dbc.Col([
                    html.Div("Moyenne", className="text-muted small"),
                    html.Div(f"{avg:.2f}", className="fw-bold fs-5",
                             style={"color": "#4361ee"}),
                ], xs=6, className="text-center mb-2"),
                dbc.Col([
                    html.Div("Effectif", className="text-muted small"),
                    html.Div(str(len(notes_list)), className="fw-bold fs-5"),
                ], xs=6, className="text-center mb-2"),
            ]),
            dbc.Row([
                dbc.Col([
                    html.Div("Min", className="text-muted small"),
                    html.Div(f"{min_n:.2f}", className="fw-bold", style={"color": "#ef476f"}),
                ], xs=4, className="text-center"),
                dbc.Col([
                    html.Div("Max", className="text-muted small"),
                    html.Div(f"{max_n:.2f}", className="fw-bold", style={"color": "#06d6a0"}),
                ], xs=4, className="text-center"),
                dbc.Col([
                    html.Div("Reussite", className="text-muted small"),
                    html.Div(f"{passed}/{len(notes_list)}", className="fw-bold"),
                ], xs=4, className="text-center"),
            ]),
        ])

        return table, fig, stats
    finally:
        db.close()
