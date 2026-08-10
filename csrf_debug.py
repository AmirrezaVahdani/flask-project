from app import create_app
from flask import render_template
app = create_app()
with app.test_request_context('/admin/login'):
    html = render_template('admin/login.html')
    print('csrf count', html.count('name="csrf_token"'))
    print(html[:800])
