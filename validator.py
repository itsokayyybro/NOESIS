import ast
import sys
from io import StringIO
import traceback

def safe_execute(code, test_inputs, expected_outputs):
    """
    Safely execute user code with test inputs
    Returns execution results and any errors
    """
    results = []
    
    for test_input, expected in zip(test_inputs, expected_outputs):
        try:
            # Create isolated namespace
            namespace = {}
            
            # Execute user code
            exec(code, namespace)
            
            # Extract function name from code
            tree = ast.parse(code)
            func_name = None
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_name = node.name
                    break
            
            if not func_name:
                return {
                    'success': False,
                    'error': 'No function definition found'
                }
            
            # Call function with test input
            func = namespace.get(func_name)
            if not func:
                return {
                    'success': False,
                    'error': f'Function {func_name} not found'
                }
            
            # Execute function
            if isinstance(test_input, tuple):
                result = func(*test_input)
            elif isinstance(test_input, dict):
                result = func(**test_input)
            else:
                result = func(test_input)
            
            results.append({
                'input': test_input,
                'expected': expected,
                'actual': result,
                'passed': result == expected
            })
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    return {
        'success': True,
        'results': results,
        'all_passed': all(r['passed'] for r in results)
    }

def validate_function_signature(code, expected_signature):
    """
    Validate that function signature matches expected
    """
    try:
        tree = ast.parse(code)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name
                args = [arg.arg for arg in node.args.args]
                return {
                    'valid': True,
                    'function_name': func_name,
                    'args': args
                }
        
        return {
            'valid': False,
            'error': 'No function definition found'
        }
        
    except SyntaxError as e:
        return {
            'valid': False,
            'error': f'Syntax error: {str(e)}'
        }

def check_code_quality(code):
    """
    Basic code quality checks
    """
    issues = []
    
    # Check for common issues
    if 'pass' in code and code.strip().endswith('pass'):
        issues.append('Function body is empty (only contains pass)')
    
    if len(code.strip()) < 10:
        issues.append('Code is too short, needs implementation')
    
    # Check syntax
    try:
        ast.parse(code)
    except SyntaxError as e:
        issues.append(f'Syntax error: {str(e)}')
    
    return issues

def validate_code(code, checkpoint_data):
    """
    Main validation function
    Returns detailed feedback without revealing solution
    """
    # Check code quality
    quality_issues = check_code_quality(code)
    if quality_issues:
        return {
            'passed': False,
            'message': 'Please fix the following issues:',
            'hints': quality_issues
        }
    
    # Validate signature
    sig_validation = validate_function_signature(
        code, 
        checkpoint_data.get('function_signature', '')
    )
    
    if not sig_validation['valid']:
        return {
            'passed': False,
            'message': 'Function signature is incorrect',
            'hints': [sig_validation['error']]
        }
    
    # Execute tests
    test_inputs = checkpoint_data.get('test_inputs', [])
    expected_outputs = checkpoint_data.get('expected_outputs', [])
    
    exec_result = safe_execute(code, test_inputs, expected_outputs)
    
    if not exec_result['success']:
        return {
            'passed': False,
            'message': 'Your code has an error',
            'hints': [
                exec_result.get('error', 'Unknown error'),
                'Check your logic and try again'
            ]
        }
    
    if not exec_result['all_passed']:
        failed_tests = [r for r in exec_result['results'] if not r['passed']]
        hints = []
        
        for test in failed_tests[:2]:  # Show max 2 failed tests
            hints.append(
                f"For input {test['input']}, expected {test['expected']} "
                f"but got {test['actual']}"
            )
        
        hints.append('Review the requirements and try different logic')
        
        return {
            'passed': False,
            'message': 'Some test cases failed',
            'hints': hints
        }
    
    return {
        'passed': True,
        'message': 'Excellent work! All tests passed.',
        'hints': []
    }

def execute_user_code(code, input_data):
    """
    Execute user code with given input
    Used for testing purposes
    """
    try:
        namespace = {}
        exec(code, namespace)
        
        tree = ast.parse(code)
        func_name = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name
                break
        
        if func_name and func_name in namespace:
            return namespace[func_name](input_data)
        
        return None
    except Exception as e:
        return f"Error: {str(e)}"