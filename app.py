#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聖書協会共同訳 対照アプリ
左右両パネルとも聖書協会共同訳（jbsbibleapp.com）を表示し、それぞれ異なる箇所を選択できる
"""

from flask import Flask, render_template, jsonify, request
import requests
import re
import json
import os

app = Flask(__name__)

CACHE = {}
_state = {'jbs_logged_in': False, 'jbs_email': ''}

JBS_SESSION = requests.Session()
JBS_SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'X-Requested-With': 'XMLHttpRequest',
    'Origin': 'https://si.jbsbibleapp.com',
    'Referer': 'https://si.jbsbibleapp.com/',
})

BOOKS = [
    # 旧約聖書
    {'id': 'GEN', 'name': '創世記',           'chapters': 50},
    {'id': 'EXO', 'name': '出エジプト記',      'chapters': 40},
    {'id': 'LEV', 'name': 'レビ記',            'chapters': 27},
    {'id': 'NUM', 'name': '民数記',            'chapters': 36},
    {'id': 'DEU', 'name': '申命記',            'chapters': 34},
    {'id': 'JOS', 'name': 'ヨシュア記',        'chapters': 24},
    {'id': 'JDG', 'name': '士師記',            'chapters': 21},
    {'id': 'RUT', 'name': 'ルツ記',            'chapters': 4},
    {'id': '1SA', 'name': 'サムエル記上',      'chapters': 31},
    {'id': '2SA', 'name': 'サムエル記下',      'chapters': 24},
    {'id': '1KI', 'name': '列王記上',          'chapters': 22},
    {'id': '2KI', 'name': '列王記下',          'chapters': 25},
    {'id': '1CH', 'name': '歴代志上',          'chapters': 29},
    {'id': '2CH', 'name': '歴代志下',          'chapters': 36},
    {'id': 'EZR', 'name': 'エズラ記',          'chapters': 10},
    {'id': 'NEH', 'name': 'ネヘミヤ記',        'chapters': 13},
    {'id': 'EST', 'name': 'エステル記',        'chapters': 10},
    {'id': 'JOB', 'name': 'ヨブ記',            'chapters': 42},
    {'id': 'PSA', 'name': '詩編',              'chapters': 150},
    {'id': 'PRO', 'name': '箴言',              'chapters': 31},
    {'id': 'ECC', 'name': 'コヘレトの言葉',    'chapters': 12},
    {'id': 'SNG', 'name': '雅歌',              'chapters': 8},
    {'id': 'ISA', 'name': 'イザヤ書',          'chapters': 66},
    {'id': 'JER', 'name': 'エレミヤ書',        'chapters': 52},
    {'id': 'LAM', 'name': '哀歌',              'chapters': 5},
    {'id': 'EZK', 'name': 'エゼキエル書',      'chapters': 48},
    {'id': 'DAN', 'name': 'ダニエル書',        'chapters': 12},
    {'id': 'HOS', 'name': 'ホセア書',          'chapters': 14},
    {'id': 'JOL', 'name': 'ヨエル書',          'chapters': 3},
    {'id': 'AMO', 'name': 'アモス書',          'chapters': 9},
    {'id': 'OBA', 'name': 'オバデヤ書',        'chapters': 1},
    {'id': 'JON', 'name': 'ヨナ書',            'chapters': 4},
    {'id': 'MIC', 'name': 'ミカ書',            'chapters': 7},
    {'id': 'NAM', 'name': 'ナホム書',          'chapters': 3},
    {'id': 'HAB', 'name': 'ハバクク書',        'chapters': 3},
    {'id': 'ZEP', 'name': 'ゼファニヤ書',      'chapters': 3},
    {'id': 'HAG', 'name': 'ハガイ書',          'chapters': 2},
    {'id': 'ZEC', 'name': 'ゼカリヤ書',        'chapters': 14},
    {'id': 'MAL', 'name': 'マラキ書',          'chapters': 4},
    # 新約聖書
    {'id': 'MAT', 'name': 'マタイによる福音書',            'chapters': 28},
    {'id': 'MRK', 'name': 'マルコによる福音書',            'chapters': 16},
    {'id': 'LUK', 'name': 'ルカによる福音書',              'chapters': 24},
    {'id': 'JHN', 'name': 'ヨハネによる福音書',            'chapters': 21},
    {'id': 'ACT', 'name': '使徒言行録',                    'chapters': 28},
    {'id': 'ROM', 'name': 'ローマの信徒への手紙',          'chapters': 16},
    {'id': '1CO', 'name': 'コリントの信徒への手紙一',      'chapters': 16},
    {'id': '2CO', 'name': 'コリントの信徒への手紙二',      'chapters': 13},
    {'id': 'GAL', 'name': 'ガラテヤの信徒への手紙',        'chapters': 6},
    {'id': 'EPH', 'name': 'エフェソの信徒への手紙',        'chapters': 6},
    {'id': 'PHP', 'name': 'フィリピの信徒への手紙',        'chapters': 4},
    {'id': 'COL', 'name': 'コロサイの信徒への手紙',        'chapters': 4},
    {'id': '1TH', 'name': 'テサロニケの信徒への手紙一',    'chapters': 5},
    {'id': '2TH', 'name': 'テサロニケの信徒への手紙二',    'chapters': 3},
    {'id': '1TI', 'name': 'テモテへの手紙一',              'chapters': 6},
    {'id': '2TI', 'name': 'テモテへの手紙二',              'chapters': 4},
    {'id': 'TIT', 'name': 'テトスへの手紙',                'chapters': 3},
    {'id': 'PHM', 'name': 'フィレモンへの手紙',            'chapters': 1},
    {'id': 'HEB', 'name': 'ヘブライ人への手紙',            'chapters': 13},
    {'id': 'JAS', 'name': 'ヤコブの手紙',                  'chapters': 5},
    {'id': '1PE', 'name': 'ペトロの手紙一',                'chapters': 5},
    {'id': '2PE', 'name': 'ペトロの手紙二',                'chapters': 3},
    {'id': '1JN', 'name': 'ヨハネの手紙一',                'chapters': 5},
    {'id': '2JN', 'name': 'ヨハネの手紙二',                'chapters': 1},
    {'id': '3JN', 'name': 'ヨハネの手紙三',                'chapters': 1},
    {'id': 'JUD', 'name': 'ユダの手紙',                    'chapters': 1},
    {'id': 'REV', 'name': 'ヨハネの黙示録',                'chapters': 22},
]

BOOK_MAP = {b['id']: b for b in BOOKS}


def strip_html(text):
    return re.sub(r'<[^>]+>', '', text).strip()


def jbs_login(email, password):
    global JBS_SESSION
    JBS_SESSION = requests.Session()
    JBS_SESSION.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://si.jbsbibleapp.com',
        'Referer': 'https://si.jbsbibleapp.com/',
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
    })
    resp = JBS_SESSION.post(
        'https://api.si.jbsbibleapp.com/api/v1/auth/signin',
        json={'email': email, 'password': password},
        timeout=15
    )
    if resp.status_code == 200:
        for k in list(CACHE.keys()):
            if k.startswith('jbs_'):
                del CACHE[k]
        return True, resp.json() if resp.text else {}
    else:
        try:
            msg = resp.json().get('message', resp.text[:200])
        except Exception:
            msg = resp.text[:200]
        return False, msg


def _auto_login_from_env():
    email    = os.environ.get('JBS_EMAIL', '').strip()
    password = os.environ.get('JBS_PASSWORD', '').strip()
    if email and password:
        try:
            ok, _ = jbs_login(email, password)
            if ok:
                _state['jbs_logged_in'] = True
                _state['jbs_email'] = email
                print(f'[auto-login] JBS ログイン成功: {email}')
            else:
                print(f'[auto-login] JBS ログイン失敗')
        except Exception as e:
            print(f'[auto-login] エラー: {e}')


def jbs_fetch_chapter(book, chapter):
    key = f'jbs_{book}_{chapter}'
    if key in CACHE:
        return CACHE[key]

    url = f'https://api.si.jbsbibleapp.com/api/v1/bible/SI/{book}/{chapter - 1}'

    for attempt in range(2):
        try:
            resp = JBS_SESSION.get(url, timeout=20)
        except Exception as e:
            if attempt == 0:
                _auto_login_from_env()
                continue
            return {'error': f'接続エラー: {e}', 'items': [], 'count': 0}

        if resp.status_code in (401, 403):
            if attempt == 0:
                _auto_login_from_env()
                continue
            return {'error': 'not_logged_in', 'items': [], 'count': 0}
        if resp.status_code != 200:
            return {'error': f'HTTP {resp.status_code}', 'items': [], 'count': 0}
        break

    try:
        data = resp.json()
    except Exception:
        return {'error': 'parse_error', 'items': [], 'count': 0}

    items = []
    book_info = BOOK_MAP.get(book, {'name': book})

    if isinstance(data, dict) and 'html' in data:
        html = data['html']

        def jbs_strip(inner):
            s = inner
            s = re.sub(r'<span[^>]*class="[^"]*\b(?:x|f)\b[^"]*"[^>]*>.*?</span>', '', s, flags=re.DOTALL)
            s = re.sub(r'<span[^>]*class="[^"]*v-number[^"]*"[^>]*>.*?</span>', '', s, flags=re.DOTALL)
            s = re.sub(r'<svg\b[^>]*>.*?</svg>', '', s, flags=re.DOTALL)
            s = re.sub(r'<rt>[^<]*</rt>', '', s)
            s = re.sub(r'</?ruby[^>]*>', '', s)
            s = strip_html(s)
            return re.sub(r'\s+', ' ', s).strip()

        para_list = []
        for pm in re.finditer(r'<p\b([^>]*)>(.*?)</p>', html, re.DOTALL):
            cls_m = re.search(r'class="([^"]*)"', pm.group(1))
            cls = cls_m.group(1) if cls_m else ''
            para_list.append((pm.start(), cls, pm.group(2)))

        para_verse_frags = []
        HEADING_CLASSES = {'s', 's1', 's2', 's3'}
        for p_start, p_cls, p_inner in para_list:
            if p_cls in HEADING_CLASSES:
                text = jbs_strip(p_inner)
                if text:
                    para_verse_frags.append((p_cls, 'heading', text))
                continue
            # index は合節 (例: "3-4", "3,4") の場合があるため数字のみに限定しない
            frags = []
            for vm in re.finditer(r'<a[^>]*class="[^"]*\bv\b[^"]*"[^>]*index="([^"]+)"[^>]*>(.*?)</a>', p_inner, re.DOTALL):
                idx_raw = vm.group(1)
                nums = re.findall(r'\d+', idx_raw)
                if not nums:
                    continue
                vnum = int(nums[0])
                # 表示ラベル: 合節はそのままの表記 (例: 3-4)、単節は数字
                label = idx_raw.strip() if len(nums) > 1 else str(vnum)
                # 本文中の節番号表記 (v-number) があればそちらを優先
                lbl_m = re.search(r'<span[^>]*class="[^"]*v-number[^"]*"[^>]*>(.*?)</span>', vm.group(2), re.DOTALL)
                if lbl_m:
                    lbl_text = re.sub(r'\s+', '', strip_html(lbl_m.group(1)))
                    if lbl_text:
                        label = lbl_text
                text = jbs_strip(vm.group(2))
                if text:
                    frags.append((vnum, label, text))
            if frags:
                para_verse_frags.append((p_cls, 'verse', frags))

        cur_lines = []
        PARA_BREAK_CLASSES = {'p', 'pi', 'm', 'mi', 'nb'}

        def flush_jbs():
            if cur_lines:
                items.append({'type': 'para', 'lines': list(cur_lines)})
                cur_lines.clear()

        for entry in para_verse_frags:
            p_cls, etype = entry[0], entry[1]
            if etype == 'heading':
                flush_jbs()
                items.append({'type': 'heading', 'text': entry[2]})
            elif etype == 'verse':
                frags = entry[2]
                first_vnum = frags[0][0]
                if p_cls in PARA_BREAK_CLASSES and cur_lines and cur_lines[-1]['num'] != first_vnum:
                    flush_jbs()
                # 各節のラベルとテキストを保持（合節は "3-4" 表記）
                cur_lines.append({
                    'num': frags[0][0],
                    'parts': [[label, text] for vnum, label, text in frags]
                })

        flush_jbs()

    elif isinstance(data, dict) and 'verses' in data:
        verses = []
        for v in data['verses']:
            vnum = v.get('order') or v.get('verse') or v.get('num')
            text = strip_html(v.get('text') or v.get('content') or '')
            if vnum and text:
                verses.append({'num': int(vnum), 'text': text})
        if verses:
            items.append({'type': 'para', 'verses': sorted(verses, key=lambda x: x['num'])})

    elif isinstance(data, list):
        verses = []
        for v in data:
            vnum = v.get('order') or v.get('verse') or v.get('num')
            text = strip_html(v.get('text') or v.get('content') or '')
            if vnum and text:
                verses.append({'num': int(vnum), 'text': text})
        if verses:
            items.append({'type': 'para', 'verses': sorted(verses, key=lambda x: x['num'])})

    total = sum(len(i.get('lines', [])) for i in items if i['type'] == 'para')
    result = {
        'title': f'{book_info["name"]} {chapter}章',
        'items': items,
        'count': total,
    }
    CACHE[key] = result
    return result


# ── Flask ルート ─────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html', books=BOOKS)


@app.route('/api/chapter')
def get_chapter():
    book = request.args.get('book', 'MAT')
    try:
        chapter = int(request.args.get('chapter', '1'))
    except ValueError:
        chapter = 1

    if not _state.get('jbs_logged_in'):
        _auto_login_from_env()

    if not _state.get('jbs_logged_in'):
        return jsonify({'error': 'not_logged_in', 'items': [], 'count': 0})

    try:
        result = jbs_fetch_chapter(book, chapter)
    except Exception as e:
        result = {'error': str(e), 'items': [], 'count': 0}

    return jsonify(result)


@app.route('/api/media')
def get_media():
    """章の公式朗読音声（Vimeo HLS）のURLを取得。
    埋め込みはドメイン制限があるため、サーバー側でReferer付きで
    Vimeo埋め込みページを取得し、playerConfigからHLS URLを抽出して返す。
    署名付きURLは期限があるためキャッシュしない。"""
    book = request.args.get('book', 'MAT')
    try:
        chapter = int(request.args.get('chapter', '1'))
    except ValueError:
        chapter = 1

    if not _state.get('jbs_logged_in'):
        _auto_login_from_env()
    if not _state.get('jbs_logged_in'):
        return jsonify({'error': 'not_logged_in'})

    # 章データからVimeo情報を取得（認証切れ・接続エラー時は再ログインして1回リトライ）
    url = f'https://api.si.jbsbibleapp.com/api/v1/bible/SI/{book}/{chapter - 1}'
    data = None
    for attempt in range(2):
        try:
            resp = JBS_SESSION.get(url, timeout=20)
        except Exception as e:
            if attempt == 0:
                _auto_login_from_env()
                continue
            return jsonify({'error': f'接続エラー: {e}'})
        if resp.status_code in (401, 403):
            if attempt == 0:
                _auto_login_from_env()
                continue
            return jsonify({'error': 'not_logged_in'})
        if resp.status_code != 200:
            return jsonify({'error': f'HTTP {resp.status_code}'})
        try:
            data = resp.json()
        except Exception:
            return jsonify({'error': 'parse_error'})
        # ログイン状態が不完全だとmedia_librariesが欠けることがある → 再ログインして1回だけ再取得
        if not (data or {}).get('media_libraries') and attempt == 0:
            _auto_login_from_env()
            continue
        break

    ml = (data or {}).get('media_libraries') or {}
    vimeo = (ml.get('vimeo') or {}).get('data') or {}
    embed_url = vimeo.get('player_embed_url')
    if not embed_url:
        return jsonify({'error': 'no_media'})

    try:
        sep = '&' if '?' in embed_url else '?'
        r = requests.get(
            embed_url + sep + 'app_id=228373',
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
                'Referer': 'https://si.jbsbibleapp.com/',
            },
            timeout=20,
        )
        m = re.search(r'window\.playerConfig\s*=\s*(\{.*)', r.text)
        if not m:
            return jsonify({'error': 'player_config_not_found'})
        cfg, _ = json.JSONDecoder().raw_decode(m.group(1))
        cdns = cfg['request']['files']['hls']['cdns']
        cdn = cdns.get('fastly_skyfire') or cdns.get('akfire_interconnect_quic') or next(iter(cdns.values()))
        return jsonify({'url': cdn['url'], 'duration': vimeo.get('duration')})
    except Exception as e:
        return jsonify({'error': f'media_fetch: {e}'})


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email    = data.get('email', '').strip()
    password = data.get('password', '').strip()

    if not email or not password:
        return jsonify({'ok': False, 'message': 'メールアドレスとパスワードを入力してください'})

    ok, result = jbs_login(email, password)

    if ok:
        _state['jbs_email'] = email
        _state['jbs_logged_in'] = True
        return jsonify({'ok': True})
    else:
        _state['jbs_logged_in'] = False
        return jsonify({'ok': False, 'message': str(result)})


@app.route('/api/logout', methods=['POST'])
def api_logout():
    global JBS_SESSION
    JBS_SESSION = requests.Session()
    _state['jbs_logged_in'] = False
    _state['jbs_email'] = ''
    for k in list(CACHE.keys()):
        if k.startswith('jbs_'):
            del CACHE[k]
    return jsonify({'ok': True})


@app.route('/api/status')
def api_status():
    if not _state.get('jbs_logged_in'):
        _auto_login_from_env()
    return jsonify({
        'logged_in': _state.get('jbs_logged_in', False),
        'email': _state.get('jbs_email', ''),
    })


_auto_login_from_env()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5052))
    print(f'聖書協会共同訳対照アプリを起動します: http://localhost:{port}')
    app.run(host='0.0.0.0', debug=False, port=port)
