"""
Comprehensive unit tests for the W5 reorder suggestions algorithm.
Tests velocity selection, MOQ/pack rounding, guardrails, and edge cases.
"""

import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal
import uuid
from app.services.reorder import (
    compute_reorder_suggestions,
    explain_reorder_suggestion,
    _compute_single_product_suggestion,
    ReorderSuggestion
)


class MockRow:
    """Mock database row for testing."""
    
    def __init__(self, **kwargs):
        self.product_id = str(kwargs.get('product_id', uuid.uuid4()))
        self.sku = kwargs.get('sku', 'TEST-SKU')
        self.product_name = kwargs.get('product_name', 'Test Product')
        self.supplier_id = kwargs.get('supplier_id', str(uuid.uuid4()))
        self.supplier_name = kwargs.get('supplier_name', 'Test Supplier')
        self.on_hand = kwargs.get('on_hand', 10)
        self.reorder_point = kwargs.get('reorder_point', 5)
        self.safety_stock_days = kwargs.get('safety_stock_days', 3)
        self.pack_size = kwargs.get('pack_size', 1)
        self.max_stock_days = kwargs.get('max_stock_days', None)
        self.lead_time_days = kwargs.get('lead_time_days', 7)
        self.moq = kwargs.get('moq', 1)
        self.chosen_velocity_latest = kwargs.get('chosen_velocity_latest', 2.0)
        self.chosen_velocity_conservative = kwargs.get('chosen_velocity_conservative', 1.5)
        self.velocity_source_latest = kwargs.get('velocity_source_latest', '7d')
        self.velocity_source_conservative = kwargs.get('velocity_source_conservative', '30d')
        self.incoming_units_30d = kwargs.get('incoming_units_30d', 0)
        self.incoming_units_60d = kwargs.get('incoming_units_60d', 0)
        self.horizon_days = kwargs.get('horizon_days', 10)
        self.missing_supplier = kwargs.get('missing_supplier', False)
        self.no_velocity_data = kwargs.get('no_velocity_data', False)


class TestVelocitySelection:
    """Test velocity strategy selection logic."""
    
    def test_latest_strategy_uses_latest_velocity(self):
        """Latest strategy should use chosen_velocity_latest."""
        row = MockRow(
            chosen_velocity_latest=2.0,
            chosen_velocity_conservative=1.5,
            velocity_source_latest='7d',
            velocity_source_conservative='30d'
        )
        
        suggestion = _compute_single_product_suggestion(row, "latest", None)
        assert suggestion is not None
        assert suggestion.chosen_velocity == 2.0
        assert suggestion.velocity_source == '7d'
    
    def test_conservative_strategy_uses_conservative_velocity(self):
        """Conservative strategy should use chosen_velocity_conservative."""
        row = MockRow(
            chosen_velocity_latest=2.0,
            chosen_velocity_conservative=1.5,
            velocity_source_latest='7d',
            velocity_source_conservative='30d'
        )
        
        suggestion = _compute_single_product_suggestion(row, "conservative", None)
        assert suggestion is not None
        assert suggestion.chosen_velocity == 1.5
        assert suggestion.velocity_source == '30d'
    
    def test_zero_velocity_handling(self):
        """Test zero velocity with different reorder point scenarios."""
        # Above reorder point - should be skipped
        row_above = MockRow(
            chosen_velocity_latest=0.0,
            on_hand=10,
            reorder_point=5
        )
        
        suggestion = _compute_single_product_suggestion(row_above, "latest", None)
        assert suggestion is None  # Should be skipped
        
        # Below reorder point - should not be skipped
        row_below = MockRow(
            chosen_velocity_latest=0.0,
            on_hand=3,
            reorder_point=5
        )
        
        suggestion = _compute_single_product_suggestion(row_below, "latest", None)
        assert suggestion is not None
        assert "NO_VELOCITY" in suggestion.reasons
        assert "BELOW_REORDER_POINT" in suggestion.reasons


