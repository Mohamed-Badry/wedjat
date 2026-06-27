import ast
import sys

def summarize_ast(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())
    
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            print(f"Function: {node.name}")
        elif isinstance(node, ast.ClassDef):
            print(f"Class: {node.name}")

summarize_ast('other_components/uwe4-orbit-decay-ai/Untitled2.py')
