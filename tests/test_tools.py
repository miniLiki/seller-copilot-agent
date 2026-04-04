import pytest
from fastapi import HTTPException

from tools.app import create_optimization_task, generate_ad_copy, read_product
from tools.schemas import CreateTaskRequest, GenerateCopyRequest


def test_read_product_returns_expected_fields() -> None:
    product = read_product("SKU_001")
    assert product.product_id == "SKU_001"
    assert product.market == "US"


def test_create_optimization_task_returns_created_status() -> None:
    response = create_optimization_task(
        CreateTaskRequest(
            product_id="SKU_001",
            task_type="creative_refresh",
            priority="high",
            reason="hero image needs refresh",
        )
    )
    assert response.status == "created"
    assert response.product_id == "SKU_001"


def test_generate_ad_copy_returns_requested_variant_count() -> None:
    response = generate_ad_copy(
        GenerateCopyRequest(
            product_id="SKU_001",
            market="US",
            angle="benefit_driven",
            num_variants=2,
        )
    )
    assert len(response.copies) == 2


def test_read_product_raises_for_missing_product() -> None:
    with pytest.raises(HTTPException):
        read_product("SKU_999")
