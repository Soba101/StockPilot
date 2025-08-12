"""
Unit tests for Purchasing CRUD operations  
Tests purchase orders, suppliers, and purchasing workflow
"""

import pytest
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db, Base
from app.core.security import create_access_token
from app.models.organization import Organization
from app.models.product import Product
from app.models.supplier import Supplier

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
    org = Organization(name="Test Purchasing Org")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org

@pytest.fixture(scope="function")
def test_supplier(db_session: Session, test_org):
    """Create test supplier"""
    supplier = Supplier(
        org_id=test_org.id,
        name="Test Supplier Inc",
        contact_person="John Supplier",
        email="john@testsupplier.com",
        phone="+1-555-0123",
        address="123 Supplier St, Business City, BC 12345",
        lead_time_days=14,
        minimum_order_quantity=50,
        payment_terms="Net 30",
        is_active="true"
    )
    db_session.add(supplier)
    db_session.commit()
    db_session.refresh(supplier)
    return supplier

@pytest.fixture(scope="function")
def test_products(db_session: Session, test_org):
    """Create test products for purchase orders"""
    products = []
    for i in range(3):
        product = Product(
            org_id=test_org.id,
            sku=f"PO-TEST-{i+1:03d}",
            name=f"Test Product {i+1}",
            description=f"Test product {i+1} for purchase orders",
            category="Test Category",
            cost=10.0 + i * 5,
            price=20.0 + i * 10,
            uom="each",
            reorder_point=25
        )
        products.append(product)
    
    db_session.add_all(products)
    db_session.commit()
    for product in products:
        db_session.refresh(product)
    return products

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

