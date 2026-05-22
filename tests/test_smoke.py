"""Phase-A smoke test: covers the uv-generated package stub so CI's
coverage gate (80%) passes before real code lands in Phase C."""

from telegram_tech_publisher import main


def test_main_runs(capsys: object) -> None:
    main()
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert "telegram-tech-publisher" in captured.out
