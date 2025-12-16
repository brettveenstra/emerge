"""
Unit tests for multi-target scanning functionality.
"""

# Authors: Grzegorz Lato <grzegorz.lato@gmail.com>
# License: MIT

import unittest
import tempfile
import os
import csv
from pathlib import Path
import logging
import coloredlogs

from emerge.analysis import Analysis
from emerge.analyzer import Analyzer
from emerge.languages.csharpparser import CSharpParser
from emerge.metrics.sloc.sloc import SourceLinesOfCodeMetric
from emerge.metrics.numberofmethods.numberofmethods import NumberOfMethodsMetric
from emerge.graph import GraphRepresentation, GraphType, FileSystemNode, FileSystemNodeType
from emerge.export import TSVExporter

LOGGER = logging.getLogger('TESTS')
coloredlogs.install(level='INFO', logger=LOGGER, fmt='\n%(asctime)s %(name)s %(levelname)s %(message)s')


# Test data for ServiceA
CSHARP_SERVICE_A_FILE = """
namespace ServiceA.Core
{
    public class ServiceAController
    {
        public void ProcessA()
        {
            System.Console.WriteLine("Service A");
        }
    }
}
"""

# Test data for ServiceB
CSHARP_SERVICE_B_FILE = """
namespace ServiceB.Core
{
    public class ServiceBController
    {
        public void ProcessB()
        {
            System.Console.WriteLine("Service B");
        }
    }
}
"""


