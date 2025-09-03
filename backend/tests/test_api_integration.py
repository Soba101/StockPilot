"""
Integration tests for StockPilot API CRUD operations
Tests against real PostgreSQL database to ensure everything works
"""

import pytest
import uuid
from datetime import datetime, timedelta
import requests
import time
import json

from app.core.security import create_access_token

# Base URL for API
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

# Test organization and user (from populated database)
TEST_ORG_ID = "6bee7759-b4fa-41ec-80e9-59adf86ed171"  # Demo Company
TEST_USER_ID = "7ddac2fe-abf7-441f-83c2-0848c54cdbbd"  # admin@demo.co

# Skip entire module if API server not running (so unit tests can still pass)
try:
    requests.get(f"{BASE_URL}/docs", timeout=1)
except Exception:  # pragma: no cover - skip path
    pytest.skip("API server is not running; skipping live integration tests.", allow_module_level=True)

@pytest.fixture(scope="session")
def auth_headers():
    """Create authentication headers for API requests"""
    token = create_access_token(
        sub=TEST_USER_ID,
        org_id=TEST_ORG_ID,
        role="admin"
    )
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

class TestProductCRUDIntegration:
    """Integration tests for Product CRUD operations"""
    
    def test_create_product_success(self, auth_headers):
        """Test successful product creation"""
        unique_sku = f"INT-TEST-{int(time.time())}"
        
        product_data = {
            "org_id": TEST_ORG_ID,
            "sku": unique_sku,
            "name": "Integration Test Product",
            "description": "A test product for integration testing",
            "category": "Integration Tests",
            "cost": 25.99,
            "price": 49.99,
            "uom": "each",
            "reorder_point": 30
        }
        
        response = requests.post(f"{API_BASE}/products/", 
                               json=product_data, 
                               headers=auth_headers)
        
        assert response.status_code == 200
        created_product = response.json()
        
        # Verify all fields
        assert created_product["sku"] == unique_sku
        assert created_product["name"] == product_data["name"]
        assert float(created_product["cost"]) == product_data["cost"]
        assert float(created_product["price"]) == product_data["price"]
        assert "id" in created_product
        
        return created_product["id"]  # Return for cleanup

    def test_get_products_list(self, auth_headers):
        """Test retrieving products list"""
        response = requests.get(f"{API_BASE}/products/", headers=auth_headers)
        
        assert response.status_code == 200
        products = response.json()
        
        assert isinstance(products, list)
        assert len(products) > 0  # Should have products from populated data
        
        # Verify structure
        for product in products[:3]:  # Check first 3
            assert "id" in product
            assert "sku" in product
            assert "name" in product
            assert "org_id" in product

    def test_update_product(self, auth_headers):
        """Test updating a product"""
        # First create a product to update
        unique_sku = f"UPD-TEST-{int(time.time())}"
        
        product_data = {
            "org_id": TEST_ORG_ID,
            "sku": unique_sku,
            "name": "Product to Update",
            "price": 19.99
        }
        
        create_response = requests.post(f"{API_BASE}/products/", 
                                      json=product_data, 
                                      headers=auth_headers)
        assert create_response.status_code == 200
        product_id = create_response.json()["id"]
        
        # Update the product
        update_data = {
            "name": "Updated Product Name",
            "price": 29.99,
            "description": "Updated description"
        }
        
        update_response = requests.put(f"{API_BASE}/products/{product_id}", 
                                     json=update_data, 
                                     headers=auth_headers)
        
        assert update_response.status_code == 200
        updated_product = update_response.json()
        
        assert updated_product["name"] == update_data["name"]
        assert float(updated_product["price"]) == update_data["price"]
        assert updated_product["description"] == update_data["description"]
        assert updated_product["sku"] == unique_sku  # Should not change


class TestChatUnifiedIntegration:
    def test_chat2_open_basic(self, auth_headers):
        """Minimal smoke test for /chat2/query OPEN path.
        Skips gracefully if feature flag is off or server not running.
        """
        import os
        # Ensure feature flag is on for this test context
        if os.getenv("HYBRID_CHAT_ENABLED", "0") not in ("1", "true", "True"):  # pragma: no cover - skip path
            pytest.skip("HYBRID_CHAT_ENABLED is off; skipping chat2 integration test")

        payload = {"message": "hello there"}
        r = requests.post(f"{API_BASE}/chat2/query", json=payload, headers=auth_headers, timeout=10)
        assert r.status_code in (200, 503, 500)
        if r.status_code == 200:
            body = r.json()
            # Expect unified contract fields (route, answer, provenance, confidence, follow_ups)
            assert isinstance(body, dict)
            assert body.get("route") in ("OPEN", "RAG", "NO_ANSWER")
            assert "answer" in body
            assert "provenance" in body
            assert "confidence" in body
            assert "follow_ups" in body

