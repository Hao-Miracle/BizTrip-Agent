from biztrip_agent.delivery import create_delivery_package


def test_delivery_package_contains_only_excel_and_referenced_originals(tmp_path):
    attachment_dir = tmp_path / "state" / "附件"
    attachment_dir.mkdir(parents=True)
    (attachment_dir / "used.pdf").write_bytes(b"%PDF-1.7 used")
    (attachment_dir / "unused.pdf").write_bytes(b"%PDF-1.7 unused")
    record = {
        "分类": "发票",
        "金额": 88.0,
        "日期": "2026-08-01",
        "供应商": "测试商店",
        "附件": "used.pdf",
    }

    package = create_delivery_package(
        [record],
        [],
        tmp_path / "output",
        attachment_dir,
        "八月报销",
        use_llm=True,
    )

    assert package["package_dir"].name.startswith("报销包_")
    assert "八月报销" in package["package_dir"].name
    assert "八月报销" in package["excel_path"].name
    assert package["excel_path"].exists()
    assert (package["package_dir"] / "原件" / "used.pdf").exists()
    assert not (package["package_dir"] / "原件" / "unused.pdf").exists()
    assert {path.name for path in package["package_dir"].iterdir()} == {
        package["excel_path"].name,
        "原件",
    }
