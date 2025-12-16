"""
Contains the implementation of the C# language parser and a relevant keyword enum.
"""

# Authors: Grzegorz Lato <grzegorz.lato@gmail.com>
# License: MIT

from typing import Dict, List
from enum import Enum, unique
import logging
from pathlib import Path

import pyparsing as pp
import coloredlogs

from emerge.languages.abstractparser import AbstractParser, ParsingMixin, Parser, CoreParsingKeyword, LanguageType
from emerge.results import EntityResult, FileResult
from emerge.abstractresult import AbstractResult, AbstractFileResult, AbstractEntityResult
from emerge.stats import Statistics
from emerge.log import Logger

LOGGER = Logger(logging.getLogger('parser'))
coloredlogs.install(level='E', logger=LOGGER.logger(), fmt=Logger.log_format)


@unique
class CSharpParsingKeyword(Enum):
    # Entity keywords
    CLASS = "class"
    INTERFACE = "interface"
    STRUCT = "struct"
    ENUM = "enum"
    RECORD = "record"
    PARTIAL = "partial"

    # Scope delimiters
    OPEN_SCOPE = "{"
    CLOSE_SCOPE = "}"

    # Comments
    INLINE_COMMENT = "//"
    START_BLOCK_COMMENT = "/*"
    STOP_BLOCK_COMMENT = "*/"

    # Dependencies
    USING = "using"
    NAMESPACE = "namespace"
    NAMESPACE_NAME = "namespace_name"