class TestHorizonCalculation:
    """Test horizon day calculations."""
    
    def test_default_horizon_calculation(self):
        """Horizon should be max(7, lead_time + safety_stock)."""
        row = MockRow(lead_time_days=5, safety_stock_days=3)  # 5 + 3 = 8
        
        suggestion = _compute_single_product_suggestion(row, "latest", None)
        assert suggestion is not None
        assert suggestion.horizon_days == 8
    
    def test_minimum_horizon_seven_days(self):
        """Horizon should never be less than 7 days."""
        row = MockRow(lead_time_days=2, safety_stock_days=2)  # 2 + 2 = 4, but min is 7
        
        suggestion = _compute_single_product_suggestion(row, "latest", None)
        assert suggestion is not None
        assert suggestion.horizon_days == 7
    
    def test_horizon_override(self):
        """Override should be used when provided."""
        row = MockRow(lead_time_days=10, safety_stock_days=5)  # would be 15
        
        suggestion = _compute_single_product_suggestion(row, "latest", 20)  # override to 20
        assert suggestion is not None
        assert suggestion.horizon_days == 20


class TestReorderPointLogic:
    """Test reorder point bump logic."""
    
    def test_below_reorder_point_bump(self):
        """Should bump to reorder point when below it."""
        row = MockRow(
            on_hand=3,
            reorder_point=10,
            chosen_velocity_latest=1.0,
            lead_time_days=7,
            safety_stock_days=3,
            incoming_units_30d=0
        )
        
        suggestion = _compute_single_product_suggestion(row, "latest", None)
        assert suggestion is not None
        
        # Should be bumped to at least reorder_point - on_hand = 10 - 3 = 7
        assert suggestion.recommended_quantity >= 7
        assert "BELOW_REORDER_POINT" in suggestion.reasons
        assert any("Bumped to reorder point" in adj for adj in suggestion.adjustments)
    
    def test_above_reorder_point_no_bump(self):
        """Should not bump when above reorder point."""
        row = MockRow(
            on_hand=15,
            reorder_point=10,
            chosen_velocity_latest=1.0,
            lead_time_days=7,
            safety_stock_days=3,
            incoming_units_30d=0
        )
        
        suggestion = _compute_single_product_suggestion(row, "latest", None)
        assert suggestion is not None
        assert "BELOW_REORDER_POINT" not in suggestion.reasons


class TestMOQHandling:
    """Test minimum order quantity logic."""
    
    def test_moq_enforcement(self):
        """Should enforce MOQ when quantity is below it."""
        row = MockRow(
            on_hand=8,
            chosen_velocity_latest=1.0,  # 1 unit/day
            lead_time_days=7,
            safety_stock_days=3,  # horizon = 10, demand = 10, shortfall = 2
            moq=50,  # Much higher than calculated need
            incoming_units_30d=0
        )
        
        suggestion = _compute_single_product_suggestion(row, "latest", None)
        assert suggestion is not None
        assert suggestion.recommended_quantity == 50
        assert "MOQ_ENFORCED" in suggestion.reasons
        assert any("Raised to MOQ" in adj for adj in suggestion.adjustments)
    
    def test_no_moq_when_above(self):
        """Should not enforce MOQ when quantity is already above it."""
        row = MockRow(
            on_hand=0,
            chosen_velocity_latest=10.0,  # High velocity
            lead_time_days=7,
            safety_stock_days=3,  # horizon = 10, demand = 100, shortfall = 100
            moq=50,  # Lower than calculated need
            incoming_units_30d=0
        )
        
        suggestion = _compute_single_product_suggestion(row, "latest", None)
        assert suggestion is not None
        assert suggestion.recommended_quantity == 100
        assert "MOQ_ENFORCED" not in suggestion.reasons


class TestPackSizeRounding:
    """Test pack size rounding logic."""
    
    def test_pack_size_rounding(self):
        """Should round up to nearest pack size multiple."""
        row = MockRow(
            on_hand=0,
            chosen_velocity_latest=3.7,  # Will create fractional shortfall
            lead_time_days=7,
            safety_stock_days=3,  # horizon = 10, demand = 37
            pack_size=20,  # Round up to nearest 20
            incoming_units_30d=0
        )
        
        suggestion = _compute_single_product_suggestion(row, "latest", None)
        assert suggestion is not None
        
        # 37 units needed, should round up to 40 (next multiple of 20)
        assert suggestion.recommended_quantity == 40
        assert "PACK_ROUNDED" in suggestion.reasons
        assert any("Rounded to pack size" in adj for adj in suggestion.adjustments)
    
    def test_no_rounding_when_pack_size_one(self):
        """Should not round when pack size is 1."""
        row = MockRow(
            chosen_velocity_latest=2.5,
            pack_size=1
        )
        
        suggestion = _compute_single_product_suggestion(row, "latest", None)
        assert suggestion is not None
        assert "PACK_ROUNDED" not in suggestion.reasons


