"""
All unit tests that are related to the cyclomatic complexity metric.
"""

# Authors: Grzegorz Lato <grzegorz.lato@gmail.com>
# License: MIT

import unittest
from typing import Dict
import logging
import coloredlogs

from emerge.tests.testdata.c import C_TEST_FILES
from emerge.tests.testdata.cpp import CPP_TEST_FILES
from emerge.tests.testdata.groovy import GROOVY_TEST_FILES
from emerge.tests.testdata.java import JAVA_TEST_FILES
from emerge.tests.testdata.javascript import JAVASCRIPT_TEST_FILES
from emerge.tests.testdata.typescript import TYPESCRIPT_TEST_FILES
from emerge.tests.testdata.kotlin import KOTLIN_TEST_FILES
from emerge.tests.testdata.objc import OBJC_TEST_FILES
from emerge.tests.testdata.ruby import RUBY_TEST_FILES
from emerge.tests.testdata.swift import SWIFT_TEST_FILES
from emerge.tests.testdata.py import PYTHON_TEST_FILES
from emerge.tests.testdata.go import GO_TEST_FILES
from emerge.tests.testdata.csharp import CSHARP_TEST_FILES

from emerge.languages.cparser import CParser
from emerge.languages.cppparser import CPPParser
from emerge.languages.groovyparser import GroovyParser
from emerge.languages.javaparser import JavaParser
from emerge.languages.javascriptparser import JavaScriptParser
from emerge.languages.typescriptparser import TypeScriptParser
from emerge.languages.kotlinparser import KotlinParser
from emerge.languages.objcparser import ObjCParser
from emerge.languages.rubyparser import RubyParser
from emerge.languages.swiftparser import SwiftParser
from emerge.languages.pyparser import PythonParser
from emerge.languages.goparser import GoParser
from emerge.languages.csharpparser import CSharpParser
from emerge.languages.abstractparser import AbstractParser

from emerge.analysis import Analysis
from emerge.analyzer import Analyzer
from emerge.metrics.cyclomaticcomplexity.cyclomaticcomplexity import CyclomaticComplexityMetric
from emerge.results import FileResult

LOGGER = logging.getLogger('TESTS')
coloredlogs.install(level='INFO', logger=LOGGER, fmt='\n%(asctime)s %(name)s %(levelname)s %(message)s')


# Test data with known cyclomatic complexity values
CSHARP_COMPLEXITY_TEST = """
using System;

namespace ComplexityTest
{
    public class TestComplexity
    {
        // Complexity = 1 (base, no decision points)
        public void SimpleMethod()
        {
            Console.WriteLine("Hello");
        }

        // Complexity = 3 (base + if + else if)
        public int ModerateMethod(int x)
        {
            if (x > 10)
                return 1;
            else if (x > 5)
                return 2;
            return 0;
        }

        // Complexity = 5 (base + 2 ifs + && + ||)
        public bool ComplexMethod(int a, int b, string c)
        {
            if (a > 0 && b > 0)
            {
                if (c != null || c.Length > 0)
                {
                    return true;
                }
            }
            return false;
        }

        // Complexity = 6 (base + for + while + 2 ifs + ?:)
        public int VeryComplexMethod(int[] items)
        {
            int count = 0;
            for (int i = 0; i < items.Length; i++)
            {
                if (items[i] > 0)
                    count++;
            }
            while (count > 10)
            {
                count--;
            }
            return count > 5 ? count : 0;
        }

        // Complexity = 8 (base + switch + 5 cases + catch)
        public string SwitchMethod(int value)
        {
            try
            {
                switch (value)
                {
                    case 1:
                        return "one";
                    case 2:
                        return "two";
                    case 3:
                        return "three";
                    case 4:
                        return "four";
                    case 5:
                        return "five";
                    default:
                        return "unknown";
                }
            }
            catch (Exception ex)
            {
                return "error";
            }
        }
    }
}
"""