class TestInventoryOperationsIntegration:
    """Integration tests for Inventory operations"""
    
    def test_create_inventory_movement(self, auth_headers):
        """Test creating inventory movement"""
        # Get a product from existing data
        products_response = requests.get(f"{API_BASE}/products/", headers=auth_headers)
        assert products_response.status_code == 200
        products = products_response.json()
        assert len(products) > 0
        test_product = products[0]
        
        # Get a location from existing data
        locations_response = requests.get(f"{API_BASE}/locations/", headers=auth_headers)
        assert locations_response.status_code == 200
        locations = locations_response.json()
        assert len(locations) > 0
        test_location = locations[0]
        
        # Create inventory movement
        movement_data = {
            "product_id": test_product["id"],
            "location_id": test_location["id"],
            "quantity": 25,
            "movement_type": "adjust",
            "reference": f"INT-TEST-{int(time.time())}",
            "notes": "Integration test stock adjustment",
            "timestamp": datetime.now().isoformat()
        }
        
        response = requests.post(f"{API_BASE}/inventory/movements", 
                               json=movement_data, 
                               headers=auth_headers)
        
        assert response.status_code == 200
        movement = response.json()
        
        assert movement["product_id"] == movement_data["product_id"]
        assert movement["location_id"] == movement_data["location_id"]
        assert movement["quantity"] == movement_data["quantity"]