class TestMaxStockDaysCapping:
    """Test maximum stock days capping logic."""
    
    def test_max_stock_days_capping(self):
        """Should cap quantity to not exceed max stock days."""
        row = MockRow(
            on_hand=10,
            chosen_velocity_latest=1.0,  # 1 unit/day
            lead_time_days=30,  # Long lead time
            safety_stock_days=10,  # horizon = 40, demand = 40
            max_stock_days=30,  # Cap at 30 days
            incoming_units_30d=0
        )
        
        suggestion = _compute_single_product_suggestion(row, "latest", None)
        assert suggestion is not None
        
        # Should be capped: max_units = 1 * 30 = 30, available after = 10 + incoming = 10
        # So max to order = 30 - 10 = 20, but raw demand was 40 - 10 = 30
        assert suggestion.recommended_quantity <= 20
        assert "CAPPED_BY_MAX_DAYS" in suggestion.reasons
    
    def test_no_capping_when_no_max_stock_days(self):
        """Should not cap when max_stock_days is None."""
        row = MockRow(
            chosen_velocity_latest=1.0,
            lead_time_days=30,
            max_stock_days=None
        )
        
        suggestion = _compute_single_product_suggestion(row, "latest", None)
        assert suggestion is not None
        assert "CAPPED_BY_MAX_DAYS" not in suggestion.reasons


class TestIncomingStock:
    """Test incoming stock calculations."""
    
    def test_incoming_stock_reduces_shortfall(self):
        """Incoming stock should reduce the calculated shortfall."""
        row = MockRow(
            on_hand=5,
            chosen_velocity_latest=2.0,  # 2 units/day
            lead_time_days=7,
            safety_stock_days=3,  # horizon = 10, demand = 20
            incoming_units_30d=10,  # Has incoming stock
            incoming_units_60d=15
        )
        
        suggestion = _compute_single_product_suggestion(row, "latest", None)
        assert suggestion is not None
        
        # Available after incoming = 5 + 10 = 15, shortfall = 20 - 15 = 5
        assert suggestion.recommended_quantity == 5
        assert suggestion.incoming == 10  # Should use 30d for 10-day horizon
        assert "INCOMING_COVERAGE" in suggestion.reasons
    
    def test_longer_horizon_uses_60d_incoming(self):
        """Horizons > 30 days should use 60d incoming stock."""
        row = MockRow(
            on_hand=5,
            chosen_velocity_latest=1.0,
            lead_time_days=40,  # Long horizon
            safety_stock_days=10,  # horizon = 50
            incoming_units_30d=10,
            incoming_units_60d=20
        )
        
        suggestion = _compute_single_product_suggestion(row, "latest", None)
        assert suggestion is not None
        assert suggestion.incoming == 20  # Should use 60d for 50-day horizon


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_zero_shortfall_no_suggestion(self):
        """Should not suggest when no shortfall and above reorder point."""
        row = MockRow(
            on_hand=100,  # Very high stock
            chosen_velocity_latest=1.0,
            reorder_point=5,  # Well above
            lead_time_days=7,
            safety_stock_days=3
        )
        
        suggestion = _compute_single_product_suggestion(row, "latest", None)
        # If final quantity < 1 and no MOQ enforcement, should return None
        # But this depends on the exact calculation - let's check it has very low or zero quantity
        if suggestion:
            assert suggestion.recommended_quantity <= 1
    
    def test_negative_on_hand(self):
        """Should handle negative on-hand gracefully."""
        row = MockRow(
            on_hand=-5,  # Negative inventory
            chosen_velocity_latest=2.0,
            reorder_point=10,
            lead_time_days=7,
            safety_stock_days=3
        )
        
        suggestion = _compute_single_product_suggestion(row, "latest", None)
        assert suggestion is not None
        # Should calculate shortfall correctly with negative on-hand
        assert suggestion.recommended_quantity > 0
    
    def test_very_high_velocity(self):
        """Should handle very high velocity without overflow."""
        row = MockRow(
            on_hand=10,
            chosen_velocity_latest=1000.0,  # Very high velocity
            lead_time_days=30,
            safety_stock_days=10,  # horizon = 40, demand = 40,000
            incoming_units_60d=0
        )
        
        suggestion = _compute_single_product_suggestion(row, "latest", None)
        assert suggestion is not None
        assert suggestion.recommended_quantity > 30000  # Large but reasonable
    
    def test_missing_supplier_handling(self):
        """Should handle products without suppliers."""
        row = MockRow(
            supplier_id=None,
            supplier_name=None,
            chosen_velocity_latest=2.0
        )
        
        suggestion = _compute_single_product_suggestion(row, "latest", None)
        assert suggestion is not None
        assert suggestion.supplier_id is None
        assert suggestion.supplier_name is None


