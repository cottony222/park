// 사방넷 이미지호스팅 - 폴더 안 모든 이미지 주소를 CSV로 내려받는 스크립트
//
// 사용법
// 1. 사방넷 > 부가기능 > 이미지호스팅을 연다 (이미지호스팅 창이 뜬 상태)
// 2. 그 이미지호스팅 창에서 F12 → Console 탭
//    (크롬이 붙여넣기를 막으면 "allow pasting" 입력 후 Enter)
// 3. 이 파일 내용을 전부 붙여넣고 Enter
// 4. "이미지호스팅_주소목록.csv" 파일이 자동으로 내려받아진다
//
// 브라우저에 이미 로그인된 정보로 목록만 읽어온다. 외부로 전송하는 것은 없다.

(async () => {
  const ROOT_NAME = '00.이지앤프리'; // 추출할 최상위 폴더명 (비워두면 전체)
  const PAGE_SIZE = 100;

  const TOKEN_KEY = 'authenticationToken';
  const getToken = () => JSON.parse(sessionStorage.getItem(TOKEN_KEY));

  async function api(path) {
    const res = await fetch(path, {
      headers: { Accept: 'application/json', Authorization: `Bearer ${getToken()}` },
    });
    const newToken = res.headers.get('Authorization');
    if (newToken) sessionStorage.setItem(TOKEN_KEY, JSON.stringify(newToken));
    if (!res.ok) throw new Error(`${path} → ${res.status}`);
    return { data: await res.json(), total: Number(res.headers.get('X-Total-Count')) || 0 };
  }

  // 폴더 하나의 전체 항목 (페이지 넘겨가며 수집, id 기준 중복 제거)
  async function listFolder(id) {
    const base = id ? `/api/imagehost/${id}` : '/api/imagehost/';
    const items = new Map();
    for (let page = 0; page < 1000; page++) {
      const q = new URLSearchParams({ page, size: PAGE_SIZE });
      q.append('sort', 'name,asc');
      const { data, total } = await api(`${base}?${q}`);
      const list = Array.isArray(data) ? data : data.content || [];
      const before = items.size;
      list.forEach((it) => items.set(it.id, it));
      if (items.size === before || list.length < PAGE_SIZE || (total && items.size >= total)) break;
    }
    return [...items.values()];
  }

  const rows = [];
  async function walk(folder, path) {
    const items = await listFolder(folder?.id);
    for (const it of items) {
      if (it.isDir) {
        await walk(it, [...path, it.name]);
      } else if (it.imageUrl) {
        rows.push({ 상품폴더: path[1] || '', 하위폴더: path.slice(2).join('/'), 파일명: it.name, 주소: it.imageUrl });
      }
    }
    console.log(`읽는 중... ${path.join(' > ') || '홈'} (누적 ${rows.length}개)`);
  }

  const top = await listFolder(0);
  const roots = ROOT_NAME ? top.filter((it) => it.isDir && it.name === ROOT_NAME) : [{ id: 0, name: '홈' }];
  if (!roots.length) throw new Error(`"${ROOT_NAME}" 폴더를 찾지 못했습니다. 최상위 폴더: ${top.map((t) => t.name).join(', ')}`);
  for (const r of roots) await walk(r.id ? r : null, [r.name]);

  const esc = (v) => `"${String(v).replace(/"/g, '""')}"`;
  const header = ['상품폴더', '하위폴더', '파일명', '주소'];
  const csv = '﻿' + [header.map(esc).join(','), ...rows.map((r) => header.map((h) => esc(r[h])).join(','))].join('\r\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  a.download = '이미지호스팅_주소목록.csv';
  a.click();

  console.table(rows.slice(0, 20));
  console.log(`완료: 이미지 ${rows.length}개 → 이미지호스팅_주소목록.csv`);
})().catch((e) => console.error('실패:', e));