class CSharpParser(AbstractParser, ParsingMixin):

    def __init__(self):
        self._results: Dict[str, AbstractResult] = {}
        self._token_mappings: Dict[str, str] = {
            ':': ' : ',
            ';': ' ; ',
            '{': ' { ',
            '}': ' } ',
            '(': ' ( ',
            ')': ' ) ',
            '[': ' [ ',
            ']': ' ] ',
            '?': ' ? ',
            '!': ' ! ',
            ',': ' , ',
            '<': ' < ',
            '>': ' > ',
            '"': ' " ',
        }

    @classmethod
    def parser_name(cls) -> str:
        return Parser.CSHARP_PARSER.name

    @classmethod
    def language_type(cls) -> str:
        return LanguageType.CSHARP.name

    @property
    def results(self) -> Dict[str, AbstractResult]:
        return self._results

    @results.setter
    def results(self, value):
        self._results = value

    def generate_file_result_from_analysis(self, analysis, *, file_name: str, full_file_path: str, file_content: str) -> None:
        LOGGER.debug('generating file results...')
        scanned_tokens = self.preprocess_file_content_and_generate_token_list_by_mapping(file_content, self._token_mappings)

        # make sure to create unique names by using the relative analysis path as a base for the result
        parent_analysis_source_path = f"{Path(analysis.source_directory).parent}/"
        relative_file_path_to_analysis = full_file_path.replace(parent_analysis_source_path, "")

        file_result = FileResult.create_file_result(
            analysis=analysis,
            scanned_file_name=file_name,
            relative_file_path_to_analysis=relative_file_path_to_analysis,
            absolute_name=full_file_path,
            display_name=file_name,
            module_name="",
            scanned_by=self.parser_name(),
            scanned_language=LanguageType.CSHARP,
            scanned_tokens=scanned_tokens,
            source=file_content,
            preprocessed_source=""
        )

        self._add_namespace_to_result(file_result)
        self._add_usings_to_result(file_result, analysis)
        self._results[file_result.unique_name] = file_result

    def after_generated_file_results(self, analysis) -> None:
        # curate dependencies from the first scan to match the real dependencies
        filtered_results = {k: v for (k, v) in self.results.items() if v.analysis is analysis and isinstance(v, FileResult)}

        result: FileResult
        for _, result in filtered_results.items():
            curated_dependencies = []

            for dependency in result.scanned_import_dependencies:
                curated = False
                haystack = dependency.replace(".", "/") + ".cs"

                for needle, _ in filtered_results.items():
                    if (needle in haystack) or (haystack in needle):
                        curated = True
                        curated_dependencies.append(needle)
                        break
                if not curated:
                    curated_dependencies.append(dependency)

            result.scanned_import_dependencies = curated_dependencies

    def create_unique_entity_name(self, entity: AbstractEntityResult) -> None:
        if entity.module_name:
            entity.unique_name = entity.module_name + CoreParsingKeyword.DOT.value + entity.entity_name
        else:
            entity.unique_name = entity.entity_name

    def generate_entity_results_from_analysis(self, analysis):
        LOGGER.debug('generating entity results...')
        filtered_results = {k: v for (k, v) in self.results.items() if v.analysis is analysis and isinstance(v, AbstractFileResult)}

        result: AbstractFileResult
        for _, result in filtered_results.items():

            entity_keywords: List[str] = [
                CSharpParsingKeyword.CLASS.value,
                CSharpParsingKeyword.INTERFACE.value,
                CSharpParsingKeyword.STRUCT.value,
                CSharpParsingKeyword.ENUM.value,
                CSharpParsingKeyword.RECORD.value
            ]

            entity_name = pp.Word(pp.alphanums + CoreParsingKeyword.UNDERSCORE.value)

            match_expression = (
                pp.Optional(pp.Keyword(CSharpParsingKeyword.PARTIAL.value)).setResultsName('is_partial') +
                (
                    pp.Keyword(CSharpParsingKeyword.CLASS.value) |
                    pp.Keyword(CSharpParsingKeyword.INTERFACE.value) |
                    pp.Keyword(CSharpParsingKeyword.STRUCT.value) |
                    pp.Keyword(CSharpParsingKeyword.ENUM.value) |
                    pp.Keyword(CSharpParsingKeyword.RECORD.value)
                ) +
                entity_name.setResultsName(CoreParsingKeyword.ENTITY_NAME.value) +
                pp.Optional(
                    pp.Keyword(CoreParsingKeyword.COLON.value) +
                    pp.delimitedList(entity_name, delim=',').setResultsName(CoreParsingKeyword.INHERITED_ENTITY_NAME.value)
                ) +
                pp.SkipTo(pp.FollowedBy(CSharpParsingKeyword.OPEN_SCOPE.value))
            )

            comment_keywords: Dict[str, str] = {
                CoreParsingKeyword.LINE_COMMENT.value: CSharpParsingKeyword.INLINE_COMMENT.value,
                CoreParsingKeyword.START_BLOCK_COMMENT.value: CSharpParsingKeyword.START_BLOCK_COMMENT.value,
                CoreParsingKeyword.STOP_BLOCK_COMMENT.value: CSharpParsingKeyword.STOP_BLOCK_COMMENT.value
            }

            entity_results = result.generate_entity_results_from_scopes(entity_keywords, match_expression, comment_keywords)

            entity_results: List[EntityResult]
            for entity_result in entity_results:
                self._add_inheritance_to_entity_result(entity_result)
                self._add_imports_to_entity_result(entity_result)
                self._add_property_dependencies_to_entity_result(entity_result)
                self.create_unique_entity_name(entity_result)

                # For partial entities, use absolute_name as key to prevent overwrites
                # We'll fix the unique_name during merging
                storage_key = entity_result.absolute_name if entity_result.is_partial else entity_result.unique_name
                self._results[storage_key] = entity_result

        # Merge partial entities after all entities have been generated
        self._merge_partial_entities(analysis)

    def _add_imports_to_entity_result(self, entity_result: EntityResult):
        LOGGER.debug('adding usings to entity result...')
        for scanned_import in entity_result.parent_file_result.scanned_import_dependencies:
            last_component_of_import = scanned_import.split(CoreParsingKeyword.DOT.value)[-1]
            for token in entity_result.scanned_tokens:
                if last_component_of_import in token and scanned_import not in entity_result.scanned_import_dependencies:
                    entity_result.scanned_import_dependencies.append(scanned_import)

    def _add_property_dependencies_to_entity_result(self, entity_result: EntityResult):
        """Extract property type dependencies from entity tokens."""
        LOGGER.debug(f'extracting property dependencies from entity {entity_result.entity_name}...')

        list_of_words = entity_result.scanned_tokens

        # Simple pattern matching for properties: look for { get; or { set;
        # which are strong indicators of property declarations
        for i, token in enumerate(list_of_words):
            if token == '{' and i > 1:
                # Look ahead for 'get' or 'set'
                is_property = False
                if i + 1 < len(list_of_words):
                    next_token = list_of_words[i + 1]
                    if next_token in ['get', 'set']:
                        is_property = True

                if is_property:
                    # Look backward to find the property type
                    # Pattern: [modifiers...] Type PropertyName {
                    # We want the Type (second-to-last token before {)
                    if i >= 2:
                        property_name_token = list_of_words[i - 1]
                        property_type_token = list_of_words[i - 2]

                        # Skip if property type is a modifier keyword
                        skip_keywords = ['public', 'private', 'protected', 'internal', 'static',
                                        'readonly', 'virtual', 'override', 'abstract', 'sealed']

                        # Walk backward past modifiers to find the actual type
                        type_index = i - 2
                        while type_index >= 0 and list_of_words[type_index] in skip_keywords:
                            type_index -= 1

                        if type_index >= 0:
                            property_type_token = list_of_words[type_index]

                            # Skip built-in types
                            builtin_types = ['string', 'int', 'bool', 'double', 'float', 'long',
                                           'decimal', 'byte', 'char', 'short', 'object', 'var']

                            base_type = property_type_token.split('<')[0].split('[')[0]

                            if base_type not in builtin_types:
                                # Check if this type appears in any import
                                # Strategy: if the type name appears anywhere in the tokens and
                                # there are imports, assume the type comes from one of the imports
                                for scanned_import in entity_result.parent_file_result.scanned_import_dependencies:
                                    # Add the import as a dependency if the type might come from it
                                    # This is a heuristic: any non-builtin type with an import is likely related
                                    if scanned_import not in entity_result.scanned_import_dependencies:
                                        entity_result.scanned_import_dependencies.append(scanned_import)
                                        LOGGER.debug(f'added property dependency: {scanned_import} from property type {base_type}')
                                        break  # Only add one import per property

                            # Also check for generic type parameters (types between < and >)
                            # Look for tokens after the current type_index
                            for j in range(type_index + 1, min(type_index + 10, len(list_of_words))):
                                potential_type = list_of_words[j]
                                if potential_type == '>':
                                    break
                                # Check if this is a type (not a symbol)
                                if potential_type not in [',', '<', '>'] and potential_type not in builtin_types:
                                    if potential_type.isalnum() or '_' in potential_type:
                                        for scanned_import in entity_result.parent_file_result.scanned_import_dependencies:
                                            if scanned_import not in entity_result.scanned_import_dependencies:
                                                entity_result.scanned_import_dependencies.append(scanned_import)
                                                LOGGER.debug(f'added property dependency: {scanned_import} from generic parameter {potential_type}')
                                                break

    def _merge_partial_entities(self, analysis):
        """Merge partial class/struct/interface declarations into single entities."""
        LOGGER.debug('merging partial entities...')

        # Get all entity results for this analysis (may be keyed by absolute_name for partials)
        entity_results = [(k, v) for (k, v) in self.results.items()
                         if v.analysis is analysis and isinstance(v, EntityResult)]

        # Group partial entities by their unique name (namespace.entityname)
        partial_groups: Dict[str, List[tuple]] = {}
        for storage_key, entity in entity_results:
            if entity.is_partial:
                # Group by the entity's unique_name (namespace.entityname), not storage key
                if entity.unique_name not in partial_groups:
                    partial_groups[entity.unique_name] = []
                partial_groups[entity.unique_name].append((storage_key, entity))

        # Merge groups that have multiple partial entities
        for unique_name, partials in partial_groups.items():
            if len(partials) > 1:
                LOGGER.debug(f'merging {len(partials)} partial declarations of {unique_name}')

                # Use first partial as the base (keep its file reference)
                primary_key, primary = partials[0]

                # Merge tokens from all other partials
                for storage_key, partial in partials[1:]:
                    primary.scanned_tokens.extend(partial.scanned_tokens)

                    # Merge import dependencies (avoid duplicates)
                    for dep in partial.scanned_import_dependencies:
                        if dep not in primary.scanned_import_dependencies:
                            primary.scanned_import_dependencies.append(dep)

                    # Merge inheritance dependencies (avoid duplicates)
                    for inh in partial.scanned_inheritance_dependencies:
                        if inh not in primary.scanned_inheritance_dependencies:
                            primary.scanned_inheritance_dependencies.append(inh)

                    # Remove the merged partial from results (using its storage key)
                    del self._results[storage_key]

                # Update storage: remove primary from old key, add to unique_name key
                if primary_key != primary.unique_name:
                    del self._results[primary_key]
                    self._results[primary.unique_name] = primary

                LOGGER.debug(f'merged partial entity {unique_name} from {len(partials)} files')
            elif len(partials) == 1:
                # Single partial entity - update storage key from absolute_name to unique_name
                storage_key, entity = partials[0]
                if storage_key != entity.unique_name:
                    del self._results[storage_key]
                    self._results[entity.unique_name] = entity

    def _add_usings_to_result(self, result: FileResult, analysis):
        LOGGER.debug(f'extracting usings from file result {result.scanned_file_name}...')
        list_of_words_with_newline_strings = result.scanned_tokens

        source_string_no_comments = self._filter_source_tokens_without_comments(
            list_of_words_with_newline_strings,
            CSharpParsingKeyword.INLINE_COMMENT.value,
            CSharpParsingKeyword.START_BLOCK_COMMENT.value,
            CSharpParsingKeyword.STOP_BLOCK_COMMENT.value
        )

        filtered_list_no_comments = self.preprocess_file_content_and_generate_token_list(source_string_no_comments)

        for _, obj, following in self._gen_word_read_ahead(filtered_list_no_comments):
            if obj == CSharpParsingKeyword.USING.value:
                read_ahead_string = self.create_read_ahead_string(obj, following)

                using_name = pp.Word(pp.alphanums + CoreParsingKeyword.DOT.value + CoreParsingKeyword.ASTERISK.value)
                expression_to_match = pp.Keyword(CSharpParsingKeyword.USING.value) + \
                    using_name.setResultsName(CoreParsingKeyword.IMPORT_ENTITY_NAME.value) + \
                    pp.FollowedBy(CoreParsingKeyword.SEMICOLON.value)

                try:
                    parsing_result = expression_to_match.parseString(read_ahead_string)
                except pp.ParseException as exception:
                    result.analysis.statistics.increment(Statistics.Key.PARSING_MISSES)
                    LOGGER.warning(f'warning: could not parse result {result=}\n{exception}')
                    LOGGER.warning(f'next tokens: {[obj] + following[:ParsingMixin.Constants.MAX_DEBUG_TOKENS_READAHEAD.value]}')
                    continue

                analysis.statistics.increment(Statistics.Key.PARSING_HITS)

                dependency: str = getattr(parsing_result, CoreParsingKeyword.IMPORT_ENTITY_NAME.value)

                # ignore any dependency substring from the config ignore list
                if self._is_dependency_in_ignore_list(dependency, analysis):
                    LOGGER.debug(f'ignoring dependency from {result.unique_name} to {dependency}')
                else:
                    result.scanned_import_dependencies.append(dependency)
                    LOGGER.debug(f'adding using: {dependency}')

    def _add_namespace_to_result(self, result: FileResult):
        LOGGER.debug(f'extracting namespace from file result {result.scanned_file_name}...')
        list_of_words_with_newline_strings = result.scanned_tokens

        source_string_no_comments = self._filter_source_tokens_without_comments(
            list_of_words_with_newline_strings,
            CSharpParsingKeyword.INLINE_COMMENT.value,
            CSharpParsingKeyword.START_BLOCK_COMMENT.value,
            CSharpParsingKeyword.STOP_BLOCK_COMMENT.value
        )

        filtered_list_no_comments = self.preprocess_file_content_and_generate_token_list(source_string_no_comments)

        for _, obj, following in self._gen_word_read_ahead(filtered_list_no_comments):
            if obj == CSharpParsingKeyword.NAMESPACE.value:
                read_ahead_string = self.create_read_ahead_string(obj, following)

                namespace_name = pp.Word(pp.alphanums + CoreParsingKeyword.DOT.value)
                expression_to_match = pp.Keyword(CSharpParsingKeyword.NAMESPACE.value) + \
                    namespace_name.setResultsName(CSharpParsingKeyword.NAMESPACE_NAME.value) + \
                    (pp.FollowedBy(CoreParsingKeyword.SEMICOLON.value) | pp.FollowedBy(CSharpParsingKeyword.OPEN_SCOPE.value))

                try:
                    parsing_result = expression_to_match.parseString(read_ahead_string)
                except pp.ParseException as exception:
                    result.analysis.statistics.increment(Statistics.Key.PARSING_MISSES)
                    LOGGER.warning(f'warning: could not parse result {result=}\n{exception}')
                    LOGGER.warning(f'next tokens: {obj} {following[:10]}')
                    continue

                result.module_name = parsing_result.namespace_name

                result.analysis.statistics.increment(Statistics.Key.PARSING_HITS)
                LOGGER.debug(f'namespace found: {parsing_result.namespace_name} and added to result')

    def _add_inheritance_to_entity_result(self, result: AbstractEntityResult):
        LOGGER.debug(f'extracting inheritance from entity result {result.entity_name}...')
        list_of_words = result.scanned_tokens

        for _, obj, following in self._gen_word_read_ahead(list_of_words):
            if obj in [CSharpParsingKeyword.CLASS.value, CSharpParsingKeyword.STRUCT.value,
                       CSharpParsingKeyword.INTERFACE.value, CSharpParsingKeyword.RECORD.value]:
                read_ahead_string = self.create_read_ahead_string(obj, following)

                entity_name = pp.Word(pp.alphanums + CoreParsingKeyword.UNDERSCORE.value)

                expression_to_match = (
                    pp.Keyword(CSharpParsingKeyword.CLASS.value) |
                    pp.Keyword(CSharpParsingKeyword.STRUCT.value) |
                    pp.Keyword(CSharpParsingKeyword.INTERFACE.value) |
                    pp.Keyword(CSharpParsingKeyword.RECORD.value)
                ) + \
                    entity_name.setResultsName(CoreParsingKeyword.ENTITY_NAME.value) + \
                    pp.Optional(
                        pp.Keyword(CoreParsingKeyword.COLON.value) +
                        pp.delimitedList(entity_name, delim=',').setResultsName(CoreParsingKeyword.INHERITED_ENTITY_NAME.value)
                    ) + \
                    pp.SkipTo(pp.FollowedBy(CSharpParsingKeyword.OPEN_SCOPE.value))

                try:
                    parsing_result = expression_to_match.parseString(read_ahead_string)
                except pp.ParseException as exception:
                    result.analysis.statistics.increment(Statistics.Key.PARSING_MISSES)
                    LOGGER.warning(f'warning: could not parse result {result=}\n{exception}')
                    LOGGER.warning(f'next tokens: {obj} {following[:10]}')
                    continue

                if len(parsing_result) > 0:
                    inherited_entities = getattr(parsing_result, CoreParsingKeyword.INHERITED_ENTITY_NAME.value, None)

                    if inherited_entities is not None and bool(inherited_entities):
                        result.analysis.statistics.increment(Statistics.Key.PARSING_HITS)

                        # Handle comma-separated inheritance (C# allows class : Base, IInterface1, IInterface2)
                        for inherited_entity in inherited_entities:
                            if inherited_entity and inherited_entity.strip():
                                result.scanned_inheritance_dependencies.append(inherited_entity.strip())
                                LOGGER.debug(
                                    f'found inheritance entity {inherited_entity} ' +
                                    f'for entity name: {getattr(parsing_result, CoreParsingKeyword.ENTITY_NAME.value)} and added to result')


if __name__ == "__main__":
    LEXER = CSharpParser()
    print(f'{LEXER.results=}')
