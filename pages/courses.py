import dash
from dash import html, dcc, callback, Input, Output, State, ctx, no_update, ALL
import dash_bootstrap_components as dbc
from database import get_db
from models import Course, Session
from sqlalchemy import func

dash.register_page(__name__, path='/courses', name='Cours', order=1)

# Add/Edit modal
course_modal = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle(id="course-modal-title")),
    dbc.ModalBody([
        dbc.Row([
            dbc.Col([
                dbc.Label("Code du Cours *"),
                dbc.Input(id="course-code-input", placeholder="ex: MATH101"),
            ], md=6),
            dbc.Col([
                dbc.Label("Volume Horaire (h) *"),
                dbc.Input(id="course-volume-input", type="number", placeholder="ex: 42", min=1),
            ], md=6),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Libelle *"),
                dbc.Input(id="course-libelle-input", placeholder="Nom complet du cours"),
            ], md=6),
            dbc.Col([
                dbc.Label("Enseignant"),
                dbc.Input(id="course-enseignant-input", placeholder="Nom de l'enseignant"),
            ], md=6),
        ]),
    ]),
    dbc.ModalFooter([
        dbc.Button("Annuler", id="course-modal-cancel", color="secondary", outline=True, className="me-2"),
        dbc.Button("Enregistrer", id="course-modal-save", color="primary"),
    ]),
], id="course-modal", is_open=False, centered=True, size="lg")

# Delete confirm modal
delete_modal = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("Confirmer la suppression")),
    dbc.ModalBody(html.P("Cette action supprimera le cours, ses seances et les notes associees. Continuer ?")),
    dbc.ModalFooter([
        dbc.Button("Annuler", id="course-del-cancel", color="secondary", outline=True, className="me-2"),
        dbc.Button("Supprimer", id="course-del-confirm", color="danger"),
    ]),
], id="course-del-modal", is_open=False, centered=True)

layout = html.Div([
    html.Div([
        html.Div([
            html.H2("Gestion des Cours"),
            html.P("Curriculum et suivi de progression", className="text-muted"),
        ]),
        dbc.Button([html.I(className="fas fa-plus me-2"), "Nouveau Cours"],
                   id="course-add-btn", color="primary"),
    ], className="d-flex justify-content-between align-items-start page-header"),

    html.Div(id="course-alert"),
    html.Div(id="courses-container"),
    course_modal,
    delete_modal,
    dcc.Store(id="course-edit-store", data=None),
    dcc.Store(id="course-del-store", data=None),
    dcc.Store(id="courses-trigger", data=0),
])


@callback(
    Output("courses-container", "children"),
    Input("courses-trigger", "data"),
)
def render_courses(_):
    db = get_db()
    try:
        courses = db.query(Course).order_by(Course.code).all()
        if not courses:
            return dbc.Card(dbc.CardBody(html.Div([
                html.I(className="fas fa-book-open fa-3x text-muted"),
                html.H5("Aucun cours enregistre", className="text-muted mt-3"),
                html.P("Cliquez sur 'Nouveau Cours' pour commencer.", className="text-muted small"),
            ], className="empty-state")))

        cards = []
        for c in courses:
            hours_done = db.query(func.sum(Session.duree)).filter(Session.id_course == c.code).scalar() or 0
            pct = min((hours_done / c.volume_horaire) * 100, 100) if c.volume_horaire > 0 else 0
            n_sessions = db.query(Session).filter(Session.id_course == c.code).count()

            if pct >= 100:
                bar_color = "success"
            elif pct >= 50:
                bar_color = "primary"
            elif pct >= 25:
                bar_color = "warning"
            else:
                bar_color = "info"

            card = dbc.Col(
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.Div([
                                dbc.Badge(c.code, color="primary", className="mb-2"),
                                html.H5(c.libelle, className="fw-bold mb-1",
                                         style={"fontSize": "1rem"}),
                                html.P([
                                    html.I(className="fas fa-user-tie me-1"),
                                    c.enseignant or "Non assigne"
                                ], className="text-muted small mb-0"),
                            ]),
                            html.Div([
                                dbc.Button(html.I(className="fas fa-pen"),
                                           id={"type": "course-edit-btn", "index": c.code},
                                           color="primary", outline=True, size="sm", className="me-1"),
                                dbc.Button(html.I(className="fas fa-trash"),
                                           id={"type": "course-del-btn", "index": c.code},
                                           color="danger", outline=True, size="sm"),
                            ], className="d-flex"),
                        ], className="d-flex justify-content-between align-items-start"),
                        html.Hr(className="my-3"),
                        html.Div([
                            html.Div([
                                html.Small(f"{hours_done:.0f}h / {c.volume_horaire:.0f}h", className="text-muted fw-bold"),
                                html.Small(f"{pct:.0f}%", className="fw-bold",
                                           style={"color": {"success": "#06d6a0", "primary": "#4361ee", "warning": "#fd7e14", "info": "#0dcaf0"}.get(bar_color)}),
                            ], className="d-flex justify-content-between mb-1"),
                            dbc.Progress(value=pct, color=bar_color, style={"height": "8px"}),
                        ]),
                        html.Div([
                            html.Small([html.I(className="fas fa-calendar-alt me-1"), f"{n_sessions} seances"],
                                       className="text-muted"),
                        ], className="mt-2"),
                    ])
                ], className="h-100"),
                md=6, lg=4, className="mb-3",
            )
            cards.append(card)
        return dbc.Row(cards, className="g-3")
    finally:
        db.close()


