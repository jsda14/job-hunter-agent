import json
import pytest

from src.domain.models.job import SourcePlatform
from src.domain.ports.harvester import CompanyTarget
from src.domain.ports.target_loader import TargetLoaderError
from src.adapters.loaders.json_targets import JsonTargetLoaderAdapter


def test_load_targets_success(tmp_path):
    """RN-01: Carga exitosa de archivo JSON válido transformando cada item en CompanyTarget válido."""
    loader = JsonTargetLoaderAdapter()
    file_path = tmp_path / "valid_companies.json"
    data = [
        {"company_slug": "kavak", "platform": "lever", "name": "Kavak"},
        {"company_slug": "nubank", "platform": "greenhouse"},
    ]
    file_path.write_text(json.dumps(data), encoding="utf-8")

    targets = loader.load_targets(file_path)

    assert len(targets) == 2
    assert targets[0] == CompanyTarget(company_slug="kavak", platform=SourcePlatform.LEVER, name="Kavak")
    assert targets[1] == CompanyTarget(company_slug="nubank", platform=SourcePlatform.GREENHOUSE, name=None)


def test_load_targets_file_not_found():
    """RN-02: Fallo ante archivo inexistente lanzando TargetLoaderError."""
    loader = JsonTargetLoaderAdapter()
    with pytest.raises(TargetLoaderError):
        loader.load_targets("nonexistent_path/companies.json")


def test_load_targets_invalid_json(tmp_path):
    """RN-02: Fallo ante JSON con sintaxis rota o corrupta lanzando TargetLoaderError."""
    loader = JsonTargetLoaderAdapter()
    file_path = tmp_path / "corrupted.json"
    file_path.write_text("{broken json: 123", encoding="utf-8")

    with pytest.raises(TargetLoaderError):
        loader.load_targets(file_path)


def test_load_targets_root_not_a_list(tmp_path):
    """CB-02: Fallo ante JSON cuya raíz no sea una lista lanzando TargetLoaderError."""
    loader = JsonTargetLoaderAdapter()
    file_path = tmp_path / "dict_root.json"
    file_path.write_text(json.dumps({"companies": [{"company_slug": "kavak", "platform": "lever"}]}), encoding="utf-8")

    with pytest.raises(TargetLoaderError):
        loader.load_targets(file_path)


def test_load_targets_invalid_schema_item(tmp_path):
    """RN-02: Fallo ante items con campos inválidos o plataformas no reconocidas lanzando TargetLoaderError."""
    loader = JsonTargetLoaderAdapter()
    file_path = tmp_path / "invalid_item.json"
    data = [
        {"company_slug": "unsupported_co", "platform": "unsupported_ats"}
    ]
    file_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(TargetLoaderError):
        loader.load_targets(file_path)


def test_load_targets_empty_list(tmp_path):
    """CB-01: Manejo correcto de lista vacía retornando []."""
    loader = JsonTargetLoaderAdapter()
    file_path = tmp_path / "empty.json"
    file_path.write_text(json.dumps([]), encoding="utf-8")

    targets = loader.load_targets(file_path)
    assert targets == []
