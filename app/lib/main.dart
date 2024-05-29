import 'package:flutter/material.dart';
import 'package:syncfusion_flutter_charts/charts.dart';
import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Real-Time Data Visualization',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(primarySwatch: Colors.blue),
      home: DefaultTabController(
        length: 5,
        child: Scaffold(
          appBar: AppBar(
            title: Text('Dashboard de Monitoreo de Planta con IoT'),
          ),
          body: TabBarView(
            children: [
              DataAndPredictionPage(title: 'Humedad Ambiental', query: "SELECT time_index, humedad FROM ethumedad WHERE entity_id = 'sensorHumedad' ORDER BY time_index ASC;"),
              MyHomePage(title: 'Humedad de la Planta', query: "SELECT time_index, humedad FROM ethumedad WHERE entity_id = 'sensorHumedadPlanta' ORDER BY time_index ASC;"),
              DataAndPredictionPage(title: 'Temperatura', query: "SELECT time_index, temperatura FROM ettemperatura ORDER BY time_index ASC;"),
              MyHomePage(title: 'Luz', query: "SELECT time_index, luz FROM etluz ORDER BY time_index ASC;"),
              MyHomePage(title: 'Proximidad', query: "SELECT time_index, proximidad FROM etproximidad ORDER BY time_index ASC;"),
            ],
          ),
          bottomNavigationBar: TabBar(
            tabs: [
              Tab(icon: Icon(Icons.ac_unit), text: 'Humedad Ambiental'),
              Tab(icon: Icon(Icons.nature), text: 'Humedad de la Planta'),
              Tab(icon: Icon(Icons.thermostat), text: 'Temperatura'),
              Tab(icon: Icon(Icons.light_mode), text: 'Luz'),
              Tab(icon: Icon(Icons.sensor_door), text: 'Proximidad'),
            ],
          ),
        ),
      ),
    );
  }
}

class DataAndPredictionPage extends StatefulWidget {
  final String title;
  final String query;

  DataAndPredictionPage({Key? key, required this.title, required this.query}) : super(key: key);

  @override
  _DataAndPredictionPageState createState() => _DataAndPredictionPageState(query: query);
}

class _DataAndPredictionPageState extends State<DataAndPredictionPage> {
  late List<LiveData> chartData;
  late List<LiveData> trainData;
  late List<LiveData> testData;
  late List<LiveData> predictionData;
  late Timer timer;
  final String query;

  _DataAndPredictionPageState({required this.query});

  @override
  void initState() {
    super.initState();
    chartData = [];
    trainData = [];
    testData = [];
    predictionData = [];
    fetchData();
    fetchPredictions();
    timer = Timer.periodic(const Duration(seconds: 5), (Timer t) => fetchData());
  }

  @override
  void dispose() {
    timer.cancel();
    super.dispose();
  }

  Future<void> fetchData() async {
    final response = await http.post(
      Uri.parse('http://54.227.149.158:4200/_sql'),
      headers: <String, String>{
        'Content-Type': 'application/json',
      },
      body: jsonEncode({"stmt": query}),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      List<dynamic> rows = data['rows'];
      List<LiveData> newData = [];
      for (var row in rows) {
        DateTime time = DateTime.fromMillisecondsSinceEpoch(row[0]);
        double variable = row[1] as double;
        newData.add(LiveData(time, variable));
      }
      setState(() {
        chartData = newData;
      });
    } else {
      throw Exception('Failed to load data');
    }
  }

  Future<void> fetchPredictions() async {
    String endpoint = widget.title == 'Temperatura' ? 'predecirtemperatura' : 'predecirhumedad';
    final response = await http.get(
      Uri.parse('http://54.227.149.158/$endpoint'),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      setState(() {
        trainData = _parseLiveData(data['data_train']);
        testData = _parseLiveData(data['data_test']);
        predictionData = _parseLiveData(data['predictions']);
      });
    } else {
      throw Exception('Failed to load predictions');
    }
  }

