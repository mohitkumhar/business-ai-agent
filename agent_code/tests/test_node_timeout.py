import pytest
from agent_code.utils.node_timeout import run_with_timeout

def fast_function():
return "success"

def slow_function():
import time
time.sleep(2)
return "slow result"

def test_run_with_timeout_success():
"""Function completes within timeout"""
result = run_with_timeout(fast_function, timeout_seconds=5)
assert result == "success"

def test_run_with_timeout_default_success():
"""Default timeout should also work for fast function"""
result = run_with_timeout(fast_function)
assert result == "success"

def test_run_with_timeout_failure():
"""Function exceeding timeout should raise TimeoutError"""
with pytest.raises(TimeoutError):
run_with_timeout(slow_function, timeout_seconds=0.5)
