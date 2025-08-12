"""
Unit tests for Inventory CRUD operations
Tests stock adjustments, transfers, and movement tracking
"""

import pytest
import uuid
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db, Base
from app.core.security import create_access_token
from app.models.organization import Organization
from app.models.product import Product
from app.models.location import Location

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)

@pytest.fixture(scope="function")
def db_session():
    """Create test database and session for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function") 
def test_org(db_session: Session):
    """Create test organization"""
    org = Organization(name="Test Org")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org

@pytest.fixture(scope="function")
def test_locations(db_session: Session, test_org):
    """Create test locations"""
    warehouse = Location(
        org_id=test_org.id,
        name="Test Warehouse",
        type="warehouse",
        address="123 Test St"
    )
    store = Location(
        org_id=test_org.id,
        name="Test Store", 
        type="store",
        address="456 Store Ave"
    )
    db_session.add_all([warehouse, store])
    db_session.commit()
    db_session.refresh(warehouse)
    db_session.refresh(store)
    return {"warehouse": warehouse, "store": store}

@pytest.fixture(scope="function")
def test_product(db_session: Session, test_org):
    """Create test product"""
    product = Product(
        org_id=test_org.id,
        sku="TEST-INVENTORY-001",
        name="Test Inventory Product",
        description="Product for inventory testing",
        category="Test",
        cost=10.0,
        price=20.0,
        uom="each",
        reorder_point=25
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product

@pytest.fixture(scope="function")
def auth_headers(test_org):
    """Create authentication headers for API requests"""
    test_user_id = str(uuid.uuid4())
    token = create_access_token(
        user_id=test_user_id,
        org_id=str(test_org.id),
        role="admin"
    )
    return {"Authorization": f"Bearer {token}"}

class TestInventoryOperations:
    """Test suite for Inventory operations"""
    
    def test_stock_adjustment_increase(self, db_session, auth_headers, test_product, test_locations):
        """Test increasing stock via adjustment"""
        adjustment_data = {
            "product_id": str(test_product.id),
            "location_id": str(test_locations["warehouse"].id),
            "quantity": 100,
            "movement_type": "adjust",
            "reference": "TEST-ADJ-001",
            "notes": "Initial stock adjustment for testing"
        }
        
        response = client.post("/api/v1/inventory/movements", 
                             json=adjustment_data, 
                             headers=auth_headers)
        
        assert response.status_code == 200
        movement = response.json()
        
        # Verify movement record
        assert movement["product_id"] == adjustment_data["product_id"]
        assert movement["location_id"] == adjustment_data["location_id"]
        assert movement["quantity"] == adjustment_data["quantity"]
        assert movement["movement_type"] == "adjust"
        assert movement["reference"] == adjustment_data["reference"]
        assert "timestamp" in movement
        assert "id" in movement

    def test_stock_adjustment_decrease(self, db_session, auth_headers, test_product, test_locations):
        """Test decreasing stock via adjustment"""
        # First add some stock
        add_stock_data = {
            "product_id": str(test_product.id),
            "location_id": str(test_locations["warehouse"].id),
            "quantity": 50,
            "movement_type": "in",
            "reference": "INITIAL-STOCK",
            "notes": "Adding initial stock"
        }
        
        response = client.post("/api/v1/inventory/movements", 
                             json=add_stock_data, 
                             headers=auth_headers)
        assert response.status_code == 200
        
        # Now decrease stock
        decrease_data = {
            "product_id": str(test_product.id),
            "location_id": str(test_locations["warehouse"].id),
            "quantity": -20,
            "movement_type": "adjust",
            "reference": "DECREASE-ADJ",
            "notes": "Decreasing stock for testing"
        }
        
        response = client.post("/api/v1/inventory/movements", 
                             json=decrease_data, 
                             headers=auth_headers)
        
        assert response.status_code == 200
        movement = response.json()
        assert movement["quantity"] == -20

    def test_stock_transfer_between_locations(self, db_session, auth_headers, test_product, test_locations):
        """Test transferring stock between locations"""
        # First add stock to warehouse
        initial_stock_data = {
            "product_id": str(test_product.id),
            "location_id": str(test_locations["warehouse"].id),
            "quantity": 100,
            "movement_type": "in",
            "reference": "INITIAL-STOCK",
            "notes": "Initial warehouse stock"
        }
        
        response = client.post("/api/v1/inventory/movements", 
                             json=initial_stock_data, 
                             headers=auth_headers)
        assert response.status_code == 200
        
        # Transfer stock from warehouse to store
        transfer_out_data = {
            "product_id": str(test_product.id),
            "location_id": str(test_locations["warehouse"].id),
            "quantity": -30,
            "movement_type": "transfer",
            "reference": "TRANSFER-001",
            "notes": "Transfer to store"
        }
        
        transfer_in_data = {
            "product_id": str(test_product.id),
            "location_id": str(test_locations["store"].id),
            "quantity": 30,
            "movement_type": "transfer",
            "reference": "TRANSFER-001", 
            "notes": "Received from warehouse"
        }
        
        # Create both movements (out from warehouse, in to store)
        response = client.post("/api/v1/inventory/movements", 
                             json=transfer_out_data, 
                             headers=auth_headers)
        assert response.status_code == 200
        
        response = client.post("/api/v1/inventory/movements", 
                             json=transfer_in_data, 
                             headers=auth_headers)
        assert response.status_code == 200

    def test_get_inventory_movements_history(self, db_session, auth_headers, test_product, test_locations):
        """Test retrieving inventory movement history"""
        # Create several movements
        movements_data = [
            {
                "product_id": str(test_product.id),
                "location_id": str(test_locations["warehouse"].id),
                "quantity": 50,
                "movement_type": "in",
                "reference": "PO-001",
                "notes": "Purchase order receipt"
            },
            {
                "product_id": str(test_product.id),
                "location_id": str(test_locations["warehouse"].id),
                "quantity": -10,
                "movement_type": "out",
                "reference": "SALE-001",
                "notes": "Customer sale"
            },
            {
                "product_id": str(test_product.id),
                "location_id": str(test_locations["warehouse"].id),
                "quantity": 5,
                "movement_type": "adjust",
                "reference": "ADJ-001",
                "notes": "Cycle count adjustment"
            }
        ]
        
        # Create movements
        for movement_data in movements_data:
            response = client.post("/api/v1/inventory/movements", 
                                 json=movement_data, 
                                 headers=auth_headers)
            assert response.status_code == 200
        
        # Get movement history
        response = client.get("/api/v1/inventory/movements", headers=auth_headers)
        assert response.status_code == 200
        
        movements = response.json()
        assert len(movements) >= 3
        
        # Verify movements contain expected data
        movement_types = [m["movement_type"] for m in movements]
        assert "in" in movement_types
        assert "out" in movement_types  
        assert "adjust" in movement_types

    def test_get_inventory_summary(self, db_session, auth_headers, test_product, test_locations):
        """Test getting current inventory summary"""
        # Add some stock movements
        movements = [
            {"quantity": 100, "movement_type": "in", "reference": "STOCK-1"},
            {"quantity": -20, "movement_type": "out", "reference": "SALE-1"},
            {"quantity": 5, "movement_type": "adjust", "reference": "ADJ-1"}
        ]
        
        for movement_data in movements:
            full_data = {
                "product_id": str(test_product.id),
                "location_id": str(test_locations["warehouse"].id),
                "notes": "Test movement",
                **movement_data
            }
            response = client.post("/api/v1/inventory/movements", 
                                 json=full_data, 
                                 headers=auth_headers)
            assert response.status_code == 200
        
        # Get inventory summary
        response = client.get("/api/v1/inventory/summary", headers=auth_headers)
        assert response.status_code == 200
        
        summary = response.json()
        
        # Verify summary structure
        assert "total_products" in summary
        assert "total_stock_value" in summary
        assert "low_stock_count" in summary
        assert "out_of_stock_count" in summary

    def test_invalid_movement_validation(self, auth_headers, test_product, test_locations):
        """Test validation of invalid inventory movements"""
        
        # Test missing required fields
        invalid_data = {
            "product_id": str(test_product.id),
            # Missing location_id, quantity, movement_type
        }
        
        response = client.post("/api/v1/inventory/movements", 
                             json=invalid_data, 
                             headers=auth_headers)
        assert response.status_code == 422  # Validation error
        
        # Test invalid movement type
        invalid_data = {
            "product_id": str(test_product.id),
            "location_id": str(test_locations["warehouse"].id),
            "quantity": 10,
            "movement_type": "invalid_type",
            "reference": "TEST"
        }
        
        response = client.post("/api/v1/inventory/movements", 
                             json=invalid_data, 
                             headers=auth_headers)
        assert response.status_code == 422  # Validation error

    def test_movement_with_nonexistent_product(self, auth_headers, test_locations):
        """Test movement with non-existent product ID"""
        fake_product_id = str(uuid.uuid4())
        
        movement_data = {
            "product_id": fake_product_id,
            "location_id": str(test_locations["warehouse"].id),
            "quantity": 10,
            "movement_type": "in",
            "reference": "TEST"
        }
        
        response = client.post("/api/v1/inventory/movements", 
                             json=movement_data, 
                             headers=auth_headers)
        assert response.status_code == 404  # Product not found

    def test_movement_with_nonexistent_location(self, auth_headers, test_product):
        """Test movement with non-existent location ID"""
        fake_location_id = str(uuid.uuid4())
        
        movement_data = {
            "product_id": str(test_product.id),
            "location_id": fake_location_id,
            "quantity": 10,
            "movement_type": "in",
            "reference": "TEST"
        }
        
        response = client.post("/api/v1/inventory/movements", 
                             json=movement_data, 
                             headers=auth_headers)
        assert response.status_code == 404  # Location not found

    def test_unauthorized_inventory_access(self, test_product, test_locations):
        """Test that inventory operations require authentication"""
        movement_data = {
            "product_id": str(test_product.id),
            "location_id": str(test_locations["warehouse"].id),
            "quantity": 10,
            "movement_type": "in",
            "reference": "UNAUTHORIZED"
        }
        
        # No auth headers
        response = client.post("/api/v1/inventory/movements", json=movement_data)
        assert response.status_code == 401
        
        response = client.get("/api/v1/inventory/summary")
        assert response.status_code == 401

if __name__ == "__main__":
    pytest.main([__file__, "-v"])