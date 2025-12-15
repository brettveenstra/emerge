"""
Unit tests for export functionality, including namespace inventory.
"""

# Authors: Grzegorz Lato <grzegorz.lato@gmail.com>
# License: MIT

import unittest
import tempfile
import os
import csv
from typing import Dict
import logging
import coloredlogs

from emerge.analysis import Analysis
from emerge.analyzer import Analyzer
from emerge.languages.csharpparser import CSharpParser
from emerge.metrics.cyclomaticcomplexity.cyclomaticcomplexity import CyclomaticComplexityMetric
from emerge.metrics.sloc.sloc import SourceLinesOfCodeMetric
from emerge.metrics.numberofmethods.numberofmethods import NumberOfMethodsMetric
from emerge.export import TSVExporter

LOGGER = logging.getLogger('TESTS')
coloredlogs.install(level='INFO', logger=LOGGER, fmt='\n%(asctime)s %(name)s %(levelname)s %(message)s')


# Test data with multiple entity types and namespaces
CSHARP_CORE_FILE = """
using System;

namespace MyApp.Core
{
    public class MyService
    {
        public void SimpleMethod()
        {
            Console.WriteLine("Hello");
        }

        public int ComplexMethod(int x, int y)
        {
            if (x > 0 && y > 0)
            {
                return x + y;
            }
            return 0;
        }
    }

    public interface IMyService
    {
        void DoSomething();
    }

    public struct Point
    {
        public int X { get; set; }
        public int Y { get; set; }
    }

    public enum Status
    {
        Active,
        Inactive,
        Pending
    }

    public record PersonRecord(string Name, int Age);
}
"""

CSHARP_DATA_FILE = """
namespace MyApp.Core.Data
{
    public class Repository
    {
        public void Save() { }
    }
}
"""

CSHARP_UI_FILE = """
namespace MyApp.UI
{
    public class MainWindow
    {
        public void Show() { }
    }
}
"""


