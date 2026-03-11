import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from database import init_db, seed_sample_data

# Initialize database (Module 0: auto-create tables)
init_db()
seed_sample_data()

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css",
    ],
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    title="SGA - Gestion Academique",
)

# Sidebar
sidebar = html.Div([
    # Brand
    html.Div([
        html.Div([
            html.I(className="fas fa-graduation-cap fa-lg", style={"color": "#4361ee"}),
            html.H4("SGA", className="ms-2 mb-0", style={"color": "#fff"}),
        ], className="d-flex align-items-center"),
        html.Small("GESTION ACADEMIQUE", style={"color": "rgba(255,255,255,0.4)", "letterSpacing": "1.5px"}),
    ], className="sidebar-brand"),

    # Navigation sections
    html.Div("PRINCIPAL", className="sidebar-section"),
    dbc.Nav([
        dbc.NavLink([html.I(className="fas fa-chart-pie"), "Tableau de Bord"],
                     href="/", active="exact"),
        dbc.NavLink([html.I(className="fas fa-book-open"), "Cours"],
                     href="/courses", active="exact"),
        dbc.NavLink([html.I(className="fas fa-calendar-check"), "Séances & Présences"],
                     href="/sessions", active="exact"),
    ], vertical=True, pills=True),

    html.Div("GESTION", className="sidebar-section"),
    dbc.Nav([
        dbc.NavLink([html.I(className="fas fa-user-graduate"), "Etudiants"],
                     href="/students", active="exact"),
        dbc.NavLink([html.I(className="fas fa-clipboard-list"), "Notes"],
                     href="/grades", active="exact"),
    ], vertical=True, pills=True),

    html.Div("OUTILS", className="sidebar-section"),
    dbc.Nav([
        dbc.NavLink([html.I(className="fas fa-file-import"), "Import Excel"],
                     href="/import", active="exact"),
    ], vertical=True, pills=True),

    # Footer
    html.Div([
        html.Hr(style={"borderColor": "rgba(255,255,255,0.08)"}),
        html.Div([
            html.I(className="fas fa-code me-2", style={"color": "rgba(255,255,255,0.3)"}),
            html.Small("Dash + SQLAlchemy", style={"color": "rgba(255,255,255,0.3)"}),
        ], className="d-flex align-items-center"),
    ], style={"position": "absolute", "bottom": "1rem", "left": "1.25rem", "right": "1.25rem"}),

], className="sidebar")

# Main layout
app.layout = html.Div([
    dcc.Location(id="url"),
    sidebar,
    html.Div(
        dash.page_container,
        className="content",
    ),
])

server = app.server

if __name__ == '__main__':
    app.run(debug=True, port=8050)
