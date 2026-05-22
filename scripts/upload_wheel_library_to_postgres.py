import os
import csv
import uuid
import tempfile
from pathlib import Path

import psycopg2

# -----------------------------
# CONFIG
# -----------------------------
CSV_FILE = Path(os.getenv("WHEEL_LIBRARY_CSV", "Wheel_Library.csv"))
TABLE_SCHEMA = "public"
TABLE_NAME = "wheel_library_raw"
DB_URL_ENV = "SUPABASE_DB_URL"

# Original CSV column -> database column mapping
COLUMN_MAPPING = [('Data PartNo', 'data_part_no'), ('VendorPartNo', 'vendor_part_no'), ('MPN', 'mpn'), ('sku', 'sku'), ('DWW PartNo', 'dww_part_no'), ('GlobalPartNo', 'global_part_no'), ('Vendor Description', 'vendor_description'), ('Brand', 'brand'), ('Model', 'model'), ('Style', 'style'), ('StyleName', 'style_name'), ('Size', 'size'), ('WheelDiameter', 'wheel_diameter'), ('WheelWidth', 'wheel_width'), ('BoltPattern1', 'bolt_pattern1'), ('BoltPattern2', 'bolt_pattern2'), ('BoltPattern', 'bolt_pattern'), ('LugHoles', 'lug_holes'), ('OFFSET1', 'offset1'), ('SIMPLEOFFSET', 'simpleoffset'), ('HUB', 'hub'), ('FINISH', 'finish'), ('BasicFinish', 'basic_finish'), ('LipFinish', 'lip_finish'), ('Vendor Code', 'vendor_code'), ('ManufacturerFinish', 'manufacturer_finish'), ('ManufacturerFinishCode', 'manufacturer_finish_code'), ('LoadRating', 'load_rating'), ('BackSpacing', 'back_spacing'), ('LipDepth', 'lip_depth'), ('CountryofOrigin', 'countryof_origin'), ('UPCCode', 'upccode'), ('CAP', 'cap'), ('CAPPartNo', 'cappart_no'), ('Warranty', 'warranty'), ('Image', 'image'), ('SideImage', 'side_image'), ('Additional Images', 'additional_images'), ('WheelVizualizerImage', 'wheel_vizualizer_image'), ('Weight', 'weight'), ('Length', 'length'), ('Width', 'width'), ('Height', 'height'), ('DimWeight', 'dim_weight'), ('Girth', 'girth'), ('Weight for Shipping', 'weight_for_shipping'), ('bandable', 'bandable'), ('Xfactor', 'xfactor'), ('Discontinued', 'discontinued'), ('Wheel Construction', 'wheel_construction'), ('Offroad', 'offroad'), ('Dually', 'dually'), ('Staggered', 'staggered'), ('Wheel Style', 'wheel_style'), ('VehicleType-Car', 'vehicle_type_car'), ('VehicleType-SUV', 'vehicle_type_suv'), ('VehicleType-Truck', 'vehicle_type_truck'), ('VehicleType-Offroad', 'vehicle_type_offroad'), ('VehicleType-Trailer', 'vehicle_type_trailer'), ('VehicleType-ATV-UTV', 'vehicle_type_atv_utv'), ('url_key', 'url_key'), ('InvoicePrice', 'invoice_price'), ('MAP', 'map_col'), ('MSRP', 'msrp'), ('Rebates', 'rebates'), ('NetPrice', 'net_price'), ('Markup', 'markup'), ('CostofShipping', 'costof_shipping'), ('average_single', 'average_single'), ('average_double', 'average_double'), ('Oversized Shipping Cost', 'oversized_shipping_cost'), ('Peak Season Shipping Cost', 'peak_season_shipping_cost'), ('RetailPrice', 'retail_price'), ('Website Display Price', 'website_display_price'), ('retailprice_before_mapcap', 'retailprice_before_mapcap'), ('MAPCAPPrice', 'mapcapprice'), ('fakeprice', 'fakeprice'), ('fakepercent', 'fakepercent'), ('CostWithoutMarkup', 'cost_without_markup'), ('Lowest Competitor Price', 'lowest_competitor_price'), ('Lowest Competitor Name', 'lowest_competitor_name'), ('We have advantage on the pricing', 'we_have_advantage_on_the_pricing'), ('all Qty', 'all_qty'), ('Location Qty', 'location_qty'), ('Last date all qty', 'last_date_all_qty'), ('All Local QTY', 'all_local_qty'), ('Last date Local QTY', 'last_date_local_qty'), ('instock Flag', 'instock_flag'), ('local_vendor', 'local_vendor'), ('local_instock', 'local_instock'), ('Rebate on consumer', 'rebate_on_consumer'), ('Rebate Amount', 'rebate_amount'), ('RebateURL', 'rebate_url'), ('rebate_product_image', 'rebate_product_image'), ('Preferred Product', 'preferred_product'), ('Local Flag for Website', 'local_flag_for_website'), ('Flag for Website', 'flag_for_website'), ('Customizable', 'customizable'), ('saleType', 'sale_type'), ('date-added', 'date_added'), ('RAWImage', 'rawimage'), ('WheelType', 'wheel_type'), ('WheelTypeDescription', 'wheel_type_description'), ('model_url', 'model_url'), ('model_url_selected', 'model_url_selected'), ('acima_loggedin_price', 'acima_loggedin_price'), ('acima_loggedin_pricex4', 'acima_loggedin_pricex4'), ('acima_notloggedin_price', 'acima_notloggedin_price'), ('acima_notloggedin_pricex4', 'acima_notloggedin_pricex4'), ('affirm_loggedin_price', 'affirm_loggedin_price'), ('affirm_loggedin_pricex4', 'affirm_loggedin_pricex4'), ('affirm_notloggedin_price', 'affirm_notloggedin_price'), ('affirm_notloggedin_pricex4', 'affirm_notloggedin_pricex4'), ('image_url', 'image_url'), ('additional_image_url', 'additional_image_url'), ('entity_id', 'entity_id'), ('FrontImage', 'front_image'), ('combined_attribute', 'combined_attribute'), ('promo_amount', 'promo_amount'), ('custom_promo_id', 'custom_promo_id'), ('ID', 'id_col')]


