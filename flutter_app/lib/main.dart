import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Options Trading',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        useMaterial3: true,
      ),
      home: const StockSearchScreen(),
    );
  }
}

class StockSearchScreen extends StatefulWidget {
  const StockSearchScreen({super.key});

  @override
  State<StockSearchScreen> createState() => _StockSearchScreenState();
}

class _StockSearchScreenState extends State<StockSearchScreen> {
  final TextEditingController _stockNameController = TextEditingController();
  final String _apiBaseUrl = 'https://ot-v1-backend-a5dcdfh0duadgpce.centralindia-01.azurewebsites.net/api';
  List<Map<String, dynamic>> _matches = [];
  bool _isLoading = false;
  bool _isProcessing = false;
  String? _errorMessage;
  String? _successMessage;

  Future<void> _searchStocks() async {
    final query = _stockNameController.text.trim();
    if (query.isEmpty) {
      setState(() {
        _errorMessage = 'Please enter a stock name';
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _matches = [];
      _successMessage = null;
    });

    try {
      final response = await http.post(
        Uri.parse('$_apiBaseUrl/stocks/search'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'query': query}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _matches = List<Map<String, dynamic>>.from(data['matches']);
          _isLoading = false;
        });
      } else {
        final error = jsonDecode(response.body);
        setState(() {
          _errorMessage = error['error'] ?? 'Failed to search stocks';
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

  Future<void> _processOptions(String tradingsymbol) async {
    setState(() {
      _isProcessing = true;
      _errorMessage = null;
      _successMessage = null;
    });

    try {
      final response = await http.post(
        Uri.parse('$_apiBaseUrl/options/process'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'tradingsymbol': tradingsymbol}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _successMessage = data['message'] ?? 'Successfully processed options';
          _isProcessing = false;
          _matches = [];
          _stockNameController.clear();
        });
      } else {
        final error = jsonDecode(response.body);
        setState(() {
          _errorMessage = error['error'] ?? 'Failed to process options';
          _isProcessing = false;
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Error connecting to server: $e';
        _isProcessing = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Options Trading'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: _stockNameController,
              decoration: const InputDecoration(
                labelText: 'Enter stock name (e.g., Reliance, TCS)',
                border: OutlineInputBorder(),
              ),
              onSubmitted: (_) => _searchStocks(),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _isLoading ? null : _searchStocks,
              child: _isLoading
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Search'),
            ),
            if (_errorMessage != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.red.shade100,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  _errorMessage!,
                  style: const TextStyle(color: Colors.red),
                ),
              ),
            ],
            if (_successMessage != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.green.shade100,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  _successMessage!,
                  style: const TextStyle(color: Colors.green),
                ),
              ),
            ],
            if (_matches.isNotEmpty) ...[
              const SizedBox(height: 24),
              const Text(
                'Select a stock:',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Expanded(
                child: ListView.builder(
                  itemCount: _matches.length,
                  itemBuilder: (context, index) {
                    final match = _matches[index];
                    return Card(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: ListTile(
                        title: Text(match['tradingsymbol'] ?? ''),
                        subtitle: Text('${match['name'] ?? ''} (${match['exchange'] ?? ''})'),
                        trailing: _isProcessing
                            ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.arrow_forward),
                        onTap: _isProcessing
                            ? null
                            : () => _processOptions(match['tradingsymbol']),
                      ),
                    );
                  },
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    _stockNameController.dispose();
    super.dispose();
  }
}

