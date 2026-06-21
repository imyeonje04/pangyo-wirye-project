"""
업무·상업 건물 지오코딩 → 밀집구역 폴리곤(Convex Hull) 추출
판교(삼평동) + 위례(창곡동·학암동)

사용 전: API_KEY를 본인 VWorld 키로 교체
실행: python geocode_biz.py
"""

import requests, time, json
import pandas as pd
import geopandas as gpd
from shapely.geometry import MultiPoint, Point, mapping

# ── 본인 VWorld 키 입력 ──────────────────────────
API_KEY = "YOUR_API_KEY"
# ────────────────────────────────────────────────

df = pd.read_csv('biz_buildings.csv', encoding='utf-8-sig')

GEOCODE_URL = "https://api.vworld.kr/req/address"

def geocode(addr):
    params = {
        'service':'address','request':'getcoord','version':'2.0',
        'crs':'EPSG:4326','address':addr,'type':'PARCEL',
        'key':API_KEY,
    }
    try:
        r = requests.get(GEOCODE_URL, params=params, timeout=10).json()
        if r['response']['status']=='OK':
            pt = r['response']['result']['point']
            return float(pt['x']), float(pt['y'])
    except:
        pass
    return None, None

# 지오코딩
results=[]
for i,row in df.iterrows():
    ji = str(row['지']).replace('.0','')
    bun = str(row['번']).replace('.0','')
    addr = f"{row['시도']} {row['시군구']} {row['법정동']} {bun}-{ji}"
    lng,lat = geocode(addr)
    results.append({'zone':row['zone'],'addr':addr,'건물명':row['건물명'],
                    '연면적':row['연면적(㎡)'],'lng':lng,'lat':lat})
    print(f"[{i+1}/{len(df)}] {row['건물명'][:20]:20s} → {lng},{lat}")
    time.sleep(0.1)

gdf = pd.DataFrame(results).dropna(subset=['lng','lat'])
print(f"\n지오코딩 성공: {len(gdf)}/{len(df)}건")

# zone별 밀집구역 폴리곤 (convex hull + buffer)
features=[]
for zone,color in [('판교','#2563eb'),('위례','#dc2626')]:
    pts = gdf[gdf['zone']==zone]
    geom = MultiPoint([Point(r['lng'],r['lat']) for _,r in pts.iterrows()])
    hull = geom.convex_hull
    # 100m 버퍼 (약 0.001도)
    hull_buf = hull.buffer(0.0009)
    features.append({'type':'Feature','properties':{
        'id':zone,'name':f'{zone} 업무·상업 밀집구역','n_buildings':len(pts),
        'color':color,'source':'건축물대장 업무상업건물 지오코딩 Convex Hull'
    },'geometry':mapping(hull_buf)})
    # 개별 건물 포인트도 저장
    for _,r in pts.iterrows():
        features.append({'type':'Feature','properties':{
            'zone':zone,'name':r['건물명'],'연면적':r['연면적'],'type':'building','color':color
        },'geometry':mapping(Point(r['lng'],r['lat']))})

fc={'type':'FeatureCollection','features':features}
with open('zones_precise.geojson','w',encoding='utf-8') as f:
    json.dump(fc,f,ensure_ascii=False,indent=2)
print('✅ zones_precise.geojson 저장')

# 면적 출력
for zone in ['판교','위례']:
    poly=[f for f in features if f['properties'].get('id')==zone][0]
    g=gpd.GeoSeries([gpd.GeoSeries.from_wkt([None])[0] if False else __import__('shapely').geometry.shape(poly['geometry'])],crs=4326).to_crs(5179)
    print(f"{zone} 밀집구역 면적: {g.area.iloc[0]/10000:.1f} ha / 건물 {poly['properties']['n_buildings']}개")