class ExportTestCase(unittest.TestCase):

    def setUp(self):
        self.analysis = Analysis()
        self.analysis.analysis_name = "test"
        self.analysis.source_directory = "/source"
        self.parsers = {
            CSharpParser.parser_name(): CSharpParser()
        }
        self.analyzer = Analyzer(None, self.parsers)

    def tearDown(self):
        pass

    def test_namespace_inventory_entity_types(self):
        """Test that namespace inventory correctly detects and counts different entity types"""

        # Parse test files
        parser = self.parsers[CSharpParser.parser_name()]

        # Parse Core file
        parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="Core.cs",
            full_file_path="/source/Core.cs",
            file_content=CSHARP_CORE_FILE
        )

        # Parse Data file
        parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="Data.cs",
            full_file_path="/source/Data.cs",
            file_content=CSHARP_DATA_FILE
        )

        # Parse UI file
        parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="UI.cs",
            full_file_path="/source/UI.cs",
            file_content=CSHARP_UI_FILE
        )

        self.assertTrue(bool(parser.results))
        self.analysis.collect_results_from_parser(parser)

        # Generate entity results
        parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(parser)

        # Add metrics
        sloc_metric = SourceLinesOfCodeMetric(self.analysis)
        methods_metric = NumberOfMethodsMetric(self.analysis)
        complexity_metric = CyclomaticComplexityMetric(self.analysis)

        self.analysis.metrics_for_entity_results.update({
            sloc_metric.metric_name: sloc_metric,
            methods_metric.metric_name: methods_metric,
            complexity_metric.metric_name: complexity_metric
        })

        # Calculate metrics
        self.analyzer._calculate_code_metric_results(self.analysis)

        # Export namespace inventory to temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            TSVExporter.export_namespace_inventory_as_tsv(
                self.analysis,
                self.analysis.local_metric_results,
                tmpdir
            )

            # Read and validate the TSV file
            tsv_path = os.path.join(tmpdir, 'emerge-namespaces.tsv')
            self.assertTrue(os.path.exists(tsv_path), "Namespace TSV file should be created")

            with open(tsv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='\t')
                rows = list(reader)

                # Should have hierarchical namespaces
                self.assertGreater(len(rows), 0, "Should have namespace entries")

                # Debug: print all namespaces
                LOGGER.info(f"Exported namespaces: {[r['Namespace'] for r in rows]}")

                # Find MyApp.Core namespace
                core_ns = next((r for r in rows if r['Namespace'] == 'MyApp.Core'), None)
                self.assertIsNotNone(core_ns, f"MyApp.Core namespace should exist. Found: {[r['Namespace'] for r in rows]}")

                # Verify entity type breakdown
                # NOTE: Hierarchical aggregation - MyApp.Core INCLUDES MyApp.Core.Data
                # So MyApp.Core has: (Core.cs: 1 class, 1 interface, 1 struct, 1 enum) + (Data.cs: 1 class)
                # Total: 5 entities, 2 classes (hierarchical)
                LOGGER.info(f"MyApp.Core entities (hierarchical): {core_ns}")

                self.assertEqual(int(core_ns['Entities']), 5, "MyApp.Core should have 5 entities (hierarchical)")
                self.assertGreaterEqual(int(core_ns['Classes']), 1, "MyApp.Core should have at least 1 class")
                self.assertGreaterEqual(int(core_ns['Interfaces']), 1, "MyApp.Core should have at least 1 interface")
                self.assertGreaterEqual(int(core_ns['Structs']), 1, "MyApp.Core should have at least 1 struct")
                self.assertGreaterEqual(int(core_ns['Enums']), 1, "MyApp.Core should have at least 1 enum")

                LOGGER.info(f"✅ Entity type detection validated: Classes={core_ns['Classes']}, Interfaces={core_ns['Interfaces']}, Structs={core_ns['Structs']}, Enums={core_ns['Enums']}")

    def test_namespace_inventory_hierarchical_aggregation(self):
        """Test that parent namespaces correctly aggregate child namespace metrics"""

        # Parse test files
        parser = self.parsers[CSharpParser.parser_name()]
        for filename, content in [("Core.cs", CSHARP_CORE_FILE), ("Data.cs", CSHARP_DATA_FILE), ("UI.cs", CSHARP_UI_FILE)]:
            parser.generate_file_result_from_analysis(self.analysis, file_name=filename, full_file_path=f"/source/{filename}", file_content=content)

        self.analysis.collect_results_from_parser(parser)
        parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(parser)

        # Add metrics
        sloc_metric = SourceLinesOfCodeMetric(self.analysis)
        self.analysis.metrics_for_entity_results.update({
            sloc_metric.metric_name: sloc_metric
        })
        self.analyzer._calculate_code_metric_results(self.analysis)

        # Export namespace inventory
        with tempfile.TemporaryDirectory() as tmpdir:
            TSVExporter.export_namespace_inventory_as_tsv(
                self.analysis,
                self.analysis.local_metric_results,
                tmpdir
            )

            tsv_path = os.path.join(tmpdir, 'emerge-namespaces.tsv')

            with open(tsv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='\t')
                rows = list(reader)
                namespaces = {r['Namespace']: r for r in rows}

                # Verify hierarchical structure exists
                self.assertIn('MyApp', namespaces, "Root MyApp namespace should exist")
                self.assertIn('MyApp.Core', namespaces, "MyApp.Core should exist")
                self.assertIn('MyApp.Core.Data', namespaces, "MyApp.Core.Data should exist")
                self.assertIn('MyApp.UI', namespaces, "MyApp.UI should exist")

                # Verify hierarchical aggregation
                root_entities = int(namespaces['MyApp']['Entities'])
                core_entities = int(namespaces['MyApp.Core']['Entities'])
                data_entities = int(namespaces['MyApp.Core.Data']['Entities'])
                ui_entities = int(namespaces['MyApp.UI']['Entities'])

                # Root should be greatest (includes everything)
                self.assertGreaterEqual(root_entities, core_entities, "MyApp root should have >= MyApp.Core entities")
                self.assertGreaterEqual(root_entities, ui_entities, "MyApp root should have >= MyApp.UI entities")

                # MyApp.Core should include MyApp.Core.Data
                self.assertGreaterEqual(core_entities, data_entities,
                                       "MyApp.Core should include MyApp.Core.Data entities")

                LOGGER.info(f"✅ Hierarchical aggregation validated:")
                LOGGER.info(f"  MyApp (root): {root_entities} entities (aggregates all)")
                LOGGER.info(f"  MyApp.Core: {core_entities} entities (includes Data)")
                LOGGER.info(f"  MyApp.Core.Data: {data_entities} entities")
                LOGGER.info(f"  MyApp.UI: {ui_entities} entities")

    def test_namespace_inventory_complexity_metrics(self):
        """Test that namespace inventory includes complexity metrics"""

        # Parse test files
        parser = self.parsers[CSharpParser.parser_name()]
        parser.generate_file_result_from_analysis(self.analysis, file_name="Core.cs", full_file_path="/source/Core.cs", file_content=CSHARP_CORE_FILE)

        self.analysis.collect_results_from_parser(parser)
        parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(parser)

        # Add complexity metrics
        complexity_metric = CyclomaticComplexityMetric(self.analysis)
        self.analysis.metrics_for_entity_results.update({
            complexity_metric.metric_name: complexity_metric
        })
        self.analyzer._calculate_code_metric_results(self.analysis)

        # Export namespace inventory
        with tempfile.TemporaryDirectory() as tmpdir:
            TSVExporter.export_namespace_inventory_as_tsv(
                self.analysis,
                self.analysis.local_metric_results,
                tmpdir
            )

            tsv_path = os.path.join(tmpdir, 'emerge-namespaces.tsv')

            with open(tsv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='\t')
                rows = list(reader)

                # Verify complexity columns exist
                self.assertIn('AvgComplexity', rows[0].keys(), "Should have AvgComplexity column")
                self.assertIn('MaxComplexity', rows[0].keys(), "Should have MaxComplexity column")

                # Find MyApp.Core namespace and verify complexity
                core_ns = next((r for r in rows if r['Namespace'] == 'MyApp.Core'), None)
                self.assertIsNotNone(core_ns)

                avg_complexity = float(core_ns['AvgComplexity'])
                max_complexity = int(core_ns['MaxComplexity'])

                # MyService has ComplexMethod with complexity > 1
                self.assertGreater(avg_complexity, 0, "Should have average complexity > 0")
                self.assertGreater(max_complexity, 1, "Should have max complexity > 1 (ComplexMethod)")

                LOGGER.info(f"✅ Complexity metrics validated:")
                LOGGER.info(f"  AvgComplexity: {avg_complexity}")
                LOGGER.info(f"  MaxComplexity: {max_complexity}")

    def test_namespace_inventory_tsv_format(self):
        """Test that namespace inventory produces valid TSV format"""

        # Parse test files
        parser = self.parsers[CSharpParser.parser_name()]
        parser.generate_file_result_from_analysis(self.analysis, file_name="Core.cs", full_file_path="/source/Core.cs", file_content=CSHARP_CORE_FILE)

        self.analysis.collect_results_from_parser(parser)
        parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(parser)

        # Export namespace inventory
        with tempfile.TemporaryDirectory() as tmpdir:
            TSVExporter.export_namespace_inventory_as_tsv(
                self.analysis,
                self.analysis.local_metric_results,
                tmpdir
            )

            tsv_path = os.path.join(tmpdir, 'emerge-namespaces.tsv')

            with open(tsv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='\t')
                rows = list(reader)

                # Verify all expected columns exist
                expected_columns = [
                    'Namespace', 'Files', 'Entities', 'Classes', 'Interfaces',
                    'Structs', 'Enums', 'Records', 'SLOC', 'Methods',
                    'AvgComplexity', 'MaxComplexity'
                ]

                for col in expected_columns:
                    self.assertIn(col, rows[0].keys(), f"Column '{col}' should exist")

                # Verify data types are correct
                for row in rows:
                    self.assertIsInstance(row['Namespace'], str, "Namespace should be string")
                    # Numeric columns should be parseable as numbers
                    int(row['Files'])
                    int(row['Entities'])
                    int(row['Classes'])
                    int(row['Interfaces'])
                    int(row['Structs'])
                    int(row['Enums'])
                    int(row['Records'])
                    int(row['SLOC'])
                    int(row['Methods'])
                    float(row['AvgComplexity'])
                    int(row['MaxComplexity'])

                LOGGER.info(f"✅ TSV format validated with {len(expected_columns)} columns")
                LOGGER.info(f"✅ {len(rows)} namespace rows exported")
