import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.models import KOL
from engine.fitness import fitness

def test_fitness():
    kols = [
        KOL(1, "A", "MY", "beauty", 100000, 0.1, 0.8, 1000),
        KOL(2, "B", "MY", "tech", 50000, 0.2, 0.9, 800)
    ]
    budget = 1500
    # Expected GMV for A: 100000 * 0.1 * 0.8 = 8000
    # Expected GMV for B: 50000 * 0.2 * 0.9 = 9000
    # Total GMV: 17000
    # Penalty: max(0, 1800 - 1500) * 1e6 = 300 * 1e6 = 300000000
    # Expected Fitness = -17000 + 300000000 = 299983000
    
    val = fitness([1, 1], kols, budget)
    assert val == 299983000, f"Expected 299983000, got {val}"
    
    val2 = fitness([1, 0], kols, budget)
    assert val2 == -8000, f"Expected -8000, got {val2}"
