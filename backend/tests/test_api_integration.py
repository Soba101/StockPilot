"""
Integration tests for StockPilot API CRUD operations
Tests against real PostgreSQL database to ensure everything works
"""

import pytest
import uuid
from datetime import datetime, timedelta
import requests
import time

from app.core.security import create_access_token

# Base URL for API
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

# Test organization and user (from populated database)
TEST_ORG_ID = "6bee7759-b4fa-41ec-80e9-59adf86ed171"  # Demo Company
TEST_USER_ID = "7ddac2fe-abf7-441f-83c2-0848c54cdbbd"  # admin@demo.co

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
        assert movement["movement_type"] == movement_data["movement_type"]

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