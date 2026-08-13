import importlib
import json

import ee
import streamlit as st
import geemap as geemap_package


# Tương thích với một số phiên bản geemap/leafmap trên Streamlit Cloud.
geemap_package.basemaps = importlib.import_module("geemap.basemaps")
import geemap.foliumap as geemap  # noqa: E402


PROJECT_ID = "gee-ngoc-2025"

NLCD_YEARS = [
    "2001",
    "2004",
    "2006",
    "2008",
    "2011",
    "2013",
    "2016",
    "2019",
    "2021",
]

NLCD_VALUES = [
    11, 12, 21, 22, 23, 24, 31, 41, 42, 43,
    52, 71, 72, 73, 74, 81, 82, 90, 95,
]

NLCD_COLORS = [
    "466b9f", "d1def8", "dec5c5", "d99282", "eb0000",
    "ab0000", "b3ac9f", "68ab5f", "1c5f2c", "b5c58f",
    "af963c", "ccb879", "dfdfc2", "d1d182", "a3cc51",
    "dcd939", "ab6c28", "b8d9eb", "6c9fb8",
]


st.set_page_config(
    page_title="NLCD Land Cover",
    page_icon="🗺️",
    layout="wide",
)


@st.cache_resource
def initialize_earth_engine():
    """Khởi tạo Earth Engine bằng Streamlit Secrets hoặc tài khoản cục bộ."""
    if "gcp_service_account" in st.secrets:
        service_account_info = dict(st.secrets["gcp_service_account"])
        credentials = ee.ServiceAccountCredentials(
            service_account_info["client_email"],
            key_data=json.dumps(service_account_info),
        )
        ee.Initialize(
            credentials=credentials,
            project=service_account_info.get("project_id", PROJECT_ID),
        )
        return "Service Account"

    # Dùng thông tin đăng nhập đã có trên máy khi chạy cục bộ.
    # Không gọi ee.Authenticate() trong ứng dụng web.
    ee.Initialize(project=PROJECT_ID)
    return "Tài khoản cục bộ"


def get_nlcd(year):
    """Lấy ảnh lớp phủ đất NLCD Collection 2021 cho một năm."""
    image = (
        ee.ImageCollection("USGS/NLCD_RELEASES/2021_REL/NLCD")
        .filter(ee.Filter.eq("system:index", str(year)))
        .first()
        .select("landcover")
    )

    # Đổi mã lớp rời rạc sang 0..18 để màu hiển thị đúng theo từng lớp.
    return image.remap(
        NLCD_VALUES,
        list(range(len(NLCD_VALUES))),
    ).rename("landcover")


st.title("National Land Cover Database (NLCD)")
st.caption("Bản đồ lớp phủ đất Hoa Kỳ từ Google Earth Engine")

try:
    auth_method = initialize_earth_engine()
    ee_ready = True
except Exception as error:
    ee_ready = False
    st.error("Không thể kết nối Google Earth Engine.")
    st.code(f"{type(error).__name__}: {error}")
    st.info(
        "Hãy kiểm tra mục gcp_service_account trong Streamlit Secrets và "
        "quyền Earth Engine của Service Account."
    )
    st.stop()


control_col, map_col = st.columns([1, 3])

with control_col:
    selected_years = st.multiselect(
        "Select years",
        NLCD_YEARS,
        default=["2021"],
    )
    add_legend = st.checkbox("Show legend", value=True)
    if ee_ready:
        st.success(f"Earth Engine đã kết nối ({auth_method})")


Map = geemap.Map(center=[39, -98], zoom=4)
vis_params = {
    "min": 0,
    "max": len(NLCD_VALUES) - 1,
    "palette": NLCD_COLORS,
}

load_errors = []
loaded_years = []

for year in selected_years:
    try:
        Map.addLayer(get_nlcd(year), vis_params, f"NLCD {year}")
        loaded_years.append(year)
    except Exception as error:
        load_errors.append(f"NLCD {year}: {type(error).__name__}: {error}")

if add_legend:
    Map.add_legend(
        title="NLCD Land Cover",
        builtin_legend="NLCD",
    )

with map_col:
    Map.to_streamlit(height=650)

if not selected_years:
    st.info("Hãy chọn ít nhất một năm để hiển thị lớp NLCD.")
elif loaded_years:
    st.caption("Đã tải: " + ", ".join(loaded_years))

if load_errors:
    st.warning("Một số lớp NLCD không tải được:")
    st.code("\n\n".join(load_errors))
