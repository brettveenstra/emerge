"""
Unit tests for C# parser improvements (partial classes, properties, attributes).
"""

# Authors: Grzegorz Lato <grzegorz.lato@gmail.com>
# License: MIT

import unittest
import logging
import coloredlogs

from emerge.analysis import Analysis
from emerge.analyzer import Analyzer
from emerge.languages.csharpparser import CSharpParser

LOGGER = logging.getLogger('TESTS')
coloredlogs.install(level='INFO', logger=LOGGER, fmt='\n%(asctime)s %(name)s %(levelname)s %(message)s')


# Test data for partial classes
PARTIAL_CLASS_FILE_1 = """
namespace MyApp.Core
{
    public partial class CustomerService
    {
        public void ProcessOrder()
        {
            Console.WriteLine("Processing order");
        }
    }
}
"""

PARTIAL_CLASS_FILE_2 = """
namespace MyApp.Core
{
    public partial class CustomerService
    {
        public void ValidateCustomer()
        {
            Console.WriteLine("Validating customer");
        }
    }
}
"""

PARTIAL_CLASS_FILE_3 = """
namespace MyApp.Core
{
    public partial class CustomerService
    {
        public void SendConfirmation()
        {
            Console.WriteLine("Sending confirmation");
        }
    }
}
"""

# Partial classes in different namespaces (should NOT be merged)
PARTIAL_DIFFERENT_NAMESPACE_1 = """
namespace MyApp.Services
{
    public partial class OrderProcessor
    {
        public void ProcessA() { }
    }
}
"""

PARTIAL_DIFFERENT_NAMESPACE_2 = """
namespace MyApp.Data
{
    public partial class OrderProcessor
    {
        public void ProcessB() { }
    }
}
"""

# Non-partial class for comparison
NON_PARTIAL_CLASS = """
namespace MyApp.Core
{
    public class RegularService
    {
        public void DoWork() { }
    }
}
"""