  List<LiveData> _parseLiveData(Map<String, dynamic> data) {
    List<LiveData> result = [];
    for (int i = 0; i < data['x'].length; i++) {
      DateTime time = DateTime.fromMillisecondsSinceEpoch(data['x'][i] * 1000);
      double value = double.parse(data['y'][i].toString());
      result.add(LiveData(time, value));
    }
    return result;
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        Expanded(
          flex: 1,
          child: SfCartesianChart(
            series: <LineSeries<LiveData, DateTime>>[
              LineSeries<LiveData, DateTime>(
                dataSource: chartData,
                color: Colors.blue,
                xValueMapper: (LiveData data, _) => data.time,
                yValueMapper: (LiveData data, _) => data.variable,
              ),
            ],
            primaryXAxis: DateTimeAxis(),
            primaryYAxis: NumericAxis(),
          ),
        ),
        Expanded(
          flex: 1,
          child: SfCartesianChart(
            series: <LineSeries<LiveData, DateTime>>[
              LineSeries<LiveData, DateTime>(
                dataSource: trainData,
                name: 'Train Data',
                color: Colors.green,
                xValueMapper: (LiveData data, _) => data.time,
                yValueMapper: (LiveData data, _) => data.variable,
              ),
              LineSeries<LiveData, DateTime>(
                dataSource: testData,
                name: 'Test Data',
                color: Colors.orange,
                xValueMapper: (LiveData data, _) => data.time,
                yValueMapper: (LiveData data, _) => data.variable,
              ),
              LineSeries<LiveData, DateTime>(
                dataSource: predictionData,
                name: 'Predictions',
                color: Colors.red,
                xValueMapper: (LiveData data, _) => data.time,
                yValueMapper: (LiveData data, _) => data.variable,
              ),
            ],
            primaryXAxis: DateTimeAxis(),
            primaryYAxis: NumericAxis(),
          ),
        ),
      ],
    );
  }
}

class MyHomePage extends StatefulWidget {
  final String title;
  final String query;

  MyHomePage({Key? key, required this.title, required this.query}) : super(key: key);

  @override
  _MyHomePageState createState() => _MyHomePageState(query: query);
}

class _MyHomePageState extends State<MyHomePage> {
  late List<LiveData> chartData;
  late Timer timer;
  final String query;

  _MyHomePageState({required this.query});

  @override
  void initState() {
    super.initState();
    chartData = [];
    fetchData();
    timer = Timer.periodic(const Duration(seconds: 5), (Timer t) => fetchData());
  }

  @override
  void dispose() {
    timer.cancel;
    super.dispose();
  }

  Future<void> fetchData() async {
    final response = await http.post(
      Uri.parse('http://54.227.149.158:4200/_sql'),
      headers: <String, String>{
        'Content-Type': 'application/json',
      },
      body: jsonEncode({"stmt": query}),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      List<dynamic> rows = data['rows'];
      List<LiveData> newData = [];
      for (var row in rows) {
        DateTime time = DateTime.fromMillisecondsSinceEpoch(row[0]);
        double variable = row[1] as double;
        newData.add(LiveData(time, variable));
      }
      setState(() {
        chartData = newData;
      });
    } else {
      throw Exception('Failed to load data');
    }
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
        child: Scaffold(
            body: SfCartesianChart(
                series: <LineSeries<LiveData, DateTime>>[
                  LineSeries<LiveData, DateTime>(
                    dataSource: chartData,
                    color: Colors.blue,
                    xValueMapper: (LiveData data, _) => data.time,
                    yValueMapper: (LiveData data, _) => data.variable,
                  ),
                ],
                primaryXAxis: DateTimeAxis(
                  edgeLabelPlacement: EdgeLabelPlacement.shift,
                  majorGridLines: const MajorGridLines(width: 0),
                ),
                primaryYAxis: NumericAxis(
                  axisLine: const AxisLine(width: 0),
                  majorTickLines: const MajorTickLines(size: 0),
                )
            )
        )
    );
  }
}

class LiveData {
  final DateTime time;
  final double variable;

  LiveData(this.time, this.variable);
}