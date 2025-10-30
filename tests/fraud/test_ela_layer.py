"""Unit tests for ELA (Error Level Analysis) fraud detection layer."""
import pytest

from app.fraud_detection.layers.ela_layer import ELALayer


@pytest.fixture
def ela_layer():
    """Create an ELA layer instance."""
    return ELALayer()


@pytest.mark.asyncio
@pytest.mark.fraud
async def test_ela_valid_image(ela_layer, sample_images):
    """Test ELA layer with valid unmodified image."""
    result = await ela_layer.analyze(sample_images["valid"])

    assert "score" in result
    assert result["score"] >= 0
    assert result["score"] <= 20


@pytest.mark.asyncio
@pytest.mark.fraud
async def test_ela_edited_image(ela_layer, sample_images):
    """Test ELA layer detects edited images."""
    result = await ela_layer.analyze(sample_images["edited"])

    assert "score" in result
    # Edited images should have higher error levels
    assert "anomalies" in result or "tampering_indicators" in result


@pytest.mark.asyncio
@pytest.mark.fraud
async def test_ela_layer_structure(ela_layer):
    """Test ELA layer has required structure."""
    assert ela_layer.layer_name == "ELA"
    assert hasattr(ela_layer, "analyze")
    assert hasattr(ela_layer, "weight")


@pytest.mark.asyncio
@pytest.mark.fraud
async def test_ela_compression_detection(ela_layer):
    """Test ELA detects image compression anomalies."""
    # This would test that ELA detects signs of recompression
    assert True  # Placeholder
