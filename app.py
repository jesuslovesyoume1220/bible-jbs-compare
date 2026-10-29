#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聖書協会訳対照
左右両パネルとも聖書協会共同訳（jbsbibleapp.com）を表示し、それぞれ異なる箇所を選択できる
"""

from flask import Flask, render_template, jsonify, request, session
from datetime import timedelta
import requests
import re
import json
import os
import secrets

app = Flask(__name__)

CACHE = {}

# ── 端末ごとのログイン ───────────────────────────────────────
# JBSのログイン状態（Cookie）はサーバーに1つだけ持たず、各端末のブラウザに
# 署名付きCookieとして持たせる。パスワードはログイン時に1回使うだけで保存しない。
def _secret_key():
    """Cookie署名用の鍵。Hugging Face では Secrets の SECRET_KEY、Mac では .secret_key ファイル"""
    key = os.environ.get('SECRET_KEY', '').strip()
    if key:
        return key
    path = os.path.join(os.path.dirname(__file__), '.secret_key')
    try:
        with open(path, encoding='utf-8') as f:
            key = f.read().strip()
        if key:
            return key
    except OSError:
        pass
    key = secrets.token_hex(32)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(key)
        os.chmod(path, 0o600)
    except OSError:
        pass  # 書き込めなければ再起動のたびにログインし直しになるだけ
    return key


app.secret_key = _secret_key()
_ON_HF = bool(os.environ.get('SPACE_ID'))  # Hugging Face Spaces 上（HTTPS・iframe表示あり）
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=_ON_HF,
    SESSION_COOKIE_SAMESITE='None' if _ON_HF else 'Lax',
    SESSION_COOKIE_PARTITIONED=_ON_HF,
    PERMANENT_SESSION_LIFETIME=timedelta(days=90),
)

JBS_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'X-Requested-With': 'XMLHttpRequest',
    'Origin': 'https://si.jbsbibleapp.com',
    'Referer': 'https://si.jbsbibleapp.com/',
    'Accept': 'application/json, text/plain, */*',
    'Content-Type': 'application/json',
}


def jbs_session():
    """この端末のJBSログインCookieを載せたセッションを作る"""
    s = requests.Session()
    s.headers.update(JBS_HEADERS)
    for c in session.get('jbs_cookies', []):
        s.cookies.set(c['name'], c['value'], domain=c['domain'], path=c['path'])
    return s


def jbs_keep_cookies(s):
    """JBS側でCookieが更新されていれば、この端末の保存分も更新する"""
    cookies = [{'name': c.name, 'value': c.value, 'domain': c.domain, 'path': c.path}
               for c in s.cookies]
    if cookies != session.get('jbs_cookies'):
        session['jbs_cookies'] = cookies


def jbs_logged_in():
    return bool(session.get('jbs_cookies'))


def jbs_forget():
    session.pop('jbs_cookies', None)
    session.pop('jbs_email', None)

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


def parse_book_chapter(args):
    """リクエストの書・章が正しいか確かめる。正しくなければ (None, None)"""
    book = args.get('book', 'MAT')
    try:
        chapter = int(args.get('chapter', '1'))
    except ValueError:
        return None, None
    info = BOOK_MAP.get(book)
    if not info or not 1 <= chapter <= info['chapters']:
        return None, None
    return book, chapter


def strip_html(text):
    return re.sub(r'<[^>]+>', '', text).strip()


def jbs_login(email, password):
    """JBS APIにログインし、得たCookieをこの端末に保存"""
    s = requests.Session()
    s.headers.update(JBS_HEADERS)
    resp = s.post(
        'https://api.si.jbsbibleapp.com/api/v1/auth/signin',
        json={'email': email, 'password': password},
        timeout=15
    )
    if resp.status_code == 200:
        session.permanent = True
        session['jbs_email'] = email
        jbs_keep_cookies(s)
        return True, {}
    else:
        try:
            msg = resp.json().get('message', resp.text[:200])
        except Exception:
            msg = resp.text[:200]
        return False, msg


def jbs_get_chapter_json(book, chapter):
    """この端末のログインでJBS APIから章データを取得。(data, error) を返す"""
    url = f'https://api.si.jbsbibleapp.com/api/v1/bible/SI/{book}/{chapter - 1}'
    s = jbs_session()
    try:
        resp = s.get(url, timeout=20)
    except Exception as e:
        return None, f'接続エラー: {e}'
    if resp.status_code in (401, 403):
        # ログインの期限切れ → この端末で再ログインしてもらう
        jbs_forget()
        return None, 'not_logged_in'
    if resp.status_code != 200:
        return None, f'HTTP {resp.status_code}'
    jbs_keep_cookies(s)
    try:
        return resp.json(), None
    except Exception:
        return None, 'parse_error'


def jbs_fetch_chapter(book, chapter):
    key = f'jbs_{book}_{chapter}'
    if key in CACHE:
        return CACHE[key]

    data, err = jbs_get_chapter_json(book, chapter)
    if err:
        return {'error': err, 'items': [], 'count': 0}

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

        HEADING_CLASSES = {'s', 's1', 's2', 's3'}

        # ── 文書順に全要素（見出し・段落の開閉・節）を収集 ──
        # ※ 節アンカー <a class="v"> は <p> の外に「はみ出す」ことがあるため、
        #    <p> 単位ではなく HTML 全体から拾う（従来は <p> 外の節を取りこぼしていた）
        events = []
        for pm in re.finditer(r'<p\b([^>]*)>(.*?)</p>', html, re.DOTALL):
            cls_m = re.search(r'class="([^"]*)"', pm.group(1))
            cls = cls_m.group(1) if cls_m else ''
            inner = pm.group(2)
            if cls in HEADING_CLASSES:
                text = jbs_strip(inner)
                if text:
                    events.append((pm.start(), 0, 'heading', text))
            else:
                events.append((pm.start(), 0, 'popen', None))
                events.append((pm.end(), 2, 'pclose', None))

        for vm in re.finditer(r'<a[^>]*class="[^"]*\bv\b[^"]*"[^>]*index="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL):
            idx_raw = vm.group(1)
            nums = re.findall(r'\d+', idx_raw)
            if not nums:
                continue
            vnum = int(nums[0])
            label = idx_raw.strip() if len(nums) > 1 else str(vnum)
            lbl_m = re.search(r'<span[^>]*class="[^"]*v-number[^"]*"[^>]*>(.*?)</span>', vm.group(2), re.DOTALL)
            if lbl_m:
                lbl_text = re.sub(r'\s+', '', strip_html(lbl_m.group(1)))
                if lbl_text:
                    label = lbl_text
            text = jbs_strip(vm.group(2))
            if text:
                events.append((vm.start(), 1, 'verse', vnum, label, text))

        events.sort(key=lambda e: (e[0], e[1]))

        cur_parts = []
        cur_first = [None]

        def flush_jbs():
            if cur_parts:
                items.append({'type': 'para', 'lines': [
                    {'num': cur_first[0], 'parts': list(cur_parts)}]})
                cur_parts.clear()
                cur_first[0] = None

        for ev in events:
            kind = ev[2]
            if kind == 'heading':
                flush_jbs()
                items.append({'type': 'heading', 'text': ev[3]})
            elif kind in ('popen', 'pclose'):
                flush_jbs()
            elif kind == 'verse':
                vnum, label, text = ev[3], ev[4], ev[5]
                if cur_first[0] is None:
                    cur_first[0] = vnum
                cur_parts.append([label, text])

        flush_jbs()

    total = sum(len(i.get('lines', [])) for i in items if i['type'] == 'para')
    result = {
        'title': f'{book_info["name"]} {chapter}章',
        'items': items,
        'count': total,
    }
    if items:  # 空の結果は覚えない（一時的な不具合を再起動まで引きずらない）
        CACHE[key] = result
    return result


# ── Flask ルート ─────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html', books=BOOKS)


@app.route('/api/chapter')
def get_chapter():
    book, chapter = parse_book_chapter(request.args)
    if not book:
        return jsonify({'error': '書名または章が正しくありません', 'items': [], 'count': 0})

    if not jbs_logged_in():
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
    book, chapter = parse_book_chapter(request.args)
    if not book:
        return jsonify({'error': 'bad_request'})

    if not jbs_logged_in():
        return jsonify({'error': 'not_logged_in'})

    data, err = jbs_get_chapter_json(book, chapter)
    if err:
        return jsonify({'error': err})

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
    data = request.get_json(silent=True) or {}
    email    = data.get('email', '').strip()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'ok': False, 'message': 'メールアドレスとパスワードを入力してください'})

    jbs_forget()
    try:
        ok, result = jbs_login(email, password)
    except Exception as e:
        return jsonify({'ok': False, 'message': f'接続エラー: {e}'})

    if ok:
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'message': str(result)})


@app.route('/api/logout', methods=['POST'])
def api_logout():
    # この端末のログインだけを消す（他の端末には影響しない）
    jbs_forget()
    return jsonify({'ok': True})


@app.route('/api/status')
def api_status():
    return jsonify({
        'logged_in': jbs_logged_in(),
        'email': session.get('jbs_email', '') if jbs_logged_in() else '',
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5052))
    print(f'聖書協会訳対照を起動します: http://localhost:{port}')
    app.run(host='0.0.0.0', debug=False, port=port)
