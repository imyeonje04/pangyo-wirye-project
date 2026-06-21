"""
VWorld WFS API - 토지이용계획 용도지역 데이터 수집
판교테크노밸리 + 위례신도시 업무·상업용지 일대

사용 전: API_KEY 값을 본인 키로 교체하세요
"""

import requests
import json
import geopandas as gpd
from pathlib import Path

# ── 여기에 본인 API 키 입력 ──────────────────────
API_KEY = "YOUR_API_KEY"
# ────────────────────────────────────────────────

OUT_DIR = Path('/home/claude/analysis/output')
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 구역별 바운딩박스 (WGS84 경도,위도)
ZONES = {
    '판교': {
        'bbox': '127.097,37.386,127.129,37.403',
    },
    '위례': {
        'bbox': '127.119,37.460,127.153,37.482',
    }
}

WFS_URL = "https://api.vworld.kr/req/wfs"

def fetch_landuse(zone_name, bbox):
    params = {
        'SERVICE'     : 'WFS',
        'VERSION'     : '2.0.0',
        'REQUEST'     : 'GetFeature',
        'TYPENAME'    : 'lt_c_uq111',   # 용도지역지구 레이어
        'BBOX'        : bbox,
        'SRSNAME'     : 'EPSG:4326',
        'OUTPUTFORMAT': 'application/json',
        'KEY'         : API_KEY,
        'DOMAIN'      : 'localhost',
    }

    print(f"▶ [{zone_name}] WFS 요청 중...")
    res = requests.get(WFS_URL, params=params, timeout=30)
    
    if res.status_code != 200:
        print(f"  ❌ HTTP 오류: {res.status_code}")
        return None

    data = res.json()
    
    if 'features' not in data:
        print(f"  ❌ 응답 오류: {data}")
        return None

    features = data['features']
    print(f"  ✅ {len(features)}개 폴리곤 수신")
    return data

# 두 구역 수집
all_features = []
for name, info in ZONES.items():
    fc = fetch_landuse(name, info['bbox'])
    if fc:
        for feat in fc['features']:
            feat['properties']['zone'] = name
        all_features.extend(fc['features'])

if all_features:
    result = {"type": "FeatureCollection", "features": all_features}
    out = OUT_DIR / 'landuse.geojson'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 저장 완료: {out}")

    # 용도지역 분포 요약
    gdf = gpd.GeoDataFrame.from_features(all_features, crs=4326)
    print("\n[ 용도지역 분포 ]")
    if 'uname' in gdf.columns:
        print(gdf.groupby(['zone','uname']).size().to_string())
    else:
        print("컬럼 목록:", gdf.columns.tolist())
        print(gdf.head(3).to_string())
else:
    print("\n❌ 데이터 수집 실패 — API 키 또는 레이어명 확인 필요")
    print("레이어명 확인용 GetCapabilities:")
    print(f"https://api.vworld.kr/req/wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities&KEY={API_KEY}&DOMAIN=localhost")