class MultiTargetScanningTestCase(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

        # Create test directory structure
        self.service_a_dir = os.path.join(self.temp_dir, "ServiceA")
        self.service_b_dir = os.path.join(self.temp_dir, "ServiceB")

        os.makedirs(self.service_a_dir, exist_ok=True)
        os.makedirs(self.service_b_dir, exist_ok=True)

        # Create test files
        self.service_a_file = os.path.join(self.service_a_dir, "ServiceAController.cs")
        with open(self.service_a_file, 'w') as f:
            f.write(CSHARP_SERVICE_A_FILE)

        self.service_b_file = os.path.join(self.service_b_dir, "ServiceBController.cs")
        with open(self.service_b_file, 'w') as f:
            f.write(CSHARP_SERVICE_B_FILE)

        self.analysis = Analysis()
        self.analysis.analysis_name = "multi-target-test"
        self.analysis.source_directories = [self.service_a_dir, self.service_b_dir]
        self.analysis.source_directory = self.service_a_dir
        self.analysis.only_permit_languages = ['csharp']
        self.analysis.only_permit_file_extensions = ['.cs']

        self.parsers = {
            CSharpParser.parser_name(): CSharpParser()
        }
        self.analyzer = Analyzer(None, self.parsers)

    def tearDown(self):
        # Clean up temp files
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_filesystem_node_source_directory_label(self):
        """Test that FileSystemNode stores source_directory_label correctly"""

        node_a = FileSystemNode(
            FileSystemNodeType.FILE,
            "ServiceA/ServiceAController.cs",
            content="test",
            source_directory_label="ServiceA"
        )

        node_b = FileSystemNode(
            FileSystemNodeType.FILE,
            "ServiceB/ServiceBController.cs",
            content="test",
            source_directory_label="ServiceB"
        )

        self.assertEqual(node_a.source_directory_label, "ServiceA")
        self.assertEqual(node_b.source_directory_label, "ServiceB")
        LOGGER.info('completed testing of FileSystemNode source_directory_label')

    def test_multi_directory_filesystem_graph(self):
        """Test that filesystem graph tracks source directories correctly"""

        # Create filesystem graph
        self.analysis.create_graph_representation(GraphType.FILESYSTEM_GRAPH)
        self.analysis.create_filesystem_graph()

        filesystem_graph = self.analysis.graph_representations[GraphType.FILESYSTEM_GRAPH.name.lower()]

        # Verify that filesystem nodes have source_directory_label
        self.assertTrue(len(filesystem_graph.filesystem_nodes) > 0)

        # Find nodes from each service
        service_a_nodes = [
            node for node in filesystem_graph.filesystem_nodes.values()
            if node.source_directory_label == "ServiceA"
        ]
        service_b_nodes = [
            node for node in filesystem_graph.filesystem_nodes.values()
            if node.source_directory_label == "ServiceB"
        ]

        self.assertTrue(len(service_a_nodes) > 0, "Should have nodes from ServiceA")
        self.assertTrue(len(service_b_nodes) > 0, "Should have nodes from ServiceB")

        LOGGER.info(f'Found {len(service_a_nodes)} nodes from ServiceA')
        LOGGER.info(f'Found {len(service_b_nodes)} nodes from ServiceB')
        LOGGER.info('completed testing of multi-directory filesystem graph')

    def test_graph_node_source_directory_attribute(self):
        """Test that graph nodes include source_directory attribute"""

        # Create filesystem graph
        self.analysis.create_graph_representation(GraphType.FILESYSTEM_GRAPH)
        self.analysis.create_filesystem_graph()

        filesystem_graph = self.analysis.graph_representations[GraphType.FILESYSTEM_GRAPH.name.lower()]

        # Check that graph nodes have source_directory attribute
        file_nodes = [
            node_id for node_id in filesystem_graph.digraph.nodes
            if filesystem_graph.digraph.nodes[node_id].get('file', False)
        ]

        self.assertTrue(len(file_nodes) > 0, "Should have file nodes in graph")

        for node_id in file_nodes:
            node_attrs = filesystem_graph.digraph.nodes[node_id]
            self.assertIn('source_directory', node_attrs,
                         f"Node {node_id} should have source_directory attribute")
            self.assertIsNotNone(node_attrs['source_directory'],
                               f"Node {node_id} source_directory should not be None")

        LOGGER.info('completed testing of graph node source_directory attribute')

    def test_entity_results_source_directory_tracking(self):
        """Test that entity results can be traced back to their source directory"""

        # Parse files and generate results
        parser = self.parsers[CSharpParser.parser_name()]

        # Parse ServiceA file
        parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="ServiceAController.cs",
            full_file_path=self.service_a_file,
            file_content=CSHARP_SERVICE_A_FILE
        )

        # Parse ServiceB file
        parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="ServiceBController.cs",
            full_file_path=self.service_b_file,
            file_content=CSHARP_SERVICE_B_FILE
        )

        self.analysis.collect_results_from_parser(parser)

        # Generate entity results
        parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(parser)

        # Create filesystem graph for source directory lookup
        self.analysis.create_graph_representation(GraphType.FILESYSTEM_GRAPH)
        self.analysis.create_filesystem_graph()

        # Create entity dependency graph
        self.analysis.create_graph_representation(GraphType.ENTITY_RESULT_DEPENDENCY_GRAPH)
        self.analysis.calculate_graph_representations()

        # Verify entities exist
        entity_results = {k: v for k, v in self.analysis.results.items()
                         if hasattr(v, 'entity_name')}

        self.assertTrue(len(entity_results) >= 2, "Should have at least 2 entities")

        LOGGER.info(f'Found {len(entity_results)} entities across multiple directories')
        LOGGER.info('completed testing of entity source directory tracking')

    def test_export_tsv_source_directory_column(self):
        """Test that TSV export includes SourceDirectory column with correct values"""

        # Parse files
        parser = self.parsers[CSharpParser.parser_name()]

        parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="ServiceAController.cs",
            full_file_path=self.service_a_file,
            file_content=CSHARP_SERVICE_A_FILE
        )

        parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="ServiceBController.cs",
            full_file_path=self.service_b_file,
            file_content=CSHARP_SERVICE_B_FILE
        )

        self.analysis.collect_results_from_parser(parser)
        parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(parser)

        # Add metrics
        sloc_metric = SourceLinesOfCodeMetric(self.analysis)
        methods_metric = NumberOfMethodsMetric(self.analysis)

        self.analysis.metrics_for_entity_results.update({
            sloc_metric.metric_name: sloc_metric,
            methods_metric.metric_name: methods_metric
        })

        # Calculate metrics
        self.analyzer._calculate_code_metric_results(self.analysis)

        # Create filesystem graph
        self.analysis.create_graph_representation(GraphType.FILESYSTEM_GRAPH)
        self.analysis.create_filesystem_graph()

        # Export to TSV
        export_dir = tempfile.mkdtemp()
        self.analysis.export_directory = export_dir

        try:
            TSVExporter.export_entity_metrics_as_tsv(
                self.analysis,
                self.analysis.local_metric_results,
                self.analysis.analysis_name,
                export_dir
            )

            # Read TSV and verify SourceDirectory column
            tsv_file = os.path.join(export_dir, "emerge-entity-metrics.tsv")
            self.assertTrue(os.path.exists(tsv_file), "TSV file should exist")

            with open(tsv_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='\t')
                rows = list(reader)

                # Verify header includes SourceDirectory
                self.assertIn('SourceDirectory', reader.fieldnames,
                            "TSV should have SourceDirectory column")

                # Verify each row has a SourceDirectory value
                for row in rows:
                    entity_name = row['Entity']
                    source_dir = row['SourceDirectory']

                    # Should have a source directory
                    self.assertIsNotNone(source_dir,
                                       f"Entity {entity_name} should have SourceDirectory")

                    # ServiceA entities should be in ServiceA
                    if 'ServiceA' in entity_name:
                        self.assertEqual(source_dir, 'ServiceA',
                                       f"Entity {entity_name} should be in ServiceA directory")

                    # ServiceB entities should be in ServiceB
                    if 'ServiceB' in entity_name:
                        self.assertEqual(source_dir, 'ServiceB',
                                       f"Entity {entity_name} should be in ServiceB directory")

                LOGGER.info(f'Verified SourceDirectory column for {len(rows)} entities')
                LOGGER.info('completed testing of TSV export SourceDirectory column')

        finally:
            import shutil
            if os.path.exists(export_dir):
                shutil.rmtree(export_dir)


if __name__ == '__main__':
    unittest.main()