class PartialClassMergingTestCase(unittest.TestCase):

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

    def test_partial_class_detection(self):
        """Test that partial keyword is detected in entity declarations"""

        parser = self.parsers[CSharpParser.parser_name()]

        # Parse partial class file
        parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="CustomerService1.cs",
            full_file_path="/source/CustomerService1.cs",
            file_content=PARTIAL_CLASS_FILE_1
        )

        self.assertTrue(bool(parser.results))
        self.analysis.collect_results_from_parser(parser)

        # Generate entity results
        parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(parser)

        # Find the CustomerService entity
        entity_results = [r for r in self.analysis.results.values()
                         if hasattr(r, 'entity_name') and r.entity_name == 'CustomerService']

        self.assertEqual(len(entity_results), 1, "Should have exactly 1 CustomerService entity")

        entity = entity_results[0]
        self.assertTrue(entity.is_partial, "CustomerService should be marked as partial")

        LOGGER.info('completed testing of partial class detection')

    def test_two_file_partial_class_merging(self):
        """Test that 2 partial class files merge into 1 entity"""

        parser = self.parsers[CSharpParser.parser_name()]

        # Parse first partial class file
        parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="CustomerService1.cs",
            full_file_path="/source/CustomerService1.cs",
            file_content=PARTIAL_CLASS_FILE_1
        )

        # Parse second partial class file
        parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="CustomerService2.cs",
            full_file_path="/source/CustomerService2.cs",
            file_content=PARTIAL_CLASS_FILE_2
        )

        self.analysis.collect_results_from_parser(parser)

        # Generate entity results (this should trigger merging)
        parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(parser)

        # Find CustomerService entities
        entity_results = [r for r in self.analysis.results.values()
                         if hasattr(r, 'entity_name') and r.entity_name == 'CustomerService']

        self.assertEqual(len(entity_results), 1, "Should have exactly 1 merged CustomerService entity")

        entity = entity_results[0]
        self.assertTrue(entity.is_partial, "Merged entity should still be marked as partial")

        # Verify tokens from both files are present
        tokens_str = ' '.join(entity.scanned_tokens)
        self.assertIn('ProcessOrder', tokens_str, "Should contain method from first file")
        self.assertIn('ValidateCustomer', tokens_str, "Should contain method from second file")

        LOGGER.info(f'Merged entity has {len(entity.scanned_tokens)} tokens from 2 files')
        LOGGER.info('completed testing of 2-file partial class merging')

    def test_three_file_partial_class_merging(self):
        """Test that 3 partial class files merge correctly"""

        parser = self.parsers[CSharpParser.parser_name()]

        # Parse three partial class files
        parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="CustomerService1.cs",
            full_file_path="/source/CustomerService1.cs",
            file_content=PARTIAL_CLASS_FILE_1
        )

        parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="CustomerService2.cs",
            full_file_path="/source/CustomerService2.cs",
            file_content=PARTIAL_CLASS_FILE_2
        )

        parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="CustomerService3.cs",
            full_file_path="/source/CustomerService3.cs",
            file_content=PARTIAL_CLASS_FILE_3
        )

        self.analysis.collect_results_from_parser(parser)

        # Generate entity results
        parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(parser)

        # Find CustomerService entities
        entity_results = [r for r in self.analysis.results.values()
                         if hasattr(r, 'entity_name') and r.entity_name == 'CustomerService']

        self.assertEqual(len(entity_results), 1, "Should have exactly 1 merged CustomerService entity")

        entity = entity_results[0]
        tokens_str = ' '.join(entity.scanned_tokens)

        # Verify tokens from all three files are present
        self.assertIn('ProcessOrder', tokens_str, "Should contain method from first file")
        self.assertIn('ValidateCustomer', tokens_str, "Should contain method from second file")
        self.assertIn('SendConfirmation', tokens_str, "Should contain method from third file")

        LOGGER.info(f'Merged entity has {len(entity.scanned_tokens)} tokens from 3 files')
        LOGGER.info('completed testing of 3-file partial class merging')

    def test_partial_classes_different_namespaces_not_merged(self):
        """Test that partials in different namespaces stay separate"""

        parser = self.parsers[CSharpParser.parser_name()]

        # Parse partial classes with same name but different namespaces
        parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="OrderProcessor1.cs",
            full_file_path="/source/OrderProcessor1.cs",
            file_content=PARTIAL_DIFFERENT_NAMESPACE_1
        )

        parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="OrderProcessor2.cs",
            full_file_path="/source/OrderProcessor2.cs",
            file_content=PARTIAL_DIFFERENT_NAMESPACE_2
        )

        self.analysis.collect_results_from_parser(parser)

        # Generate entity results
        parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(parser)

        # Find OrderProcessor entities
        entity_results = [r for r in self.analysis.results.values()
                         if hasattr(r, 'entity_name') and r.entity_name == 'OrderProcessor']

        self.assertEqual(len(entity_results), 2, "Should have 2 separate OrderProcessor entities (different namespaces)")

        # Verify they have different unique names
        unique_names = [e.unique_name for e in entity_results]
        self.assertIn('MyApp.Services.OrderProcessor', unique_names, "Should have Services.OrderProcessor")
        self.assertIn('MyApp.Data.OrderProcessor', unique_names, "Should have Data.OrderProcessor")

        LOGGER.info('completed testing of partial classes in different namespaces')

    def test_non_partial_class_not_affected(self):
        """Test that non-partial classes are not affected by merging logic"""

        parser = self.parsers[CSharpParser.parser_name()]

        # Parse non-partial class
        parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="RegularService.cs",
            full_file_path="/source/RegularService.cs",
            file_content=NON_PARTIAL_CLASS
        )

        self.analysis.collect_results_from_parser(parser)

        # Generate entity results
        parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(parser)

        # Find RegularService entity
        entity_results = [r for r in self.analysis.results.values()
                         if hasattr(r, 'entity_name') and r.entity_name == 'RegularService']

        self.assertEqual(len(entity_results), 1, "Should have exactly 1 RegularService entity")

        entity = entity_results[0]
        self.assertFalse(entity.is_partial, "RegularService should NOT be marked as partial")

        LOGGER.info('completed testing of non-partial class')

    def test_mixed_partial_and_nonpartial_classes(self):
        """Test parsing a mix of partial and non-partial classes"""

        parser = self.parsers[CSharpParser.parser_name()]

        # Parse partial class
        parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="CustomerService1.cs",
            full_file_path="/source/CustomerService1.cs",
            file_content=PARTIAL_CLASS_FILE_1
        )

        parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="CustomerService2.cs",
            full_file_path="/source/CustomerService2.cs",
            file_content=PARTIAL_CLASS_FILE_2
        )

        # Parse non-partial class
        parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="RegularService.cs",
            full_file_path="/source/RegularService.cs",
            file_content=NON_PARTIAL_CLASS
        )

        self.analysis.collect_results_from_parser(parser)

        # Generate entity results
        parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(parser)

        # Should have 2 entities total: 1 merged CustomerService + 1 RegularService
        entity_results = [r for r in self.analysis.results.values() if hasattr(r, 'entity_name')]

        self.assertEqual(len(entity_results), 2, "Should have 2 entities: merged partial + non-partial")

        # Find specific entities
        customer_service = next((e for e in entity_results if e.entity_name == 'CustomerService'), None)
        regular_service = next((e for e in entity_results if e.entity_name == 'RegularService'), None)

        self.assertIsNotNone(customer_service, "Should find CustomerService")
        self.assertIsNotNone(regular_service, "Should find RegularService")

        self.assertTrue(customer_service.is_partial, "CustomerService should be partial")
        self.assertFalse(regular_service.is_partial, "RegularService should not be partial")

        LOGGER.info('completed testing of mixed partial and non-partial classes')


