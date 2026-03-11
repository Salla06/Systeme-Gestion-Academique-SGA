import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from database import get_db
from models import Student, Course, Session, Attendance, Grade
from sqlalchemy import func

dash.register_page(__name__, path='/', name='Tableau de Bord', order=0)


def stat_card(title, value, icon, bg_color, icon_color):
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.Div([
                    html.Div(title, className="stat-label"),
                    html.Div(str(value), className="stat-value mt-1"),
                ]),
                html.Div(
                    html.I(className=f"{icon}"),
                    className="stat-icon",
                    style={"background": bg_color, "color": icon_color}
                ),
            ], className="d-flex justify-content-between align-items-center")
        ])
    ], className="stat-card")


layout = html.Div([
    html.Div([
        html.H2("Tableau de Bord"),
        html.P("Vue d'ensemble du systeme de gestion academique", className="text-muted"),
    ], className="page-header"),

    # Filtre
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Filtrer par cours"),
                    dcc.Dropdown(id="home-course-filter", placeholder="Tous les cours", clearable=True),
                ], md=4),
            ]),
        ])
    ], className="mb-3"),

    dbc.Row(id="home-stats-row", className="g-3 mb-4"),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Distribution des Notes"),
                dbc.CardBody(dcc.Graph(id="home-grade-chart", config={"displayModeBar": False},
                                       style={"height": "320px"}))
            ])
        ], md=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Taux de Presence par Cours"),
                dbc.CardBody(dcc.Graph(id="home-attendance-chart", config={"displayModeBar": False},
                                       style={"height": "320px"}))
            ])
        ], md=6),
    ], className="g-3 mb-4"),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Moyennes par Cours"),
                dbc.CardBody(dcc.Graph(id="home-avg-chart", config={"displayModeBar": False},
                                       style={"height": "300px"}))
            ])
        ], md=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Seances Recentes"),
                dbc.CardBody(id="home-recent-sessions", style={"maxHeight": "300px", "overflowY": "auto"})
            ])
        ], md=6),
    ], className="g-3"),

    dcc.Interval(id="home-refresh", interval=30000, n_intervals=0),
])


# Charger les options du filtre
@callback(
    Output("home-course-filter", "options"),
    Input("home-refresh", "n_intervals"),
)
def load_course_options(_):
    db = get_db()
    try:
        courses = [{"label": f"{c.code} - {c.libelle}", "value": c.code}
                   for c in db.query(Course).order_by(Course.code).all()]
        return courses
    finally:
        db.close()


