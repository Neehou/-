"""
东华倪家 - 家庭门户网站
Flask + SQLite + 登录认证
"""
import os
import sys
import io
import hashlib
import secrets
import sqlite3
import uuid
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, g, session, redirect, url_for

# 解决 Windows 控制台编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

app = Flask(__name__, static_folder='public', static_url_path='')

# 密钥（用于 session 加密）
SECRET_KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', '.secret_key')
os.makedirs(os.path.dirname(SECRET_KEY_FILE), exist_ok=True)
if os.path.exists(SECRET_KEY_FILE):
    with open(SECRET_KEY_FILE, 'r') as f:
        app.secret_key = f.read().strip()
else:
    app.secret_key = secrets.token_hex(32)
    with open(SECRET_KEY_FILE, 'w') as f:
        f.write(app.secret_key)

# 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DB_DIR, 'family.db')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

MEMBER_COLORS = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#FF9FF3', '#54A0FF']


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys=ON")

    db.executescript('''
        CREATE TABLE IF NOT EXISTS family_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            color TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_by INTEGER NOT NULL,
            assigned_to INTEGER,
            status TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo', 'done')),
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            completed_at TEXT,
            FOREIGN KEY (created_by) REFERENCES members(id),
            FOREIGN KEY (assigned_to) REFERENCES members(id)
        );

        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_name TEXT NOT NULL,
            uploaded_by INTEGER NOT NULL,
            caption TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (uploaded_by) REFERENCES members(id)
        );
    ''')

    # 预设家庭成员
    count = db.execute('SELECT COUNT(*) FROM members').fetchone()[0]
    if count == 0:
        default_members = [
            ('爸爸', MEMBER_COLORS[0]),
            ('妈妈', MEMBER_COLORS[1]),
            ('宝贝', MEMBER_COLORS[2]),
        ]
        db.executemany('INSERT INTO members (name, color) VALUES (?, ?)', default_members)

    db.commit()
    db.close()


init_db()


# ==================== 登录验证装饰器 ====================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            # API 请求返回 JSON 错误
            if request.path.startswith('/api/'):
                return jsonify({'error': '未登录', 'redirect': '/login'}), 401
            # 页面请求重定向到登录页
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated


# ==================== 登录 / 设置页面 ====================

@app.route('/login')
def login_page():
    # 检测是否需要首次设置
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    user_count = db.execute('SELECT COUNT(*) as c FROM family_users').fetchone()['c']
    db.close()

    if user_count == 0:
        # 首次使用，显示设置页
        return send_from_directory('public', 'login.html')
    elif session.get('logged_in'):
        return redirect('/')
    else:
        return send_from_directory('public', 'login.html')


# ==================== 认证 API ====================

@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    user_count = db.execute('SELECT COUNT(*) as c FROM family_users').fetchone()['c']
    db.close()

    return jsonify({
        'logged_in': session.get('logged_in', False),
        'username': session.get('username', ''),
        'needs_setup': user_count == 0
    })