# Test data for property dependencies
SIMPLE_PROPERTY_CLASS = """
using MyApp.Data;

namespace MyApp.Services
{
    public class OrderService
    {
        public IRepository Repository { get; set; }
    }
}
"""

GENERIC_PROPERTY_CLASS = """
using System.Collections.Generic;
using MyApp.Models;

namespace MyApp.Services
{
    public class CustomerService
    {
        public List<Customer> Customers { get; set; }
        public Dictionary<string, Order> Orders { get; set; }
    }
}
"""

ARRAY_PROPERTY_CLASS = """
using MyApp.Models;

namespace MyApp.Services
{
    public class ProductService
    {
        public Product[] Products { get; set; }
    }
}
"""

MULTIPLE_PROPERTIES_CLASS = """
using MyApp.Data;
using MyApp.Models;

namespace MyApp.Services
{
    public class BusinessService
    {
        public IRepository Repository { get; set; }
        public Customer CurrentCustomer { get; set; }
        private Order _lastOrder { get; set; }
        protected List<Product> Inventory { get; set; }
    }
}
"""

NO_DEPENDENCY_PROPERTY_CLASS = """
namespace MyApp.Services
{
    public class SimpleService
    {
        public string Name { get; set; }
        public int Count { get; set; }
    }
}
"""


