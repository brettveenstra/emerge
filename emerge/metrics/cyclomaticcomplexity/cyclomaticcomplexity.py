"""
Contains the implementation of the cyclomatic complexity metric.
"""

# Authors: Brett Veenstra (C# support contribution)
# License: MIT

from typing import Dict, List
from enum import auto
import logging
import re

import coloredlogs

from emerge.analysis import Analysis

# interfaces for inputs
from emerge.abstractresult import AbstractResult, AbstractFileResult, AbstractEntityResult
from emerge.log import Logger

# enums and interface/type of the given metric
from emerge.metrics.abstractmetric import EnumLowerKebabCase
from emerge.metrics.metrics import CodeMetric


LOGGER = Logger(logging.getLogger('metrics'))
coloredlogs.install(level='E', logger=LOGGER.logger(), fmt=Logger.log_format)


class CyclomaticComplexityMetric(CodeMetric):
    """
    Calculates McCabe Cyclomatic Complexity for methods/functions.

    Cyclomatic complexity measures the number of linearly independent paths
    through a program's source code. Higher complexity indicates more complex
    code that is harder to test and maintain.

    Complexity Thresholds:
    - 1-10: Simple, easy to understand
    - 11-20: Moderate complexity, may need refactoring
    - 21+: High complexity, should be refactored
    """

    class Keys(EnumLowerKebabCase):
        # Entity-level metrics
        CYCLOMATIC_COMPLEXITY_IN_ENTITY = auto()
        MAX_CYCLOMATIC_COMPLEXITY_IN_ENTITY = auto()
        AVG_CYCLOMATIC_COMPLEXITY_IN_ENTITY = auto()

        # File-level metrics
        CYCLOMATIC_COMPLEXITY_IN_FILE = auto()
        MAX_CYCLOMATIC_COMPLEXITY_IN_FILE = auto()
        AVG_CYCLOMATIC_COMPLEXITY_IN_FILE = auto()

        # Overall metrics
        MAX_CYCLOMATIC_COMPLEXITY = auto()
        AVG_CYCLOMATIC_COMPLEXITY = auto()

    def __init__(self, analysis: Analysis):
        super().__init__(analysis)

        # Method extraction patterns (copied from NumberOfMethods)
        self.method_patterns = {
            "JAVA":       r"\b(?!if|for|while|switch|catch)\b[a-zA-Z\d_]+?\s*?\([a-zA-Z\d\s_,\>\<\?\*\.\[\]]*?\)\s*?\{",
            "KOTLIN":     r"fun\s[a-zA-Z\d_\.]+?\s*?\([a-zA-Z\d\s_,\?\@\>\<\?\*\.\[\]\:]*?\)\s*?.*?(\{|\=)",
            "OBJC":       r"[\-\+]\s*?[a-zA-Z\d_\(\)\:\*\s]+?\s*?\{",
            "SWIFT":      r"func\s*?[a-zA-Z\d_\(\)\:\*\s\-\<\>\?\,\[\]\.]+?\s*?\{",
            "RUBY":       r"(def)\s(.+)",
            "GROOVY":     r"\b(?!if|for|while|switch|catch)\b[a-zA-Z\d_]+?\s*?\([a-zA-Z\d\s_,\>\<\?\*\.\[\]\=\@\']*?\)\s*?\{",
            "JAVASCRIPT": r"(function\s+?)([a-zA-Z\d_\:\*\-\<\>\?\,\[\]\.\s\|\=\$]+?)\(([a-zA-Z\d_\(\)\:\*\s\-\<\>\?\,\[\]\.\|\=\$\/]*?)\)*?[\:]*?\s*?\{",
            "TYPESCRIPT": r"(function\s+?)([a-zA-Z\d_\:\*\-\<\>\?\,\[\]\.\s\|\=\$]+?)\(([a-zA-Z\d_\(\)\:\*\s\-\<\>\?\,\[\]\.\|\=\$\/]*?)\)*?[\:]*?\s*?\{",
            "C":          r"\b(?!if|for|while|switch)\b[a-zA-Z\d_]+?\s*?\([a-zA-Z\d\s_,\*]*?\)\s*?\{",
            "CPP":        r"\b(?!if|for|while|switch)\b[a-zA-Z\d\_\:\<\>\*\&]+?\s*?\([\(a-zA-Z\d\s_,\*&:]*?\)\s*?\w+\s*?\{",
            "PY":         r"(def)\s.+(.+):",
            "GO":         r"func\s*?[a-zA-Z\d_\(\)\:\*\s\-\<\>\?\,\[\]\.]+?\s*?\{",
            "CSHARP":     r"\b(?!if|for|while|switch|catch|using|lock|foreach)\b[a-zA-Z\d_]+?\s*?\([a-zA-Z\d\s_,\>\<\?\*\.\[\]]*?\)\s*?\{",
        }

        # C# decision point patterns
        # Control flow keywords
        self.csharp_control_keywords = [
            r'\bif\s*\(',
            r'\belse\s+if\s*\(',
            r'\bfor\s*\(',
            r'\bforeach\s*\(',
            r'\bwhile\s*\(',
            r'\bdo\s*\{',
            r'\bcatch\s*[\(\{]',
            r'\bcase\s+',
            r'\bwhen\s+',  # Pattern matching guard clause
        ]

        # Logical operators
        self.csharp_logical_operators = [
            r'&&',
            r'\|\|',
            r'\?\?',  # Null-coalescing
        ]

        # Ternary and null-conditional
        self.csharp_ternary_operators = [
            r'\?[^.]',  # Ternary (but not ?. null-conditional)
            r'\?\.',    # Null-conditional operator
        ]

        self.compiled_method_re: Dict[str, re.Pattern] = {}
        self.compiled_keyword_re: List[re.Pattern] = []
        self.compiled_operator_re: List[re.Pattern] = []
        self._compile()

    def _compile(self):
        """Compile all regex patterns for performance."""
        # Compile method extraction patterns
        for lang, pattern in self.method_patterns.items():
            self.compiled_method_re[lang] = re.compile(pattern)

        # Compile C# decision point patterns
        for keyword in self.csharp_control_keywords:
            self.compiled_keyword_re.append(re.compile(keyword))

        for operator in (self.csharp_logical_operators + self.csharp_ternary_operators):
            self.compiled_operator_re.append(re.compile(operator))

    def calculate_from_results(self, results: Dict[str, AbstractResult]):
        """Main entry point for metric calculation."""
        self._calculate_local_metric_data(results)
        self._calculate_global_metric_data(results)

    def _calculate_local_metric_data(self, results: Dict[str, AbstractResult]):
        """Calculate complexity for each file/entity."""
        for _, result in results.items():
            LOGGER.debug(f'calculating cyclomatic complexity for {result.unique_name}')

            # Get full source code
            full_source = " ".join(result.scanned_tokens)

            # Extract methods and calculate complexity
            method_complexities = self._extract_method_complexities(result, full_source)

            if method_complexities:
                total_complexity = sum(method_complexities)
                max_complexity = max(method_complexities)
                avg_complexity = total_complexity / len(method_complexities)
            else:
                total_complexity = 0
                max_complexity = 0
                avg_complexity = 0

            # Store metrics based on result type
            if isinstance(result, AbstractFileResult):
                result.metrics[self.Keys.CYCLOMATIC_COMPLEXITY_IN_FILE.value] = total_complexity
                result.metrics[self.Keys.MAX_CYCLOMATIC_COMPLEXITY_IN_FILE.value] = max_complexity
                result.metrics[self.Keys.AVG_CYCLOMATIC_COMPLEXITY_IN_FILE.value] = avg_complexity

                self.local_data[result.unique_name] = {
                    self.Keys.CYCLOMATIC_COMPLEXITY_IN_FILE.value: total_complexity,
                    self.Keys.MAX_CYCLOMATIC_COMPLEXITY_IN_FILE.value: max_complexity,
                    self.Keys.AVG_CYCLOMATIC_COMPLEXITY_IN_FILE.value: avg_complexity,
                }

            if isinstance(result, AbstractEntityResult):
                result.metrics[self.Keys.CYCLOMATIC_COMPLEXITY_IN_ENTITY.value] = total_complexity
                result.metrics[self.Keys.MAX_CYCLOMATIC_COMPLEXITY_IN_ENTITY.value] = max_complexity
                result.metrics[self.Keys.AVG_CYCLOMATIC_COMPLEXITY_IN_ENTITY.value] = avg_complexity

                self.local_data[result.unique_name] = {
                    self.Keys.CYCLOMATIC_COMPLEXITY_IN_ENTITY.value: total_complexity,
                    self.Keys.MAX_CYCLOMATIC_COMPLEXITY_IN_ENTITY.value: max_complexity,
                    self.Keys.AVG_CYCLOMATIC_COMPLEXITY_IN_ENTITY.value: avg_complexity,
                }

            LOGGER.debug(f'complexity calculated: {len(method_complexities)} methods, avg={avg_complexity:.2f}, max={max_complexity}')

    def _calculate_global_metric_data(self, results: Dict[str, AbstractResult]):
        """Calculate overall complexity statistics."""
        LOGGER.debug('calculating overall cyclomatic complexity statistics...')

        entity_results = {k: v for (k, v) in results.items() if isinstance(v, AbstractEntityResult)}
        file_results = {k: v for (k, v) in results.items() if isinstance(v, AbstractFileResult)}

        all_max_values = []
        all_avg_values = []

        # Aggregate from entity results
        for _, entity_result in entity_results.items():
            if self.Keys.MAX_CYCLOMATIC_COMPLEXITY_IN_ENTITY.value in entity_result.metrics:
                all_max_values.append(entity_result.metrics[self.Keys.MAX_CYCLOMATIC_COMPLEXITY_IN_ENTITY.value])
            if self.Keys.AVG_CYCLOMATIC_COMPLEXITY_IN_ENTITY.value in entity_result.metrics:
                all_avg_values.append(entity_result.metrics[self.Keys.AVG_CYCLOMATIC_COMPLEXITY_IN_ENTITY.value])

        # Aggregate from file results
        for _, file_result in file_results.items():
            if self.Keys.MAX_CYCLOMATIC_COMPLEXITY_IN_FILE.value in file_result.metrics:
                all_max_values.append(file_result.metrics[self.Keys.MAX_CYCLOMATIC_COMPLEXITY_IN_FILE.value])
            if self.Keys.AVG_CYCLOMATIC_COMPLEXITY_IN_FILE.value in file_result.metrics:
                all_avg_values.append(file_result.metrics[self.Keys.AVG_CYCLOMATIC_COMPLEXITY_IN_FILE.value])

        if all_max_values:
            self.overall_data[self.Keys.MAX_CYCLOMATIC_COMPLEXITY.value] = max(all_max_values)

        if all_avg_values:
            self.overall_data[self.Keys.AVG_CYCLOMATIC_COMPLEXITY.value] = sum(all_avg_values) / len(all_avg_values)

        LOGGER.debug(f'overall max complexity: {self.overall_data.get(self.Keys.MAX_CYCLOMATIC_COMPLEXITY.value, 0)}')
        LOGGER.debug(f'overall avg complexity: {self.overall_data.get(self.Keys.AVG_CYCLOMATIC_COMPLEXITY.value, 0):.2f}')

    def _extract_method_complexities(self, result: AbstractResult, full_source: str) -> List[int]:
        """
        Extract all methods and calculate complexity for each.

        Returns:
            List of complexity values, one per method
        """
        method_complexities = []

        # Get method extraction pattern for this language
        if result.scanned_language.name not in self.compiled_method_re:
            LOGGER.debug(f'no method pattern for language {result.scanned_language.name}')
            return method_complexities

        method_pattern = self.compiled_method_re[result.scanned_language.name]

        # Find all method starts
        method_matches = list(method_pattern.finditer(full_source))

        LOGGER.debug(f'found {len(method_matches)} methods in {result.unique_name}')

        # For each method, extract body and calculate complexity
        for i, match in enumerate(method_matches):
            method_start = match.start()

            # Find method end (next method start or end of file)
            if i + 1 < len(method_matches):
                method_end = method_matches[i + 1].start()
            else:
                method_end = len(full_source)

            method_body = full_source[method_start:method_end]

            # Calculate complexity for this method
            complexity = self._calculate_method_complexity(method_body, result.scanned_language.name)
            method_complexities.append(complexity)

        return method_complexities

    def _calculate_method_complexity(self, method_source: str, language: str) -> int:
        """
        Calculate cyclomatic complexity for a single method.

        Formula: Complexity = 1 (base) + number of decision points

        Args:
            method_source: Source code of the method
            language: Programming language name

        Returns:
            Cyclomatic complexity value
        """
        complexity = 1  # Base complexity

        # For C#, count all decision points
        if language == "CSHARP":
            # Count control flow keywords (if, for, while, etc.)
            for keyword_re in self.compiled_keyword_re:
                matches = keyword_re.findall(method_source)
                complexity += len(matches)

            # Count logical operators (&&, ||, ??)
            for operator_re in self.compiled_operator_re:
                matches = operator_re.findall(method_source)
                complexity += len(matches)
        else:
            # For other languages, use simplified detection (can be enhanced later)
            basic_keywords = [r'\bif\b', r'\bfor\b', r'\bwhile\b', r'\bcatch\b', r'\bcase\b']
            for keyword in basic_keywords:
                matches = re.findall(keyword, method_source)
                complexity += len(matches)

        return complexity
