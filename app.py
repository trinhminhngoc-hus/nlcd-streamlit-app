import importlib
import json

import ee
import streamlit as st
import geemap as geemap_package


# Tương thích với một số phiên bản geemap/leafmap khi dùng foliumap.
geemap_package.basemaps = importlib.import_module("geemap.basemaps")
import geemap.foliumap as geemap  # noqa: E402


PROJECT_ID = "gee-ngoc-2025"
NLCD_COLLECTION = "USGS/NLCD_RELEASES/2021_REL/NLCD"


st.set_page_config(
    page_title="NLCD Land Cover",
    page_icon="🗺️",
    layout="wide",
)


@st.cache_resource(show_spinner=False)
def initialize_earth_engine():
    """Khởi tạo Earth Engine bằng Service Account trên Streamlit Cloud."""
    if "gcp_service_account" not in st.secrets:
        raise RuntimeError(
            "Chưa tìm thấy mục [gcp_service_account] trong Streamlit Secrets."
        )

    service_account_info = dict(st.secrets["gcp_service_account"])

    required_fields = (
        "type",
        "project_id",
        "private_key",
        "client_email",
        "token_uri",
    )
    missing_fields = [
        field for field in required_fields if not service_account_info.get(field)
    ]
    if missing_fields:
        raise RuntimeError(
            "Streamlit Secrets đang thiếu trường: " + ", ".join(missing_fields)
        )

    # Hỗ trợ cả private_key có xuống dòng thật và private_key chứa ký tự \\n.
    service_account_info["private_key"] = service_account_info[
        "private_key"
    ].replace("\\n", "\n")

    credentials = ee.ServiceAccountCredentials(
        service_account_info["client_email"],
        key_data=json.dumps(service_account_info),
    )

    ee.Initialize(
        credentials=credentials,
        project=service_account_info.get("project_id", PROJECT_ID),
    )

    # Một yêu cầu nhỏ để phát hiện sớm lỗi khóa, IAM hoặc đăng ký Earth Engine.
    ee.Number(1).getInfo()


@st.cache_data(ttl=3600, show_spinner=False)
def get_available_years():
    """Đọc danh sách năm có thật trong bộ NLCD hiện hành."""
    indexes = (
        ee.ImageCollection(NLCD_COLLECTION)
        .aggregate_array("system:index")
        .getInfo()
    )
    return sorted((str(value) for value in indexes), key=int)


def get_nlcd(year):
    """Lấy ảnh land cover của một năm NLCD."""
    return (
        ee.ImageCollection(NLCD_COLLECTION)
        .filter(ee.Filter.eq("system:index", str(year)))
        .first()
        .select("landcover")
    )


st.title("National Land Cover Database (NLCD)")
st.caption("Bản đồ lớp phủ đất Hoa Kỳ từ Google Earth Engine")

try:
    initialize_earth_engine()
except Exception as error:
    st.error("Không thể khởi tạo Google Earth Engine bằng Service Account.")
    st.code(str(error))
    st.info(
        "Hãy kiểm tra Streamlit Secrets, quyền IAM của Service Account và việc "
        "dự án Google Cloud đã được đăng ký Earth Engine."
    )
    st.stop()

try:
    years = get_available_years()
except Exception as error:
    st.error("Đã đăng nhập nhưng không đọc được bộ dữ liệu NLCD.")
    st.code(str(error))
    st.info(
        "Service Account cần được phép sử dụng Earth Engine trong dự án "
        f"{PROJECT_ID}."
    )
    st.stop()

control_col, map_col = st.columns([1, 3])

with control_col:
    selected_years = st.multiselect(
        "Select years",
        options=years,
        default=["2019"] if "2019" in years else years[-1:],
    )
    add_legend = st.checkbox("Show legend", value=True)
    st.success("Earth Engine đã kết nối")

Map = geemap.Map(center=[40, -100], zoom=4)
layer_errors = []

for year in selected_years:
    try:
        Map.addLayer(get_nlcd(year), {}, f"NLCD {year}")
    except Exception as error:
        layer_errors.append((year, str(error)))

if add_legend:
    Map.add_legend(title="NLCD Land Cover", builtin_legend="NLCD")

with map_col:
    if not selected_years:
        st.info("Hãy chọn ít nhất một năm để hiển thị lớp NLCD.")

    try:
        Map.to_streamlit(height=650)
    except Exception as error:
        st.error("Không thể hiển thị bản đồ.")
        st.code(str(error))

if layer_errors:
    st.warning("Một số lớp NLCD không tải được:")
    for year, message in layer_errors:
        st.code(f"NLCD {year}: {message}")