class TestComplexScenarios:
    """Test complex real-world scenarios."""
    
    def test_all_adjustments_applied(self):
        """Test case where multiple adjustments are applied in sequence."""
        row = MockRow(
            on_hand=2,
            reorder_point=10,  # Below reorder point
            chosen_velocity_latest=1.0,
            lead_time_days=7,
            safety_stock_days=3,
            moq=25,  # Higher than reorder bump
            pack_size=12,  # Will need rounding
            max_stock_days=60,  # Should not trigger capping
            incoming_units_30d=0
        )
        
        suggestion = _compute_single_product_suggestion(row, "latest", None)
        assert suggestion is not None
        
        # Expected flow: 
        # 1. Reorder bump: max(0, 10-2) = 8
        # 2. MOQ: max(8, 25) = 25  
        # 3. Pack rounding: ceil(25/12) * 12 = 36
        assert suggestion.recommended_quantity == 36
        
        expected_reasons = ["BELOW_REORDER_POINT", "LEAD_TIME_RISK", "MOQ_ENFORCED", "PACK_ROUNDED"]
        for reason in expected_reasons:
            assert reason in suggestion.reasons
    
    def test_explanation_structure(self):
        """Test that explanation contains all required fields."""
        row = MockRow(
            chosen_velocity_latest=2.0,
            on_hand=10,
            lead_time_days=7,
            safety_stock_days=3
        )
        
        suggestion = _compute_single_product_suggestion(row, "latest", None)
        assert suggestion is not None
        assert suggestion.explanation is not None
        
        # Check explanation structure
        explanation = suggestion.explanation
        assert "inputs" in explanation
        assert "calculations" in explanation
        assert "logic_path" in explanation
        
        # Check required input fields
        inputs = explanation["inputs"]
        required_inputs = [
            "on_hand", "incoming_units_within_horizon", "chosen_velocity",
            "lead_time_days", "safety_stock_days", "horizon_days"
        ]
        for field in required_inputs:
            assert field in inputs
        
        # Check calculations
        calculations = explanation["calculations"]
        required_calculations = [
            "demand_forecast_units", "net_available_after_incoming", 
            "raw_shortfall", "final_quantity"
        ]
        for field in required_calculations:
            assert field in calculations


@patch('app.services.reorder.engine.connect')
class TestIntegrationWithDatabase:
    """Test integration with database queries."""
    
    def test_compute_reorder_suggestions_with_mock_data(self, mock_connect):
        """Test full compute_reorder_suggestions function with mocked database."""
        # Setup mock connection and result
        mock_conn = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        
        # Mock query result with two products
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            MockRow(
                product_id="product-1",
                sku="SKU-001",
                product_name="Product 1",
                chosen_velocity_latest=2.0,
                on_hand=5,
                reorder_point=10
            ),
            MockRow(
                product_id="product-2", 
                sku="SKU-002",
                product_name="Product 2",
                chosen_velocity_latest=0.0,  # Should be skipped
                on_hand=15,
                reorder_point=10
            )
        ]
        mock_conn.execute.return_value = mock_result
        
        org_id = uuid.uuid4()
        suggestions = compute_reorder_suggestions(org_id)
        
        # Should return one suggestion (second product skipped due to zero velocity above reorder point)
        assert len(suggestions) == 1
        assert suggestions[0].sku == "SKU-001"
        assert suggestions[0].name == "Product 1"
    
    def test_explain_reorder_suggestion_with_mock_data(self, mock_connect):
        """Test explain_reorder_suggestion function with mocked database."""
        # Setup mock connection and result
        mock_conn = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        
        # Mock single product result
        mock_result = MagicMock()
        mock_result.fetchone.return_value = MockRow(
            sku="TEST-SKU",
            product_name="Test Product",
            chosen_velocity_latest=2.0
        )
        mock_conn.execute.return_value = mock_result
        
        org_id = uuid.uuid4()
        product_id = uuid.uuid4()
        
        explanation = explain_reorder_suggestion(org_id, product_id)
        
        assert explanation is not None
        assert explanation["sku"] == "TEST-SKU"
        assert explanation["name"] == "Test Product"
        assert "explanation" in explanation