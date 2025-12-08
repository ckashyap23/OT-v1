import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:fl_chart/fl_chart.dart';

class TrendViewScreen extends StatefulWidget {
  final int optionInstrumentId;
  final String tradingsymbol;
  final String apiBaseUrl;

  const TrendViewScreen({
    super.key,
    required this.optionInstrumentId,
    required this.tradingsymbol,
    required this.apiBaseUrl,
  });

  @override
  State<TrendViewScreen> createState() => _TrendViewScreenState();
}

class _TrendViewScreenState extends State<TrendViewScreen> {
  Map<String, dynamic>? _trendData;
  bool _isLoading = false;
  String? _errorMessage;
  int _selectedMetric = 0; // 0: Prices, 1: IV, 2: Greeks

  @override
  void initState() {
    super.initState();
    _fetchTrendData();
  }

  Future<void> _fetchTrendData() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final response = await http.get(
        Uri.parse('${widget.apiBaseUrl}/options/trend?option_instrument_id=${widget.optionInstrumentId}&days=30'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _trendData = data;
          _isLoading = false;
        });
      } else {
        final error = jsonDecode(response.body);
        setState(() {
          _errorMessage = error['error'] ?? 'Failed to fetch trend data';
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Error connecting to server: $e';
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Trend: ${widget.tradingsymbol}'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _errorMessage != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        _errorMessage!,
                        style: const TextStyle(color: Colors.red),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: _fetchTrendData,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : _trendData == null || (_trendData!['data_points'] as List).isEmpty
                  ? const Center(
                      child: Text('No trend data available'),
                    )
                  : _buildTrendView(),
    );
  }

  Widget _buildTrendView() {
    final dataPoints = List<Map<String, dynamic>>.from(_trendData!['data_points'] ?? []);
    if (dataPoints.isEmpty) {
      return const Center(child: Text('No data points available'));
    }

    return Column(
      children: [
        // Metric selector
        Container(
          padding: const EdgeInsets.all(16.0),
          child: SegmentedButton<int>(
            segments: const [
              ButtonSegment(value: 0, label: Text('Prices')),
              ButtonSegment(value: 1, label: Text('IV')),
              ButtonSegment(value: 2, label: Text('Greeks')),
            ],
            selected: {_selectedMetric},
            onSelectionChanged: (Set<int> newSelection) {
              setState(() {
                _selectedMetric = newSelection.first;
              });
            },
          ),
        ),
        // Chart
        Expanded(
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: _buildChart(dataPoints),
          ),
        ),
        // Legend
        Container(
          padding: const EdgeInsets.all(16.0),
          child: _buildLegend(),
        ),
      ],
    );
  }

  Widget _buildChart(List<Map<String, dynamic>> dataPoints) {
    switch (_selectedMetric) {
      case 0:
        return _buildPriceChart(dataPoints);
      case 1:
        return _buildIVChart(dataPoints);
      case 2:
        return _buildGreeksChart(dataPoints);
      default:
        return _buildPriceChart(dataPoints);
    }
  }

  Widget _buildPriceChart(List<Map<String, dynamic>> dataPoints) {
    // Filter out null values
    final underlyingPoints = <FlSpot>[];
    final optionPoints = <FlSpot>[];

    for (int i = 0; i < dataPoints.length; i++) {
      final point = dataPoints[i];
      final underlyingPrice = point['underlying_price'];
      final optionPrice = point['option_price'];

      if (underlyingPrice != null) {
        underlyingPoints.add(FlSpot(i.toDouble(), underlyingPrice.toDouble()));
      }
      if (optionPrice != null) {
        optionPoints.add(FlSpot(i.toDouble(), optionPrice.toDouble()));
      }
    }

    if (underlyingPoints.isEmpty && optionPoints.isEmpty) {
      return const Center(child: Text('No price data available'));
    }

    // Find min/max for scaling
    double minY = double.infinity;
    double maxY = double.negativeInfinity;

    for (var point in underlyingPoints) {
      if (point.y < minY) minY = point.y;
      if (point.y > maxY) maxY = point.y;
    }
    for (var point in optionPoints) {
      if (point.y < minY) minY = point.y;
      if (point.y > maxY) maxY = point.y;
    }

    final padding = (maxY - minY) * 0.1;
    minY = minY - padding;
    maxY = maxY + padding;

    return LineChart(
      LineChartData(
        gridData: FlGridData(show: true),
        titlesData: FlTitlesData(
          leftTitles: AxisTitles(
            sideTitles: SideTitles(showTitles: true, reservedSize: 50),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 30,
              getTitlesWidget: (value, meta) {
                if (value.toInt() >= 0 && value.toInt() < dataPoints.length) {
                  final date = dataPoints[value.toInt()]['date'] as String;
                  return Text(
                    date.substring(5), // Show MM-DD
                    style: const TextStyle(fontSize: 10),
                  );
                }
                return const Text('');
              },
            ),
          ),
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
        ),
        borderData: FlBorderData(show: true),
        minX: 0,
        maxX: (dataPoints.length - 1).toDouble(),
        minY: minY,
        maxY: maxY,
        lineBarsData: [
          // Underlying price line
          LineChartBarData(
            spots: underlyingPoints,
            isCurved: true,
            color: Colors.blue,
            barWidth: 2,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(show: false),
          ),
          // Option price line
          LineChartBarData(
            spots: optionPoints,
            isCurved: true,
            color: Colors.orange,
            barWidth: 2,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(show: false),
          ),
        ],
      ),
    );
  }

  Widget _buildIVChart(List<Map<String, dynamic>> dataPoints) {
    final ivPoints = <FlSpot>[];

    for (int i = 0; i < dataPoints.length; i++) {
      final point = dataPoints[i];
      final iv = point['implied_volatility'];
      if (iv != null) {
        ivPoints.add(FlSpot(i.toDouble(), iv.toDouble()));
      }
    }

    if (ivPoints.isEmpty) {
      return const Center(child: Text('No IV data available'));
    }

    double minY = ivPoints.map((p) => p.y).reduce((a, b) => a < b ? a : b);
    double maxY = ivPoints.map((p) => p.y).reduce((a, b) => a > b ? a : b);
    final padding = (maxY - minY) * 0.1;
    minY = minY - padding;
    maxY = maxY + padding;

    return LineChart(
      LineChartData(
        gridData: FlGridData(show: true),
        titlesData: FlTitlesData(
          leftTitles: AxisTitles(
            sideTitles: SideTitles(showTitles: true, reservedSize: 50),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 30,
              getTitlesWidget: (value, meta) {
                if (value.toInt() >= 0 && value.toInt() < dataPoints.length) {
                  final date = dataPoints[value.toInt()]['date'] as String;
                  return Text(
                    date.substring(5),
                    style: const TextStyle(fontSize: 10),
                  );
                }
                return const Text('');
              },
            ),
          ),
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
        borderData: FlBorderData(show: true),
        minX: 0,
        maxX: (dataPoints.length - 1).toDouble(),
        minY: minY,
        maxY: maxY,
        lineBarsData: [
          LineChartBarData(
            spots: ivPoints,
            isCurved: true,
            color: Colors.purple,
            barWidth: 2,
            dotData: const FlDotData(show: false),
            dashArray: [5, 5], // Dotted line
          ),
        ],
      ),
    );
  }

  Widget _buildGreeksChart(List<Map<String, dynamic>> dataPoints) {
    final deltaPoints = <FlSpot>[];
    final gammaPoints = <FlSpot>[];
    final thetaPoints = <FlSpot>[];
    final vegaPoints = <FlSpot>[];

    for (int i = 0; i < dataPoints.length; i++) {
      final point = dataPoints[i];
      if (point['delta'] != null) {
        deltaPoints.add(FlSpot(i.toDouble(), (point['delta'] as num).toDouble()));
      }
      if (point['gamma'] != null) {
        gammaPoints.add(FlSpot(i.toDouble(), (point['gamma'] as num).toDouble()));
      }
      if (point['theta'] != null) {
        thetaPoints.add(FlSpot(i.toDouble(), (point['theta'] as num).toDouble()));
      }
      if (point['vega'] != null) {
        vegaPoints.add(FlSpot(i.toDouble(), (point['vega'] as num).toDouble()));
      }
    }

    if (deltaPoints.isEmpty && gammaPoints.isEmpty && thetaPoints.isEmpty && vegaPoints.isEmpty) {
      return const Center(child: Text('No Greeks data available'));
    }

    // Find min/max across all Greeks
    double minY = double.infinity;
    double maxY = double.negativeInfinity;

    for (var points in [deltaPoints, gammaPoints, thetaPoints, vegaPoints]) {
      for (var point in points) {
        if (point.y < minY) minY = point.y;
        if (point.y > maxY) maxY = point.y;
      }
    }

    final padding = (maxY - minY) * 0.1;
    minY = minY - padding;
    maxY = maxY + padding;

    return LineChart(
      LineChartData(
        gridData: FlGridData(show: true),
        titlesData: FlTitlesData(
          leftTitles: AxisTitles(
            sideTitles: SideTitles(showTitles: true, reservedSize: 50),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 30,
              getTitlesWidget: (value, meta) {
                if (value.toInt() >= 0 && value.toInt() < dataPoints.length) {
                  final date = dataPoints[value.toInt()]['date'] as String;
                  return Text(
                    date.substring(5),
                    style: const TextStyle(fontSize: 10),
                  );
                }
                return const Text('');
              },
            ),
          ),
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
        borderData: FlBorderData(show: true),
        minX: 0,
        maxX: (dataPoints.length - 1).toDouble(),
        minY: minY,
        maxY: maxY,
        lineBarsData: [
          if (deltaPoints.isNotEmpty)
            LineChartBarData(
              spots: deltaPoints,
              isCurved: true,
              color: Colors.green,
              barWidth: 2,
              dotData: const FlDotData(show: false),
              dashArray: [5, 5],
            ),
          if (gammaPoints.isNotEmpty)
            LineChartBarData(
              spots: gammaPoints,
              isCurved: true,
              color: Colors.red,
              barWidth: 2,
              dotData: const FlDotData(show: false),
              dashArray: [5, 5],
            ),
          if (thetaPoints.isNotEmpty)
            LineChartBarData(
              spots: thetaPoints,
              isCurved: true,
              color: Colors.blue,
              barWidth: 2,
              dotData: const FlDotData(show: false),
              dashArray: [5, 5],
            ),
          if (vegaPoints.isNotEmpty)
            LineChartBarData(
              spots: vegaPoints,
              isCurved: true,
              color: Colors.orange,
              barWidth: 2,
              dotData: const FlDotData(show: false),
              dashArray: [5, 5],
            ),
        ],
      ),
    );
  }

  Widget _buildLegend() {
    switch (_selectedMetric) {
      case 0:
        return Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            _buildLegendItem('Underlying Price', Colors.blue),
            const SizedBox(width: 16),
            _buildLegendItem('Option Price', Colors.orange),
          ],
        );
      case 1:
        return _buildLegendItem('Implied Volatility', Colors.purple);
      case 2:
        return Wrap(
          alignment: WrapAlignment.center,
          spacing: 16,
          runSpacing: 8,
          children: [
            _buildLegendItem('Delta', Colors.green),
            _buildLegendItem('Gamma', Colors.red),
            _buildLegendItem('Theta', Colors.blue),
            _buildLegendItem('Vega', Colors.orange),
          ],
        );
      default:
        return const SizedBox.shrink();
    }
  }

  Widget _buildLegendItem(String label, Color color) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 16,
          height: 16,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 8),
        Text(
          label,
          style: const TextStyle(fontSize: 12),
        ),
      ],
    );
  }
}

