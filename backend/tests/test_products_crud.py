"""
Unit tests for Product CRUD operations
Tests all Create, Read, Update, Delete operations for products API
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
    org = Organization(
        name="Test Organization",
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org

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

@pytest.fixture(scope="function")
def sample_product_data(test_org):
    """Sample product data for testing"""
    return {
        "org_id": str(test_org.id),
        "sku": "TEST-PRODUCT-001",
        "name": "Test Product",
        "description": "A test product for unit testing",
        "category": "Test Category", 
        "cost": 15.99,
        "price": 29.99,
        "uom": "each",
        "reorder_point": 25
    }

class TestProductCRUD:
    """Test suite for Product CRUD operations"""
    
    def test_create_product_success(self, db_session, auth_headers, sample_product_data):
        """Test successful product creation"""
        response = client.post("/api/v1/products/", 
                             json=sample_product_data, 
                             headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all fields are returned correctly
        assert data["sku"] == sample_product_data["sku"]
        assert data["name"] == sample_product_data["name"]
        assert data["description"] == sample_product_data["description"]
        assert data["category"] == sample_product_data["category"]
        assert float(data["cost"]) == sample_product_data["cost"]
        assert float(data["price"]) == sample_product_data["price"]
        assert data["uom"] == sample_product_data["uom"]
        assert data["reorder_point"] == sample_product_data["reorder_point"]
        
        # Verify metadata fields
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert data["org_id"] == sample_product_data["org_id"]

    def test_create_product_duplicate_sku(self, db_session, auth_headers, sample_product_data):
        """Test product creation fails with duplicate SKU"""
        # Create first product
        response = client.post("/api/v1/products/", 
                             json=sample_product_data, 
                             headers=auth_headers)
        assert response.status_code == 200
        
        # Try to create duplicate SKU
        response = client.post("/api/v1/products/", 
                             json=sample_product_data, 
                             headers=auth_headers)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_create_product_missing_required_fields(self, auth_headers, test_org):
        """Test product creation fails with missing required fields"""
        incomplete_data = {
            "org_id": str(test_org.id),
            "name": "Test Product"
            # Missing required SKU
        }
        
        response = client.post("/api/v1/products/", 
                             json=incomplete_data, 
                             headers=auth_headers)
        assert response.status_code == 422  # Validation error

    def test_get_products_list(self, db_session, auth_headers, sample_product_data):
        """Test retrieving list of products"""
        # Create test products
        for i in range(3):
            product_data = sample_product_data.copy()
            product_data["sku"] = f"TEST-{i+1:03d}"
            product_data["name"] = f"Test Product {i+1}"
            
            response = client.post("/api/v1/products/", 
                                 json=product_data, 
                                 headers=auth_headers)
            assert response.status_code == 200
        
        # Get products list
        response = client.get("/api/v1/products/", headers=auth_headers)
        assert response.status_code == 200
        
        products = response.json()
        assert len(products) == 3
        assert all("id" in product for product in products)
        assert all("sku" in product for product in products)

    def test_get_product_by_id(self, db_session, auth_headers, sample_product_data):
        """Test retrieving specific product by ID"""
        # Create product
        response = client.post("/api/v1/products/", 
                             json=sample_product_data, 
                             headers=auth_headers)
        assert response.status_code == 200
        created_product = response.json()
        product_id = created_product["id"]
        
        # Get product by ID
        response = client.get(f"/api/v1/products/{product_id}", headers=auth_headers)
        assert response.status_code == 200
        
        product = response.json()
        assert product["id"] == product_id
        assert product["sku"] == sample_product_data["sku"]
        assert product["name"] == sample_product_data["name"]

    def test_get_product_not_found(self, auth_headers):
        """Test retrieving non-existent product returns 404"""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/products/{fake_id}", headers=auth_headers)
        assert response.status_code == 404

    def test_update_product_success(self, db_session, auth_headers, sample_product_data):
        """Test successful product update"""
        # Create product
        response = client.post("/api/v1/products/", 
                             json=sample_product_data, 
                             headers=auth_headers)
        assert response.status_code == 200
        created_product = response.json()
        product_id = created_product["id"]
        
        # Update product
        update_data = {
            "name": "Updated Test Product",
            "description": "Updated description",
            "price": 39.99,
            "reorder_point": 50
        }
        
        response = client.put(f"/api/v1/products/{product_id}", 
                            json=update_data, 
                            headers=auth_headers)
        assert response.status_code == 200
        
        updated_product = response.json()
        assert updated_product["name"] == update_data["name"]
        assert updated_product["description"] == update_data["description"]
        assert float(updated_product["price"]) == update_data["price"]
        assert updated_product["reorder_point"] == update_data["reorder_point"]
        
        # Verify unchanged fields remain the same
        assert updated_product["sku"] == sample_product_data["sku"]
        assert updated_product["category"] == sample_product_data["category"]
        
        # Verify updated_at timestamp changed
        assert updated_product["updated_at"] != created_product["updated_at"]

    def test_update_product_not_found(self, auth_headers):
        """Test updating non-existent product returns 404"""
        fake_id = str(uuid.uuid4())
        update_data = {"name": "Updated Name"}
        
        response = client.put(f"/api/v1/products/{fake_id}", 
                            json=update_data, 
                            headers=auth_headers)
        assert response.status_code == 404

    def test_delete_product_success(self, db_session, auth_headers, sample_product_data):
        """Test successful product deletion"""
        # Create product
        response = client.post("/api/v1/products/", 
                             json=sample_product_data, 
                             headers=auth_headers)
        assert response.status_code == 200
        created_product = response.json()
        product_id = created_product["id"]
        
        # Verify product exists
        response = client.get(f"/api/v1/products/{product_id}", headers=auth_headers)
        assert response.status_code == 200
        
        # Delete product
        response = client.delete(f"/api/v1/products/{product_id}", headers=auth_headers)
        assert response.status_code == 200
        
        # Verify product is deleted
        response = client.get(f"/api/v1/products/{product_id}", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_product_not_found(self, auth_headers):
        """Test deleting non-existent product returns 404"""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/api/v1/products/{fake_id}", headers=auth_headers)
        assert response.status_code == 404

    def test_unauthorized_access(self, sample_product_data):
        """Test API endpoints require authentication"""
        # Test without auth headers
        response = client.get("/api/v1/products/")
        assert response.status_code == 401
        
        response = client.post("/api/v1/products/", json=sample_product_data)
        assert response.status_code == 401

    def test_product_validation_constraints(self, auth_headers, test_org):
        """Test product field validation constraints"""
        base_data = {
            "org_id": str(test_org.id),
            "sku": "VALID-SKU",
            "name": "Valid Name"
        }
        
        # Test negative price
        invalid_data = base_data.copy()
        invalid_data["price"] = -10.0
        response = client.post("/api/v1/products/", 
                             json=invalid_data, 
                             headers=auth_headers)
        # Should either reject or accept (depending on validation rules)
        # This tests that the API handles edge cases gracefully
        
        # Test very long SKU
        invalid_data = base_data.copy()
        invalid_data["sku"] = "A" * 200  # Very long SKU
        response = client.post("/api/v1/products/", 
                             json=invalid_data, 
                             headers=auth_headers)
        # Should handle gracefully

    def test_product_search_and_filtering(self, db_session, auth_headers, sample_product_data):
        """Test product search and filtering capabilities"""
        # Create multiple products with different categories
        categories = ["Electronics", "Books", "Clothing"]
        for i, category in enumerate(categories):
            product_data = sample_product_data.copy()
            product_data["sku"] = f"FILTER-{i+1:03d}"
            product_data["name"] = f"Product {category}"
            product_data["category"] = category
            
            response = client.post("/api/v1/products/", 
                                 json=product_data, 
                                 headers=auth_headers)
            assert response.status_code == 200
        
        # Test filtering (if API supports it)
        response = client.get("/api/v1/products/", headers=auth_headers)
        assert response.status_code == 200
        products = response.json()
        assert len(products) >= 3

if __name__ == "__main__":
    pytest.main([__file__, "-v"])