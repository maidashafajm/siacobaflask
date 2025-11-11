from flask import Flask, request, redirect, session, flash, url_for
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from config import Config
from supabase import create_client, Client
import re
from datetime import datetime, timedelta

app = Flask(__name__)
app.config.from_object(Config)
mail = Mail(app)

# Inisialisasi Supabase Client
supabase: Client = create_client(
    app.config['SUPABASE_URL'],
    app.config['SUPABASE_KEY']
)

# Serializer untuk generate token
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# ============== FUNGSI HELPER ==============

def validate_password(password):
    """Validasi password sesuai ketentuan"""
    if len(password) < 8 or len(password) > 20:
        return False, "Password harus 8-20 karakter"
    if not re.search(r'[A-Z]', password):
        return False, "Password harus mengandung huruf besar"
    if not re.search(r'[a-z]', password):
        return False, "Password harus mengandung huruf kecil"
    if not re.search(r'\d', password):
        return False, "Password harus mengandung angka"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password harus mengandung karakter khusus (!@#$%^&*...)"
    return True, "Password valid"

def send_email(to, subject, html_content):
    """Kirim email"""
    msg = Message(subject, recipients=[to], html=html_content, sender=app.config['MAIL_DEFAULT_SENDER'])
    mail.send(msg)

# ============== DATABASE FUNCTIONS ==============

def get_user_by_email(email):
    """Ambil user dari database berdasarkan email"""
    try:
        response = supabase.table('users').select('*').eq('email', email).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error get_user_by_email: {e}")
        return None

def get_user_by_username(username):
    """Ambil user dari database berdasarkan username"""
    try:
        response = supabase.table('users').select('*').eq('username', username).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error get_user_by_username: {e}")
        return None

def create_pending_registration(email, role, token):
    """Buat pending registration di database"""
    try:
        # Hapus pending registration lama dengan email yang sama
        supabase.table('pending_registrations').delete().eq('email', email).execute()
        
        # Buat pending registration baru
        expires_at = (datetime.now() + timedelta(hours=1)).isoformat()
        data = {
            'email': email,
            'role': role,
            'token': token,
            'expires_at': expires_at
        }
        response = supabase.table('pending_registrations').insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error create_pending_registration: {e}")
        return None

def get_pending_registration(email):
    """Ambil pending registration berdasarkan email"""
    try:
        response = supabase.table('pending_registrations').select('*').eq('email', email).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error get_pending_registration: {e}")
        return None

def delete_pending_registration(email):
    """Hapus pending registration setelah berhasil verifikasi"""
    try:
        supabase.table('pending_registrations').delete().eq('email', email).execute()
        return True
    except Exception as e:
        print(f"Error delete_pending_registration: {e}")
        return False

def create_user(email, username, password, role):
    """Buat user baru di database"""
    try:
        password_hash = generate_password_hash(password)
        data = {
            'email': email,
            'username': username,
            'password_hash': password_hash,
            'role': role
        }
        response = supabase.table('users').insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error create_user: {e}")
        return None

def update_user_password(email, new_password):
    """Update password user"""
    try:
        password_hash = generate_password_hash(new_password)
        data = {'password_hash': password_hash, 'updated_at': datetime.now().isoformat()}
        response = supabase.table('users').update(data).eq('email', email).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error update_user_password: {e}")
        return None

# ============== HTML GENERATOR FUNCTIONS ==============

def generate_base_style():
    """Generate CSS base style"""
    return """
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            max-width: 500px;
            width: 100%;
        }
        .logo { font-size: 50px; text-align: center; margin-bottom: 10px; }
        h1 { color: #667eea; text-align: center; margin-bottom: 30px; font-size: 28px; }
        .subtitle { text-align: center; color: #666; margin-bottom: 30px; font-size: 14px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; color: #333; font-weight: bold; margin-bottom: 8px; }
        input, select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        input:focus, select:focus { outline: none; border-color: #667eea; }
        .btn {
            width: 100%;
            padding: 15px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            background: #667eea;
            color: white;
        }
        .btn:hover {
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        .links { text-align: center; margin-top: 20px; }
        .links a { color: #667eea; text-decoration: none; font-size: 14px; }
        .links a:hover { text-decoration: underline; }
        .alert {
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .password-requirements {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 13px;
        }
        .password-requirements h3 {
            color: #333;
            font-size: 14px;
            margin-bottom: 10px;
        }
        .password-requirements ul {
            margin-left: 20px;
            color: #666;
        }
        .password-requirements li { margin-bottom: 5px; }
    </style>
    """

def generate_index_page():
    """Generate halaman index (home)"""
    style = """
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 50px;
            max-width: 500px;
            width: 100%;
            text-align: center;
        }
        .logo { font-size: 60px; margin-bottom: 10px; }
        h1 { color: #667eea; margin-bottom: 10px; font-size: 36px; }
        .subtitle { color: #666; margin-bottom: 40px; font-size: 14px; }
        .role-selection { margin-bottom: 30px; }
        .role-selection h2 {
            color: #333;
            margin-bottom: 20px;
            font-size: 20px;
        }
        .role-buttons {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        .role-btn {
            background: white;
            border: 2px solid #667eea;
            color: #667eea;
            padding: 20px;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 16px;
            font-weight: bold;
            text-decoration: none;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 10px;
        }
        .role-btn:hover {
            background: #667eea;
            color: white;
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }
        .role-btn .icon { font-size: 30px; }
        .auth-buttons {
            display: flex;
            gap: 15px;
            margin-top: 30px;
        }
        .btn {
            flex: 1;
            padding: 15px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
            display: inline-block;
        }
        .btn-primary {
            background: #667eea;
            color: white;
        }
        .btn-primary:hover {
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        .btn-secondary {
            background: #f0f0f0;
            color: #333;
        }
        .btn-secondary:hover {
            background: #e0e0e0;
            transform: translateY(-2px);
        }
    </style>
    """
    
    html = f"""
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Geboy Mujair - Sistem Akuntansi Budidaya Ikan</title>
        {style}
    </head>
    <body>
        <div class="container">
            <div class="logo">🐟</div>
            <h1>Geboy Mujair</h1>
            <p class="subtitle">Sistem Akuntansi Budidaya Ikan Mujair</p>
            
            <div class="role-selection">
                <h2>Pilih Role Anda</h2>
                <div class="role-buttons">
                    <a href="/register?role=kasir" class="role-btn">
                        <span class="icon">💰</span>
                        <span>Kasir</span>
                    </a>
                    <a href="/register?role=akuntan" class="role-btn">
                        <span class="icon">📊</span>
                        <span>Akuntan</span>
                    </a>
                    <a href="/register?role=owner" class="role-btn">
                        <span class="icon">👔</span>
                        <span>Owner</span>
                    </a>
                    <a href="/register?role=karyawan" class="role-btn">
                        <span class="icon">👷</span>
                        <span>Karyawan</span>
                    </a>
                </div>
            </div>
            
            <div class="auth-buttons">
                <a href="/login" class="btn btn-primary">Login</a>
                <a href="/register" class="btn btn-secondary">Daftar</a>
            </div>
        </div>
    </body>
    </html>
    """
    return html

def generate_register_page(role=''):
    """Generate halaman registrasi"""
    flash_html = ''.join([
        f'<div class="alert alert-{cat}">{msg}</div>'
        for cat, msg in session.pop('_flashes', [])
    ])
    
    html = f"""
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Daftar - Geboy Mujair</title>
        {generate_base_style()}
    </head>
    <body>
        <div class="container">
            <div class="logo">🐟</div>
            <h1>Daftar Akun</h1>
            {flash_html}
            <form method="POST" action="/register">
                <div class="form-group">
                    <label for="email">Email</label>
                    <input type="email" id="email" name="email" required placeholder="email@example.com">
                </div>
                <div class="form-group">
                    <label for="role">Role</label>
                    <select id="role" name="role" required>
                        <option value="">-- Pilih Role --</option>
                        <option value="kasir" {'selected' if role == 'kasir' else ''}>Kasir</option>
                        <option value="akuntan" {'selected' if role == 'akuntan' else ''}>Akuntan</option>
                        <option value="owner" {'selected' if role == 'owner' else ''}>Owner</option>
                        <option value="karyawan" {'selected' if role == 'karyawan' else ''}>Karyawan</option>
                    </select>
                </div>
                <button type="submit" class="btn">Daftar</button>
            </form>
            <div class="links">
                <p>Sudah punya akun? <a href="/login">Login di sini</a></p>
                <p><a href="/">← Kembali ke Halaman Utama</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    return html

def generate_verify_email_page(token):
    """Generate halaman verifikasi email"""
    flash_html = ''.join([
        f'<div class="alert alert-{cat}">{msg}</div>'
        for cat, msg in session.pop('_flashes', [])
    ])
    
    html = f"""
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Verifikasi Email - Geboy Mujair</title>
        {generate_base_style()}
    </head>
    <body>
        <div class="container">
            <div class="logo">✉️</div>
            <h1>Buat Akun</h1>
            <p class="subtitle">Email Anda telah diverifikasi! Silakan buat username dan password.</p>
            {flash_html}
            <form method="POST">
                <div class="form-group">
                    <label for="username">Username</label>
                    <input type="text" id="username" name="username" required placeholder="Minimal 3 karakter" minlength="3">
                </div>
                <div class="password-requirements">
                    <h3>Ketentuan Password:</h3>
                    <ul>
                        <li>8-20 karakter</li>
                        <li>Minimal 1 huruf besar (A-Z)</li>
                        <li>Minimal 1 huruf kecil (a-z)</li>
                        <li>Minimal 1 angka (0-9)</li>
                        <li>Minimal 1 karakter khusus (!@#$%^&*...)</li>
                    </ul>
                </div>
                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" required placeholder="Masukkan password">
                </div>
                <div class="form-group">
                    <label for="confirm_password">Konfirmasi Password</label>
                    <input type="password" id="confirm_password" name="confirm_password" required placeholder="Ulangi password">
                </div>
                <button type="submit" class="btn">Buat Akun</button>
            </form>
        </div>
    </body>
    </html>
    """
    return html

def generate_login_page():
    """Generate halaman login"""
    flash_html = ''.join([
        f'<div class="alert alert-{cat}">{msg}</div>'
        for cat, msg in session.pop('_flashes', [])
    ])
    
    html = f"""
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Login - Geboy Mujair</title>
        {generate_base_style()}
    </head>
    <body>
        <div class="container">
            <div class="logo">🐟</div>
            <h1>Login</h1>
            {flash_html}
            <form method="POST" action="/login">
                <div class="form-group">
                    <label for="username">Username</label>
                    <input type="text" id="username" name="username" required placeholder="Masukkan username">
                </div>
                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" required placeholder="Masukkan password">
                </div>
                <button type="submit" class="btn">Login</button>
            </form>
            <div class="links">
                <a href="/forgot-password">Lupa Password?</a>
                <p>Belum punya akun? <a href="/register">Daftar di sini</a></p>
                <a href="/">← Kembali ke Halaman Utama</a>
            </div>
        </div>
    </body>
    </html>
    """
    return html

def generate_forgot_password_page():
    """Generate halaman lupa password"""
    flash_html = ''.join([
        f'<div class="alert alert-{cat}">{msg}</div>'
        for cat, msg in session.pop('_flashes', [])
    ])
    
    html = f"""
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Lupa Password - Geboy Mujair</title>
        {generate_base_style()}
    </head>
    <body>
        <div class="container">
            <div class="logo">🔑</div>
            <h1>Lupa Password</h1>
            <p class="subtitle">Masukkan email Anda dan kami akan mengirimkan link untuk reset password.</p>
            {flash_html}
            <form method="POST" action="/forgot-password">
                <div class="form-group">
                    <label for="email">Email</label>
                    <input type="email" id="email" name="email" required placeholder="email@example.com">
                </div>
                <button type="submit" class="btn">Kirim Link Reset</button>
            </form>
            <div class="links">
                <p><a href="/login">← Kembali ke Login</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    return html

def generate_reset_password_page(token):
    """Generate halaman reset password"""
    flash_html = ''.join([
        f'<div class="alert alert-{cat}">{msg}</div>'
        for cat, msg in session.pop('_flashes', [])
    ])
    
    html = f"""
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Reset Password - Geboy Mujair</title>
        {generate_base_style()}
    </head>
    <body>
        <div class="container">
            <div class="logo">🔒</div>
            <h1>Reset Password</h1>
            <p class="subtitle">Buat password baru untuk akun Anda.</p>
            {flash_html}
            <form method="POST">
                <div class="password-requirements">
                    <h3>Ketentuan Password:</h3>
                    <ul>
                        <li>8-20 karakter</li>
                        <li>Minimal 1 huruf besar (A-Z)</li>
                        <li>Minimal 1 huruf kecil (a-z)</li>
                        <li>Minimal 1 angka (0-9)</li>
                        <li>Minimal 1 karakter khusus (!@#$%^&*...)</li>
                    </ul>
                </div>
                <div class="form-group">
                    <label for="password">Password Baru</label>
                    <input type="password" id="password" name="password" required placeholder="Masukkan password baru">
                </div>
                <div class="form-group">
                    <label for="confirm_password">Konfirmasi Password</label>
                    <input type="password" id="confirm_password" name="confirm_password" required placeholder="Ulangi password baru">
                </div>
                <button type="submit" class="btn">Reset Password</button>
            </form>
        </div>
    </body>
    </html>
    """
    return html

def generate_dashboard(role, username):
    """Generate dashboard sesuai role"""
    role_info = {
        'kasir': {
            'icon': '💰',
            'title': 'Dashboard Kasir',
            'welcome': 'Selamat Datang, Kasir!',
            'subtitle': 'Kelola transaksi dan penjualan ikan mujair dengan mudah',
            'features': [
                ('🛒', 'Transaksi Penjualan', 'Catat penjualan ikan mujair'),
                ('📝', 'Riwayat Transaksi', 'Lihat riwayat transaksi harian'),
                ('💵', 'Laporan Kas', 'Laporan pemasukan dan pengeluaran'),
            ]
        },
        'akuntan': {
            'icon': '📊',
            'title': 'Dashboard Akuntan',
            'welcome': 'Selamat Datang, Akuntan!',
            'subtitle': 'Kelola siklus akuntansi budidaya ikan mujair',
            'features': [
                ('📖', 'Jurnal Umum', 'Catat transaksi keuangan'),
                ('📚', 'Buku Besar', 'Posting ke buku besar'),
                ('⚖️', 'Neraca Saldo', 'Lihat neraca saldo periode'),
                ('📋', 'Laporan Keuangan', 'Generate laporan keuangan'),
            ]
        },
        'owner': {
            'icon': '👔',
            'title': 'Dashboard Owner',
            'welcome': 'Selamat Datang, Owner!',
            'subtitle': 'Pantau seluruh operasional budidaya ikan mujair Anda',
            'features': [
                ('📈', 'Dashboard Analytics', 'Lihat performa bisnis real-time'),
                ('💼', 'Laporan Keuangan', 'Analisis laporan laba rugi'),
                ('👥', 'Manajemen Tim', 'Kelola karyawan dan kasir'),
                ('🎯', 'Target & Planning', 'Set target produksi dan penjualan'),
            ]
        },
        'karyawan': {
            'icon': '👷',
            'title': 'Dashboard Karyawan',
            'welcome': 'Selamat Datang, Karyawan!',
            'subtitle': 'Kelola kegiatan operasional budidaya ikan mujair',
            'features': [
                ('🐠', 'Monitoring Kolam', 'Catat kondisi kolam ikan'),
                ('🍽️', 'Pemberian Pakan', 'Jadwal dan catat pemberian pakan'),
                ('📊', 'Laporan Harian', 'Buat laporan kegiatan harian'),
                ('🔔', 'Notifikasi', 'Lihat tugas dan reminder'),
            ]
        }
    }
    
    info = role_info.get(role, role_info['kasir'])
    
    features_html = ''
    for icon, title, desc in info['features']:
        features_html += f"""
        <div class="feature-card">
            <div class="feature-icon">{icon}</div>
            <h3>{title}</h3>
            <p>{desc}</p>
        </div>
        """
    
    style = """
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header-left {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .logo { font-size: 40px; }
        .header-info h1 {
            color: #667eea;
            font-size: 28px;
            margin-bottom: 5px;
        }
        .header-info p {
            color: #666;
            font-size: 14px;
        }
        .logout-btn {
            background: #f44336;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.3s;
        }
        .logout-btn:hover {
            background: #da190b;
            transform: translateY(-2px);
        }
        .content {
            background: white;
            border-radius: 15px;
            padding: 40px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            text-align: center;
        }
        .welcome {
            font-size: 50px;
            margin-bottom: 20px;
        }
        .content h2 {
            color: #333;
            font-size: 32px;
            margin-bottom: 10px;
        }
        .content p {
            color: #666;
            font-size: 16px;
            line-height: 1.6;
        }
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        .feature-card {
            background: #f8f9fa;
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            transition: all 0.3s;
        }
        .feature-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        }
        .feature-icon {
            font-size: 40px;
            margin-bottom: 15px;
        }
        .feature-card h3 {
            color: #333;
            margin-bottom: 10px;
        }
        .feature-card p {
            color: #666;
            font-size: 14px;
        }
    </style>
    """
    
    html = f"""
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{info['title']} - Geboy Mujair</title>
        {style}
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="header-left">
                    <div class="logo">🐟</div>
                    <div class="header-info">
                        <h1>{info['title']}</h1>
                        <p>Selamat datang, {username}!</p>
                    </div>
                </div>
                <a href="/logout" class="logout-btn">Logout</a>
            </div>
            
            <div class="content">
                <div class="welcome">{info['icon']}</div>
                <h2>{info['welcome']}</h2>
                <p>{info['subtitle']}</p>
                
                <div class="features">
                    {features_html}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html

# ============== ROUTES ==============

@app.route('/')
def index():
    return generate_index_page()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        role = request.form.get('role')
        
        # Validasi email
        if not email or '@' not in email:
            flash('Email tidak valid!', 'error')
            return redirect(url_for('register'))
        
        # Cek apakah email sudah terdaftar
        if get_user_by_email(email):
            flash('Email sudah terdaftar!', 'error')
            return redirect(url_for('register'))
        
        # Generate token untuk verifikasi email
        token = serializer.dumps(email, salt='email-verification')
        
        # Simpan data sementara di Supabase
        if not create_pending_registration(email, role, token):
            flash('Gagal menyimpan data registrasi!', 'error')
            return redirect(url_for('register'))
        
        # Kirim email verifikasi
        verify_url = url_for('verify_email', token=token, _external=True)
        html = f"""
        <h2>Verifikasi Email Geboy Mujair</h2>
        <p>Terima kasih telah mendaftar!</p>
        <p>Klik link di bawah untuk melanjutkan pendaftaran:</p>
        <p><a href="{verify_url}">Verifikasi Email</a></p>
        <p>Link ini berlaku selama 1 jam.</p>
        """
        
        try:
            send_email(email, 'Verifikasi Email Geboy Mujair', html)
            flash('Email verifikasi telah dikirim! Cek inbox Anda.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Gagal mengirim email: {str(e)}', 'error')
            return redirect(url_for('register'))
    
    role = request.args.get('role', '')
    return generate_register_page(role)

@app.route('/verify/<token>', methods=['GET', 'POST'])
def verify_email(token):
    try:
        # Verifikasi token (expired setelah 1 jam)
        email = serializer.loads(token, salt='email-verification', max_age=3600)
    except SignatureExpired:
        flash('Link verifikasi sudah expired!', 'error')
        return redirect(url_for('register'))
    except BadSignature:
        flash('Link verifikasi tidak valid!', 'error')
        return redirect(url_for('register'))
    
    # Cek apakah pending registration ada
    pending = get_pending_registration(email)
    if not pending:
        flash('Data pendaftaran tidak ditemukan!', 'error')
        return redirect(url_for('register'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validasi username
        if not username or len(username) < 3:
            flash('Username minimal 3 karakter!', 'error')
            return generate_verify_email_page(token)
        
        # Cek username sudah dipakai atau belum
        if get_user_by_username(username):
            flash('Username sudah digunakan!', 'error')
            return generate_verify_email_page(token)
        
        # Validasi password
        if password != confirm_password:
            flash('Password tidak cocok!', 'error')
            return generate_verify_email_page(token)
        
        is_valid, message = validate_password(password)
        if not is_valid:
            flash(message, 'error')
            return generate_verify_email_page(token)
        
        # Buat user baru
        role = pending['role']
        user = create_user(email, username, password, role)
        
        if not user:
            flash('Gagal membuat akun! Coba lagi.', 'error')
            return generate_verify_email_page(token)
        
        # Hapus pending registration
        delete_pending_registration(email)
        
        flash('Registrasi berhasil! Silakan login.', 'success')
        return redirect(url_for('login'))
    
    return generate_verify_email_page(token)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Cari user berdasarkan username
        user = get_user_by_username(username)
        
        if not user:
            flash('Username atau password salah!', 'error')
            return redirect(url_for('login'))
        
        # Cek password
        if not check_password_hash(user['password_hash'], password):
            flash('Username atau password salah!', 'error')
            return redirect(url_for('login'))
        
        # Login berhasil
        session['username'] = username
        session['role'] = user['role']
        session['email'] = user['email']
        
        # Redirect ke dashboard sesuai role
        return redirect(url_for(f'dashboard_{user["role"]}'))
    
    return generate_login_page()

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        
        user = get_user_by_email(email)
        if not user:
            flash('Email tidak terdaftar!', 'error')
            return redirect(url_for('forgot_password'))
        
        # Generate token untuk reset password
        token = serializer.dumps(email, salt='password-reset')
        
        # Kirim email reset password
        reset_url = url_for('reset_password', token=token, _external=True)
        html = f"""
        <h2>Reset Password Geboy Mujair</h2>
        <p>Anda meminta reset password.</p>
        <p>Klik link di bawah untuk membuat password baru:</p>
        <p><a href="{reset_url}">Reset Password</a></p>
        <p>Link ini berlaku selama 1 jam.</p>
        <p>Jika Anda tidak meminta reset password, abaikan email ini.</p>
        """
        
        try:
            send_email(email, 'Reset Password Geboy Mujair', html)
            flash('Link reset password telah dikirim ke email Anda!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Gagal mengirim email: {str(e)}', 'error')
            return redirect(url_for('forgot_password'))
    
    return generate_forgot_password_page()

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        # Verifikasi token (expired setelah 1 jam)
        email = serializer.loads(token, salt='password-reset', max_age=3600)
    except SignatureExpired:
        flash('Link reset password sudah expired!', 'error')
        return redirect(url_for('forgot_password'))
    except BadSignature:
        flash('Link reset password tidak valid!', 'error')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validasi password
        if password != confirm_password:
            flash('Password tidak cocok!', 'error')
            return generate_reset_password_page(token)
        
        is_valid, message = validate_password(password)
        if not is_valid:
            flash(message, 'error')
            return generate_reset_password_page(token)
        
        # Update password
        if update_user_password(email, password):
            flash('Password berhasil direset! Silakan login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Gagal reset password! Coba lagi.', 'error')
            return generate_reset_password_page(token)
    
    return generate_reset_password_page(token)

@app.route('/dashboard/kasir')
def dashboard_kasir():
    if 'username' not in session or session.get('role') != 'kasir':
        flash('Silakan login terlebih dahulu!', 'error')
        return redirect(url_for('login'))
    return generate_dashboard('kasir', session['username'])

@app.route('/dashboard/akuntan')
def dashboard_akuntan():
    if 'username' not in session or session.get('role') != 'akuntan':
        flash('Silakan login terlebih dahulu!', 'error')
        return redirect(url_for('login'))
    return generate_dashboard('akuntan', session['username'])

@app.route('/dashboard/owner')
def dashboard_owner():
    if 'username' not in session or session.get('role') != 'owner':
        flash('Silakan login terlebih dahulu!', 'error')
        return redirect(url_for('login'))
    return generate_dashboard('owner', session['username'])

@app.route('/dashboard/karyawan')
def dashboard_karyawan():
    if 'username' not in session or session.get('role') != 'karyawan':
        flash('Silakan login terlebih dahulu!', 'error')
        return redirect(url_for('login'))
    return generate_dashboard('karyawan', session['username'])

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah logout!', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)