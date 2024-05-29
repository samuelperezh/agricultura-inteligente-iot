from crate import client
import dash
from dash import dcc
from dash import html
import dash_bootstrap_components as bdc
import plotly.graph_objs as go
from dash.dependencies import Input, Output
import dash_daq as daq
import pandas as pd
import plotly.express as px
import numpy as np
from scipy.interpolate import interp1d
from skforecast.ForecasterAutoreg import ForecasterAutoreg
from sklearn.linear_model import LinearRegression
from flask import Flask, request, jsonify
from flask_cors import CORS

server = Flask(__name__)
CORS(server)
app = dash.Dash(server=server, routes_pathname_prefix="/", external_stylesheets=[bdc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

basededatos = "http://0.0.0.0:4200"

def leer(url_db, variable, tabla, entity):
    con = client.connect(url_db)
    cur = con.cursor()
    cur.execute(f"SELECT entity_id, time_index, {variable} FROM {tabla} WHERE entity_id = '{entity}' ORDER BY time_index ASC;")
    result = cur.fetchall()
    datos = pd.DataFrame(result,columns=['id','timestamp',variable])
    return datos

def gps(url_db):
    con = client.connect(url_db)
    cur = con.cursor()
    cur.execute(f"SELECT latitud, longitud FROM etgps ORDER BY time_index ASC;")
    result = cur.fetchall()
    datos = pd.DataFrame(result,columns=['latitud','longitud'])
    return datos

def alarma(datos, lim_inf, lim_sup):
    cnt=0
    for d in datos:
        if d > lim_sup or d < lim_inf:
            cnt += 1
    return 'red' if cnt > 0 else 'green'

def predecir(datos, variable):
    data = datos
    data['fecha'] = pd.to_datetime(data['timestamp'], unit='ms')
    data = data.sort_values('fecha', ascending=True)
    data = data.reset_index()
    data['minutos'] = (data['fecha'] - data['fecha'][0]).dt.total_seconds() / 3600
    tiempo = data["minutos"].to_list()
    var = data[variable].to_list()
    t = np.linspace(min(tiempo), max(tiempo), 1000)
    f = interp1d(tiempo, var)
    y = f(t)
    data = pd.DataFrame(list(zip(t, y)), columns=["t", "y"])
    steps = 200
    data_train = data[:-steps]
    data_test = data[-steps:]
    forecaster = ForecasterAutoreg(regressor=LinearRegression(), lags=125)
    forecaster.fit(y=data_train['y'])
    predictions = forecaster.predict(steps=steps + 150)
    return data_train, data_test, predictions

def actualizar_datos():
    temperatura = leer(basededatos, 'temperatura', 'ettemperatura', 'sensorTemperatura')
    humedad = leer(basededatos, 'humedad', 'ethumedad', 'sensorHumedad')
    luz = leer(basededatos, 'luz', 'etluz', 'sensorLuz')
    proximidad = leer(basededatos, 'proximidad', 'etproximidad', 'sensorProximidad')
    gps_data = gps(basededatos)
    data_trainT, data_testT, predictionsT = predecir(temperatura, 'temperatura')
    data_trainH, data_testH, predictionsH = predecir(humedad, 'humedad')
    return temperatura, humedad, luz, proximidad, gps_data, data_trainT, data_testT, predictionsT, data_trainH, data_testH, predictionsH

app.layout = html.Div([
    bdc.NavbarSimple(
        brand="IoT Control de Planta",
        brand_href="/",
        color="success",
        dark=True,
        children=[
            bdc.NavItem(bdc.NavLink("Inicio", href="/inicio")),
            bdc.NavItem(bdc.NavLink("Sensores", href="/sensores")),
            bdc.NavItem(bdc.NavLink("Información", href="/informacion"))
        ]
    ),
    dcc.Location(id='url', refresh=False),
    html.Div(id='contenido'),
    html.Footer("Samuel Pérez Hurtado - Internet de las Cosas - Universidad Pontificia Bolivariana 2024 ©"),
    dcc.Interval(
        id='interval-component',
        interval=10*1000,  # en milisegundos
        n_intervals=0
    )
])

inicio_layout = html.Div([
    html.H2("Información del proyecto", style={'text-align': 'center'}),
    html.P("Este es un proyecto de IoT que permite monitorear la planta Primavera. Se utilizan sensores de humedad, temperatura y luz para obtener información en tiempo real. Además, se toman fotos de las plantas para tener un historial de su crecimiento."),
    html.H2("Primavera"),
    html.P("La planta Primavera es una planta de interior que necesita cuidados especiales. Es una planta que necesita mucha luz y poca agua. Se recomienda regarla una vez a la semana y mantenerla en un lugar con luz indirecta."),
    html.Img(src='https://images.meredith.com/content/dam/bhg/Images/life-in-color/whopper%20begonia.jpg.rendition.largest.jpg', alt= 'Primavera', style={'width':'50%'}),
])

sensores_layout = html.Div([
    html.H2("Dashboard de control para los sensores", style={'text-align': 'center'}),
    html.Div([
        dcc.Graph(id='TemperaturaVsTiempo', style={'display': 'inline-block', 'width': '50%'}),
        dcc.Graph(id='Prediccion Temperatura', style={'display': 'inline-block', 'width': '50%'})
    ], style={'display': 'flex'}),
    html.Div([
        dcc.Graph(id='HumedadVsTiempo', style={'display': 'inline-block', 'width': '50%'}),
        dcc.Graph(id='Prediccion Humedad', style={'display': 'inline-block', 'width': '50%'})
    ], style={'display': 'flex'}),
    html.Div([
        dcc.Graph(id='LuzVsTiempo', style={'display': 'inline-block', 'width': '50%'}),
        dcc.Graph(id='ProximidadVsTiempo', style={'display': 'inline-block', 'width': '50%'})
    ], style={'display': 'flex'}),
    dcc.Graph(id='Mapa'),
])

informacion_layout = html.Div([
    html.H2("Historial de la planta", style={'text-align': 'center'}),
])

@app.callback(Output('contenido', 'children'), Input('url', 'pathname'))
def mostrar_contenido(pathname):
    if pathname == '/inicio':
        return inicio_layout
    elif pathname == '/sensores':
        return sensores_layout
    elif pathname == '/informacion':
        return informacion_layout
    else:
        return "error 500"

@app.callback(
    [Output('TemperaturaVsTiempo', 'figure'),
     Output('HumedadVsTiempo', 'figure'),
     Output('LuzVsTiempo', 'figure'),
     Output('ProximidadVsTiempo', 'figure'),
     Output('Prediccion Temperatura', 'figure'),
     Output('Prediccion Humedad', 'figure'),
     Output('Mapa', 'figure')],
    Input('interval-component', 'n_intervals')
)
def actualizar_graficas(n):
    temperatura, humedad, luz, proximidad, gps_data, data_trainT, data_testT, predictionsT, data_trainH, data_testH, predictionsH = actualizar_datos()
    
    temperatura_x = pd.to_datetime(temperatura['timestamp'], unit='ms')
    humedad_x = pd.to_datetime(humedad['timestamp'], unit='ms')
    luz_x = pd.to_datetime(luz['timestamp'], unit='ms')
    proximidad_x = pd.to_datetime(proximidad['timestamp'], unit='ms')
    temperatura_y = temperatura['temperatura']
    humedad_y = humedad['humedad']
    luz_y = luz['luz']
    proximidad_y = proximidad['proximidad']
    latitud = gps_data['latitud']
    longitud = gps_data['longitud']
    
    fig_temperatura = {
        'data': [go.Scatter(
            x=temperatura_x,
            y=temperatura_y,
            name='Temperatura'
        )],
        'layout': go.Layout(
            title='Temperatura vs Tiempo',
            xaxis={'title': 'Tiempo'},
            yaxis={'title': 'Temperatura'},
            shapes=[
                dict(type="line", yref='y', y0=16, y1=16, xref="paper", x0=0, x1=1, line=dict(color='red')),
                dict(type="line", yref='y', y0=24, y1=24, xref="paper", x0=0, x1=1, line=dict(color='red'))
            ],
            annotations=[
                dict(
                    x=0.65,  # Colocación horizontal
                    y=1.15,  # Colocación vertical
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    text="",
                    xanchor='center',
                    yanchor='bottom',
                    bgcolor=alarma(temperatura_y, 16, 24),
                    opacity=1,
                    bordercolor="black",
                    borderwidth=2,
                    borderpad=4,
                    width=20,
                    height=20,
                )
            ]
        )
    }
    
    fig_humedad = {
        'data': [go.Scatter(
            x=humedad_x,
            y=humedad_y,
            name='Humedad'
        )],
        'layout': go.Layout(
            title='Humedad vs Tiempo',
            xaxis={'title': 'Tiempo'},
            yaxis={'title': 'Humedad'},
            shapes=[
                dict(type="line", yref='y', y0=50, y1=50, xref="paper", x0=0, x1=1, line=dict(color='red')),
                dict(type="line", yref='y', y0=76, y1=76, xref="paper", x0=0, x1=1, line=dict(color='red'))
            ],
            annotations=[
                dict(
                    x=0.65,  # Colocación horizontal
                    y=1.15,  # Colocación vertical
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    text="",
                    xanchor='center',
                    yanchor='bottom',
                    bgcolor=alarma(humedad_y, 50, 76),
                    opacity=1,
                    bordercolor="black",
                    borderwidth=2,
                    borderpad=4,
                    width=20,
                    height=20,
                )
            ]
        )
    }

    fig_luz = {
        'data': [go.Scatter(
            x=luz_x,
            y=luz_y,
            name='Luz'
        )],
        'layout': go.Layout(
            title='Luz vs Tiempo',
            xaxis={'title': 'Tiempo'},
            yaxis={'title': 'Luz'},
            shapes=[
                dict(type="line", yref='y', y0=1000, y1=1000, xref="paper", x0=0, x1=1, line=dict(color='red')),
                dict(type="line", yref='y', y0=1200, y1=1200, xref="paper", x0=0, x1=1, line=dict(color='red'))],
            annotations=[
                dict(x=0.65,  # Colocación horizontal
                     y=1.15,  # Colocación vertical
                     xref="paper",
                     yref="paper",
                     showarrow=False,
                     text="",
                     xanchor='center',
                     yanchor='bottom',
                     bgcolor=alarma(luz_y, 1000, 1200),
                     opacity=1,
                     bordercolor="black",
                     borderwidth=2,
                     borderpad=4,
                     width=20,
                     height=20,)]
        )
    }

    fig_proximidad = {
        'data': [go.Scatter(
            x=proximidad_x,
            y=proximidad_y,
            name='Proximidad'
        )],
        'layout': go.Layout(
            title='Proximidad vs Tiempo',
            xaxis={'title': 'Tiempo'},
            yaxis={'title': 'Proximidad'},
        )
    }

    fig_prediccion_temperatura = {
        'data': [
            go.Scatter(
                x=data_trainT.index,
                y=data_trainT['y'],
                mode='lines',
                name='Entrenamiento'
            ),
            go.Scatter(
                x=data_testT.index,
                y=data_testT['y'],
                mode='lines',
                name='Prueba'
            ),
            go.Scatter(
                x=predictionsT.index,
                y=predictionsT,
                mode='lines',
                name='Predicciones'
            )
        ],
        'layout': go.Layout(
            title='Predicción Temperatura',
            xaxis={'title': 'Tiempo'},
            yaxis={'title': 'Predicción'},
        )
    }

    fig_prediccion_humedad = {
        'data': [
            go.Scatter(
                x=data_trainH.index,
                y=data_trainH['y'],
                mode='lines',
                name='Entrenamiento'
            ),
            go.Scatter(
                x=data_testH.index,
                y=data_testH['y'],
                mode='lines',
                name='Prueba'
            ),
            go.Scatter(
                x=predictionsH.index,
                y=predictionsH,
                mode='lines',
                name='Predicciones'
            )
        ],
        'layout': go.Layout(
            title='Predicción Humedad',
            xaxis={'title': 'Tiempo'},
            yaxis={'title': 'Predicción'},
        )
    }
    
    fig_gps = {
        'data': [{
            'lat': latitud,
            'lon': longitud,
            'marker': {
                'color': 150,
                'size': 11,
                'opacity': 0.6
            },
            'customdata': 'data',
            'type': 'scattermapbox'
        }],
        'layout': {
            'mapbox': {
                'accesstoken': 'pk.eyJ1IjoibGVvbmFyZG9iZXRhbmN1ciIsImEiOiJjazlybGNiZWcwYjZ6M2dwNGY4MmY2eGpwIn0.EJjpR4klZpOHSfdm7Tsfkw',
                'center' : {
                    'lat': 6.240737,
                    'lon': -75.589900
                    },
                'zoom' : 10
            },
            'hovermode': 'closest',
            'margin': {'l': 0, 'r': 0, 'b': 0, 't': 0}
        }
    }

    return fig_temperatura, fig_humedad, fig_luz, fig_proximidad, fig_prediccion_temperatura, fig_prediccion_humedad, fig_gps

@server.route('/predecirtemperatura', methods=['GET'])
def predecirtemperatura():
    temperatura = leer(basededatos, 'temperatura', 'ettemperatura', 'sensorTemperatura')
    data_train, data_test, predictions = predecir(temperatura, 'temperatura')    
    return jsonify({
        'data_train': {
            'x': data_train.index.to_list(),
            'y': data_train['y'].to_list()
        },
        'data_test': {
            'x': data_test.index.to_list(),
            'y': data_test['y'].to_list()
        },
        'predictions': {
            'x': predictions.index.to_list(),
            'y': predictions.to_list()
        }
    })
    
@server.route('/predecirhumedad', methods=['GET'])
def predecirhumedad():
    humedad = leer(basededatos, 'humedad', 'ethumedad', 'sensorHumedad')
    data_train, data_test, predictions = predecir(humedad, 'humedad')
    return jsonify({
        'data_train': {
            'x': data_train.index.to_list(),
            'y': data_train['y'].to_list()
        },
        'data_test': {
            'x': data_test.index.to_list(),
            'y': data_test['y'].to_list()
        },
        'predictions': {
            'x': predictions.index.to_list(),
            'y': predictions.to_list()
        }
    })

if __name__ == '__main__':
    app.run_server(use_reloader=False, host='0.0.0.0',port=80)