class TestPurchasingCRUD:
    """Test suite for Purchasing CRUD operations"""
    
    def test_create_purchase_order_success(self, db_session, auth_headers, test_supplier, test_products):
        """Test successful purchase order creation"""
        expected_date = datetime.now() + timedelta(days=21)
        
        po_data = {
            "supplier_id": str(test_supplier.id),
            "po_number": "",  # Auto-generate
            "expected_date": expected_date.isoformat(),
            "notes": "Test purchase order",
            "items": [
                {
                    "product_id": str(test_products[0].id),
                    "quantity": 100,
                    "unit_cost": 15.0
                },
                {
                    "product_id": str(test_products[1].id),
                    "quantity": 50,
                    "unit_cost": 20.0
                }
            ]
        }
        
        response = client.post("/api/v1/purchasing/purchase-orders", 
                             json=po_data, 
                             headers=auth_headers)
        
        assert response.status_code == 200
        created_po = response.json()
        
        # Verify PO details
        assert created_po["supplier_id"] == po_data["supplier_id"]
        assert created_po["supplier_name"] == test_supplier.name
        assert created_po["status"] == "draft"
        assert created_po["notes"] == po_data["notes"]
        assert "po_number" in created_po
        assert created_po["po_number"].startswith("PO-")
        
        # Verify total amount calculation
        expected_total = (100 * 15.0) + (50 * 20.0)  # 2500.0
        assert float(created_po["total_amount"]) == expected_total
        
        # Verify items
        assert len(created_po["items"]) == 2
        assert all("id" in item for item in created_po["items"])

    def test_get_purchase_orders_list(self, db_session, auth_headers, test_supplier, test_products):
        """Test retrieving list of purchase orders"""
        # Create multiple POs
        for i in range(3):
            po_data = {
                "supplier_id": str(test_supplier.id),
                "po_number": f"TEST-PO-{i+1:03d}",
                "expected_date": (datetime.now() + timedelta(days=14)).isoformat(),
                "notes": f"Test PO {i+1}",
                "items": [
                    {
                        "product_id": str(test_products[0].id),
                        "quantity": 25 * (i+1),
                        "unit_cost": 15.0
                    }
                ]
            }
            
            response = client.post("/api/v1/purchasing/purchase-orders", 
                                 json=po_data, 
                                 headers=auth_headers)
            assert response.status_code == 200
        
        # Get PO list
        response = client.get("/api/v1/purchasing/purchase-orders?limit=20", 
                            headers=auth_headers)
        assert response.status_code == 200
        
        pos = response.json()
        assert len(pos) == 3
        
        # Verify structure
        for po in pos:
            assert "id" in po
            assert "po_number" in po
            assert "supplier_name" in po
            assert "status" in po
            assert "total_amount" in po
            assert "item_count" in po

    def test_get_purchase_order_by_id(self, db_session, auth_headers, test_supplier, test_products):
        """Test retrieving specific purchase order by ID"""
        # Create PO
        po_data = {
            "supplier_id": str(test_supplier.id),
            "expected_date": (datetime.now() + timedelta(days=14)).isoformat(),
            "notes": "Detailed PO test",
            "items": [
                {
                    "product_id": str(test_products[0].id),
                    "quantity": 75,
                    "unit_cost": 12.50
                }
            ]
        }
        
        response = client.post("/api/v1/purchasing/purchase-orders", 
                             json=po_data, 
                             headers=auth_headers)
        assert response.status_code == 200
        created_po = response.json()
        po_id = created_po["id"]
        
        # Get PO details
        response = client.get(f"/api/v1/purchasing/purchase-orders/{po_id}", 
                            headers=auth_headers)
        assert response.status_code == 200
        
        po_details = response.json()
        assert po_details["id"] == po_id
        assert po_details["supplier_name"] == test_supplier.name
        assert len(po_details["items"]) == 1
        
        # Verify item details include product info
        item = po_details["items"][0]
        assert "product_name" in item
        assert "product_sku" in item
        assert item["quantity"] == 75
        assert float(item["unit_cost"]) == 12.50

    def test_update_purchase_order_status(self, db_session, auth_headers, test_supplier, test_products):
        """Test updating purchase order status"""
        # Create PO
        po_data = {
            "supplier_id": str(test_supplier.id),
            "expected_date": (datetime.now() + timedelta(days=14)).isoformat(),
            "items": [
                {
                    "product_id": str(test_products[0].id),
                    "quantity": 30,
                    "unit_cost": 18.0
                }
            ]
        }
        
        response = client.post("/api/v1/purchasing/purchase-orders", 
                             json=po_data, 
                             headers=auth_headers)
        assert response.status_code == 200
        created_po = response.json()
        po_id = created_po["id"]
        
        # Update status to ordered
        status_update = {
            "status": "ordered",
            "notes": "PO has been sent to supplier"
        }
        
        response = client.put(f"/api/v1/purchasing/purchase-orders/{po_id}/status", 
                            json=status_update, 
                            headers=auth_headers)
        assert response.status_code == 200
        
        updated_po = response.json()
        assert updated_po["status"] == "ordered"
        assert updated_po["notes"] == status_update["notes"]
        assert "order_date" in updated_po  # Should be set when status changed to ordered
        
        # Update to received
        received_date = datetime.now().isoformat()
        status_update = {
            "status": "received",
            "received_date": received_date,
            "notes": "Items received and verified"
        }
        
        response = client.put(f"/api/v1/purchasing/purchase-orders/{po_id}/status", 
                            json=status_update, 
                            headers=auth_headers)
        assert response.status_code == 200
        
        updated_po = response.json()
        assert updated_po["status"] == "received"
        assert "received_date" in updated_po

    def test_delete_purchase_order_draft_only(self, db_session, auth_headers, test_supplier, test_products):
        """Test that only draft POs can be deleted"""
        # Create draft PO
        po_data = {
            "supplier_id": str(test_supplier.id),
            "expected_date": (datetime.now() + timedelta(days=14)).isoformat(),
            "items": [
                {
                    "product_id": str(test_products[0].id),
                    "quantity": 20,
                    "unit_cost": 15.0
                }
            ]
        }
        
        response = client.post("/api/v1/purchasing/purchase-orders", 
                             json=po_data, 
                             headers=auth_headers)
        assert response.status_code == 200
        created_po = response.json()
        po_id = created_po["id"]
        
        # Should be able to delete draft PO
        response = client.delete(f"/api/v1/purchasing/purchase-orders/{po_id}", 
                               headers=auth_headers)
        assert response.status_code == 200
        
        # Verify PO is deleted
        response = client.get(f"/api/v1/purchasing/purchase-orders/{po_id}", 
                            headers=auth_headers)
        assert response.status_code == 404

    def test_cannot_delete_ordered_purchase_order(self, db_session, auth_headers, test_supplier, test_products):
        """Test that ordered POs cannot be deleted"""
        # Create and order PO
        po_data = {
            "supplier_id": str(test_supplier.id),
            "expected_date": (datetime.now() + timedelta(days=14)).isoformat(),
            "items": [
                {
                    "product_id": str(test_products[0].id),
                    "quantity": 15,
                    "unit_cost": 16.0
                }
            ]
        }
        
        response = client.post("/api/v1/purchasing/purchase-orders", 
                             json=po_data, 
                             headers=auth_headers)
        assert response.status_code == 200
        created_po = response.json()
        po_id = created_po["id"]
        
        # Update to ordered status
        status_update = {"status": "ordered"}
        response = client.put(f"/api/v1/purchasing/purchase-orders/{po_id}/status", 
                            json=status_update, 
                            headers=auth_headers)
        assert response.status_code == 200
        
        # Should NOT be able to delete ordered PO
        response = client.delete(f"/api/v1/purchasing/purchase-orders/{po_id}", 
                               headers=auth_headers)
        assert response.status_code == 400  # Bad request

    def test_purchase_order_with_invalid_supplier(self, auth_headers, test_products):
        """Test creating PO with non-existent supplier"""
        fake_supplier_id = str(uuid.uuid4())
        
        po_data = {
            "supplier_id": fake_supplier_id,
            "expected_date": (datetime.now() + timedelta(days=14)).isoformat(),
            "items": [
                {
                    "product_id": str(test_products[0].id),
                    "quantity": 10,
                    "unit_cost": 15.0
                }
            ]
        }
        
        response = client.post("/api/v1/purchasing/purchase-orders", 
                             json=po_data, 
                             headers=auth_headers)
        assert response.status_code == 404  # Supplier not found

    def test_purchase_order_with_invalid_product(self, auth_headers, test_supplier):
        """Test creating PO with non-existent product"""
        fake_product_id = str(uuid.uuid4())
        
        po_data = {
            "supplier_id": str(test_supplier.id),
            "expected_date": (datetime.now() + timedelta(days=14)).isoformat(),
            "items": [
                {
                    "product_id": fake_product_id,
                    "quantity": 10,
                    "unit_cost": 15.0
                }
            ]
        }
        
        response = client.post("/api/v1/purchasing/purchase-orders", 
                             json=po_data, 
                             headers=auth_headers)
        assert response.status_code == 404  # Product not found

    def test_purchase_order_filtering(self, db_session, auth_headers, test_supplier, test_products):
        """Test filtering purchase orders by status and supplier"""
        # Create POs with different statuses
        po_statuses = ["draft", "ordered", "received"]
        created_pos = []
        
        for i, status in enumerate(po_statuses):
            po_data = {
                "supplier_id": str(test_supplier.id),
                "expected_date": (datetime.now() + timedelta(days=14)).isoformat(),
                "items": [
                    {
                        "product_id": str(test_products[0].id),
                        "quantity": 10 + i * 5,
                        "unit_cost": 15.0
                    }
                ]
            }
            
            # Create PO
            response = client.post("/api/v1/purchasing/purchase-orders", 
                                 json=po_data, 
                                 headers=auth_headers)
            assert response.status_code == 200
            created_po = response.json()
            created_pos.append(created_po)
            
            # Update status if not draft
            if status != "draft":
                status_update = {"status": status}
                response = client.put(f"/api/v1/purchasing/purchase-orders/{created_po['id']}/status", 
                                    json=status_update, 
                                    headers=auth_headers)
                assert response.status_code == 200
        
        # Test filtering by status
        response = client.get("/api/v1/purchasing/purchase-orders?status=ordered", 
                            headers=auth_headers)
        assert response.status_code == 200
        filtered_pos = response.json()
        assert len(filtered_pos) >= 1
        assert all(po["status"] == "ordered" for po in filtered_pos)

    def test_unauthorized_purchasing_access(self, test_supplier, test_products):
        """Test that purchasing operations require authentication"""
        po_data = {
            "supplier_id": str(test_supplier.id),
            "expected_date": (datetime.now() + timedelta(days=14)).isoformat(),
            "items": [
                {
                    "product_id": str(test_products[0].id),
                    "quantity": 10,
                    "unit_cost": 15.0
                }
            ]
        }
        
        # No auth headers
        response = client.post("/api/v1/purchasing/purchase-orders", json=po_data)
        assert response.status_code == 401
        
        response = client.get("/api/v1/purchasing/purchase-orders")
        assert response.status_code == 401

if __name__ == "__main__":
    pytest.main([__file__, "-v"])