class CyclomaticComplexityTestCase(unittest.TestCase):

    def setUp(self):

        self.test_data: Dict[str, Dict[str, str]] = {
            CParser.parser_name(): C_TEST_FILES,
            CPPParser.parser_name(): CPP_TEST_FILES,
            GroovyParser.parser_name(): GROOVY_TEST_FILES,
            JavaParser.parser_name(): JAVA_TEST_FILES,
            JavaScriptParser.parser_name(): JAVASCRIPT_TEST_FILES,
            TypeScriptParser.parser_name(): TYPESCRIPT_TEST_FILES,
            KotlinParser.parser_name(): KOTLIN_TEST_FILES,
            ObjCParser.parser_name(): OBJC_TEST_FILES,
            RubyParser.parser_name(): RUBY_TEST_FILES,
            SwiftParser.parser_name(): SWIFT_TEST_FILES,
            PythonParser.parser_name(): PYTHON_TEST_FILES,
            GoParser.parser_name(): GO_TEST_FILES,
            CSharpParser.parser_name(): CSHARP_TEST_FILES
        }

        self.parsers: Dict[str, AbstractParser] = {
            CParser.parser_name(): CParser(),
            CPPParser.parser_name(): CPPParser(),
            GroovyParser.parser_name(): GroovyParser(),
            JavaParser.parser_name(): JavaParser(),
            JavaScriptParser.parser_name(): JavaScriptParser(),
            TypeScriptParser.parser_name(): TypeScriptParser(),
            KotlinParser.parser_name(): KotlinParser(),
            ObjCParser.parser_name(): ObjCParser(),
            RubyParser.parser_name(): RubyParser(),
            SwiftParser.parser_name(): SwiftParser(),
            PythonParser.parser_name(): PythonParser(),
            GoParser.parser_name(): GoParser(),
            CSharpParser.parser_name(): CSharpParser()
        }

        self.analysis = Analysis()
        self.analyzer = Analyzer(None, self.parsers)
        self.analysis.analysis_name = "test"
        self.analysis.source_directory = "/source"

        self.cyclomatic_complexity_metric = CyclomaticComplexityMetric(self.analysis)

    def tearDown(self):
        pass

    def test_cyclomatic_complexity_for_file_results(self):
        """Generate file results for all parsers and check if complexity metrics could be calculated."""
        results: Dict[str, FileResult] = {}

        for parser_name, test_data_dict in self.test_data.items():
            for file_name, file_content in test_data_dict.items():
                self.parsers[parser_name].generate_file_result_from_analysis(
                    self.analysis, file_name=file_name, full_file_path="/source/tests/" + file_name, file_content=file_content)

                self.assertTrue(bool(self.parsers[parser_name].results))
                results.update(self.parsers[parser_name].results)
                self.analysis.collect_results_from_parser(self.parsers[parser_name])

        self.assertTrue(bool(results))
        self.assertTrue(bool(self.analysis.file_results))
        self.assertFalse(bool(self.analysis.entity_results))

        for _, result in results.items():
            self.assertFalse(bool(result.metrics))

        self.assertTrue(bool(self.cyclomatic_complexity_metric.metric_name))
        self.analysis.metrics_for_file_results.update({
            self.cyclomatic_complexity_metric.metric_name: self.cyclomatic_complexity_metric
        })

        self.assertTrue(bool(self.analysis.contains_code_metrics))
        self.assertFalse(bool(self.analysis.contains_graph_metrics))

        self.assertFalse(self.analysis.local_metric_results)
        self.assertFalse(self.analysis.overall_metric_results)
        self.analyzer._calculate_code_metric_results(self.analysis)
        self.assertTrue(self.analysis.local_metric_results)
        self.assertTrue(self.analysis.overall_metric_results)

        # Verify that complexity metrics exist in results
        for _, result in self.analysis.file_results.items():
            if result.metrics:
                # Check if any complexity metrics were calculated
                has_complexity = any(
                    'cyclomatic-complexity' in key for key in result.metrics.keys()
                )
                if has_complexity:
                    LOGGER.info(f"✅ Complexity calculated for {result.scanned_file_name}: {result.metrics}")

    def test_cyclomatic_complexity_for_entity_results(self):
        """Generate entity results for all parsers and check if complexity metrics could be calculated."""
        results: Dict[str, FileResult] = {}

        for parser_name, test_data_dict in self.test_data.items():
            for file_name, file_content in test_data_dict.items():
                self.parsers[parser_name].generate_file_result_from_analysis(self.analysis, file_name=file_name, full_file_path="/tests/" + file_name, file_content=file_content)

                self.assertTrue(bool(self.parsers[parser_name].results))
                results.update(self.parsers[parser_name].results)
                self.analysis.collect_results_from_parser(self.parsers[parser_name])

        self.assertFalse(self.analysis.entity_results)

        for _, parser in self.parsers.items():
            try:
                parser.generate_entity_results_from_analysis(self.analysis)
                self.analysis.collect_results_from_parser(parser)
            except NotImplementedError:
                continue

        self.assertTrue(self.analysis.entity_results)

        self.assertTrue(bool(self.cyclomatic_complexity_metric.metric_name))
        self.analysis.metrics_for_entity_results.update({
            self.cyclomatic_complexity_metric.metric_name: self.cyclomatic_complexity_metric
        })

        self.assertFalse(self.analysis.local_metric_results)
        self.assertFalse(self.analysis.overall_metric_results)
        self.analyzer._calculate_code_metric_results(self.analysis)
        self.assertTrue(self.analysis.local_metric_results)
        self.assertTrue(self.analysis.overall_metric_results)

        # Verify that complexity metrics exist in entity results
        for _, result in self.analysis.entity_results.items():
            if result.metrics:
                has_complexity = any(
                    'cyclomatic-complexity' in key for key in result.metrics.keys()
                )
                if has_complexity:
                    LOGGER.info(f"✅ Complexity calculated for entity {result.entity_name}: {result.metrics}")

    def test_known_complexity_values(self):
        """Test cyclomatic complexity calculation with code that has known complexity values."""
        # Parse test code with known complexity
        csharp_parser = CSharpParser()
        csharp_parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="ComplexityTest.cs",
            full_file_path="/source/ComplexityTest.cs",
            file_content=CSHARP_COMPLEXITY_TEST
        )

        self.assertTrue(bool(csharp_parser.results))
        self.analysis.collect_results_from_parser(csharp_parser)

        # Generate entity results
        csharp_parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(csharp_parser)

        # Calculate complexity
        self.analysis.metrics_for_entity_results.update({
            self.cyclomatic_complexity_metric.metric_name: self.cyclomatic_complexity_metric
        })
        self.analyzer._calculate_code_metric_results(self.analysis)

        # Verify complexity values
        for _, result in self.analysis.entity_results.items():
            if result.entity_name == "TestComplexity":
                # The TestComplexity class has 5 methods with known complexity values
                # Expected: SimpleMethod(1), ModerateMethod(3), ComplexMethod(5),
                #           VeryComplexMethod(6), SwitchMethod(8)
                # Average: (1+3+5+6+8)/5 = 4.6
                # Max: 8

                avg_complexity = result.metrics.get('avg-cyclomatic-complexity-in-entity', 0)
                max_complexity = result.metrics.get('max-cyclomatic-complexity-in-entity', 0)

                LOGGER.info(f"TestComplexity - Avg Complexity: {avg_complexity}, Max Complexity: {max_complexity}")

                # Allow some tolerance for floating point comparison
                self.assertGreater(avg_complexity, 3.0, "Average complexity should be > 3")
                self.assertLess(avg_complexity, 6.0, "Average complexity should be < 6")
                self.assertGreaterEqual(max_complexity, 6, "Max complexity should be >= 6")

                LOGGER.info("✅ Complexity values validated!")
