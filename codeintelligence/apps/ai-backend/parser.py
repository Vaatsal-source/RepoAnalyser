import os
from tree_sitter import Language, Parser

# 1. SETUP THE LANGUAGE GRAMMAR
# Tree-sitter requires language-specific shared libraries to parse syntax trees.
# We will download and build the JavaScript parser grammar dynamically.
import tree_sitter_javascript as tsjavascript

JS_LANGUAGE = Language(tsjavascript.language(), "javascript")

class CodeParser:
    def __init__(self):
        self.parser = Parser()
        self.parser.set_language(JS_LANGUAGE)

    def parse_code_file(self, file_content):
        """Parses source code string and extracts structured symbol-level code blocks."""
        tree = self.parser.parse(bytes(file_content, "utf8"))
        root_node = tree.root_node
        
        symbols = []
        self._traverse_tree(root_node, file_content, symbols)
        return symbols

    def _traverse_tree(self, node, original_code, symbols):
        """Recursively walks the Abstract Syntax Tree (AST) to harvest specific symbols."""
        
        # Target important JavaScript structural architectural components
        target_types = {
            'function_declaration': 'function',
            'arrow_function': 'function',
            'class_declaration': 'class',
            'lexical_declaration': 'variable/constant', # Catching exported functions/components
            'import_statement': 'import'
        }

        if node.type in target_types:
            # Safely slice the exact byte range out of the original code file
            start_byte = node.start_byte
            end_byte = node.end_byte
            code_snippet = original_code[start_byte:end_byte]
            
            # Extract names for better structural grouping where possible
            name = "anonymous"
            if node.type == 'function_declaration' or node.type == 'class_declaration':
                # Child nodes usually hold the identifier name
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = original_code[name_node.start_byte:name_node.end_byte]

            symbols.append({
                "type": target_types[node.type],
                "name": name,
                "ast_type": node.type,
                "content": code_snippet,
                "start_line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1
            })

        # Keep walking deep down into children nodes recursively
        for child in node.children:
            self._traverse_tree(child, original_code, symbols)