def q_ident(name):
    return '"' + name.replace('"', '""') + '"'


def create_table(conn):
    columns_sql = ",\n".join(
        [f"    {q_ident(db_col)} text" for _, db_col in COLUMN_MAPPING]
    )

    create_sql = f"""
    CREATE TABLE IF NOT EXISTS {q_ident(TABLE_SCHEMA)}.{q_ident(TABLE_NAME)} (
        db_row_id bigserial PRIMARY KEY,
        upload_batch_id uuid NOT NULL,
        uploaded_at timestamptz NOT NULL DEFAULT now(),
        {columns_sql},
        sku_clean text GENERATED ALWAYS AS (upper(trim("sku"))) STORED
    );
    """

    index_sql = [
        f'CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_sku ON {q_ident(TABLE_SCHEMA)}.{q_ident(TABLE_NAME)} ("sku");',
        f'CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_sku_clean ON {q_ident(TABLE_SCHEMA)}.{q_ident(TABLE_NAME)} ((upper(trim("sku"))));',
        f'CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_brand ON {q_ident(TABLE_SCHEMA)}.{q_ident(TABLE_NAME)} ("brand");',
        f'CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_brand_sku ON {q_ident(TABLE_SCHEMA)}.{q_ident(TABLE_NAME)} ("brand", "sku");',
        f'CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_model ON {q_ident(TABLE_SCHEMA)}.{q_ident(TABLE_NAME)} ("model");'
    ]

    with conn.cursor() as cur:
        cur.execute(create_sql)
        for statement in index_sql:
            cur.execute(statement)
    conn.commit()


def write_temp_csv_for_copy(source_csv, batch_id):
    db_columns = ["upload_batch_id"] + [db_col for _, db_col in COLUMN_MAPPING]
    original_columns = [src_col for src_col, _ in COLUMN_MAPPING]

    temp_file = tempfile.NamedTemporaryFile(
        mode="w",
        newline="",
        encoding="utf-8",
        suffix="_wheel_library_upload.csv",
        delete=False
    )

    with open(source_csv, newline="", encoding="utf-8-sig") as src, temp_file as out:
        reader = csv.DictReader(src)
        writer = csv.writer(out)
        writer.writerow(db_columns)

        row_count = 0
        for row in reader:
            writer.writerow([batch_id] + [row.get(col, "") for col in original_columns])
            row_count += 1

            if row_count % 10000 == 0:
                print(f"Prepared {row_count:,} rows...")

    return Path(temp_file.name), row_count, db_columns


def copy_to_postgres(conn, temp_csv_path, db_columns):
    column_list = ", ".join(q_ident(col) for col in db_columns)

    copy_sql = f"""
    COPY {q_ident(TABLE_SCHEMA)}.{q_ident(TABLE_NAME)} ({column_list})
    FROM STDIN WITH CSV HEADER
    """

    with conn.cursor() as cur:
        with open(temp_csv_path, "r", encoding="utf-8") as f:
            cur.copy_expert(copy_sql, f)
    conn.commit()


def main():
    db_url = os.getenv(DB_URL_ENV)

    if not db_url:
        raise RuntimeError(
            f"Missing {DB_URL_ENV} environment variable. "
            "Set it to your Supabase Postgres connection string."
        )

    if not CSV_FILE.exists():
        raise FileNotFoundError(
            f"{CSV_FILE} not found. Put this script in the same folder as Wheel_Library.csv."
        )

    batch_id = str(uuid.uuid4())
    print(f"Upload batch id: {batch_id}")

    print("Connecting to Supabase/Postgres...")
    conn = psycopg2.connect(db_url)

    temp_csv_path = None
    try:
        print("Creating table/indexes if needed...")
        create_table(conn)

        print("Preparing CSV for upload...")
        temp_csv_path, row_count, db_columns = write_temp_csv_for_copy(CSV_FILE, batch_id)

        print(f"Uploading {row_count:,} rows to Supabase...")
        copy_to_postgres(conn, temp_csv_path, db_columns)

        with conn.cursor() as cur:
            cur.execute(
                f"SELECT count(*) FROM {q_ident(TABLE_SCHEMA)}.{q_ident(TABLE_NAME)} WHERE upload_batch_id = %s",
                (batch_id,)
            )
            uploaded_count = cur.fetchone()[0]

        print(f"Done. Uploaded {uploaded_count:,} rows.")
        print(f"Batch id: {batch_id}")

    finally:
        conn.close()
        if temp_csv_path is not None:
            try:
                temp_csv_path.unlink(missing_ok=True)
            except Exception:
                pass


if __name__ == "__main__":
    main()
