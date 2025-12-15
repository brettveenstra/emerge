"""
All unit tests that are related to CSharpParser.
"""

# Authors: Grzegorz Lato <grzegorz.lato@gmail.com>
# License: MIT

from typing import Dict
import unittest

from tests.testdata.csharp import CSHARP_TEST_FILES

from emerge.languages.csharpparser import CSharpParser
from emerge.results import FileResult, EntityResult
from emerge.languages.abstractparser import LanguageType
from emerge.analysis import Analysis


class CSharpParserTestCase(unittest.TestCase):

    def setUp(self):
        self.example_data = CSHARP_TEST_FILES
        self.parser = CSharpParser()
        self.analysis = Analysis()
        self.analysis.analysis_name = "test"
        self.analysis.source_directory = "/tests"

    def tearDown(self):
        pass

    def test_generate_file_results(self):
        """Generate file results for all C# files and check if metrics were calculated."""
        self.assertFalse(self.parser.results)

        for file_name, file_content in self.example_data.items():
            self.parser.generate_file_result_from_analysis(
                self.analysis,
                file_name=file_name,
                full_file_path="/tests/" + file_name,
                file_content=file_content
            )

        results: Dict[str, FileResult] = self.parser.results
        self.assertTrue(results)
        self.assertEqual(len(results), 3)

        result: FileResult
        for _, result in results.items():
            self.assertTrue(len(result.scanned_tokens) > 0)
            self.assertTrue(len(result.scanned_import_dependencies) > 0)

            self.assertTrue(result.analysis.analysis_name.strip())
            self.assertTrue(result.scanned_file_name.strip())
            self.assertTrue(result.scanned_by.strip())
            self.assertEqual(result.scanned_language, LanguageType.CSHARP)

    def test_namespace_extraction(self):
        """Test namespace extraction from C# files."""
        for file_name, file_content in self.example_data.items():
            self.parser.generate_file_result_from_analysis(
                self.analysis,
                file_name=file_name,
                full_file_path="/tests/" + file_name,
                file_content=file_content
            )

        results: Dict[str, FileResult] = self.parser.results

        # Check that namespaces were extracted
        namespaces_found = []
        for _, result in results.items():
            if result.module_name:
                namespaces_found.append(result.module_name)

        self.assertTrue(len(namespaces_found) > 0)
        self.assertIn("Transportation.Vehicles", namespaces_found)
        self.assertIn("Transportation.Land", namespaces_found)
        self.assertIn("Transportation.Air", namespaces_found)

    def test_using_statements_extraction(self):
        """Test using statement extraction from C# files."""
        for file_name, file_content in self.example_data.items():
            self.parser.generate_file_result_from_analysis(
                self.analysis,
                file_name=file_name,
                full_file_path="/tests/" + file_name,
                file_content=file_content
            )

        results: Dict[str, FileResult] = self.parser.results

        # Check that using statements were extracted
        for _, result in results.items():
            self.assertTrue(len(result.scanned_import_dependencies) > 0)

        # Check specific using statements
        vehicle_file = [r for _, r in results.items() if "Vehicle.cs" in r.scanned_file_name][0]
        self.assertIn("System", vehicle_file.scanned_import_dependencies)
        self.assertIn("System.Collections.Generic", vehicle_file.scanned_import_dependencies)

    def test_generate_entity_results(self):
        """Generate entity results and check basic attributes."""
        self.assertFalse(self.parser.results)

        for file_name, file_content in self.example_data.items():
            self.parser.generate_file_result_from_analysis(
                self.analysis,
                file_name=file_name,
                full_file_path="/tests/" + file_name,
                file_content=file_content
            )

        self.parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(self.parser)
        entity_results = self.analysis.entity_results

        # Should find multiple entities:
        # Vehicle, IFlyable, ISwimmable, VehicleContainer
        # Car, Engine, ElectricCar, FuelType, Position, VehicleInfo, IChargeable
        # Airplane, Seaplane
        self.assertTrue(len(entity_results) >= 10)

        result: EntityResult
        for _, result in entity_results.items():
            self.assertTrue(len(result.scanned_tokens) > 0)
            self.assertTrue(result.analysis.analysis_name.strip())
            self.assertTrue(result.entity_name.strip())
            self.assertTrue(result.scanned_file_name.strip())
            self.assertTrue(result.scanned_by.strip())
            self.assertEqual(result.scanned_language, LanguageType.CSHARP)

    def test_class_detection(self):
        """Test that classes are correctly detected."""
        for file_name, file_content in self.example_data.items():
            self.parser.generate_file_result_from_analysis(
                self.analysis,
                file_name=file_name,
                full_file_path="/tests/" + file_name,
                file_content=file_content
            )

        self.parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(self.parser)
        entity_results = self.analysis.entity_results

        # Find specific classes
        entity_names = [e.entity_name for _, e in entity_results.items()]
        self.assertIn("Vehicle", entity_names)
        self.assertIn("Car", entity_names)
        self.assertIn("Airplane", entity_names)
        self.assertIn("ElectricCar", entity_names)

    def test_interface_detection(self):
        """Test that interfaces are correctly detected."""
        for file_name, file_content in self.example_data.items():
            self.parser.generate_file_result_from_analysis(
                self.analysis,
                file_name=file_name,
                full_file_path="/tests/" + file_name,
                file_content=file_content
            )

        self.parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(self.parser)
        entity_results = self.analysis.entity_results

        # Find interfaces
        entity_names = [e.entity_name for _, e in entity_results.items()]
        self.assertIn("IFlyable", entity_names)
        self.assertIn("ISwimmable", entity_names)
        self.assertIn("IChargeable", entity_names)

    def test_struct_detection(self):
        """Test that structs are correctly detected."""
        for file_name, file_content in self.example_data.items():
            self.parser.generate_file_result_from_analysis(
                self.analysis,
                file_name=file_name,
                full_file_path="/tests/" + file_name,
                file_content=file_content
            )

        self.parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(self.parser)
        entity_results = self.analysis.entity_results

        # Find struct
        entity_names = [e.entity_name for _, e in entity_results.items()]
        self.assertIn("Position", entity_names)

    def test_enum_detection(self):
        """Test that enums are correctly detected."""
        for file_name, file_content in self.example_data.items():
            self.parser.generate_file_result_from_analysis(
                self.analysis,
                file_name=file_name,
                full_file_path="/tests/" + file_name,
                file_content=file_content
            )

        self.parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(self.parser)
        entity_results = self.analysis.entity_results

        # Find enum
        entity_names = [e.entity_name for _, e in entity_results.items()]
        self.assertIn("FuelType", entity_names)

    def test_record_detection(self):
        """Test that records are correctly detected."""
        for file_name, file_content in self.example_data.items():
            self.parser.generate_file_result_from_analysis(
                self.analysis,
                file_name=file_name,
                full_file_path="/tests/" + file_name,
                file_content=file_content
            )

        self.parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(self.parser)
        entity_results = self.analysis.entity_results

        # Find record
        entity_names = [e.entity_name for _, e in entity_results.items()]
        self.assertIn("VehicleInfo", entity_names)

    def test_nested_class_detection(self):
        """Test that nested classes are correctly detected."""
        for file_name, file_content in self.example_data.items():
            self.parser.generate_file_result_from_analysis(
                self.analysis,
                file_name=file_name,
                full_file_path="/tests/" + file_name,
                file_content=file_content
            )

        self.parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(self.parser)
        entity_results = self.analysis.entity_results

        # Find nested Engine class
        entity_names = [e.entity_name for _, e in entity_results.items()]
        self.assertIn("Engine", entity_names)

    def test_inheritance_detection(self):
        """Test that inheritance relationships are detected."""
        for file_name, file_content in self.example_data.items():
            self.parser.generate_file_result_from_analysis(
                self.analysis,
                file_name=file_name,
                full_file_path="/tests/" + file_name,
                file_content=file_content
            )

        self.parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(self.parser)
        entity_results = self.analysis.entity_results

        # Find Car class and check it has Vehicle as inheritance
        car_entities = [e for _, e in entity_results.items() if e.entity_name == 'Car']
        self.assertTrue(len(car_entities) > 0)

        car = car_entities[0]
        self.assertTrue(len(car.scanned_inheritance_dependencies) > 0)
        self.assertIn("Vehicle", car.scanned_inheritance_dependencies)

    def test_multiple_inheritance_detection(self):
        """Test that multiple inheritance (class + interfaces) is detected."""
        for file_name, file_content in self.example_data.items():
            self.parser.generate_file_result_from_analysis(
                self.analysis,
                file_name=file_name,
                full_file_path="/tests/" + file_name,
                file_content=file_content
            )

        self.parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(self.parser)
        entity_results = self.analysis.entity_results

        # Find ElectricCar class - should inherit from Car and IChargeable
        electric_car_entities = [e for _, e in entity_results.items() if e.entity_name == 'ElectricCar']
        self.assertTrue(len(electric_car_entities) > 0)

        electric_car = electric_car_entities[0]
        self.assertTrue(len(electric_car.scanned_inheritance_dependencies) >= 2)
        self.assertIn("Car", electric_car.scanned_inheritance_dependencies)
        self.assertIn("IChargeable", electric_car.scanned_inheritance_dependencies)

    def test_file_scoped_namespace(self):
        """Test that file-scoped namespaces (C# 10+) are correctly parsed."""
        # Airplane.cs uses file-scoped namespace
        airplane_content = self.example_data["Airplane.cs"]
        self.parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="Airplane.cs",
            full_file_path="/tests/Airplane.cs",
            file_content=airplane_content
        )

        results: Dict[str, FileResult] = self.parser.results
        airplane_result = [r for _, r in results.items() if "Airplane.cs" in r.scanned_file_name][0]

        # Should have Transportation.Air namespace
        self.assertEqual(airplane_result.module_name, "Transportation.Air")


if __name__ == '__main__':
    unittest.main()
