import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch
from app import app, server, leer, gps, alarma, predecir, actualizar_datos

@pytest.fixture
def client():
    with server.test_client() as client:
        yield client

def test_leer():
    mock_data = [('sensor1', 1609459200000, 22.5), ('sensor1', 1609459260000, 23.0)]
    with patch('crate.client.connect') as mock_connect:
        mock_connect.return_value.cursor.return_value.fetchall.return_value = mock_data
        data = leer('http://localhost:4200', 'temperatura', 'ettemperatura', 'sensorTemperatura')
        assert isinstance(data, pd.DataFrame)
        assert len(data) == 2
        assert list(data.columns) == ['id', 'timestamp', 'temperatura']

def test_gps():
    mock_data = [(6.267, -75.568), (6.268, -75.569)]
    with patch('crate.client.connect') as mock_connect:
        mock_connect.return_value.cursor.return_value.fetchall.return_value = mock_data
        data = gps('http://localhost:4200')
        assert isinstance(data, pd.DataFrame)
        assert len(data) == 2
        assert list(data.columns) == ['latitud', 'longitud']

def test_alarma():
    datos = [22.5, 23.0, 25.0]
    assert alarma(datos, 16, 24) == 'red'
    datos = [18.0, 20.0, 22.0]
    assert alarma(datos, 16, 24) == 'green'

def test_predecir():
    mock_data = pd.DataFrame({
        'timestamp': [1609459200000, 1609459260000, 1609459320000],
        'temperatura': [22.5, 23.0, 23.5]
    })
    data_train, data_test, predictions = predecir(mock_data, 'temperatura')
    assert isinstance(data_train, pd.DataFrame)
    assert isinstance(data_test, pd.DataFrame)
    assert isinstance(predictions, pd.Series)

def test_actualizar_datos():
    with patch('app.leer') as mock_leer, patch('app.gps') as mock_gps, patch('app.predecir') as mock_predecir:
        mock_leer.side_effect = [
            pd.DataFrame({'timestamp': [1609459200000], 'temperatura': [22.5]}),
            pd.DataFrame({'timestamp': [1609459200000], 'humedad': [50]}),
            pd.DataFrame({'timestamp': [1609459200000], 'luz': [1000]}),
            pd.DataFrame({'timestamp': [1609459200000], 'proximidad': [1]}),
        ]
        mock_gps.return_value = pd.DataFrame({'latitud': [6.267], 'longitud': [-75.568]})
        mock_predecir.side_effect = [
            (pd.DataFrame(), pd.DataFrame(), pd.Series(dtype='float64')),
            (pd.DataFrame(), pd.DataFrame(), pd.Series(dtype='float64'))
        ]
        results = actualizar_datos()
        assert len(results) == 11

def test_predecirtemperatura(client):
    with patch('app.leer') as mock_leer, patch('app.predecir') as mock_predecir:
        mock_leer.return_value = pd.DataFrame({'timestamp': [1609459200000], 'temperatura': [22.5]})
        mock_predecir.return_value = (pd.DataFrame({'index': [0], 'y': [22.5]}), pd.DataFrame({'index': [0], 'y': [22.5]}), pd.Series([22.5]))
        response = client.get('/predecirtemperatura')
        assert response.status_code == 200
        data = response.get_json()
        assert 'data_train' in data
        assert 'data_test' in data
        assert 'predictions' in data

def test_predecirhumedad(client):
    with patch('app.leer') as mock_leer, patch('app.predecir') as mock_predecir:
        mock_leer.return_value = pd.DataFrame({'timestamp': [1609459200000], 'humedad': [50]})
        mock_predecir.return_value = (pd.DataFrame({'index': [0], 'y': [50]}), pd.DataFrame({'index': [0], 'y': [50]}), pd.Series([50]))
        response = client.get('/predecirhumedad')
        assert response.status_code == 200
        data = response.get_json()
        assert 'data_train' in data
        assert 'data_test' in data
        assert 'predictions' in data

def test_mostrar_contenido():
    with app.server.test_client() as client:
        response = client.get('/inicio')
        assert response.status_code == 200
        response_text = response.data.decode('utf-8')
        assert 'html' in response_text

def test_actualizar_graficas():
    with patch('app.actualizar_datos') as mock_actualizar_datos:
        mock_actualizar_datos.return_value = (
            pd.DataFrame({'timestamp': [1609459200000], 'temperatura': [22.5]}),
            pd.DataFrame({'timestamp': [1609459200000], 'humedad': [50]}),
            pd.DataFrame({'timestamp': [1609459200000], 'luz': [1000]}),
            pd.DataFrame({'timestamp': [1609459200000], 'proximidad': [1]}),
            pd.DataFrame({'latitud': [6.267], 'longitud': [-75.568]}),
            pd.DataFrame(), pd.DataFrame(), pd.Series(dtype='float64'),
            pd.DataFrame(), pd.DataFrame(), pd.Series(dtype='float64')
        )
        with app.server.test_client() as client:
            response = client.get('/inicio')
            assert response.status_code == 200