@app.route('/api/auth/setup', methods=['POST'])
def auth_setup():
    """首次设置：创建管理员账号"""
    db = get_db()
    user_count = db.execute('SELECT COUNT(*) FROM family_users').fetchone()[0]
    if user_count > 0:
        return jsonify({'error': '已存在管理员账号，请直接登录'}), 400

    data = request.get_json()
    if not data:
        return jsonify({'error': '请提供账号信息'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or len(username) < 2:
        return jsonify({'error': '账号至少2个字符'}), 400
    if not password or len(password) < 4:
        return jsonify({'error': '密码至少4个字符'}), 400

    password_hash = hash_password(password)
    db.execute(
        'INSERT INTO family_users (username, password_hash, is_admin) VALUES (?, ?, 1)',
        (username, password_hash)
    )
    db.commit()

    # 自动登录
    session['logged_in'] = True
    session['username'] = username
    session.permanent = True

    return jsonify({'message': '设置成功', 'username': username})


@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    data = request.get_json()
    if not data:
        return jsonify({'error': '请输入账号密码'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'error': '请输入账号和密码'}), 400

    db = get_db()
    user = db.execute(
        'SELECT * FROM family_users WHERE username = ?',
        (username,)
    ).fetchone()

    if not user:
        return jsonify({'error': '账号不存在'}), 401

    if user['password_hash'] != hash_password(password):
        return jsonify({'error': '密码错误'}), 401

    session['logged_in'] = True
    session['username'] = username
    session.permanent = True

    return jsonify({'message': '登录成功', 'username': username})


@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    session.clear()
    return jsonify({'message': '已退出'})


# ==================== 静态页面（需登录） ====================

@app.route('/')
@login_required
def index():
    return send_from_directory('public', 'index.html')


@app.route('/stats')
@login_required
def stats_page():
    return send_from_directory('public', 'stats.html')


@app.route('/photos')
@login_required
def photos_page():
    return send_from_directory('public', 'photos.html')


# ==================== 成员 API（需登录） ====================

@app.route('/api/members', methods=['GET'])
@login_required
def get_members():
    db = get_db()
    members = db.execute('SELECT id, name, color, created_at FROM members ORDER BY id').fetchall()
    return jsonify([dict(m) for m in members])


@app.route('/api/members', methods=['POST'])
@login_required
def add_member():
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': '请提供成员名称'}), 400

    name = data['name'].strip()
    if not name:
        return jsonify({'error': '名称不能为空'}), 400

    db = get_db()
    exist = db.execute('SELECT id FROM members WHERE name = ?', (name,)).fetchone()
    if exist:
        return jsonify({'error': '该名称已存在'}), 400

    count = db.execute('SELECT COUNT(*) FROM members').fetchone()[0]
    color = data.get('color', MEMBER_COLORS[count % len(MEMBER_COLORS)])

    cursor = db.execute('INSERT INTO members (name, color) VALUES (?, ?)', (name, color))
    db.commit()

    return jsonify({'id': cursor.lastrowid, 'name': name, 'color': color}), 201


# ==================== 任务 API（需登录） ====================

@app.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks():
    db = get_db()
    status = request.args.get('status', 'all')

    query = '''
        SELECT t.id, t.title, t.description, t.status, t.created_at, t.completed_at,
               t.created_by, t.assigned_to,
               c.name as creator_name, c.color as creator_color,
               a.name as assignee_name, a.color as assignee_color
        FROM tasks t
        JOIN members c ON t.created_by = c.id
        LEFT JOIN members a ON t.assigned_to = a.id
    '''
    params = []
    if status == 'todo':
        query += ' WHERE t.status = ? ORDER BY t.created_at DESC'
        params.append('todo')
    elif status == 'done':
        query += ' WHERE t.status = ? ORDER BY t.completed_at DESC'
        params.append('done')
    else:
        query += ' ORDER BY CASE WHEN t.status = "todo" THEN 0 ELSE 1 END, t.created_at DESC'

    tasks = db.execute(query, params).fetchall()
    return jsonify([dict(t) for t in tasks])


@app.route('/api/tasks', methods=['POST'])
@login_required
def create_task():
    data = request.get_json()
    if not data or not data.get('title'):
        return jsonify({'error': '请填写任务标题'}), 400

    title = data['title'].strip()
    if not title:
        return jsonify({'error': '标题不能为空'}), 400

    created_by = data.get('created_by')
    if not created_by:
        return jsonify({'error': '请选择发布者'}), 400

    db = get_db()
    member = db.execute('SELECT id FROM members WHERE id = ?', (created_by,)).fetchone()
    if not member:
        return jsonify({'error': '成员不存在'}), 400

    description = data.get('description', '').strip()

    cursor = db.execute(
        'INSERT INTO tasks (title, description, created_by) VALUES (?, ?, ?)',
        (title, description, created_by)
    )
    db.commit()

    task = db.execute('''
        SELECT t.*, c.name as creator_name, c.color as creator_color
        FROM tasks t JOIN members c ON t.created_by = c.id WHERE t.id = ?
    ''', (cursor.lastrowid,)).fetchone()

    return jsonify(dict(task)), 201


@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    data = request.get_json()
    db = get_db()

    task = db.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
    if not task:
        return jsonify({'error': '任务不存在'}), 404

    updates = []
    params = []

    if 'assigned_to' in data:
        assigned_to = data['assigned_to']
        if assigned_to is not None:
            member = db.execute('SELECT id FROM members WHERE id = ?', (assigned_to,)).fetchone()
            if not member:
                return jsonify({'error': '成员不存在'}), 400
        updates.append('assigned_to = ?')
        params.append(assigned_to)

    if 'status' in data:
        new_status = data['status']
        if new_status not in ('todo', 'done'):
            return jsonify({'error': '无效的状态'}), 400
        updates.append('status = ?')
        params.append(new_status)
        if new_status == 'done':
            updates.append('completed_at = ?')
            params.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        else:
            updates.append('completed_at = NULL')

    if not updates:
        return jsonify({'error': '没有要更新的字段'}), 400

    params.append(task_id)
    db.execute(f'UPDATE tasks SET {", ".join(updates)} WHERE id = ?', params)
    db.commit()

    updated = db.execute('''
        SELECT t.*, c.name as creator_name, c.color as creator_color,
               a.name as assignee_name, a.color as assignee_color
        FROM tasks t JOIN members c ON t.created_by = c.id
        LEFT JOIN members a ON t.assigned_to = a.id
        WHERE t.id = ?
    ''', (task_id,)).fetchone()

    return jsonify(dict(updated))


@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    db = get_db()
    task = db.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    db.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    db.commit()
    return jsonify({'message': '删除成功'})


# ==================== 照片 API（需登录） ====================

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/photos', methods=['GET'])
@login_required
def get_photos():
    db = get_db()
    photos = db.execute('''
        SELECT p.*, m.name as uploader_name, m.color as uploader_color
        FROM photos p JOIN members m ON p.uploaded_by = m.id
        ORDER BY p.created_at DESC
    ''').fetchall()
    return jsonify([dict(p) for p in photos])


@app.route('/api/photos', methods=['POST'])
@login_required
def upload_photo():
    if 'photo' not in request.files:
        return jsonify({'error': '请选择照片'}), 400

    file = request.files['photo']
    if file.filename == '':
        return jsonify({'error': '请选择照片'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': '不支持的图片格式，支持: png, jpg, jpeg, gif, webp, bmp'}), 400

    uploaded_by = request.form.get('uploaded_by')
    if not uploaded_by:
        return jsonify({'error': '请选择上传者'}), 400

    db = get_db()
    member = db.execute('SELECT id FROM members WHERE id = ?', (uploaded_by,)).fetchone()
    if not member:
        return jsonify({'error': '成员不存在'}), 400

    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(UPLOAD_DIR, unique_name))

    caption = request.form.get('caption', '').strip()

    cursor = db.execute(
        'INSERT INTO photos (filename, original_name, uploaded_by, caption) VALUES (?, ?, ?, ?)',
        (unique_name, file.filename, int(uploaded_by), caption)
    )
    db.commit()

    photo = db.execute('''
        SELECT p.*, m.name as uploader_name, m.color as uploader_color
        FROM photos p JOIN members m ON p.uploaded_by = m.id
        WHERE p.id = ?
    ''', (cursor.lastrowid,)).fetchone()

    return jsonify(dict(photo)), 201


@app.route('/api/photos/<int:photo_id>', methods=['DELETE'])
@login_required
def delete_photo(photo_id):
    db = get_db()
    photo = db.execute('SELECT * FROM photos WHERE id = ?', (photo_id,)).fetchone()
    if not photo:
        return jsonify({'error': '照片不存在'}), 404

    filepath = os.path.join(UPLOAD_DIR, photo['filename'])
    if os.path.exists(filepath):
        os.remove(filepath)

    db.execute('DELETE FROM photos WHERE id = ?', (photo_id,))
    db.commit()
    return jsonify({'message': '删除成功'})


@app.route('/uploads/<filename>')
@login_required
def serve_photo(filename):
    return send_from_directory(UPLOAD_DIR, filename)


# ==================== 统计 API（需登录） ====================

@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    db = get_db()
    members = db.execute('SELECT id, name, color FROM members ORDER BY id').fetchall()

    stats = []
    for m in members:
        done_count = db.execute(
            'SELECT COUNT(*) FROM tasks WHERE assigned_to = ? AND status = "done"', (m['id'],)
        ).fetchone()[0]
        created_count = db.execute(
            'SELECT COUNT(*) FROM tasks WHERE created_by = ?', (m['id'],)
        ).fetchone()[0]
        ongoing_count = db.execute(
            'SELECT COUNT(*) FROM tasks WHERE assigned_to = ? AND status = "todo"', (m['id'],)
        ).fetchone()[0]
        photo_count = db.execute(
            'SELECT COUNT(*) FROM photos WHERE uploaded_by = ?', (m['id'],)
        ).fetchone()[0]

        stats.append({
            'member_id': m['id'],
            'name': m['name'],
            'color': m['color'],
            'done_count': done_count,
            'created_count': created_count,
            'ongoing_count': ongoing_count,
            'photo_count': photo_count,
            'total_score': done_count * 10 + created_count * 3 + photo_count * 5
        })

    stats.sort(key=lambda x: x['total_score'], reverse=True)

    total_tasks = db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0]
    total_done = db.execute('SELECT COUNT(*) FROM tasks WHERE status = "done"').fetchone()[0]
    total_photos = db.execute('SELECT COUNT(*) FROM photos').fetchone()[0]

    return jsonify({
        'members': stats,
        'summary': {'total_tasks': total_tasks, 'total_done': total_done, 'total_photos': total_photos}
    })


# ==================== 启动 ====================

def get_local_ip():
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def get_ngrok_token():
    for i, arg in enumerate(sys.argv):
        if arg == '--token' and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    token = os.environ.get('NGROK_AUTH_TOKEN')
    if token:
        return token
    token_file = os.path.join(BASE_DIR, '.ngrok_token')
    if os.path.exists(token_file):
        try:
            with open(token_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception:
            pass
    return None


def start_ngrok():
    token = get_ngrok_token()
    if not token:
        return None
    try:
        from pyngrok import ngrok, conf
        conf.get_default().auth_token = token
        tunnel = ngrok.connect(5000, "http")
        return tunnel.public_url
    except Exception as e:
        print(f'  [ngrok 启动失败] {e}')
        return None


if __name__ == '__main__':
    local_ip = get_local_ip()
    public_url = start_ngrok()

    print('=' * 55)
    print('       东华倪家 - 家庭门户网站')
    print('=' * 55)

    if public_url:
        print(f'  [公网访问] {public_url}')
        print(f'     任何人、任何地方都可以打开！')
        print()
    else:
        print(f'  [提示] 配置 ngrok 即可从外网访问')
        print(f'     1. 注册: https://ngrok.com')
        print(f'     2. 创建 .ngrok_token 文件并粘贴 token')
        print(f'     3. 重新启动')
        print()

    if local_ip:
        print(f'  [局域网] http://{local_ip}:5000')
    print(f'  [本机]   http://localhost:5000')
    print()
    print(f'  首次使用需设置管理员账号密码')
    print('  按 Ctrl+C 停止服务')
    print('=' * 55)
    app.run(host='0.0.0.0', port=5000, debug=True)