@callback(
    [Output("home-stats-row", "children"),
     Output("home-grade-chart", "figure"),
     Output("home-attendance-chart", "figure"),
     Output("home-avg-chart", "figure"),
     Output("home-recent-sessions", "children")],
    [Input("home-refresh", "n_intervals"), Input("home-course-filter", "value")],
)
def update_dashboard(_, course_filter):
    db = get_db()
    try:
        n_students = db.query(Student).count()
        n_courses = db.query(Course).count()
        
        # Filtrage par cours
        if course_filter:
            n_sessions = db.query(Session).filter(Session.id_course == course_filter).count()
            avg_grade = db.query(func.avg(Grade.note)).filter(Grade.id_course == course_filter).scalar()
        else:
            n_sessions = db.query(Session).count()
            avg_grade = db.query(func.avg(Grade.note)).scalar()
        
        avg_str = f"{avg_grade:.2f}" if avg_grade else "N/A"

        stats = [
            dbc.Col(stat_card("ETUDIANTS", n_students, "fas fa-users",
                              "rgba(67,97,238,0.1)", "#4361ee"), xs=6, lg=3),
            dbc.Col(stat_card("COURS", n_courses, "fas fa-book-open",
                              "rgba(6,214,160,0.1)", "#06d6a0"), xs=6, lg=3),
            dbc.Col(stat_card("SEANCES", n_sessions, "fas fa-calendar-check",
                              "rgba(253,126,20,0.1)", "#fd7e14"), xs=6, lg=3),
            dbc.Col(stat_card("MOYENNE", avg_str, "fas fa-chart-line",
                              "rgba(239,71,111,0.1)", "#ef476f"), xs=6, lg=3),
        ]

        # Grade distribution
        if course_filter:
            grades = [g[0] for g in db.query(Grade.note).filter(Grade.id_course == course_filter).all()]
        else:
            grades = [g[0] for g in db.query(Grade.note).all()]
        
        if grades:
            fig_grades = px.histogram(x=grades, nbins=20,
                                       labels={"x": "Note", "count": "Effectif"},
                                       color_discrete_sequence=["#4361ee"])
            fig_grades.update_layout(
                margin=dict(l=40, r=20, t=10, b=40),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(gridcolor="#f0f0f0", title="Note /20"),
                yaxis=dict(gridcolor="#f0f0f0", title="Nombre"),
                bargap=0.08,
            )
        else:
            fig_grades = _empty_fig("Aucune note")

        # Attendance by course
        if course_filter:
            courses = db.query(Course).filter(Course.code == course_filter).all()
        else:
            courses = db.query(Course).all()
        
        course_labels, att_rates = [], []
        for c in courses:
            total_s = db.query(Session).filter(Session.id_course == c.code).count()
            if total_s > 0 and n_students > 0:
                total_possible = total_s * n_students
                total_abs = db.query(Attendance).join(Session).filter(Session.id_course == c.code).count()
                rate = ((total_possible - total_abs) / total_possible) * 100
                course_labels.append(c.code)
                att_rates.append(round(rate, 1))

        if course_labels:
            colors = ["#06d6a0" if r >= 80 else "#fd7e14" if r >= 60 else "#ef476f" for r in att_rates]
            fig_att = go.Figure(go.Bar(x=course_labels, y=att_rates, marker_color=colors, text=[f"{r}%" for r in att_rates], textposition='outside'))
            fig_att.update_layout(
                margin=dict(l=40, r=20, t=10, b=40),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(gridcolor="#f0f0f0"), yaxis=dict(gridcolor="#f0f0f0", range=[0, 110]),
                bargap=0.35,
            )
        else:
            fig_att = _empty_fig("Aucune seance")

        # Average by course
        avg_labels, avg_values = [], []
        for c in courses:
            avg = db.query(func.avg(Grade.note)).filter(Grade.id_course == c.code).scalar()
            if avg:
                avg_labels.append(c.code)
                avg_values.append(round(avg, 2))

        if avg_labels:
            colors2 = ["#4361ee" if v >= 12 else "#fd7e14" if v >= 10 else "#ef476f" for v in avg_values]
            fig_avg = go.Figure(go.Bar(x=avg_labels, y=avg_values, marker_color=colors2,
                                        text=[f"{v:.1f}" for v in avg_values], textposition='outside'))
            fig_avg.update_layout(
                margin=dict(l=40, r=20, t=10, b=40),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(gridcolor="#f0f0f0"), yaxis=dict(gridcolor="#f0f0f0", range=[0, 20]),
                bargap=0.35,
            )
        else:
            fig_avg = _empty_fig("Aucune note")

        # Recent sessions
        if course_filter:
            recent = db.query(Session).filter(Session.id_course == course_filter).order_by(Session.date.desc()).limit(8).all()
        else:
            recent = db.query(Session).order_by(Session.date.desc()).limit(8).all()
        
        if recent:
            rows = []
            for s in recent:
                n_abs = db.query(Attendance).filter(Attendance.id_session == s.id).count()
                rows.append(html.Tr([
                    html.Td(dbc.Badge(s.id_course, color="primary", className="me-1")),
                    html.Td(s.date.strftime("%d/%m/%Y") if s.date else ""),
                    html.Td(f"{s.duree}h"),
                    html.Td(s.theme or "-", style={"maxWidth": "200px", "overflow": "hidden", "textOverflow": "ellipsis", "whiteSpace": "nowrap"}),
                    html.Td(dbc.Badge(f"{n_abs} abs", color="danger" if n_abs > 0 else "success")),
                ]))
            recent_content = dbc.Table([
                html.Thead(html.Tr([html.Th("Cours"), html.Th("Date"), html.Th("Duree"), html.Th("Theme"), html.Th("Absences")])),
                html.Tbody(rows)
            ], hover=True, borderless=True, size="sm", className="mb-0")
        else:
            recent_content = html.Div([
                html.I(className="fas fa-calendar-times fa-2x text-muted"),
                html.P("Aucune seance", className="text-muted mt-2"),
            ], className="empty-state")

        return stats, fig_grades, fig_att, fig_avg, recent_content
    finally:
        db.close()


def _empty_fig(text):
    fig = go.Figure()
    fig.update_layout(
        annotations=[dict(text=text, showarrow=False, font=dict(size=14, color="#aaa"))],
        margin=dict(l=20, r=20, t=20, b=20),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )
    return fig
