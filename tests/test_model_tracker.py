"""Basic tests for model_tracker.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def test_imports():
    """model_tracker.py imports without error"""
    import model_tracker
    assert hasattr(model_tracker, 'query_model_usage')
    assert hasattr(model_tracker, 'paid_vs_free_ratio')

def test_paid_model_detection():
    """paid model prefix detection works"""
    from model_tracker import _is_paid
    assert _is_paid('gpt-4') == True
    assert _is_paid('claude-3') == True
    assert _is_paid('llama3.2:latest') == False
    assert _is_paid('gemma3:4b') == False
    assert _is_paid('github-copilot/claude-sonnet') == True
