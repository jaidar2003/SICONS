from app.db.import_pastina import (  # noqa: F401
    ImportSummary,
    PastinaPrecio,
    PastinaRow,
    build_rows,
    grouped_prices,
    import_pastina,
    main,
    normalize_invoice,
    observaciones,
    parse_date,
    parse_decimal,
    upsert_precio,
)


if __name__ == "__main__":
    main()