# Open add modal
@callback(
    [Output("course-modal", "is_open"), Output("course-modal-title", "children"),
     Output("course-code-input", "value"), Output("course-libelle-input", "value"),
     Output("course-volume-input", "value"), Output("course-enseignant-input", "value"),
     Output("course-code-input", "disabled"), Output("course-edit-store", "data")],
    [Input("course-add-btn", "n_clicks"),
     Input({"type": "course-edit-btn", "index": ALL}, "n_clicks"),
     Input("course-modal-cancel", "n_clicks")],
    prevent_initial_call=True,
)
def open_course_modal(add_n, edit_ns, cancel_n):
    triggered = ctx.triggered_id
    if triggered == "course-modal-cancel":
        return False, "", "", "", "", "", False, None
    if triggered == "course-add-btn":
        return True, "Nouveau Cours", "", "", "", "", False, None
    if isinstance(triggered, dict) and triggered.get("type") == "course-edit-btn":
        if not any(n for n in edit_ns if n):
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
        code = triggered["index"]
        db = get_db()
        try:
            c = db.query(Course).get(code)
            if c:
                return True, f"Modifier {c.code}", c.code, c.libelle, c.volume_horaire, c.enseignant or "", True, c.code
        finally:
            db.close()
    return False, "", "", "", "", "", False, None


# Save course
@callback(
    [Output("courses-trigger", "data"), Output("course-modal", "is_open", allow_duplicate=True),
     Output("course-alert", "children")],
    Input("course-modal-save", "n_clicks"),
    [State("course-code-input", "value"), State("course-libelle-input", "value"),
     State("course-volume-input", "value"), State("course-enseignant-input", "value"),
     State("course-edit-store", "data"), State("courses-trigger", "data")],
    prevent_initial_call=True,
)
def save_course(n, code, libelle, volume, enseignant, edit_code, trigger):
    if not code or not libelle or not volume:
        return no_update, no_update, dbc.Alert("Remplissez tous les champs obligatoires (*)", color="warning", dismissable=True, duration=4000)

    db = get_db()
    try:
        if edit_code:
            c = db.query(Course).get(edit_code)
            if c:
                c.libelle = libelle
                c.volume_horaire = float(volume)
                c.enseignant = enseignant
                db.commit()
                return (trigger or 0) + 1, False, dbc.Alert("Cours modifie avec succes !", color="success", dismissable=True, duration=3000)
        else:
            if db.query(Course).get(code):
                return no_update, no_update, dbc.Alert(f"Le code '{code}' existe deja.", color="danger", dismissable=True, duration=4000)
            db.add(Course(code=code, libelle=libelle, volume_horaire=float(volume), enseignant=enseignant))
            db.commit()
            return (trigger or 0) + 1, False, dbc.Alert("Cours ajoute avec succes !", color="success", dismissable=True, duration=3000)
    except Exception as e:
        db.rollback()
        return no_update, no_update, dbc.Alert(f"Erreur: {e}", color="danger", dismissable=True, duration=5000)
    finally:
        db.close()
    return no_update, no_update, no_update


# Open delete modal
@callback(
    [Output("course-del-modal", "is_open"), Output("course-del-store", "data")],
    [Input({"type": "course-del-btn", "index": ALL}, "n_clicks"),
     Input("course-del-cancel", "n_clicks")],
    prevent_initial_call=True,
)
def open_del_modal(del_ns, cancel):
    triggered = ctx.triggered_id
    if isinstance(triggered, dict) and triggered.get("type") == "course-del-btn":
        if any(n for n in del_ns if n):
            return True, triggered["index"]
    return False, None


# Confirm delete
@callback(
    [Output("courses-trigger", "data", allow_duplicate=True),
     Output("course-del-modal", "is_open", allow_duplicate=True),
     Output("course-alert", "children", allow_duplicate=True)],
    Input("course-del-confirm", "n_clicks"),
    [State("course-del-store", "data"), State("courses-trigger", "data")],
    prevent_initial_call=True,
)
def delete_course(n, code, trigger):
    if not code:
        return no_update, False, no_update
    db = get_db()
    try:
        c = db.query(Course).get(code)
        if c:
            db.delete(c)
            db.commit()
            return (trigger or 0) + 1, False, dbc.Alert(f"Cours {code} supprime.", color="info", dismissable=True, duration=3000)
    except Exception as e:
        db.rollback()
        return no_update, False, dbc.Alert(f"Erreur: {e}", color="danger", dismissable=True, duration=5000)
    finally:
        db.close()
    return no_update, False, no_update