class PropertyDependencyTestCase(unittest.TestCase):

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

    def test_simple_property_dependency(self):
        """Test that simple property type creates dependency"""

        parser = self.parsers[CSharpParser.parser_name()]

        parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="OrderService.cs",
            full_file_path="/source/OrderService.cs",
            file_content=SIMPLE_PROPERTY_CLASS
        )

        self.analysis.collect_results_from_parser(parser)

        # Generate entity results
        parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(parser)

        # Find the OrderService entity
        entity_results = [r for r in self.analysis.results.values()
                         if hasattr(r, 'entity_name') and r.entity_name == 'OrderService']

        self.assertEqual(len(entity_results), 1, "Should have exactly 1 OrderService entity")

        entity = entity_results[0]
        self.assertIn('MyApp.Data', entity.scanned_import_dependencies,
                     "Should have dependency on MyApp.Data from IRepository property")

        LOGGER.info('completed testing of simple property dependency')

    def test_generic_property_dependencies(self):
        """Test that generic property types create dependencies"""

        parser = self.parsers[CSharpParser.parser_name()]

        parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="CustomerService.cs",
            full_file_path="/source/CustomerService.cs",
            file_content=GENERIC_PROPERTY_CLASS
        )

        self.analysis.collect_results_from_parser(parser)

        # Generate entity results
        parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(parser)

        # Find the CustomerService entity
        entity_results = [r for r in self.analysis.results.values()
                         if hasattr(r, 'entity_name') and r.entity_name == 'CustomerService']

        self.assertEqual(len(entity_results), 1, "Should have exactly 1 CustomerService entity")

        entity = entity_results[0]

        # Should have MyApp.Models dependency from both Customer and Order generic types
        self.assertIn('MyApp.Models', entity.scanned_import_dependencies,
                     "Should have dependency on MyApp.Models from generic properties")

        LOGGER.info('completed testing of generic property dependencies')

    def test_array_property_dependency(self):
        """Test that array property types create dependencies"""

        parser = self.parsers[CSharpParser.parser_name()]

        parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="ProductService.cs",
            full_file_path="/source/ProductService.cs",
            file_content=ARRAY_PROPERTY_CLASS
        )

        self.analysis.collect_results_from_parser(parser)

        # Generate entity results
        parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(parser)

        # Find the ProductService entity
        entity_results = [r for r in self.analysis.results.values()
                         if hasattr(r, 'entity_name') and r.entity_name == 'ProductService']

        self.assertEqual(len(entity_results), 1, "Should have exactly 1 ProductService entity")

        entity = entity_results[0]
        self.assertIn('MyApp.Models', entity.scanned_import_dependencies,
                     "Should have dependency on MyApp.Models from Product[] property")

        LOGGER.info('completed testing of array property dependency')

    def test_multiple_properties_different_types(self):
        """Test that multiple properties with different types all create dependencies"""

        parser = self.parsers[CSharpParser.parser_name()]

        parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="BusinessService.cs",
            full_file_path="/source/BusinessService.cs",
            file_content=MULTIPLE_PROPERTIES_CLASS
        )

        self.analysis.collect_results_from_parser(parser)

        # Generate entity results
        parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(parser)

        # Find the BusinessService entity
        entity_results = [r for r in self.analysis.results.values()
                         if hasattr(r, 'entity_name') and r.entity_name == 'BusinessService']

        self.assertEqual(len(entity_results), 1, "Should have exactly 1 BusinessService entity")

        entity = entity_results[0]

        # Should have both MyApp.Data and MyApp.Models dependencies
        self.assertIn('MyApp.Data', entity.scanned_import_dependencies,
                     "Should have dependency on MyApp.Data from Repository property")
        self.assertIn('MyApp.Models', entity.scanned_import_dependencies,
                     "Should have dependency on MyApp.Models from Customer, Order, Product properties")

        LOGGER.info(f'BusinessService has {len(entity.scanned_import_dependencies)} dependencies')
        LOGGER.info('completed testing of multiple property dependencies')

    def test_builtin_type_properties_no_dependencies(self):
        """Test that built-in type properties don't create false dependencies"""

        parser = self.parsers[CSharpParser.parser_name()]

        parser.generate_file_result_from_analysis(
            self.analysis,
            file_name="SimpleService.cs",
            full_file_path="/source/SimpleService.cs",
            file_content=NO_DEPENDENCY_PROPERTY_CLASS
        )

        self.analysis.collect_results_from_parser(parser)

        # Generate entity results
        parser.generate_entity_results_from_analysis(self.analysis)
        self.analysis.collect_results_from_parser(parser)

        # Find the SimpleService entity
        entity_results = [r for r in self.analysis.results.values()
                         if hasattr(r, 'entity_name') and r.entity_name == 'SimpleService']

        self.assertEqual(len(entity_results), 1, "Should have exactly 1 SimpleService entity")

        entity = entity_results[0]

        # Built-in types (string, int) should not create dependencies
        self.assertEqual(len(entity.scanned_import_dependencies), 0,
                        "Built-in types should not create dependencies")

        LOGGER.info('completed testing of built-in type properties')


if __name__ == '__main__':
    unittest.main()