class TestAnalyticsExtensionsIntegration:
    def test_stockout_risk_latest_and_conservative(self, auth_headers):
        r1 = requests.get(f"{API_BASE}/analytics/stockout-risk?velocity_strategy=latest", headers=auth_headers)
        assert r1.status_code == 200
        data1 = r1.json()
        if data1:
            assert "velocity_source" in data1[0]

        r2 = requests.get(f"{API_BASE}/analytics/stockout-risk?velocity_strategy=conservative", headers=auth_headers)
        assert r2.status_code == 200
        data2 = r2.json()
        if data2:
            assert "velocity_source" in data2[0]

    def test_internal_run_daily_alerts_auth(self):
        # Missing token
        r_fail = requests.post(f"{API_BASE}/internal/run-daily-alerts")
        assert r_fail.status_code == 401
        import os
        token_val = os.getenv("ALERT_CRON_TOKEN", "dev-cron-token")
        r_ok = requests.post(f"{API_BASE}/internal/run-daily-alerts", headers={"Authorization": f"Bearer {token_val}"})
        assert r_ok.status_code in (200, 207)
        body_resp = r_ok.json()
        assert "date" in body_resp and "already_ran" in body_resp

    def test_get_inventory_summary(self, auth_headers):
        """Test getting inventory summary"""
        response = requests.get(f"{API_BASE}/inventory/summary", headers=auth_headers)
        
        assert response.status_code == 200
        summary = response.json()
        
        # Verify expected fields
        expected_fields = ["total_products", "total_stock_value", "low_stock_count", "out_of_stock_count"]
        for field in expected_fields:
            assert field in summary
            assert isinstance(summary[field], (int, float))

    def test_week_in_review_report(self, auth_headers):
        """Test week in review report endpoint returns expected structure and does not error when marts empty."""
        r = requests.get(f"{API_BASE}/reports/week-in-review", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        # Core sections
        for key in ["report_id", "generated_at", "period", "top_products", "inventory_alerts", "channel_insights", "key_insights", "recommendations", "summary"]:
            assert key in data
        # Arrays present
        assert isinstance(data["top_products"], list)
        assert isinstance(data["channel_insights"], list)
        # Period subfields
        for sub in ["total_revenue", "total_units", "total_orders", "gross_margin", "margin_percent"]:
            assert sub in data["period"]

class TestPurchasingIntegration:
    """Integration tests for Purchasing operations"""
    
    def test_get_purchase_orders(self, auth_headers):
        """Test getting purchase orders list"""
        response = requests.get(f"{API_BASE}/purchasing/purchase-orders", headers=auth_headers)
        
        assert response.status_code == 200
        purchase_orders = response.json()
        
        assert isinstance(purchase_orders, list)
        # Should have POs from populated data
        if len(purchase_orders) > 0:
            po = purchase_orders[0]
            expected_fields = ["id", "po_number", "supplier_name", "status", "total_amount"]
            for field in expected_fields:
                assert field in po

    def test_create_purchase_order(self, auth_headers):
        """Test creating a purchase order"""
        # Get a supplier
        # First we need to check if we have suppliers (we should from populated data)
        
        # Get products for PO items
        products_response = requests.get(f"{API_BASE}/products/", headers=auth_headers)
        assert products_response.status_code == 200
        products = products_response.json()
        assert len(products) > 0
        test_product = products[0]
        
        # For this test, we'll use a known supplier ID from our populated data
        # This is the Global Electronics Ltd supplier ID
        supplier_id = None
        
        # Try to get existing POs to find a supplier ID
        existing_pos_response = requests.get(f"{API_BASE}/purchasing/purchase-orders", headers=auth_headers)
        if existing_pos_response.status_code == 200:
            existing_pos = existing_pos_response.json()
            if len(existing_pos) > 0:
                # Get supplier from existing PO
                po_detail_response = requests.get(f"{API_BASE}/purchasing/purchase-orders/{existing_pos[0]['id']}", 
                                                headers=auth_headers)
                if po_detail_response.status_code == 200:
                    supplier_id = po_detail_response.json()["supplier_id"]
        
        if not supplier_id:
            pytest.skip("No supplier found in test data")
        
        # Create purchase order  
        po_data = {
            "supplier_id": supplier_id,
            "po_number": f"TEST-PO-{int(time.time())}",
            "expected_date": (datetime.now() + timedelta(days=21)).isoformat(),
            "notes": "Integration test purchase order",
            "items": [
                {
                    "product_id": test_product["id"],
                    "quantity": 50,
                    "unit_cost": float(test_product.get("cost", 15.0))
                }
            ]
        }
        
        response = requests.post(f"{API_BASE}/purchasing/purchase-orders", 
                               json=po_data, 
                               headers=auth_headers)
        
        assert response.status_code == 200
        created_po = response.json()
        
        assert created_po["supplier_id"] == supplier_id
        assert created_po["status"] == "draft"
        assert len(created_po["items"]) == 1
        assert "po_number" in created_po

class TestAnalyticsIntegration:
    """Integration tests for Analytics endpoints"""
    
    def test_get_analytics_data(self, auth_headers):
        """Test getting analytics data"""
        response = requests.get(f"{API_BASE}/analytics?days=30", headers=auth_headers)
        
        assert response.status_code == 200
        analytics = response.json()
        
        # Verify expected structure
        expected_sections = ["sales_metrics", "top_products", "category_data", "recent_sales", "revenue_trend"]
        for section in expected_sections:
            assert section in analytics
        
        # Verify sales metrics structure
        sales_metrics = analytics["sales_metrics"]
        expected_metrics = ["total_revenue", "total_units", "avg_order_value", "total_orders"]
        for metric in expected_metrics:
            assert metric in sales_metrics
            assert isinstance(sales_metrics[metric], (int, float))

class TestStockTransferIntegration:
    """Integration tests for Stock Transfer operations"""
    
    def test_stock_transfer_success(self, auth_headers):
        """Test successful stock transfer between locations"""
        # Get products and locations from existing data
        products_response = requests.get(f"{API_BASE}/products/", headers=auth_headers)
        assert products_response.status_code == 200
        products = products_response.json()
        assert len(products) > 0
        test_product = products[0]
        
        locations_response = requests.get(f"{API_BASE}/locations/", headers=auth_headers)
        assert locations_response.status_code == 200
        locations = locations_response.json()
        assert len(locations) >= 2  # Need at least 2 locations for transfer
        from_location = locations[0]
        to_location = locations[1]
        
        # First, ensure we have stock in the from_location by creating an 'in' movement
        stock_in_data = {
            "product_id": test_product["id"],
            "location_id": from_location["id"],
            "quantity": 100,
            "movement_type": "in",
            "reference": f"STOCK-IN-{int(time.time())}",
            "notes": "Adding stock for transfer test",
            "timestamp": datetime.now().isoformat()
        }
        
        stock_response = requests.post(f"{API_BASE}/inventory/movements", 
                                     json=stock_in_data, 
                                     headers=auth_headers)
        assert stock_response.status_code == 200
        
        # Now test the transfer
        transfer_data = {
            "product_id": test_product["id"],
            "from_location_id": from_location["id"],
            "to_location_id": to_location["id"],
            "quantity": 25,
            "reference": f"TEST-TRANSFER-{int(time.time())}",
            "notes": "Integration test stock transfer"
        }
        
        response = requests.post(f"{API_BASE}/inventory/transfer", 
                               json=transfer_data, 
                               headers=auth_headers)
        
        assert response.status_code == 200
        movements = response.json()
        
        # Should return 2 movements (out from source, in to destination)
        assert len(movements) == 2
        
        # Verify the transfer movements
        out_movement = next(m for m in movements if m["movement_type"] == "transfer")
        in_movement = next(m for m in movements if m["movement_type"] == "in")
        
        # Check out movement
        assert out_movement["product_id"] == test_product["id"]
        assert out_movement["location_id"] == from_location["id"]
        assert out_movement["quantity"] == 25
        assert "TEST-TRANSFER" in out_movement["reference"]
        
        # Check in movement  
        assert in_movement["product_id"] == test_product["id"]
        assert in_movement["location_id"] == to_location["id"]
        assert in_movement["quantity"] == 25
        assert "TEST-TRANSFER" in in_movement["reference"]
        
    def test_stock_transfer_insufficient_stock(self, auth_headers):
        """Test transfer fails when insufficient stock available"""
        # Get products and locations
        products_response = requests.get(f"{API_BASE}/products/", headers=auth_headers)
        assert products_response.status_code == 200
        products = products_response.json()
        test_product = products[0]
        
        locations_response = requests.get(f"{API_BASE}/locations/", headers=auth_headers)
        assert locations_response.status_code == 200
        locations = locations_response.json()
        from_location = locations[0]
        to_location = locations[1]
        
        # Try to transfer more stock than available
        transfer_data = {
            "product_id": test_product["id"],
            "from_location_id": from_location["id"],
            "to_location_id": to_location["id"],
            "quantity": 999999,  # Extremely high quantity
            "reference": f"FAIL-TRANSFER-{int(time.time())}",
            "notes": "This should fail due to insufficient stock"
        }
        
        response = requests.post(f"{API_BASE}/inventory/transfer", 
                               json=transfer_data, 
                               headers=auth_headers)
        
        assert response.status_code == 400
        error_response = response.json()
        assert "Insufficient stock" in error_response["detail"]

class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_unauthorized_access(self):
        """Test that endpoints require authentication"""
        # Test without auth headers
        response = requests.get(f"{API_BASE}/products/")
        assert response.status_code == 401
        
        response = requests.get(f"{API_BASE}/inventory/summary")
        assert response.status_code == 401

    def test_not_found_errors(self, auth_headers):
        """Test 404 errors for non-existent resources"""
        fake_id = str(uuid.uuid4())
        
        # Non-existent product
        response = requests.get(f"{API_BASE}/products/{fake_id}", headers=auth_headers)
        assert response.status_code == 404
        
        # Non-existent purchase order
        response = requests.get(f"{API_BASE}/purchasing/purchase-orders/{fake_id}", headers=auth_headers)
        assert response.status_code == 404

    def test_validation_errors(self, auth_headers):
        """Test validation errors with invalid data"""
        # Invalid product data (missing required fields)
        invalid_product = {
            "org_id": TEST_ORG_ID,
            "name": "Invalid Product"
            # Missing required SKU field
        }
        
        response = requests.post(f"{API_BASE}/products/", 
                               json=invalid_product, 
                               headers=auth_headers)
        assert response.status_code == 422  # Validation error


class TestReorderSuggestionsIntegration:
    """Integration tests for W5 reorder suggestions API endpoints"""
    
    def test_get_reorder_suggestions_success(self, auth_headers):
        """Test successful retrieval of reorder suggestions"""
        response = requests.get(
            f"{API_BASE}/purchasing/reorder-suggestions",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "suggestions" in data
        assert "summary" in data
        assert "generated_at" in data
        assert "parameters" in data
        
        # Check summary structure
        summary = data["summary"]
        assert "total_suggestions" in summary
        assert "total_recommended_quantity" in summary
        assert "suppliers_involved" in summary
        assert "reason_breakdown" in summary
        assert "strategy_used" in summary
        
        # Each suggestion should have required fields
        for suggestion in data["suggestions"]:
            assert "product_id" in suggestion
            assert "sku" in suggestion
            assert "name" in suggestion
            assert "on_hand" in suggestion
            assert "incoming" in suggestion
            assert "recommended_quantity" in suggestion
            assert "velocity_source" in suggestion
            assert "horizon_days" in suggestion
            assert "reasons" in suggestion
            assert "adjustments" in suggestion
    
    def test_get_reorder_suggestions_with_strategy_filter(self, auth_headers):
        """Test reorder suggestions with different velocity strategies"""
        # Test latest strategy
        response_latest = requests.get(
            f"{API_BASE}/purchasing/reorder-suggestions?strategy=latest",
            headers=auth_headers
        )
        assert response_latest.status_code == 200
        data_latest = response_latest.json()
        
        # Test conservative strategy
        response_conservative = requests.get(
            f"{API_BASE}/purchasing/reorder-suggestions?strategy=conservative",
            headers=auth_headers
        )
        assert response_conservative.status_code == 200
        data_conservative = response_conservative.json()
        
        # Both should return valid data
        assert data_latest["summary"]["strategy_used"] == "latest"
        assert data_conservative["summary"]["strategy_used"] == "conservative"
        
        # Results may differ between strategies
        # (we can't guarantee specific differences without knowing the data)
    
    def test_get_reorder_suggestions_with_filters(self, auth_headers):
        """Test reorder suggestions with various filters"""
        params = {
            "horizon_days_override": 14,
            "include_zero_velocity": True,
            "min_days_cover": 0,
            "max_days_cover": 60
        }
        
        response = requests.get(
            f"{API_BASE}/purchasing/reorder-suggestions",
            headers=auth_headers,
            params=params
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that filters were applied
        filters_applied = data["summary"]["filters_applied"]
        assert filters_applied["horizon_days_override"] == 14
        assert filters_applied["include_zero_velocity"] is True
        assert filters_applied["min_days_cover"] == 0
        assert filters_applied["max_days_cover"] == 60
    
    def test_get_reorder_suggestions_invalid_strategy(self, auth_headers):
        """Test reorder suggestions with invalid strategy parameter"""
        response = requests.get(
            f"{API_BASE}/purchasing/reorder-suggestions?strategy=invalid",
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_reorder_suggestions_invalid_horizon(self, auth_headers):
        """Test reorder suggestions with invalid horizon parameter"""
        response = requests.get(
            f"{API_BASE}/purchasing/reorder-suggestions?horizon_days_override=0",
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Should be gt=0
        
        response = requests.get(
            f"{API_BASE}/purchasing/reorder-suggestions?horizon_days_override=400",
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Should be le=365
    
    def test_explain_reorder_suggestion_success(self, auth_headers):
        """Test successful retrieval of reorder explanation"""
        # First get a suggestion to explain
        suggestions_response = requests.get(
            f"{API_BASE}/purchasing/reorder-suggestions",
            headers=auth_headers
        )
        
        assert suggestions_response.status_code == 200
        suggestions_data = suggestions_response.json()
        
        if suggestions_data["suggestions"]:
            # Test explanation for first product
            product_id = suggestions_data["suggestions"][0]["product_id"]
            
            response = requests.get(
                f"{API_BASE}/purchasing/reorder-suggestions/explain/{product_id}",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            explanation = response.json()
            
            # Check explanation structure
            assert "product_id" in explanation
            assert "sku" in explanation
            assert "name" in explanation
            assert "reasons" in explanation
            assert "adjustments" in explanation
            
            # If not skipped, should have additional details
            if not explanation.get("skipped", False):
                assert "recommendation" in explanation
                assert "coverage" in explanation
                assert "velocity" in explanation
                assert "explanation" in explanation
                
                # Check detailed explanation structure
                detailed = explanation["explanation"]
                assert "inputs" in detailed
                assert "calculations" in detailed
                assert "logic_path" in detailed
    
    def test_explain_reorder_suggestion_not_found(self, auth_headers):
        """Test explanation for non-existent product"""
        fake_product_id = str(uuid.uuid4())
        
        response = requests.get(
            f"{API_BASE}/purchasing/reorder-suggestions/explain/{fake_product_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_explain_reorder_suggestion_invalid_uuid(self, auth_headers):
        """Test explanation with invalid UUID"""
        response = requests.get(
            f"{API_BASE}/purchasing/reorder-suggestions/explain/not-a-uuid",
            headers=auth_headers
        )
        
        assert response.status_code == 400
    
    def test_create_draft_pos_success(self, auth_headers):
        """Test successful creation of draft purchase orders"""
        # First get suggestions
        suggestions_response = requests.get(
            f"{API_BASE}/purchasing/reorder-suggestions",
            headers=auth_headers
        )
        
        assert suggestions_response.status_code == 200
        suggestions_data = suggestions_response.json()
        
        if suggestions_data["suggestions"]:
            # Select first few products for draft PO
            selected_products = [
                s["product_id"] for s in suggestions_data["suggestions"][:2]
            ]
            
            draft_po_data = {
                "product_ids": selected_products,
                "strategy": "latest",
                "auto_number": True
            }
            
            response = requests.post(
                f"{API_BASE}/purchasing/reorder-suggestions/draft-po",
                headers=auth_headers,
                json=draft_po_data
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Check response structure
            assert "draft_pos" in data
            assert "summary" in data
            assert "created_at" in data
            
            # Check summary
            summary = data["summary"]
            assert "total_draft_pos" in summary
            assert "total_items" in summary
            assert "total_quantity" in summary
            assert "suppliers" in summary
            
            # Check each draft PO structure
            for po in data["draft_pos"]:
                assert "supplier_id" in po
                assert "supplier_name" in po
                assert "po_number" in po
                assert "items" in po
                assert "total_items" in po
                assert "total_quantity" in po
                assert "lead_time_days" in po
                assert "minimum_order_quantity" in po
                assert "created_at" in po
                
                # Check items structure
                for item in po["items"]:
                    assert "product_id" in item
                    assert "sku" in item
                    assert "product_name" in item
                    assert "quantity" in item
                    assert "on_hand" in item
                    assert "recommended_quantity" in item
                    assert "reasons" in item
                    assert "adjustments" in item
    
    def test_create_draft_pos_no_products(self, auth_headers):
        """Test draft PO creation with no products selected"""
        draft_po_data = {
            "product_ids": [],
            "strategy": "latest"
        }
        
        response = requests.post(
            f"{API_BASE}/purchasing/reorder-suggestions/draft-po",
            headers=auth_headers,
            json=draft_po_data
        )
        
        assert response.status_code == 400
        error_data = response.json()
        assert "No products selected" in error_data["detail"]
    
    def test_create_draft_pos_invalid_product_ids(self, auth_headers):
        """Test draft PO creation with non-existent product IDs"""
        fake_product_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        
        draft_po_data = {
            "product_ids": fake_product_ids,
            "strategy": "latest"
        }
        
        response = requests.post(
            f"{API_BASE}/purchasing/reorder-suggestions/draft-po",
            headers=auth_headers,
            json=draft_po_data
        )
        
        # Should handle gracefully - either 400 or return empty result
        assert response.status_code in [400, 200]
        
        if response.status_code == 200:
            data = response.json()
            # Should have no draft POs if no valid suggestions found
            assert data["summary"]["total_draft_pos"] == 0
    
    def test_reorder_suggestions_unauthorized(self):
        """Test that reorder endpoints require authentication"""
        # Test without auth headers
        response = requests.get(f"{API_BASE}/purchasing/reorder-suggestions")
        assert response.status_code == 401
        
        fake_product_id = str(uuid.uuid4())
        response = requests.get(
            f"{API_BASE}/purchasing/reorder-suggestions/explain/{fake_product_id}"
        )
        assert response.status_code == 401
        
        draft_po_data = {"product_ids": [fake_product_id]}
        response = requests.post(
            f"{API_BASE}/purchasing/reorder-suggestions/draft-po",
            json=draft_po_data
        )
        assert response.status_code == 401
    
    def test_draft_pos_require_admin_role(self, auth_headers):
        """Test that draft PO creation requires admin role"""
        # Create a non-admin token
        regular_token = create_access_token(
            sub=TEST_USER_ID,
            org_id=TEST_ORG_ID,
            role="user"  # Non-admin role
        )
        
        non_admin_headers = {
            "Authorization": f"Bearer {regular_token}",
            "Content-Type": "application/json"
        }
        
        draft_po_data = {
            "product_ids": [str(uuid.uuid4())],
            "strategy": "latest"
        }
        
        response = requests.post(
            f"{API_BASE}/purchasing/reorder-suggestions/draft-po",
            headers=non_admin_headers,
            json=draft_po_data
        )
        
        # Should require admin role
        assert response.status_code == 403


def test_api_health_check():
    """Test that the API is running and accessible"""
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        # Should get the OpenAPI docs page (could be 200 or redirect)
        assert response.status_code in [200, 307, 308]
    except requests.exceptions.RequestException:
        pytest.fail("API server is not running. Please start the FastAPI server first.")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])