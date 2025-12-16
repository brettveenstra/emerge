"""
All unit tests that are related to configuration.
"""

# Authors: Grzegorz Lato <grzegorz.lato@gmail.com>
# License: MIT

import unittest
from emerge.config import Configuration
from emerge.config import Analysis, YamlLoader
import coloredlogs
import logging

LOGGER = logging.getLogger('TESTS')
coloredlogs.install(level='INFO', logger=LOGGER, fmt='\n%(asctime)s %(name)s %(levelname)s %(message)s')


# pylint: disable=protected-access
class ConfigurationTestCase(unittest.TestCase):

    def setUp(self):
        self.version = "1.0.0"
        self.configuration = Configuration(self.version)
        self.analysis = Analysis()

    def tearDown(self):
        pass

    def test_config_init(self):
        self.assertIsNotNone(self.configuration)
        self.assertIsNotNone(self.configuration.analyses)
        self.assertTrue(len(self.configuration.analyses) == 0)
        self.assertTrue(self.configuration.project_name == "unnamed")
        self.assertIsNotNone(self.configuration._yaml_loader)
        self.assertIs(type(self.configuration._yaml_loader), YamlLoader)
        LOGGER.info(f'completed testing of CurrentConfiguration init')

    def test_single_source_directory(self):
        """Test backward compatibility with single source_directory"""
        self.analysis.source_directory = "/path/to/repo"
        self.analysis.source_directories = ["/path/to/repo"]

        self.assertEqual(self.analysis.source_directory, "/path/to/repo")
        self.assertEqual(len(self.analysis.source_directories), 1)
        self.assertEqual(self.analysis.source_directories[0], "/path/to/repo")
        LOGGER.info('completed testing of single source_directory')

    def test_multiple_source_directories(self):
        """Test multi-target scanning with multiple source directories"""
        source_dirs = ["/path/to/repo1", "/path/to/repo2", "/path/to/repo3"]
        self.analysis.source_directories = source_dirs
        self.analysis.source_directory = source_dirs[0]

        self.assertEqual(len(self.analysis.source_directories), 3)
        self.assertEqual(self.analysis.source_directories, source_dirs)
        self.assertEqual(self.analysis.source_directory, source_dirs[0])
        LOGGER.info('completed testing of multiple source_directories')

    def test_source_directories_normalization(self):
        """Test that both config formats are normalized internally"""
        # Single directory should create a list with one element
        self.analysis.source_directory = "/single/repo"
        self.analysis.source_directories = ["/single/repo"]

        self.assertIsInstance(self.analysis.source_directories, list)
        self.assertEqual(len(self.analysis.source_directories), 1)

        # Multiple directories
        self.analysis.source_directories = ["/repo1", "/repo2"]
        self.assertEqual(len(self.analysis.source_directories), 2)
        LOGGER.info('completed testing of source_directories normalization')


if __name__ == '__main__':
    unittest.main()
